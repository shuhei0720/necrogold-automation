# iPhone 8 capture-only probeのレビュー・検証

2026-11-16（日本時間）。[計画](../plans/iphone8-capture-probe.md)に対応。
**実装・host検証中、未配布。iPhone 11への接続・導入なし。** 通常TEST107、既定launcher、旧G1/G2 source・seal・workflowは維持する。

## 設計レビュー

基準は文書更新済み `f64e694` と固定LoopCtrl upstream
`6e25cf6a9f65bc86c372cdce94bdb151d0cf6767`。旧nativeは前基準 `95eb3b9` と同じbytes。

| 周回 | 指摘と対応 |
| --- | --- |
| 1 | 資格判定、IDの有限保持、受付期限、旧回収の継続、送信例外と実callback終了の分離、cycle prepareの副作用を具体化 |
| 2 | 旧callback末尾・app screenshot worker・非同期VT consumerまでの共存観測が必要と判明。これらの旧実装を修正済みとは扱わない |
| 3 | 8専用capture-only buildへ縮小。fresh process・旧資料検出時busy・旧producer開始0で共存を避け、独立NG8 bridge/overlay/二重封印を採用。設計/網羅/安全の残P0/P1なし |

最終の認証P1は、remote configの純読取と端末上のrevokeを区別して解消した。
既tokenだけを継承し、このmodeのPOST /pairと承認UIは無効化する。
typedなtrusted in-process adminだけにlocal read/revoke/pauseを許可し、callerのJSONやloopback推測から昇格させない。
全5 listener生成箇所で同mode/coordinator/runtime ID/seen/元期限を保持する。

この判定は設計の成立性だけを示す。起動入口のproducer開始0、認証origin、完全drain、通常11のfalse path同値、二重封印・実compiler・8実機は、実装後の必須gateである。

## 初回TDDの対象

最初は独立NG8 bridgeのcompile可能な未実装stubと、実Objective-C境界を通すfake daemon fixtureを用意する。
標準macos-26でcompile成功後、`primary` の
`FAIL capture_one_daemon_request` / exit 1を実測してからGreenへ進む。
compile・環境失敗はRedに数えない。23ケースの準備や静的レビューを、実行成功とは記載しない。

専用workflowは承認済みbranchと専用pathだけのpushを対象にし、閉じたhost phaseを実行する。
この段階ではIPA作成・導入・公開Releaseへの到達はない。通常workflowを変更しない。

初回実測は[Actions 43833216314](https://github.com/shuhei0720/necrogold-automation/actions/runs/43833216314)、
commit `9f86c93c6e316582efe78842dd2472e781f79e69`。
macos-26でObjC compile成功後、指定assertion/exit1/空stderrを確認した。
CI reportの4 source SHAは当該stub/fixtureと全一致。これはbehavior Redの成功であり、取得処理のGreenや実機成功ではない。

bridge実装レビューのP1は、SDKがcallback後のliteral return ACKを持たない点だった。
新8 capだけは全owned data/getter/primary consumerとsend終了後のfinal handoffを境界とし、
通知後のmutable workを禁止する。wireは`callback_body_handoff_ns`と`callback_return_verified=false`で未証明を明示する。
独立確認の残P0/P1なし。旧native契約は変更せず、producer開始0・nonblocking receiver・受け側jobの別追跡はintegrationで検証する。
### 拡張Redとhost Greenの実測

[run43842351667](https://github.com/shuhei0720/necrogold-automation/actions/runs/43842351667)、job133213889275、commit `9d1bfa6c08168cde044e73aba40826bceac5522f` でSwift compile成功後、Core全32 selectorを実行した。31件は指定first FAIL/exit1、`default_unqualified` だけ0 FAIL/exit0、すべてstderr空。全FAILラベルと件数をreportへ保存し、modeもqualification/metadata/routes/bindingの4 selector×両flagsで8件の指定FAIL/exit1を確認した。Bridgeはcompile後の `encoding_unavailable` がSIGSEGV（return_code=-11）、FAILとstderrは空、閉診断より前に停止した。これはassertion Redではなくblockedである。

NEW8だけのalloc/init ARC ownership修正、CoreとmodeのGreen候補は各独立レビュー後にfreezeした。Coreレビューのfresh-clock P1は、外部gate後に時刻を再取得する修正を確認し、残P0/P1なし。fixture・既assert・Red期待JSONは変更しない。

[run43847996126](https://github.com/shuhei0720/necrogold-automation/actions/runs/43847996126)、job133232962600、commit `3ece8519f15e2a0bfcb86439e04d8f42910aba22` は標準macos-26で全componentのcompileと実行に成功した。

- Bridge: 26 selectorすべてexact PASS/exit0/空stderr。前回SIGSEGVのselectorも成功。
- Core: 同32 selectorすべて0 FAIL/exit0/空stderr。
- mode: 同4 selector×両flagsの8件すべてexact PASS/exit0/空stderr。

実reportの9 source/fixture/JSON SHAは実行commitのGit blob・review freezeと一致する。implementation SHAはBridge `202ab11d5c25226b392e9637f24ba1226b8841f0ec255c997f0e72bd2225ba5c`、Core `9a98b03c02f47b4460add0c697a345447c872c98f0aaa14dfc35f3fd84cb470d`、mode `b8cca3c87af2021ec8eddf42399b10f1f43635367b2ade8ef52db8838245dc8f`。この8-file commitは専用module/checker/stage/READMEだけで、fixture・旧native/R12・通常workflow変更0、IPA/端末/Release操作0だった。

これは独立host componentのGreenであり、実機capture・production ImageIO adapter・実認証/router・5 constructor接続・producer開始0・二重封印/実IPA・iPhone 11受入の証明ではない。reportは `input_authorized=false` / `device_acceptance=not_run` / `callback_return_verified=false` を維持する。

## 現在の証明範囲

旧R12は40ファイルすべてmanifestと一致し、座標/capture/raster/閾値を含む保護対象99件は前基準と同じbytesだった。
これはsource検査であり、iPhone 11の物理受入や未移送の旧資料の代用ではない。

既TEST107による8の限定操作ではAll Zones 1-1到達を確認したが、本probe・8 native入力profile・正規START-03の自動一連・商品到達の受入には含めない。
原画像・端末ID・鍵・全ログはGit外に保持する。旧資料移送は未解決。
