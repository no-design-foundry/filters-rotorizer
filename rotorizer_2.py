import sys

from fontTools import varLib
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph as FTGlyph, table__g_l_y_f
from fontTools.ttLib.tables._m_a_x_p import table__m_a_x_p
from fontTools.ttLib.tables._h_m_t_x import table__h_m_t_x
from fontTools.ttLib.tables._h_e_a_d import table__h_e_a_d
from fontTools.ttLib.tables._c_m_a_p import cmap_format_4
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.t2CharStringPen import T2CharStringPen

from ufo2ft import compileVariableTTF
from fontTools.designspaceLib import DesignSpaceDocument, AxisDescriptor, SourceDescriptor
from defcon.objects.point import Point
# from fontTools.ttLib.tables._g_l_y_f import Glyph
import defcon


# from tools.otf2ttf import otf_to_ttf
from defcon.objects.glyph import Glyph
# from tools.curveTools import curveConverter
from copy import deepcopy
from pathlib import Path
from fontPens.flattenPen import flattenGlyph

base = Path(__file__).parent

def extractGlyph(tt_font, destination, glyph_name, reversed_cmap):
    # grab the cmaptt
    is_ttf = "glyf" in tt_font
    # grab the glyphs
    glyph_set = tt_font.getGlyphSet()
    source_glyph = glyph_set[glyph_name]

    destination["hmtx"][glyph_name] = tt_font["hmtx"][glyph_name]
    destination["glyf"][glyph_name] = source_glyph._glyph

@property
def position(self):
    return self.x, self.y

setattr(Point, "position", position)
setattr(Point, "type", Point.segmentType)

def process_glyph(glyph, draw_sides, absolute=False, depth=160):
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
    output_glyph.unicode = glyph.unicode
    output_glyph.name = glyph.name
    output_glyph.width = glyph.width
    for contour in drawings:
        output_glyph.appendContour(contour)
    return output_glyph

def draw(source_glyph, destination):
    pass
    # destination.copyDataFromGlyph(source_glyph)

def flip(source_glyph, destination):
    width_half = source_glyph.width / 2
    for contour in destination:
        for point in contour:
            point.x = width_half + (width_half - point.x)
    draw(source_glyph, destination)

def align(source_glyph, destination):
    for contour in source_glyph:
        for point in contour:
            point.x = 0
    draw(source_glyph, destination)

# font = Font()

def process_fonts(source, masters={}, depth=160, tt_font_cubic=None, cmap={}):
    print(cmap)
    for glyph_name in cmap.keys():
        glyph = source["glyf"][glyph_name]
        if glyph.numberOfContours > 0:
            corrected_glyph = deepcopy(glyph)
            # curveConverter.quadratic2bezier(corrected_glyph)
            # corrected_glyph.correctContourDirection(segmentLength=10)
            # directions = [a.clockwise == b.clockwise for a,b in zip(glyph, corrected_glyph)]
            # if not all(directions):
            #     for index, change in enumerate(directions): 
            #         if not change:
            #             glyph[index].reverse()

            processed_glyph = process_glyph(glyph, False, depth=depth)
            processed_glyph_side = process_glyph(glyph, True, depth=depth)

            draw(processed_glyph, masters["master_0"][glyph.name])
            draw(processed_glyph_side, masters["master_90"][glyph.name])
            flip(processed_glyph_side, masters["master_90_flipped"][glyph.name])
            align(processed_glyph_side, masters["master_90_flipped_left"][glyph.name])
            flip(processed_glyph, masters["master_0_flipped"][glyph.name])
            align(processed_glyph_side, masters["master_90_flipped_right"][glyph.name])

            # for master_name in ("master_90", "master_90_flipped", "master_90_flipped_left"):
            #     master = masters[master_name]
            #     width, lsb = master["hmtx"][glyph_name]
            #     master["hmtx"][glyph_name] = (width, width/2-depth/2)
            
            # for master_name in ("master_90_flipped_right",):
            #     master = masters[master_name]
            #     width, lsb = master["hmtx"][glyph_name]
            #     master["hmtx"][glyph_name] = (width, width/2+depth/2)


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

    

def rotorize(tt_font=None, depth=360, glyph_names_to_process=[], cmap={}):
    
    master_0 = tt_font
    start = datetime.now()
    masters = dict(
        master_0=master_0,
        master_90=deepcopy(master_0),
        master_90_flipped=deepcopy(master_0),
        master_0_flipped=deepcopy(master_0),
        master_90_flipped_left=deepcopy(master_0),
        master_90_flipped_right=deepcopy(master_0)
        )
    end = datetime.now()
    process_fonts(tt_font, masters, depth=depth, cmap=cmap)
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
    # start = datetime.now()
    # compileVariableTTF(designspace_overlay)
    # compileVariableTTF(designspace_underlay)
    # end = datetime.now()
    # print((end - start).total_seconds())
    # return (varLib.build(designspace_underlay, optimize=False)[0], varLib.build(designspace_overlay, optimize=False)[0])


if __name__ == "__main__":
    # font = TTFont("../server/test_fonts/ADOBE.ttf")
    from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
    from datetime import datetime
    start = datetime.now()
    preview_string = "ABCD"
    preview_string_unicodes = [ord(char) for char in preview_string]
    tt_font = TTFont("fe/public/verdana.ttf")
    template = TTFont(base/"template.ttf")
    glyph_order = [".notdef", *preview_string]
    template["glyf"].setGlyphOrder(glyph_order)
    template.setGlyphOrder(glyph_order)
    
    cmap = {k:v for k,v in tt_font.getBestCmap().items() if k in preview_string_unicodes}
    reversed_cmap = {v:k for k,v in cmap.items()}
    for glyph_name in glyph_order:
        extractGlyph(tt_font, template, glyph_name, reversed_cmap=reversed_cmap)

    # template["cmap"].tables.append(cmap_format_4(format=4))
    outtables = []
    
        # Convert ot format4
    newtable = CmapSubtable.newSubtable(4)
    newtable.platformID = 0
    newtable.platEncID = 3
    newtable.language = 0
    newtable.cmap = {ord(char): char for char in preview_string}
    outtables.append(newtable)
    template["cmap"].tables = outtables
    template["name"] = tt_font["name"]
    template["hhea"] = tt_font["hhea"]
    template["head"] = tt_font["head"]


    fonts = rotorize(tt_font=template, depth=360, cmap=reversed_cmap)
    # template.save("debug.ttf")
    end = datetime.now()
    print((end - start).total_seconds())

    # fonts[1].save("output_over.ttf")
    # font.save("debug.ufo")