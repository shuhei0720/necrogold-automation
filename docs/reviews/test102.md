# TEST102: 入店継続と対象なし周回

2026-11-15（日本時間）。基準cb65755、製品はTEST101/build192のCODE2c5afa96。実機2回とも次周回未到達。実装前調査、修正の実機改善未確認。[要件](../requirements/necrogold.md)・[修正表](../fix-records.md)。

## 原本と停止条件

4ZIPは2runと内容が同一のcampaign。実順d809eed6→4114596b。全106原本ファイル/54record/48PNGをCRC・安全path・重複・SHA・記録連鎖・session/clock/generation・prefix/取得順・登録PNG/RGBA・厳密JSONまで照合した。浮動小数の元JSON bytesを再serializeで置換しない。campaignのcancelledはnative停止理由goodsとは別。

実1はUP9で実DOOR_OPENED、capture152/prefix9の商品PARTIALが期限内にUNKNOWN/INCOMPLETEで採用された。row_count0/partial_count0/safe_no_positive0/flags1。続くPAUSE10、pause161/terminal162。release_after0、再開intent/command0。ITEMはrow-4だけでrow-5に無く、097の空framingが要求するtopが成立しない。観測UP床と原点は非保護FLOOR、金railもある。旧097のno_top_item拒否fixtureとはrailの観測が異なるため、旧assertを消して一律に通す変更にはしない。

実2はLEFT17で実DOOR_OPENED、18はACK済みだが移動UNKNOWNのまま商品FULLとなり、capture254/prefix18を期限内にUNKNOWN/INCOMPLETEで採用。row_count2/partial_count2/flags258=BOARD|ROWS。続くPAUSE19、pause264/terminal265、release_after0、再開intent/command0。LEFTの到着セル(-1,0)自体は非保護FLOORだが、ITEM(-2,-1)の保護範囲をさらに近傍へ広げる検査が(-2,0)/(-1,-1)を拒否する。旧18の変位creditや再送を復活させない。

商品列は(-4..-2,-1)、両capはScene上FLOOR。下壁の(-2,2)はDOORでありGOLDではなく、既policy3/5の形から外れる。追加診断で、看板中心Yの差も独立した阻害条件と確認した。

元Perceptionは152/254を各1回だけ校正し、Scene/RGBAを私的cacheへ固定した。旧Perception/Coreと既libraryのhashは一致。追加Perception/未知評価/未来実画像の捏造は行わない。

## 過去修正と試験の不足

旧097/098/100/101の開扉・partial・FULL継続と修正記録を照合。2件とも101上端縮退creditや新framing後ではなく、継続admission前の拒否。旧対策削除・同原因回帰と断定しないが、同じ開扉後停止/次周回未達の実機不合格は継続している。

Mac101は宣言した旧開扉/ACK履歴、手続き的Scene、結果上書きで新workerの候補保持までを確認した部品試験。今回の実配置や実Ring陰性→intent→restartの実ゲーム成立を証明していない。公開Cの新陰性試験も証明fixtureからRESTART予約/intent未保存拒否までで、旧094が別に確認するUI完了経路との接続が不足していた。今回の限定試験は実画像の判定とその後の正規保存/再開まで結合し、実機E2Eとの違いを明記する。

## 計画確認

独立review102が8項目の設計・網羅・安全を要件/契約/旧C・Ring・関連試験と照合しGO、P0/P1/P2なし。Controller/Ringの各担当は実装前の意味Redを先に保存し、担当外source/旧assertは変更しない。102入口は既101から番号だけを替える薄いwrapper/shellで、共有099 engineは不変。振る舞い追加ではないため重複する鏡像単体を増やさず、実Python3.9のcheckとshell構文を確認する。

## Ringの1回限定診断

全native/import/wrapper/driver/原RGBA/Sceneを実行前に凍結し、私的instrument compile1、元254の通常assessment1、既canonical observationのsnapshot1を実行。追加Perception0。分類の既処理結果をsnapshotして再利用し、別の観測/slot探索/分類を繰り返さない。checks2556・certificate全数値・slot値/boxは実機原本と一致、outcomeUNKNOWN/coverageINCOMPLETE/flags258を保持した。host20.85msをiPhone速度の合格にはしない。

左SIGNはbox[287,103,29,29]/中心(301,117)/支持579、右は[359,113,29,19]/中心(373,122)/支持279。両底辺132は一致するが中心Y差5>旧2なので、row117/122のどちらも片側だけがstructural_faceを通る。下壁DOORだけを直しても完全判定にはならない。旧policy2のboard外枠/legacy glyph/merchantも不成立だが、そのfallbackを緩めない。

