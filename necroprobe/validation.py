"""外部応答の上限と型検査。例外に入力値を含めない。"""
import base64
import binascii
import json
import math

MAX_HTTP = 12 * 1024 * 1024
MAX_PLAIN = 8 * 1024 * 1024
MAX_IMAGE = 4 * 1024 * 1024
MAX_PIXELS = 8_000_000


class ProbeError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def number(value, low, high):
    if type(value) not in (int, float) or not low <= value <= high or not math.isfinite(value):
        raise ProbeError("invalid_number")
    return value


def b64(value, limit):
    if not isinstance(value, str) or len(value) > 4 * ((limit + 2) // 3):
        raise ProbeError("base64_size_or_type")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise ProbeError("invalid_base64") from None
    if len(raw) > limit:
        raise ProbeError("base64_size_or_type")
    return raw


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ProbeError("duplicate_json_key")
        result[key] = value
    return result


def _constant(_):
    raise ProbeError("nonfinite_json")


def json_object(raw, limit=MAX_PLAIN):
    if not isinstance(raw, bytes) or not raw or len(raw) > limit:
        raise ProbeError("json_size")
    try:
        text = raw.decode("utf-8")
        # C scanstring skips long base64 strings. Check depth before json.loads,
        # so a tiny but deeply nested object never reaches the recursive parser.
        index = depth = nodes = 0
        while index < len(text):
            char = text[index]
            if char == '"':
                _, index = json.decoder.scanstring(text, index + 1, True)
                look = index
                while look < len(text) and text[look] in " \t\r\n":
                    look += 1
                if look >= len(text) or text[look] != ":":
                    nodes += 1
                if nodes > 10_000:
                    raise ProbeError("json_nodes")
                continue
            if char in "[{":
                depth += 1
                nodes += 1
                if depth > 16:
                    raise ProbeError("json_depth")
            elif char in "]}":
                depth -= 1
            elif char not in " \t\r\n,:":
                nodes += 1
                while index < len(text) and text[index] not in ' \t\r\n,{}[]"':
                    index += 1
                if nodes > 10_000:
                    raise ProbeError("json_nodes")
                continue
            if nodes > 10_000:
                raise ProbeError("json_nodes")
            index += 1
        result = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    except (UnicodeError, ValueError, RecursionError):
        raise ProbeError("invalid_json") from None
    if not isinstance(result, dict):
        raise ProbeError("json_object_required")
    pending = [result]
    nodes = 0
    while pending:
        item = pending.pop()
        nodes += 1
        if nodes > 10_000:
            raise ProbeError("json_nodes")
        if isinstance(item, dict):
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, float) and not math.isfinite(item):
            raise ProbeError("nonfinite_json")
    return result
