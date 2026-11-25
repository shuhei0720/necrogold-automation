# TEST121: 未開始の閉扉票と近傍blocking材質差

2026-11-25（日本時間）。基準は出荷TEST120/build268、CODE723c1c6、HEAD55a762f、Controller `cf471e36e1eb74c3c9f6924d21de9e25608830cdbab6324505579d0668bc7e0e`。[要件](../requirements/necrogold.md)・[native契約](../contracts/native-control.md)・[開発フロー](../development-flow.md)・[修正表](../fix-records.md)に従う。**この文書は実装前の計画。root/designレビューとroot GOまでは製品・正式試験・CIを変更しない。**

## 原因と修正対象

7ZIP/4run/99PNG/117記録は欠損なく照合済み。受領receipt SHA `91a4a10a1d9e661fec2edfbe54dc2adadded17d8b971a55a81e2a2ca4e601220`。周1の3a4a rootは6実MOVED後、未開始LEFT11/source125をcapture126で撤回した。原125/126は両FLOOR/GOLD_CANDIDATE/商品UNKNOWN、GOLD2・ITEM0・保護0、通常Motionは直接strict BLOCKED(dx=dy=0)、完全判断もLEFT/reason5/target(-1,0)/DOORで同じである。

材質差は(1,1)/(1,2)DIRT→STONE、(8,2)FLOOR→DIRT、(3,4)DIRT→FLOOR。`quiet_gate_scene`はorigin3×3内の(1,1)を拒否する。同時に一般`monotone_terrain`は遠方(3,4)のDIRT→FLOORを拒否する。nextがDOORなので`safe_step`は0となり、`continuous_validation`のstrict値FLOOR7をFRESHへ救済できず、旧gate/observation refreshも資格外でSCREENになる。FLOOR7はavatarの床が失われた意味ではない。

旧119/出荷120で全99PNGの正常Scene全bytes、該当raw Motion/Nav packet、対象10helperのbodyと原guard matrixは同一。120の新route/cacheの回帰ではなく、閉扉の既quietと材質関係の合成適用漏れである。元MOVE Dは96939884326592。停止後cleanup PAUSE12のUI予約actual clockは96939782573416でDより101.753ms前にあり、停止処理もその前に完了している。source125のP=96942707932791内、recovery episode0で待機Wは始まっていない。末尾endedがD後なのはcleanup ACKのためである。

私的根拠はGit外の`test121-movement/normal-frames.json`（SHA `755d1e6794a9990ae14cef4f02567f0e1a3298f170fd50735a827d3419e7df86`）と`closed-door-guard-cut/result.json`（SHA `643edeb7aacf9237edd3f717c40d67656323a3a066a6dfcc207d7a02469bc1a8`）。後者は宣言した最小Controller contextのpure predicate cutで、元model/全opaque状態の完全再生ではない。1セルを戻したablationはguard必要条件の静的診断であり、原RGBAからの正常Sceneとは区別する。

## 追加する資格は既quietの同ID保持だけ

新しい待機・replan・FRESH別IDを作らず、旧quietが近傍差で拒否した未開始closedDOOR票だけへ別の限定admissionを加える。旧quietの受理を先に維持し、一般monotone・safe_step・全Motion/Perception/Nav・door検出の意味は変えない。FR081/093の同ID quiet優先とFR113の距離1FLOOR/別refreshを維持し、次がFLOORのvariantへ広げない。

- exact未開始MOVE/event（input1・current ID一致・begin0/outcome0）、通常continuous WALK/lead/実MOVED所有で、replan/他wait・entry/framing mode・終了/取消/候補保持中ではないことを要する。旧sourceと現在画像は両FLOOR/CANDIDATE/商品UNKNOWNで、全ITEM/保護0、全旧GOLD保持・同GOLD集合、originは正FLOOR。nextは同じ正DOORで、同じ両GOLDのclosed bracketを確認する。
- 新しく許す近傍差は**進行方向の反対へ1セル・横へ1セルの対角位置にある、ちょうど1セルのDIRT→STONEだけ**。旧新とも正のblocking材質であり、origin・route axis・next DOOR・bracket GOLDを変えない。方向`d`に対し`dot(point,d)=-1`かつ横距離1の2候補の片側に限定する。原LEFTでは(1,1)が該当する。STONE→DIRTや任意の近傍blocking差を一般化しない。
- 他の近傍差は禁止する。残りの差は既quietが既に許す遠方UNKNOWN/FLOOR/DIRT/STONE関係だけで、全GOLD/DOOR/ITEM/保護は保持する。原(1,2)は既origin/next各3×3外なので旧far規則の範囲であり、near許可セルを増やさない。
- 固定元sourceから現在画像への**通常の直接strict零**と、旧source/現在の正常chooserによる同じ完全Decision（方向・reason5・target=next・obstacle DOOR）を要求する。UNKNOWN、非zero、自己比較や隣接画像の零の連鎖は資格にならない。
- current prefix/owner/世代・captureの安定性と時間の通常guardを維持する。command ID/source/before、target/NB/D/ordinal/period、準備epoch、親P・schedule/visual・walk/session・全counter/位置/visitsを変更しない。正常HUD追跡は従来通りで、モデルや準備を偽造/更新して延命しない。

