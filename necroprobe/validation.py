"""外部応答の上限と型検査。例外に入力値を含めない。"""
import base64
import binascii
import json
import math
import re

MAX_HTTP = 12 * 1024 * 1024
MAX_PLAIN = 8 * 1024 * 1024
MAX_IMAGE = 4 * 1024 * 1024
MAX_PIXELS = 8_000_000

# Short ordinary keys can be skipped without allocating a second key string.
# This is only a fast path: longer or escaped keys use scanstring below.
_JSON_TOKEN = re.compile(
    r'(?P<key>"[^"\\\x00-\x1f]{0,128}"[ \t\r\n]*:)|"|[{}\[\]]|'
    r'[^ \t\r\n,:{}\[\]"][^ \t\r\n,{}\[\]"]*')
_JSON_SPACE = re.compile(r'[ \t\r\n]*')


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
        # Native token seeking skips number bytes and whitespace. C scanstring
        # still handles escaped or long strings. Reject depth/nodes before
        # json.loads allocates the object, including at the exact boundaries.
        index = depth = nodes = 0
        nonfinite = False

        def parse_float(text):
            nonlocal nonfinite
            value = float(text)
            if not math.isfinite(value):
                nonfinite = True
            return value

        while True:
            marker = _JSON_TOKEN.search(text, index)
            if marker is None:
                break
            index = marker.end()
            if marker.lastgroup == 'key':
                continue
            char = marker.group()[0]
            if char == '"':
                _, index = json.decoder.scanstring(text, index, True)
                look = _JSON_SPACE.match(text, index).end()
                if look >= len(text) or text[look] != ":":
                    nodes += 1
            elif char in "[{":
                depth += 1
                nodes += 1
                if depth > 16:
                    raise ProbeError("json_depth")
            elif char in "]}":
                depth -= 1
            else:
                nodes += 1
            if nodes > 10_000:
                raise ProbeError("json_nodes")
        result = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant,
                            parse_float=parse_float)
    except (UnicodeError, ValueError, RecursionError):
        raise ProbeError("invalid_json") from None
    if not isinstance(result, dict):
        raise ProbeError("json_object_required")
    # The preflight already counts each container/value once. Defer overflow
    # rejection until after duplicate keys and root type to retain error order.
    if nonfinite:
        raise ProbeError("nonfinite_json")
    return result
