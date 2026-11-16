# NG8 coordinator host TDD

[純state core](../assets/NG8CaptureProbe.swift) と [専用Swift fixture](NG8CaptureProbeTests.swift) の準備段階。実装は全入口 `not_available` のstubで、capture・queue・端末操作を行わない。実macOSのcompile成功とassertion Redを受領するまでGreen実装へ進まない。Bridge担当のREADME・ObjC fixtureとは別scopeである。

repo rootから、macOSのFoundation/ImageIO/CryptoKitを使ってcompileする。出力先は既存の私有一時directoryを指定する。

```sh
swiftc -swift-version 5 -Onone -parse-as-library \
  patches/loopctrl/iphone8_probe/assets/NG8CaptureProbe.swift \
  patches/loopctrl/iphone8_probe/tests/NG8CaptureProbeTests.swift \
  -o <private-temp>/ng8-probe-host-tests
<private-temp>/ng8-probe-host-tests
```

引数なしは `qualified_capture` だけを実行する。qualified・新ID・active owner・旧spool clean・合法JPEG・全job終了を用意し、capture1回→ready→原bytes/length/SHA/EXIF一致を要求する。現stubの期待結果は7 assertion FAIL・`ASSERTIONS_FAILED 7`・exit1。これは未実測の期待値であり、compile失敗/環境不足/他の例外をRedに数えない。初期fixtureは公開生成8×6 JPEG/EXIF8で、実機画像ではない。

他の準備済みselectorは `default_unqualified`、`queued_main_deadline`、`cancel_drain_fence`、`synchronous_reply_fence`、`prepare_cancel`、`revoked_owner`、`old_evidence_runtime`、`closed_params`、`ttl_chunk_bounds`。`all` で全10件、selector名を引数にして部分実行できる。既定falseの拒否だけが通ってもcoordinator全体のGreenとしない。main/workerの実return、bridgeのreply候補とaggregate drainedを独立に注入するhost modelであり、実ObjC callback finallyや実機drainの証明ではない。

chunkの `limit` は最大返却bytes数で、非bool整数1..65536。`offset + limit` の加算overflowを先に検査し、`end = min(checked offset + limit, byteLength)` とする。`offset` が負又は実長以上、加算overflow、hash不一致は拒否する。残りbytesがlimitより短い最終chunkは、その残りだけを返してよい。従って668Bのfixtureへの `offset=0, limit=65536` は全668B成功が正しく、既存qualified assertは変更しない。

## Green前に追加するRed

[正式計画](../../../../docs/plans/iphone8-capture-probe.md)の全ケースが既存10 selectorで網羅されたとは扱わない。次の契約を実装する前に対応するassertion Redを追加し、既assertを削除しない。

- generation 1..128と129件目拒否、正確な64件履歴退役/tombstone、退役IDの再取得0。
- 同IDの繰返し、cancel/TTL後の同ID、別ownerによる同IDの再取得/metadata/raw公開0。
- owner pause/revokeをprepare・request・commit・export各境界へ注入する。現revoked-owner caseだけで全境界済みとしない。
- chunkの負値/非整数/Bool・limitの0/上限超過・offsetの実長以上・加算overflow・hash不一致と、最終chunk短縮/8MiB/最大128chunkの境界。現overflow/hash/Bool-limit caseは部分検査である。
- 合法EXIF全1..8・欠落null・不正型/値・JPEG/count/寸法/8MiBの境界と、inspector失敗時のraw非公開・reason保持。

認証boundary・実8 qualification・production ImageIO inspectorとその実接続はRoot integration担当。coreは信頼されたtyped値/clock/owner/old-evidence gate/driver/schedulerを注入されるstate部分だけを担当する。wireからqualification/ownerを作らず、通常11・旧native/G1/R12を変更しない。fixtureのImageIOはmetadata検査だけで、full raster decode・resize・rotate・再encodeを行わない。
