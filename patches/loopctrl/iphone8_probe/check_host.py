"""Run the explicitly selected, isolated macOS probe assertion phase.

This checker never builds an IPA, runs a phone, or publishes a release. A compile
failure never counts as the expected behavioral Red.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
BRIDGE_FILES = (
    "assets/NG8CaptureBridge.h", "assets/NG8CaptureBridge.m",
    "tests/NG8CaptureHostTest.h", "tests/NG8CaptureBridgeTests.m",
)
CORE_FILES = ("assets/NG8CaptureProbe.swift", "tests/NG8CaptureProbeTests.swift")
MODE_FILES = ("assets/NG8CaptureMode.swift", "tests/NG8CaptureModeTests.swift")
BRIDGE_CASES = (
    "primary", "three_arg_request", "exact_maximum", "mutable_original", "unprepared",
    "empty", "nil_data", "oversize", "wrong_type", "getter_exception", "daemon_error",
    "throw_retained", "throw_unknown", "sync_send_held", "getter_fence", "consumer_fence",
    "sync_then_throw", "sync_error_then_throw", "api_unavailable", "encoding_unavailable",
    "request_unavailable", "off_main_prepare", "prepare_exception", "never_callback",
    "consumer_exception", "handoff_not_return",
)
CORE_EXPECTED_RED = (
    "CASE qualified_capture\n"
    "FAIL qualified_start_is_accepted\n"
    "FAIL qualified_new_id_one_capture\n"
    "FAIL qualified_capture_ready_keeps_raw_lease\n"
    "FAIL original_jpeg_hash_length_and_exif8_metadata\n"
    "FAIL ready_chunk_exact_original_bytes\n"
    "FAIL capture_never_mints_input_geometry_or_freshness\n"
    "FAIL immutable_original_inspected_and_hashed_once\n"
    "ASSERTIONS_FAILED 7\n"
)


def source_hashes(names):
    result = {}
    for name in names:
        path = HERE / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("invalid_fixture_source")
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def execute(command, output, name, timeout):
    result = subprocess.run(command, capture_output=True, text=True,
                            timeout=timeout, check=False)
    (output / (name + ".stdout.txt")).write_text(result.stdout)
    (output / (name + ".stderr.txt")).write_text(result.stderr)
    return result


def bridge(output, *, expect_red):
    before = source_hashes(BRIDGE_FILES)
    binary = output / "ng8-bridge-tests"
    built = execute([
        "xcrun", "clang", "-fobjc-arc", "-fblocks",
        "-DNG8_CAPTURE_HOST_TEST=1", "-I", str(HERE / "assets"),
        "-I", str(HERE / "tests"), str(HERE / "assets/NG8CaptureBridge.m"),
        str(HERE / "tests/NG8CaptureBridgeTests.m"),
        "-framework", "Foundation", "-framework", "CoreGraphics", "-o", str(binary),
    ], output, "bridge-compile", 120)
    if built.returncode:
        raise ValueError("bridge_compile_failed_not_behavior_red")
    if not expect_red:
        for case in BRIDGE_CASES:
            tested = execute([str(binary), case], output, "bridge-" + case, 30)
            expected = "PASS NG8 bridge " + case + " (real ObjC boundary, daemon fake)"
            if tested.returncode or tested.stdout.strip() != expected or tested.stderr:
                raise ValueError("bridge_green_failed_" + case)
        if source_hashes(BRIDGE_FILES) != before:
            raise ValueError("fixture_source_changed")
        return {"status": "green", "compiled": True, "passed_cases": len(BRIDGE_CASES),
                "source_sha256": before, "callback_return_verified": False}
    tested = execute([str(binary), "primary"], output, "bridge-primary", 30)
    if source_hashes(BRIDGE_FILES) != before:
        raise ValueError("fixture_source_changed")
    expected = "FAIL capture_one_daemon_request"
    if tested.returncode != 1 or tested.stdout.strip() != expected or tested.stderr:
        raise ValueError("expected_bridge_assertion_red_missing")
    return {"status": "expected_red", "compiled": True, "assertion_red": expected,
            "source_sha256": before}


def coordinator_red(output):
    before = source_hashes(CORE_FILES)
    binary = output / "ng8-core-tests"
    built = execute(["xcrun", "swiftc", "-swift-version", "5", "-Onone",
        "-parse-as-library", *(str(HERE / name) for name in CORE_FILES), "-o", str(binary)],
        output, "core-compile", 120)
    if built.returncode:
        raise ValueError("core_compile_failed_not_behavior_red")
    tested = execute([str(binary)], output, "core-qualified", 30)
    if tested.returncode != 1 or tested.stdout != CORE_EXPECTED_RED or tested.stderr:
        raise ValueError("expected_core_assertion_red_missing")
    if source_hashes(CORE_FILES) != before:
        raise ValueError("fixture_source_changed")
    return {"status": "expected_red", "compiled": True, "assertion_failures": 7,
            "assertion_red": "FAIL qualified_new_id_one_capture", "source_sha256": before}


def mode_red(output):
    before = source_hashes(MODE_FILES)
    expected = "FAIL qualified_optin_raw_iphone10_1_selects_capture_only"
    for opt_in in (True, False):
        variant = "dedicated" if opt_in else "ordinary"
        binary = output / ("ng8-mode-" + variant)
        command = ["xcrun", "swiftc", "-swift-version", "5", "-Onone", "-parse-as-library"]
        if opt_in:
            command += ["-D", "NG8_CAPTURE_PROBE_BUILD"]
        built = execute([*command, *(str(HERE / name) for name in MODE_FILES), "-o", str(binary)],
                        output, "mode-" + variant + "-compile", 120)
        if built.returncode:
            raise ValueError("mode_compile_failed_not_behavior_red_" + variant)
        tested = execute([str(binary)], output, "mode-" + variant, 30)
        if tested.returncode != 1 or tested.stdout.strip() != expected or tested.stderr:
            raise ValueError("expected_mode_assertion_red_missing_" + variant)
    if source_hashes(MODE_FILES) != before:
        raise ValueError("fixture_source_changed")
    return {"status": "expected_red", "compiled": True, "variants": 2,
            "assertion_red": expected, "source_sha256": before}


def run(output):
    if sys.platform != "darwin":
        raise ValueError("macos_host_required_not_behavior_red")
    stage = json.loads((HERE / "host-stage.json").read_text())
    if (set(stage) != {"schema", "phase"}
            or stage["schema"] != "ng8-host-stage-v1"
            or stage["phase"] not in ("bridge-red", "bridge-green-components-red")):
        raise ValueError("unsupported_host_stage")
    if stage["phase"] == "bridge-red":
        result = bridge(output, expect_red=True)
        return dict(result, schema="ng8-host-report-v1", phase=stage["phase"],
                    green_implementation=False, device_acceptance="not_run")
    # Independent components use distinct binaries/logs. Inspect every outcome,
    # including a compiler failure; none can be converted into an expected Red.
    operations = {"bridge": lambda: bridge(output, expect_red=False),
                  "coordinator": lambda: coordinator_red(output), "mode": lambda: mode_red(output)}
    contracts = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        pending = {name: executor.submit(operation) for name, operation in operations.items()}
        for name, future in pending.items():
            try:
                contracts[name] = future.result()
            except Exception as error:
                contracts[name] = {"status": "blocked",
                    "reason": str(error) if isinstance(error, ValueError) else type(error).__name__}
    return {"schema": "ng8-host-report-v1", "phase": stage["phase"],
            "status": "blocked" if any(c["status"] == "blocked" for c in contracts.values()) else "pass",
            "contracts": contracts, "green_implementation": False, "input_authorized": False,
            "device_acceptance": "not_run", "scope": "Isolated public host fixtures; no IPA or device"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=True)
    try:
        report = run(output)
    except Exception as error:
        # No credentials, private devices, or raw test material enter this job.
        report = {"schema": "ng8-host-report-v1", "status": "blocked",
                  "reason": str(error) if isinstance(error, ValueError) else type(error).__name__,
                  "device_acceptance": "not_run"}
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, sort_keys=True))
        return 1
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 1 if report.get("status") == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