結果は元票の同ID保持である。`preinput_same_source`はobstacle FLOORだけを扱うため、このDOOR資格をSAME別ID更新へ渡さない。新admissionは入力・開扉・入店・MOVEDのcreditを一切増やさず、元D内の既prepare→begin→実送信guardがそのまま必要となる。開始済み/ACK/UNKNOWNをこのguardで再armしない。既knownACK回復の独立した契約まで一律に禁止しない。

## 正式試験と保持する成功

予定する新正式ファイルは`tests/test_native_closed_door_palette121.py`。製品変更より先に、出荷120の全sourceを固定し、公開Cのnormal fit→正常ACK/実MOVEDで所有と位置をearned→閉扉未開始票→今回の具体材質差を観測する意味的assertion Redを保存する。cycle/irregular/restart_yieldを有効に保つ。private setterで票/visits/modelを作らない。手続きScene/HUD/時計は独立した意味モデルであり、原6歩の未保存private状態を再生したとは呼ばない。

正常期待は、原4差の合成が直接零/同fullchoiceを満たしたときに同ID/event/sourceと元NBD/epoch/全counterが残り、正常begin/ACK後にだけ通常DOOR_OPENEDを確認できることである。4方向・behind対角の左右を選び、door glyph木/鉄の個別認識を新しいfixtureの正解で代用せず、共通DOOR契約の範囲と明記する。

拒否はnear FLOOR/UNKNOWN変化、別の近傍セル/2セル変更、STONE→DIRT、bracket/旧GOLD/DOOR損失、ITEM/保護/商品変化、別fullchoice、normal UNKNOWN/TWEEN/実単位、未安定/不正prefix、開始済み/ACK/UNKNOWN、元D・親/phase/source期限、foreground/lock/owner取消を含む。無効画像の採用拒否と、既合法な元票まで無条件で失効させることは区別する。元Dの前/等号/後、capture end<Dかつactual commit>Dでも元入力窓を延ばさない。

旧quietのremote差/同ID source-return優先、閉FLOORのquiet/refresh、旧gate refreshのUNKNOWN→独立proof/fit、通常未送信/ACK/UNKNOWN安全を直接関連methodsだけで確認する。5572成功の205→208は遠方DIRT→STONE1・通常UNKNOWN・`gate_refresh_scene=1`で、旧refit経路の保存validation11/実recoveryと一致する。この成功を新near資格へ迂回させない。正常NEG policy17/source283→durable→実RS24→newfloor306→childと、従来policy9/7/4/11817を保持する。

## 所有範囲・レビュー・実機への返却

製品の予定owned fileは`NG2Controller.c`のみ。`quiet_gate_scene`近傍にpureなclosedDOOR/behind-blocking資格を置き、既near拒否の箇所で旧条件が拒否する場合だけ試す小hunkとする。`continuous_validation`/`monotone_terrain`・既gate refresh・入力/予約/期限/失効・P継承・PARTIAL cache・Ring producer/consumerは編集しない。商品担当が同じCのconsumer hunkを必要とする場合は関数分担を先に共有し、currentへの局所patchだけを行う。

短planのroot/designレビュー→root GO→公開正式Red→最小実装/Green・関連回帰→独立最終差分レビューを行う。原guard matrixと新資格を結び、未保持のmodel/未来画像を正解として補わない。今回のC-only geometry qualificationはABI/API、Runtime/getter/queue/lease/prepare/実send/clockを変えず、新票やcallbackを作らないので追加Mac worldは既定にしない。既結合の再利用理由と保持bytesを記録し、native変更に必要な実IPA/compiler/profile/seal/配布物同一性はroot工程で確認する。

初回RS・全商品が見えるまでの移動・対象候補保持・未観測陰性禁止・UNKNOWN無再送・全既予算を維持する。商品2失敗の修正は別所有scopeとする。次のiPhone受入では、通常1-1ポーズから商店扉前を通過→開扉→全商品観測→判定/実RS→次周回を確認し、全run/campaign ZIPを返却してもらう。host Greenを実機停止解消や毎拍/速度の達成へ読み替えない。
