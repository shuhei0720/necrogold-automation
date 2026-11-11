# TEST076: 未送信の静止再確認と通路の期限切れ回復

2026-11-11（日本時間）。baseline `6408286ec380a29541e385836e1c209d445f1fe1`（TEST075/build120）。実機主軸の通常局所修正としてControllerと対応単体/限定CI、独立差分レビュー1名、新IPA/固定配布/一連実機で進める。Nav/Runtime/Perception/JSON/ABI/全数値閾値/入力窓は変更しない。

## 実機根拠と採用判断

TEST075実順1828c816→05379963→6b407804→c43fa118。4ZIP/69選択PNG（20/17/17/15）を全hash/CRC/manifest/prefix/cursor/report/strict schema/実publicationで照合、全PAUSE/resolved/terminal/drained成立。2回目は原198に3商品/価格が見える。全商品到達1/4。raw/Scene/proofはGit外received075/test076-*、保持省略/未来応答を補わない。

1は8restart/2MOVED後、未送信DOWN/source275→277のstrict静止がUNKNOWN。全gold/保護/近傍/full5維持、遠方3cellだけ変化、C終了時D残6.088ms。4は1restart/2MOVED後、未送信UP/source97→99、全230tile/固定candidate/フル5不変、静止UNKNOWN、D残21.245ms。どちらも旧票は未送信で、ルート変更や期限超過が直接の停止原因ではない。

原raw最良zero/gapは1=.50146/.29095、4=.48363/.27746。旧95%追加面は不足し、固定標準Sobel面は95%/2帯を満たしても全73への15pp差が2/1候補不足。不採用とし、別kernel/閾値探索は行わない。旧UNKNOWNをBLOCKEDへ書き換えず、入力権限を捨てて後続の厳密な再確認を待つ方へ修正する。

3は0restart/3MOVED、4歩目UP/source161のbegin0。source161のC終了でD残1.325ms、complete0はD+11.065ms。capture failure/timeoutなし、dispatch_failureは別の初歩cmd3 too_lateを保持（gate D+0.597924ms）。直前の歩行発行間隔は532.821/523.251ms、実game受理時刻とは区別。通路GOLD_CLEARが既存の確実未送信回復から除外され、reason CAPTUREへ落ちる。iSH status46回エラー/取消0（最大1.324秒）で、075の2秒cancelは今回再発なし。

## 変更1: 不確実な未送信票を廃棄して再観測

shopは既存generic mask変更による静止拒否経路だけを対象とし、通常mask0 shopへ新しいmotion評価/拒否を加えない。passageは既存quietがmask0にも必須のためmask0を含む（実run1=mask4、run4=mask0）。対象はlead/実MOVED確認済み、state1/current-ID一致・event begin0/outcome0・MOVE/実next FLOOR・通常shop reason8または固定passage reason10だけ。初歩/未校正/扉/茶壁/ACK待ち/UNKNOWN送信/continuous pendingへ広げない。両FLOOR/GOODS_UNKNOWN、goldは両CANDIDATEで同非空集合、またはpassageの両CLEAR/金0。origin/nextと両3x3局所材質、全gold/全保護・全protected材質、位置/visits/entrance/passage候補/world口/prefix/完全5field Decisionを維持。許す材質変化は保護外・遠方のUNKNOWN/FLOOR/DIRT/STONE間だけ。商品・新金・保護・前面/取消を優先し、不一致を不在や新権限にしない。

元before→triggerのmotion UNKNOWNで、trigger自己比較がstrict BLOCKEDだけ、元票をnot_sentへ永久撤回しslot/epoch/referenceを無効化する。移動/開通/lead/入力creditなし。観測refreshの元verified時刻ごと1回/session8回を共有し新しい無限回復を作らない。元before画像/capture/prefix・完全Decisionとworld位置をanchorとして固定、待機中に最新画像へすり替えない。

