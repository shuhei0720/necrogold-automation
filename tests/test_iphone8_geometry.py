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

    def test_out_of_source_footer_guard_remains_explicitly_unknown(self):
        # The old crop really includes two unobserved columns. A different,
        # fully observed UI map must not make that crop observed retroactively.
        footer = geometry._ui_copy(Image.new("RGB", geometry.SOURCE_POINTS),
            Image.new("RGB", (896, 414)), "old_footer", (565, 357, 669, 375),
            (752, 396, 856, 414), Image.Resampling.BILINEAR)
        self.assertEqual(36, footer["unknown_required_domain_pixels"])
        self.assertFalse(footer["entire_required_domain_observed"])

    def test_footer_margin_copies_real_pixels_without_assuming_black(self):
        source = Image.new("RGB", geometry.SOURCE_PIXELS)
        for y in range(714, 750):
            for x in range(1330, 1334):
                source.putpixel((x, y), (30*(x-1329), y-700, 200))
        raster = geometry.adapt_g1(source)
        maps = {item["name"]: item for item in raster.provenance["ui_copies"]}
        self.assertIn("footer_guard", maps)
        for name in ("footer_body", "footer_guard"):
            self.assertEqual(0, maps[name]["unknown_required_domain_pixels"])
            self.assertTrue(maps[name]["entire_required_domain_observed"])
        image = Image.frombytes("RGBA", (896, 414), raster.rgba)
        for y in range(18):
            for x in range(4):
                self.assertEqual((*source.getpixel((1330+x, 715+2*y)), 255),
                                 image.getpixel((852+x, 396+y)))
        hidden = geometry.adapt_g1(source, occlusions=((665, 357, 667, 375),))
        guard = next(item for item in hidden.provenance["ui_copies"]
                     if item["name"] == "footer_guard")
        self.assertEqual(72, guard["required_pixels_in_declared_occlusion"])
        self.assertFalse(guard["entire_required_domain_observed"])
        self.assertFalse(raster.provenance["input_authorized"])
        self.assertFalse(raster.provenance["profile_qualified"])

    def test_bilinear_coverage_uses_actual_nonzero_taps(self):
        # 8x6 -> 5x3 samples final source indices x6/7, y4/5. Its bounding
        # rectangle touches the edge, but every nonzero kernel tap is observed.
        copy = geometry._ui_copy(Image.new("RGB", (8, 6)),
            Image.new("RGB", (5, 3)), "edge", (0, 0, 8, 6), (0, 0, 5, 3),
            Image.Resampling.BILINEAR)
        self.assertEqual(0, copy["unknown_required_domain_pixels"])
        self.assertTrue(copy["entire_required_domain_observed"])
        self.assertEqual([0, 0, 8, 6], copy["source_sample_support_xyxy"])
        outside = geometry._ui_copy(Image.new("RGB", (8, 6)),
            Image.new("RGB", (5, 3)), "clamped_edge", (0, 0, 9, 6),
            (0, 0, 5, 3), Image.Resampling.BILINEAR)
        self.assertEqual(3, outside["unknown_required_domain_pixels"])
        self.assertFalse(outside["entire_required_domain_observed"])
        # Independent nonglyph probes fix Pillow's pixel-center convention:
        # final x is6.7, so impulses at x6/x7 have weights .3/.7.
        gradient = Image.new("F", (8, 6))
        gradient.putdata([float(x) for _ in range(6) for x in range(8)])
        transform = (1.6, 0, 0, 0, 2, 0)
        sample = gradient.transform((5, 3), Image.Transform.AFFINE, transform,
                                    Image.Resampling.BILINEAR)
        self.assertAlmostEqual(6.7, sample.getpixel((4, 2)), places=5)
        for point, weight in (((6, 4), .15), ((7, 4), .35), ((5, 5), 0)):
            impulse = Image.new("F", (8, 6))
            impulse.putpixel(point, 1)
            sample = impulse.transform((5, 3), Image.Transform.AFFINE, transform,
                                       Image.Resampling.BILINEAR)
            self.assertAlmostEqual(weight, sample.getpixel((4, 2)), places=6)

    def test_resize_box_has_half_open_support_and_negative_edge_is_unknown(self):
        try:
            taps = geometry._axis_taps(.5, 2, 1, Image.Resampling.BOX)
        except ValueError:
            self.fail("proper BOX reduction support is missing")
        self.assertEqual([(1, 2)], taps)
        self.assertEqual([(-1, 0)], geometry._axis_taps(-.6, 2, 1, Image.Resampling.BOX))
        # Independent Pillow impulses distinguish the exact half-open edge:
        # source centre.5 is excluded, source centres1.5/2.5 have weight.5.
        for x, expected in ((0, 0), (1, .5), (2, .5), (3, 0)):
            source = Image.new("F", (4, 1))
            source.putpixel((x, 0), 1)
            sampled = source.resize((1, 1), Image.Resampling.BOX, box=(.5, 0, 2.5, 1))
            self.assertEqual(expected, sampled.getpixel((0, 0)))

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
