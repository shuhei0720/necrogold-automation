"""Read-only NEW8 G1 geometry preview; never an input/native-RAW profile.

The existing production C is compiled without edits. This host diagnostic owns
only geometry and coverage, and has no device, network, or input operation.
Dynamic overlays are explicit source-point occlusions. For the observed
All Zones instruction block, use --occlusion 259,151,405,269; do not infer its
absence from elapsed time. A C FLOOR here is a diagnostic value, never input
qualification. UI copies require every actual nonzero resampling tap to be
observed; the footer margin copies real source pixels without painting a guard.
"""
from dataclasses import dataclass
from pathlib import Path
import argparse
import ctypes as C
import hashlib
import io
import json
import math
import subprocess
import tempfile

from PIL import Image, ImageDraw

WIDTH, HEIGHT = 896, 414
SOURCE_POINTS = (667, 375)
SOURCE_PIXELS = (1334, 750)
WORLD_OFFSET = (114.5, 19.5)
ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "patches/loopctrl/ngg2"
PROFILE = "iphone8-g1-geometry-preview-v1"
FOOTER_UI_MAPS = (
    ("footer_body", (565, 357, 665, 375), (752, 396, 852, 414), Image.Resampling.BILINEAR),
    ("footer_guard", (665, 357, 667, 375), (852, 396, 856, 414), Image.Resampling.NEAREST),
)
# Conservative envelopes measured in NEW8 G1 point space, not old11 masks.
# Dynamic notifications/instruction text must be supplied as extra occlusions.
HUD_BOXES = (
    ("inventory_and_external_indicator", (0, 0, 86, 140)),
    ("health", (436, 0, 581, 60)),
    ("currency", (594, 8, 648, 78)),
    ("pause", (315, 6, 351, 42)),
    ("minimap", (576, 291, 627, 336)),
    ("beat_band", (0, 312, 667, 350)),
    ("beat_heart", (308, 292, 360, 365)),
    ("bottom_labels", (0, 350, 667, 375)),
    ("left_upper_control", (0, 148, 87, 153)),
    ("right_upper_control", (578, 148, 667, 153)),
    ("left_lower_control", (0, 220, 87, 225)),
    ("right_lower_control", (578, 220, 667, 225)),
)


def _overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _occlusions(boxes):
    checked = []
    if len(boxes) > 16:
        raise ValueError("too_many_occlusions")
    for box in boxes:
        if len(box) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in box):
            raise ValueError("invalid_occlusion")
        x0, y0, x1, y1 = box
        if not (0 <= x0 < x1 <= 667 and 0 <= y0 < y1 <= 375):
            raise ValueError("invalid_occlusion")
        checked.append(tuple(box))
    return tuple(checked)


def world_cell_coverage(x, y, occlusions=()):
    """Source observations for a canonical material window, never permission."""
    if type(x) is not int or type(y) is not int or not (-11 <= x <= 11 and -5 <= y <= 4):
        raise ValueError("cell_out_of_range")
    cx, cy = 448 + 36*x, 207 + 36*y
    box = (cx-12-WORLD_OFFSET[0], cy-12-WORLD_OFFSET[1],
           cx+13-WORLD_OFFSET[0], cy+13-WORLD_OFFSET[1])
    occlusions = _occlusions(occlusions)
    # A half-point source halo covers the 2x->1x BOX support at the boundary.
    support = (box[0]-.5, box[1]-.5, box[2]+.5, box[3]+.5)
    fov = support[0] >= 0 and support[1] >= 0 and support[2] <= 667 and support[3] <= 375
    reasons = [] if fov else ["outside_source_fov"]
    reasons += ["source_hud:" + name for name, hud in HUD_BOXES if _overlap(support, hud)]
    if any(_overlap(support, rect) for rect in occlusions):
        reasons.append("declared_occlusion")
    return {"observed": not reasons, "full_source_fov": fov,
            "source_point_box": list(box), "source_support_box": list(support), "reasons": reasons}


@dataclass
class GeometryRaster:
    rgba: bytes
    provenance: dict
    cell_coverage: list


