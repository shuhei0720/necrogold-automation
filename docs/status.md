# 最新状態

更新: 2026-11-10（日本時間）。TEST063受領: ユーザーの商品可視1/3、プログラム完全商品判定0/3。2回目は開扉後の次MOVE前、3回目は初歩前に停止。受領43PNGの全SHA/bytes/CRC/896×414、manifest一致、全3run terminal/drained、activeと最後のreport一致を確認した。回収済み063を再実行しない。

## TEST064: 遠方の描画揺れで同じ予約を失わない

[計画](plans/test064-stationary-step.md)。実画像は全て正常FLOOR判定。直接原因は遠方1cellの変化に対する未送信予約の再検証。認識閾値を変更しない。

- 初歩: 初期2回の再予約後にモデルを再取得。83→84は遠方DIRT→UNKNOWN、同じ全5field/金/保護/strict BLOCKEDだが、actual commitがnotBefore−90.060msで旧quiet50ms窓外。既に公開した初歩ticketの100ms窓へquietを広げる。準備50ms、未発行時刻、replan≤2、元sync12秒は不変。
- 開扉後: 120→121と139→140は同じ入口FLOOR1歩、商品PARTIAL、金/保護/全5field/strict BLOCKED不変。遠方DIRT↔STONEだけでも既存safe_floorがgate/PARTIALを拒否していた。実移動/lead確認済み・state1確実未送信・同じ入口1歩だけ、局所床/金/保護/判断/実motion/元期限を再検査して同IDを維持する。再予約・入力再送・source/期限延長はしない。

Controller.cだけを変更予定。Navigation/Perception/Runtime/公開ABI/API1.98.15-ngg2/cap13/client v14は不変。商品VISIBLE/取消/owner/lock/prefix/未知入力優先を保持する。下方の商品は未観測であり陰性にせず、停止箇所の先は既存plannerで進める。実機到達は未確認。

## 検証と配布の進行

旧Cで新初歩5methodの意味的assertion Red（errors0）と新入口の正常系Redを確認。修正後は初歩5+旧quiet3、入口6がローカルGreen。独立差分レビューP0/P1/P2なし。device laneの変更単体/関連回帰、実IPA/22seal/実compiler/完全source照合を行い、固定ReleaseでTEST064を依頼する。全Runtime/world/未変更clientを配布前提にしない。

## TEST063の記録

[配布/検証](reviews/test063.md)、[固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test063-build96)。code d7b42b627caa0e1c28b1c4a4900f2e0bc1a22323、最終source365af6978117c202299fbf88cfae482986fbcbe7、Mac96/device成功、固定配布Mac97成功。IPA build96 SHA `61e0e40c0f78e226d64aae97dfc053aaba3638ca52d12014be268c21dcb09b06`、source SHA `10f2043c5c7a24f85d6a08073b2ecd74b7f71e10bf6cdf3ecb6b626bba2cbad8`、認証なし固定URL取得200/一致を確認済み。

1回目7b881は5移動+開扉1、商品3点と価格100/125/25が見えるがCはPARTIAL。2回目9c778は5移動+開扉1、未送信3歩目からの再同期1回後も歩行し、入口MOVE10の前で停止。3回目7f9は0入力、再取得後のMOVE5前で停止。SCREEN17を画面分類不良と読み替えない。[受領台帳](device-tests/README.md#test063-received)。

## 運用・未受入

[最新方針](development-flow.md#最新の運用方針2026-11-10-日本時間): 実機ログ→局所修正→単体/関連回帰→必要なIPA/同一性確認→次の実機。固定時間なし・品質/安全条件不変。通常は独立差分レビュー1回。コード/資料は承認済みbranchへ保存し、raw ZIP/画像/report/log・秘密値はGit外。配布は固定Release asset。

ユーザーはMacを持たず実機担当、通常利用はiPhone単体。商品到達率・完全商品判定・毎拍/人超え・指輪未知評価・通知・自動周回・耐久は未受入。初読3文書≤16KiB、追加資料は[索引](context.md)。
