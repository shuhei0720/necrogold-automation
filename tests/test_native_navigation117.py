"""TEST116 capture128: a wall-separated exterior FLOOR L merits a closer view.

The private source was classified once and its unchanged Scene was retained.
These public maps describe only the observed spatial witnesses, without phone
pixels or a copied Scene. A candidate authorizes three known FLOOR steps and
stops at the opaque boundary; it does not classify a shop or open a door.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_passage_navigation072 as nav

MOUTH = (-3, -1)
VANTAGE = (-2, -1)
FLOORS = ((0, 0), (-1, 0), (-2, 0), (0, -1), (-1, -1), VANTAGE,
          (-4, -1), (-4, -2), (-5, -2))
WALLS = ((-3, -1), (-3, -2), (-3, -3), (-2, -3), (-1, -3), (-5, -1))


def opaque_bend(wall_kind=nav.DIRT, complete_room=False):
    scene = nav.room() if complete_room else nav.Scene(
        abi_version=1, struct_size=C.sizeof(nav.Scene), state=2, gold_state=1)
    for point in FLOORS:
        nav.set_cell(scene, *point, nav.FLOOR)
    for point in WALLS:
        nav.set_cell(scene, *point, wall_kind)
    return scene


class NativeOpaqueFringe117Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        nav.NativePassageNavigation072Tests.setUpClass.__func__(cls)

    tearDownClass = classmethod(nav.NativePassageNavigation072Tests.tearDownClass.__func__)

    def candidates(self, lib, scene):
        original = bytes(scene)
        answer = lib.ng2_passage_candidates(C.byref(scene))
        self.assertEqual(original, bytes(scene), 'an observation hypothesis cannot relabel the opaque edge')
        return answer

    def test_observed_floor_bend_adds_only_its_fixed_left_mouth(self):
        for profile, lib in self.libraries.items():
            for wall_kind in (nav.DIRT, nav.STONE):
                with self.subTest(profile=profile, wall_kind=wall_kind):
                    scene = opaque_bend(wall_kind)
                    self.assertEqual(1 << 6, self.candidates(lib, scene),
                                     'the wall-separated exterior FLOOR L needs an observed inboard view')
                    self.assertEqual(wall_kind, scene.tiles[nav.offset(*MOUTH)])
                    self.assertEqual(0, scene.tiles[nav.offset(-3, 0)])

    def test_complete_independent_room_does_not_change_the_fixed_view_or_open_wall(self):
        for profile, lib in self.libraries.items():
            for wall_kind in (nav.DIRT, nav.STONE):
                with self.subTest(profile=profile, wall_kind=wall_kind):
                    scene = opaque_bend(wall_kind, complete_room=True)
                    self.assertEqual(1 << 6, self.candidates(lib, scene))
                    self.assertEqual(wall_kind, scene.tiles[nav.offset(*MOUTH)])
                    self.assertEqual(0, scene.tiles[nav.offset(-4, 0)])

    def test_each_external_floor_cap_boundary_and_roof_witness_is_required(self):
        for profile, lib in self.libraries.items():
            source = opaque_bend()
            required_floors = ((-4, -1), (-4, -2), (-5, -2), VANTAGE)
            for point in WALLS + required_floors:
                forbidden = (0, nav.FLOOR, nav.GOLD, nav.DOOR, nav.ITEM) if point in WALLS else (
                    0, nav.GOLD, nav.STONE, nav.DIRT, nav.DOOR, nav.ITEM)
                for kind in forbidden:
                    with self.subTest(profile=profile, point=point, kind=kind):
                        changed = deepcopy(source)
                        nav.set_cell(changed, *point, kind)
                        self.assertEqual(0, self.candidates(lib, changed))
            for kind in (nav.FLOOR, nav.DOOR):
                changed = deepcopy(source)
                nav.set_cell(changed, -3, 0, kind)
                self.assertEqual(0, self.candidates(lib, changed) & (1 << 6),
                                 'a different lower flank cannot claim this fixed inboard view')
            connected = deepcopy(source)
            nav.set_cell(connected, -3, 0, nav.FLOOR)
            nav.set_cell(connected, -4, 0, nav.FLOOR)
            self.assertEqual(1 << 7, self.candidates(lib, connected),
                             'the already connected normal mouth keeps its original bit without the new hypothesis')
            for point in ((-1, -1), (0, -1), (-1, 0), (0, 0)):
                changed = deepcopy(source)
                nav.set_cell(changed, *point, 0)
                self.assertEqual(0, self.candidates(lib, changed))

    def test_ui_goods_positive_gold_and_protected_cells_never_gain_authority(self):
        for profile, lib in self.libraries.items():
            for field, value in (('state', 0), ('state', 1), ('gold_state', 0),
                                 ('gold_state', 2), ('gold_state', 3), ('goods', 1), ('goods', 2)):
                with self.subTest(profile=profile, field=field, value=value):
                    changed = opaque_bend()
                    setattr(changed, field, value)
                    self.assertEqual(0, self.candidates(lib, changed))
            for point in ((0, 0), (-1, 0), (-2, 0), VANTAGE, (-4, -1), (-5, -1), (3, 2)):
                changed = opaque_bend()
                changed.protected_cells[nav.offset(*point)] = 1
                self.assertEqual(0, self.candidates(lib, changed))
            for point in ((2, 2), (-4, -2)):
                for kind in (nav.GOLD, nav.ITEM):
                    changed = opaque_bend()
                    nav.set_cell(changed, *point, kind)
                    self.assertEqual(0, self.candidates(lib, changed))

    def test_existing_chooser_uses_three_known_floor_steps_then_stops_at_the_wall(self):
        for profile, lib in self.libraries.items():
            with self.subTest(profile=profile):
                terrain = opaque_bend()
                self.assertEqual(1 << 6, self.candidates(lib, terrain))
                x = y = 0
                directions = []
                while True:
                    scene = nav.shifted(terrain, x, y)
                    original = bytes(scene)
                    out = nav.Decision()
                    count = lib.ng2_choose_passage(C.byref(scene), x, y, *MOUTH, C.byref(out))
                    self.assertEqual(original, bytes(scene))
                    if count == 0:
                        break
                    self.assertLess(len(directions), 3)
                    self.assertEqual((10, nav.FLOOR), (out.reason, out.obstacle))
                    dx, dy = nav.DIRS[out.direction]
                    self.assertEqual(nav.FLOOR, scene.tiles[nav.offset(dx, dy)])
                    self.assertEqual(nav.FLOOR, terrain.tiles[nav.offset(x + dx, y + dy)])
                    directions.append(out.direction)
                    x += dx
                    y += dy
                self.assertEqual([1, 1, 3], directions)
                self.assertEqual(VANTAGE, (x, y))
                self.assertEqual(nav.DIRT, terrain.tiles[nav.offset(*MOUTH)])
                self.assertEqual(0, terrain.tiles[nav.offset(-3, 0)])


if __name__ == '__main__':
    unittest.main()
