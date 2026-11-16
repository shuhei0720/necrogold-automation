# NG8 Kit mode / route policy: Red evidence and Green candidate

This stage owns only `assets/NG8CaptureMode.swift`,
`tests/NG8CaptureModeTests.swift`, and this README. It does not modify or bind
the existing Kit router/metadata/session, overlay, bridge, coordinator or CI.

The initial stub deliberately selected `.normal`, returned no hardware model,
refused dedicated dispatch, preserved baseline metadata, and returned no binding.
The real macOS compiler first observed this named assertion failure:

`FAIL qualified_optin_raw_iphone10_1_selects_capture_only`

The fixture first verifies that opt-in false performs zero hardware queries
and other/unknown/failed raw models remain normal. It then requires dedicated
opt-in plus exact raw `iPhone10,1` to select the new mode. This value assertion,
not a missing symbol/compiler/environment error, is the intended first Red.
The expanded four-selector Red was subsequently observed for both compile flags
in [run43842351667](https://github.com/shuhei0720/necrogold-automation/actions/runs/43842351667),
job `133213889275`, commit `9d1bfa6c08168cde044e73aba40826bceac5522f`.
All eight executions matched the required FAIL, exit 1 and empty stderr, with
source/fixture hashes matching that commit. Green source is now a reviewed
candidate; actual Mac Green and iOS hardware-reader execution remain unverified.

From the repository root on macOS, with a fresh scratch directory:

```sh
MODE_STAGE_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ng8-mode-red.XXXXXX")
xcrun swiftc -Onone -D NG8_CAPTURE_PROBE_BUILD \
  patches/loopctrl/iphone8_probe/assets/NG8CaptureMode.swift \
  patches/loopctrl/iphone8_probe/tests/NG8CaptureModeTests.swift \
  -o "$MODE_STAGE_DIR/ng8-mode-tests"
"$MODE_STAGE_DIR/ng8-mode-tests"
```

The recorded stub compiled then printed the named FAIL and exited 1 for both
compile flags. For the Green candidate, every selector must instead print its
exact `PASS NG8 mode selector ...` line and exit 0 with empty stderr. Repeat
compilation without `-D NG8_CAPTURE_PROBE_BUILD` to check the ordinary compile
condition. No live iPhone, credentials or network access is needed by this host
fixture; its injected hardware cases do not prove production iOS sysctl behavior.

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

## Feature selectors and Red evidence

The executable accepts exactly one optional selector: `qualification`,
`metadata`, `routes`, `binding`, or `all`. No argument preserves the previous
full order (`all`). Unknown or multiple arguments print
`FAIL invalid_mode_test_selector` and exit 2; that is not a behavior Red.
Each selector runs the existing feature function without removing or relaxing
its assertions. Run each as a separate process so an earlier Red does not hide
the other features:

```sh
"$MODE_STAGE_DIR/ng8-mode-tests" qualification
"$MODE_STAGE_DIR/ng8-mode-tests" metadata
"$MODE_STAGE_DIR/ng8-mode-tests" routes
"$MODE_STAGE_DIR/ng8-mode-tests" binding
```

The implementation stub produced these exact failures in both flag variants:

| Selector | Expected first stdout line | Evidence |
| --- | --- | --- |
| `qualification` | `FAIL qualified_optin_raw_iphone10_1_selects_capture_only` | Measured in run43842351667; original no-argument entry also measured in run43837286672 |
| `metadata` | `FAIL dedicated_metadata_names_service_mode` | Measured in run43842351667 |
| `routes` | `FAIL pair_is_always_403_without_approval_dispatch` | Measured in run43842351667 |
| `binding` | `FAIL capture_only_constructor_gets_process_binding_initialStart` | Measured in run43842351667 |

The next `bridge-core-mode-green` phase runs all four selectors for both flags
and requires eight exact PASS lines, exit 0 and empty stderr. Existing assertions
and the fixture remain unchanged. Compile/environment failure and timeouts are
blocked results; host Green does not establish live authentication, integration,
device capture or iPhone 11 acceptance.
