# TEST102: 入店の追加観測と対象なし周回

2026-11-15（日本時間）。基準cb65755、製品CODE2c5afa96。[要件](../requirements/necrogold.md)・[契約](../contracts/native-control.md)・[受領](../reviews/test102.md)・[修正表](../fix-records.md)。実装前計画。実機2回とも不合格であり、旧CI成功を実機改善へ読み替えない。

## 1. 背景と根拠

4ZIP=2runの106原本/54record/48PNGを全照合。実1の152は開扉後PARTIAL、空UNKNOWNを採用したが、097の最上端ITEM条件外で保持終了。実2の254はFULL UNKNOWNを採用し、到着セルLEFT自体は非保護FLOORなのに、その隣接保護を重ねた検査が追加観測を拒否。両方とも期限内の正常な分類結果であり、期限延長・旧UNKNOWN入力の再送や変位加点を修正に使わない。

実2のRingは別に2阻害条件がある。下壁(-2,2)の正のDOORと、右看板の上側が欠けたため左右canonical SIGN中心Yが5px違うこと。両看板の底辺は132で一致し、row117のsy+15に一致する。row122は一致しない。原診断1回で両raw cap・3価格・3商品存在は成立したが、完全対象探索はまだ成立していないので元画像を陰性扱いしない。Perceptionは152/254各1回のcacheのみを使う。

## 2. 設計と所有

A: Controllerに、既097と別の観測済み入口通路証明を追加する。現在の実UP開扉・同prefix・元完全Decision・元状態/期限/候補/保管条件を維持し、原点と到着点は非保護FLOOR。中心の観測床通路、片側の連続した正のGOLD railと対側の入口GOLDから通路を確認する。全ITEMは上方にあり保護され、保護セルは実ITEMのself/cardinal投影で説明できることを確認する。最上段にITEMがあるかどうかを安全根拠にせず、全potential商品の既観測pixel包絡がUP後もviewport/HUDで失われないことを要求する。既097のtop証明とno_top_item拒否は残す。旧fixtureのDIRT railを勝手にGOLDにしない。

B: FULLの別観測証明で、原点/実到着セルの非保護FLOORという実footprintを使う。全ITEMのself/cardinal保護が正確に存在することを旧local/新footprintの両証明に共通して要求し、保護をその隣へ再度広げた箇所だけが旧local条件から外れる場合を限定して扱う。欠落保護で旧localへ逃げない。実上下面GOLD bracket、同軸の実開扉→既知ACK/visual UNKNOWNの履歴、全候補上界/強語拒否、全row/partial/ITEMの潜在ROI保存は101と同じ。protectedな到着点や説明不能/欠落保護は拒否する。一般経路の保護条件を緩めない。

A/Bとも後続の独立新static/current-prefix画像とstrict BLOCKEDを確認し、新ID/将来ordinalの新しい一歩だけを許す。ACKだけでは0credit、新しい実MOVED後だけ最新immutable画像の新jobへ渡す。旧ACK18の変位や位置/visitsを復活させない。候補/対象/UNKNOWN送信は保持し、元horizon・16入力・45秒walk・180秒session・取消・通常の一度限り制限を維持する。未来の実画像を収録済みと偽らず、新画像で判定できない場合を強制陰性にしない。

### A2: 新しい入口通路だけの有限観測episode（追加設計）

03:09 UTCの設計確認で、Aの一歩後も不明なら再び保持終了する未対応経路を確認した。152のITEM量子化候補の上端は63-86=-23で、一歩UP後13はpause HUD0..45に重なる可能性があり、二歩後49になる。この算術は未来の全商品可視の保証ではない。旧Aには新jobで最初の親期限を明示保存する仕組みもない。元画像だけで二歩を連打せず、最新観測で毎回資格を取り直す有限episodeを新102の正の通路証明だけへ追加する。旧097のtop証明と旧101横framingの一度限り条件は変更しない。

開始は旧top証明不成立・新corridor証明成立の正常UNKNOWNだけ。privateなorigin/stage、開始済み入力数0..2、実UP移動数0..2、level/opening-command/initial-job/source/prefix、最初の絶対horizonと全potential領域を凍結する。入力数は実begin時だけ、移動数はその発行UPのstrict MOVEDだけで増やす。各cycle_latch/bindで親を保存し、元horizonとのminを強制する。新しいjob/時刻/画像で上限・期限・親をリセットしない。

