# TEST059: 次の未予約MOVEの拍と期限を揃える8項目計画

状態: fresh設計/網羅/安全の計画第2周clear。実装・TDD中。2026-11-09（日本時間）。要件SHOP-02/BEAT-01/STOPを維持する。

## 1. 概要

直前MOVEの移動確認期限と、まだ予約していない次ordinalの入力期限を分離する。次の同じ物理拍を最新modelで補正してから、その未予約slotのtarget/notBefore/deadlineを対で更新し、初回reserveで10ms窓を凍結する。予約済みticketの延長・次拍への送り直しは行わない。

## 2. 背景

受領TEST058はLEFT2入力/2MOVED、(-2,0)、goods/door/terrainは0、最終PAUSE/drain/resolved=true。原ZIP SHA `5a10c1c76237e15133843d13231206157b43f1e66cc42873b2de9cbf8c70c369`。12PNGは全回収済み。strict評価は整合性pass・商品到達failで、完全Controller再生ではない。

2歩目event4の元motion deadlineは `96955181537247`。移動を確認したcapture54で次拍を補正するとtarget=`96955334816816`、notBefore=`96955184816816`となり、親から流用した旧deadlineより3,279,569ns後。停止を開始したtick自体は旧deadlineより約113.7ms早い。第3MOVEのevent/AX照会はなく、送信遅延でも壁への3回目入力でもない。最新C/PillowはDOWN/FLOORの経路を選べる。前回058のqualified continuous reissueは本runにないので、その実機改善効果は未評価とする。

## 3. 詳細設計

`resolve_move`は親MOVEのACK・元motion horizon内の実MOVED/開通を先に検査する。その既存deadlineと元source/phase/walk/session境界は変更しない。成功して初めて次ordinalが必要になった時、親target+元periodを次のnominalとし、既存8%以内の`corrected`で同じ物理拍のtargetを得る。そのtargetからleadを引き、10msを加えた期限を未予約slotの`next_deadline`候補としてtargetと同時に設定する。MOVED後から初回reserveまで追加observeがあれば、input_state=0かつreplan/continuous pendingなしの時だけ同じnominal/元periodアンカーから両方を更新する。候補はまだ入力権限ではなく、初回reserveでtarget/notBefore/deadline/command periodを一体で凍結する。以後のobserveは元ticketを検証するだけで書き換えない。これはまだcommand/eventのない別ordinalであり、親のmotion deadlineを延ばす変更ではない。

次slotのtargetは元のnominalと8%以内・NS_LIMIT内、notBefore/deadlineの減算加算はoverflow/underflowを拒否する。補正不可/失効modelは安全停止。新commandの予約は既存source/phase/walk/sessionのhorizonとtailでさらに短縮し、notBeforeよりdeadlineが前なら送らない。予約後のSAME/FRESH・元target/notBefore/deadline/period/ordinal・motion horizon・初歩/retune・UNKNOWN無再送はそのまま。拍を探索して遅れを救済せず、期限切れ親から次slotを作らない。

既存controller testの「HUD微更新後の子commandも親nominal由来のdeadlineに等しい」という既存期待は今回の欠陥と結びつく。親/再予約の全凍結fieldとmotion horizonのassertは維持し、子だけ初回reserve時の最新補正target由来の10ms窓＋horizon短縮へ置き換える。対象はtest_continuous_refresh_preserves_original_period_and_visual_horizon_after_hud_updateと、test_initial_replan_keeps_original_beat_when_latest_fit_period_changesの少なくとも2assertで、その他の親/reissue期待は維持する。理由を記録し削除/skipで通さない。

## 4. 影響範囲

productionはNG2Controller.cの次slot確定だけ。他native21、Runtime/Beat/Nav/Perception/ABI/RPC/client v13/cap12、R12/G1は不変。controller unit・既存world回帰・故障検出・TEST059 launcher/実画像manifest/CI/seal/必要な契約と資料を更新する。原058の12PNG/reportはGit外、hash/由来だけをmanifestへ置く。

## 5. 新規試験

旧Cに実ACK/MOVEDと合成HUDの補正を与え、親の観測は期限内だが次の未予約窓だけ空になるassertion Redを実装前に記録。元/最新target、親motion deadline、子窓、ordinal/移動数を保存する。コンパイル失敗はRedに数えない。補正前後/±shift/10ms等号・+1ns/8%・overflow境界を確認し、MOVED確認→未予約で複数の正/逆HUD補正→初回reserveでもtarget/窓の対が揃うことを確認する。初回reserve後の補正は元ticketを変えず、予約済みやreissueの窓は変えない。

親motionのdeadline等号/+1ns・古いmodel/phase/source・取消/UNKNOWN・開通と進入・商品優先は元の拒否を維持する。新slot期限後は別拍を探さない。新しい位相差は実C Controllerの合成HUD/時刻で窓の整合を検査し、真のゲーム受付成功とは呼ばない。既存の独立shop world16は改変せず回帰し、実gesture→開扉/進入/商品・PAUSEの結合を維持する。world真時計/HUD/受付幅へ補正を流用せず、report/Decisionから移動応答を作らない。原058再生は既収録2移動と未実行DOWNの判断まで、未収録未来画像は作らない。

旧式の次deadline凍結を戻す故障を新しい別枠で検出する。従来59＋058の2故障、world16、Raster3、C parity-field、実RPC/実compilerを維持する。

## 6. 順序

freshな設計/網羅/安全の計画レビュー（最大3周）→旧コードassertion Red→最小Green→Refactor→fresh3実装レビュー→全必須local/標準Mac CI→新IPA/全source照合→具体的実機依頼。前回058の閉じたレビューを第4周として再開しない。

## 7. 配布前

local必須177paths＋新12・controller/native/evaluator/client/package、新旧故障・world回帰を検証。22sealはController.cだけ変更・他21同一、R12原40/G1・rawPBX/実compiler/6RSP・IPA9Mach-O HOST非混入を照合。完全source ZIPは全tracked bytes/CRC/pathを確認する。新IPAをSideStore更新→LoopCtrl完全終了/再起動/Start Server。新通常1-1・開幕gold可視・左下edge0ポーズから `sh test_059.sh` を依頼し、「TEST-059: 終了」後の `runtime/test-059` 全ZIPを必ず依頼する。

## 8. 対象外・未確認

10ms/8%/鮮度/入力・再予約予算の緩和、既存ticket・親motion期限の延長、拍スキップ、初歩の再選択、UNKNOWN再送、認識色変更、購入、周回・指輪完成。合成world/既知画像のGreenは実ゲームや人より速い性能の受入ではない。Mac正規ゲーム本体は未導入で今回も実ゲームE2Eを主張しない。