def _axis_taps(start, scale, count, resample):
    """Pillow affine pixel centers, including only nonzero kernel support."""
    taps = []
    for index in range(count):
        center = start+(index+.5)*scale
        if resample == Image.Resampling.NEAREST:
            taps.append((math.floor(center),))
            continue
        coordinate = center-.5
        lower = math.floor(coordinate)
        if resample not in (Image.Resampling.BILINEAR, Image.Resampling.BICUBIC):
            raise ValueError("unsupported_ui_resampler")
        if coordinate == lower:
            taps.append((lower,))
        elif resample == Image.Resampling.BILINEAR:
            taps.append((lower, lower+1))
        else:
            taps.append((lower-1, lower, lower+1, lower+2))
    return taps


def _ui_copy(source, canvas, name, source_box, target_box, resample, occlusions=()):
    x0, y0, x1, y1 = source_box
    left, top, right, bottom = target_box
    width, height = right-left, bottom-top
    sx, sy = (x1-x0)/width, (y1-y0)/height
    # Apply the affine to the full observed rectangle, including all template
    # zero positions. Never crop active ink and paint its surrounding guard.
    patch = source.transform((width, height), Image.Transform.AFFINE,
                             (sx, 0, x0, 0, sy, y0), resample)
    canvas.paste(patch, (left, top))
    xtaps = _axis_taps(x0, sx, width, resample)
    ytaps = _axis_taps(y0, sy, height, resample)
    # A crop touching the image edge need not use any out-of-image sample.
    # Conversely, a valid center with an outside nonzero tap is not observed;
    # Pillow's edge clamp cannot turn it into observed evidence.
    unknown = sum(not (0 <= xs[0] and xs[-1] < source.width and
                       0 <= ys[0] and ys[-1] < source.height)
                  for ys in ytaps for xs in xtaps)
    occluded = sum(any(_overlap((xs[0], ys[0], xs[-1]+1, ys[-1]+1), box)
                       for box in occlusions) for ys in ytaps for xs in xtaps)
    support = [min(xs[0] for xs in xtaps), min(ys[0] for ys in ytaps),
               max(xs[-1] for xs in xtaps)+1, max(ys[-1] for ys in ytaps)+1]
    return {"name": name, "source_diagnostic_xyxy": list(source_box),
            "destination_canonical_xyxy": list(target_box),
            "inverse_affine": [sx, 0, x0, 0, sy, y0],
            "resampler": "Pillow_"+Image.Resampling(resample).name,
            "support_model": "pillow_affine_nonzero_kernel_taps",
            "source_sample_support_xyxy": support,
            "unknown_required_domain_pixels": unknown,
            "required_pixels_in_declared_occlusion": occluded,
            "entire_required_domain_observed": unknown == 0 and occluded == 0,
            "interpolation_support_within_source": unknown == 0}


