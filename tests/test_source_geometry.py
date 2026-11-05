"""NG-G1 opt-in contract; synthetic images are not device acceptance."""
import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from PIL import Image
from necroprobe import __main__ as cli
from necroprobe.capture import inspect_bytes, inspect_payload
from necroprobe.crypto import Crypto
from necroprobe.protocol import Client, GAME, RpcReply
from necroprobe.session import collect, new_report, VARIANTS
from necroprobe.validation import ProbeError
from test_capture import picture


CAPABILITY = "screenshot_image_geometry_v1"
GEOMETRY = "image_size_v1"


def geometry_payload(params, size=(80, 40), source_scale=1, device_scale=2):
    image_points = tuple(value * source_scale / device_scale for value in size)
    pixels = tuple(math.floor(value * params["scale"] + .5) for value in image_points)
    raw = picture(pixels, format=params["format"].upper())
    return raw, {
        "data": base64.b64encode(raw).decode(), "format": params["format"],
        "geometry": GEOMETRY, "input_geometry_verified": False, "scope": "screen",
        "pixel_width": float(pixels[0]), "pixel_height": float(pixels[1]),
        "point_width": 414, "point_height": 896,
        "image_point_width": image_points[0], "image_point_height": image_points[1],
        "source_width": size[0], "source_height": size[1], "source_scale": source_scale,
        "source_pixel_width": size[0] * source_scale, "source_pixel_height": size[1] * source_scale,
        "source_orientation": 3, "device_scale": device_scale,
        "scale": params["scale"], "requested_scale": params["scale"],
        "device_name": "PRIVATE", "hint": "PRIVATE", "unknown": "PRIVATE",
    }


class GeometryClient:
    timeout = 1
    allow_launch = True
    source_geometry = True

    def __init__(self, caps=None, *, info_error=None, mutate=None, size=(80, 40), source_scale=1, device_scale=2):
        self.caps = [CAPABILITY] if caps is None else caps
        self.info_error = info_error
        self.mutate = mutate
        self.size, self.source_scale, self.device_scale = size, source_scale, device_scale
        self.calls, self.raws = [], []

    def call(self, method, params=None, timeout=None):
        self.calls.append((method, params))
        if method == "device_info":
            if self.info_error:
                raise ProbeError(self.info_error)
            return RpcReply({"capabilities": self.caps, "system": {"foreground_app": GAME}}, {})
        if method == "launch_app":
            return RpcReply({}, {})
        raw, result = geometry_payload(params, self.size, self.source_scale, self.device_scale)
        self.raws.append(raw)
        if self.mutate:
            self.mutate(result)
        return RpcReply(result, {"request_start_ns": time.monotonic_ns()})


