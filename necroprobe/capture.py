"""取得画像を加工前に調べる。非黒画像≠ゲーム認識成功。"""
import hashlib
import io
import math
import time
import warnings

from PIL import Image, UnidentifiedImageError
from .validation import MAX_IMAGE, MAX_PIXELS, ProbeError, b64, number


def inspect_bytes(raw):
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_IMAGE:
        raise ProbeError("image_bytes_limit")
    started = time.monotonic_ns()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                width, height = source.size
                if source.format not in ("JPEG", "PNG") or getattr(source, "n_frames", 1) != 1:
                    raise ProbeError("image_format")
                if min(width, height) <= 0 or max(width, height) > 4096 or width * height > MAX_PIXELS:
                    raise ProbeError("image_dimensions")
                exif_orientation = source.getexif().get(274, 1)
                if type(exif_orientation) is not int or exif_orientation not in range(1, 9):
                    raise ProbeError("image_orientation")
                with Image.open(io.BytesIO(raw)) as integrity:
                    integrity.verify()
                source.load()
                decoded = time.monotonic_ns()
                with source.convert("L") as gray:
                    histogram = gray.histogram()
                maximum = max(index for index, count in enumerate(histogram) if count)
                mean = sum(index * count for index, count in enumerate(histogram)) / (width * height)
                # A conservative *diagnostic* dark flag, never shop absence.
                state = "blank_or_dark" if maximum <= 12 else "decoded_nonblank"
                result = {
                    "image_status": state, "format": source.format,
                    "pixel_width": width, "pixel_height": height,
                    "exif_orientation": exif_orientation,
                    "raw_bytes": len(raw), "max_luma": maximum,
                    "mean_luma": round(mean, 4), "sha256": hashlib.sha256(raw).hexdigest(),
                    "decode_start_ns": started, "decode_end_ns": decoded,
                    "inspect_end_ns": time.monotonic_ns(),
                    "game_state": "not_classified", "input_authorized": False,
                    "geometry_applied": "none",
                }
                return result
    except ProbeError:
        raise
    except (OSError, ValueError, SyntaxError, UnidentifiedImageError,
            Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ProbeError("invalid_image") from None


def inspect_payload(payload):
    if not isinstance(payload, dict):
        raise ProbeError("invalid_capture_payload")
    start = time.monotonic_ns()
    raw = b64(payload.get("data"), MAX_IMAGE)
    end = time.monotonic_ns()
    result = inspect_bytes(raw)
    result.update(base64_start_ns=start, base64_end_ns=end,
                  capture_time_ns=None, source_sequence=None,
                  frame_age_ms=None, freshness_verified=False)
    metadata = {}
    issues = []
    for key in ("pixel_width", "pixel_height", "point_width", "point_height", "scale"):
        if key not in payload:
            continue
        try:
            value = number(payload[key], 0.01, 4096)
            if key.startswith("pixel_") and (type(value) is not int or value != result[key]):
                issues.append(key + "_mismatch")
            metadata[key] = value
        except ProbeError:
            issues.append(key + "_invalid")
    if not all(key in metadata for key in ("point_width", "point_height")):
        issues.append("point_dimensions_missing")
    if "format" in payload and payload["format"] not in ("jpeg", "jpg", "png", "JPEG", "PNG"):
        issues.append("format_invalid")
    elif isinstance(payload.get("format"), str) and payload["format"].upper().replace("JPG", "JPEG") != result["format"]:
        issues.append("format_mismatch")
    result["reported_geometry"] = metadata
    result["metadata_issues"] = issues
    return raw, result


def validate_source_geometry(payload, result, params):
    """Validate NG-G1 metadata against the already decoded, unchanged raster.

    UIImage.size reflects its orientation; never swap axes from the orientation
    enum or use the separate input-side point dimensions as a coordinate map.
    """
    def invalid():
        raise ProbeError("source_geometry_invalid")

    def positive(key, maximum):
        value = payload.get(key)
        try:
            number(value, 0, maximum)
        except ProbeError:
            invalid()
        if value <= 0:
            invalid()
        return value

    def matches(left, right):
        if not math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-9):
            invalid()

    if (payload.get("geometry") != "image_size_v1"
            or payload.get("input_geometry_verified") is not False
            or payload.get("scope") != "screen"
            or payload.get("format") != params["format"]
            or result["format"].lower() != params["format"]
            or result["exif_orientation"] != 1):
        invalid()
    orientation = payload.get("source_orientation")
    if type(orientation) is not int or not 0 <= orientation <= 7:
        invalid()
    metadata = {"geometry": "image_size_v1", "input_geometry_verified": False,
                "source_orientation": orientation, "scope": "screen"}
    for key in ("source_scale", "device_scale", "scale", "requested_scale"):
        metadata[key] = positive(key, 8)
    if metadata["scale"] != params["scale"] or metadata["requested_scale"] != params["scale"]:
        invalid()
    expected = []
    for axis in ("width", "height"):
        # Native source dimensions may exceed the bounded output dimensions.
        for prefix, maximum in (("source_", 32768), ("source_pixel_", 32768),
                                ("image_point_", 4096), ("point_", 4096), ("pixel_", 4096)):
            key = prefix + axis
            metadata[key] = positive(key, maximum)
        source_pixels = metadata["source_" + axis] * metadata["source_scale"]
        matches(metadata["source_pixel_" + axis], source_pixels)
        image_points = source_pixels / metadata["device_scale"]
        matches(metadata["image_point_" + axis], image_points)
        pixels = image_points * metadata["scale"]
        if not 1 <= pixels <= 4096:
            invalid()
        # Swift .rounded() rounds positive halves up; Python round() does not.
        rounded = math.floor(pixels + .5)
        claimed = metadata["pixel_" + axis]
        if claimed != rounded or claimed != result["pixel_" + axis]:
            invalid()
        expected.append(pixels)
    if expected[0] * expected[1] > MAX_PIXELS:
        invalid()
    # inspect_bytes already bounds the decoded integer raster and total pixels.
    result["reported_geometry"] = metadata
    result["metadata_issues"] = []
