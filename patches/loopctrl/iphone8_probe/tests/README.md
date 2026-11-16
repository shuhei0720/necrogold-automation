# NEW8 Objective-C bridge assertion fixture

This fixture connects the actual NEW8 `.m` implementation to fake private daemon
classes. It does not substitute a Swift string error for an Objective-C send
exception and does not claim device capture, JPEG decoding, or gameplay success.

The current bridge is deliberately a **not-implemented assertion-Red stub**.
Do not deploy it. Green implementation waits for the parent to observe a real
macOS compile followed by the behavioral Red below.

Run from the repository root on the standard `macos-26` runner:

```sh
mkdir -p "$RUNNER_TEMP/ng8-capture-host"
xcrun clang -fobjc-arc -fblocks -DNG8_CAPTURE_HOST_TEST=1 \
  -I patches/loopctrl/iphone8_probe/assets \
  -I patches/loopctrl/iphone8_probe/tests \
  patches/loopctrl/iphone8_probe/assets/NG8CaptureBridge.m \
  patches/loopctrl/iphone8_probe/tests/NG8CaptureBridgeTests.m \
  -framework Foundation -framework CoreGraphics \
  -o "$RUNNER_TEMP/ng8-capture-host/bridge-tests"
"$RUNNER_TEMP/ng8-capture-host/bridge-tests" primary
```

The stub must compile successfully, then `primary` must exit 1 with exactly:

```text
FAIL capture_one_daemon_request
```

An absent compiler/framework or a compile failure is **not** the behavior Red.
The Linux preparation environment has no clang/macOS frameworks; no local compile
or execution result is claimed.

After implementation, run every selector in its own process. Each process starts
with independent descriptor/ticket/global fake state; never-callback and ambiguous
send-throw cases intentionally keep ownership unresolved until process exit.

```sh
for fixture in primary three_arg_request exact_maximum empty nil_data oversize \
  wrong_type getter_exception daemon_error throw_retained throw_unknown \
  sync_send_held getter_fence consumer_fence sync_then_throw \
  sync_error_then_throw api_unavailable encoding_unavailable request_unavailable \
  off_main_prepare prepare_exception never_callback consumer_exception
do
  "$RUNNER_TEMP/ng8-capture-host/bridge-tests" "$fixture" || exit "$?"
done
```

| Case | Required behavior |
| --- | --- |
| primary / three_arg_request | prepare descriptor once; one full-screen `public.jpeg`, requested quality0.6; original bytes unchanged; duplicate getter/reply/drain zero |
| exact_maximum / empty / nil_data / oversize / wrong_type | exact8MiB accepted, invalid NSData boundaries fixed `bytes_invalid`, no encoding/fallback |
| getter_exception / daemon_error | fixed closed failure, no raw exception/daemon string, late duplicate cannot replace first outcome |
| throw_retained | synthetic `request_exception` reply is not daemon drain; actual late callback only drains; no late data getter/second reply |
| throw_unknown / never_callback | no guessed drain, no resend; unresolved owner remains with caller/coordinator |
| sync_send_held | synchronous daemon callback does not end send ownership; success reply waits for send return |
| getter_fence / consumer_fence | send return alone is insufficient; drain remains false while callback getter/consumer executes; duplicate during getter does not enter twice |
| sync_then_throw / sync_error_then_throw | send failure overrides an uncommitted success candidate; first actual failure is immutable; both real callback and send unwind required |
| API / encoding / request unavailable | proven pre-send failure can reply/drain once without inventing a daemon wait |
| off_main_prepare / prepare_exception | no off-main descriptor/capture; fixed prepare failure without capture |
| consumer_exception | consumer invoked once; no second error reply to the same throwing consumer; finally drain still occurs |

The four-byte byte-transport sample is deliberately not a valid complete JPEG.
The coordinator's ImageIO metadata contract must reject malformed JPEG separately;
the bridge only validates NSData type, nonempty length, and the8MiB transport cap.
No tests alter NG2/R12 sources, coordinate tables, or production iPhone11 paths.
