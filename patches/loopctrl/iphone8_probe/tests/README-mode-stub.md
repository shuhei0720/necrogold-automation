# NG8 Kit mode / route policy: initial Red stub

This stage owns only `assets/NG8CaptureMode.swift`,
`tests/NG8CaptureModeTests.swift`, and this README. It does not modify or bind
the existing Kit router/metadata/session, overlay, bridge, coordinator or CI.

`RPCServiceMode.select` deliberately returns `.normal`; the raw-hardware reader
returns nil, capture-only route policy refuses dispatch, metadata keeps its
baseline input, and constructor binding returns nil. Do not implement Green
until the real macOS compiler has observed this named assertion failure:

`FAIL qualified_optin_raw_iphone10_1_selects_capture_only`

The fixture first verifies that opt-in false performs zero hardware queries
and other/unknown/failed raw models remain normal. It then requires dedicated
opt-in plus exact raw `iPhone10,1` to select the new mode. This value assertion,
not a missing symbol/compiler/environment error, is the intended first Red.

From the repository root on macOS, with a fresh scratch directory:

```sh
MODE_STAGE_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ng8-mode-red.XXXXXX")
xcrun swiftc -Onone -D NG8_CAPTURE_PROBE_BUILD \
  patches/loopctrl/iphone8_probe/assets/NG8CaptureMode.swift \
  patches/loopctrl/iphone8_probe/tests/NG8CaptureModeTests.swift \
  -o "$MODE_STAGE_DIR/ng8-mode-tests"
"$MODE_STAGE_DIR/ng8-mode-tests"
```

Expected: compilation succeeds, execution prints the named FAIL and exits 1.
Repeat compilation without `-D NG8_CAPTURE_PROBE_BUILD` to check the normal
compile condition: the fixture's explicit injected positive case still has
the same required Red. No live `hw.machine`, iPhone, credentials or network
access is needed. The production Darwin reader is intentionally still a stub.

The remaining prepared assertions cover normal surface identity, the new
probe-only advertised surface, closed remote/local policy, pair HTTP403,
typed trusted in-process admin, owner pause/revoke, producer rejection, and
same-process coordinator binding across the five declared constructor sites.
Origin is a non-Codable typed argument supplied by the future actual callsite;
wire fields cannot be treated as proof of trusted local origin. Policy inputs
contain only caller fields, before internal peer/actor fields are added.

Config decisions name separate response-shape lanes; this fixture does not
generate the actual RunnerAdmin response or authenticate an envelope. Generic
constructor binding checks the supplied object identity without duplicating
the coordinator's state implementation. It does not prove that the five real
constructor calls use the helper. Actual router/authentication/metadata/body
schemas/constructor wiring and producer-zero integration remain later work.
