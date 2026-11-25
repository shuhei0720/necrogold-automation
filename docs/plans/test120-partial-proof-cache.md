# TEST120: 普通PARTIALのbeginで同じ通常零を再計算しない

2026-11-25（日本時間）。[制御契約](../contracts/native-control.md)・[FR119までの修正表](../fix-records.md)・[旧V2上部の限定対策](test118-upper-begin-cost.md)に従う。計画段階であり、製品・正式試験は未編集。実装は独立レビューとrootの関数分担・GO後に行う。

## 1. 目的と確認済みの原因

TEST119の4周目子`2d1e229d88fb415cb302a84de9363cf1`は、LEFT21の既知ACKで開扉後、source287/job2を正しくPARTIAL/UNKNOWNとして採用した。原画像は2商品だけが見え、未観測の商品を陰性にしてはならない。Cは商品を見るためのLEFT22/source298/ordinal6を予約し、beginも承認したが、Runtimeの実送信直前の時計が元Dを50,136ns超え、CAPTURE/確実未送信となった。

保存begin_nsから実sendNowまで7,466,542ns。このbegin_nsはpreparationMatchesより前に採ったcallerの時計で、C関数の実入場時刻ではない。preparation/任意epoch getter、Cbegin、外部owner/lock/時計の実機内訳は未記録であり、全区間をMotion単体の費用と断定しない。元anchor287→current300の通常MotionはLinuxで旧/新各9回ともstrict BLOCKED、中央値4.506/4.554ms。observeで既に確認した同じ画像対をbeginでも計算する重複があることを修正根拠にする。

旧CODEdca8ca3のC535a9f0eと119のCef0fffaf、旧/新通常Perception・Ringを同じ原入力で比較した。24画像のScene全bytes、選択6画像の判定packet全bytesは同一。宣言した限定contextで287→298/300のpartial_static/comparisonも両版validation0だった。119のentered token・yield順序・松明床の判定回帰として扱わず、普通PARTIALのbeginに残る別の重複経路を対象にする。完全な過去opaque state再生ではない。

## 2. 再利用する事実とprivate key

再利用するのは、固定された分類anchorから最新のC-owned Sceneへ、通常`ng2_motion`が直接strict BLOCKED(dx=dy=0)を返した事実だけ。別画像を経由した零の推移、UNKNOWNの零化、経路・入力権限の保存は行わない。beginの`cycle_partial_static`を含むcheap geometry/route検査と、時刻・位相・model・ID・owner等は従来通り毎回評価する。

private `NG2PartialStaticProof`を最大1個だけ保持する。固定anchor/currentの各`NG2Scene`全bytesをコピーし、owner開始、level/job、anchorのcapture/start/end/prefix、currentのcapture/start/end/prefix、方向、exact未開始`NG2Command`全bytes、inputs/moves/restartsと必要なcredit identityを結ぶ。公開ABI・wire・分類結果は増やさない。

分類anchor287、現在のC Scene300、commandの撮影元298は異なる役割として保持する。currentをcommand.sourceへ偽装せず、currentが撮影元より新しい既存の正常経路も扱う。anchor endは`cycle_bind`時にCのcurrent/seenと元Scene全bytes・id/start/prefixが一致したときだけ凍結し、不明な場合は再利用不可とする。古いqueued sourceのendを推定しない。

## 3. proofを作る限定条件

ordinary PARTIAL creditで、既に予約されたMOVEがstate1、exact current eventが未begin・未completeである場合に限る。既`cycle_partial_comparison`が固定anchorから今の独立画像へ、全static guardと通常Motionのvalidation0を実際に返し、その画像がC-owned currentとして採用された後にだけkeyを保存する。

実2d1ではticket22/source298の予約後に観測した299/300が該当する。予約前の零だけでは未開始commandを後付けして再利用しない。その後の独立画像がない場合は従来の通常Motionへfallbackする。この限定により`reserve`への新しいattach処理は不要である。

stampは`ng2_controller_observe_at`の既partial_credit再検査成功後だけに置く。`cycle_observe_hold`で予約前に得る零/creditは、未開始commandがまだ存在しないのでcacheの適用対象にしない。毎回の新画像では通常Motionを省略しない。新しい観測を古いkeyへrestampしない。候補・FULL・pending worker・別modeの結果をproofへ変換しない。

## 4. beginの照合・fallback・消費

beginは先に従来のpartial_static/choice・FLOOR・ITEM/GOLD/保護・routeを再検査する。そのうえでkeyの全identity、双方の全Scene bytes、現在のseen/current metadata、未開始command/event/counterが完全一致したときだけ、同じ通常Motionの再計算を省く。hitは静止factの利用であり、合成のMotion出力や新しいMOVE creditを作らない。不一致・未証明・anchor end不明は同じ元anchorに対する従来の通常Motionへfallbackし、そのUNKNOWN/非zero/拒否を維持する。

新source/bind、画像bytes/metadata・job/level/owner/prefixの変化、候補・hold・取消・終了はclearまたは必須identity不一致で利用不可にする。accepted新画像の前に旧proofを撤回し、成功した現在pairだけで置き換える。破棄された新画像もseen/current不一致を検査する。正しいIDの真beginが入力を開始するときにproofを消費する。古いIDの早期returnは純粋なまま、新予約のproofを壊さない。NOT_SENT/UNKNOWN後に再arm、旧ID再送、観測枠の返還をしない。

