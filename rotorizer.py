from defcon.objects.point import Point
from defcon.objects.glyph import Glyph
from defcon.objects.base import BaseObject
from defcon import Font
from ufo2ft import compileVariableTTF, compileOTF
from fontTools.designspaceLib import (
    DesignSpaceDocument,
    SourceDescriptor,
    AxisDescriptor,
)
from datetime import datetime
from copy import deepcopy, copy 

@property
def position(self):
    return self.x, self.y

setattr(Point, "position", position)
setattr(Point, "type", Point.segmentType)

def font__deepcopy__(self, settings):
    clean = self.__class__()
    clean._layers.defaultLayer = deepcopy(self._layers.defaultLayer)
    clean.kerning.update(self.kerning)
    clean.info.deserialize(self.info.serialize())
    clean.features.text = self.features.text
    return clean

Font.__deepcopy__ = font__deepcopy__

def process_glyph(glyph, draw_sides, absolute=False, width=160):
    drawings = []
    first_clockwise = glyph[0].clockwise
    for contour in glyph:
        lowest_point = min(
            zip(contour.segments, range(len(contour.segments))),
            key=lambda x: x[0][-1].position[::-1],
        )[1]
        contour_reordered = (
            contour.segments[lowest_point:] + contour.segments[:lowest_point]
        )
        values = [
            a[-1].y > b[-1].y
            for a, b in zip(
                contour_reordered, contour_reordered[1:] + contour_reordered[:1]
            )
        ]
        if values[0] == values[-1]:
            index = values[::-1].index(not values[0])
            contour_reordered = contour_reordered[-index:] + contour_reordered[:-index]
            values = values[-index:] + values[:-index]
        last_value = values[0]
        drawing = contour.__class__()
        edges = [glyph.width / 2 + width/2, glyph.width / 2 - width/2]
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
    return drawings

import concurrent

def process_font(ufo, draw_sides, absolute=False, width=160):
    font = deepcopy(ufo)
    for glyph in font:
        if len(glyph):
            drawing = [i for i in process_glyph(glyph, draw_sides, absolute=absolute, width=width)]
            for contour in [contour for contour in glyph]:
                glyph.removeContour(contour)
            for contour in drawing:
                glyph.appendContour(contour)
            glyph.width = glyph.width
            glyph.unicode = glyph.unicode
    return font


def flip(ufo):
    ufo = deepcopy(ufo)
    for glyph in ufo:
        width_half = glyph.width/2
        for contour in glyph:
            for point in contour:
                point.x = width_half+(width_half-point.x)
    return ufo
    

def align(font, value):
    font = deepcopy(font)
    for glyph in font:
        width_half = glyph.width/2
        for contour in glyph:
            for point in contour:
                point.x = width_half+value
    return font

def make_designspace():
    axes = {
        "rotation": [0, 90, 90.0001, 180, 270, 270.0001, 360]
    }
    doc = DesignSpaceDocument()
    
    axis = AxisDescriptor()
    axis.minimum = 0
    axis.maximum = 360
    axis.default = 0
    axis.name = "rotation"
    axis.tag = "RTTX"

    doc.addAxis(axis)
    for i, font in enumerate([None]*len(axes["rotation"])):
        source = SourceDescriptor()
        source.font = font
        if i == 0:
            source.copyLib = True
            source.copyInfo = True
            source.copyFeatures = True
        source.location = {"rotation":axes["rotation"][i]}
        doc.addSource(source)
    return doc

designspace_template = make_designspace()

def designspace(fonts):
    designspace_copy = deepcopy(designspace_template)
    for source, font in zip(designspace_copy.sources, fonts):
        source.font =  font
    return designspace_copy


def rotorize(ufo=None, width=80, **kwargs):
    designspaces = []
    if isinstance(width, str):
        width = round(float(width))
    for glyph in ufo:
        if len(glyph):
            glyph.correctContourDirection(segmentLength=5)
    
    master_0 = process_font(ufo, False, False, width)
    master_90 = process_font(ufo, True, False, width)
    master_90_flipped = flip(master_90)
    master_0_flipped = flip(master_0)
    master_90_flipped_left = align(master_90_flipped, -width/2)
    master_90_flipped_right = align(master_90_flipped, width/2)
    
    for i in range(2):
        if i == 0:
            fonts = (
                master_0,
                master_90,
                master_90_flipped,
                master_0_flipped,
                master_90_flipped,
                master_90,
                master_0
            )
        elif i == 1:
            fonts = (
                master_0,
                master_90_flipped_right,
                master_90_flipped_left,
                master_0_flipped,
                master_90_flipped_right,
                master_90_flipped_left,
                master_0
            )
        designspaces.append(designspace(fonts))
    return designspaces



    # for glyph in ufo:
    #     if len(glyph):
    #         contours_a = [deepcopy(contour) for contour in glyph]
    #         glyph.correctContourDirection(segmentLength=10)
    #         contours_b = [contour for contour in glyph]
    #         equals = set(a.clockwise == b.clockwise  for a,b in zip(contours_a, contours_b))
    #         if len(equals) == 2:
    #             largest_contour = max(glyph, key=lambda x:x.area)
    #             index = contours_b.index(largest_contour)
    #             operand = ("__eq__", "__ne__")[contours_a[index].clockwise == contours_b[index].clockwise]
    #             for contour_a, contour_b in zip(contours_a, contours_b):
    #                 if getattr(contour_a.clockwise, operand)(contour_b.clockwise):
    #                     contour_b.reverse()