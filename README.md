# Birkon for Garmin — Hebrew bitmap fonts (GPL)

The Garmin (Connect IQ) version of the **Birkon** watch app draws Hebrew with nikud using bitmap fonts generated
from **Hadasim CLM** by Yoram Gnat ([Culmus project](https://culmus.sourceforge.io/)). Connect IQ cannot shape
Hebrew, so every letter-with-nikud combination used by the app is shaped once with HarfBuzz and stored as one glyph
of a BMFont (`.fnt` + `.png`), one set per screen size.

Hadasim CLM is licensed under the GNU GPL v2 with the font exception, and so are the generated fonts in this
repository. This repository is their corresponding source:

| Path | What |
|---|---|
| `source-fonts/` | Hadasim CLM 0.140, unmodified: `.otf` files as released and their FontForge sources (`.sfd`) |
| `tools/fontgen.py` | shapes and rasterizes the glyphs, packs the BMFont atlas |
| `tools/recipe.json` | the glyph list (code point → Hebrew cluster) and the pixel size of every generated font |
| `tools/generate.py` | regenerates `fonts/` from the above: `pip install uharfbuzz freetype-py pillow && python tools/generate.py` |
| `fonts/` | the generated fonts shipped in the app |

Code points: multi-character clusters (a letter with nikud) are in the Private Use Area from U+E000; single Hebrew
characters are at their Unicode code point + U+E800 (Connect IQ would otherwise reorder them).

Licence: GNU GPL v2 (`LICENSE`) with the font exception — see `LICENSE_culmus.txt`. The font exception means the
fonts do not by themselves cause an app or document that uses them to be covered by the GPL.
