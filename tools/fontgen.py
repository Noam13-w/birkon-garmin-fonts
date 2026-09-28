"""Bitmap font generation: each grapheme cluster is shaped with HarfBuzz and rasterised with FreeType into one
glyph of a BMFont (.fnt text + .png atlas, premultiplied white), tightly packed to keep the atlas small."""
import freetype
import uharfbuzz as hb
from PIL import Image, ImageChops, ImageDraw


class Rasterizer:
    def __init__(self, font_path, px):
        self.px = px
        self.hb_font = hb.Font(hb.Face(hb.Blob.from_file_path(str(font_path))))
        self.hb_font.scale = (px * 64, px * 64)
        self.face = freetype.Face(str(font_path))
        self.face.set_pixel_sizes(0, px)

    def render(self, text):
        """Shapes one cluster. Returns (advance, image or None, left, top): image placed with its left edge at
        `left` px from the pen origin and its top edge `top` px above the baseline."""
        if len(text) == 1 and ord(text) > 32 and not self.face.get_char_index(ord(text)):
            return self._synthetic(text)
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb_font, buf, {"kern": True, "mark": True, "mkmk": True})
        pen_x = pen_y = 0
        pieces = []
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            self.face.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
            g = self.face.glyph
            bm = g.bitmap
            if bm.width and bm.rows:
                img = Image.frombytes("L", (bm.width, bm.rows), bytes(bm.buffer))
                pieces.append((img, round((pen_x + pos.x_offset) / 64) + g.bitmap_left,
                               round((pen_y + pos.y_offset) / 64) + g.bitmap_top))
            pen_x += pos.x_advance
            pen_y += pos.y_advance
        adv = round(abs(pen_x) / 64)
        if not pieces:
            return adv, None, 0, 0
        left = min(x for _, x, _ in pieces)
        top = max(y for _, _, y in pieces)
        right = max(x + img.width for img, x, _ in pieces)
        bottom = min(y - img.height for img, _, y in pieces)
        cell = Image.new("L", (right - left, top - bottom), 0)
        for img, x, y in pieces:
            layer = Image.new("L", cell.size, 0)
            layer.paste(img, (x - left, top - y))
            cell = ImageChops.lighter(cell, layer)
        return adv, cell, left, top

    def _synthetic(self, ch):
        """Characters the font lacks (only the middle dot so far): drawn by hand."""
        if ch != "·":
            raise ValueError(f"font has no glyph for U+{ord(ch):04X}")
        d = max(2, round(self.px * 0.12))
        img = Image.new("L", (d, d), 0)
        ImageDraw.Draw(img).ellipse((0, 0, d - 1, d - 1), fill=255)
        adv = round(self.px * 0.3)
        return adv, img, (adv - d) // 2, round(self.px * 0.3) + d // 2


def build_font(glyphs, font_path, px, name, out_dir):
    """Writes <name>.fnt + <name>.png containing glyphs = {code point: cluster text}. Returns the line height."""
    r = Rasterizer(font_path, px)
    rendered = {cp: r.render(text) for cp, text in sorted(glyphs.items())}
    ascent = max([top for _, img, _, top in rendered.values() if img] + [1])
    descent = max([img.height - top for _, img, _, top in rendered.values() if img] + [0])
    pad = 1
    line_h = ascent + descent + 2 * pad
    # Shelf packing, tallest first.
    area = sum((img.width + 1) * (img.height + 1) for _, img, _, _ in rendered.values() if img)
    atlas_w = 256
    while atlas_w < 2048 and atlas_w * atlas_w < area * 1.3:
        atlas_w *= 2
    order = sorted((cp for cp in rendered if rendered[cp][1]), key=lambda c: -rendered[c][1].height)
    placed, x, y, shelf = {}, 0, 0, 0
    for cp in order:
        img = rendered[cp][1]
        if x + img.width > atlas_w:
            x, y, shelf = 0, y + shelf + 1, 0
        placed[cp] = (x, y)
        x += img.width + 1
        shelf = max(shelf, img.height)
    atlas_h = max(1, y + shelf)
    alpha = Image.new("L", (atlas_w, atlas_h), 0)
    for cp, (px_, py_) in placed.items():
        alpha.paste(rendered[cp][1], (px_, py_))
    # Premultiplied (white on black): the coverage is in the colour channels as well as in alpha.
    Image.merge("RGBA", (alpha, alpha, alpha, alpha)).save(out_dir / f"{name}.png", optimize=True)
    lines = [
        f'info face="{name}" size={px} bold=0 italic=0 charset="" unicode=1 stretchH=100 smooth=1 aa=1 '
        f'padding=0,0,0,0 spacing=1,1',
        f"common lineHeight={line_h} base={pad + ascent} scaleW={atlas_w} scaleH={atlas_h} pages=1 packed=0",
        f'page id=0 file="{name}.png"',
        f"chars count={len(rendered)}",
    ]
    for cp, (adv, img, left, top) in rendered.items():
        if img:
            gx, gy = placed[cp]
            lines.append(f"char id={cp} x={gx} y={gy} width={img.width} height={img.height} xoffset={left} "
                         f"yoffset={pad + ascent - top} xadvance={adv} page=0 chnl=15")
        else:
            lines.append(f"char id={cp} x=0 y=0 width=0 height=0 xoffset=0 yoffset=0 xadvance={adv} page=0 chnl=15")
    (out_dir / f"{name}.fnt").write_text("\n".join(lines) + "\n", encoding="ascii")
    return line_h, atlas_w, atlas_h
