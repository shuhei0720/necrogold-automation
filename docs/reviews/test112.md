# TEST112の受領・検証

2026-11-17（日本時間）。基準08d6ce9/配布TEST111 build219。[修正計画](../plans/test112-device-failures.md)、[上側入店](../plans/test112-upper-door.md)、[正常な区切り](../plans/test112-restarted-budget.md)、[修正表](../fix-records.md)。最終試験・配布と実機改善は未確認。

## 成功の比較と失敗原因

8添付=4campaign/4run、全102 PNG/118記録について既存client/hashchain/PNG・896×414 RGBA hashを照合した。添付順で回数を推測せず、開始時刻順57f3→4344→1eab→ff8fを確認した。原画・Scene・実記録・解析出力はGit外。

1eab原133/328の2回は、通常Ring/policy7・全3商品/価格・完全陰性、C採用、durable保存、RESTART11/25、実新floor160/355まで成立。実分類51.336/55.732ms、画像取得から判定99.072/101.908msはこの2例の値で、全体の人超え/毎拍/未知精度の受入ではない。

57f3は右端の床が実際に黒く、既完全陰性の閾値不足ではなく観測不足。元436→450は旧visual期限内の通常MOVEDだが、最初のFULL446でACKを終了するため後続の強い証明を使えない。446→450を静止とは呼ばない。

4344は確実未送信のCLEAR待機。旧STONE1個のSceneと、光のぼけ競合を扱う既plural数値証明の積が適用外。通常MotionはUNKNOWNを維持し、専用の有界待機補助だけを追加する。

1eabの次フロア停止はinputs16/moves14/restarts3/reasonLIMIT。意図された累積上限が次の探索途中に到達した。旧上限/診断容量をリセットせず、正常なリスタート後に新フロアを保持してrunを区切る明示opt-inを設ける。

ff8f原147は開扉のみで移動しておらず、下の商品は部分表示。通常Ringは約7.56msで正常UNKNOWN/slotなし。既UP入店/実MOVED後lowerの両条件外。次の正の床はLEFTだけで、後続の各新FLOORと実MOVEDから内側→DOWNへ進む必要がある。

## 変更部と段階確認

4344: 新10件、直接関連36件Green。既singleton Scene/raw零/plural数値の専用積を確実未送信の固定worldへ追加し、旧helper本体・通常Motion・Core ABIを保持。実58→60..75の新/旧補助資格を校正した。未収録の未来入力成功は主張しない。

57f3: 新7件＋関連50件Green。旧101の初回FULLでのACK終了assertを保持し、強い後続の元ACK MOVEDだけを1回creditする。実436/446..450＋通常Ringによる公開C校正で、元hold/root/visual期限・イベント/参照・DATA専用bindを確認。450の端はなお黒いためUNKNOWNを維持し、次の独立画像・新ticketを要求する。

上側入店は独立設計レビューのP1（元店/商品行のworld結合、途中の潜在ROIを全可視と誤要求する点）を修正し、残P0/P1なし。最終陰性は元店へ投影できる単独の通常完全証明に限定する。空結果/保存した原画だけを陰性証明にしない。

正常区切りも独立設計レビューのP1を解消。新opt-inだけ新鮮PAUSE開始を要求し、FLOOR/他UIではUI0。手動変更なしを条件に同フロアを再開し、旧画像/陰性を入力権限へ流用しない。原画3別名は既raw/pin容量内で管理し、producer/control実return・capture解析・writerを待つ。

## 残工程と証明範囲

上側入店は新14件、予算区切りは新16件を含む直接144件が最終Cで成功。Runtime/C相互レビューの3件のP1（死亡UI・開始PAUSEの鮮度・UNKNOWN後の新床保存）を修正し、残P0/P1なし。Pythonは実記録のoutcome座標がreset前である点と、行/slot内の候補の検査を補強した。旧102の1methodだけ、111以前の「期限後の対象を捨てる」という期待を現行の候補保持へ変更し、他bytes/期限/入力数は維持した。

全36nativeを封印・実適用し、変更はController.c/.h、Navigation.c、Runtime.swift、RPCMethod.swiftの5資産。Ring/Perception/Wire/Spool/Export・G1/R12は保持した。最終CODEでの選択host/実Python3.9、実Macの限定callback、IPA/実compiler/全source/固定配布の同一性確認が残る。旧全240native/29Runtime故障集合を既定では再実行しない。選んだ現sourceの結果と、不変資産の過去結果を区別する。

次の実機では全3商品の可視位置への到達、対象/対象外の正しい判定、正常リスタートと自動継続を確認する。複数手の未来Sceneを手続き的fixtureで生成した確認を、実機到達成功とは扱わない。

## 配布前CI221の試験補助修正

CODE915cee9/run44096307751で制御219＋selector7＝226件、実CPython3.9.25の55件は成功。旧Runtime37cのopt-in API assertion Redも正しい単一assert/compile0で成立した。現Runtimeの8ケースは、別Swiftファイルのprivate NSLock補助を新fixtureから呼ぶ2箇所がcompile errorとなり、未実行。製品assertion RedやIPA成功ではない。新112 fixtureの2読み取りだけを明示lock/read/unlockへ直し、assert全体・旧13資材・全36製品sourceを維持して再ビルドする。旧runの成功と未実施はそのsourceに結び付けて保持する。

CI222/CODE1760a5fは制御226/実3.9 55/API Redと旧方式Macが成功。新7ケースはcompile後に全て取得0で停止した。保存先の子directoryを新fixtureが作らず、SpoolのO_DIRECTORY openがsupport失敗し、initializeCycleがcancel6へ入っていた。C開始前であり、C/Runtimeの有効化順序は正常。新reset内だけmkdir0700とdirectory/非symlink/権限の明示assertを追加し、既assert・製品source・旧資材を保持。独立レビュー残P0/P1なし。これも製品assertion Redや実機障害へ算入せず、修正後のMac実行を要する。

## CI223の実callbackで見つかった候補停止

223/CODE35b27c0は開始・通常区切り・producer return等を実行。候補後の通常PAUSEはACK済みでも観測ID0/input3に残った。新境界のinvalid/pendingが通常停止PAUSEを横取りし、専用budget PAUSEだけを閉じる実装が原因。対応する既知ACK・同prefix・ACK以後の有効PAUSEだけを閉じるC修正309169c4を適用し、対象/候補・raw・元期限・再送/区切り禁止を維持した。旧ebbで新1method/3assert失敗(error0)→最終17＋直接67件Green、独立レビュー残P0/P1なし。

旧223のfirst_partialはdriver上Greenでも、実Spool検証がwatchdog reason19/input3を検出して最終資格を拒否した。候補用fixtureもreasonGoods/input0/通常PAUSEの実観測を必須に強める。happyの実24PNG/29記録は実Python3.9で通常parserへ通り、candidateの26PNG/31記録はhashchain/RGBA正常・parser候補保持だが入力待機残存を拒否した。これは診断で、全8ケース/最終5gate/実client ZIP公開/実機の合格ではない。

上側入店の手続き的画像にはstage依存の価格消去があり、通常producerの最初の4部分候補と空結果限定のC資格も不一致だった。物理的なHUD/可視性と実商品の投影を照合してから対策を選び、分類結果の注入や可視価格の消去で合格させない。Mac反復用の専用diagnostic laneを追加し、現8ケースだけを実行する。配布用device laneの制御/実3.9/IPA確認は維持する。
