"""Run the explicitly selected, isolated macOS probe assertion phase.

This checker never builds an IPA, runs a phone, or publishes a release. A compile
failure never counts as the expected behavioral Red.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


HERE = Path(__file__).resolve().parent
BRIDGE_FILES = (
    "assets/NG8CaptureBridge.h", "assets/NG8CaptureBridge.m",
    "tests/NG8CaptureHostTest.h", "tests/NG8CaptureBridgeTests.m",
)
CORE_FILES = ("assets/NG8CaptureProbe.swift", "tests/NG8CaptureProbeTests.swift")
CORE_EXPECTATIONS = "tests/coordinator-red-expectations.json"
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
    if result.returncode and name.endswith("-compile"):
        # These jobs compile committed public fixture source, never device data.
        print(json.dumps({"public_fixture_compile_failure": name,
            "stderr_tail": result.stderr[-6000:], "stdout_tail": result.stdout[-1000:]}), flush=True)
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
                # Only named assertions and the fixture's closed diagnostic
                # object enter the job log; no arbitrary exception/data dump.
                details = {"bridge_failure_case": case, "return_code": tested.returncode,
                    "assertions": re.findall(r"^FAIL ([a-z0-9_]+)$", tested.stdout, re.MULTILINE),
                    "stderr_nonempty": bool(tested.stderr), "source_sha256": before}
                for line in tested.stderr.splitlines():
                    try:
                        diagnostic = json.loads(line)
                    except ValueError:
                        continue
                    if (isinstance(diagnostic, dict)
                            and set(diagnostic) == {"observed_error_code", "reply_calls", "drain_calls", "send_calls"}
                            and diagnostic["observed_error_code"] in {"none", "api_unavailable", "request_unavailable",
                                "prepare_unavailable", "request_exception", "reply_exception", "capture_failed",
                                "bytes_invalid", "not_implemented", "unrecognized_fixed_code"}
                            and all(type(diagnostic[k]) is int and 0 <= diagnostic[k] <= 128
                                    for k in ("reply_calls", "drain_calls", "send_calls"))):
                        details["fixed_fixture_diagnostic"] = diagnostic
                print(json.dumps(details, sort_keys=True), flush=True)
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


def coordinator_red(output, *, expanded=False):
    names = (*CORE_FILES, CORE_EXPECTATIONS) if expanded else CORE_FILES
    before = source_hashes(names)
    if expanded:
        expectations = json.loads((HERE / CORE_EXPECTATIONS).read_text())
        if (set(expectations) != {"schema", "execution_status", "default_selector", "source_path",
                "fixture_path", "core_sha256", "fixture_sha256", "selectors"}
                or expectations["schema"] != "ng8-coordinator-stub-red-expectations-v1"
                or expectations["execution_status"] != "additional_cases_not_run"
                or expectations["default_selector"] != "qualified_capture"
                or expectations["source_path"] != "patches/loopctrl/iphone8_probe/" + CORE_FILES[0]
                or expectations["fixture_path"] != "patches/loopctrl/iphone8_probe/" + CORE_FILES[1]
                or expectations["core_sha256"] != before[CORE_FILES[0]]
                or expectations["fixture_sha256"] != before[CORE_FILES[1]]):
            raise ValueError("invalid_core_expectations_or_source_hash")
        selectors = expectations["selectors"]
        if not isinstance(selectors, list) or len(selectors) != 32:
            raise ValueError("invalid_core_selector_inventory")
        seen = set()
        for item in selectors:
            if (not isinstance(item, dict)
                    or set(item) != {"name", "expected_exit", "expected_first_fail", "expected_failed_assertions"}
                    or not isinstance(item["name"], str)
                    or re.fullmatch(r"[a-z0-9_]+", item["name"]) is None
                    or item["name"] in seen
                    or type(item["expected_exit"]) is not int or item["expected_exit"] not in (0, 1)
                    or (item["expected_first_fail"] is not None and
                        (not isinstance(item["expected_first_fail"], str) or
                         re.fullmatch(r"[a-z0-9_]+", item["expected_first_fail"]) is None))
                    or (item["expected_failed_assertions"] is not None and
                        (type(item["expected_failed_assertions"]) is not int or item["expected_failed_assertions"] < 0))
                    or (item["expected_exit"] == 0) != (item["name"] == "default_unqualified")
                    or (item["expected_exit"] == 0) != (item["expected_first_fail"] is None)):
                raise ValueError("invalid_core_selector_expectation")
            seen.add(item["name"])
    binary = output / "ng8-core-tests"
    built = execute(["xcrun", "swiftc", "-swift-version", "5", "-Onone",
        "-parse-as-library", *(str(HERE / name) for name in CORE_FILES), "-o", str(binary)],
        output, "core-compile", 120)
    if built.returncode:
        raise ValueError("core_compile_failed_not_behavior_red")
    if expanded:
        cases = {}
        for item in selectors:
            selector = item["name"]
            try:
                tested = execute([str(binary), selector], output, "core-" + selector, 30)
                labels = re.findall(r"^FAIL ([a-z0-9_]+)$", tested.stdout, re.MULTILINE)
                matched = re.fullmatch(r"CASE " + re.escape(selector) +
                    r"\n(?:FAIL [a-z0-9_]+\n)*ASSERTIONS_FAILED ([0-9]+)\n", tested.stdout)
                count = int(matched[1]) if matched else None
                valid = (matched is not None and not tested.stderr
                    and tested.returncode == item["expected_exit"]
                    and count == len(labels)
                    and (labels[0] if labels else None) == item["expected_first_fail"]
                    and (count > 0) == (item["expected_exit"] == 1)
                    and (item["expected_failed_assertions"] is None or count == item["expected_failed_assertions"]))
                cases[selector] = {"status": ("expected_red" if tested.returncode == 1 else "green") if valid else "blocked",
                    "return_code": tested.returncode, "assertion_labels": labels,
                    "failed_assertions": count, "stderr_nonempty": bool(tested.stderr)}
            except Exception as error:
                cases[selector] = {"status": "blocked", "reason": type(error).__name__}
        if source_hashes(names) != before:
            raise ValueError("fixture_source_changed")
        return {"status": "blocked" if any(c["status"] == "blocked" for c in cases.values()) else "expected_red",
            "compiled": True, "selector_count": len(cases), "cases": cases, "source_sha256": before}
    tested = execute([str(binary)], output, "core-qualified", 30)
    if tested.returncode != 1 or tested.stdout != CORE_EXPECTED_RED or tested.stderr:
        raise ValueError("expected_core_assertion_red_missing")
    if source_hashes(CORE_FILES) != before:
        raise ValueError("fixture_source_changed")
    return {"status": "expected_red", "compiled": True, "assertion_failures": 7,
            "assertion_red": "FAIL qualified_new_id_one_capture", "source_sha256": before}


def mode_red(output):
    before = source_hashes(MODE_FILES)
    variants = {}
    expected_by_selector = {
        "qualification": "FAIL qualified_optin_raw_iphone10_1_selects_capture_only",
        "metadata": "FAIL dedicated_metadata_names_service_mode",
        "routes": "FAIL pair_is_always_403_without_approval_dispatch",
        "binding": "FAIL capture_only_constructor_gets_process_binding_initialStart",
    }
    for opt_in in (True, False):
        variant = "dedicated" if opt_in else "ordinary"
        binary = output / ("ng8-mode-" + variant)
        command = ["xcrun", "swiftc", "-swift-version", "5", "-Onone", "-parse-as-library"]
        if opt_in:
            command += ["-D", "NG8_CAPTURE_PROBE_BUILD"]
        try:
            built = execute([*command, *(str(HERE / name) for name in MODE_FILES), "-o", str(binary)],
                            output, "mode-" + variant + "-compile", 120)
        except Exception as error:
            variants[variant] = {"status": "blocked", "reason": type(error).__name__}
            continue
        if built.returncode:
            variants[variant] = {"status": "blocked", "compiled": False,
                "reason": "mode_compile_failed_not_behavior_red"}
            continue
        cases = {}
        for selector, expected in expected_by_selector.items():
            try:
                tested = execute([str(binary), selector], output, "mode-" + variant + "-" + selector, 30)
                valid = tested.returncode == 1 and tested.stdout.strip() == expected and not tested.stderr
                cases[selector] = {"status": "expected_red" if valid else "blocked",
                    "return_code": tested.returncode,
                    "assertion_labels": re.findall(r"^FAIL ([a-z0-9_]+)$", tested.stdout, re.MULTILINE),
                    "stderr_nonempty": bool(tested.stderr)}
            except Exception as error:
                cases[selector] = {"status": "blocked", "reason": type(error).__name__}
        variants[variant] = {"status": "blocked" if any(c["status"] == "blocked" for c in cases.values()) else "expected_red",
            "compiled": True, "cases": cases}
    if source_hashes(MODE_FILES) != before:
        raise ValueError("fixture_source_changed")
    return {"status": "blocked" if any(v["status"] == "blocked" for v in variants.values()) else "expected_red",
            "variants": variants, "assertion_red_by_selector": expected_by_selector, "source_sha256": before}


def run(output):
    if sys.platform != "darwin":
        raise ValueError("macos_host_required_not_behavior_red")
    stage = json.loads((HERE / "host-stage.json").read_text())
    if (set(stage) != {"schema", "phase"}
            or stage["schema"] != "ng8-host-stage-v1"
            or stage["phase"] not in ("bridge-red", "bridge-green-components-red", "bridge-green-mode-red",
                                      "bridge-green-components-batch-red")):
        raise ValueError("unsupported_host_stage")
    if stage["phase"] == "bridge-red":
        result = bridge(output, expect_red=True)
        return dict(result, schema="ng8-host-report-v1", phase=stage["phase"],
                    green_implementation=False, device_acceptance="not_run")
    # Independent components use distinct binaries/logs. Inspect every outcome,
    # including a compiler failure; none can be converted into an expected Red.
    operations = {"bridge": lambda: bridge(output, expect_red=False), "mode": lambda: mode_red(output)}
    if stage["phase"] == "bridge-green-components-red":
        operations["coordinator"] = lambda: coordinator_red(output)
    elif stage["phase"] == "bridge-green-components-batch-red":
        operations["coordinator"] = lambda: coordinator_red(output, expanded=True)
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
