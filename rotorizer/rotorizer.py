from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.designspaceLib import DesignSpaceDocument, AxisDescriptor, SourceDescriptor, InstanceDescriptor
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from fontTools.pens.cu2quPen import Cu2QuPen
from ufo2ft import compileVariableTTF
from gc import collect
from defcon import Glyph, Point, Font
from copy import deepcopy
# from ufoLib2.objects.font import Font
# from ufoLib2.objects.glyph import Font
# from ufoLib2.objects.point import Point

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

def process_fonts(ufo, glyph_names, masters={}, depth=160, is_cff=None):
    for glyph_name in glyph_names:
        if len(ufo[glyph_name]) > 0:
            processed_glyph_glyph = Glyph()
            ufo[glyph_name].draw(processed_glyph_glyph.getPen())

            processed_glyph_side = Glyph()
            ufo[glyph_name].draw(processed_glyph_side.getPen())

            processed_glyph = process_glyph(processed_glyph_glyph, False, depth=depth, is_cff=is_cff)
            processed_glyph_side = process_glyph(processed_glyph_side, True, depth=depth, is_cff=is_cff)
            
            if "master_0" in masters:
                draw(masters["master_0"], glyph_name, processed_glyph, go=glyph_names)
            if "master_90" in masters:
                draw(masters["master_90"], glyph_name, processed_glyph_side, go=glyph_names)
            if "master_90_flipped" in masters:
                flip(masters["master_90_flipped"], glyph_name, processed_glyph_side, go=glyph_names)
            if "master_90_flipped_left" in masters:
                align(masters["master_90_flipped_left"], glyph_name, processed_glyph_side, go=glyph_names)
            if "master_0_flipped" in masters:
                flip(masters["master_0_flipped"], glyph_name, processed_glyph, go=glyph_names)
            if "master_90_flipped_right" in masters:
                align(masters["master_90_flipped_right"], glyph_name, processed_glyph_side, go=glyph_names)

            for master_name in ("master_90", "master_90_flipped", "master_90_flipped_left"):
                if master_name in masters:
                    master = masters[master_name]
                    width = master[glyph_name].width
                    master[glyph_name].leftMargin = width/2-depth/2
                    master[glyph_name].width = width
        
            for master_name in ("master_90_flipped_right",):
                if master_name in masters:
                    master = masters[master_name]
                    width = master[glyph_name].width
                    master[glyph_name].leftMargin = width/2+depth/2
                    master[glyph_name].width = width
    collect()


