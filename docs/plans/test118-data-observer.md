# TEST118 DATA release: one synchronous observation snapshot

This is a host-fixture change only. CI262's current source46 returned a normal
complete policy17 NEGATIVE, but C adoption exceeded its unchanged worker
deadline by 17.045875ms. The timed release path includes `report(id)` and
`cycleCompanion(id)`. Their individual costs were not recorded, so this plan
does not assign the whole delay to either RPC or promise a later pass.

The production Controller535a9f, Runtime58c6, Ringf62, native37 manifest,
generator, physical phase, RGBA, ACK model, source150ms and worker100ms stay
unchanged. The CI262 Green `testRuntime118Preinput` and
`testRuntime118Upper` bodies stay byte-identical. All DATA assertions, normal
Ring production, the far-material observation, full NEGATIVE, durable RS and
next-child requirements remain in place.

## Source scope

Only `check_runtime118.py`, `ngg2_runtime118_fixture.c`, and DATA-related
declarations/hunks in `ngg2_runtime118_tests.swift` are implementation targets.
No production source or public production ABI is edited or resealed.

The Controller host object receives one additional compile-only alias:
`ng2_controller_observe_irregular_at=ng2_controller_observe_irregular_at118_actual`.
The fixture defines the original public symbol as a wrapper. It calls the
actual function exactly once, with the original pointer, arguments, stable
flag and commit timestamp, and preserves its void return semantics.
The source/object/Bridge/nm evidence must disclose this fourth alias and both
symbols. Existing begin, tick and preparation-epoch wrappers are unchanged.

## Exact one request and snapshot

DATA alone installs a fixture callback/context before its run. Immediately
before the first palette frame's real C call, the existing
`beforeAnalysisFrameCommit` hook arms one immutable request containing that
frame's exact capture ID, start, end and prefix and the expected current
worker's nine identities. Root identity is the Controller `started_ns` from
the already-existing initial-RS report; reuse that same report response
instead of adding an RPC, and require the copied status to match it.
It does not substitute any C input or result.
No later frame may replace an unanswered or rejected request.

Within the matching real observation wrapper's synchronous dynamic extent,
after the unchanged actual C observation returns, copy the public
`NG2ControllerStatus` and `NG2ControllerCycleStatus` into stack PODs using
`ng2_controller_status` and `ng2_controller_cycle_status`. These are two
read-only getters, once only. Both snapshots come from the same live core on
the same serial controlQueue while Runtime owns its observation gate.
No core pointer or stack pointer is retained. The callback copies POD values
into the DATA fixture cache only; it performs no assertion, signal, RPC,
decoding, Perception, file serialization or clock advance.

Request/input metadata mismatch, C rejection (`status.last_capture_id` does
not match the requested actual input), missing response, skipped call or
current identity mismatch must fail closed. A copied snapshot must never be
relabelled as a later frame or job. The cached result retains the actual call
metadata and a matching flag; the original last-capture and pending guards
are checked before release, not replaced by an expected-value claim.

The root current worker remains physically blocked before normal producer
execution while this request is observed. The callback and release therefore
refer to that same run/current job, not a child. C calls are serialized; no
other controlQueue callback can interleave between this observation and its
following `beforeControlTick`. The production deadline/cancellation guards
and original worker check still reject an elapsed or cancelled run.
The callback/request are uninstalled in the case defer, after the existing
cancel/drain sequence; the context remains strongly owned for that lifetime.

## Clock and release order

The required order is:

1. Original `cost.beforeObserve` starts its real measurement.
2. The wrapper performs the original C call, two getters and POD callback.
3. Original `cost.afterObserve` charges the entire wrapper/getter/copy cost
   to the existing fixture clock, once.
4. The existing post-cost `afterObserve` marker records the actual palette
   ID. `DATA_ORDER.observe_return_ns` remains at this original post-charge
   point and must still equal the original capture's `observe_end_ns`.
5. The original `beforeControlTick` release point reads the cached POD,
   verifies `last_capture_id == palette` and the unchanged pending/current
   job, source, source-start, prefix, level, worker-start, deadline, hold and
   parent identities, then signals the same semaphore.
6. The original worker whole-hook maximum accounts for any remaining real
   hook work without adding already charged observation time twice.

There is no signal in the C wrapper or POD callback. There is no separate
snapshot-cost advance, altered `passed_now`, fabricated tick cost or moved
phase. Other two cases never install/request this callback and execute no
new read getters. Their method bodies and existing cost-hook behavior stay
unchanged.

## Alternatives and evidence

The existing tick wrapper cannot supply this pending snapshot: with the
worker's drain token live, `waitForCycleAssessmentBeforePause` skips the
actual tick while `beforeControlTick` still runs. Waiting for a tick callback
would create a release cycle. A retained raw core pointer is rejected because
its cancellation/destruction lifetime cannot be proved before dereference.
`testCachedControllerCapture` reads `reportSnapshot`, which can lag; it also
lacks the nine worker fields. An after-observe ID alone does not establish C
acceptance. Pure postdrain reconstruction cannot preserve the timed pending
guard. These alternatives therefore do not retain the same condition.

Keep existing `DATA_ORDER` (13 fields) and `CURRENT_DATA` (11 fields).
A separate postdrain `CURRENT_SNAPSHOT` witness will bind the actual palette
request/input metadata, copied status/worker identities and post-observation
charged timestamp to the original capture/report. Its closed schema and
fourth-alias reader change require a separate source review before pinning;
they cannot turn a failed original case into a pass.

No implementation, compile, CI, reclassification, retry or artifact-reader
gate is authorized by this plan alone. Source-review P0 closure and root
implementation authorization are required first.
