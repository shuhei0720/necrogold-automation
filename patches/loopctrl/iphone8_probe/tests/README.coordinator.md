# NG8 coordinator host TDD

[純state core](../assets/NG8CaptureProbe.swift) と [専用Swift fixture](NG8CaptureProbeTests.swift) のTDD段階。初期qualified caseは実macOS run43837286672/job133196971358（commit fa768790）でcompile成功→7 expected FAILを確認した。拡張版は[run43842351667](https://github.com/shuhei0720/necrogold-automation/actions/runs/43842351667)/job133213889275（commit9d1bfa6）でcompile成功後に全32 selectorを実行し、31 expected Red/exit1と `default_unqualified` の0 FAIL/exit0、全stderr空を実測した。source/fixture/期待JSONのSHAは当該commitと一致し、全FAILラベル・観測件数をreportへ保存した。現在はGreen候補の実装・host検証段階であり、実Mac Green・実機受入は未確認。Bridge担当のREADME・ObjC fixtureとは別scopeである。

repo rootから、macOSのFoundation/ImageIO/CryptoKitを使ってcompileする。出力先は既存の私有一時directoryを指定する。

```sh
swiftc -swift-version 5 -Onone -parse-as-library \
  patches/loopctrl/iphone8_probe/assets/NG8CaptureProbe.swift \
  patches/loopctrl/iphone8_probe/tests/NG8CaptureProbeTests.swift \
  -o <private-temp>/ng8-probe-host-tests
<private-temp>/ng8-probe-host-tests
```

引数なしは `qualified_capture` だけを実行する。qualified・新ID・active owner・旧spool clean・合法JPEG・全job終了を用意し、capture1回→ready→原bytes/length/SHA/EXIF一致を要求する。追加版でも初期caseの7 assertと期待FAILは不変。compile失敗/環境不足/他の例外をRedに数えない。fixtureは公開生成8×6 JPEGで、実機画像ではない。

既10＋追加22の全32 selectorとstub時のfirst FAIL/exit期待は [期待JSON](coordinator-red-expectations.json) に固定した。selector名を引数にして個別実行、`all` で全件実行できる。stubでは `default_unqualified` だけ0 FAIL/exit0、他31件は意味assertion FAIL/exit1を期待する。初期の一部selectorは共通start受理assertが最初に落ちるため、その後の全FAILも記録する。追加selectorは汎用setup assertを先頭へ置かず、各契約をfirst FAILにした。既定falseの拒否だけが通っても全体Greenとしない。Green後は同32 caseすべてに `ASSERTIONS_FAILED 0` / exit0を要求する。

専用host phase `bridge-green-components-batch-red` は、凍結JSONのstub source/fixture SHAを照合し、各caseのfirst FAIL/exitと出力全体の閉形式を検査した。JSONの件数nullは初回実測前の期待値として保持し、観測件数はreportへ保存する。次の `bridge-core-mode-green` は同fixture SHA・32 selectorを保持し、全caseにexit0・0 FAIL・空stderrを要求する。各caseの全FAILラベル・件数・exit・stderr有無をreportへ残し、1件の不一致後も残るcaseと他componentを検査する。compile/timeout/fixture前提不成立はRed/Green成功に数えない。mode4 selector×2 flagsとbridgeも同時実行するが、実機・IPA・旧nativeの成功を意味しない。

main/worker/受け側coordinator jobの実returnと、bridgeのreply候補/最終owned-work handoffを独立に注入するhost model。bridge通知receiverはenqueueだけで解析/hash等を実行せず、受けjobの実終了も待つ。`callbackEndNs` の意味はwireの `callback_body_handoff_ns` で、`callbackReturnVerified=false` を固定する。literal daemon block returnや実ObjC finally/内部cleanupの証明ではない。

chunkの `limit` は最大返却bytes数で、非bool整数1..65536。`offset + limit` の加算overflowを先に検査し、`end = min(checked offset + limit, byteLength)` とする。`offset` が負又は実長以上、加算overflow、hash不一致は拒否する。残りbytesがlimitより短い最終chunkは、その残りだけを返してよい。従って668Bのfixtureへの `offset=0, limit=65536` は全668B成功が正しく、既存qualified assertは変更しない。

## 追加Redの範囲と残る未実施gate

[正式計画](../../../../docs/plans/iphone8-capture-probe.md)に従い、次の契約のRedを追加し、全32 selectorをstubのまま上記Mac phaseで実測した。既assert削除0で、Redの成立をGreenや全計画の網羅済みへ読み替えない。

- generation 1..128と129件目拒否、前64件退役/tombstoneと後64件cached、退役IDの再取得0。
- 同IDの繰返し、cancel/TTL後の同ID、別ownerによる同IDの再取得/metadata/raw公開0。
- owner pause/revokeをprepare・request・commit・export各境界へ注入する。現revoked-owner caseだけで全境界済みとしない。
- chunkの負値/非整数/Bool・limitの0/上限超過・offsetの実長以上/UInt64.max・hash不一致、最終chunk短縮と原slice一致。
- 公開JPEGのEXIF全1..8・欠落nullの原bytes/metadata保持、不正なtyped orientation/寸法/画素数、空/8MiB超過、inspector失敗時のraw非公開/reason保持。
- busy拒否IDの未消費、stale generationのlate callback、受け側coordinator jobの実終了fenceとliteral-return非証明flag。

Bool/小数のEXIFや実JPEG/count等を含むproduction ImageIO adapterの拒否、実8 qualification/auth boundary、8MiBちょうど/128chunkの全回収、実thread並行/ObjC handoff/実fresh processは別の未実施gate。typed metadata seamや公開生成JPEGだけでそれらを済みとしない。追加caseのfixture前提不成立は `FIXTURE_ERROR`/exit2で止め、assertion Redへ数えない。

認証boundary・実8 qualification・production ImageIO inspectorとその実接続はRoot integration担当。coreは信頼されたtyped値/clock/owner/old-evidence gate/driver/schedulerを注入されるstate部分だけを担当する。wireからqualification/ownerを作らず、通常11・旧native/G1/R12を変更しない。fixtureのImageIOはmetadata検査だけで、full raster decode・resize・rotate・再encodeを行わない。
