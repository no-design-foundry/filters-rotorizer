import base64
import defcon
from io import BytesIO
from itertools import chain
from fontTools.ttLib import TTFont
from ufo2ft import compileTTF
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.cffLib import PrivateDict

from extractor.formats.opentype import (
    extractGlyphOrder,
    extractOpenTypeInfo,
    extractOpenTypeKerning,
    extractOpenTypeGlyphs,
    # extractUnicodeVariationSequences,
    # extractInstructions
)

def inject_features(source, destination):
    for table_name in ("GPOS", "GSUB", "GDEF"):
        if table_name in source:
            destination[table_name].table = source[table_name].table
    # go = [glyph_name for glyph_name in source.getGlyphOrder() if glyph_name in destination.getGlyphOrder()]

def get_glyph(char_string):
    glyph = defcon.objects.glyph.Glyph()
    pen = glyph.getPen()
    char_string.draw(pen)
    pen.endPath()
    return glyph

def get_charstring(glyph):
    cff_pen = T2CharStringPen(None, [], CFF2=True)
    glyph.draw(cff_pen)
    cff_pen.endPath()
    private = PrivateDict()
    return cff_pen.getCharString(private=private)

def fonts_to_base64(fonts):
    fonts_ = []
    for font in fonts:
        if isinstance(font, defcon.Font):
            font = compileTTF(font, removeOverlaps=False, flattenComponents=False)
            font.save("debug_2.ttf")
        if isinstance(font, TTFont):
            font_bytes = BytesIO()
            font.save(font_bytes)
            fonts_.append(font_bytes)
    # return fonts_[0]
    return [base64.b64encode(font.getvalue()).decode('ascii') for font in fonts_]

def get_components_in_subsetted_text(tt_font, text):
    if "glyf" in tt_font:
        def get_component_names(glyf, glyph_names, collector=[]):
            components = list(chain(*[glyf[glyph_name].getComponentNames(glyf) for glyph_name in glyph_names]))
            if components:
                collector += components
                return get_component_names(glyf, components, collector)
            else:
                return collector
        glyf = tt_font["glyf"]
        components = []
        cmap = tt_font.getBestCmap()
        keep_glyphs = map(lambda keep_character:cmap.get(ord(keep_character)), text)
        keep_glyphs = filter(lambda glyph_name:False if glyph_name is None else True, keep_glyphs)
        return get_component_names(glyf, list(keep_glyphs))
    else:
        return ()


def extract_to_ufo(tt_font):
    assert isinstance(tt_font, TTFont), "tt_font must be an instance of TTFont"
    ufo = defcon.Font()
    extract_OTF(tt_font, ufo)
    return ufo

def extract_OTF(source, destination):
    # extractUnicodeVariationSequences(source, destination) # don't know what this is
    extractOpenTypeGlyphs(source, destination)