class SourceGeometryTests(unittest.TestCase):
    def run_probe(self, client, count=3):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            report = new_report(count, time.monotonic_ns())
            collect(client, report, folder, time.monotonic_ns() + 5_000_000_000)
            files = {p.name: p.read_bytes() for p in Path(folder).iterdir() if p.suffix in (".png", ".jpg")}
            self.assertEqual(report, json.loads((Path(folder) / "report.json").read_text()))
            return report, files

    def test_capability_must_be_exact_list_member_before_launch_or_capture(self):
        for caps in ([], ["screenshot_image_geometry_v10"], CAPABILITY, {CAPABILITY: True}, [True], [[CAPABILITY]]):
            with self.subTest(caps=caps):
                client = GeometryClient(caps)
                report, files = self.run_probe(client)
                self.assertEqual([("device_info", None)], client.calls)
                self.assertEqual("source_geometry_capability_missing", report["stop_reason"])
                self.assertEqual(3, report["summary"]["not_started"])
                self.assertEqual({}, files)

    def test_initial_info_failure_is_fatal_without_implicit_legacy_fallback(self):
        for error in ("connection_error", "rpc_deadline", "rpc_error", "response_mac_mismatch"):
            with self.subTest(error=error):
                client = GeometryClient(info_error=error)
                report, _ = self.run_probe(client)
                self.assertEqual([("device_info", None)], client.calls)
                self.assertEqual(error, report["stop_reason"])

    def test_advertising_old_server_ignoring_geometry_stops_after_first_capture(self):
        def ignore(result):
            result.pop("geometry")
        client = GeometryClient(mutate=ignore)
        report, files = self.run_probe(client)
        self.assertEqual("source_geometry_invalid", report["stop_reason"])
        self.assertEqual(1, report["summary"]["errors"])
        self.assertEqual(2, report["summary"]["not_started"])
        self.assertEqual({}, files)
        self.assertEqual(["device_info", "launch_app", "screenshot"], [m for m, _ in client.calls])

    def test_all_formats_scales_preserve_raw_bytes_and_decode_once(self):
        client = GeometryClient()
        with patch("necroprobe.session.inspect_payload", wraps=inspect_payload) as inspect, \
             patch("necroprobe.capture.inspect_bytes", wraps=inspect_bytes) as decode, \
             patch.object(Image.Image, "save", side_effect=Image.Image.save, autospec=True) as save:
            report, files = self.run_probe(client)
        self.assertEqual(3, report["summary"]["complete"])
        self.assertEqual(3, inspect.call_count)
        self.assertEqual(3, decode.call_count, "Each raw payload must be decoded only once")
        self.assertEqual(3, save.call_count, "Only fixture generation may encode; the client must not")
        self.assertEqual([dict(p, geometry=GEOMETRY) for _, p in VARIANTS], [p for m, p in client.calls if m == "screenshot"])
        self.assertEqual([CAPABILITY], report["events"][0]["observation"]["advertised_known_capabilities"])
        self.assertNotIn("PRIVATE", json.dumps(report))
        for row, raw in zip(report["rows"], client.raws):
            self.assertEqual(raw, files[row["raw_file"]])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row["image"]["sha256"])
            image = row["image"]
            self.assertEqual(GEOMETRY, image["reported_geometry"]["geometry"])
            self.assertFalse(image["reported_geometry"]["input_geometry_verified"])
            self.assertEqual(414, image["reported_geometry"]["point_width"])
            self.assertEqual(40, image["reported_geometry"]["image_point_width"])
            self.assertEqual([], image["metadata_issues"])
            self.assertEqual("none", image["geometry_applied"])
            self.assertFalse(image["input_authorized"])

    def test_portrait_source_scale_and_half_up_rounding(self):
        for size, source_scale, device_scale in (((80, 161), 1, 2), ((40, 80), 2, 2), ((120, 60), 1, 3)):
            with self.subTest(size=size, source_scale=source_scale):
                report, _ = self.run_probe(GeometryClient(size=size, source_scale=source_scale, device_scale=device_scale))
                self.assertEqual(3, report["summary"]["complete"])
                expected = tuple(math.floor(value * source_scale / device_scale + .5) for value in size)
                image = report["rows"][0]["image"]
                self.assertEqual(expected, (image["pixel_width"], image["pixel_height"]))

    def test_native_source_can_exceed_output_limit_but_unrounded_output_cannot(self):
        for source_width, accepted in ((6000, True), (8192, True), (8192.4, False)):
            with self.subTest(source_width=source_width):
                client = GeometryClient(size=(source_width, 2))
                report, _ = self.run_probe(client, count=1)
                if accepted:
                    self.assertEqual(1, report["summary"]["complete"])
                else:
                    self.assertEqual("source_geometry_invalid", report["stop_reason"])

    def test_tolerated_image_point_noise_cannot_change_expected_half_up_output(self):
        def changed_half(result):
            result.update(image_point_width=40.499999999, pixel_width=40,
                          data=base64.b64encode(picture((40, 20), format="JPEG")).decode())
        report, files = self.run_probe(GeometryClient(size=(81, 40), mutate=changed_half), count=1)
        self.assertEqual("source_geometry_invalid", report.get("stop_reason"))
        self.assertEqual({}, files)

    def test_all_uiimage_orientation_values_are_reported_without_transform(self):
        for orientation in range(8):
            with self.subTest(orientation=orientation):
                client = GeometryClient(mutate=lambda result: result.update(source_orientation=orientation))
                report, files = self.run_probe(client, count=1)
                image = report["rows"][0]["image"]
                self.assertEqual(orientation, image["reported_geometry"]["source_orientation"])
                self.assertEqual((40, 20), (image["pixel_width"], image["pixel_height"]))
                self.assertEqual(client.raws[0], next(iter(files.values())))

    def test_new_mode_prints_decoded_dimensions_and_legacy_output_stays_unchanged(self):
        for new_mode in (True, False):
            with self.subTest(new_mode=new_mode), tempfile.TemporaryDirectory() as folder:
                client = GeometryClient()
                client.source_geometry = new_mode
                client.allow_launch = False
                report = new_report(1, time.monotonic_ns())
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    collect(client, report, folder, time.monotonic_ns() + 5_000_000_000)
                expected = "1/1 jpeg_scale1: decoded_nonblank" + (" 40x20" if new_mode else "") + "\n"
                self.assertEqual(expected, output.getvalue())

    def test_unexpected_output_exif_orientation_stops_without_transpose(self):
        # The source UIImage orientation may vary, but the renderer emits .up.
        for orientation in (2, 6, 8):
            with self.subTest(orientation=orientation):
                exif = Image.Exif()
                exif[274] = orientation
                raw = picture((40, 20), format="JPEG", exif=exif)
                client = GeometryClient(mutate=lambda result: result.update(data=base64.b64encode(raw).decode()))
                report, files = self.run_probe(client, count=1)
                self.assertEqual("source_geometry_invalid", report.get("stop_reason"))
                self.assertEqual({}, files)

    def test_missing_geometry_fields_are_not_successes(self):
        _, valid = geometry_payload({"format": "jpeg", "scale": 1})
        for key in set(valid) - {"data", "device_name", "hint", "unknown"}:
            with self.subTest(key=key):
                report, files = self.run_probe(GeometryClient(mutate=lambda result: result.pop(key)))
                self.assertEqual("source_geometry_invalid", report["stop_reason"])
                self.assertEqual({}, files)

    def test_invalid_metadata_and_raw_format_or_dimensions_stop(self):
        invalid = {
            "geometry": (None, "legacy", True), "input_geometry_verified": (True, 0, None),
            "scope": ("app", "PRIVATE"), "pixel_width": (41, 40.5, True),
            "pixel_height": (21, 20.5), "format": ("png", "PRIVATE", None),
            "point_width": (float("nan"), 0, 4097, True), "point_height": (float("inf"), -1),
            "image_point_width": (41, 0, float("inf")), "image_point_height": (21, False),
            "source_width": (81, float("nan"), 1e100), "source_height": (41, 0),
            "source_scale": (0, True, 9), "source_pixel_width": (81, -1),
            "source_pixel_height": (41, float("inf")), "source_orientation": (-1, 8, 3.0, True, "3"),
            "device_scale": (0, 3, 9), "scale": (2, True, float("nan")), "requested_scale": (2, None),
            "data": (base64.b64encode(picture((41, 20), format="JPEG")).decode(),
                     base64.b64encode(picture((40, 20), format="PNG")).decode()),
        }
        for key, values in invalid.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    report, files = self.run_probe(GeometryClient(mutate=lambda result: result.update({key: value})))
                    self.assertEqual("source_geometry_invalid", report["stop_reason"])
                    self.assertEqual({}, files)

    def test_legacy_default_keeps_requests_and_nonfatal_metadata_warnings(self):
        client = GeometryClient(caps=[], mutate=lambda result: result.pop("geometry"))
        client.source_geometry = False
        report, _ = self.run_probe(client)
        self.assertEqual(3, report["summary"]["complete"])
        self.assertEqual([p for _, p in VARIANTS], [p for m, p in client.calls if m == "screenshot"])
        self.assertIn("pixel_width_mismatch", report["rows"][0]["image"]["metadata_issues"])


