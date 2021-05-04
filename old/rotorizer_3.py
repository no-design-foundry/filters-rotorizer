import operator
from itertools import zip_longest
from fontParts.world import OpenFont
from defcon.objects.point import Point
    
draw_side = True
visualize = False

if visualize:
    source = CurrentGlyph().getLayer('background')
    dest = CurrentGlyph().getLayer('foreground')
    dest.clear()
    translate(170, 100)
    fontSize(40)
    font("Helvetica-Bold")
    bez = BezierPath()
    source.draw(bez)
    drawPath(bez)
    fill(0.5)

@property
def position(self):
    return self.x, self.y

setattr(Point, "position", position)

def process_glyph(glyph):
    for contour in glyph:
        lowest_point = sorted(zip(contour.segments, range(len(contour.segments))), key = lambda x:x[0][-1].position[::-1])
        index = lowest_point[0][1]
        segments = contour.segments[index:] + contour.segments[:index]
        last_value = segments[0][-1].y > segments[1][-1].y
        last_y = segments[-1][-1].y
        color = 0
        drawing = glyph.contourClass()
        absolute_x = 0
        
        #reorder before starting
        
        for i, (segment, segment_next) in enumerate(zip(segments[1:]+segments[:1], segments[2:]+segments[:2])):
            duplicate = False
            shift = False
            value = segment[-1].y < segment_next[-1].y
            print(value)
            if segment[-1].y == segment_next[-1].y:
                shift = True
            elif segment[-1].y == last_y:
                pass
            elif value != last_value:
                duplicate = True
            last_value = value
            last_y = segment[-1].y
            for point in segment:
                x, y = point.position
                if draw_side:
                    x = absolute_x + 150
                point = Point((x, y), segmentType=point.segmentType)
                drawing.appendPoint(point)
            else:
                if duplicate or shift:
                    absolute_x = (absolute_x + 300)%600
                    if draw_side:
                        x = absolute_x + 150
                    point = Point((x, y), segmentType=point.segmentType)
                    drawing.appendPoint(point) 
        yield drawing
        break

def process_font(ufo):
    for glyph in ufo:
        if glyph.name in 'a':
            contours = [i for i in process_glyph(glyph)]
            glyph.clear()
            for contour in contours:
                glyph.appendContour(contour)
            


# glyph = CurrentGlyph()
# drawing = process_glyph(glyph.getLayer("background"))
# glyph.getLayer("foreground").clear()
# for contour in drawing:
#     glyph.getLayer("foreground").appendContour(contour)
# glyph.getLayer("foreground").update()
# if __name__ == "__main__":

import extractor
import defcon
from pathlib import Path


base = Path(__file__).parent
ufo = defcon.Font()
extractor.extractUFO(base/"font.otf", ufo)
process_font(ufo)
ufo.save('output.ufo')
    