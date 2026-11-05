"""認証済み遠隔エラーを固定分類へ縮約する。本文・dataは保持しない。"""
import re

from .validation import ProbeError

DIAGNOSTIC_REVISION = "rpc-diagnostics-v1"
FIXED_FIND_PARAMS = {"bundle_id": "jp.co.spike-chunsoft.necrodancerjp",
                     "element_id": "ゲームを続行", "match": "exact"}
CATEGORY_CODES = {"no_matching_element": -32602, "system_alert_reported": -32602,
                  "webview_context_reported": -32602, "app_not_running": -32004,
                  "app_background": -32004, "ax_unresponsive": -32000,
                  "server_queued": -32000, "server_timeout": -32000}
CATEGORIES = frozenset(CATEGORY_CODES) | {"unclassified", "malformed_remote_error"}
MAX_MESSAGE_CHARS = 8192

# 固定v0.3.4 + NG-G1 ActionHandler.swiftの文法。助言は分類用であり実行しない。
_BASE = "No element matching label/id 'ゲームを続行'"
_WEBVIEW_ADVICE = (
    " ⚠️ The foreground app is a BROWSER: web page content is NOT exposed to the "
    "accessibility tree, so find_element/page_source can never see links, buttons or text in the page "
    "(page_source returns only browser chrome). Do NOT retry with scroll_to_element or match:'contains' — "
    "they cannot help here. Next: call screenshot, read the target's position off the image, convert "
    "pixel→point by dividing by the `scale` field in that same screenshot response, then tap{x,y}."
)
_BUNDLE = FIXED_FIND_PARAMS["bundle_id"]
_APP = "Can't find 'ゲームを続行': app '" + _BUNDLE + "'"
_PREFIXES = (
    ("system_alert_reported", _BASE + ": a system alert "),
    ("webview_context_reported", _BASE + "." + _WEBVIEW_ADVICE),
    ("no_matching_element", _BASE + ". It may be off-screen (page{direction}, then find_element again), or the label differs from on-screen text — check page_source. Try match:'contains'."),
    ("app_not_running", _APP + " is not running ("),
    ("app_background", _APP + " is in the background, so it has no snapshottable window."),
    ("ax_unresponsive", _BUNDLE + "'s accessibility isn't answering right now, so 'ゲームを続行' can't be looked up."),
    ("server_queued", "find_element has NOT run yet: it is queued behind "),
    ("server_timeout", "find_element exceeded 6s and may still be running on the device."),
)
_AX_DURATION = re.compile(
    re.escape(_BUNDLE + "'s accessibility isn't answering right now (the tree read failed after ")
    + r"[0-9]{1,3}" + re.escape("s), so 'ゲームを続行' couldn't be looked up."))


def valid_rpc_code(value):
    return type(value) is int and -2147483648 <= value <= 2147483647


class RemoteRpcError(ProbeError):
    """既存codeを保ち、安全な3値だけを属性へ載せる。"""

    def __init__(self, rpc_code, category, error_shape_valid):
        super().__init__("rpc_error")
        self.rpc_code = rpc_code
        self.category = category
        self.error_shape_valid = error_shape_valid


def remote_error(response, method, params):
    """MAC・応答ID照合済みの応答専用。未知キーと自由文は返さない。"""
    error = response.get("error")
    code = error.get("code") if type(error) is dict else None
    code = code if valid_rpc_code(code) else None
    valid = (type(error) is dict and code is not None and type(error.get("message")) is str
             and "result" not in response)
    if not valid:
        return RemoteRpcError(code, "malformed_remote_error", False)
    message = error["message"]
    category = "unclassified"
    fixed_request = (method == "find_element" and type(params) is dict
                     and params == FIXED_FIND_PARAMS
                     and all(type(value) is str for value in params.values()))
    if fixed_request and len(message) <= MAX_MESSAGE_CHARS:
        for candidate, prefix in _PREFIXES:
            if code == CATEGORY_CODES[candidate] and message.startswith(prefix):
                category = candidate
                break
        if category == "unclassified" and code == -32000 and _AX_DURATION.match(message):
            category = "ax_unresponsive"
    return RemoteRpcError(code, category, True)
