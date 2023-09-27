from fontTools import varLib
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.designspaceLib import DesignSpaceDocument, AxisDescriptor, SourceDescriptor
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.pointPen import PointToSegmentPen

from defcon import Glyph, Point

from datetime import datetime
from pathlib import Path
from tools.curveTools import curveConverter
from copy import deepcopy
from pathlib import Path
from ufo2ft import compileVariableTTF

base = Path(__file__).parent

@property
def position(self):
    return self.x, self.y

setattr(Point, "position", position)

def process_glyph(glyph, draw_sides, absolute=False, depth=160):
    drawings = []
    first_clockwise = glyph[0].clockwise
    for contour in glyph:
        print(contour, glyph)
        lowest_point = min(zip(contour.segments, range(len(contour.segments))),key=lambda x: x[0][-1].position[::-1],)[1]
        contour_reordered = (contour.segments[lowest_point:] + contour.segments[:lowest_point])
        values = [a[-1].y > b[-1].y for a, b in zip(contour_reordered, contour_reordered[1:] + contour_reordered[:1])
        ]
        if values[0] == values[-1]:
            try:
                index = values[::-1].index(not values[0])
            except ValueError:
                index = 0
            contour_reordered = contour_reordered[-index:] + contour_reordered[:-index]
            values = values[-index:] + values[:-index]
        last_value = values[0]
        drawing = contour.__class__()
        edges = [glyph.width / 2 + depth / 2, glyph.width / 2 - depth / 2]
        if absolute:
            edges = edges[:1] * 2
        if contour.clockwise:
            edges = edges[::-1]
        for index in range(1, len(values) + 1):
            value = values[index % len(values)]
            duplicate = False
            value_next = values[(index + 1) % len(values)]
            segment = contour_reordered[index % len(values)]
            segment_next = contour_reordered[(index + 1) % len(values)]
            if value != last_value:
                duplicate = True
                last_value = value
            for point in segment:
                x, y = point.position
                if draw_sides:
                    x = edges[0]
                drawing.appendPoint(Point((x, y), point.segmentType))
            if duplicate is True:
                x, y = segment[-1].position
                if draw_sides:
                    edges = edges[::-1]
                    x = edges[0]
                drawing.appendPoint(Point((x, y), "line"))
        if contour.clockwise and draw_sides:
            for segment in drawing.segments:
                for point in segment:
                    point.x = edges[(edges.index(point.x) + 1) % 2]
        drawings.append(drawing)
    output_glyph = Glyph()
    output_glyph.unicode = glyph.unicode
    output_glyph.name = glyph.name
    output_glyph.width = glyph.width
    for contour in drawings:
        output_glyph.appendContour(contour)
    return output_glyph

class TranslatingPen():
    def __init__(self, other_pen):
        self.other_pen = other_pen

    def moveTo(self, point):
        self.other_pen.moveTo(point)

    def lineTo(self, point):
        self.other_pen.lineTo(point)

    def closePath(self):
        self.other_pen.closePath()

    def qCurveTo(self, *points):
        self.other_pen.qCurveTo(*points)

def draw(master, glyph_name, defcon_glyph, go=[]):
    if isinstance(master, TTFont):
        pen = TTGlyphPen(go)
        defcon_glyph.draw(pen)
        master["glyf"][glyph_name] = pen.glyph()
        master["hmtx"][glyph_name] = (master["hmtx"][glyph_name][0], defcon_glyph.bounds[0])
    else:
        master[glyph_name].clear()
        defcon_glyph.draw(master[glyph_name].getPen())

def flip(master, glyph_name, defcon_glyph, go=[]):
    if isinstance(master, TTFont):
        width_half = master["hmtx"][glyph_name][0] / 2
    else:
        width_half = master[glyph_name].width / 2
    for contour in defcon_glyph:
        for point in contour:
            point.x = width_half + (width_half - point.x)
    draw(master, glyph_name, defcon_glyph, go=go)