追加画像はtrigger.end以降に開始する独立stable current-prefix/増加IDを必要とする。元anchor→最新のng2_motionがstrict BLOCKED(dx=dy=0)に戻って初めてREADYとし、隣接2枚だけのBLOCKEDでは許可しない。UNKNOWN中は入力0、MOVED/TWEEN/UNEXPECTED/開通・無効画像は停止、旧anchorとlatestの静止成立を偽造しない。READY後/予約直前も元anchor直結の証拠・固定候補を再検査する。

親期限P=min(元sourceStart+3秒,元phaseSample+3秒,元verified+12秒,旧command_syncがあればそれ,walk+45秒,session+180秒)を固定する。待機期限W=min(P,triggerCommit+2*元period)を別に持ち、P/Wとも後続画像や再fitで延ばさない。W内に未解決なら停止。READY後の新ID/新拍はPをcommand_sync/新schedule/visualの上限へ継承し、将来prep≥50ms・model sampleID≥proof・現在Nav/safe_stepを必要とする。旧ticketのtarget/NB/D/ordinal/eventを更新せず、元Dを延長して送らない。旧ID/callbackと期限後のproofは無効。

既存gate_refreshへ専用モードを追加しても、旧gate/terrain/observationの動作・previous更新・証拠面は不変。専用モードのanchor比較、親/待機期限の分離、passage.observeとの優先順を明示する。

## 変更2: 通路の確実未送信late回復

既存recover_unsent_continuousのlive state1枝だけ、passage_active/no-wait・reason10/FLOOR・両CLEAR/GOODS_UNKNOWN/実金0・ITEM/保護0・全230材質不変・固定口への同フル5/safe_step・strict BLOCKEDを許可する。GOLD_CANDIDATEの旧枝は不変。passageのpending/reissuedを追加しない（現ケースはlive、探索quietはそれらを生成しない）。元prefix/鮮度/owner・lead/実MOVED・元sync/walk/session・入力上限を維持する。

元D超過のみ。等号/in-time complete0、state2/3/4、event開始済/不明送信、取消/商品/新金/地形不一致は救わない。旧eventをnot_sent/LATEへ確定して旧bytes/姿勢/歩数を保存し、既存post_move_recoverと新fresh HUD/将来prep≥50ms/新IDへ。clock/期限延長やUNKNOWN再送は行わない。tick/begin/late complete0の既存入口を確認し、observeが先にSCREENへ落ちる経路も対象ケースとして検討する。古い画像で最新変更を飛び越えない。

## TDD・レビュー・返却

新publicC単体は実PNGを埋めず手続Sceneで意味的Red→Greenを取る。静止UNKNOWN→無入力待機→旧anchor直結BLOCKED後の別ID、shop/passsage両方、隣接だけBLOCKEDの拒否、trigger重なり/旧ID/低prefix、候補/全5field/位置/保護/商品/新gold/取消、W/P等号/超過、元refresh上限、ready後変更、始動済UNKNOWN無再送を確認。時計巻戻しは無変更の共通guardを静的確認し、新modeを理由に同じ既存試験を積み増さない。lateはcomplete0/begin/tick/observe先着・等号・新票prep/期限/元姿勢・既存gold回復を検査する。

既存gate/terrain/観測refresh、gold未送信回復、passage候補/商品/UNKNOWNの関係回帰のみ選ぶ。Runtime/Ticket/JSON/Navの累積全体試験は既定にせず、実compiler/seal/配布実物/全source照合は維持。受領画像と公開snapshotの範囲を超えた全実機再現や到達保証をしない。特にUNKNOWN後の未来画像は未保持で、待機で全商品へ到達すること自体は次の実機で確認する。

検証済み新IPA/完全sourceを固定Releaseへ保存し匿名全取得する。通常1-1ポーズからrestart→金壁/候補接近→入店→全商品確認をまず2回、全画像/ZIP保存完了後のruntime/test-076-<run_id>.zip全回分と全商品/停止位置/拍間隔を依頼。回収済み075の追加回収/再実行は不要。