class SourceGeometryProtocolTests(unittest.TestCase):
    def test_exact_geometry_is_allowed_and_all_other_values_rejected(self):
        client = Client(None, crypto=Crypto(native=False))
        params = {"format": "jpeg", "scale": 1, "geometry": GEOMETRY}
        client._validate("screenshot", params)
        for geometry in (None, "", "legacy", "image_size_v2", True, 1, [], {}):
            with self.subTest(geometry=geometry), self.assertRaises(ProbeError):
                client._validate("screenshot", dict(params, geometry=geometry))
        for extra in ({"bundle_id": GAME}, {"x": 1}, {"rotate": 90}):
            with self.subTest(extra=extra), self.assertRaises(ProbeError):
                client._validate("screenshot", dict(params, **extra))

    def test_flag_reaches_parent_command_worker_and_client(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            args = cli.parser().parse_args(["capture", "--source-geometry", "--output", folder, "--samples", "3"])
            with patch.object(cli, "supervise", return_value="fixture_stop") as supervise:
                cli.run_capture(args)
            command = supervise.call_args.args[0]
            self.assertEqual(1, command.count("--source-geometry"))
            worker_args = cli.parser().parse_args(command[3:])
            with patch.object(cli, "load_pairing", return_value=(b"key", "tok")), \
                 patch.object(cli, "Crypto") as crypto, patch.object(cli, "OwnedRpcTimer") as timer, \
                 patch.object(cli, "Client") as client, patch.object(cli, "collect"):
                crypto.return_value.engine = "python"
                timer.return_value.diagnostics.return_value = {}
                cli.worker(worker_args)
            self.assertIs(True, client.call_args.kwargs["source_geometry"])

    def test_helper_accepts_new_known_capability_without_private_names(self):
        path = Path(__file__).resolve().parents[1] / "tools/inspect_capture_source.py"
        spec = importlib.util.spec_from_file_location("geometry_source_info", path)
        source = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(source)
        result = source.sanitize({"capabilities": [CAPABILITY, "PRIVATE", CAPABILITY]})
        self.assertEqual([CAPABILITY], result["known_capabilities"])
        self.assertNotIn("PRIVATE", str(result))