def make_designspace(fonts, depth_fonts, family_name):
    axes = {"rotation": [0, 90, 90.0001, 180, 270, 270.0001, 360]}
    doc = DesignSpaceDocument()

    axis = AxisDescriptor()
    axis.minimum = 0
    axis.maximum = 360
    axis.default = 0
    axis.name = "Rotation"
    axis.tag = "RTTX"
    doc.addAxis(axis)

    axis = AxisDescriptor()
    axis.minimum = 0
    axis.maximum = 100
    axis.default = 0
    axis.name = "Depth"
    axis.tag = "DPTH"
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
        source.location = {"Rotation": axes["rotation"][i], "Depth": 0}
        doc.addSource(source)
    
    for i, font in enumerate(depth_fonts):
        source = SourceDescriptor()
        source.font = font
        source.location = {"Rotation": axes["rotation"][i], "Depth": 100}
        doc.addSource(source)

    for i, instance_position in enumerate([0, 45, 90, 135, 180, 225, 270, 315]):
        instance = InstanceDescriptor()
        instance.designLocation = {"Rotation":instance_position}
        instance.styleName = f"Rotation {instance_position}"
        doc.addInstance(instance)
    return doc

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
def rotorize(ufo=None, glyph_names_to_process=None, is_cff=None):

    masters_0 = Font()
    for value in ["xHeight", "unitsPerEm", "ascender", "descender", "capHeight"]:
        setattr(masters_0.info, value, getattr(ufo.info, value))

    masters_90 = Font()
    masters_90_flipped = Font()
    masters_0_flipped = Font()
    masters_90_flipped_left = Font()
    masters_90_flipped_right = Font()

    masters_90_depth = Font()
    masters_90_flipped_depth = Font()
    masters_90_flipped_left_depth = Font()
    masters_90_flipped_right_depth = Font()

    for glyph_name_to_process in glyph_names_to_process:
        glyph = ufo[glyph_name_to_process]
        for master in (
                masters_0,
                masters_90,
                masters_90_flipped,
                masters_0_flipped,
                masters_90_flipped_left,
                masters_90_flipped_right,
                masters_90_depth,
                masters_90_flipped_depth,
                masters_90_flipped_left_depth,
                masters_90_flipped_right_depth,
            ):
            new_glyph = master.newGlyph(glyph.name)
            new_glyph.width = glyph.width
            new_glyph.unicodes = glyph.unicodes
            pen = new_glyph.getPen()
            glyph.draw(pen)

    masters = dict(
        master_0=masters_0,
        master_90=masters_90,
        master_90_flipped=masters_90_flipped,
        master_0_flipped=masters_0_flipped,
        master_90_flipped_left=masters_90_flipped_left,
        master_90_flipped_right=masters_90_flipped_right
        )
    
    depth_masters = dict(
        master_90=masters_90_depth,
        master_90_flipped=masters_90_flipped_depth,
        master_90_flipped_left=masters_90_flipped_left_depth,
        master_90_flipped_right=masters_90_flipped_right_depth
    )

    scale_factor = ufo.info.unitsPerEm/1000
    process_fonts(ufo, glyph_names_to_process, masters, depth=0, is_cff=is_cff)
    process_fonts(ufo, glyph_names_to_process, depth_masters, depth=500*scale_factor, is_cff=is_cff) # this needs to be first as it contains input ufo


    designspace_underlay = make_designspace((
            masters["master_0"],
            masters["master_90"],
            masters["master_90_flipped"],
            masters["master_0_flipped"],
            masters["master_90_flipped"],
            masters["master_90"],
            masters["master_0"],
        ),(
            masters["master_0"],
            depth_masters["master_90"],
            depth_masters["master_90_flipped"],
            masters["master_0_flipped"],
            depth_masters["master_90_flipped"],
            depth_masters["master_90"],
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
        ), (
            masters["master_0"],
            depth_masters["master_90_flipped_right"],
            depth_masters["master_90_flipped_left"],
            masters["master_0_flipped"],
            depth_masters["master_90_flipped_right"],
            depth_masters["master_90_flipped_left"],
            masters["master_0"],
        ), ufo.info.familyName)
    
    
    output = []
    for designspace in (designspace_underlay, designspace_overlay):
        output.append(compileVariableTTF(designspace, optimizeGvar=False))
        del designspace
        collect()
    return output


def main():
    from extractor import extractUFO
    from pathlib import Path
    import argparse

    parser = argparse.ArgumentParser(description="Rotorize ufo")
    parser.add_argument("input_file", type=Path, help="Path to the input font file.")
    parser.add_argument("--output_dir", "-o", type=Path, help="Path to the output file. If not provided, the output will be saved in the same directory as the input file.")
    parser.add_argument("--glyph_names", "-g", type=str, nargs="+", help="List of glyph names to process. If not provided, all glyphs will be processed.")

    args = parser.parse_args()
    
    
    input_file = args.input_file
    ufo = Font(input_file)

    glyph_names_to_process = args.glyph_names if args.glyph_names else ufo.glyphOrder
    output_dir = args.output_dir
    
    rotorized_layers = rotorize(ufo, glyph_names_to_process=glyph_names_to_process, is_cff=True)

    for layer_name, layer in zip(("underlay", "overlay"), rotorized_layers):
        output_file_name = f"{input_file.stem}_rotorized_{layer_name}.ttf"
        layer.save(output_dir/output_file_name if output_dir else input_file.parent/output_file_name)


if __name__ == "__main__":
    main()

