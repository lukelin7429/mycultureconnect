#!/usr/bin/python3
"""Build the site logo and the icon set from one master image.

    /usr/bin/python3 scripts/build_favicons.py      (needs Pillow)

To change the logo: replace assets/img/logo-source.jpg and run this again.
If the lettering sits somewhere else in the new picture, adjust LETTERS below.

Why there are two pieces of artwork
-----------------------------------
The site used to ship a single icon: the full square logo at 180px. A browser
tab shows an icon at 16px, and at that size "MCC + My Culture Connect + book +
globe" is an orange smudge that nobody reads as a logo. Nothing answered at
/favicon.ico either, which is the only place many apps look.

  the logo   the full square picture. Used where there is room for it: the
             header and footer of every page, the iPhone / iPad home screen.
  the mark   "MCC" — the logo's own lettering, lifted out of the picture — on
             the logo's orange. Used wherever the icon is shown small (tabs,
             bookmarks, history, search results).

The mark is drawn separately for each size, not scaled down from one master:
the lettering is 3.3x wider than it is tall, so at 16px it would be 4px high.
Each small size stretches it taller (nobody can see the distortion at that
size; everybody can see whether it says MCC).

Outputs
  /assets/img/logo.png        256, the logo (pages show it at 42px)
  /assets/img/favicon.png     180, the logo — the old icon address, kept alive
                              for anything that still points at it
  /apple-touch-icon.png       180, the logo, no transparency
  /favicon.ico                16 + 32 + 48, the mark
  /assets/img/icon-32.png     the mark
  /assets/img/icon-192.png    the mark (Google shows this one inside a circle,
                              so the lettering stays clear of the corners)
"""
import io
import os
import struct

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = 'assets/img/logo-source.jpg'
LETTERS = (174, 125, 1128, 416)             # where "MCC" sits in the source
ORANGE = (249, 98, 4)                       # the source's own background
BIG = 1024                                  # draw large, then reduce: smooth edges

logo = Image.open(os.path.join(ROOT, SOURCE)).convert('RGB')

# The lettering is the only thing in the picture that is white: skin, sleeves,
# the orange and the thin yellow globe lines are all low in at least one
# channel. The darkest channel of each pixel therefore separates it cleanly.
_r, _g, _b = logo.split()
alpha = ImageChops.darker(ImageChops.darker(_r, _g), _b).point(
    lambda v: max(0, min(255, int((v - 200) * 255 / 40))))
WORD = alpha.crop(LETTERS)

#        size: (width of the lettering as a share of the tile, vertical stretch, extra weight)
TUNING = {16: (0.90, 1.70, 0),
          32: (0.86, 1.55, 0),
          48: (0.86, 1.25, 0),
          192: (0.82, 1.08, 0)}        # room to spare here: keep the letters' own proportions


def mark(size):
    width, stretch, weight = TUNING[size]
    tile = Image.new('RGBA', (BIG, BIG), (0, 0, 0, 0))
    shape = Image.new('L', (BIG, BIG), 0)
    ImageDraw.Draw(shape).rounded_rectangle((0, 0, BIG - 1, BIG - 1), radius=int(BIG * 0.22), fill=255)
    tile.paste(ORANGE + (255,), (0, 0), shape)

    w, h = WORD.size
    k = BIG * width / w
    word = WORD.resize((round(w * k), round(h * k * stretch)), Image.LANCZOS)
    if weight:
        room = Image.new('L', (word.width + 2 * weight, word.height + 2 * weight), 0)
        room.paste(word, (weight, weight))
        word = room.filter(ImageFilter.MaxFilter(weight | 1))
    tile.paste(Image.new('RGBA', word.size, (255, 255, 255, 255)),
               ((BIG - word.width) // 2, (BIG - word.height) // 2), word)
    return tile.resize((size, size), Image.LANCZOS)


def full(size):
    return logo.resize((size, size), Image.LANCZOS)


def png(im):
    buf = io.BytesIO()
    im.save(buf, 'PNG', optimize=True)
    return buf.getvalue()


def ico(images):
    """An .ico holding one PNG per size (Pillow would rescale a single image)."""
    blobs = [png(im) for im in images]
    out = struct.pack('<HHH', 0, 1, len(images))
    offset = 6 + 16 * len(images)
    for im, blob in zip(images, blobs):
        out += struct.pack('<BBBBHHII', im.width % 256, im.height % 256, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    return out + b''.join(blobs)


def save(rel, data):
    path = os.path.join(ROOT, rel)
    with open(path, 'wb') as f:
        f.write(data)
    print(f'  {rel:28s} {len(data):>7,d} bytes')


if __name__ == '__main__':
    save('assets/img/logo.png', png(full(256)))
    save('assets/img/favicon.png', png(full(180)))
    save('apple-touch-icon.png', png(full(180)))
    save('favicon.ico', ico([mark(16), mark(32), mark(48)]))
    save('assets/img/icon-32.png', png(mark(32)))
    save('assets/img/icon-192.png', png(mark(192)))
