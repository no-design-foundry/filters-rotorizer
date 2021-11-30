from defcon import Glyph
from fontTools.ttLib.tables._g_l_y_f import Glyph as FTGlyph
from fontTools.ttLib.ttFont import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from pathlib import Path
from copy import deepcopy
from fontTools import varLib
from fontTools.designspaceLib import DesignSpaceDocument, AxisDescriptor, SourceDescriptor

base = Path(__file__).parent

def process_fonts(source, masters={}, depth=160, tt_font_cubic=None, cmap={}):
    for glyph_name in cmap.keys():
        glyph = source["glyf"][glyph_name]
        if glyph.numberOfContours > 0:
            corrected_glyph = deepcopy(glyph)
            processed_glyph = glyph
            processed_glyph_side = glyph
            # processed_glyph = process_glyph(glyph, False, depth=depth)
            # processed_glyph_side = process_glyph(glyph, True, depth=depth)
            draw(processed_glyph, masters["master_0"][glyph.name])
            draw(processed_glyph_side, masters["master_90"][glyph.name])
            flip(processed_glyph_side, masters["master_90_flipped"][glyph.name])
            align(processed_glyph_side, masters["master_90_flipped_left"][glyph.name])
            flip(processed_glyph, masters["master_0_flipped"][glyph.name])
            align(processed_glyph_side, masters["master_90_flipped_right"][glyph.name])

def process_glyph(glyph, draw_sides=False, absolute=False, depth=160):
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
    output_glyph.width = gl

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

def rotorize(source, glyphs, depth=360):
    for glyph in glyphs:
        process_glyph(glyph)
    # process_glyphs(glyphs)
    # process_fonts(source, masters, depth=depth, cmap=cmap)
    # designspace_underlay = make_designspace((
    #     None,
    #     None,
    #     None,
    #     None,
    #     None,
    #     None,
    #     None,
    #     ))
    quit()
    # return (varLib.build(designspace_underlay, optimize=False)[0], varLib.build(designspace_overlay, optimize=False)[0])

def createCmap(preview_string_glyph_names, preview_string_unicodes):
    outtables = []
    subtable = CmapSubtable.newSubtable(4)
    subtable.platformID = 0
    subtable.platEncID = 3
    subtable.language = 0
    subtable.cmap = {k:v for v,k in zip(preview_string_glyph_names, preview_string_unicodes)}
    outtables.append(subtable)
    return outtables

def extractCff(source, glyph_name, glyph_order):
    cff2 = source["CFF "]
    content = cff.cff[cff.cff.keys()[0]]
    glyph = content.CharStrings[glyph_name]
    output_pen = TTGlyphPen([])
    cu2quPen = Cu2QuPen(other_pen=output_pen, max_err=2)
    glyph.draw(cu2quPen)
    cu2quPen.endPath()
    return output_pen.glyph()

class ExtractingPen():
    def __init__(self):
        self.instructions = []

    def moveTo(self, point):
        self.instructions.append((point, "move"))

    def lineTo(self, point):
        self.instructions.append((point, "line"))

    def qCurveTo(self, points):
        self.instructions.append((points, "qCurveTo"))

    def closePath(self):
        pass


def extractCff2(source, glyph_name, glyph_order):
    cff2 = source["CFF2"]
    content = cff2.cff[cff2.cff.keys()[0]]
    glyph = content.CharStrings[glyph_name]
    output_pen = TTGlyphPen([])
    cu2quPen = Cu2QuPen(other_pen=output_pen, max_err=2)
    glyph.draw(cu2quPen)
    cu2quPen.endPath()
    return output_pen.glyph()

def extractGlyf(source, glyph_name):
    glyph = source["glyf"][glyph_name]
    extracting_pen = ExtractingPen()
    glyph.draw(extracting_pen, source)
    return extracting_pen.instructions

def extractHmtx(source, glyph_name):
    return source["hmtx"][glyph_name]

def extractUnicode():
    return reversed_mapping.get(glyph_name, [])

source = TTFont("fe/public/verdana.ttf")
# source = TTFont("fe/public/sourceSerif.otf")
output = TTFont(base/"template.ttf")
from datetime import datetime

preview_string = "ABCDEF"
preview_string_unicodes = [ord(char) for char in preview_string]

cmap = {k:v for k,v in source.getBestCmap().items() if k in preview_string_unicodes}
reversed_mapping = {v:(k,) for k,v in cmap.items()}
glyph_order = reversed_mapping.keys()

preview_string_glyph_names = [cmap[unicode_] for unicode_ in preview_string_unicodes]

is_ttf = False
is_cff = False
is_cff2 = False
if "glyf" in source:
    is_ttf = True
elif "CFF " in source:
    is_cff = True
elif "CFF2" in source:
    is_cff2 = True


start = datetime.now()
glyphs = []
for unicode_ in preview_string_unicodes:
    glyph_name = cmap[unicode_]
    if is_ttf:
        glyph = extractGlyf(source, glyph_name)
    elif is_cff2:
        glyph = extractCff2(source, glyph_name, glyph_order)
    elif is_cff:
        glyph = extractCff(source, glyph_name, glyph_order)
    glyphs.append(glyph)
    print(glyph)
    output["hmtx"][glyph_name] = source["hmtx"][glyph_name]
# output["cmap"].tables = createCmap(preview_string_glyph_names, preview_string_unicodes)
# output["name"] = source["name"]
# output["hhea"] = source["hhea"]
# output["head"] = source["head"]


# fonts = rotorize(output, glyphs)

# for i, font in enumerate(fonts):
#     font.save(f"cmap-{i}.ttf")
# # output.save("cmap.ttf")

# end = datetime.now()




# print((end - start).total_seconds())