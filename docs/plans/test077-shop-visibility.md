# TEST077: 通路の局所変化と開扉後の商品可視化

2026-11-11（日本時間）。baseline `d3e9bbde44ceb41dac43beaf818043c588cc3aab`（TEST076/build122）。実機主軸の通常局所修正。Controllerと新単体/限定CI・独立差分レビュー1名・新IPA/固定配布・一連実機で進める。Nav/Perception/Runtime/JSON/全public header/API/ABI/元閾値/全予算・入力窓は変えない。

## 根拠・期待

受領2ZIP/37選択PNG（20/17）を全hash/CRC/manifest/prefix/cursor/strict API16 schema/実publicationで照合、両PAUSE/resolved/terminal/drained。実順1f2371f7→013ca451、全商品可視0/2。3回目はユーザー報告のみ・ログ未受領で原因未確認、補完や回収済み再実行は要求しない。raw/Scene/proofはGit外received076/test077-*。

1は6restart/実2LEFT後の次未送信UP/source248→250。GOLD_CLEAR/GOODS_UNKNOWN、固定候補bit5/pose(-2,0)/フル5 UP/reason10/target(-1,-2)/FLOOR不変、実次床/保護も同じ。ng2_motionはUNKNOWNで、(1,-1)FLOOR→DIRT、(2,1)DIRT→FLOOR、(3,1)FLOOR→DIRTにより076待機の3×3局所不変条件が拒否。回復/待機記録0、C7.979875ms/終了D残16.835326ms、期限超過ではない。

2は3restart/6MOVED+1DOOR。開扉ACK済み、未送信進入LEFT/source220→221、両GOODS_PARTIAL/全protected12セル不変/同フル5 LEFT/reason5/target(-1,0)/FLOOR、strict BLOCKED成立。遠方(-7,-1)DIRT→GOLD追加だけでquietのsame_goldが失敗し、genericはPARTIALにvalidation7(FLOOR)で拒否。C終了D残91.921093ms。実原画は店を下に広く残し商品を全確認できていない。開扉だけを完了にせず入店/店内の観測床へ進む必要がある。

2の別cmd11（ordinal4）のtoo_lateは、旧IDを未送信/LATEへ確定し次拍の別IDcmd12が実MOVEDとなり、076の回復が実際に成立。取得failure/timeoutなし、iSH status28回エラー/取消0/最大1.110秒。今回の2停止を既修正late/JSON障害へ混同しない。

## 1. 固定通路だけ、実入力先以外の局所差を待機へ

076 stationary_wait_sceneのshop局所不変条件は維持。固定passage・両FLOOR/GOLD_CLEAR/GOODS_UNKNOWN・origin/実nextの観測FLOOR・全protected集合/材質・固定world/bit・位置/visits/入口・フル5一致を満たす場合だけ、保護外の実origin/next以外にあるUNKNOWN/FLOOR/DIRT/STONE間の材質差を局所にも許す。GOLD/DOOR/ITEMの変更は不可、実stepの危険やroute変更を同じ画像として扱わない。

許可するのはUNKNOWN時の入力権限撤回と無入力待機の開始/継続であり、UNKNOWNをBLOCKED/MOVEDへ変更しない。元before anchor固定・後続独立current-prefix画像の直接strict BLOCKED・P/W固定・per-verified1回/session8・新ID/将来prep50ms/全旧callback無効は076のまま。隣接画像だけの静止、保護/商品/新gold、実next/原点変更、フル5不一致は従来どおり停止/既存優先処理。shopのnear拒否assertを含む既076条件は削除しない。

## 2. 既に開いた店で、遠方の金壁の可視増加を同IDへ

既quiet_gate_observationのopened_entry（直前の同向きDOOR_OPENED ACK、reason5/next FLOOR）とinterior_step（実入口valid=1、reason8/next FLOOR）だけ、両GOODS_PARTIAL安定の追加証拠を使う。閉扉/未開通/普通の開幕approach/GOODS_UNKNOWNには適用しない。開通ACKと進入MOVEDを分け、入口は実MOVED後だけラッチする。

元before画像/ticketのGOLD全保持に加え、同IDで直前にacceptedしたp.sceneからincomingへもGOLD全保持を要求する。新たなGOLDは、元/直前のUNKNOWN又はDIRTからの増加だけで、origin/nextの両3×3外・非保護セルに限る。旧GOLD削除/shift、一度許した新GOLDの消失/shift、FLOOR/STONE/DOOR/ITEMからGOLD、局所/保護上の新GOLDは拒否する。before/command/epochは差し替えない。

全protected集合/材質・既存ITEM/DOOR等を保持し、実origin/next/ゲートの法線・既存金bracket・フル5 Decision/固定入口を変えない。以前からあるITEM/保護が遠方に不変で存在すること自体は許す（原場の下端12protectedを否定しない）。strict BLOCKED(dx=dy=0)を必須とし、UNKNOWN/TWEEN/非zero/未確認開通は許さない。その他のpalette変化は既quiet条件どおり。3商品のGOODS_VISIBLEは追加入力より優先、不可視を対象なしにせず自動購入しない。

成立時は旧同ID/target/NB/D/ordinal/source/元phase・source鮮度/元horizonを全て維持し、replan/SAME回数や移動・開通creditを増やさない。goods PARTIALから先へ進む通常Navを妨げず、商品が新たに見えた時点の保護/GOODS優先を維持する。商品/保護集合が変わった場合や新goldで次手が変わる場合の一般再計画まで拡張しない。

## 単体・レビュー・配布

新public C手続単体2moduleを旧076 compile成功の意味的Red→最小Greenで検証。通路はoff-route局所差→旧票撤回/無入力待機→固定anchor strict0後の別ID、origin/next/保護/GOLD/ITEM/DOOR/フル5/PW拒否、shop旧near拒否を確認する。opened-entryと実MOVED後interiorはfar新GOLDを受理後、同ticket全bytes保持→NB begin成功→ACK/実MOVED/入口・次Navまで検査。source/直前追加GOLDの消失・shift、near/protected・未開扉・部分商品変化・route変更・未知motion・期限/owner/prefix・GOODS優先を拒否する。

既076の固定anchor/PW・既071opened entry・closed gate・partial goods/UNKNOWN無再送の必要な回帰だけ選ぶ。assert削除/skipなし、同bytes Nav/JSONの過去結果を現在実行へ足さず、全Runtime/worldの積み増しはしない。実PNGの純幾何/predicate確認とclock/model/ownerを含むlive admission、未保持future proofを区別する。通常局所修正として独立1名が計画/最終差分と拒否境界を確認する。

新nativeはfresh G1→seal、22中Controller1/他21・R12/G1/実compiler/全MachO/IPA/全tracked sourceを照合。標準public CIを使用し、検証済みIPA/完全sourceを固定Releaseへ保存して匿名全GETで確認。通常1-1ポーズから自動restart→金壁/通路候補→全商品確認をまず2回、全画像/ZIP保存照合完了後runtime/test-077-<run_id>.zip全回分と全商品/停止位置/拍間隔を依頼。3回目076の未受領ログを必須にせず、新実機で到達を評価する。
