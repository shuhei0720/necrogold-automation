"""TEST119 capture62: a wall cap supports a finite left inside view.

The public maps express the user's marked upper-left boundary, not private
pixels, a copied Scene, or a shop-positive label. DIRT and UNKNOWN never
become traversal cells. A source override is only for the exact TEST119 Red.
"""
import ctypes as C
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests import test_native_passage_navigation072 as nav
from tests import test_native_lower_fringe100 as lower100
from tests import test_native_navigation116 as neck116
from tests import test_native_navigation117 as bend117

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'patches/loopctrl/ngg2'
BASELINE_SHA256 = 'e6893c8a08ddd03065c154ae47c75a9994a5f0372084d6850fa3e41a7c30e1f1'
MOUTH = (-3, -2)
CAP = (-4, -3)
INBOARD = (-2, -2)
VANTAGE = (-2, -1)
WALLS = tuple(dict.fromkeys((CAP,) + tuple((x, -3) for x in range(-3, 3))
                           + tuple((-3, y) for y in range(-3, 4))))
FLOORS = (INBOARD, VANTAGE, (-1, -2), (-1, -1), (0, -1), (-1, 0), (0, 0))
DARK = ((-4, -2), (-4, -1))
LEGACY_FLOOR_MASKS = {CAP: 32, (-2, -3): 1, (-1, -3): 2, MOUTH: 32, (-3, -1): 64}


def capped_left120(wall_kind=nav.DIRT):
    scene = nav.Scene(abi_version=1, struct_size=C.sizeof(nav.Scene), state=2, gold_state=1)
    for point in WALLS:
        nav.set_cell(scene, *point, wall_kind)
    for point in FLOORS:
        nav.set_cell(scene, *point, nav.FLOOR)
    return scene


