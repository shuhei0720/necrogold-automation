# TEST124: 上端PARTIALの対象候補を保持する

2026-11-27（日本時間）。GOODS-01/02・[対象判定契約](../contracts/target-assessment.md)。実機TEST123のroot3/原196に対象「のろいのゆびわ」があるが、正常job1はUNKNOWN/incomplete/row0/partial0を採用した。完了は元Dより88.413083ms前であり、未実行・期限切れではない。左看板は中央HUD mask、右看板は上端と文字で228画素/29×13・106画素/29×7に分かれ、既最小高16に届かずseedが0になる。元kernelを原spriteへ直接診断すると .8324065441364757、候補閾値.80以上だが、この診断を正常producerの検出成功とはしない。

## 限定する変更

`NG2Ring.c`の新positive専用helperと限定dispatchだけを追加する。mode2・有効な同immutable SceneのFLOOR/PARTIAL・元GOLD観測・正常OK/UNKNOWN/incomplete・元row/partial/sign全0でだけ適用する。既positive/negative/通常row/partial・word vetoは先行保持する。元kernel/feature・Perception・Controller/Runtime・negative validator・POD/ABIを変えず、名称/価格や全商品登録を必須にしない。

正常Sceneの有限230cellからITEMを取り、既grid `cx=448+36*x, base_sy=207+36*y-48`を使う。元全sprite pose領域が中央pauseHUDの下端45を縦にまたぎ、各元x poseがそのHUDと横に交差する場合に限る。元windowが既にHUD下に収まる別rowへは広げない。`probe_sy=45-24`、`0<probe_sy-base_sy<=6`を要求し、該当ITEMは最大1個とする。run/capture番号・hash・価格値は資格にしない。

元spriteは32×28・33×28・34×29。新probeの**全sprite・全poseの完全探索envelope**を元HUD全領域と原寸境界で検査してから、変更しないkernelを呼ぶ。原196は`cx448/base_sy15/probe_sy21`で、半開envelope `[423,473)×[45,107)`が全て非HUD。元y39..72の安全poseはy45..72で、新probeのy45..78は全安全poseと追加6行を含む有限のpositive範囲である。返却global最大のposeだけを後から捨てる方法は、安全な次善の対象も失うため採用しない。追加6行を元探索の完全同値とは呼ばない。

新slotはlocalへstageする。exact iconが.80以上の場合だけCANDIDATE/incompleteへ保持し、TARGET・NEG・policy16へのpromotionをしない。元base geometryとprobe geometryを区別し、ずらした仮rowの名前/価格で種類を確定しない。元geometryでのword処理/vetoは保持する。候補は旧Controllerで入力取消・通常PAUSEを経て対象/候補通知条件へ進み、新MOVE/RS/購入権限を与えない。

no-hitでは元rows/partial/certificate/outcome/`partial_safe_no_positive`を保持する。低scoreのpartialを足すとsafe1が生まれ観測MOVEへ進めるため、positive以外をappendしない。元checkpoint・取消・source150ms/worker100ms/minDを維持し、nonOKを元OKへ戻さない。追加探索のchecks/終了時刻は同一呼出の実作業として記録する。

## Red・確認と範囲

root正式GO・独立短計画レビュー後、exact出荷123へ原196の通常producer CANDIDATE期待を置き、UNKNOWNの意味Redを保存する。公開手続きfixtureでも「より強いHUD内pose＋.80以上の非HUD次善pose」を正常producerで保持するRedを先に保存し、compile失敗をRedに数えない。その後に最小実装する。

公開fixtureは候補専用/incomplete/noNEG、HUDだけ・閾値未満・noITEM/nohitのsafe0、無効Scene/mode、既row/partial/sign/positive/negative先行、十分下の別row、元/new全pose境界・有限/maxone、取消/D前・等号・後を選ぶ。既成功whole6112Bと今回stable商品12packetは、原196の明示した候補変更以外を保持する。既public earned C lifecycleで元owner/job/source/prefix/世代/Dに結ぶ正常候補→PAUSE・NoRSを確認し、旧Runtime通知条件とOS受付/実配信を区別する。原private Controllerの未出力状態は復元したと呼ばない。

独立差分レビュー1回と直接関連だけを選び、無関係な全world/旧全Runtimeを再走しない。native変更後の実IPA/完全source同一性を確認して次の実機へ進む。固定診断時計のpacket結果をiPhone期限や速度へ読み替えず、原時差を保持した実clock診断は別欄に残す。

root5の原188は別原因。右capの461/625画素が黒くupper/full FLOORが不成立なので、原188をNEGにする期待や閾値緩和はしない。追加の有限安全観測と新immutable sourceの通常完全陰性→独立C→保存/RSは別計画とする。

## 実施と証明範囲

原196はexact出荷123で通常return0のまま候補期待1/UNKNOWN0の意味Red1/errors0。公開9methodは同出荷sourceで意味assertion failure6/errors0/skip0、同fixtureで新9Green。初回Green試行で最終PARTIAL coverage設定前にdispatchした入口不足を検出し、既最終化直後へ移した最小修正後に同9Greenを確認した。既PARTIAL/name/price遮蔽/HUD/safe/fastに直接関係する旧5methodもGreen。公開fixtureの初期oracle校正は正式Redへ数えていない。

原196は正常CANDIDATE/incomplete/partial1/safe0、exact icon .832406544・実pose(429,45,33,28)を保持した。今回stable商品12枚では対象1枚だけを明示変更し、他11枚、既成功8枚、旧policy15成功・未観測PARTIAL・新22の3原画像を合わせた24packetは全6112B保持した。候補の独立negative証明はRing/Cとも0で、旧NEGは双方1を保持した。新eligible no-hitの意味fieldsと権限は不変だが、実作業checks/finishedを元値に巻き戻さず記録する。全6112B保持はfallback非適用の旧画像に限定する。

変更しない出荷Controllerを既public helperでearnedし、新しい正常producerの公開手続き画像から得たcandidate packetをそのままsource/job/prefixへ結び、候補latch→通常PAUSE/ACK→durable→terminal・移動/RS0を確認した。Runtimeの既通知条件を静的照合した範囲であり、OSへの要求・実配信や元実機の未出力private状態を再現したものではない。

原source/worker/assessment開始の差を一原点だけhost単調時計へ移した固定1対の実clock診断では、旧UNKNOWN約3.37ms、新CANDIDATE約6.55msで、どちらも元minD内だった。Linux1対の校正に限り、元150/100msを延長せず、iPhone費用・速度達成・未知配置精度の証明とはしない。実機の候補通知と以後の停止は次の返却まで未確認。
