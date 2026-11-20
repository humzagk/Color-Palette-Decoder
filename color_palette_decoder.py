"""
Color Palette Decoder: find the dominant colours of any image.

Instead of uploading an image to an online palette generator, run this locally.
The image is downscaled, quantised with Pillow's fast octree algorithm so that near-identical shades
merge into one colour, and the resulting colours are ranked by how much of the
image they cover.

Usage:
    python color_palette_decoder.py photo.jpg
    python color_palette_decoder.py photo.jpg -n 8 --format json
    python color_palette_decoder.py photo.jpg --swatch palette.png
"""

import argparse
import json
import sys

from PIL import Image, ImageDraw

MAX_SIDE = 200  # downscale target; plenty for palette extraction and keeps it fast


def _prepare(image, max_side=MAX_SIDE):
    """Downscale and return an RGB image of only the visible (non-transparent) pixels."""
    image = image.copy()
    image.thumbnail((max_side, max_side))
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        opaque = [p[:3] for p in rgba.getdata() if p[3] >= 128]
        if not opaque:
            raise ValueError("image is fully transparent")
        strip = Image.new("RGB", (len(opaque), 1))
        strip.putdata(opaque)
        return strip
    return image.convert("RGB")


def extract_palette(image, n_colors=6):
    """
    Return the image's dominant colours as a list of ((r, g, b), share) tuples,
    sorted from most to least common. Shares sum to 1.
    """
    if n_colors < 1:
        raise ValueError("n_colors must be at least 1")
    rgb = _prepare(image)
    quantized = rgb.quantize(colors=n_colors, method=Image.Quantize.FASTOCTREE)
    lut = quantized.getpalette()
    counts = quantized.getcolors(maxcolors=256)
    total = sum(c for c, _ in counts)
    palette = [
        (tuple(lut[3 * idx: 3 * idx + 3]), count / total)
        for count, idx in sorted(counts, reverse=True)
    ]
    return palette


def to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def render_swatch(palette, path, width=600, height=120):
    """Save a strip whose segments are sized by each colour's share of the image."""
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    x = 0
    for i, (rgb, share) in enumerate(palette):
        w = width - x if i == len(palette) - 1 else round(share * width)
        draw.rectangle([x, 0, x + w, height], fill=rgb)
        if w >= 60:
            luminance = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
            text_color = "black" if luminance > 140 else "white"
            draw.text((x + 6, height - 18), to_hex(rgb), fill=text_color)
        x += w
    img.save(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract the dominant colour palette of an image.")
    parser.add_argument("image", help="path to the input image")
    parser.add_argument("-n", "--colors", type=int, default=6, help="number of colours to extract (default 6)")
    parser.add_argument("--format", choices=["hex", "rgb", "json"], default="hex", help="output format")
    parser.add_argument("--swatch", metavar="PATH", help="also save a palette swatch image to PATH")
    args = parser.parse_args(argv)

    if not 1 <= args.colors <= 256:
        parser.error("--colors must be between 1 and 256")
    try:
        with Image.open(args.image) as image:
            palette = extract_palette(image, args.colors)
    except (OSError, ValueError) as e:
        parser.exit(1, f"error: {e}\n")

    if args.format == "json":
        json.dump([{"hex": to_hex(rgb), "rgb": list(rgb), "share": round(share, 4)} for rgb, share in palette],
                  sys.stdout, indent=2)
        print()
    else:
        for rgb, share in palette:
            label = to_hex(rgb) if args.format == "hex" else "rgb({}, {}, {})".format(*rgb)
            print(f"{label}  {share:6.1%}")

    if args.swatch:
        render_swatch(palette, args.swatch)


if __name__ == "__main__":
    main()
