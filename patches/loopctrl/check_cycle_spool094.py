#!/usr/bin/env python3
"""Compile/run TEST094 spool real-filesystem fixture on a Swift/CryptoKit host.

The optional mutation is a semantic fault-boundary Red, never evidence of
baseline iPhone behavior or of a pre-implementation baseline for a new file.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from PIL import Image

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "ngg2" / "NG2CycleSpool.swift"
FIXTURE = HERE / "ngg2_cycle_spool_tests.swift"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--swiftc", default="swiftc")
    parser.add_argument("--fault-red", action="store_true")
    options = parser.parse_args()
    compiler = shutil.which(options.swiftc)
    if compiler is None:
        raise SystemExit("Swift compiler unavailable; no spool fixture or semantic Red was executed")
    with tempfile.TemporaryDirectory(prefix="ngg2-cycle-spool094-") as temporary:
        stage = Path(temporary)
        original = SOURCE.read_text()
        source = stage / "NG2CycleSpool.swift"
        fixture = stage / "main.swift"
        fixture.write_bytes(FIXTURE.read_bytes())
        executable = stage / "fixture"

        def compile_and_run(content):
            source.write_text(content)
            subprocess.run([compiler, "-Onone", "-D", "NG2_RUNTIME_HOST_TEST",
                            str(source), str(fixture), "-o", str(executable)], check=True)
            environment = dict(os.environ, NG2_SPOOL_PNG_OUTPUT=str(stage / "roundtrip"))
            return subprocess.run([str(executable)], env=environment, capture_output=True, text=True)

        if options.fault_red:
            marker = "catch { damaged = true; writable = false; diagnosticInterrupted = true; incompleteEntries = true; throw error }"
            if original.count(marker) != 1:
                raise SystemExit("fault mutation boundary changed")
            red = compile_and_run(original.replace(marker, "catch { throw error }", 1))
            if red.returncode == 0 or "FAIL fault permanently revokes writer part_open" not in red.stdout:
                raise SystemExit("semantic Red missing or wrong failure: " + red.stdout + red.stderr)
            print("PASS semantic fault-boundary Red: uncommitted failure cannot preserve writer authority")
        green = compile_and_run(original)
        print(green.stdout, end="")
        if green.returncode:
            raise SystemExit(green.stderr or green.returncode)
        png = (stage / "roundtrip.png").read_bytes()
        raw = (stage / "roundtrip.rgba").read_bytes()
        assert len(png) == 1_484_368
        with Image.open(stage / "roundtrip.png") as image:
            image.load()
            assert image.size == (896, 414) and image.mode == "RGBA"
            assert image.tobytes() == raw
        print("PASS stored-DEFLATE PNG independent decoder: every original pixel, exact bound")


if __name__ == "__main__":
    main()