両rowでraw endcapと3価格群は成立、商品存在3も成立。policy6の全対象帯binary検索はまだ未実施なので、この時点で陰性完了とは書かない。12固定GOLDのDOOR版と完全anchor/同幅/共通底辺による上側だけの看板欠損を別証明として実装する。

## 最初の実装と原画像の校正

Ring96952d237fc84ad21be97ffbac7b02a70c35a3003d9dea6d4fe98d3c3fa38977で新12＋関連27の39件成功。Controller cca0a4b5d2445f5b9c00ad4bbcfcc0e95fabaf551bfe3b5c04bc92438f4a2d6dで新17＋関連12の29件成功。各featureの意味Redを先に凍結し、setup/import失敗はRedに数えない。旧assertの削除/skipなし。Ring18旧関数本体bytes、旧097/101拒否と候補/不明保持を維持した。両担当の独立差分レビューはP0/P1なし。

新footprint試験の流用したITEM変更が実際にはFLOORのままというP2を検出。変更成立のassertでその試験不足を先に再現し、実ITEMへの変更と明確なHELD/KERNEL/SCREEN状態、無変更時の将来票を確認する試験へ訂正した。旧101試験と製品は変更せず、狭い確認でP2解消。

Ringの原254は、修正後source/cache/import/driverを再び凍結し、通常assessmentを1回だけ実行。compile1/classify1/hooks0/Perception追加0。商品帯全位置binary探索/強語vetoを経てNEGATIVE/COMPLETE/policy6/board6/flags0、唯一row0(301,117)、商品3/価格3、checks2742。host45.124303msで元worker残98.261833ms以内。実画像の校正であり、未知精度/実機周回/人との速度比較の合格にしない。

cached実Result/Scene254をpublic Cのfresh cycle/observe/worker/assessへ渡し、時刻fieldだけ手続き的clockへ正規化して正常な完全陰性として採用された。prefix0等は宣言した手続き的な条件で、実prefix18の全履歴を再現したとはしない。152の旧top0/新corridor1/正確mask1とUP選択・admission1も、実visits未記録のため宣言した空visits下の条件付き校正。追加の原Ring/Perceptionは実行していない。

判定採用後・PAUSE入力前の別FLOOR原本は両runとも無い。最初の後続登録画像161/264は既にPAUSE後なので、実static pairとして使わない。未来像は手続き的試験の範囲に限る。

## 配布前に確認したA2継続不足

cca0のAは一歩後もPARTIAL/UNKNOWNなら追加接近できない。row-4→row-3では旧top/新corridor条件外となり、通常partialは隣接保護、FULLは水平ACK-UNKNOWN履歴の条件で拒否される。ITEM候補上端-23が一歩後13ならpause HUDに重なる可能性が残る。二歩後49という算術も全未観測領域の解消保証ではない。

旧cca0の29件と原画像校正をその版の証拠として保存し、配布前に計画§A2を追加した。新102通路に限った最大2入力episode、最初の絶対親期限/全potential領域/level/親IDの保存、最新分類/独立static/実MOVEDからの新job、FULL入力前の未送信票撤回、2歩後UNKNOWNとgoodsUNKNOWNの保持を別scopeで設計。旧097と水平101の一度限りを変えない。独立review102は追加計画と私的状態案10788adを確認してGO、P0/P1なし。実装前の意味Redを追加してから進める。

追加A2の私的状態案10788adを独立review102が確認し、P0/P1なしでGO。開始済み入力の返却禁止、親期限と全potential領域、FULL前の未送信撤回、二歩後HELDを重点確認した。旧cca0/初回74件scopeの証跡を保存し、新Cと選択CIをpendingへ戻した。追加scopeの実装前に意味Redを測る。

## A2の実装・重点確認・最終作者試験

凍結cca0で親期限の更新と、実一歩後の不明から二歩目へ進めない点を別々にassertion Redとして確認。新しいprivate episodeは元親/level/入力数/実MOVED数/全potential領域を持ち越し、旧097と水平101を変更しない。通常Ringの完全陰性をactive episodeへ渡したときHELDへ誤分岐する不足も意味Redで検出し、既存のNEGATIVE_PAUSEと正規UI経路へ接続した。

