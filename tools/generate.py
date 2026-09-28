"""Regenerates fonts/ from the Hadasim CLM sources: python tools/generate.py (needs uharfbuzz, freetype-py, Pillow)."""
import json
import pathlib

from fontgen import build_font

ROOT = pathlib.Path(__file__).resolve().parents[1]
recipe = json.loads((ROOT / "tools/recipe.json").read_text(encoding="utf-8"))
glyphs = {int(cp): text for cp, text in recipe["glyphs"].items()}
for f in recipe["fonts"]:
    out = ROOT / "fonts" / f["group"]
    out.mkdir(parents=True, exist_ok=True)
    build_font(glyphs, ROOT / f"source-fonts/HadasimCLM-{f['face'].capitalize()}.otf", f["px"], f["file"], out)
    print(f["group"], f["file"], f["px"])
