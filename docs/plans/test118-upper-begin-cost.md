# TEST118: V2上部入店の確定済み静止証明をbeginで再利用する

2026-11-24（日本時間）。[V2五歩計画](test118-upper-five-step.md)の限定追加。元10ms窓とRuntimeの実send直前guardを維持し、同じC-owned画像対への重複Motion計算だけを避ける。

## 1. 概要

V2の`upper_observe`が通常`ng2_motion(cycle_anchor,current)`で直接strict BLOCKED/dx0/dy0を確認した事実を、有限のprivate proofとして保存する。begin時に同じanchor/currentの全bytes・metadataとepisode identityが一致する場合だけ、この通常Motionの再実行を省く。新しい入力・移動・陰性の権限を作らず、既存のcheap guardと最終実時計検査は全て残す。V1と未証明のfallbackは変更しない。

## 2. 背景

実Mac CI257の正常Runtimeは初回RS、lead2歩、開扉、H1、正常UNKNOWN採用を経てH2 ticketまで進んだ。保存RAW/結果では5潜在ITEM・正確保護・実床・元GOLDが保たれ、Ring4slotは元潜在域内、候補なし。H2のC beginも成功している。停止はその後のRuntime実send gateが元Dを249,740ns超えたための確実未送信である。

main entryはnotBeforeの約7.730ms後で、C begin時の残窓は2.270ms、C beginから後続外部guard/実時計までの実費は2.520msだった。この全区間をMotion単体の費用と断定しない。既`upper_static`の通常Motionは直前の`upper_observe`でも同じ画像対で実行済みなので、その重複を限定して削る。遅いmain入場の原因や全ホスト負荷・iPhone速度をこの変更だけで保証しない。

## 3. 詳細設計

- public ABIを変えずprivate upperにvalid flag、owner開始時刻、level/opening、job、anchorのcapture/start/end/prefix、currentのcapture/start/end/prefix、direction・horizontal/down/inputs/reboundを保存する。anchor/currentの`NG2Scene`を各1個コピーし、beginでは両方の全bytesを比較する。追加画像は最大2個で、無制限cache/外部tokenを導入しない。
- `cycle_anchor`への製品書込は`cycle_bind`の一箇所。upperのadmit/bindで、そのsourceが現在のC-owned metadataとexactに対応する場合だけanchor endを凍結する。不明ならcache不成立とし旧Motionへ戻す。以後はそのendとjob/source identityも照合する。別sourceへ同じidentityのままbytesを移さない。
- proofの作成はV2の`upper_observe`で実`upper_static`がvalidation0を返した後だけ。元anchorへの直接通常zeroを要求し、前画像からのzeroを連鎖しない。stage1→2→3は正当な遷移として扱い、stage番号だけをstampしてhitを妨げない。issued/現在commandの権限は既begin guardで別に検査する。
- CI257のようにcommand source63より新しいcurrent64が来ても、current64対anchor62を通常Motionで直接確認済みなら、そのexact pairのproofを使える。63→64の静止から62→64を推論しない。新観測ごとに旧proofを撤回し、同じanchorへの新しい通常検査が成功した場合だけ置き換える。破棄された新captureもseen/current identityの不一致によりcacheを使えない。
- beginは従来と同じupper identity、world、実origin/dest床・非保護、goods/tiles/protection、方向/started cap/issued、route上限、正常modelと鮮度、owner/前面/lock/取消/元時刻を検査する。追加proofがexact matchする場合だけMotionを省略し、未証明・不一致は従来の通常Motionへfallbackする。cache不一致を静止へ丸めない。
- 新bind/anchor、hold/候補/取消、入力開始はvalid撤回または全identity不一致で利用不可。beginの古いID早期returnは純粋なままとし、古いID呼出で新予約のproofを消さない。成功した正しいbeginの入力開始時にproofを消費する。UNKNOWN/NOT_SENTの再送やcap返還は追加しない。

## 4. 影響範囲

変更はControllerのprivate upper state・admit/bind/observe・begin用static helperと既upper begin分岐に限定する。Perception/Navigation/Motion数値・Ring/Runtime/Spool・公開schemaは変更しない。元10ms窓、50ms準備、source/phase鮮度、V2初回配分、各job短縮、5 started入力、worker予算とV1の挙動は維持する。Swift側は別担当が既実境界のまま検証する。

## 5. 新規テスト

新`tests/test_native_upper_begin118.py`は公開Controller lifecycleを使う。Controllerオブジェクトだけ`-Dng2_motion=...`で回数wrapperへ結び、wrapperは同じ本物のNavigation Motionへ委譲する。返値・閾値・時間は偽装しない。Controller/Beat O0、Perception/Navigation O2の既compile profileを変えない。

- V2の同exact pair・左右、H1後のH2、commandより新しいcurrentで、observeには通常Motion呼出があり、beginの追加呼出0・成功を要求する。旧Cのbegin追加1が意味Redとなる。
- 新しい画像/変更signatureのnonzero、床/保護/ITEM/元GOLD変化、prefix・job/bind・候補/target・取消・freshness/親期限を検査し、旧proofで入力しない。V1と未認証currentは旧通常Motionのfallbackを保持する。
- 古いcommand IDが新予約のproofを壊さず、真のbegin/NOT_SENT/UNKNOWN後にproofを再利用しない。元counter/target/ordinal/期限とRuntime postgateを弱めない。
- 原CI257のsource62/63/64を使う限定費用cutが必要なら、通常Scene/元metadata/exact anchor/currentの出典と呼出回数を残す。完全な元opaque stateや元117実機再生とは呼ばない。

## 6. 実装順

独立設計レビューP0解消→公開回数assertion Red→小hunkの最小実装→新単体と上部5歩/V1の直接関連→限定実費確認→独立差分レビュー。実装前の失敗と元CI257の失敗を保持する。元clock/phaseやfixture camera/ACKを移動し、compiler flagsを速い設定へ差し替えて合格にはしない。

## 7. 保存・コミット前確認

proofの全identity/bytes条件とcycle_anchor writer一箇所を照合し、新source・候補・取消・入力開始の失効を対応付ける。単体のcount削減、原sourceの費用、実Swift Runtimeの最終send結果を別証跡にする。native/source seal/実compiler/IPA/完全sourceと固定配布の同一性はrootで更新する。iPhone受入・毎拍/実効速度は未確認のまま実機へ返し、ホスト1回の成功を全負荷保証としない。

## 8. 対象外

入力窓/routeP/phaseの延長、C begin成功を実synth送信と扱うこと、上部静止の推移律、未確認MotionのBLOCKED化、入力再送、V1や他episodeのcache化、Runtime最終guardの削除、classifier/全商品名登録、既geometryを広げる変更、全体CI追加。
