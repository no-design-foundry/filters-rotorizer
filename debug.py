from pathlib import Path
from fontTools.ttLib.ttFont import TTFont

base = Path(__file__).parent
ttFont = TTFont(base.parent.parent.parent/"verdana.ttf")
print(ttFont["cmap"].tables[1].cmap)