class NativeCappedLeft120Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        override = os.environ.get('NECRO_NAV120_RED_SOURCE')
        source = Path(override) if override else CORE / 'NG2Navigation.c'
        if override and hashlib.sha256(source.read_bytes()).hexdigest() != BASELINE_SHA256:
            raise AssertionError('TEST120 Red source must be exact TEST119 Navigation')
        cls.directory = tempfile.TemporaryDirectory(prefix='capped-left120-')
        cls.libraries = {}
        for profile, flags in (('unchanged_o0', ['-O0']),
                               ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            target = Path(cls.directory.name) / (profile + '.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror', '-pedantic',
                            '-fPIC', '-shared', '-I' + str(CORE), str(source), '-lm',
                            '-o', str(target)], check=True)
            cls.libraries[profile] = library = C.CDLL(str(target))
            library.ng2_passage_candidates.argtypes = [C.POINTER(nav.Scene)]
            library.ng2_passage_candidates.restype = C.c_uint32
            library.ng2_choose_passage.argtypes = [C.POINTER(nav.Scene), C.c_int32, C.c_int32,
                                                  C.c_int32, C.c_int32, C.POINTER(nav.Decision)]
            library.ng2_choose_passage.restype = C.c_int

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def candidates(self, library, scene):
        before = bytes(scene)
        mask = library.ng2_passage_candidates(C.byref(scene))
        self.assertEqual(before, bytes(scene), 'a view hypothesis must preserve every Scene byte')
        return mask

    def choose(self, library, scene, x=0, y=0):
        before = bytes(scene)
        out = nav.Decision(99, 99, 99, 99, 99)
        length = library.ng2_choose_passage(C.byref(scene), x, y, *MOUTH, C.byref(out))
        self.assertEqual(before, bytes(scene))
        return length, tuple(getattr(out, name) for name, _ in out._fields_)

    def test_cap_and_independent_boundaries_merit_only_the_fixed_left_bit5(self):
        for profile, library in self.libraries.items():
            for kind in (nav.DIRT, nav.STONE):
                with self.subTest(profile=profile, kind=kind):
                    scene = capped_left120(kind)
                    self.assertEqual(32, self.candidates(library, scene),
                                     'the marked cap and observed inside FLOOR merit a closer view')
                    self.assertEqual(kind, scene.tiles[nav.offset(*MOUTH)])
                    self.assertEqual((0, 0), tuple(scene.tiles[nav.offset(*point)] for point in DARK))

    def test_each_wall_and_outer_cap_is_required_without_erasing_legacy_candidates(self):
        for library in self.libraries.values():
            for point in WALLS:
                for kind in (0, nav.FLOOR, nav.GOLD, nav.DOOR, nav.ITEM):
                    with self.subTest(point=point, kind=kind):
                        scene = capped_left120(); nav.set_cell(scene, *point, kind)
                        expected = LEGACY_FLOOR_MASKS.get(point, 0) if kind == nav.FLOOR else 0
                        self.assertEqual(expected, self.candidates(library, scene))
            shifted_cap = capped_left120()
            nav.set_cell(shifted_cap, *CAP, 0); nav.set_cell(shifted_cap, -5, -3, nav.DIRT)
            self.assertEqual(0, self.candidates(library, shifted_cap), 'a different cap cannot claim this mouth')

    def test_every_inside_floor_and_unknown_outside_are_required(self):
        for library in self.libraries.values():
            for point in FLOORS:
                for kind in (0, nav.GOLD, nav.STONE, nav.DIRT, nav.DOOR, nav.ITEM):
                    with self.subTest(floor=point, kind=kind):
                        scene = capped_left120(); nav.set_cell(scene, *point, kind)
                        self.assertEqual(0, self.candidates(library, scene))
            for point in DARK:
                for kind in (nav.FLOOR, nav.GOLD, nav.STONE, nav.DIRT, nav.DOOR, nav.ITEM):
                    with self.subTest(outside=point, kind=kind):
                        scene = capped_left120(); nav.set_cell(scene, *point, kind)
                        self.assertEqual(0, self.candidates(library, scene))
            isolated = capped_left120()
            for point in ((-1, 0), (0, -1)):
                nav.set_cell(isolated, *point, 0)
            self.assertEqual(0, self.candidates(library, isolated))
            self.assertEqual((0, (0, 0, 0, 0, 0)), self.choose(library, isolated))

    def test_scene_goods_gold_item_protection_and_ordinary_door_alone_do_not_qualify(self):
        for library in self.libraries.values():
            for field, value in (('state', 0), ('state', 1), ('state', 3), ('abi_version', 2),
                                 ('struct_size', C.sizeof(nav.Scene)-1), ('gold_state', 0),
                                 ('gold_state', 2), ('gold_state', 3), ('goods', 1), ('goods', 2)):
                scene = capped_left120(); setattr(scene, field, value); scene.gold_peak = 200
                self.assertEqual(0, self.candidates(library, scene))
            for kind in (nav.GOLD, nav.ITEM, 7):
                scene = capped_left120(); nav.set_cell(scene, 8, 1, kind)
                self.assertEqual(0, self.candidates(library, scene))
            for index in range(230):
                scene = capped_left120(); scene.protected_cells[index] = 1
                self.assertEqual(0, self.candidates(library, scene))
            scene = capped_left120(); scene.protected_cells[0] = 2
            self.assertEqual(0, self.candidates(library, scene))
            self.assertEqual(0, self.candidates(library, nav.room()), 'a closed room with walls alone is not a cap')
            ordinary = nav.Scene(abi_version=1, struct_size=C.sizeof(nav.Scene), state=2, gold_state=1)
            for point in FLOORS:
                nav.set_cell(ordinary, *point, nav.FLOOR)
            nav.set_cell(ordinary, *MOUTH, nav.DIRT)
            self.assertEqual(0, self.candidates(library, ordinary), 'an ordinary wooden door alone is insufficient')
            self.assertEqual(0, library.ng2_passage_candidates(None))

    def test_unchanged_chooser_uses_four_known_floors_and_stops_before_the_opaque_mouth(self):
        for library in self.libraries.values():
            terrain = capped_left120(); before = bytes(terrain)
            self.assertEqual(32, self.candidates(library, terrain))
            x = y = 0
            for remaining in range(4, 0, -1):
                scene = nav.shifted(terrain, x, y)
                length, choice = self.choose(library, scene, x, y)
                direction, reason, tx, ty, obstacle = choice
                self.assertEqual((remaining, 10, -2-x, -2-y, nav.FLOOR),
                                 (length, reason, tx, ty, obstacle))
                dx, dy = nav.DIRS[direction]
                self.assertEqual(nav.FLOOR, scene.tiles[nav.offset(dx, dy)])
                self.assertEqual(nav.FLOOR, terrain.tiles[nav.offset(x+dx, y+dy)])
                x += dx; y += dy
            self.assertEqual(INBOARD, (x, y))
            self.assertEqual((0, (0, 0, 0, 0, 0)),
                             self.choose(library, nav.shifted(terrain, x, y), x, y))
            self.assertEqual(before, bytes(terrain))

    def test_old_nonzero_masks_win_even_when_the_new_witness_also_matches(self):
        for library in self.libraries.values():
            both = capped_left120()
            for point in lower100.WALLS:
                nav.set_cell(both, *point, nav.DIRT)
            for point in lower100.FLOORS + (lower100.VANTAGE, (-2, 0)):
                nav.set_cell(both, *point, nav.FLOOR)
            self.assertEqual(512, self.candidates(library, both), 'keep old512 exactly, never add new32')
            exterior_floor = capped_left120(); nav.set_cell(exterior_floor, *CAP, nav.FLOOR)
            self.assertEqual(32, self.candidates(library, exterior_floor), 'the existing opaque FLOOR-cap stays32')
            self.assertEqual(64, self.candidates(library, bend117.opaque_bend()))
            for side in (0, 1):
                for k in range(-2, 3):
                    scene, _, _, _ = neck116.capped_neck(side, k)
                    self.assertEqual(1 << (side*5+k+2), self.candidates(library, scene))
                    mouth = (-3, k) if side else (k, -3)
                    self.assertEqual(1 << (side*5+k+2), self.candidates(library, nav.room([mouth])))
            multiple = nav.room([(-2, -3), (2, -3), (-3, 2)])
            self.assertEqual(1 | 16 | 512, self.candidates(library, multiple))


if __name__ == '__main__':
    unittest.main()
