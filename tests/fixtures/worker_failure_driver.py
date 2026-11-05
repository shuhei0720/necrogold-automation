"""Inject startup failures into a real CLI child; no device or credentials used."""
import os
import json
from pathlib import Path
import signal
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from necroprobe import __main__ as cli


def child(mode, arguments):
    cli.load_pairing = lambda *_: (b"fixture-key" * 4, "fixture")
    def broken_crypto(**_):
        if mode == "corrupt_report":
            folder = Path(arguments[arguments.index("--output") + 1])
            (folder / "report.json").write_text("PRIVATE_FIXTURE_SECRET_MUST_NOT_APPEAR")
            os._exit(23)
        if mode.startswith("invalid_structure_"):
            folder = Path(arguments[arguments.index("--output") + 1])
            invalid = [{}, {"worker": []}, {"rows": []}, {"status": "running"}]
            (folder / "report.json").write_text(json.dumps(invalid[int(mode.rsplit("_", 1)[1])]))
            os._exit(23)
        if mode == "custom":
            private_type = type("PRIVATE_FIXTURE_SECRET_TYPE", (Exception,), {})
            raise private_type("PRIVATE_FIXTURE_SECRET_MESSAGE")
        if mode == "oserror":
            raise OSError("PRIVATE_FIXTURE_SECRET_OSERROR")
        if mode == "signal":
            import resource
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            os.kill(os.getpid(), signal.SIGSEGV)
        raise ValueError("PRIVATE_FIXTURE_SECRET_MUST_NOT_APPEAR")
    cli.Crypto = broken_crypto
    return cli.main(arguments)


def main():
    if sys.argv[1] == "child":
        return child(sys.argv[2], sys.argv[3:])
    mode, folder = sys.argv[1:]
    original = cli.supervise
    def use_fixture(command, timeout, diagnostics=None):
        injected = [sys.executable, str(Path(__file__).resolve()), "child", mode] + command[3:]
        return original(injected, timeout, diagnostics)
    cli.supervise = use_fixture
    return cli.main(["capture", "--output", folder, "--samples", "3", "--seconds", "5"])


if __name__ == "__main__":
    raise SystemExit(main())
