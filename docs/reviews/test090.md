# TEST090: 実089の4回を受けた修正

2026-11-13（日本時間）。基準169eb67bc4906c83e6bedf30678b99a240b44522。[計画](../plans/test090-device-stops.md)。raw/原PNG/Scene/実行log・配布照合receiptはGit外。

## 受領と主指標

添付順ではなく同じ端末時計のnative開始順で対応した。4ZIP/80原PNG・18,839,952ZIP Bを全CRC/SHA/size/strict load/publication certificate/canonical sidecarと登録fileのwhitelistで照合。全4runの回収と出版は完了している。今回の実機の商品全体確認は1/4。

| 実順 | run先頭 | 実機と記録 |
| --- | --- | --- |
| 1 | c11722aa | 2restart/5歩、3商品と3価格が全体可視、GOODS/PAUSE。ロングソード・カリスマのゆびわ・ホルスターと読め、のろいの見逃し根拠なし。authority204はunknown/no_target_evidence |
| 2 | 4bca6a1d | 候補から2歩後にUP実1歩を確認できず8UNKNOWN、movement停止 |
| 3 | 059f6b82 | 候補から4歩後、新しい扉/金壁と遠方の床判定で未送信LEFTを拒否、screen停止 |
| 4 | 848d9572 | 金可視から5歩、鉄扉の開通をBLOCKEDと判定、下の商品を確認する前にmovement停止 |

実1は対象のみを識別する現契約のunknownであり、対象なし確定/全商品名識別ではない。ユーザーから「iSHのログで不明って書いてたから」と追加回答を受領し、画像上の対象見逃しとは区別した。正例309との目視比較・同じ独立担当の読取とも中央は別ringで一致した。unknownの表示だけを「のろいのゆびわとの一致は未確認（対象なしとは未確定）」へ変更する。新しい陰性判定/全商品識別は混ぜずoutcome/schemaは維持する。

実1のauthority最終chunk応答→次bulk要求は5.275987秒、manifest要求→bulk開始9.722475秒、host開始→最終response53.497227秒、native相対12.913819秒。端末/hostの絶対時計を引かず、5.276秒を純C秒とは呼ばない。画像保存・初回配置/全source検証・PNG・分類等の合算で、実iSH/人間速度は未達確認のまま。

## 原因に対応する範囲

実2は元STONE1個だけが移動先の心臓HUDでUNKNOWNとなる場合を、残る可視STONE/非共線DIRT・全73候補の独立raw/world/axis証拠で厳密確認する。実3は同じ安全な一歩と目標を保持した新gold bracket露出に限り、元未送信ticketの全期限/予算下で既FRESHへ移す。実4は観測された薄鉄の縦線を金bracket内でDOORと読めるようにし、既開扉経路へ渡す。開扉は0歩であり商品の観測とは別。

icon kernelは整数上界と同じbinary64積の再利用による意味不変整理のみ。閾値/feature/word/出力順やsource15検証は変更しない。旧UNKNOWN/未観測商品を陰性へ変えず、自動購入0・全画像保持・入力権限/有限予算・UNKNOWN無再送を維持する。

各変更の有効Red/Green、原画校正、選択関連、最終source/配布の確認結果は確定後に追記する。通常の限定反復として独立reviewは同じ1担当、無関係な全Runtime故障や旧33群を配布前提にしない。実到達率・毎拍/人超え・未知陽性精度は実機で別に確認する。

## 修正記録と再発照合

追加ユーザー指示により[修正記録表](../fix-records.md)へ主要履歴80件と今回6件を整理し、修正日/事象/原因/対策/改善確認方法/再発数を記録した。AGENTSの修正前参照を必須とし、今回の着手済み分は提出前に遡及照合。旧038の可視anchor、074の通路/開通、055/081のFRESH・再取得、082の明示回帰、088/089の判定対策を確認した。類似症状だけで同原因再発へ加算せず、同じ原因が対策後にも出れば継続/回帰を記録する。

修正日や単体合格・保存画像校正を改善完了とは扱わない。実機改善未確認は未確認で、表の過去対策を原因候補から除外する根拠にしない。既知の082配布前回帰と088の待ち継続も記録し、不明な過去回数を0にしていない。

## 独立した差分レビュー

同じ独立担当1名が計画・今回の全製品/新試験・契約/文書・配布selectorと実物readerを確認し、製品/selectorは残P0/P1/P2なしでGO。独立compile・意味試験・画像分類の再実行は0。編集は本節の追記だけで、原画像204/108/115の目視とsource/証跡の読取を行った。実物/公開後の照合と修正記録表の最終追記は別gateとする。

