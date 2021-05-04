import operator
from itertools import zip_longest
from fontParts.world import OpenFont
from defcon.objects.point import Point
# from defcon.objects.segment import Segment

    
draw_side = True
visualize = False

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
            duplicate = False
            value = segment[-1].y < segment_next[-1].y
            if segment[-1].y == last_y:
                pass
            elif segment[-1].y == segment_next[-1].y:
                if visualize: 
                    fill(0, 1, 0)
                    rect(*[i - 15 for i in segment[-1].position], 30, 30)
                # duplicate = True
            elif value != last_value:
                if visualize:
                    fill(0)
                    rect(*[i - 15 for i in segment[-1].position], 30, 30)
                duplicate = True
            last_value = value
            last_y = segment[-1].y
            if visualize:
                fill(color)
                stroke(1)
            for point in segment:
                x, y = point.position
                if draw_side:
                    x = absolute_x + 150
                #new_point = Point()
                drawing.appendPoint((x, y), type=point.type)
            else:
                if duplicate:
                    absolute_x = (absolute_x + 300)%600
                    if draw_side:
                        x = absolute_x + 150
                    #new_point = Point()
                    drawing.appendPoint((x, y), type=point.type) 
            if visualize:
                text(str(i), segment[-1].position, align="center")
        drawings.append(drawing)
    return drawings

def process_font(ufo):
    for glyph in ufo:
        if glyph.name in 'abcdef':
            drawing = process_glyph(glyph)
            glyph.clear()
            for contour in drawing:
                print(contour)
                glyph.appendContour(contour)


# contours = process_glyph(CurrentGlyph().getLayer("background"))
# dest = CurrentGlyph().getLayer("foreground")
# for contour in contours:
#     dest.appendContour(contour)

if __name__ == "__main__":
    
    import extractor
    import defcon
    from pathlib import Path
    from fontParts.world import OpenFont
    
    base = Path(__file__).parent
    ufo = defcon.Font()
    extractor.extractUFO(base/"font.otf", ufo)
    ufo = OpenFont(ufo)
    process_font(ufo)
    ufo.save('output.ufo')
    