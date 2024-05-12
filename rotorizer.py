from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.designspaceLib import DesignSpaceDocument, AxisDescriptor, SourceDescriptor, InstanceDescriptor
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from fontTools.pens.cu2quPen import Cu2QuPen

from defcon import Glyph, Point, Font

from datetime import datetime
from pathlib import Path
from pathlib import Path
from ufo2ft import compileVariableTTF
from gc import collect


@property
def position(self):
    return self.x, self.y

setattr(Point, "position", position)

def process_glyph(glyph, draw_sides, absolute=False, depth=160, is_cff=None):
    drawings = []
    for contour in glyph:
        lowest_point = min(zip(contour.segments, range(len(contour.segments))),key=lambda x: x[0][-1].position[::-1],)[1]
        contour_reordered = (contour.segments[lowest_point:] + contour.segments[:lowest_point])
        values = [a[-1].y > b[-1].y for a, b in zip(contour_reordered, contour_reordered[1:] + contour_reordered[:1])
        ]
        if values[0] == values[-1]:
            try:
                index = values[::-1].index(not values[0])
                contour_reordered = contour_reordered[-index:] + contour_reordered[:-index]
                values = values[-index:] + values[:-index]
            except ValueError as e:
                print(e)
                contour_reordered = contour_reordered[::-1]
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
            segment = contour_reordered[index % len(values)]
            if value != last_value:
                duplicate = True
                last_value = value
            for point in segment:
                x, y = point.position
                if draw_sides:
                    x = edges[0 if is_cff else 1]
                drawing.appendPoint(Point((x, y), point.segmentType))
            if duplicate is True:
                x, y = segment[-1].position
                if draw_sides:
                    edges = edges[::-1]
                    x = edges[0 if is_cff else 1]
                drawing.appendPoint(Point((x, y), "line"))
        if contour.clockwise and draw_sides:
            for segment in drawing.segments:
                for point in segment:
                    point.x = edges[(edges.index(point.x) + 1) % 2]
        drawings.append(drawing)
    output_glyph = Glyph()
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

def process_fonts(glyph_names, masters={}, depth=160, is_cff=None):
    for glyph_name in glyph_names:
        glyph = Glyph()
        pen = glyph.getPen()
        if isinstance(masters["master_0"], TTFont):
            masters["master_0"]["glyf"][glyph_name].draw(pen, masters["master_0"]["glyf"])
            glyph.width = masters["master_0"]["hmtx"][glyph_name][0]
        else:
            masters["master_0"][glyph_name].draw(pen)

        if len(glyph) > 0:
            processed_glyph_glyph = Glyph()
            glyph.draw(processed_glyph_glyph.getPen())

            processed_glyph_side = Glyph()
            glyph.draw(processed_glyph_side.getPen())

            processed_glyph = process_glyph(processed_glyph_glyph, False, depth=depth, is_cff=is_cff)
            processed_glyph_side = process_glyph(processed_glyph_side, True, depth=depth, is_cff=is_cff)
            draw(masters["master_0"], glyph_name, processed_glyph, go=glyph_names)
            draw(masters["master_90"], glyph_name, processed_glyph_side, go=glyph_names)
            flip(masters["master_90_flipped"], glyph_name, processed_glyph_side, go=glyph_names)
            align(masters["master_90_flipped_left"], glyph_name, processed_glyph_side, go=glyph_names)
            flip(masters["master_0_flipped"], glyph_name, processed_glyph, go=glyph_names)
            align(masters["master_90_flipped_right"], glyph_name, processed_glyph_side, go=glyph_names)

            for master_name in ("master_90", "master_90_flipped", "master_90_flipped_left"):
                master = masters[master_name]
                width = master[glyph_name].width
                master[glyph_name].leftMargin = width/2-depth/2
                master[glyph_name].width = width
        
            for master_name in ("master_90_flipped_right",):
                master = masters[master_name]
                width = master[glyph_name].width
                master[glyph_name].leftMargin = width/2+depth/2
                master[glyph_name].width = width
    collect()


def make_designspace(fonts, family_name):
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
            source.styleName = "Rotation 0"
            source.familyName = family_name
        source.location = {"rotation": axes["rotation"][i]}
        doc.addSource(source)
    for i, instance_position in enumerate([0, 45, 90, 135, 180, 225, 270, 315]):
        instance = InstanceDescriptor()
        instance.designLocation = {"rotation":instance_position}
        instance.styleName = f"Rotation {instance_position}"
        doc.addInstance(instance)
    return doc


def createCmap(preview_string_glyph_names, cmap_reversed):
    outtables = []
    subtable = CmapSubtable.newSubtable(4)
    subtable.platformID = 0
    subtable.platEncID = 3
    subtable.language = 0

    subtable.cmap = {cmap_reversed[glyph_name]:glyph_name for glyph_name in preview_string_glyph_names if cmap_reversed.get(glyph_name)} # if
    outtables.append(subtable)
    return outtables