重点差分レビューでP1を1件検出。pending HOLD/ASSESSのFULLを安定性/prefix検査前に新jobへbindし、旧workerの対象/候補を捨て得ること、queued UNKNOWNで上界/強語検査を飛ばすこと、入力用親期限が正常worker自身の残予算まで取り消すことが同じpending保全境界にあった。各反例を意味Redで保存し、適格FULLのFIFO保持、旧候補優先、UNKNOWN安全検査と親失効保持、元worker期限の維持へ限定修正。不適格FULLのcycle不変と、一歩後に既判定済みPARTIALから新FULLへ更新する正常経路も保持した。狭い修正確認でP1解消、残P0/P1なし。Runtime/ABI/通信/保存は変更していない。

最終Controllerは8c74aa3e931d732af3d88dc52c080ad7c04b2ba9bc1607258cbe9e5df1ea5b11、episode試験4e53a56f269df171806dbc635d1248a6a7056731ab47d90cfa5549d3e49cbba3。新29＋直接関連12の41件を同sourceで一度実行し成功、errors0/source_unchanged。execute-time57ファイルは実compilerが使う27 native-addition資産・Python/helper27・Ring feature JSON3を凍結したもので、配布native36の全てが試験compile入力だったとは書かない。Ring96952の新12＋関連27は不変sourceの39件で、合わせて80 product methods。最終選択CIはselector6を加えた86件/16scopeへ結合する予定。

証跡の限界として、A2陰性joinのRedは実行前のC d060/Python/common-C44を直接凍結したが、Ring producerのC/header/dataはそのbefore.jsonに直接列挙していなかった。先行する不変のfinal29/sourceに残る同Ring96952の資産を補助来歴として明示し、完全な直接compiler-input bundleと偽らない。最終41の入力凍結はこれらを全て含む。過去Redの再実行や時点の書換えはしない。

rootは最終native36を封印し、基準cb65755からの変更がController/Ringだけと確認。manifest SHA99b2cfe825f86ed888cc14d69097f66b4849978ce164686641984e760d336017。旧header/ABI/Runtime/Nav/Perception/Bank/Coverage/canonical15/ELF/G1/R12/共有099は保持。新しいRuntime/Mac実行は行わず、Cの公開worker/observe/assessと通常Ringの結合、変わらないRuntimeのjob/owner guardの静的対応を確認範囲とする。Mac191を現Cの実行とはしない。IPA実ビルド/実物検査/固定公開/実機はまだ未実施。

## DEVICE194と実物照合の完了
DEVICE194/run43675514954、CODE`0efbbf319425dd82a18c5241c3c432a683d51e66`が完了・成功。選択86件/16scope（C41＋Ring39＋selector6）と未署名IPA作成が成功した。今回変更scope内の残P0/P1なし。修正後の実機改善は未確認。
IPAは18,039,374 bytes、build194、SHA256 `cf6a59a7aec231be04ce1328817a6f6585ae259c246461780b979a69ee020198`。元artifactはunsigned14146855385/validation14146702608/host14146331297で、API digestと全ZIP bytes/CRC/安全path/重複/IPA plistを照合した。
実物package/host/retained/macho/compileの五つを各一度、読取専用で照合して成功。旧1561＋新59＝1620 marker、native36/変更2、実compiler記録とresponse/filelist、9 Mach-O、seal/来歴を確認。追加semantic/compile/classifier実行0。
原254 Result→公開Cは時刻正規化を伴う校正であり、実prefix18全履歴・端末Runtime・実ゲームUIの再現ではない。新しいRuntime/Mac部品試験は追加せず、Mac191は旧C4101の歴史的証跡として区別する。
五つの照合証跡SHA256:

| gate | SHA256 |
| --- | --- |
| package | `c322bff0fbeb1512d783700c1473690164e937adb49034d86ba738c424208b25` |
| host | `9b9fbfc32d72c3da2626ddd6f53476e565b026496da061493e9f0c3285b39797` |
| retained | `c15a867f7ccd2d48072da5165ba847c50dbcc96778e8d149ea53c11b1ca19e56` |
| macho | `bfd657a1c1cb781c42e4620445a652c11405cfaafbff7ee10b8ee8eb747668a2` |
| compile | `ef0c8ba549aa7ce7f07c1c8bb34dda937c0d6e4643f4d32961bc433cb97544f1` |

試験コードを固定後、終了資料だけのcommitを完全sourceへ含めて固定Release `test102-build194` に公開する。匿名全GET/hash/tagの成功は公開後に別記する。IPAの追加試験を未実施なのに成功扱いせず、実機では候補探索→入店→全商品確認→陰性なら次周回を依頼する。