Runtime58のpost-beginは外部owner、LockStateMonitor、実時計とTicketGuard/campaignのみで、通常Motionを呼ばない。preparationMatches/任意preparation_epochはbegin前で、ここにもMotionはない。したがって真beginでproofを消費してもpostで再計算は発生しない。これらのgetter・guard・実sendの10ms窓は変更しない。

## 5. 変更箇所と担当境界

goods担当の予定範囲はControllerの次の小hunkに限定し、同じCを扱うルート担当との着手順・共有hunkはrootがGO時に確定する。

- private struct/field: `NG2PartialStaticProof`とordinary PARTIAL用field、判明したanchor end。既upper/static、entered token、passage proofのfieldは変更しない。
- partial helper付近: `cycle_partial_comparison`の通常評価は保持し、近傍へstamp/match/clear helperを置く。begin専用`cycle_partial_relation`だけ、従来static再検査→exact fact hit→従来通常Motion fallbackへ整理する。
- `cycle_bind`/`cycle_latch`と`reset_level`/`cycle_failure`/`finish`/`terminal`: このfieldの初期化・失効・anchor end取得だけ。共有reset本体のルート関連条件を変更しない。
- `ng2_controller_observe_at`の既partial_credit branch: 既検査成功・C-owned current採用後の限定stamp/失効だけ。`cycle_observe_hold`の入力前credit、他modeのguardや119 entered順序は変更しない。
- `ng2_controller_begin`: 既partial credit消費位置でprivate proofも消費。ID/time/state/ownerの既順序と許可条件は保持する。

`reserve`、ルート担当のpassage/source/revalidation helper、Nav/kernel/Perception/Ring、Beat、Runtime本体、API/ABI、R12/G1/特徴資産は変更しない。beginのルート担当が触るhunkと重なる場合はrootが順番に統合し、双方が全関数を上書きしない。普通PARTIAL以外の新しいcache適用域を混ぜない。

## 6. 正式Redと必要なGreen

公開C lifecycleで開扉→正常PARTIAL→通常零→未開始LEFT予約→別の独立currentの通常零→beginまで進め、通常Motionの呼出counterで旧beginの1回と新hitの0回を意味的Red→Greenにする。期待値を計測時間だけに置かず、static/route検査は毎回通り、ID/ordinal/target・元D・counter・ACK/MOVEDの意味的結果が不変であることを検査する。

- owner/level/job、source/currentの各metadata、方向/command/event、両Sceneの各bytesの1項違いでhitしない。正常なら従来fallback、ITEM/保護/旧GOLD喪失/route不成立・UNKNOWN/非zeroなら従来通り拒否する。
- 新しい独立currentを毎回元anchorから再評価し、未知→零の推移を使わない。予約後の新しい証明がない場合、anchor end不明、別modeもfallbackする。
- 新bind/候補/取消/reset、古いID呼出の無副作用、真begin消費、NOT_SENT/UNKNOWN後の再arm0回を確認する。元P、source150ms/worker100ms、通常準備50ms、入力10ms、後続実時刻gateを保持する。
- 普通PARTIAL/empty framing、既upper fact/fallback、119 entered/候補優先の変更部に直接関連する旧assertを選ぶ。3rootのpolicy9/7成功packet不変、119のpolicy4正常陰性、既policy17成功を保持し、分類/耐久保存/実RSの契約を変更しない。

原287/298/300はguard/costの校正として固定し、未知評価に再利用しない。test-only counter/private fault probeは製品へ入れない。原7.466542msからhostのMotion費用を引いて実機成功と推定しない。

## 7. Runtime結合と性能の確認範囲

Cの入力直前の仕事を変えるため、実RuntimeのPARTIAL callback最小1caseを候補とする。公開の独立RGBA、通常Perception/Motion/Ring、公開Cで得た未開始ticketを使い、通常pipelineのcurrent更新と同じmain callbackのpreparation/getter→begin→post guardへ結ぶ。Scene/判定の注入や宣言private stateをRuntime成功としない。

observeの通常zero以後、同pairのbeginでMotion呼出0、post getterでMotion呼出0を数える。外部guard・実時計による期限後の確実未送信が引き続き成立することも確認する。実compiler/profileと通常の時計を保持し、画像/ACK時刻をずらして通さない。全world・全故障集合を追加せず、guardの既結合は同bytes等の根拠を付けて過去結果と区別する。

呼出1→0はhot window内の重複仕事削減の事実であり、実機の全内訳、毎拍・人超え速度、任意負荷での成功を証明しない。Macのcomponent成功と次のiPhoneの商品到達・実RSを別に評価する。

## 8. 実装順・レビュー・返却

単一の独立計画レビュー→rootのowned hunk分担/GO→正式assertion Red→private field/helperの最小実装→新単体と直接関連Green→原pairの意味的同一性/呼出数・限定費用の比較→必要な最小Runtime結合→独立最終差分レビューの順に進める。新たな失敗は原本を保持し、同原因の再試行を成功へ付け替えない。

source/function/test/選択scopeを固定し、native変更として新IPA・seal・実compiler・全source/配布物の同一性確認をroot工程で行う。source/classifier/kernelとRuntime本体の保持bytesも照合する。元入力権限・親P/期限/予算を変更する必要が生じたらこの計画の範囲外として止め、別の根拠を先に示す。

原2d1の未保存の未来画像を補完せず、LEFT22が実送信されたことや全商品へ到達したことにしない。次の通常1-1ポーズからのiPhone試験で、開扉後の観測移動→全商品確認→対象なしなら正常判定/保存/実RS→次周回を確認し、終了後の全runtime ZIPを返却してもらう。
