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
from drawBot import *

base = Path(__file__).parent

font = TTFont("fe/public/verdana.ttf")

glyph = font["glyf"]["A"]

class RotorizingPen:
    def __init__(self, other_pen):
        self.other_pen = other_pen
        self.last_y = None
    
    def moveTo(self, point):
        self.last_y = point[1]
        self.other_pen.moveTo(point)
    
    def lineTo(self, point):
        x, y = point
        if y > self.last_y:
            print("going up")
        else:
            print("going down")
        self.last_y = y
        self.other_pen.lineTo(point)

    def closePath(self):
        self.other_pen.closePath()



newDrawing()
size(2000, 2000)
bez = BezierPath()
rotorizing_pen = RotorizingPen(bez)
glyph.draw(rotorizing_pen, font)
drawPath(bez)

saveImage("output.png")

endDrawing()
