# 最新状態

更新: 2026-11-10（日本時間）。TEST061実装・配布前検証中。[全体設計](plans/test061-verified-progress.md)・[検証記録](reviews/test061.md)。新IPAは未配布。回収済みTEST060は再実行しない。

## TEST061の修正

初歩の確実な未送信失効は、旧IDを撤回し元12秒以内でライブHUDを再取得する。ACK後は次拍の入力期限と、元source/phase各3秒・walk45秒・session180秒の画像確認期限を分ける。途中35pxはUNKNOWNのまま待ち、真の移動/開通を確認後に次行動を決める。旧次拍が過ぎていれば新しい将来拍へ同期する。実commitとC処理後の実時計も期限を検査し、UNKNOWN再送・閾値緩和・移動の推測は行わない。

API1.98.15-ngg2/cap13/client v14。失効前model/sampleの最初・最新snapshotを保存し、旧v1〜v13 journalは保存API1.98.14で回収する。Beat/Nav/Perception/Raster/入力座標・R12原40/G1は不変。source sealと実IPAの同一性はビルド後に確認する。

旧Cで途中停止のassertion Redを確認。修正Cの独立商店worldは四方向×木鉄8例＋LEFT→UPの曲がり＋処理遅延のみの計10ケースで、開扉→進入→商品/PAUSEが成功。合成clock/画像であり、実機の到達率・毎拍・速度の合格ではない。関連client212method成功。C全回帰・Swift公開結合/故障・実IPA/compiler・全source照合の最終結果は検証記録へ追記する。

## 直前TEST060の受領事実

[受領記録](device-tests/README.md#test060-received)。商品確認0/2。1回目inputs/moves0でBEAT停止。準備上限より約118ms前にPAUSEへ移ったが、途中25画像とmodel/sampleの欠落により失効内訳は断定できない。

2回目LEFT1、C計上moves0、LATE停止。実Cの28→32比較はUNKNOWN。画像は約34〜35pxずれるが既存の1歩完了条件を満たさず、適格確認画像1枚だけで元motion期限の2.603ms後に停止。原参照27でもUNKNOWN。両runともlead_confirmed0で連続歩行の予約gateへ未到達。期限/認識閾値を緩めず、未収録の未来画像を作らない。

TEST060 code `04b213f27364bc9e5cf3c68f9caf031f842fba97` / [Mac91](https://github.com/shuhei0720/necrogold-automation/actions/runs/42632308407)。配布物・旧検証件数は[配布時の固定記録](https://github.com/shuhei0720/necrogold-automation/blob/42e625b0311c79c6d3e6acf19a150b9316fcc2a4/docs/status.md)と[review060](reviews/test060.md#test060-final-mac)へ保存。CI成功を実機合格に数えない。

## 運用・未受入

[最新開発方針](development-flow.md#最新の運用方針2026-11-10-日本時間): 固定時間なし、品質を落とさず変更範囲で単体/関連回帰と必要な結合を選ぶ。focusedを手動既定、fullは明示的な節目だけ。新実装の返却時は検証済みIPA/完全source・更新/再起動・iSH手順を示し、runtime全ZIPの実機返却を必ず依頼する。

ユーザーはMacを持たず、実機試験を担当する。CIのMac実ゲームは正規ゲーム導入/認証/起動が未成立。通常利用はiPhoneだけで完結する要件を維持する。商品到達率・毎拍/人より速い処理・対象指輪の未知評価・通知・自動周回・耐久は未受入。

初読3文書は16KiB以内。[作業索引](context.md)から必要な正本/関数/試験へ進む。rawZIP/画像/report/logはGit外。公開releaseは作らず、標準public CIのArtifactsへ保存する。
