# TEST062: 実機を主にした短い反復

2026-11-10（日本時間）。要件/安全条件/固定時間なしを維持し、受領061で確認できた二つの停止だけを直す。大規模な構造変更や認識閾値の変更は行わない。

## 受領事実

ZIP SHA `ec6f284ca112485437a006396cac6affb0df256ea7c4d3b8e92237ae1a6273d7`。1回目540802…は0入力、SCREEN17。初歩の遠方セル揺れで再予約2回を消費し、送信notBeforeの実commit4.924ms前に終了。2回目9d8908…は実機2歩/C計上1歩、MOVEMENT10。2入力目のACK後28/74/118ms開始の3画像でUNKNOWNを消費し、ACK+156msで終了。visualDは約2.4秒残っていた。原画/CのUNKNOWN判定は維持する。

## 二つの局所修正

1. 初歩の送信前50msから元deadline内では、安定した同prefix・確実未送信の既存ticketに対する無害な遠方分類揺れをまとめる。両safe_floor、全gold/全protected不変、originと次セルの各3×3不変、完全5field Decision一致、同beforeへのstrict BLOCKEDを全て要求する。変更セルは遠方のUNKNOWN/FLOOR/DIRTだけ。元ID/source/before/時刻/期限/予算/前面準備は維持し、latest Sceneだけを通常どおり更新。早い変更、近傍/保護/gold/DOOR/STONE/ITEM、経路変化、UNKNOWN motionには従来の再予約/拒否を適用する。最大2回を増やさない。
2. UNKNOWN/TWEEN後の確認は、初回評価の取得開始を原点に、2回目は元command periodの1/4以降、3回目は1period以降に取得開始した画像だけを評価する。最初の適格評価は即時。UNKNOWN後はcheckpointまで完全画像も評価を待つ。上限3評価、同before/ACK prefix、元visualD、実commit/次actualtick、商品優先、UNKNOWN無再送を保持する。期限検査を間隔gateより先に行い、間隔待ちで期限を隠さない。拍が空いた場合は実機速度合格としない。

## 選ぶ検証と返却

新単体で旧Cのassertion Red→修正Green、該当する旧再予約/移動/取消/期限回帰、独立差分レビュー1回。user-device用CIはこれら単体とactual IPA/profile/seal/source照合を行い、未変更Runtime公開suite/全故障/shop16/LoopCtrlKitを今回の前提にしない。既存suiteは保存し、必要な変更時/節目に選ぶ。API15/cap13/client v14とABIは不変、TEST062 scriptを追加。新IPA・完全source・iSH手順を返し、通常1-1から商品確認までの実機とruntime/test-062全ZIPを依頼する。
