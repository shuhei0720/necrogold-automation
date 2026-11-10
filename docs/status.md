# 最新状態

更新: 2026-11-10（日本時間）。TEST064の実機4回をユーザー報告で受領。1〜3回目は商品可視位置へ到達、4回目は2歩で停止（商品可視3/4）。ZIPは添付カード表示後「Codexとの接続は無効になりました」。再試行も失敗、ZIP未着・実行環境は稼働中。Safariは未試行。自動商品判定・4回目の原因は未確認。再ビルド/再実行より元runtime/test-064の受領・解析を優先。[受領台帳](device-tests/README.md#test064-reported)。

## TEST064: 遠方の描画揺れで同じ予約を失わない

[計画](plans/test064-stationary-step.md)。実画像は全て正常FLOOR判定。直接原因は遠方1cellの変化に対する未送信予約の再検証。認識閾値を変更しない。

- 初歩: 初期2回の再予約後にモデルを再取得。83→84は遠方DIRT→UNKNOWN、同じ全5field/金/保護/strict BLOCKEDだが、actual commitがnotBefore−90.060msで旧quiet50ms窓外。既に公開した初歩ticketの100ms窓へquietを広げる。準備50ms、未発行時刻、replan≤2、元sync12秒は不変。
- 開扉後: 120→121と139→140は同じ入口FLOOR1歩、商品PARTIAL、金/保護/全5field/strict BLOCKED不変。遠方DIRT↔STONEだけでも既存safe_floorがgate/PARTIALを拒否していた。実移動/lead確認済み・state1確実未送信・同じ入口1歩だけ、局所床/金/保護/判断/実motion/元期限を再検査して同IDを維持する。再予約・入力再送・source/期限延長はしない。

Controller.cだけを変更。Navigation/Perception/Runtime/公開ABI/API1.98.15-ngg2/cap13/client v14は不変。商品VISIBLE/取消/owner/lock/prefix/未知入力優先を保持する。下方の商品は未観測であり陰性にせず、停止箇所の先は既存plannerで進める。実機到達は未確認。

## TEST064配布と検証済み同一性

固定配布: [IPA build98](https://github.com/shuhei0720/necrogold-automation/releases/download/test064-build98/LoopCtrl.ipa)・[完全source ZIP](https://github.com/shuhei0720/necrogold-automation/releases/download/test064-build98/source.zip)。code `3d8334249394ae81ed8d449d4925dc2eb85c35d3`、[Mac98/device](https://github.com/shuhei0720/necrogold-automation/actions/runs/42747426496)成功。TEST064の実機はユーザー報告3/4商品可視、ログ未受領。[検証](reviews/test064.md)。

| 配布物 | 同一性 |
| --- | --- |
| 内部IPA | build98 / SHA `34a588f1e53808f97e62681df83513b9d1b38456d66dfda8bc0e5a4992af0c53` |
| IPA外ZIP | artifact13731848321 / 17,842,056bytes / SHA `6ba6b4416d3b1420ca4114ca207eb8be0584a11f339dde79e9dd7e460b835e9e` |
| 診断ZIP | artifact13732821205 / 156,926bytes / SHA `161470321ec1c114579781366408606fddfc4c5dcc4d00125c2a5080b6141e5f` |
| native-host | artifact13732285934 / 7,239bytes / SHA `ed12ebdd8df5808232f29f3b927452a3db7b4108e175b701902564198e114720` |
| build-source | 全488tracked bytes/CRC/path一致、7,314,954bytes / SHA `7a49b3b0684ba3b79572ac5df10c1fac3a8b61127574e70fbc97fa6de01446b8` |

新11+関連16のC27、小selector3の30件を実IPAと同じpatched sourceで確認。独立差分レビューP0/P1/P2なし。元画像2組は新入口helper適合、初歩は実画像の5field/strict BLOCKEDと記録時刻を確認。未収録のmodel/timeを補った完全実機再生ではない。

22seal中Controllerだけ変更/他21・R12原40/G1不変、実4C/5Swift/6RSP/PBXとraw compiler引数、全9Mach-O/101 HOST・旧API marker非混入を照合。API15/cap13/ABI不変。完全source最終版はこのcodeとの差分がstatus/review/台帳の3文書だけであることを確認し、固定Releaseへ保存する。全Runtime/world/不変client/不変workflow-publisherを今回再実行しない。

## TEST064手順（配布時の記録）

SideStoreで新IPA/build98更新→LoopCtrl完全終了/起動→Start Server→通常VPN/disk。新しい通常オールゾーン1-1の金壁可視・左側が下/端0の開幕ポーズから。

```sh
mkdir -p /mnt/necro_test064
mount -t ios . /mnt/necro_test064
cd /mnt/necro_test064 && sh test_064.sh
```

folder pickerは完全source ZIPを展開しtest_064.shが入っているフォルダ。歩行中はゲーム前面、自動PAUSE後約5秒でiSHへ戻り「TEST-064: 終了」を待つ。新しいランで商品可視位置まで、特に下方商品への追加移動と0歩停止を実機確認し、runtime/test-064全ZIPを依頼する。受領待ちの4runを追加回収目的で再実行せず、元runtimeを保持する。

## TEST063の記録

[配布/検証](reviews/test063.md)、[固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test063-build96)。code d7b42b627caa0e1c28b1c4a4900f2e0bc1a22323、最終source365af6978117c202299fbf88cfae482986fbcbe7、Mac96/device成功、固定配布Mac97成功。IPA build96 SHA `61e0e40c0f78e226d64aae97dfc053aaba3638ca52d12014be268c21dcb09b06`、source SHA `10f2043c5c7a24f85d6a08073b2ecd74b7f71e10bf6cdf3ecb6b626bba2cbad8`、認証なし固定URL取得200/一致を確認済み。

1回目7b881は5移動+開扉1、商品3点と価格100/125/25が見えるがCはPARTIAL。2回目9c778は5移動+開扉1、未送信3歩目からの再同期1回後も歩行し、入口MOVE10の前で停止。3回目7f9は0入力、再取得後のMOVE5前で停止。SCREEN17を画面分類不良と読み替えない。[受領台帳](device-tests/README.md#test063-received)。

## 運用・未受入

[最新方針](development-flow.md#最新の運用方針2026-11-10-日本時間): 実機ログ→局所修正→単体/関連回帰→必要なIPA/同一性確認→次の実機。固定時間なし・品質/安全条件不変。通常は独立差分レビュー1回。コード/資料は承認済みbranchへ保存し、raw ZIP/画像/report/log・秘密値はGit外。配布は固定Release asset。

ユーザーはMacを持たず実機担当、通常利用はiPhone単体。商品到達率・完全商品判定・毎拍/人超え・指輪未知評価・通知・自動周回・耐久は未受入。初読3文書≤16KiB、追加資料は[索引](context.md)。
