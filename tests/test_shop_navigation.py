"""TEST-016の限定歩行。合成挙動と任意の外部実画像を分けて検証する。"""
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops, ImageDraw, ImageFilter

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
    def test_08_test023_up_step_with_changing_illumination(self):
        folder = os.environ.get('NECRO_TEST023_FRAMES')
        if not folder:
            self.skipTest('external TEST023 second-run images not supplied')
        import hashlib
        frames = []
        for name, expected in (
                ('run-099.jpg', '7fb69b5fbb860f0b50f6d119048852e2f4bfdc1f7cc0ce20de627095fbf6ece5'),
                ('run-101.jpg', '4283d30c80506c7a59e165d0a13c242f5471a8efd4885ae809f8b648a840f3f5')):
            path = Path(folder) / name
            self.assertEqual(expected, hashlib.sha256(path.read_bytes()).hexdigest())
            with Image.open(path) as image:
                frames.append(nav.scan(image.convert('RGB')))
        # Door/walls move down36px while player remains centered: one up step.
        self.assertEqual('moved', nav.motion(*frames, 'up'))
        self.assertEqual('unexpected', nav.motion(*frames, 'down'))
        self.assertEqual('blocked', nav.motion(frames[0], frames[0], 'up'))

    def test_09_local_light_changes_do_not_create_or_hide_displacement(self):
        rng = random.Random(24024)
        width, height = 224, 104
        raw = bytes(rng.randrange(20, 80) for _ in range(width * height))
        def frame(data):
            return nav.Scene({}, set(), 'unknown', set(), data)
        def light(data):
            # Smooth illumination varies across space, not the terrain texture.
            return bytes(min(255, v + (i % width) // 4 + (i // width) // 3)
                         if v > 6 else v for i, v in enumerate(data))
        before = frame(raw)
        original = Image.frombytes('L', (width, height), raw)
        for direction, (dx, dy) in nav.DIRECTIONS.items():
            for amount, expected in ((0, 'blocked'), (9, 'moved'), (8, 'tween'),
                                     (-9, 'unexpected'), (18, 'unexpected')):
                with self.subTest(direction=direction, amount=amount):
                    moved = Image.new('L', original.size)
                    moved.paste(original, (-dx * amount, -dy * amount))
                    self.assertEqual(expected, nav.motion(before, frame(light(moved.tobytes())), direction))
        for a, b in ((bytes(width * height), raw), (bytes([20]) * len(raw), bytes([80]) * len(raw)),
                     (raw, bytes(rng.randrange(20, 80) for _ in raw))):
            self.assertEqual('unknown', nav.motion(frame(a), frame(b), 'up'))
        repeated = bytes(20 + (i % width % 9) * 5 for i in range(len(raw)))
        self.assertEqual('unknown', nav.motion(frame(repeated), frame(repeated), 'left'))

    def test_10_moving_light_on_textureless_surface_is_not_movement(self):
        for background in (0, 5, 7, 20, 60):
            for shape in ('rectangle', 'ellipse'):
                for sx, sy in ((9, 0), (-9, 0), (0, 9), (0, -9)):
                    with self.subTest(background=background, shape=shape, shift=(sx, sy)):
                        images = []
                        for dx, dy in ((0, 0), (sx, sy)):
                            im = Image.new('L', (224, 104), background)
                            getattr(ImageDraw.Draw(im), shape)((45+dx, 25+dy, 165+dx, 76+dy), fill=150)
                            images.append(nav.Scene({}, set(), 'unknown', set(), im.tobytes()))
                        for direction in nav.DIRECTIONS:
                            self.assertNotEqual('moved', nav.motion(*images, direction))

    def test_11_soft_light_boundary_is_not_terrain_texture(self):
        for shape in ('rectangle', 'ellipse'):
            for radius in (.5, 1, 2, 3, 5):
                with self.subTest(shape=shape, blur=radius):
                    a = Image.new('L', (224, 104), 20)
                    getattr(ImageDraw.Draw(a), shape)((45, 25, 165, 76), fill=220)
                    a = a.filter(ImageFilter.GaussianBlur(radius))
                    b = Image.new('L', a.size, 20); b.paste(a, (9, 0))
                    scenes = [nav.Scene({}, set(), 'unknown', set(), im.tobytes()) for im in (a, b)]
                    self.assertEqual('unknown', nav.motion(*scenes, 'left'))

    def test_12_light_moves_but_weak_ground_texture_stays_still(self):
        rng = random.Random(24024)
        base = Image.frombytes('L', (224, 104), bytes(
            round(30 + 5 * rng.uniform(-1, 1)) for _ in range(224 * 104)))
        for shape in ('rectangle', 'ellipse'):
            light = Image.new('L', base.size)
            getattr(ImageDraw.Draw(light), shape)((45, 25, 165, 76), fill=190)
            light = light.filter(ImageFilter.GaussianBlur(.5))
            for direction, (dx, dy) in nav.DIRECTIONS.items():
                with self.subTest(shape=shape, direction=direction):
                    moved_light = Image.new('L', base.size)
                    moved_light.paste(light, (-9 * dx, -9 * dy))
                    frames = [nav.Scene({}, set(), 'unknown', set(), im.tobytes()) for im in
                              (ImageChops.add(base, light), ImageChops.add(base, moved_light))]
                    self.assertNotEqual('moved', nav.motion(*frames, direction))

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


class ShopNavigationBurstTests(unittest.TestCase):
    @staticmethod
    def corridor(direction, gate_distance=4, goods="unknown"):
        dx, dy = nav.DIRECTIONS[direction]
        gate = (gate_distance * dx, gate_distance * dy)
        tiles = {(i * dx, i * dy): "floor" for i in range(gate_distance)}
        tiles.update({gate: "door", (gate[0] - dy, gate[1] + dx): "gold",
                      (gate[0] + dy, gate[1] - dx): "gold"})
        return scene(tiles, goods=goods)

    def test_01_two_floor_steps_follow_chosen_path_in_all_directions(self):
        for direction in nav.DIRECTIONS:
            for gate_distance in (3, 4, 5):
                with self.subTest(direction=direction, gate_distance=gate_distance):
                    actual = self.corridor(direction, gate_distance)
                    decision = nav.choose(actual)
                    self.assertEqual({"direction", "reason", "target"}, set(decision))
                    self.assertEqual(direction, decision["direction"])
                    self.assertEqual(2, nav.burst_count(actual, decision))

    def test_02_never_overrun_target_or_burst_a_gate_probe(self):
        for direction, (dx, dy) in nav.DIRECTIONS.items():
            with self.subTest(direction=direction):
                actual = self.corridor(direction, 2)
                actual.tiles[(3 * dx, 3 * dy)] = "floor"
                self.assertEqual(1, nav.burst_count(actual, nav.choose(actual)))
                actual = self.corridor(direction, 1)
                decision = nav.choose(actual)
                self.assertEqual("gate_single_probe", decision["reason"])
                self.assertEqual(1, nav.burst_count(actual, decision))

    def test_03_turns_or_different_selected_direction_stay_single(self):
        actual = scene({(0, 0): "floor", (1, 0): "floor", (2, 0): "floor",
                        (1, 1): "floor", (1, 2): "floor", (1, 3): "gold"})
        decision = nav.choose(actual)
        self.assertEqual({"direction": "right", "reason": "observed_floor_vantage",
                          "target": (1, 2)}, decision)
        self.assertEqual(1, nav.burst_count(actual, decision))
        actual = self.corridor("left")
        decision = nav.choose(actual)
        decision["direction"] = "right"
        self.assertEqual(1, nav.burst_count(actual, decision))

    def test_04_unknown_door_and_open_gate_cells_stay_single(self):
        for direction, (dx, dy) in nav.DIRECTIONS.items():
            for distance in (1, 2):
                for obstruction in (None, "unknown", "door", "stone", "dirt", "gate"):
                    with self.subTest(direction=direction, distance=distance, obstruction=obstruction):
                        actual = self.corridor(direction)
                        decision = nav.choose(actual)
                        point = (distance * dx, distance * dy)
                        if obstruction is None:
                            actual.tiles.pop(point)
                        elif obstruction == "gate":
                            actual.tiles[(point[0] - dy, point[1] + dx)] = "gold"
                            actual.tiles[(point[0] + dy, point[1] - dx)] = "gold"
                        else:
                            actual.tiles[point] = obstruction
                        self.assertEqual(1, nav.burst_count(actual, decision))

    def test_05_protected_cells_and_neighbors_prevent_burst(self):
        for direction, (dx, dy) in nav.DIRECTIONS.items():
            for distance in (0, 1, 2):
                point = (distance * dx, distance * dy)
                for offset in ((0, 0), *nav.DIRECTIONS.values()):
                    with self.subTest(direction=direction, distance=distance, offset=offset):
                        actual = self.corridor(direction)
                        decision = nav.choose(actual)
                        actual.protected.add((point[0] + offset[0], point[1] + offset[1]))
                        self.assertEqual(1, nav.burst_count(actual, decision))

    def test_06_partial_visible_or_missing_route_stay_single(self):
        actual = self.corridor("left")
        decision = nav.choose(actual)
        for goods in ("partial", "visible"):
            actual.goods = goods
            self.assertEqual(1, nav.burst_count(actual, decision))
        actual.goods = "unknown"
        for invalid in ({}, {"direction": None}, dict(decision, target=(0, 0)),
                        dict(decision, target=(-9, 0)), dict(decision, target=None),
                        dict(decision, reason="gate_single_probe")):
            self.assertEqual(1, nav.burst_count(actual, invalid))

    def test_07_two_step_motion_partition_and_opposite_all_directions(self):
        rng = random.Random(25025)
        raw = bytes(rng.randrange(20, 80) for _ in range(224 * 104))
        before = nav.Scene({}, set(), "unknown", set(), raw)
        original = Image.frombytes("L", (224, 104), raw)
        for direction, (dx, dy) in nav.DIRECTIONS.items():
            for amount in range(19):
                with self.subTest(direction=direction, amount=amount):
                    image = Image.new("L", original.size)
                    image.paste(original, (-amount * dx, -amount * dy))
                    after = nav.Scene({}, set(), "unknown", set(), image.tobytes())
                    expected = ("blocked" if amount == 0 else "partial" if amount == 9
                                else "moved" if amount == 18 else "tween")
                    self.assertEqual(expected, nav.motion(before, after, direction, expected_steps=2))
            for amount in (-18, -9, -1, 19, 27):
                with self.subTest(direction=direction, invalid_amount=amount):
                    image = Image.new("L", original.size)
                    image.paste(original, (-amount * dx, -amount * dy))
                    after = nav.Scene({}, set(), "unknown", set(), image.tobytes())
                    result = nav.motion(before, after, direction, expected_steps=2)
                    if amount < 0:
                        self.assertEqual("unexpected", result)
                    else:
                        self.assertNotIn(result, ("moved", "partial", "tween"))

    def test_08_motion_steps_are_strict_and_door_opening_is_single_only(self):
        rng = random.Random(25025)
        raw = bytes(rng.randrange(20, 80) for _ in range(224 * 104))
        before = nav.Scene({(1, 0): "door"}, set(), "unknown", set(), raw)
        after = nav.Scene({(1, 0): "floor", (1, -1): "gold", (1, 1): "gold"},
                          set(), "unknown", set(), raw)
        self.assertEqual("door_opened", nav.motion(before, after, "right"))
        self.assertEqual("door_opened", nav.motion(before, after, "right", expected_steps=1))
        self.assertEqual("blocked", nav.motion(before, after, "right", expected_steps=2))
        for invalid in (False, True, 0, 3, -1, 1.0, 2.0, "2", None):
            with self.subTest(expected_steps=invalid):
                self.assertEqual("unknown", nav.motion(before, after, "right", expected_steps=invalid))

    def test_09_two_step_motion_preserves_texture_and_lighting_guards(self):
        rng = random.Random(25025)
        raw = bytes(rng.randrange(20, 80) for _ in range(224 * 104))
        original = Image.frombytes("L", (224, 104), raw)
        before = nav.Scene({}, set(), "unknown", set(), raw)
        for direction, (dx, dy) in nav.DIRECTIONS.items():
            moved = Image.new("L", original.size)
            moved.paste(original, (-18 * dx, -18 * dy))
            lit = bytes(min(255, value + (index % 224) // 4 + (index // 224) // 3)
                        if value > 6 else value for index, value in enumerate(moved.tobytes()))
            after = nav.Scene({}, set(), "unknown", set(), lit)
            self.assertEqual("moved", nav.motion(before, after, direction, expected_steps=2))
        flat = Image.new("L", original.size, 20)
        ImageDraw.Draw(flat).ellipse((45, 25, 165, 76), fill=220)
        flat = flat.filter(ImageFilter.GaussianBlur(1))
        shifted_light = Image.new("L", original.size, 20)
        shifted_light.paste(flat, (18, 0))
        frames = [nav.Scene({}, set(), "unknown", set(), im.tobytes()) for im in (flat, shifted_light)]
        self.assertEqual("unknown", nav.motion(*frames, "left", expected_steps=2))

    def test_10_optional_test024_turn_and_straight_route(self):
        folder = os.environ.get("NECRO_TEST024_FRAMES")
        if not folder:
            self.skipTest("external TEST024 run-101/run-103 images not supplied")
        import hashlib
        for name, expected_hash, count in (
                ("run-101.jpg", "114d277a56e6c6a6108d6ba6d87588e2a8736b74387c01bb05229f9b5493c87c", 1),
                ("run-103.jpg", "c3bdfde05c2beb48b7f76845225b3b8435d8fc8def4b024c6165f15e90cd154e", 2)):
            path = Path(folder) / name
            self.assertEqual(expected_hash, hashlib.sha256(path.read_bytes()).hexdigest())
            with Image.open(path) as image:
                actual = nav.scan(image.convert("RGB"))
            decision = nav.choose(actual)
            self.assertEqual("left", decision["direction"])
            self.assertEqual(count, nav.burst_count(actual, decision))


if __name__ == "__main__":
    unittest.main()