各歩は正常な最新PARTIAL/FULLの判定結果から、候補/対象/強い対象語・上界違反がなく、原点/UP到着点が観測済み非保護FLOOR、ITEMのself/cardinal保護が正確、親の実移動分だけ投影した領域と現在の全ITEM/保護/row/partial検索包絡の既観測pixelがUP後もviewport/HUDで失われない場合だけ再資格化する。未観測pixelを可視としない。空/非空のUNKNOWNを対象なしへ変換しない。さらに同job/prefixの独立新staticとstrict BLOCKEDを要求してから、新ID/将来ordinalのUP票を一つだけ出す。INFLIGHTはFULL表示だけで終了させず、ACKだけでは0credit/新jobなし、実MOVED後だけ最新画像を通常workerへ渡す。

最初の入力前に新FULLが来た場合、input0または確実未送信RESERVED1だけ旧票/slotを撤回し、新sourceの通常jobへ。分類を更新しても親/steps0は保持する。最初の入力資格は同じ実開扉prefix・現在も正の通路支持・旧episode参照からのstrict零・判定後の別staticで取り直し、旧票を再利用しない。二歩目は最初の発行UPの実MOVED・そのobserved source/prefixと最新jobの対応が必要。実MOVED後のgoodsUNKNOWNは保持して一般経路へ落とさない。

二歩後もUNKNOWNならHELDを先に確定し、通常partial/fullの別creditへ流れて三歩目を作らない。TARGET/CANDIDATEの保持が常に先、完全陰性だけ通常の保存/intent/restartへ進む。入力UNKNOWN/TWEEN、元期限失効、取消/前面/owner/世代/level・親の不一致は追加入力不可。新level以外でepisodeを復活させない。追加観測の権限は最大二歩で、未知全体の安全や商品確認成功を保証するものではない。

C: Ringに別policy6/board6を追加し、旧1〜5を変えない。商品3ITEM/両FLOOR cap/既policy3の側壁・入口bracketと閉じた下壁を正に観測する。下壁は全GOLD、または内側1セルだけ正のDOORで両隣GOLD・他全セルGOLD。DOOR版はsolid-columnのay-2にもGOLDを要求し、12個の異なる固定GOLDと正のDOORを要求する。単なる総数やDOOR→GOLD置換で許可しない。

看板は既canonical部品を使い、既ROI36×40、サイズ18..36×16..40、色支持150以上、横中心±2/間隔72±2を保持。少なくとも片側が旧structural_faceを満たす完全anchorで、対側は同幅・高さ以下・上端が同じか下にある成分。両底辺はsy+15±2かつ相互差±2で、失われた部分は上側prefixだけに限定する。各側1成分/別成分/余剰なし・唯一rowを要求する。中心Yの許容幅を一律に広げない。

旧価格3群・raw cap・商品帯全位置のbinary対象探索・強い対象語のveto・候補優先・数値有限/box/証明条件を同じ値で保持する。全商品登録や宝箱開封を追加しない。Controllerが独立に同じ位置/DOOR/GOLD/看板/全数値証明を検査し、Ringからの結果だけでUIを解放しない。header/ABIを変えない。

Controller担当はA/BとCの独立証明、Ring担当はCのpixel/分類とそれぞれの固有試験を所有する。Runtime/Nav/Perception/Bank/Coverage/canonical15/ELF/G1/R12/通信・回収/共有099 engineは不変。102入口は番号だけの薄いwrapperとshellにする。

## 3. 期待値・境界

Aは実152相当のrow-4のみ/正のrailで開扉→UNKNOWN→新static→将来票→実MOVED→最新jobまで。rail欠落/別材質、ITEM/保護不一致、潜在ROI逸脱、開扉/方向/Decision/prefix/期限不成立は拒否。旧097no_top_itemを保持。

Bは実254相当で到着点は非保護、隣接だけITEM投影で保護された場合の新観測。到着点ITEM/保護/UNKNOWN、保護欠落/無根拠保護、候補/強語/ROI逸脱、旧票/旧job・ACKだけ・同levelの使い直し・未知inputは拒否。旧101正例と拒否を維持。

