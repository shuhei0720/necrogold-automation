"""Measured NEW8 geometry exclusions; no private image fixture is bundled."""
import unittest
from pathlib import Path

from PIL import Image

from tools import iphone8_geometry as geometry


class IPhone8GeometryTests(unittest.TestCase):
    def test_received_partial_top_windows_are_unknown(self):
        # A measured NEW8 frame has component-only FLOOR at these cells. Their
        # y15..40 canonical windows cross the actual FOV top19.5 by4.5px.
        # Black padding alone therefore cannot establish UNKNOWN.
        for cell in ((2, -5), (4, -5)):
            with self.subTest(cell=cell):
                observed = geometry.world_cell_coverage(*cell)
                self.assertFalse(observed["observed"])
                self.assertIn("outside_source_fov", observed["reasons"])

    def test_actual_new8_health_domain_cannot_be_world_floor(self):
        observed = geometry.world_cell_coverage(5, -4)
        self.assertTrue(observed["full_source_fov"])
        self.assertFalse(observed["observed"])
        self.assertIn("source_hud:health", observed["reasons"])

    def test_declared_notification_removes_world_observation(self):
        before = geometry.world_cell_coverage(2, -2)
        after = geometry.world_cell_coverage(2, -2, ((156, 8, 511, 140),))
        self.assertTrue(before["observed"])
        self.assertFalse(after["observed"])
        self.assertIn("declared_occlusion", after["reasons"])

    def test_mixed_or_unknown_geometry_is_rejected(self):
        for size in ((896, 414), (828, 1792), (750, 1334), (1334, 749)):
            with self.subTest(size=size), self.assertRaisesRegex(ValueError, "unsupported_g1_geometry"):
                geometry.adapt_g1(Image.new("RGB", size))

    def test_footer_negative_guard_remains_explicitly_unknown(self):
        raster = geometry.adapt_g1(Image.new("RGB", geometry.SOURCE_PIXELS))
        footer = next(item for item in raster.provenance["ui_copies"] if item["name"] == "footer")
        self.assertEqual(36, footer["unknown_required_domain_pixels"])
        self.assertFalse(footer["entire_required_domain_observed"])
        self.assertFalse(raster.provenance["input_authorized"])
        self.assertFalse(raster.provenance["profile_qualified"])

    def test_notification_cannot_be_reported_as_observed_pause_ui(self):
        raster = geometry.adapt_g1(Image.new("RGB", geometry.SOURCE_PIXELS),
                                   occlusions=((156, 8, 511, 84),))
        pause = next(item for item in raster.provenance["ui_copies"] if item["name"] == "pause_icon")
        self.assertGreater(pause["required_pixels_in_declared_occlusion"], 0)
        self.assertFalse(pause["entire_required_domain_observed"])

    def test_masked_real_ui_pixels_are_not_copied_into_world(self):
        source = Image.new("RGB", geometry.SOURCE_PIXELS)
        # A bright sample wholly inside measured source health HUD must not
        # become terrain just because its centered position misses old11 HUD.
        from PIL import ImageDraw
        ImageDraw.Draw(source).rectangle((900, 40, 950, 80), fill=(255, 255, 255))
        raster = geometry.adapt_g1(source)
        image = Image.frombytes("RGBA", (896, 414), raster.rgba)
        self.assertEqual((0, 0, 0, 255), image.getpixel((577, 49)))

    def test_public_c_unknown_has_no_component_bypass_or_input(self):
        raster = geometry.adapt_g1(Image.new("RGB", geometry.SOURCE_PIXELS))
        before = geometry.native_hashes()
        with geometry.ProductionPerception() as engine:
            result = engine.analyze(raster)
        self.assertEqual(0, result["native_scene"]["state"])
        self.assertEqual(0, result["known_cell_count"])
        self.assertTrue(result["state_unknown_was_not_bypassed"])
        self.assertFalse(result["input_authorized"])
        self.assertFalse(result["automation_ready"])
        self.assertEqual(before, geometry.native_hashes())

    def test_analyzer_cannot_authorize_input_from_mutated_provenance(self):
        raster = geometry.adapt_g1(Image.new("RGB", geometry.SOURCE_PIXELS))
        raster.provenance.update(input_authorized=True, automation_ready=True, profile_qualified=True)
        with geometry.ProductionPerception() as engine:
            result = engine.analyze(raster)
        for flag in ("input_authorized", "automation_ready", "profile_qualified"):
            self.assertFalse(result[flag], flag)

    def test_private_outputs_cannot_be_created_in_repository(self):
        with self.assertRaisesRegex(ValueError, "outside_repository"):
            geometry._outside_repo(Path(geometry.ROOT)/"capture-analysis.json")


if __name__ == "__main__":
    unittest.main()