def extractGlyf(source, glyph_name, output_glyph):
    source["glyf"][glyph_name].draw(output_glyph.getPen(), source["glyf"])

def extractCff(source, glyph_name, output_glyph):
    cff = source["CFF "]
    content = cff.cff[cff.cff.keys()[0]]
    glyph = content.CharStrings[glyph_name]
    output_pen = output_glyph.getPen()
    cu2quPen = Cu2QuPen(other_pen=output_pen, max_err=2)
    glyph.draw(cu2quPen)
    try:
        cu2quPen.endPath()
    except:
        pass

def extractCff2(source, glyph_name, output_glyph):
    cff2 = source["CFF2"]
    content = cff2.cff[cff2.cff.keys()[0]]
    glyph = content.CharStrings[glyph_name]
    output_pen = output_glyph.getPen()
    cu2quPen = Cu2QuPen(other_pen=output_pen, max_err=2)
    glyph.draw(cu2quPen)
    try:
        cu2quPen.endPath()
    except:
        pass
def rotorize(ufo=None, tt_font=None, depth=360, glyph_names_to_process=None, cmap_reversed=None, is_cff=None):
    
    is_ttf = False
    is_cff = False
    is_cff2 = False

    if "glyf" in tt_font:
        is_ttf = True
    elif "CFF " in tt_font:
        is_cff = True
    elif "CFF2" in tt_font:
        is_cff2 = True
    for glyph_name in glyph_names_to_process:
        output_glyph = ufo.newGlyph(glyph_name)
        output_glyph.unicode=cmap_reversed.get(glyph_name, None)
        output_glyph.width = tt_font["hmtx"][glyph_name][0]
        if is_ttf:
            extractGlyf(tt_font, glyph_name, output_glyph)
        elif is_cff:
            extractCff(tt_font, glyph_name, output_glyph)
        elif is_cff2:
            extractCff2(tt_font, glyph_name, output_glyph)

    masters_90 = Font()
    masters_90_flipped = Font()
    masters_0_flipped = Font()
    masters_90_flipped_left = Font()
    masters_90_flipped_right = Font()
    for glyph in ufo:
        for master in (masters_90, masters_90_flipped, masters_0_flipped, masters_90_flipped_left, masters_90_flipped_right):
            new_glyph = master.newGlyph(glyph.name)
            new_glyph.width = glyph.width
            pen = new_glyph.getPen()
            glyph.draw(pen)

    masters = dict(
        master_0=ufo,
        master_90=masters_90,
        master_90_flipped=masters_90_flipped,
        master_0_flipped=masters_0_flipped,
        master_90_flipped_left=masters_90_flipped_left,
        master_90_flipped_right=masters_90_flipped_right
        )
    process_fonts(glyph_names_to_process, masters, depth=depth*(ufo.info.unitsPerEm/1000), is_cff=is_cff)
    designspace_underlay = make_designspace((
        masters["master_0"],
        masters["master_90"],
        masters["master_90_flipped"],
        masters["master_0_flipped"],
        masters["master_90_flipped"],
        masters["master_90"],
        masters["master_0"],
        ), ufo.info.familyName)
    designspace_overlay = make_designspace((
        masters["master_0"],
        masters["master_90_flipped_right"],
        masters["master_90_flipped_left"],
        masters["master_0_flipped"],
        masters["master_90_flipped_right"],
        masters["master_90_flipped_left"],
        masters["master_0"],
        ), ufo.info.familyName)
    
    output = (compileVariableTTF(designspace_underlay, optimizeGvar=False), compileVariableTTF(designspace_overlay, optimizeGvar=False))
    collect()
    return output
    # return (varLib.build(designspace_underlay, optimize=False)[0], varLib.build(designspace_overlay, optimize=False)[0])

if __name__ == "__main__":

    from pathlib import Path
    base = Path(__file__).parent
    for font_file in (base.parent.parent.parent/"be_test/fonts").glob("*"):
        if font_file.suffix in [".otf", ".ttf"]:
            print(font_file.stem)
            start = datetime.now()
            source = TTFont(font_file)
            cmap = source.getBestCmap()
            cmap_reversed = {v:k for k,v in cmap.items()}
            glyph_names_to_process = [cmap.get(ord(glyph_name)) for glyph_name in "ABC"]
            glyph_names_to_process = [glyph_name for glyph_name in glyph_names_to_process if glyph_name]
            fonts = rotorize(ufo=Font(), tt_font=source, cmap_reversed=cmap_reversed, glyph_names_to_process=glyph_names_to_process, depth=360)
            for i, font in enumerate(fonts):
                font.save(f"output/{font_file.stem}-output-{i}.ttf")
                del font
            end = datetime.now()
            print((end-start).total_seconds())
            break
