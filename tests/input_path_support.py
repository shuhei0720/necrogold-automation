"""TEST-011用の合成応答。端末の結果を表さない。"""
from copy import deepcopy

from necroprobe.protocol import GAME, RpcReply
from necroprobe.validation import ProbeError
from test_source_geometry import geometry_payload

CAPABILITY = "screenshot_image_geometry_v1"
AX = {"exists": True, "hittable": True, "ref": "el_123", "label": "ゲームを続行",
      "x": 12, "y": 20, "width": 80, "height": 25, "element_type": "Button",
      "visibility": "in_view", "match_count": 1, "alternatives": [],
      "value": "PRIVATE", "hint": "PRIVATE", "unknown": "PRIVATE"}
METHODS = ["device_info", "launch_app", "device_info", "screenshot", "device_info",
           "find_element", "device_info", "screenshot", "device_info"]


class FakeClient:
    timeout = 8

    def __init__(self, *, caps=None, ax=None, failure=None, info_changes=None, image_change=None):
        self.caps = [CAPABILITY] if caps is None else caps
        self.ax = deepcopy(AX if ax is None else ax)
        self.failure, self.info_changes, self.image_change = failure, info_changes or {}, image_change
        self.calls, self.raws = [], []

    def call(self, method, params=None, timeout=None):
        self.calls.append((method, deepcopy(params)))
        index = len(self.calls)
        if index == self.failure:
            raise ProbeError("rpc_error")
        if method == "device_info":
            result = {"capabilities": self.caps, "system": {"foreground_app": GAME, "screen_locked": False},
                      "private": "PRIVATE"}
            result.update(deepcopy(self.info_changes.get(index, {})))
        elif method == "launch_app":
            result = {"private": "PRIVATE"}
        elif method == "find_element":
            result = deepcopy(self.ax)
        elif method == "screenshot":
            raw, result = geometry_payload(params)
            self.raws.append(raw)
            if self.image_change:
                self.image_change(result, len(self.raws))
        else:
            raise AssertionError("許可外のメソッド")
        return RpcReply(result, {"private": "PRIVATE"})
