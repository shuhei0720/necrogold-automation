"""TEST-014の画像3群。実画像の小さな文字maskと合成場面で境界を検査する。

mask出典はTEST-013未加工896×414 JPEG。deathのみ既存R12資料のcrop。
全画像評価はrepo外のホスト記録。
このportable suiteの合格は、未知の実機画像での認識精度を証明しない。
"""
import base64
import io
import unittest
from unittest.mock import patch
import zlib

from PIL import Image, ImageDraw
from necroprobe import gold_scan

# 実画像から独立に切り出した参照。production定数はimportしない。
FIXTURES = {'icon': ((429, 6, 465, 42), 'eNpjYMAHmP8w/sEkmKlMMGKw8AMA5CwvxQ=='),
 'footer': ((752, 396, 856, 414),
            'eNqVzsEJhTAQBNAJEeJhC/AYCPyz4F0sZYXfhwEb+iWsXViMqGNOehH+3h47DAP8fy7e8buhXYHyDAcB9FHCNpl3+YGamSSodEhjRtoRCz4uo9uhBV+CMRM0OhhhcLOgJcYL3gtUjQis5g6bltfVJ7bzHl0='),
 'continue': ((384, 104, 512, 132),
              'eNq9j7ENwjAQRX+iSHYRyS5dgSMxABvggiJjMAZdDuEhKBgmozBCBkAyd+eEBZC44vTfv/O3Dfxa3Sas9jhIY9fadj+LXBmhVWlXHkquI21lSdaLPFYOSEHzTm9lj+tEwol4LWHH17XTwoa4qb6gITQgU3gpPiSftjnd5wlP1Vp0o4BeuJFzoEz20H3ZRU9j5ZobPcZOuWd2L+Gz5l/qr83iTHaEf9cH8iMj6w=='),
 'restart': ((357, 256, 538, 284),
             'eNrN0DEOwjAMBdCfOgIPCHlkqIS5B0OOwjEYO3GuHqVH6NgBCZy4gUiIFZHF0ZPzaxf4m9PVItFKrPKdw8r0eDM13dTwUu60GAds55Ujg60wFxapX2NPcYasscK4BBnUWSWBJmNlUuOUOeImx3vX+/vMZebYLCiHwuo8GlNuEhNrULvsgPTa27kM0YQk52R8Aoa6ZY7t87ApjMMGbcjnrz5nnnC1Z3vo3HT/+DwBq5wVvQ=='),
 'death': ((312, 312, 582, 336),
           'eNrN0j1OhUAQB/D/woaPhADmNRTGt4UHwN4EoonnIBav1Rs4aGNhrLXyKs+Eg3AEsHomRpxZQDQxsbFwCdnJ7m93ZheAv2jm5+GYX9dGdQAoQEscjAsyifcISuF0BxAWgUX4RyxWucxSuYiTRQw94BW9FcseaTqKdWvrGO6ULWQSnogpS15xH60fYteRkaEVkUg3CyPHC4o0eeo4cBzehVNoR4SxojTnOZ/L1MDFGxPYImwd8N9FNGYjonrOcJvL2mKnNSJOl6aJCHVfnRkWzaZ4JTPtoXEoJUxnUVsWKW6SbkXzjWubxWAWqJDjWpESITcdaNXIZDAtIJQsSHnbT/ES6y+Cr6fkXSjUNGfJnG/fZWplGNUiLjm+GgU5o4jgwyVUYfbIwpVb5wMdz4KTtNjnBweq6+v2t9+L8G/aBzi1QXA=')}


def fixture(image, name):
    box, encoded = FIXTURES[name]
    mask = Image.frombytes("1", (box[2] - box[0], box[3] - box[1]),
                           zlib.decompress(base64.b64decode(encoded)))
    image.paste(mask.convert("RGB"), box[:2])


def floor():
    image = Image.new("RGB", (896, 414))
    draw = ImageDraw.Draw(image)
    for row in range(6):
        for col in range(8):
            value = 25 + (row + col) % 3 * 20
            draw.rectangle((224 + col * 56, 70 + row * 48,
                            279 + col * 56, 117 + row * 48), fill=(value, value, value))
    fixture(image, "icon")
    fixture(image, "footer")
    return image


def encoded(image):
    output = io.BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