def adapt_g1(source, ui="floor", occlusions=()):
    """Return a diagnostic-only raster and source validity; no state inference."""
    if source.size != SOURCE_PIXELS:
        raise ValueError("unsupported_g1_geometry")
    if ui not in ("floor", "pause"):
        raise ValueError("unknown_ui_geometry")
    occlusions = _occlusions(occlusions)
    source = source.convert("RGB")
    world = source.copy()
    painter = ImageDraw.Draw(world)
    for _, box in HUD_BOXES:
        painter.rectangle((math.floor(box[0]*2), math.floor(box[1]*2),
                           math.ceil(box[2]*2)-1, math.ceil(box[3]*2)-1), fill=0)
    for box in occlusions:
        painter.rectangle((math.floor(box[0]*2), math.floor(box[1]*2),
                           math.ceil(box[2]*2)-1, math.ceil(box[3]*2)-1), fill=0)
    # This pixel phase is a G1 hypothesis, not the production CoreGraphics map.
    padded = Image.new("RGB", (1792, 828))
    padded.paste(world, (229, 39))
    canvas = padded.resize((WIDTH, HEIGHT), Image.Resampling.BOX)
    coverage = []
    painter = ImageDraw.Draw(canvas)
    for y in range(-5, 5):
        for x in range(-11, 12):
            cell = {"x": x, "y": y, **world_cell_coverage(x, y, occlusions)}
            coverage.append(cell)
            if not cell["observed"]:
                cx, cy = 448+36*x, 207+36*y
                # Full 36px footprint, including the material lower bands.
                # This is unknown exclusion, never a fabricated observation.
                painter.rectangle((cx-18, cy-18, cx+17, cy+17), fill=0)
    copies = []
    if ui == "floor":
        logical = source.resize(SOURCE_POINTS, Image.Resampling.BOX)
        # Preserve the existing pause preview phase. Footer body retains its
        # point dimensions; only the observed terminal whitespace is widened.
        # Copy the real margin even when bright/occluded, never a painted zero.
        item = _ui_copy(logical, canvas, "pause_icon", (315, 6, 351, 42),
                        (429, 6, 465, 42), Image.Resampling.BILINEAR, occlusions)
        item["source_point_xyxy"] = item.pop("source_diagnostic_xyxy")
        item["source_diagnostic_xyxy"] = [v*2 for v in item["source_point_xyxy"]]
        item["inverse_affine_source_units"] = "logical_points"
        copies.append(item)
        for name, source_box, target_box, resample in FOOTER_UI_MAPS:
            item = _ui_copy(source, canvas, name, tuple(v*2 for v in source_box),
                            target_box, resample,
                            tuple(tuple(v*2 for v in box) for box in occlusions))
            item["source_point_xyxy"] = list(source_box)
            item["inverse_affine_source_units"] = "diagnostic_pixels"
            copies.append(item)
        bottom = Image.new("RGB", (1792, 828))
        bottom.paste(source, (229, 78))
        bottom = bottom.resize((WIDTH, HEIGHT), Image.Resampling.BOX)
        canvas.paste(bottom.crop((114, 350, 782, 389)), (114, 350))
        copies.append({"name": "beat", "source_diagnostic_xyxy": [0, 622, 1334, 700],
                       "destination_canonical_xyxy": [114.5, 350, 781.5, 389],
                       "entire_required_domain_observed": False,
                       "actual_source_band_observed": not any(_overlap((0, 311, 667, 350), box) for box in occlusions),
                       "note": "Only actual FOV is observed; outside horizontal FOV is unknown."})
    else:
        # One measured known-capture Continue geometry, not an accepted menu
        # profile. Restart is deliberately left unmatched rather than painted.
        copies.append(_ui_copy(source, canvas, "continue",
            (551.4417721518987, 186.85, 782.9065099457505, 241.11356589147286),
            (384, 104, 512, 132), Image.Resampling.BICUBIC,
            tuple(tuple(v*2 for v in box) for box in occlusions)))
    return GeometryRaster(canvas.convert("RGBA").tobytes(), {
        "profile": PROFILE, "evidence_kind": "g1_reencoded_diagnostic",
        "input_authorized": False, "automation_ready": False, "profile_qualified": False,
        "source_pixels": list(SOURCE_PIXELS), "declared_source_points": list(SOURCE_POINTS),
        "declared_uiimage_scale": 2, "declared_uiimage_orientation": 2,
        "uiimage_orientation_is_not_exif": True, "world_offset_points": list(WORLD_OFFSET),
        "world_fov_canonical_xyxy": [114.5, 19.5, 781.5, 394.5],
        "source_hud_boxes": [{"name": n, "point_xyxy": list(b)} for n, b in HUD_BOXES],
        "declared_occlusions": [list(b) for b in occlusions], "ui_copies": copies,
        "dynamic_overlay_inventory_qualified": False,
        "native_raw_coregraphics_motion_and_input_unaccepted": True,
    }, coverage)


class _Scene(C.Structure):
    _fields_ = [(k, C.c_uint32) for k in ("abi_version", "struct_size")] + [
        (k, C.c_int32) for k in ("state", "restart_label", "gold_state", "gold_peak", "goods")] + [
        ("tiles", C.c_uint8*230), ("protected_cells", C.c_uint8*230),
        ("signature", C.c_uint8*23296), ("fingerprint", C.c_uint8*48),
        ("beat_valid", C.c_int32), ("beat_remaining", C.c_double),
        ("beat_spacing", C.c_double), ("beat_center", C.c_double)]


def native_hashes():
    return {name: hashlib.sha256((CORE/name).read_bytes()).hexdigest()
            for name in ("NG2Perception.c", "NG2Core.h", "NG2Templates.h")}


