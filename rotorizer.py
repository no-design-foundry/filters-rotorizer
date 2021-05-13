import sys

from fontTools import varLib
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph as FTGlyph
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.designspaceLib import DesignSpaceDocument, AxisDescriptor, SourceDescriptor
from defcon.objects.point import Point
from defcon.objects.font import Font

sys.path.append("..")
from server.tools.otf2ttf import otf_to_ttf
from defcon.objects.glyph import Glyph
from server.tools.curveTools import curveConverter
from copy import deepcopy
from pathlib import Path
from fontPens.flattenPen import flattenGlyph

@property
def position(self):
    return self.x, self.y

setattr(Point, "position", position)
setattr(Point, "type", Point.segmentType)

def process_glyph(glyph, draw_sides, absolute=False, depth=160, go=[]):
    drawings = []
    first_clockwise = glyph[0].clockwise
    for contour in glyph:
        lowest_point = min(zip(contour.segments, range(len(contour.segments))),key=lambda x: x[0][-1].position[::-1],)[1]
        contour_reordered = (contour.segments[lowest_point:] + contour.segments[:lowest_point])
        values = [a[-1].y > b[-1].y for a, b in zip(contour_reordered, contour_reordered[1:] + contour_reordered[:1])
        ]
        if values[0] == values[-1]:
            index = values[::-1].index(not values[0])
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
                drawing.appendPoint(Point((x, y), point.type))
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
    for contour in drawings:
        output_glyph.appendContour(contour)
    return output_glyph

def draw(master, glyph_name, defcon_glyph, go=[]):
    pen = TTGlyphPen(go)
    defcon_glyph.draw(pen)
    master["glyf"][glyph_name] = pen.glyph()
    master["hmtx"][glyph_name] = (master["hmtx"][glyph_name][0], defcon_glyph.bounds[0])

def flip(master, glyph_name, defcon_glyph, go=[]):
    width_half = master["hmtx"][glyph_name][0] / 2

    for contour in defcon_glyph:
        for point in contour:
            point.x = width_half + (width_half - point.x)
    draw(master, glyph_name, defcon_glyph, go=go)

def align(master, glyph_name, defcon_glyph, go=[]):
    for contour in defcon_glyph:
        for point in contour:
            point.x = 0
    draw(master, glyph_name, defcon_glyph, go=go)

font = Font()

def process_fonts(glyph_names, masters={}, depth=160, tt_font_cubic=None):
    for glyph_name in glyph_names:
        glyph = Glyph()
        pen = glyph.getPen()
        masters["master_0"]["glyf"][glyph_name].draw(pen, masters["master_0"]["glyf"])
        glyph.width = masters["master_0"]["hmtx"][glyph_name][0]

        if masters["master_0"]["glyf"][glyph_name].numberOfContours > 0:
            corrected_glyph = deepcopy(glyph)
            curveConverter.quadratic2bezier(corrected_glyph)
            corrected_glyph.correctContourDirection(segmentLength=10)
            directions = [a.clockwise == b.clockwise for a,b in zip(glyph, corrected_glyph)]
            if not all(directions):
                for index, change in enumerate(directions): 
                    if not change:
                        glyph[index].reverse()

            processed_glyph = process_glyph(glyph, False, go=glyph_names, depth=depth)
            processed_glyph_side = process_glyph(glyph, True, depth=depth)

            draw(masters["master_0"], glyph_name, processed_glyph, go=glyph_names)
            draw(masters["master_90"], glyph_name, processed_glyph_side, go=glyph_names)
            flip(masters["master_90_flipped"], glyph_name, processed_glyph_side, go=glyph_names)
            align(masters["master_90_flipped_left"], glyph_name, processed_glyph_side, go=glyph_names)
            flip(masters["master_0_flipped"], glyph_name, processed_glyph, go=glyph_names)
            align(masters["master_90_flipped_right"], glyph_name, processed_glyph_side, go=glyph_names)

            for master_name in ("master_90", "master_90_flipped", "master_90_flipped_left"):
                master = masters[master_name]
                width, lsb = master["hmtx"][glyph_name]
                master["hmtx"][glyph_name] = (width, width/2-depth/2)
            
            for master_name in ("master_90_flipped_right",):
                master = masters[master_name]
                width, lsb = master["hmtx"][glyph_name]
                master["hmtx"][glyph_name] = (width, width/2+depth/2)


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

def rotorize(tt_font=None, depth=360, **kwargs):
    if not isinstance(depth, int):
        depth = int(float(depth))

    master_0 = tt_font
    glyph_names = master_0.getGlyphOrder()
    
    remove_tables = ("TSI0", "TSI1", "TSI2", "TSI3", "TSI4", "TSI5", "gvar", "stat", "fvar", "hvar")
    tables = master_0.keys()
    for table_name in remove_tables:
        if table_name in tables:
            del master_0[table_name]

    tt_font_cubic = None
    if "glyf" not in tt_font:
        tt_font_cubic = deepcopy(tt_font)
        otf_to_ttf(tt_font)
        
    masters = dict(
        master_0=master_0,
        master_90=deepcopy(master_0),
        master_90_flipped=deepcopy(master_0),
        master_0_flipped=deepcopy(master_0),
        master_90_flipped_left=deepcopy(master_0),
        master_90_flipped_right=deepcopy(master_0)
        )
    process_fonts(glyph_names, masters, depth=depth, tt_font_cubic=tt_font_cubic)
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
    return (varLib.build(designspace_underlay, optimize=False)[0], varLib.build(designspace_overlay, optimize=False)[0])


if __name__ == "__main__":
    from fontTools.subset import Subsetter
    # font = TTFont("../server/test_fonts/ADOBE.ttf")
    font = TTFont("../server/test_fonts/OTF.otf")
    subsetter = Subsetter()
    subsetter.populate(glyphs=["dotlessj", "j", "dotaccent"])
    subsetter.subset(font)
    fonts = rotorize(font, depth=360)
    fonts[1].save("output_over.ttf")
    font.save("debug.ufo")