def align(master, glyph_name, defcon_glyph, go=[]):
    for contour in defcon_glyph:
        for point in contour:
            point.x = 0
    draw(master, glyph_name, defcon_glyph, go=go)

def process_fonts(glyph_names, masters={}, depth=160):
    for glyph_name in glyph_names:
        glyph = Glyph()
        pen = glyph.getPen()
        if isinstance(masters["master_0"], TTFont):
            masters["master_0"]["glyf"][glyph_name].draw(pen, masters["master_0"]["glyf"])
            glyph.width = masters["master_0"]["hmtx"][glyph_name][0]
        else:
            masters["master_0"][glyph_name].draw(pen)

        if len(glyph) > 0:
            corrected_glyph = deepcopy(glyph)
            curveConverter.quadratic2bezier(corrected_glyph)
            try:
                corrected_glyph.correctContourDirection(segmentLength=10)
            except TypeError:
                pass
            directions = [a.clockwise == b.clockwise for a,b in zip(glyph, corrected_glyph)]
            if not all(directions):
                for index, change in enumerate(directions): 
                    if not change:
                        glyph[index].reverse()

            processed_glyph = process_glyph(deepcopy(glyph), False, depth=depth)
            processed_glyph_side = process_glyph(deepcopy(glyph), True, depth=depth)

            draw(masters["master_0"], glyph_name, processed_glyph, go=glyph_names)
            draw(masters["master_90"], glyph_name, processed_glyph_side, go=glyph_names)
            flip(masters["master_90_flipped"], glyph_name, processed_glyph_side, go=glyph_names)
            align(masters["master_90_flipped_left"], glyph_name, processed_glyph_side, go=glyph_names)
            flip(masters["master_0_flipped"], glyph_name, processed_glyph, go=glyph_names)
            align(masters["master_90_flipped_right"], glyph_name, processed_glyph_side, go=glyph_names)

            for master_name in ("master_90", "master_90_flipped", "master_90_flipped_left"):
                master = masters[master_name]
                if isinstance(master, TTFont):
                    width, lsb = master["hmtx"][glyph_name]
                    master["hmtx"][glyph_name] = (width, width/2-depth/2)
                else:
                    width = master[glyph_name].width
                    master[glyph_name].leftMargin = width/2-depth/2
                    master[glyph_name].width = width
            
            for master_name in ("master_90_flipped_right",):
                master = masters[master_name]
                if isinstance(master, TTFont):
                    width, lsb = master["hmtx"][glyph_name]
                    master["hmtx"][glyph_name] = (width, width/2+depth/2)
                else:
                    width = master[glyph_name].width
                    master[glyph_name].leftMargin = width/2+depth/2
                    master[glyph_name].width = width


def make_designspace(fonts):
    axes = {"rotation": [0, 90, 90.0001, 180, 270, 270.0001, 360]}
    doc = DesignSpaceDocument()
    axis = AxisDescriptor()
    axis.minimum = 0
    axis.maximum = 360
    axis.default = 0
    axis.name = "rotation"
    axis.tag = "RTTX"
    doc.addAxis(axis)
    for i, font in enumerate(fonts):
        source = SourceDescriptor()
        source.font = font
        if i == 0:
            source.copyLib = True
            source.copyInfo = True
            source.copyFeatures = True
        source.location = {"rotation": axes["rotation"][i]}
        doc.addSource(source)
    return doc


def createCmap(preview_string_glyph_names, cmap_reversed):
    outtables = []
    subtable = CmapSubtable.newSubtable(4)
    subtable.platformID = 0
    subtable.platEncID = 3
    subtable.language = 0
    subtable.cmap = {cmap_reversed[glyph_name]:glyph_name for glyph_name in preview_string_glyph_names}
    outtables.append(subtable)
    return outtables

def extractGlyf(source, glyph_name):
    return source["glyf"][glyph_name]

