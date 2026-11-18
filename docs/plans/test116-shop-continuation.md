# TEST116の商店停止を直す範囲

2026-11-18（日本時間）。[全体計画](test116-device-failures.md)の商店部分。

## 確認した原因

- 1周0084: 開扉117から120への上端ITEM消失は正常Motionの直接零であり、115の独立PARTIAL移行条件も成立する。しかし静止確認後の`cycle_credit`分岐には新移行の呼出がなく停止した。credit獲得前だけを直した境界漏れ。原117の通常RingはUNKNOWN/空、6.298ms。
- 3周36b6: 開扉188→190で115の新PARTIAL job2が成立した。その後191で元188と完全同じtop投影が戻り、currentの完全一致が停止した。原190/191とも通常RingはUNKNOWN/空、188/190/191間の正常Motionは直接BLOCKED零。191の全保護は旧188潜在領域に含まれる。
- 2周最後134e: 開扉後のUP13に原142がFULLとして現れ、元136→142の通常MotionはUNKNOWN。商品優先の旧契約で移動待機を終了した。原144は同じ元136から通常MOVED(0,-1)となるが、142→144の静止はUNKNOWNであり新GOLD/近傍材質変化もある。古い142を静止だったことにせず、元ACKの単回creditと新DATAの限定経路を設計する。

## 限定変更と期待値

1. 未消費のframing credit/確実未送信MOVEの状態でも、同じtop消失を独立した現在PARTIAL DATAへ移す。元親期限/同期期限/一回UP/共用DATA枠を保持し、旧予約と準備モデルを退役させる。begin済み・ACK・入力UNKNOWNを移さない。
2. 独立PARTIALの静止検査へ、固定の下段ITEM支持と旧潜在保護内だけのtop複製投影を合成する。旧current anchorは差し替えず、毎回そのanchorからの通常厳密零を要求する。新商品・下段/歩行床/元金壁の無根拠変化は拒否し、直接零2枚/新fit/元一回UPを維持する。ITEM認識の全体閾値や陰性条件は変更しない。
3. 元ACK後の早期FULLについては[商品優先契約](../contracts/native-control.md#10-商品優先)へ限定追記し、意味Redを先に用意した。候補DATAを優先し、元before/command/visual期限・評価数/間隔・prefix・一回creditを保持する。通常UNKNOWNからMOVEを捏造せず、元beforeから通常unitが出た時だけその元event/主MotionReferenceへ実後続captureを記録する。位置/visit加算は通常resolverと同じ小関数で一度だけ行い、UI入力stateを開き直さない。新source/jobのDATAと直接零2枚/新fitを経た未消費一回UPのみへ進む。未収録の後続商品結果を実機成功と扱わない。

## 検査範囲

各境界の実装前assertion Red、正常producerを使った手続き的な一回UP→全商品陰性→保存/リスタート、既115と113/114の該当回帰。新商品の出現・潜在領域外・候補/不正陰性・直接零不成立・source/prefix/期限・開始済み入力・取消の反例を選ぶ。Runtimeとの受渡し変更が必要なら該当Macケースだけ追加する。実機の改善完了と速度受入は次の電話試験で確認する。

## 作者検証の記録

商店C凍結`3596edf6`。新`test_native_partial116`4件/`test_native_early_full116`4件は正常producerを使い成功。PARTIAL移行のRedは2件の指定assert失敗、早期FULLはUNKNOWN/PARTIALの元sourceと未送信PAUSE有無の4指定assert失敗（3method/error0）。最初の逆投影案はobserveだけを直しbeginが拒否したため既assertを保持して共通静止述語をbeginにも適用した。

直接旧回帰は115商店11件、114current12件、113UP9件、094商品優先1件の計33件が成功。新旧41件の実行では製品assert失敗はなく、新trace追加assertの便宜getterが093harnessに存在しない試験導入誤りで4subcaseがerrorになった。assertを削除せず公開Cgetterへ接続し、凍結Cで該当1method/全4正例を再実行して成功した。最終統合Cでのhost/Runtime/IPA確認は全体工程へ引き継ぐ。

私的校正では原117→120の正常直接零/移行述語、原190→191の正常直接零/新top述語、原136→144の通常unit/新DATA述語が成立する。最後は原142の正常結果と記録時刻を置いた宣言最小contextで、位置6→7・元event観測144・新job5/source144/pending1/input0を確認した。失われたprivate stateの復元や電話成功とは区別する。
