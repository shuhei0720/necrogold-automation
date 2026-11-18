"""TEST115 capture25: observe a FLOOR neck with a supported outside cap.

The source is a known calibration image, not an unseen shop-positive label.
These sparse procedural maps authorize a bounded view over observed FLOOR;
the dark flanks never become FLOOR and the cap never becomes a shop proof.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_passage_navigation072 as nav


def capped_neck(side=0, k=1, flank=1):
    scene = nav.Scene(abi_version=1, struct_size=C.sizeof(nav.Scene), state=2, gold_state=1)
    mx, my = (-3, k) if side else (k, -3)
    dx, dy = (-1, 0) if side else (0, -1)
    tx, ty = -dy, dx
    for n in range(min(0, k), max(0, k) + 1):
        nav.set_cell(scene, 0 if side else n, n if side else 0, nav.FLOOR)
    for n in range(1, 5):
        nav.set_cell(scene, -n if side else k, k if side else -n, nav.FLOOR)
    boundary = [n for n in range(-3, 4) if abs(n-k) > 1][:3]
    for n in boundary:
        nav.set_cell(scene, -3 if side else n, n if side else -3, nav.DIRT)
    walls = ((mx+2*dx, my+2*dy),
             (mx+dx+flank*tx, my+dy+flank*ty),
             (mx+2*dx+flank*tx, my+2*dy+flank*ty))
    for point in walls:
        nav.set_cell(scene, *point, nav.STONE)
    return scene, (mx, my), walls, boundary


class NativeCappedNeck116Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        nav.NativePassageNavigation072Tests.setUpClass.__func__(cls)

    tearDownClass = classmethod(nav.NativePassageNavigation072Tests.tearDownClass.__func__)

    def candidates(self, lib, scene):
        original = bytes(scene)
        mask = lib.ng2_passage_candidates(C.byref(scene))
        self.assertEqual(original, bytes(scene), 'candidate detection cannot promote dark cells')
        return mask

    def test_capped_observed_necks_keep_the_existing_world_bits_in_both_axes(self):
        for lib in self.libraries.values():
            for side in (0, 1):
                for k in range(-2, 3):
                    for flank in (-1, 1):
                        with self.subTest(side=side, k=k, flank=flank):
                            scene, _, _, _ = capped_neck(side, k, flank)
                            self.assertEqual(1 << (side*5+k+2), self.candidates(lib, scene),
                                'observed FLOOR and an independent outer wall corner merit a closer view')

    def test_cap_and_both_lateral_wall_segments_are_independent_required_evidence(self):
        for lib in self.libraries.values():
            for side in (0, 1):
                scene, _, walls, _ = capped_neck(side)
                for point in walls:
                    for tile in (0, nav.FLOOR, nav.GOLD, nav.DOOR, nav.ITEM):
                        with self.subTest(side=side, point=point, tile=tile):
                            broken = deepcopy(scene); nav.set_cell(broken, *point, tile)
                            self.assertEqual(0, self.candidates(lib, broken))
                    broken = deepcopy(scene); nav.set_cell(broken, *point, nav.STONE, protected=1)
                    self.assertEqual(0, self.candidates(lib, broken))

    def test_outer_corner_cannot_replace_three_independent_room_boundary_walls(self):
        for lib in self.libraries.values():
            for side in (0, 1):
                scene, _, _, boundary = capped_neck(side)
                for n in boundary:
                    broken = deepcopy(scene)
                    nav.set_cell(broken, -3 if side else n, n if side else -3, 0)
                    self.assertEqual(0, self.candidates(lib, broken))

    def test_both_observed_neck_cells_and_reachable_inboard_are_required(self):
        for lib in self.libraries.values():
            for side in (0, 1):
                scene, (mx, my), _, _ = capped_neck(side)
                dx, dy = (-1, 0) if side else (0, -1)
                for point in ((mx, my), (mx+dx, my+dy), (mx-dx, my-dy)):
                    for tile in (0, nav.GOLD, nav.STONE, nav.DIRT, nav.DOOR, nav.ITEM):
                        broken = deepcopy(scene); nav.set_cell(broken, *point, tile)
                        self.assertEqual(0, self.candidates(lib, broken), (side, point, tile))
                    broken = deepcopy(scene); nav.set_cell(broken, *point, nav.FLOOR, protected=1)
                    self.assertEqual(0, self.candidates(lib, broken))

    def test_neck_refuses_goods_other_screens_and_observed_nonfloor_flanks(self):
        for lib in self.libraries.values():
            for side in (0, 1):
                scene, (mx, my), _, _ = capped_neck(side)
                for field, value in (('state', 0), ('state', 1), ('gold_state', 0),
                                     ('gold_state', 3), ('goods', 1), ('goods', 2)):
                    broken = deepcopy(scene); setattr(broken, field, value)
                    self.assertEqual(0, self.candidates(lib, broken))
                tx, ty = (0, -1) if side else (1, 0)
                for sign in (-1, 1):
                    for tile in (nav.FLOOR, nav.GOLD, nav.DOOR, nav.ITEM):
                        broken = deepcopy(scene); nav.set_cell(broken, mx+sign*tx, my+sign*ty, tile)
                        self.assertEqual(0, self.candidates(lib, broken))

    def test_unchanged_chooser_walks_only_known_floor_and_stops_at_the_outside(self):
        for lib in self.libraries.values():
            for side in (0, 1):
                scene, mouth, _, _ = capped_neck(side)
                self.assertEqual(1 << (side*5+3), self.candidates(lib, scene))
                x = y = count = 0
                while True:
                    view = nav.shifted(scene, x, y)
                    original = bytes(view); choice = nav.Decision()
                    length = lib.ng2_choose_passage(C.byref(view), x, y, *mouth, C.byref(choice))
                    self.assertEqual(original, bytes(view))
                    if not length:
                        break
                    self.assertLess(count, 5)
                    self.assertEqual((10, nav.FLOOR), (choice.reason, choice.obstacle))
                    dx, dy = nav.DIRS[choice.direction]
                    self.assertEqual(nav.FLOOR, view.tiles[nav.offset(dx, dy)])
                    self.assertEqual(nav.FLOOR, scene.tiles[nav.offset(x+dx, y+dy)])
                    x += dx; y += dy; count += 1
                self.assertEqual(5, count)
                self.assertEqual((-4, 1) if side else (1, -4), (x, y))


if __name__ == '__main__':
    unittest.main()