def extractCff(source, glyph_name, glyph_order):
    cff = source["CFF "]
    content = cff.cff[cff.cff.keys()[0]]
    glyph = content.CharStrings[glyph_name]
    output_pen = TTGlyphPen([])
    cu2quPen = Cu2QuPen(other_pen=output_pen, max_err=2)
    glyph.draw(cu2quPen)
    try:
        cu2quPen.endPath()
    except:
        pass
    return output_pen.glyph()

def extractCff2(source, glyph_name, glyph_order):
    cff2 = source["CFF2"]
    content = cff2.cff[cff2.cff.keys()[0]]
    glyph = content.CharStrings[glyph_name]
    output_pen = TTGlyphPen([])
    cu2quPen = Cu2QuPen(other_pen=output_pen, max_err=2)
    glyph.draw(cu2quPen)
    cu2quPen.endPath()
    return output_pen.glyph()

def rotorize(ufo=None, tt_font=None, depth=360, glyph_names_to_process=[], cmap_reversed={}):
    processing_ufo = False
    if tt_font:
        if not isinstance(depth, int):
            depth = int(float(depth))
        
        source = tt_font
        output = TTFont(base/"template.ttf")
        glyph_order = tt_font.getGlyphOrder()
        is_ttf = False
        is_cff = False
        is_cff2 = False
        if "glyf" in source:
            is_ttf = True
        elif "CFF " in source:
            is_cff = True
        elif "CFF2" in source:
            is_cff2 = True
        for glyph_name in glyph_names_to_process:
            if is_ttf:
                glyph = extractGlyf(source, glyph_name)
            elif is_cff2:
                glyph = extractCff2(source, glyph_name, glyph_order)
            elif is_cff:
                glyph = extractCff(source, glyph_name, glyph_order)
            output["glyf"][glyph_name] = glyph
            output["hmtx"][glyph_name] = source["hmtx"][glyph_name]
        output["cmap"].tables = createCmap(glyph_names_to_process, cmap_reversed)
        output["name"] = source["name"]
        output["hhea"] = source["hhea"]
        output["head"] = source["head"]
        master_0 = output
    else:
        glyph_names_to_process=[glyph.name for glyph in ufo]
        processing_ufo = True
        master_0 = ufo
        
    masters = dict(
        master_0=master_0,
        master_90=deepcopy(master_0),
        master_90_flipped=deepcopy(master_0),
        master_0_flipped=deepcopy(master_0),
        master_90_flipped_left=deepcopy(master_0),
        master_90_flipped_right=deepcopy(master_0)
        )
    process_fonts(glyph_names_to_process, masters, depth=depth)
    designspace_underlay = make_designspace((
        masters["master_0"],
        masters["master_90"],
        masters["master_90_flipped"],
        masters["master_0_flipped"],
        masters["master_90_flipped"],
        masters["master_90"],
        masters["master_0"],
        ))
    designspace_overlay = make_designspace((
        masters["master_0"],
        masters["master_90_flipped_right"],
        masters["master_90_flipped_left"],
        masters["master_0_flipped"],
        masters["master_90_flipped_right"],
        masters["master_90_flipped_left"],
        masters["master_0"],
        ))
    if processing_ufo:
        return (compileVariableTTF(designspace_underlay), compileVariableTTF(designspace_overlay))
    else:
        return (varLib.build(designspace_underlay, optimize=False)[0], varLib.build(designspace_overlay, optimize=False)[0])

if __name__ == "__main__":

    start = datetime.now()

    # source = TTFont("test_fonts/sourceSerif.otf")
    # source = TTFont("test_fonts/gabion.otf")
    source = TTFont("test_fonts/VTT.ttf")

    preview_string = "rotor"    
    fonts = rotorize(source, depth=360)

    for i, font in enumerate(fonts):
        font.save(f"output-{i}.ttf")
    end = datetime.now()
    print((end-start).total_seconds())