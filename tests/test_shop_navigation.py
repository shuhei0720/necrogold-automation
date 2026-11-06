"""TEST-016の限定歩行。合成挙動と任意の外部実画像を分けて検証する。"""
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from necroprobe import shop_navigation as nav


def terrain():
    rng = random.Random(16016)
    image = Image.new("RGB", (896, 414))
    pixels = image.load()
    for y in range(70, 320):
        for x in range(180, 710):
            r = rng.randrange(12, 35)
            pixels[x, y] = (r, r * 3 // 5, r * 3 // 5)
    return image


def tile(image, point, color):
    x, y = 448 + 36 * point[0], 207 + 36 * point[1]
    image.paste(color, (x - 17, y - 17, x + 18, y + 18))


def shifted(image, dx, dy):
    result = Image.new("RGB", image.size)
    result.paste(image, (dx, dy))
    return result


def scene(tiles, protected=(), goods="unknown"):
    return nav.Scene(tiles, {p for p, kind in tiles.items() if kind == "gold"},
                     goods, set(protected), b"")


def shop_image():
    image = terrain()
    draw = ImageDraw.Draw(image)
    # A sign over each outer merchandise slot, three sprites and price labels.
    for x in (268, 340):
        draw.rectangle((x - 14, 114, x + 14, 142), fill=(190, 180, 12))
        draw.text((x - 10, 121), "SHOP", fill=(20, 20, 10))
    for x in (268, 304, 340):
        draw.ellipse((x - 9, 167, x + 9, 188), fill=(70, 150, 210))
        draw.text((x - 9, 201), "100", fill=(245, 245, 245))
    return image


class ShopNavigationTests(unittest.TestCase):
    def test_06_bright_floor_keeps_stone_dirt_and_unknown_blocked(self):
        def patch_cell(image, color, texture=True):
            cell=Image.new('RGB',(25,25))
            cell.putdata([tuple(max(0,min(255,c+(0 if i==624 else -3 if i%2 else 3))) for c in color)
                          if texture else color for i in range(625)])
            image.paste(cell,(400,195))  # player-relative (-1,0)
        for color in ((39,24,22),(40,25,23),(45,30,30),(52,35,29)):
            with self.subTest(floor=color):
                image=terrain();patch_cell(image,color)
                self.assertEqual('floor',nav.scan(image).tiles.get((-1,0)))
        for color in ((50,36,30),(50,25,25),(45,32,29),(53,33,31),(70,70,65),(50,32,15)):
            with self.subTest(blocked=color):
                image=terrain();patch_cell(image,color)
                self.assertNotEqual('floor',nav.scan(image).tiles.get((-1,0)))
        image=terrain();patch_cell(image,(40,25,23),False)
        self.assertNotEqual('floor',nav.scan(image).tiles.get((-1,0)))

    def test_07_optional_test019_left_shop_bright_frame(self):
        path=os.environ.get('NECRO_NAV_TEST019')
        if not path:self.skipTest('external TEST019 run-101.jpg not supplied')
        with Image.open(path) as src:actual=nav.scan(src.convert('RGB'))
        self.assertEqual({(-6,-1),(-6,1)},actual.gold)
        self.assertEqual('floor',actual.tiles.get((-1,0)))
        self.assertEqual('floor',actual.tiles.get((-2,0)))
        decision=nav.choose(actual)
        self.assertEqual('left',decision['direction'])
        self.assertEqual((-5,0),decision['target'])
        actual.protected.add((-1,0))
        self.assertIsNone(nav.choose(actual)['direction'])

    def test_01_native_grid_dark_floor_gold_and_invalid_geometry(self):
        image = terrain()
        tile(image, (-5, -1), (160, 130, 45))
        tile(image, (-5, 1), (160, 130, 45))
        tile(image, (-5, 0), (65, 44, 22))
        tile(image, (2, 0), (70, 70, 65))
        tile(image, (1, 1), (50, 32, 15))
        with patch.object(Image.Image, "resize", side_effect=AssertionError("resize")), \
             patch.object(Image.Image, "rotate", side_effect=AssertionError("rotate")):
            actual = nav.scan(image)
        self.assertEqual("floor", actual.tiles[(-1, 0)])
        self.assertEqual({(-5, -1), (-5, 1)}, actual.gold)
        self.assertEqual("door", actual.tiles[(-5, 0)])
        self.assertNotEqual("floor", actual.tiles[(2, 0)])
        self.assertNotEqual("floor", actual.tiles[(1, 1)])
        self.assertNotEqual("floor", actual.tiles.get((-10, 0)))
        self.assertEqual("left", nav.choose(actual)["direction"])
        self.assertIsNone(nav.choose(nav.scan(Image.new("RGB", (414, 896))))["direction"])

    def test_02_routes_four_gates_and_never_enter_protected_or_unknown(self):
        for name, (dx, dy) in {"up": (0, -1), "down": (0, 1),
                               "left": (-1, 0), "right": (1, 0)}.items():
            gate = (3 * dx, 3 * dy)
            tiles = {(i * dx, i * dy): "floor" for i in range(3)}
            tiles.update({gate: "door", (gate[0] - dy, gate[1] + dx): "gold",
                          (gate[0] + dy, gate[1] - dx): "gold"})
            self.assertEqual(name, nav.choose(scene(tiles))["direction"])
            # Every possible adjacent result must be safe until controls are verified.
            dangerous = scene(tiles, {(1, 0)})
            self.assertIsNone(nav.choose(dangerous)["direction"])
            tiles.pop((dx, dy))
            self.assertIsNone(nav.choose(scene(tiles))["direction"])
        tiles = {(0, 0): "floor", (1, 0): "stone", (2, 0): "gold"}
        self.assertIsNone(nav.choose(scene(tiles))["direction"])

    def test_03_goods_stop_before_movement_and_partial_never_means_absent(self):
        image = shop_image()
        actual = nav.scan(image)
        self.assertEqual("visible", actual.goods)
        self.assertTrue(actual.protected)
        self.assertIsNone(nav.choose(actual)["direction"])
        partial = image.copy()
        partial.paste((0, 0, 0), (326, 197, 357, 220))
        actual = nav.scan(partial)
        self.assertEqual("partial", actual.goods)
        self.assertTrue(actual.protected)
        hidden_prices = image.copy()
        hidden_prices.paste((0, 0, 0), (250, 197, 360, 225))
        actual = nav.scan(hidden_prices)
        self.assertEqual("partial", actual.goods)
        self.assertTrue(actual.protected)
        self.assertNotEqual("visible", nav.scan(terrain()).goods)

    def test_04_signed_motion_tween_blocked_and_door_opening(self):
        image = terrain()
        before = nav.scan(image)
        for direction, vector in {"up": (0, -1), "down": (0, 1),
                                  "left": (-1, 0), "right": (1, 0)}.items():
            dx, dy = vector
            with self.subTest(direction=direction):
                self.assertEqual("moved", nav.motion(before, nav.scan(shifted(image, -36 * dx, -36 * dy)), direction))
                self.assertEqual("tween", nav.motion(before, nav.scan(shifted(image, -32 * dx, -32 * dy)), direction))
                self.assertEqual("unexpected", nav.motion(before, nav.scan(shifted(image, 36 * dx, 36 * dy)), direction))
                self.assertEqual("unexpected", nav.motion(before, nav.scan(shifted(image, -72 * dx, -72 * dy)), direction))
        self.assertEqual("blocked", nav.motion(before, before, "left"))
        self.assertEqual("unknown", nav.motion(before, nav.scan(Image.new("RGB", (896, 414))), "left"))
        closed = image.copy()
        tile(closed, (1, -1), (160, 130, 45))
        tile(closed, (1, 1), (160, 130, 45))
        tile(closed, (1, 0), (65, 44, 22))
        opened = closed.copy()
        opened.paste(image.crop((467, 190, 502, 225)), (467, 190))
        self.assertEqual("door_opened", nav.motion(nav.scan(closed), nav.scan(opened), "right"))

    def test_05_optional_recorded_native_images(self):
        fixture_dir = os.environ.get("NECRO_NAV_FIXTURES")
        found_path = os.environ.get("NECRO_NAV_FOUND")
        if not fixture_dir or not found_path:
            self.skipTest("外部実画像はNECRO_NAV_FIXTURES/NECRO_NAV_FOUND指定時だけ検証")
        with Image.open(found_path) as image:
            actual = nav.scan(image.convert("RGB"))
        self.assertEqual("left", nav.choose(actual)["direction"])
        with Image.open(Path(fixture_dir) / "floor-124.jpg") as image:
            actual = nav.scan(image.convert("RGB"))
        self.assertEqual("visible", actual.goods)
        self.assertIsNone(nav.choose(actual)["direction"])
        frames = {}
        for number in (119, 121, 124):
            with Image.open(Path(fixture_dir) / f"floor-{number:03}.jpg") as image:
                frames[number] = nav.scan(image.convert("RGB"))
        self.assertEqual("tween", nav.motion(frames[119], frames[121], "left"))
        # Retain the command's original frame while observing the tween settle.
        self.assertEqual("moved", nav.motion(frames[119], frames[124], "left"))


if __name__ == "__main__":
    unittest.main()
