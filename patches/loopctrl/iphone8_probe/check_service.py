#!/usr/bin/env python3
"""Compile/run the isolated service boundary; assertion Red is an explicit stage."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    options = parser.parse_args()
    output = Path(options.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    stage = json.loads((HERE / "service-stage.json").read_text())
    if sys.platform != "darwin" or not shutil.which("swiftc"):
        raise SystemExit("macOS Swift unavailable; no service semantic Red/Green executed")
    sources = [ROOT / row["path"] for row in stage["sources"]]
    actual = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sources}
    if any(actual[row["path"]] != row["sha256"] for row in stage["sources"]):
        raise SystemExit("service source pin mismatch")
    with tempfile.TemporaryDirectory(prefix="ng8-service-host-") as temporary:
        executable = Path(temporary) / "service-tests"
        command = ["swiftc", "-swift-version", "5", "-Onone", "-parse-as-library",
                   "-D", "NG8_CAPTURE_PROBE_BUILD", "-D", "NG8_CAPTURE_SERVICE_HOST_TEST",
                   *map(str, sources), "-o", str(executable)]
        compile_result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        (output / "compile.stdout").write_text(compile_result.stdout)
        (output / "compile.stderr").write_text(compile_result.stderr)
        if compile_result.returncode:
            print("\n".join(compile_result.stderr.splitlines()[:16]))
            raise SystemExit("service compilation failed; not assertion Red")
        selector = stage["selector"]
        result = subprocess.run([str(executable), selector], capture_output=True,
                                text=True, timeout=15)
        (output / "service.stdout").write_text(result.stdout)
        (output / "service.stderr").write_text(result.stderr)
        expected = f"CASE {selector}\n"
        if stage["phase"] == "red":
            expected += f"FAIL {stage['expected_failure']}\nASSERTIONS_FAILED 1\n"
            accepted = result.returncode == 1
        elif stage["phase"] == "green":
            expected += "ASSERTIONS_FAILED 0\n"
            accepted = result.returncode == 0
        else:
            raise SystemExit("unsupported service stage")
        accepted = accepted and result.stdout == expected and result.stderr == ""
        report = {"schema": "ng8-service-host-v1", "phase": stage["phase"],
                  "compile_returncode": compile_result.returncode, "sources": actual,
                  "selector": selector, "returncode": result.returncode,
                  "stdout": result.stdout, "stderr": result.stderr, "accepted": accepted}
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, sort_keys=True))
        if not accepted:
            raise SystemExit("service named assertion proof mismatch")
        print("PASS service host " + stage["phase"] + " assertion contract")


if __name__ == "__main__":
    main()
