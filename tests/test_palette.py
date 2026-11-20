import io
import json
import os
import random
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import color_palette_decoder as cpd  # noqa: E402

COLOURS = [(220, 60, 50), (40, 90, 160), (240, 200, 70), (30, 30, 35)]


def noisy_blocks(widths=(100, 100, 100, 100), noise=6, seed=0):
    """Vertical colour blocks with per-pixel noise, like a photo of flat colours."""
    rng = random.Random(seed)
    img = Image.new("RGB", (sum(widths), 100))
    px = []
    for y in range(100):
        for colour, w in zip(COLOURS, widths):
            for _ in range(w):
                px.append(tuple(max(0, min(255, round(c + rng.gauss(0, noise)))) for c in colour))
    img.putdata(px)
    return img


def distance(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


class ExtractPaletteTest(unittest.TestCase):
    def test_noisy_image_gives_one_entry_per_real_colour(self):
        palette = cpd.extract_palette(noisy_blocks(), 4)
        self.assertEqual(len(palette), 4)
        for colour in COLOURS:
            nearest = min(distance(colour, rgb) for rgb, _ in palette)
            self.assertLess(nearest, 10, f"{colour} not found in {palette}")

    def test_shares_reflect_area_and_are_sorted(self):
        palette = cpd.extract_palette(noisy_blocks(widths=(200, 100, 60, 40)), 4)
        shares = [s for _, s in palette]
        self.assertAlmostEqual(sum(shares), 1.0, places=6)
        self.assertEqual(shares, sorted(shares, reverse=True))
        self.assertAlmostEqual(shares[0], 0.5, delta=0.02)
        self.assertLess(distance(palette[0][0], COLOURS[0]), 10)

    def test_transparent_pixels_are_ignored(self):
        img = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        for x in range(5):
            for y in range(10):
                img.putpixel((x, y), (10, 200, 30, 255))
        palette = cpd.extract_palette(img, 3)
        self.assertEqual(len(palette), 1)
        self.assertEqual(palette[0][0], (10, 200, 30))

    def test_fewer_unique_colours_than_requested(self):
        img = Image.new("RGB", (10, 10), (255, 0, 0))
        self.assertEqual(cpd.extract_palette(img, 6), [((255, 0, 0), 1.0)])

    def test_invalid_n(self):
        with self.assertRaises(ValueError):
            cpd.extract_palette(Image.new("RGB", (4, 4)), 0)


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "img.png")
        noisy_blocks().save(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            cpd.main([self.path, *args])
        return out.getvalue()

    def test_hex_output(self):
        lines = self.run_cli("-n", "4").strip().splitlines()
        self.assertEqual(len(lines), 4)
        self.assertTrue(all(line.startswith("#") and len(line.split()[0]) == 7 for line in lines))

    def test_json_output_and_swatch(self):
        swatch = os.path.join(self.tmp.name, "swatch.png")
        data = json.loads(self.run_cli("-n", "4", "--format", "json", "--swatch", swatch))
        self.assertEqual(len(data), 4)
        self.assertEqual(set(data[0]), {"hex", "rgb", "share"})
        self.assertEqual(Image.open(swatch).size, (600, 120))


if __name__ == "__main__":
    unittest.main()
