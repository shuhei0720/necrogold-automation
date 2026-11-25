"""TEST120 child capture1: observe a split-roof FLOOR mouth from inside.

Public sparse maps encode the marked observations, never phone pixels or
hidden gold. The unmodified chooser may use only three currently known
FLOOR steps; the disconnected mouth and UNKNOWN inboard remain unreachable.
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
from tests import test_native_navigation120 as cap120
from tests import test_native_shadow_passage094 as shadow094

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'patches/loopctrl/ngg2'
BASELINE_SHA256 = '6b4faeb6adbee72c60e0ad58f3e253dffd40254b6b17e9bfb24d92e6ae8c3d97'
MOUTH, INBOARD, VANTAGE = (-3, -2), (-2, -2), (-2, -1)
WALLS = ((-4, -3), (-3, -3), (1, -3), (2, -3), (3, -3)) + tuple((-3, y) for y in range(-1, 4))
FLOORS = (MOUTH, (-2, -1), (-2, 0), (-1, -2), (-1, -1), (-1, 0), (0, -1), (0, 0))
DARK = (INBOARD, (-4, -2), (-4, -1), (-2, -3), (-1, -3), (0, -3))


def split_roof_mouth121(wall_kind=nav.DIRT, complete_room=False):
    scene = nav.Scene(abi_version=1, struct_size=C.sizeof(nav.Scene), state=2, gold_state=1)
    if complete_room:
        for y in range(-2, 3):
            for x in range(-2, 3):
                nav.set_cell(scene, x, y, nav.FLOOR)
        nav.set_cell(scene, *INBOARD, 0)
    for point in WALLS:
        nav.set_cell(scene, *point, wall_kind)
    for point in FLOORS:
        nav.set_cell(scene, *point, nav.FLOOR)
    return scene


class NativeSplitRoofMouth121Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        override = os.environ.get('NECRO_NAV121_RED_SOURCE')
        source = Path(override) if override else CORE/'NG2Navigation.c'
        if override and hashlib.sha256(source.read_bytes()).hexdigest() != BASELINE_SHA256:
            raise AssertionError('TEST121 Red requires exact shipped TEST120 Navigation')
        cls.directory = tempfile.TemporaryDirectory(prefix='split-roof-mouth121-')
        cls.libraries = {}
        for profile, flags in (('unchanged_o0', ['-O0']),
                               ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            target = Path(cls.directory.name)/(profile+'.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror', '-pedantic',
                            '-fPIC', '-shared', '-I'+str(CORE), str(source), '-lm', '-o', str(target)], check=True)
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
        answer = library.ng2_passage_candidates(C.byref(scene))
        self.assertEqual(before, bytes(scene), 'a candidate cannot relabel any observed or dark cell')
        return answer

    def choose(self, library, scene, x=0, y=0):
        before = bytes(scene); out = nav.Decision(99, 99, 99, 99, 99)
        length = library.ng2_choose_passage(C.byref(scene), x, y, *MOUTH, C.byref(out))
        self.assertEqual(before, bytes(scene))
        return length, tuple(getattr(out, name) for name, _ in out._fields_)

    def test_split_roof_observed_mouth_adds_only_its_fixed_left_bit5(self):
        for profile, library in self.libraries.items():
            for kind in (nav.DIRT, nav.STONE):
                for complete in (False, True):
                    with self.subTest(profile=profile, kind=kind, complete=complete):
                        scene = split_roof_mouth121(kind, complete)
                        self.assertEqual(32, self.candidates(library, scene),
                                         'the observed FLOOR mouth and independent roof ends merit an inside view')
                        self.assertEqual(nav.FLOOR, scene.tiles[nav.offset(*MOUTH)])
                        self.assertEqual((0,)*len(DARK), tuple(scene.tiles[nav.offset(*p)] for p in DARK))

    def test_each_roof_end_cap_and_lower_boundary_is_independent_required_support(self):
        for library in self.libraries.values():
            for point in WALLS:
                for kind in (0, nav.FLOOR, nav.GOLD, nav.DOOR, nav.ITEM):
                    with self.subTest(point=point, kind=kind):
                        scene = split_roof_mouth121(); nav.set_cell(scene, *point, kind)
                        expected = 128 if point == (-3, 0) and kind == nav.FLOOR else 0
                        self.assertEqual(expected, self.candidates(library, scene))
                mixed = split_roof_mouth121(); nav.set_cell(mixed, *point, nav.STONE)
                self.assertEqual(32, self.candidates(library, mixed))
            displaced = split_roof_mouth121(); nav.set_cell(displaced, -4, -3, 0)
            nav.set_cell(displaced, -5, -3, nav.DIRT)
            self.assertEqual(0, self.candidates(library, displaced))

    def test_all_positive_inside_floors_and_the_mouth_are_required(self):
        for library in self.libraries.values():
            for point in FLOORS:
                for kind in (0, nav.GOLD, nav.STONE, nav.DIRT, nav.DOOR, nav.ITEM):
                    with self.subTest(point=point, kind=kind):
                        scene = split_roof_mouth121(); nav.set_cell(scene, *point, kind)
                        self.assertEqual(0, self.candidates(library, scene))
            isolated = split_roof_mouth121()
            for point in ((-1, 0), (0, -1)):
                nav.set_cell(isolated, *point, 0)
            self.assertEqual(0, self.candidates(library, isolated))
            self.assertEqual((0, (0, 0, 0, 0, 0)), self.choose(library, isolated))

    def test_dark_cells_remain_unknown_without_erasing_existing_positive_mouths(self):
        for library in self.libraries.values():
            for point in DARK:
                for kind in (nav.FLOOR, nav.GOLD, nav.STONE, nav.DIRT, nav.DOOR, nav.ITEM):
                    with self.subTest(point=point, kind=kind):
                        scene = split_roof_mouth121(); nav.set_cell(scene, *point, kind)
                        expected = 32 if ((point in (INBOARD, (-4, -2)) and kind == nav.FLOOR)
                            or (point == (-2, -3) and kind in (nav.DIRT, nav.STONE))) else 0
                        self.assertEqual(expected, self.candidates(library, scene))

    def test_state_goods_gold_item_all_protection_and_black_or_door_only_are_refused(self):
        for library in self.libraries.values():
            for field, value in (('state', 0), ('state', 1), ('state', 3), ('abi_version', 2),
                                 ('struct_size', C.sizeof(nav.Scene)-1), ('gold_state', 0),
                                 ('gold_state', 2), ('gold_state', 3), ('goods', 1), ('goods', 2)):
                scene = split_roof_mouth121(); setattr(scene, field, value); scene.gold_peak = 200
                self.assertEqual(0, self.candidates(library, scene))
            for kind in (nav.GOLD, nav.ITEM, 7):
                scene = split_roof_mouth121(); nav.set_cell(scene, 8, 1, kind)
                self.assertEqual(0, self.candidates(library, scene))
            for index in range(230):
                scene = split_roof_mouth121(); scene.protected_cells[index] = 1
                self.assertEqual(0, self.candidates(library, scene))
            scene = split_roof_mouth121(); scene.protected_cells[0] = 2
            self.assertEqual(0, self.candidates(library, scene))
            for points in ((MOUTH,), WALLS, tuple(p for p in FLOORS if p != MOUTH), ()):
                scene = nav.Scene(abi_version=1, struct_size=C.sizeof(nav.Scene), state=2, gold_state=1)
                nav.set_cell(scene, 0, 0, nav.FLOOR)
                for point in points:
                    nav.set_cell(scene, *point, nav.DIRT if point in WALLS else nav.FLOOR)
                self.assertEqual(0, self.candidates(library, scene), 'a single evidence family is insufficient')
            self.assertEqual(0, library.ng2_passage_candidates(None))

    def test_unchanged_chooser_stops_after_three_floors_before_unknown_inboard_and_mouth(self):
        for library in self.libraries.values():
            terrain = split_roof_mouth121(); before = bytes(terrain); x = y = 0
            self.assertEqual(32, self.candidates(library, terrain))
            for remaining in range(3, 0, -1):
                view = nav.shifted(terrain, x, y)
                length, choice = self.choose(library, view, x, y)
                direction, reason, tx, ty, obstacle = choice
                self.assertEqual((remaining, 10, -2-x, -1-y, nav.FLOOR),
                                 (length, reason, tx, ty, obstacle))
                dx, dy = nav.DIRS[direction]
                self.assertEqual(nav.FLOOR, view.tiles[nav.offset(dx, dy)])
                self.assertEqual(nav.FLOOR, terrain.tiles[nav.offset(x+dx, y+dy)])
                x += dx; y += dy
            self.assertEqual(VANTAGE, (x, y))
            self.assertEqual((0, (0, 0, 0, 0, 0)),
                             self.choose(library, nav.shifted(terrain, x, y), x, y))
            self.assertEqual(0, terrain.tiles[nav.offset(*INBOARD)])
            self.assertEqual(nav.FLOOR, terrain.tiles[nav.offset(*MOUTH)])
            self.assertEqual(before, bytes(terrain))

    def test_legacy_nonzero_including_120_cap_and_simultaneous_lower_fringe_wins_exactly(self):
        for library in self.libraries.values():
            both = split_roof_mouth121()
            for point in lower100.WALLS:
                nav.set_cell(both, *point, nav.DIRT)
            for point in lower100.FLOORS + (lower100.VANTAGE, (-2, 0)):
                nav.set_cell(both, *point, nav.FLOOR)
            self.assertEqual(512, self.candidates(library, both), 'preserve old512, do not add new32')
            self.assertEqual(32, self.candidates(library, cap120.capped_left120()))
            complete = split_roof_mouth121(complete_room=True)
            nav.set_cell(complete, 2, -3, nav.FLOOR)
            self.assertEqual(16, self.candidates(library, complete), 'the old upper-right mouth keeps its identity')
            multiple = nav.room([(-2, -3), (2, -3), (-3, 2)])
            self.assertEqual(1 | 16 | 512, self.candidates(library, multiple))

    def test_fixed_coordinates_do_not_alias_new_directions_and_keep_old_transposed_shape(self):
        for library in self.libraries.values():
            for operation, expected in ((lambda x, y: (-x, y), 0), (lambda x, y: (x, -y), 0),
                                        (lambda x, y: (y, x), 1), (lambda x, y: (x+1, y), 0)):
                transformed = shadow094.remap(split_roof_mouth121(), operation)
                self.assertEqual(expected, self.candidates(library, transformed),
                                 'an already supported upper mouth is not a new left-bit alias')


if __name__ == '__main__':
    unittest.main()
