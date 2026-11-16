# NEW8 Objective-C bridge assertion fixture

This fixture connects the actual NEW8 `.m` implementation to fake private daemon
classes. It does not substitute a Swift string error for an Objective-C send
exception and does not claim device capture, JPEG decoding, or gameplay success.

The bridge began as a **not-implemented assertion-Red stub**. The parent observed
a real macOS compile followed by the behavioral Red below at commit
`9f86c93c6e316582efe78842dd2472e781f79e69`, Actions run `43833216314`, job
`133183319327`. Green source has now been written; a new macOS run must verify it.
This component alone is not a deployable or device-qualified build.

Subsequent run `43842351667` / job `133213889275` at commit `9d1bfa6` compiled
successfully, but `encoding_unavailable` exited by SIGSEGV (`return_code=-11`)
before any named assertion or closed diagnostic was emitted; stderr was empty.
That is a blocked execution, not an assertion Red. A NEW8-only alloc/init ARC
ownership correction is now a reviewed candidate, with all fixture assertions
unchanged. The next host phase must rerun all 26 selectors; improvement is still
unverified. The existing NG2/iPhone 11 factory remains unchanged.

For this new, isolated capture-only capability, `drained` means **the final
owned-work handoff**: send return/unwind plus all first-callback data/getter/copy
work and the primary reply consumer have ended. It does not prove literal daemon
block stack return or framework-internal cleanup. Wire status/manifest must retain
`callback_return_verified=false` and name its event time
`callback_body_handoff_ns`. This interpretation does not change NG2, the existing
native contract, or R12. The probe process has no UI/native/legacy producer and
its images never become input authority.

The integration's handoff receiver must only enqueue a nonblocking event: no AX,
metadata parsing, hashing, waits, or lock acquisition. The receiving coordinator
tracks its own queued work until that work really ends. The bridge does not
perform data/getter/consumer work or mutate ticket state after its final handoff.

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

The baseline stub compiled successfully, then `primary` exited 1 with exactly:

```text
FAIL capture_one_daemon_request
```

An absent compiler/framework or a compile failure is **not** the behavior Red.
The Linux preparation environment has no clang/macOS frameworks; no local compile
or Green execution result is claimed.

After implementation, run every selector in its own process. Each process starts
with independent descriptor/ticket/global fake state; never-callback and ambiguous
send-throw cases intentionally keep ownership unresolved until process exit.

```sh
for fixture in primary three_arg_request exact_maximum mutable_original unprepared empty nil_data oversize \
  wrong_type getter_exception daemon_error throw_retained throw_unknown \
  sync_send_held getter_fence consumer_fence sync_then_throw \
  sync_error_then_throw api_unavailable encoding_unavailable request_unavailable \
  off_main_prepare prepare_exception never_callback consumer_exception handoff_not_return
do
  "$RUNNER_TEMP/ng8-capture-host/bridge-tests" "$fixture" || exit "$?"
done
```

| Case | Required behavior |
| --- | --- |
| primary / three_arg_request | prepare descriptor once; one full-screen `public.jpeg`, requested quality0.6; original bytes unchanged; duplicate getter/reply/drain zero |
| exact_maximum / empty / nil_data / oversize / wrong_type | exact8MiB accepted, invalid NSData boundaries fixed `bytes_invalid`, no encoding/fallback |
| mutable_original | daemon-owned mutable NSData can change after delivery without changing the retained artifact |
| unprepared | no daemon request or implicit descriptor read; fixed prepare failure and proven-no-send drain |
| getter_exception / daemon_error | fixed closed failure, no raw exception/daemon string, late duplicate cannot replace first outcome |
| throw_retained | synthetic `request_exception` reply is not daemon drain; actual late callback only drains; no late data getter/second reply |
| throw_unknown / never_callback | no guessed drain, no resend; unresolved owner remains with caller/coordinator |
| sync_send_held | synchronous daemon callback does not end send ownership; success reply waits for send return |
| getter_fence / consumer_fence | send return alone is insufficient; drain remains false while callback getter/consumer executes; duplicate during getter does not enter twice |
| sync_then_throw / sync_error_then_throw | send failure overrides an uncommitted success candidate; first actual failure is immutable; both real callback and send unwind required |
| API / encoding / request unavailable | proven pre-send failure can reply/drain once without inventing a daemon wait |
| off_main_prepare / prepare_exception | no off-main descriptor/capture; fixed prepare failure without capture |
| consumer_exception | consumer invoked once; no second error reply to the same throwing consumer; finally drain still occurs |
| handoff_not_return | deliberately holding the notification receiver shows callback stack return is still unobserved; duplicate callbacks start no new data/getter/consumer work. This blocking receiver is a test demonstration, not an allowed integration pattern |

The four-byte byte-transport sample is deliberately not a valid complete JPEG.
The coordinator's ImageIO metadata contract must reject malformed JPEG separately;
the bridge only validates NSData type, nonempty length, and the8MiB transport cap.
No tests alter NG2/R12 sources, coordinate tables, or production iPhone11 paths.