実2のproofは旧16段がUNKNOWNの後だけ働く。元可視STONEのちょうど1個だけが投影先の心臓HUDでUNKNOWN、他のSTONE全保存と可視2以上・非共線DIRT9以上・9候補唯一・同方向unitを要求する。raw/両bandの有限性と差、world95%/axis75%・各2領域100以上・全73候補への差は既条件を再利用してANDする。指摘したP2（元/支持anchorの可視性をheart以外ではproducer不変に依存）は新helper内の全7HUD/25px sample除外で解消し、hidden特例はheartだけを維持した。HUD外消失/他材質/金壁/扉/商品/保護/非unit/逆移動・既知motionの上書きを拒否する。新helper/callを逆除去すると旧Navigation全bytesが一致することを独立に照合した。

実3は元state/timing/chain2・run8 guardを維持し、旧monotone本文は完全一致。新helperは前方3セルの旧DIRTからbracket DOOR、旧金1→新金2、遠方DIRT→FLOORという限定関係だけを扱う。cached全5fieldの一回の証明と、最新同方向/同目標2セル先/FLOOR/reason8→7、strict BLOCKEDの後に既FRESH12へ渡す。旧IDのbegin/completeは新状態不変、予約のtarget/notBefore/deadline/ordinal/visualDと元入力creditを延長しない。

実4は旧FLOOR/上下GOLD・GOODS_UNKNOWN/原点外/保護外/全ROI非HUDに限定し、同じ3列以上がそれぞれtotal20/上12行8/下13行8を同時に満たす閉縦線だけをDOORへ回復する。原108はSceneのFLOOR→DOOR一byteだけ、原115はPARTIAL=1を含め全bytes不変で、公開motionは開通0歩。PARTIAL/商人露出を全商品確認と扱わない。新helper/callの逆除去で旧Perception全bytes一致を照合した。

作者の新native11methodsの有効assertion RedとGreenを確認した。各初回の作図不備・二候補/HUD重なり・旧SAMEへ合法に入る負例の訂正はログへ残り、期待や製品閾値を弱めず該当methodだけ再実行している。実2の原8観測は初めの2枚のUNKNOWNを保持し、適格な後6枚をUP1へ回復。P2追加後の元Sceneのanchor全7HUD外をsourceへ結合し、原8の再分類を不要とした。実3の元のlive beat modelは未保存であり、Controller試験の時計は明示的な合成値である。未来の実ゲーム到達を再現したとは扱わない。

ringのint32上界・積前int64拡張・同じvolatile binary64積の256値再利用は意味不変。全word/探索順/first-tie/閾値/source15検証を維持し、実物56,088B ELF32/LE/i386/SHA885356d8bf0fe8b2088ebc433e5497e58813821f4e0bfa129cd0b4f725c2535aとmanifest15sourceを独立に照合した。作者の異cwd再build一致・原309/235/今回204のmode0/1計6packetの全raw bytes同値・実3.9公開backend1Greenへ結合する。UI2literal以外のtest087/ring_early本文不変を逆変換で独立に確認し、既publicationの否定文言assertと実3.9関連3Greenは元の候補保持の意図を保つ。

native seal731490124fc8be88b367ab194cd032be6bb76cc95f816e8afb6e6b732eb22fedは22source中Controller/Navigation/Perceptionだけ変更、残19は不変。API16/cap15・既ABI/Runtime/G1/R12・元期限と入力権限を保持する。090 entry/shは089のtest番号だけの変更として全bytesを照合した。新selectorはactual patched source/HEAD/repo8C・header/ABIとring15/ELFを結び、表示literal2箇所だけの既Python差分を許可する。新11/関連9とselector4の24methods/9scopeを固定し、skip/error/空/不一致を成功にしない。ここで24は実CIの選択集合であり、作者のselector self4Greenを全24の実行成功へ足し替えない。

device laneでは旧070/081を再実行せず、Runtimeと対応fixtureの不変bytes・過去receiptへ結合してnot_runと明記する。MacのIPA実compile/Perception profile/package/provenance検査は無条件で残す。実物readerはpackage/host/retained/Mach-O/実compilerの5gateを維持し、CODE/RUN/BUILDとactual GOの未設定を拒否する。指摘したP1（新forbidden markerの空/欠落を許す）は、固定HEADの新fixture3とselectorのAST/class/testmethod/Cshim定義から得る完全集合へ結合する修正で解消した。旧268markerは保持し、今回の新25を足す。実物を読む前のcoverage/self検査と実CI/IPA検査は分ける。

ユーザーの修正履歴ルールは今回の修正着手後に追加されたため、今回分は提出前の遡及照合であり、以後は修正前照合を必須とする。再発数不明を0にせず、同症状の別原因と同根本の再発を区別する。修正記録表の今回行が未実機確認を完了扱いしていないことを最終文書gateで確認する。商品到達率・人超え/毎拍・未知陽性精度は未受入で、単体/校正/静的reviewを実機合格へ転用しない。
