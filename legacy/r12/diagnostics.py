"""Bounded stage record for a separate parent process; contains no RPC secrets."""
from contextlib import contextmanager
import faulthandler
import json
import os
from pathlib import Path
import time

_path = None
_current = None


def write_record(path, record):
    path = Path(path)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def read_record(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def enable():
    global _path
    try:
        faulthandler.enable(all_threads=True)
    except (OSError, RuntimeError):
        pass
    name = os.environ.get("NECRO_STAGE_FILE")
    _path = Path(name) if name else None
    mark("起動中")


def mark(label, limit=30, state="running"):
    global _current
    if _path is None:
        return
    _current = dict(pid=os.getpid(), phase=label, since=time.monotonic(),
                    wall_time=time.time(), limit=limit, state=state)
    try:
        write_record(_path, _current)
    except OSError:
        # Failure to write diagnostics must not cause an extra game input.
        pass


@contextmanager
def stage(label, limit=30):
    previous = _current
    mark(label, limit)
    try:
        yield
    except BaseException:
        # Keep the failing innermost phase for the parent's exit report.
        raise
    else:
        if previous is not None:
            mark(previous["phase"], previous["limit"])
        elif _path is not None:
            mark("処理継続中")


def finish(state):
    if _current is not None:
        mark(_current["phase"], state=state)