A2は一歩目の実MOVED→まだ不明のPARTIAL/FULL通常job→別static→新しい二歩目→新jobを公開APIで確認する。入力前FULL再bind/旧票無効、合計二歩/三歩目拒否、正常陰性の既保存/再開、候補保持、ACK UNKNOWN/TWEEN/goodsUNKNOWN、元親期限/取消/prefix/level/identity、実変化のあるstatic/ROI/保護反例を含む。旧cca0の17+12件は旧版の結果として凍結し、追加featureの意味Redを先に保存する。

Cは全GOLD/追加DOOR・左右mirror・開口FLOOR/DOOR、片側の上側欠落とrow重複の分離を確認。12固定GOLD各欠落/総数偽装、2DOOR/端DOOR/隣GOLD欠落、両看板欠損/下端欠損/横欠損/高さ逆転/底辺不一致/余剰/複数row、cap遮蔽、価格欠落/4群、対象/強語・上界境界、証明改ざんを拒否する。旧1〜5の対象保持/完全陰性/不明は保持。

## 4. 試験と実装順

独立した計画確認→各作者が現製品と新test/import closureを私的凍結→要件に対応するassertion Red→最小実装→新単体と直接関連→独立差分レビュー1回。compile/setup errorをRedへ数えず、元assertの削除/skipはしない。

新しい限定結合は、通常Ringが手続き的RGBA/Sceneから出す実結果を公開Controllerへ渡し、陰性→PAUSE確認→durable→intent commit→RESTART実begin/ACK→新floor/outcomeまで確認する。候補/不明なら保持し、証明を手書きして再開成功としない。必要なら生成物の時間fieldだけを手続き的clockへ正規化し、証明本体は変更しない。手続き的UI応答であり実ゲームE2Eとは呼ばない。元254の新Ring校正は実装後1回だけ、cacheへ固定して未知精度にしない。

A2の追加は入力権限と親期限の新しい閉じたscopeとして独立した重点計画確認→意味Red→最小実装→関連回帰→差分確認を行う。Ring96952の39件と元254の新校正は同bytesの過去結果として維持し、追加分類/Perceptionや無関係な試験を繰り返さない。Controller/fixtureと最終選択CIの件数はA2最終inventoryで更新する。

## 5. 影響範囲と選択

変更はController/Ringだけ。各新公開試験と直接関連する097/101のframing、096/100/101の構造/対象証明、094の正常保存/intent/restartの該当methodを最終同source CIに選ぶ。正確なmethod一覧と件数は作者の最終inventoryで固定する。Navや全Runtime故障/worldを形式的に再実行しない。

Runtime42f2/headers/旧ABIはbytes不変なので新Macのqueue/取得/回収試験は追加しない。Mac191は旧Controller4101を使った歴史的部品試験として記録し、現Controllerを実行した証拠へ流用しない。C/Ringの変更経路は新公開Cと実分類結合で確認する。Runtime/非同期/ABIへ変更が必要ならこのscopeを停止して計画を拡張する。

## 6. レビューと残課題

実footprintの安全、ITEM量子化と保護の完全性、既観測商品の消失/HUD、候補を見逃さない全探索、12固定位置・上側欠落看板の独立証明、元期限と一度限り、正常陰性の保存/再開までを重点確認する。1歩追加であらゆる未来像を処理できる保証はなく、必要な未観測領域を陰性化しない。旧097/098の未確定停止・毎拍/速度/未知対象精度/耐久を解決済みにしない。

## 7. 保存と配布

修正表に日付/事象/原因/対策/確認方法/再発を記録し、実機不合格を継続表示する。seal36の変更2ファイル・実compiler・9Mach-O・保護資産・全source ZIPを照合。標準public runnerのみ。配布補助は歴史的Runtime証拠と今回のC/Ring検証を閉schemaで区別し、独立静的確認後に実物5gateを一度実行する。失敗は原因を記録しpassed gateを再実行せず再開する。固定ReleaseへIPA/完全source/SHAを保存し匿名全GET/hash/tagを確認する。

## 8. 実機

IPA更新・LoopCtrl完全終了/起動・Start Server/通知/通常VPN。通常1-1ポーズから`sh test_102.sh --until-target`で候補探索→入店→全商品確認→対象なしなら次周回を依頼する。対象/候補/不明/障害/元上限では保持。全画像保存/ZIP照合後の表示campaign ZIPを返却し、全run原本を保持する。実機到達率と次周回を主指標にし、CI件数を代用しない。
