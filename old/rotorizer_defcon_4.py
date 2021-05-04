import operator
from itertools import zip_longest
from fontParts.world import OpenFont
from defcon.objects.point import Point
# from defcon.objects.segment import Segment

    
draw_side = True
visualize = True

if visualize:
    source = CurrentGlyph().getLayer('background')
    dest = CurrentGlyph().getLayer('foreground')
    dest.clear()
    fontSize(40)
    translate(170, 100)

    font("Helvetica-Bold")
    bez = BezierPath()
    source.draw(bez)
    drawPath(bez)
    fill(0.5)

@property
def position(self):
    return self.x, self.y

setattr(Point, "position", position)
setattr(Point, "type", Point.segmentType)

def process_glyph(glyph):
    drawings = []
    for contour in glyph:
        lowest_point = sorted(zip(contour.segments, range(len(contour.segments))), key = lambda x:x[0][-1].position[::-1])
        index = lowest_point[0][1]
        segments = contour.segments[index:] + contour.segments[:index]
        last_value = segments[0][-1].y > segments[1][-1].y
        last_y = segments[-1][-1].y
        color = 0
        drawing = glyph.contourClass()
        absolute_x = 0
        for i, (segment, segment_next) in enumerate(zip(segments, segments[1:]+[segments[0]])):
            value = segment[-1].y >= segment_next[-1].y
            y = segment[-1].y
            if last_y == y:
                pass
            
            elif value != last_value:
                oval(*[i-20 for i in segment[-1].position], 40, 40)
                last_value = value
            last_y = y     
    return drawings

def process_font(ufo):
    for glyph in ufo:
        if glyph.name in 'abcdef':
            drawing = process_glyph(glyph)
            glyph.clear()
            for contour in drawing:
                print(contour)
                glyph.appendContour(contour)
        return
        
process_glyph(CurrentGlyph().getLayer("background"))



    