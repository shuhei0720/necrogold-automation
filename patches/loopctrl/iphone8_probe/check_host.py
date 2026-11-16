"""Run the explicitly selected, isolated macOS probe assertion phase.

This checker never builds an IPA, runs a phone, or publishes a release. A compile
failure never counts as the expected behavioral Red.
"""
import argparse
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


def run(output):
    if sys.platform != "darwin":
        raise ValueError("macos_host_required_not_behavior_red")
    stage = json.loads((HERE / "host-stage.json").read_text())
    if (set(stage) != {"schema", "phase"}
            or stage["schema"] != "ng8-host-stage-v1"
            or stage["phase"] != "bridge-red"):
        raise ValueError("unsupported_host_stage")
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
    tested = execute([str(binary), "primary"], output, "bridge-primary", 30)
    if source_hashes(BRIDGE_FILES) != before:
        raise ValueError("fixture_source_changed")
    expected = "FAIL capture_one_daemon_request"
    if tested.returncode != 1 or tested.stdout.strip() != expected or tested.stderr:
        raise ValueError("expected_bridge_assertion_red_missing")
    return {
        "schema": "ng8-host-report-v1", "phase": stage["phase"],
        "compiled": True, "assertion_red": expected, "source_sha256": before,
        "scope": "Actual NG8 ObjC stub and fake daemon; no device or IPA",
        "green_implementation": False, "device_acceptance": "not_run",
    }


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
