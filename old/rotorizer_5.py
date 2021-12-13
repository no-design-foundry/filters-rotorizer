from fontTools import varLib
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.designspaceLib import DesignSpaceDocument, AxisDescriptor, SourceDescriptor
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.pointPen import PointToSegmentPen

from defcon import Glyph, Point, Font

import ufo2ft

from datetime import datetime
from pathlib import Path
from tools.curveTools import curveConverter
from copy import deepcopy
from pathlib import Path

base = Path(__file__).parent


@property
def position(self):
    return self.x, self.y

setattr(Point, "position", position)

def process_glyph(glyph, draw_sides, absolute=False, depth=160):
    drawings = []
    first_clockwise = glyph[0].clockwise
    contours = [contour for contour in glyph]
    pen = glyph.getPointPen()
    for contour in contours:
        glyph.removeContour(contour)
    for contour in contours:
        pen.beginPath()
        lowest_point = min(zip(contour.segments, range(len(contour.segments))),key=lambda x: x[0][-1].position[::-1],)[1]
        contour_reordered = (contour.segments[lowest_point:] + contour.segments[:lowest_point])
        values = [a[-1].y > b[-1].y for a, b in zip(contour_reordered, contour_reordered[1:] + contour_reordered[:1])
        ]
        if values[0] == values[-1]:
            index = values[::-1].index(not values[0])
            contour_reordered = contour_reordered[-index:] + contour_reordered[:-index]
            values = values[-index:] + values[:-index]
        last_value = values[0]
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
                pen.addPoint((x, y), point.segmentType)
            if duplicate is True:
                x, y = segment[-1].position
                if draw_sides:
                    edges = edges[::-1]
                    x = edges[0]
                pen.addPoint((x, y), "line")
        pen.endPath()
        if contour.clockwise and draw_sides:
            for segment in glyph[-1].segments:
                for point in segment:
                    point.x = edges[(edges.index(point.x) + 1) % 2]
    return glyph

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

def draw(master, defcon_glyph):
    output_glyph = master.newGlyph(defcon_glyph.name)
    defcon_glyph.draw(output_glyph.getPen())

def flip(master, defcon_glyph):
    width_half = defcon_glyph.width/2
    for contour in defcon_glyph:
        for point in contour:
            point.x = width_half + (width_half - point.x)
    draw(master, defcon_glyph)

def align(master, defcon_glyph):
    for contour in defcon_glyph:
        for point in contour:
            point.x = 0
    draw(master, defcon_glyph)

def process_fonts(source, masters={}, depth=160):
    for glyph in source:
        if len(glyph) > 0:
            corrected_glyph = deepcopy(glyph)
            curveConverter.quadratic2bezier(corrected_glyph)
            corrected_glyph.correctContourDirection(segmentLength=10)
            directions = [a.clockwise == b.clockwise for a,b in zip(glyph, corrected_glyph)]
            if not all(directions):
                for index, change in enumerate(directions): 
                    if not change:
                        glyph[index].reverse()

            processed_glyph = process_glyph(deepcopy(glyph), False, depth=depth)
            processed_glyph_side = process_glyph(deepcopy(glyph), True, depth=depth)

            draw(masters["master_0"], processed_glyph)
            draw(masters["master_90"], processed_glyph_side)
            flip(masters["master_90_flipped"], processed_glyph_side)
            align(masters["master_90_flipped_left"], processed_glyph_side)
            flip(masters["master_0_flipped"], processed_glyph)
            align(masters["master_90_flipped_right"], processed_glyph_side)
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


def createCmap(preview_string_glyph_names, preview_string_unicodes):
    outtables = []
    subtable = CmapSubtable.newSubtable(4)
    subtable.platformID = 0
    subtable.platEncID = 3
    subtable.language = 0
    subtable.cmap = {k:v for v,k in zip(preview_string_glyph_names, preview_string_unicodes)}
    outtables.append(subtable)
    return outtables


def rotorize(ufo=None, tt_font=None, depth=360):
    if not isinstance(depth, int):
        depth = int(float(depth))

    master_0 = ufo
    masters = dict(
        master_0=master_0,
        master_90=Font(),
        master_90_flipped=Font(),
        master_0_flipped=Font(),
        master_90_flipped_left=Font(),
        master_90_flipped_right=Font()
        )
    process_fonts(ufo, masters, depth=depth)
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
    return ufo2ft.compileVariableTTF(designspace_underlay, optimizeGvar=False), ufo2ft.compileVariableTTF(designspace_overlay, optimizeGvar=False)

if __name__ == "__main__":

    start = datetime.now()
    source = Font("test_fonts/VTT.ufo")

    preview_string = "rotor"    
    fonts = rotorize(ufo=source, depth=360)
    for i, font in enumerate(fonts):
        font.save(f"output-{i}.ttf")
    end = datetime.now()
    print((end-start).total_seconds())