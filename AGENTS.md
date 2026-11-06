# Project instructions

## Read before making changes

Read `README.md`, `docs/status.md`, `docs/development-flow.md`, `docs/requirements.md`, and `docs/video-2-analysis.md`.

Follow the user's `shuhei0720/AI-Driven-Development` Codex workflow, identified in `docs/development-flow.md`. Separate requirements from the eight-part plan. Review the plan independently by design, edge cases/test coverage, and security; use subagents with fresh context, no implementation history, and inherited model settings. Limit review/fix rounds to three and record remaining issues. Build behavior tests with observed Red → Green → Refactor, not after-the-fact success-only checks. Human review of test expectations and implementation is part of the workflow. Current work is P1 measurement tooling and host tests; device acceptance and gameplay implementation remain gated.

## Current scope

The user accepted TEST-015's observed nine quick restarts followed by gold detection and pause. Actual median new-scene observation interval is 4.171757 seconds; human-faster performance is not established. The authorized feature is TEST-016/017/018/019/020: after gold detection, move with beat alignment to a merchandise-visible position and pause, using edge-control layout 0 and the same left-side-down orientation. Prepare a bounded real-device increment with per-step observed displacement and goods visibility, preserving unknown versus absent and no auto-purchase. Do not replace beat alignment with fixed-interval spam. Source-frame and input timestamps/cancellation remain limited by NG-G1; report inferred timing and empirical device success separately. TEST-016 found gold after eight restarts but failed after resume with internal_error, zero movement and final pause unconfirmed. TEST-017 fixes the reproducible scalar-only Pillow incompatibility and cleanup/diagnostics; the actual device exception was not retained, so do not call its direct cause proven. TEST-017 had no analysis exception on Pillow8.2 but spent4.2–5.7s per navigation frame; eight samples spanned36.660922s, exceeding fit20s, with zero movement. TEST-018 changes only tile statistics to parity-checked native i386 and bounds new sync capture starts to12s. TEST-018 device navigation is native_i386 at median1.012s, but full navigation per beat sample still caused timeout with7 samples; no movement, final pause confirmed. TEST-019 skips navigation only during beat collection and requires a fresh full scene, goods-first latch, compatible/refitted live phase and deadline checks before movement. Missing scene cannot authorize direction input. New30fps video yields period~0.522s, not an input-acceptance window; do not hardcode its epoch or cadence. TEST-019 established one right step and final pause at estimated period0.52160s; shop approach failed because the target was left. run101 reproduces right-routing when lit floor medians39..45 exceed old38 cap; first command frame was not retained. TEST-020 adds a narrow textured bright-floor band disjoint from existing stone/dirt, preserves all73 motion scores while moving integer statistics to native i386 (TEST019 motion4.47172s), and reacquires beats if prior observation is stale. Latest input-before image is reserved run-099.jpg. Direction coordinates unchanged; left approach, continued walking and human-faster performance remain unverified. Received manual walking video and user-confirmed cursed-ring image are evidence, not a completed ring classifier. GitHub saving remains authorized. Do not add raw logs/images/ZIPs or duplicate plans/review documents to git.

## Functional and performance requirements

- Runtime target: the user's iPhone, Japanese NecroDancer, normal all-zones 1-1.
- Normal startup must resume directly from GAME PAUSE. Do not open Options as a normal calibration step.
- The user's physical orientation is “left side down”; screen-edge controls, setting 0, was shown. Validate the actual px/pt transform on the device. Do not infer input coordinates from a resized video frame.
- Human-faster operation is a core acceptance condition. Measure capture, decoding, detection, command submission and visible input effect separately and end to end.
- Current MVP follows the latest user decision: only pursue runs with initially visible gold, including partial gold. Skip valid initial frames without gold; label these as out of opening scope, not globally shop-free. Hidden-shop exploration is future work. Both wooden and iron doors, horizontal and southern entrances remain required.
- Keep observed absence distinct from unobserved or occluded goods. Hold a target candidate before sending more movement/restart commands. Never buy automatically.
- Do not treat an old game frame as authorization to tap after a foreground change. Distinguish transient loading black frames from persistent invalid capture. Bound retries and make cancellation interrupt pending commands.
- The user expects complete code. Save full files without ellipses and provide links to the source, together with explanations and exact validation status.

## Evidence and validation

- Preserve `legacy/r12/` byte-for-byte. Its 40 files are described by `docs/r12-source-manifest.json`. Make future implementation changes outside this archival directory.
- Existing mock/offline tests do not establish that resume, orientation, image capture, navigation or timing work on the iPhone.
- Do not report a provisional target as an achieved benchmark. The manual videos show human screen changes, not input-event timestamps or automated performance.
- Attach evidence and a measured result to each acceptance condition. An empty result is “not tested,” not “pass.”
- Label extraction source, timestamp, rotation, dimensions and hashes. The first video needs rotation; the second is already landscape. Neither justifies stretching every incoming image.
- Target-positive recognition and long-running device reliability remain unverified. Retain a genuinely unseen evaluation set when tuning recognition.
- Do not add pairing tokens, device secrets, personal runtime configuration, or raw credentials to git.

## Reporting

Use Japanese for user-facing documentation and explanations. Use Japan time for user-facing dates. State what changed, what was verified, and what still requires device evidence. Never promise absolute success without proof.

