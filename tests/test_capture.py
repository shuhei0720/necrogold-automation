import base64
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image
from necroprobe.capture import inspect_bytes, inspect_payload
from necroprobe.validation import MAX_IMAGE, ProbeError

ROOT = Path(__file__).resolve().parents[1]


def picture(size=(20, 40), color=(255, 255, 255), format="PNG", exif=None):
    with io.BytesIO() as stream:
        image = Image.new("RGB", size, color)
        image.save(stream, format, **({"exif": exif} if exif else {}))
        return stream.getvalue()


def payload(raw=None):
    return {"data": base64.b64encode(raw or picture()).decode(), "point_width": 414, "point_height": 896}


class CaptureTests(unittest.TestCase):
    def test_black_is_not_a_valid_game_frame(self):
        result = inspect_bytes(picture((414, 896), (0, 0, 0)))
        self.assertEqual("blank_or_dark", result["image_status"])

    def test_recorded_failed_frame_is_black_before_geometry(self):
        result = inspect_bytes((ROOT / "evidence/start-failed.jpg").read_bytes())
        self.assertEqual("blank_or_dark", result["image_status"])
        self.assertEqual((414, 896), (result["pixel_width"], result["pixel_height"]))
        self.assertEqual("none", result["geometry_applied"])

    def test_recorded_pause_is_nonblank_but_not_input_permission(self):
        result = inspect_bytes((ROOT / "analysis/manual-video-2/frames/002000-pause.jpg").read_bytes())
        self.assertEqual("decoded_nonblank", result["image_status"])
        self.assertFalse(result["input_authorized"])
        self.assertEqual("not_classified", result["game_state"])
        self.assertEqual((1108, 512), (result["pixel_width"], result["pixel_height"]))

    def test_portrait_and_exif_not_stretched_or_rotated(self):
        exif = Image.Exif()
        exif[274] = 6
        raw = picture((40, 80), exif=exif)
        result = inspect_bytes(raw)
        self.assertEqual((40, 80, 6), (result["pixel_width"], result["pixel_height"], result["exif_orientation"]))

    def test_dimensions_match_file_not_untrusted_metadata(self):
        encoded = payload()
        encoded.update(pixel_width=800, pixel_height=600)
        _, result = inspect_payload(encoded)
        self.assertEqual(20, result["pixel_width"])
        self.assertIn("pixel_width_mismatch", result["metadata_issues"])
        self.assertIsNone(result["capture_time_ns"])
        self.assertIsNone(result["frame_age_ms"])

    def test_metadata_nan_bool_and_missing_points(self):
        for value in (float("nan"), float("inf"), True, -1, "414"):
            with self.subTest(value=repr(value)):
                data = payload()
                data["point_width"] = value
                _, result = inspect_payload(data)
                self.assertIn("point_width_invalid", result["metadata_issues"])

    def test_invalid_empty_truncated_and_oversized_images(self):
        for raw in (b"", b"bad", picture()[:20], b"x" * (MAX_IMAGE + 1)):
            with self.subTest(size=len(raw)), self.assertRaises(ProbeError):
                inspect_bytes(raw)

    def test_dimensions_rejected_before_decode(self):
        for size in ((4097, 1), (3000, 3000)):
            with self.subTest(size=size), self.assertRaisesRegex(ProbeError, "image_dimensions"):
                inspect_bytes(picture(size))

    def test_dimension_limit_allows_4096(self):
        self.assertEqual(4096, inspect_bytes(picture((4096, 1)))["pixel_width"])

    def test_unsupported_format(self):
        with self.assertRaisesRegex(ProbeError, "image_format"):
            inspect_bytes(picture(format="GIF"))

    def test_invalid_base64_is_rejected(self):
        with self.assertRaisesRegex(ProbeError, "invalid_base64"):
            inspect_payload({"data": "!!!!"})

    def test_crc_corruption_and_missing_iend_are_rejected(self):
        original = picture()
        raw = bytearray(original)
        index = 8
        while raw[index + 4:index + 8] != b"IDAT":
            index += int.from_bytes(raw[index:index + 4], "big") + 12
        crc = index + 8 + int.from_bytes(raw[index:index + 4], "big")
        raw[crc] ^= 1
        for damaged in (bytes(raw), original[:-12]):
            with self.subTest(size=len(damaged)), self.assertRaises(ProbeError):
                inspect_bytes(damaged)
