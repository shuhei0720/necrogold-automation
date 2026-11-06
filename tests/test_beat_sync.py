"""TEST-016の視覚同期候補。ホスト時計の一致を端末の同期成功としない。"""
import math
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from necroprobe import beat_sync


def hud(remaining, right_shift=0):
    image = Image.new("RGB", (896, 414))
    draw = ImageDraw.Draw(image)
    for side in (-1, 1):
        for index in range(5):
            x = round(446 + side * (remaining + index) * 104)
            if side == 1:
                x += right_shift
            if 20 < x < 876 and not 418 < x < 474:
                draw.rectangle((x - 2, 354, x + 2, 385), fill=(30, 220, 175))
    return image


def observations(count=10, uniform=False, noise=False):
    base = 6_000_000_000_000
    increments = (610, 740, 590, 830, 670, 900, 620, 780, 690, 850, 640)
    offsets = [0]
    for index in range(count - 1):
        offsets.append(offsets[-1] + (900 if uniform else increments[index]) * 1_000_000)
    result = []
    for index, offset in enumerate(offsets):
        q = (0.23 - offset / 520_000_000) % 1
        if noise:
            q = (q + (0.004, -0.006, 0.002)[index % 3]) % 1
        result.append(beat_sync.make_sample(
            {"remaining": q, "spacing_px": 104.0, "center_px": 446.0},
            base + offset - 220_000_000, base + offset + 220_000_000))
    return result


class BeatSyncTests(unittest.TestCase):
    def test_01_hud_wrap_occlusion_and_rejection_without_reformatting(self):
        with patch.object(Image.Image, "resize", side_effect=AssertionError("resize forbidden")), \
             patch.object(Image.Image, "rotate", side_effect=AssertionError("rotate forbidden")), \
             patch.object(Image.Image, "transpose", side_effect=AssertionError("transpose forbidden")):
            for q in (0.01, 0.18, 0.55, 0.99):
                with self.subTest(q=q):
                    feature = beat_sync.extract(hud(q))
                    self.assertIsNotNone(feature)
                    delta = (feature["remaining"] - q + 0.5) % 1 - 0.5
                    self.assertLess(abs(delta), 0.012)
                    self.assertAlmostEqual(104, feature["spacing_px"], delta=1)
                    self.assertAlmostEqual(446, feature["center_px"], delta=1)
            for image in (Image.new("RGB", (414, 896)), Image.new("L", (896, 414)),
                          Image.new("RGB", (896, 414)), hud(0.25, right_shift=32)):
                self.assertIsNone(beat_sync.extract(image))
            left_only = hud(0.25)
            left_only.paste(0, (474, 350, 896, 388))
            self.assertIsNone(beat_sync.extract(left_only))
            self.assertIsNone(beat_sync.extract(None))

    def test_02_samples_preserve_http_bounds_and_reject_invalid_values(self):
        feature = {"remaining": 0.75, "spacing_px": 104, "center_px": 446}
        sample = beat_sync.make_sample(feature, 1_000_000_001, 1_450_000_002)
        self.assertEqual((1_000_000_001, 1_450_000_002),
                         (sample["http_start_ns"], sample["http_end_ns"]))
        self.assertEqual(1_225_000_001, sample["midpoint_ns"])
        self.assertEqual(225_000_000.5, sample["http_half_width_ns"])
        self.assertEqual(0.75, sample["q"])
        for start, end in ((2, 1), (1, 1), (-1, 2), (True, 2), (1, math.inf)):
            with self.assertRaises(ValueError):
                beat_sync.make_sample(feature, start, end)
        for q in (-0.1, 1.0, math.nan, math.inf, True):
            with self.assertRaises(ValueError):
                beat_sync.make_sample(dict(feature, remaining=q), 1, 2)

    def test_03_period_fit_wrap_noise_alias_and_sample_limits(self):
        for count in (8, 10, 12):
            with self.subTest(count=count):
                model = beat_sync.fit(observations(count, noise=True))
                self.assertIsNotNone(model)
                self.assertAlmostEqual(520_000_000, model["period_ns"], delta=1_000_000)
                self.assertLess(model["residual_cycles"], 0.012)
                self.assertFalse(model["device_timing_verified"])
                self.assertFalse(model["dispatch_timing_calibrated"])
                self.assertEqual("http_midpoint_unverified", model["clock_source"])
                self.assertEqual(220_000_000, model["http_half_width_max_ns"])
        self.assertIsNone(beat_sync.fit(observations(uniform=True)))
        self.assertIsNone(beat_sync.fit(observations(7)))
        self.assertIsNone(beat_sync.fit(observations() + observations()[:3]))
        repeated = observations()
        repeated[2] = dict(repeated[1])
        self.assertIsNone(beat_sync.fit(repeated))
        stale = observations()
        for sample in stale:
            sample.update(q=0.25, remaining=0.25)
        self.assertIsNone(beat_sync.fit(stale))
        corrupt = observations()
        corrupt[4] = dict(corrupt[4], q=math.nan)
        self.assertIsNone(beat_sync.fit(corrupt))
        shifted = observations()
        shifted[4].update(q=(shifted[4]["q"] + 0.35) % 1,
                          remaining=(shifted[4]["remaining"] + 0.35) % 1)
        self.assertIsNone(beat_sync.fit(shifted))

    def test_04_future_target_freshness_and_phase_check(self):
        samples = observations()
        model = beat_sync.fit(samples)
        now = samples[-1]["midpoint_ns"] + 230_000_000
        target = beat_sync.next_target(model, now)
        self.assertGreater(target, now + 150_000_000)
        self.assertLessEqual(target, now + 150_000_000 + model["period_ns"])
        self.assertAlmostEqual(0, ((target - model["epoch_ns"]) % model["period_ns"]), delta=1)
        self.assertIsNone(beat_sync.next_target(model, model["last_sample_ns"] + 3_000_000_001))
        self.assertIsNone(beat_sync.next_target(model, model["last_sample_ns"] - 1))
        self.assertIsNone(beat_sync.next_target(model, now, lead_ns=-1))
        self.assertIsNone(beat_sync.next_target(None, now))
        offset = 720_000_000
        current = dict(samples[-1])
        for key in ("http_start_ns", "http_end_ns", "midpoint_ns"):
            current[key] += offset
        current["q"] = current["remaining"] = (samples[-1]["q"] - offset / 520_000_000) % 1
        self.assertTrue(beat_sync.compatible(model, current))
        wrong = dict(current, q=(current["q"] + 0.3) % 1,
                     remaining=(current["remaining"] + 0.3) % 1)
        self.assertFalse(beat_sync.compatible(model, wrong))
        late = dict(current)
        for key in ("http_start_ns", "http_end_ns", "midpoint_ns"):
            late[key] += 4_000_000_000
        self.assertFalse(beat_sync.compatible(model, late))
        self.assertFalse(beat_sync.compatible(None, current))


if __name__ == "__main__":
    unittest.main()