class ProductionPerception:
    """Exactly the public production entry. No internal component bypass."""
    def __enter__(self):
        self.directory = tempfile.TemporaryDirectory(prefix="new8-same-c-")
        library = Path(self.directory.name)/"perception.so"
        self.hashes = native_hashes()
        self.flags = ["-std=c99", "-O2", "-fno-fast-math", "-ffp-contract=off",
                      "-Wall", "-Wextra", "-Werror", "-fPIC", "-shared"]
        try:
            subprocess.run(["cc", *self.flags, str(CORE/"NG2Perception.c"), "-lm", "-o", str(library)],
                           check=True, capture_output=True, timeout=30)
            self.library = C.CDLL(str(library))
            self.library.ng2_analyze_rgba.argtypes = [C.c_void_p, C.c_size_t, C.c_size_t, C.POINTER(_Scene)]
            self.library.ng2_analyze_rgba.restype = C.c_int
            return self
        except BaseException:
            self.directory.cleanup()
            raise

    def analyze(self, raster):
        result = _Scene()
        rc = self.library.ng2_analyze_rgba(raster.rgba, len(raster.rgba), WIDTH*4, C.byref(result))
        if rc or result.abi_version != 1 or result.struct_size != C.sizeof(_Scene):
            raise ValueError("production_c_analysis_failed")
        if self.hashes != native_hashes():
            raise ValueError("production_source_changed")
        # Coverage only removes known labels; it cannot turn UNKNOWN into a
        # FLOOR, a beat, or a state. C UNKNOWN is kept without another analyzer.
        cells = [{"x": cell["x"], "y": cell["y"], "kind": int(result.tiles[i]) if cell["observed"] and result.state == 2 else 0,
                  "observed": cell["observed"], "reasons": cell["reasons"]}
                 for i, cell in enumerate(raster.cell_coverage)]
        return {"schema": "new8-same-c-diagnostic-v1", **raster.provenance,
                "input_authorized": False, "automation_ready": False, "profile_qualified": False,
                "native_source_sha256": self.hashes, "compiler_flags": self.flags,
                "native_scene": {"state": result.state, "restart_label": result.restart_label,
                    "gold_state": result.gold_state, "gold_peak": result.gold_peak, "goods": result.goods,
                    "beat_valid": result.beat_valid, "beat_remaining": result.beat_remaining,
                    "beat_spacing": result.beat_spacing, "beat_center": result.beat_center,
                    "tiles": list(result.tiles), "protected_cells": list(result.protected_cells)},
                "world_cells": cells, "cell_coverage": raster.cell_coverage,
                "known_cell_count": sum(cell["kind"] != 0 for cell in cells),
                "classification_fraction_is_not_accuracy": True,
                "state_unknown_was_not_bypassed": result.state != 0 or not any(cell["kind"] for cell in cells)}

    def __exit__(self, *_):
        self.directory.cleanup()


def _outside_repo(path):
    path = Path(path).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError:
        return path
    raise ValueError("private_output_must_be_outside_repository")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--ui", choices=("floor", "pause"), required=True)
    parser.add_argument("--occlusion", action="append", default=[], help="Observed overlay x0,y0,x1,y1 in source points")
    parser.add_argument("--output", type=_outside_repo, required=True)
    args = parser.parse_args(argv)
    occlusions = [tuple(float(v) for v in entry.split(",")) for entry in args.occlusion]
    with args.capture.open("rb") as capture:
        encoded = capture.read(8*1024*1024+1)
    if not 0 < len(encoded) <= 8*1024*1024:
        raise ValueError("encoded_size")
    with Image.open(io.BytesIO(encoded)) as source:
        orientation = source.getexif().get(274)
        if source.format != "JPEG" or orientation not in (None, 1):
            raise ValueError("unsupported_g1_encoding_or_exif")
        raster = adapt_g1(source, args.ui, occlusions)
    with ProductionPerception() as engine:
        report = engine.analyze(raster)
    report["capture_sha256"] = hashlib.sha256(encoded).hexdigest()
    report["file_exif_orientation"] = orientation
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as destination:
        destination.write(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({"input_authorized": False, "state": report["native_scene"]["state"],
                      "beat_valid": report["native_scene"]["beat_valid"]}))


if __name__ == "__main__":
    main()