class GoldScanTests(unittest.TestCase):
    def test_01_floor_gold_top_edge_and_occlusion(self):
        image = floor()
        draw = ImageDraw.Draw(image)
        # HUD coin/minimap and narrow torch flame are not gold walls.
        draw.rectangle((780, 10, 815, 40), fill=(210, 170, 30))
        draw.rectangle((780, 340, 815, 370), fill=(210, 170, 30))
        draw.rectangle((350, 115, 355, 145), fill=(210, 170, 30))
        clear = gold_scan.analyze(encoded(image))
        self.assertEqual(("floor", "clear"), (clear["state"], clear["gold"]))
        self.assertEqual(48, len(clear["fingerprint"]))
        self.assertFalse(clear["restart_label"])
        for box in ((300, 100, 335, 135), (300, 0, 335, 5)):
            with self.subTest(box=box):
                candidate = image.copy()
                ImageDraw.Draw(candidate).rectangle(box, fill=(210, 170, 30))
                result = gold_scan.analyze(encoded(candidate))
                self.assertEqual(("floor", "candidate"), (result["state"], result["gold"]))
                self.assertGreaterEqual(result["gold_peak"], 135)
        # A 12-pixel stripe is ambiguous, never a clearance for restarting.
        maybe = image.copy()
        ImageDraw.Draw(maybe).rectangle((300, 100, 311, 135), fill=(210, 170, 30))
        result = gold_scan.analyze(encoded(maybe))
        self.assertEqual("unknown", result["gold"])
        self.assertTrue(100 <= result["gold_peak"] < 135)
        dead = image.copy()
        fixture(dead, "death")
        self.assertEqual("unknown", gold_scan.analyze(encoded(dead))["state"])
        # Missing or changed floor numeral, or an obscured pause icon is unknown.
        for box in ((842, 399, 855, 414), (429, 6, 465, 42)):
            altered = image.copy()
            ImageDraw.Draw(altered).rectangle(box, fill="black")
            self.assertEqual("unknown", gold_scan.analyze(encoded(altered))["state"])

    def test_02_pause_restart_label_and_invalid_frames(self):
        pause = Image.new("RGB", (896, 414))
        fixture(pause, "continue")
        fixture(pause, "restart")
        result = gold_scan.analyze(encoded(pause))
        self.assertEqual(("pause", "unknown", [], True),
                         (result["state"], result["gold"], result["fingerprint"], result["restart_label"]))
        ImageDraw.Draw(pause).rectangle((357, 256, 538, 284), fill="black")
        result = gold_scan.analyze(encoded(pause))
        self.assertEqual("pause", result["state"])
        self.assertFalse(result["restart_label"])
        for raw in (b"", b"not an image", encoded(Image.new("RGB", (896, 414))),
                    encoded(Image.new("RGB", (896, 414), "white")),
                    encoded(Image.new("RGB", (414, 896))), encoded(Image.new("RGB", (1792, 828)))):
            with self.subTest(length=len(raw)):
                result = gold_scan.analyze(raw)
                self.assertEqual(("unknown", "unknown", [], False),
                                 (result["state"], result["gold"], result["fingerprint"], result["restart_label"]))

    def test_03_terrain_change_ignores_animation_and_never_reformats(self):
        image = floor()
        first = gold_scan.analyze(encoded(image))["fingerprint"]
        animation = image.copy()
        ImageDraw.Draw(animation).rectangle((430, 180, 470, 320), fill="white")
        ImageDraw.Draw(animation).rectangle((350, 115, 355, 145), fill=(210, 170, 30))
        current = gold_scan.analyze(encoded(animation))["fingerprint"]
        self.assertFalse(gold_scan.changed(first, current))
        terrain = image.copy()
        ImageDraw.Draw(terrain).rectangle((224, 70, 391, 165), fill=(130, 130, 130))
        later = gold_scan.analyze(encoded(terrain))["fingerprint"]
        self.assertTrue(gold_scan.changed(first, later))
        self.assertFalse(gold_scan.changed(first, first))
        for bad in ([], [1] * 47, [True] * 48, [256] * 48, None):
            self.assertFalse(gold_scan.changed(first, bad))
        raw = encoded(image)
        with patch.object(Image.Image, "resize", side_effect=AssertionError("resize forbidden")), \
             patch.object(Image.Image, "rotate", side_effect=AssertionError("rotate forbidden")), \
             patch.object(Image.Image, "transpose", side_effect=AssertionError("transpose forbidden")):
            self.assertEqual("floor", gold_scan.analyze(raw)["state"])


if __name__ == "__main__":
    unittest.main()
