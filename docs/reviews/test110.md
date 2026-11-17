# TEST110: TEST109の4停止と再試行経路

2026-11-17（日本時間）。基準c2f7624。[通常計画](../plans/test110-device-failures.md)・[再試行設計](../plans/test110-irregular-retry.md)・[修正表](../fix-records.md)。実機改善は未確認。

## 最終CODEと実物検証

CODE `cdff28438adf31e45863dfb7af85e4535c8d46c4`、[実CI217](https://github.com/shuhei0720/necrogold-automation/actions/runs/44044340448) が成功。選択native173＋selector7、実CPython3.9.25の108method、実Mac Runtime29閉case、Spool production Green＋2件の実装後故障感度検査が同sourceで成功した。手続き画素・模擬時計・制御した分類結果を使うcallback/実FSの検査であり、iPhone実ゲーム受入ではない。

Runtime最終37c079fd・seal f4551161、native36/変更10/保持26を確認。IPA18,184,294bytes/SHA256 `677ce1d1b4fa62b4abad6a997b71d9f2e3a37531431d2e1fdc33a9b2b9f54af5`、CODE完全source1000files/全bytes・CRC・安全path、実compiler・9 Mach-O・保持sourceを照合。package/host/retained/macho/compileの5gateは各1回で成功し、ここで意味試験やcompilerを再実行していない。閉じsource2424bb4はCODEとの差が文書3件だけで、全1000files/CRC/全bytesを照合。完全source9,554,385bytes/SHA63a148ff。

Mac214はdurable C commit後に公開controllerSnapshotが古い製品不具合を検出。lock内で同C statusを取得しlock外cacheへ公開する5行修正を行い、215以降で同検査が成功した。215はUNKNOWN tail用の撮影制限が再表示後も再armするfixture不足、216は不可逆readOnlyの故障writerへ追記を求める誤oracle。元失敗/bytesを保持して製品Redと分け、finalではfresh PAUSE観測、原本全bytes不変、同UUID新owner凍結回収、全PNG公開chunkのサイズ/SHAと診断sibling receiptを検査した。最終combined fixture15540b13、新IRG3b831290。独立した限定再読で残P0/P1/P2なし。

[固定Release test110-build217](https://github.com/shuhei0720/necrogold-automation/releases/tag/test110-build217) をpublisher218/run44047487420で公開。IPA/source.zip/SHA256SUMS.txtの3assetを匿名GET200・全bytes/SHA・公開digest・tag2424bb4一致まで確認した。閉じsourceとIPAは再作成せず保存している。次は新IPAの更新/完全再起動・Start Server、メインiPhone11の通常1-1ポーズから --until-target で実機確認し、全campaign ZIPと各run原本を保持する。

以下は準備経過であり、「未実行」は当該段階の状態を示す。実機改善、未知の対象精度、人より速い実効速度、商品到達率は未確認のまま次の実機で評価する。

## 受領・原因

8添付は4固有run/98 PNG/108記録/214論理ファイル。全CRC/安全path/内包ZIP一致・manifest/hashchain・896×414 RGBA SHAを確認した。原本・Scene・作者の実行証跡はGit外。単調時刻順8d78→9bf5→fe54→80c6は利用者4周に整合する。

| run | 停止と実証 |
| --- | --- |
| 8d78 | known-ACK LEFT後189のgold UNKNOWNを変位比較前に拒否、SCREEN17/attempt0。189commitは元visualD内約2.418秒。generic stopのDは入力窓で、ACK後visualDではない。原Motionは半端なcamera移動でUNKNOWNを保持 |
| 9bf5 | FULL210の正常UNKNOWN後、元Sceneの遠方2セルが戻るのを待ちLATE。原250は未変更Ringで完全陰性/C検査1、同prefixで元Dまで795ms。後続251〜264はUNKNOWNなので判定開始済250を捨てない |
| fe54 | 開扉後244→245は通常strict零・同完全LEFT判断。遠方DIRT→FLOORと対角bracketed DOOR→GOLDだけで入店を拒否。進行先は観測FLOOR。右の敵は左入力の妨害/死亡の実証ではない |
| 80c6 | safe PARTIAL317→321でSHOP表示が重なるpause iconが旧最良IoU.7835となりScene UNKNOWN/SCREEN17。新3×9openingは.8135/.8122で既0.8全参照を満たし、通常SceneはFLOOR/PARTIALに戻る |

## 通常4修正の作者確認

最終normal C `6e8be76ed115ba39ba52d1ca75693c0416bfec00b706da4b49442e28699d0865`、Perception `43682044cf954eda380f16b161c17b0309b649768f3085ff56c8cb88de9bc1bb`。

- ACK: 変更前の実assertion Red後、新10＋直接旧37の47件成功。元8評価/visualDとUNKNOWN無再送を保持し、変位後も金壁不明なら元anchorで新入力を止める。原178→189の限定ACK境界seedではbaselineのSCREEN/attempt0から、UNKNOWN/reason0/input3/attempt1へ。未保存の次画像/実MOVEDを作っていない。
- FULL data: 変更前Red後、新10/直接旧16の26件、追加open/edge14を含む40件成功。分類sourceと移動anchorを分離し、元D/一用/最初の適格1枠FIFO・候補優先・不正観測後のnegative拒否を維持。公開C/producerの保存→RESTART、40ms撮影と44/80/100ms workerの競合を確認。限定原210→250→251では250を新jobへ採用し、80ms worker中も250を保持して正常陰性/C採用・次PAUSE票まで確認。実PAUSE/RESTARTは未実行。
- 対角閉鎖: 変更前1method/8方向側方assert失敗から新7＋直接旧20の27件成功。最終normal Cでも新7成功。通常observe→旧票撤回→同拍新票→begin/ACK→unit MOVEDを手続き画素で確認。原244→245は同判断/strict零/新opened relation1、before0。原記録に完全beat履歴がないためRuntime再演とは呼ばない。
- pause icon: 変更前1method/1assert失敗から新7/旧066・084の11件成功。3×9zero-padding openingは観測maskの部分集合。旧raw/縦opening、全36×36/0.8、footer/zone/floor/死亡拒否を維持。全98原のO0/strictO2で321だけUNKNOWN→FLOOR/PARTIAL、他97のScene全bytes不変・profile間も全一致。新321はCの既存partial比較/通常strict零も通る。

独立担当review110_irregular_designはnormal C/Perceptionと新4moduleを読取り、P0/P1/P2新規指摘なし。レビューの実行0。Runtimeのqueued RGBA保持・実callbackは別境界であり、このnormal成功だけで完了と扱わない。

## Runtimeの実Red準備

job切替時に旧cycle.framesを消し、移送元をincoming/initial/found/recent4/pinnedだけから探す既Runtimeでは、Cが保持したqueued sourceのRGBAがrecent4外で失われ得る。必要IDを保った移送と、実Swift Runtimeの分類workerへ届くことを検査する。Runtimeはまだ `42f2f88634357083e82be64e56e6ba0806f26454e278b74782caee763c5bb3e8` のまま。

新driver/check_runtime110と実Swift/C fixtureは、元Runtimeに対する指定2assert（新profile prepare/queued frame worker）だけをRedとして資格化し、compile/環境失敗を拒否する。公開RESUMEを横断する非適格FULL sentinelでfoundを占め、適格PARTIAL→最初のFULL250→8つの実accepted framesを経てrecent4外に出る条件を作る。各caseは別process。実RGBAのhash/kernel後に分類結果だけを制御する。画像/時刻は手続きfixtureで、原runの全Runtime再現とはしない。

独立読取review110_red_fixtureはP0/P1なし、P2のcapture IDだけの排出条件を指摘。公開accepted_frames増加8＋prefix維持を追加し、単なるID飛びを前提にしない。現時点ではSwift未実行であり、標準Macのbefore-source実Redを先行する。normal2件だけを封印した36source/他34保持の中間manifestを使用し、IPAや無関係な全Runtime試験は作らない。

## イレギュラー再試行

設計/網羅/安全の3独立読取で、敵の正の証拠、最初のBLOCKEDの処理順、保存容量予約、pending候補/中断回復・schema交差の不足を検出した。正のhealthbar/body、288Bの新companion、旧profile分離、元8/D、continueとrestart各intent/outcome、有限容量予約の[契約](../contracts/irregular-retry.md)へ閉じる。まだ実装承認/試験成功とはしていない。今回の98原に死亡/被害の証拠はなく、死亡後の実menuも未受領。通常4停止を敵としてリセットしない。

### イレギュラー設計の限定再読（2026-11-17 日本時間）

独立の設計・網羅・安全担当がSSOT `docs/contracts/irregular-retry.md` を再読。敵の正の証拠、最初のBLOCKED処理順と元8比較/D、全future raw/pin/metadata予約の初回P1を閉鎖。網羅のkind5 ACK→status/export/journal・MOVE診断分離条件を追記し、planの旧interface/API確認中と現在床条件を同期。設計/試験条件としてP0/P1残0。実装合格・実機確認という意味ではない。

通常修正の中間SOURCE `abf70e5` をpushし、Mac Red run44018498941/build210を初実行。新profile公開prepareの指定assertionはRed成立。queued画像のcaseは別assertionで失敗してRed資格拒否。compile/environment失敗ではないが、画像欠落のRedとして数えずfixtureを調査する。Runtime製品sourceはまだ未変更。

### before-Runtime Redの成立と通常移送修正

fixtureの最初の不足は、queued画像がpin24枠未満でfallbackに残り、欠落に届かなかったことと、旧PARTIAL→FULLの合法的なsource+3秒bindを誤って不変Dとassertしたこと。32枚の実accepted/current-prefix後続画像・既helperの元画像取得nil・実pin24を前提にし、source150ms/worker100ms/source3秒の既境界へ修正した。製品のassert/期限は緩めていない。

SOURCE `18e3683a28707984b5dcda5dd69f5e21abb07bde` の[Mac211](https://github.com/shuhei0720/necrogold-automation/actions/runs/44019392210)はprofile/retention両caseで指定FAIL1件/exit1・compile errors0を確認し、before-code Redとして成立。Runtimeは42f2不変、native変更は既正常C/Perception2件だけ。artifact14300681123（SHA256 f505ceb897b9f5caf71d10bb31f672f062a15be5ff16f15c395dd54b047e1add）をCRC/path/hash検証しGit外保存。product_pass=falseを維持。

その後、Runtimeは旧cycle.framesをsnapshotし必要ID集合だけへfilterして移送する3行を適用（直後hash9d03444e）。最終newprofile実装後に同sourceの現在Runtime Greenを確認する。Red成功は実機改善/新機能合格ではない。

### 新producerの独立差分レビュー（第1周・配布前）

P0なし、P1二件。旧死亡matcherだけ正の時のveto証拠欠落と、不完全な4個目を捨て残る3個を受理する反例。NONE/deathbbox/matches2の旧非neutral countsをveto専用に保存し、選択chain左右の隣接slotに未採用redがある場合の部分bar拒否を追加する。strong DEATH/actionの閾値は変更しない。実Red→Greenと既知3枚RIGHT/98 Scene不変を作者が再確認し、限定再読で閉じる。C/Runtimeは編集中で、このproducerレビューを全機能合格としない。

### C差分の独立設計・安全レビュー（第1周）

P0なし、P1二件。安全担当は、irregular restart outcomeのdurable後に初回floorの商品資格/epochを通常処理へ渡さず、後続UNKNOWNで失う点を指摘。設計担当は、translated menuからのRS予約/intent後にPAUSEへ変わると旧座標でbeginできる点を指摘。各反例を追加assertion Redへ固定し、初回floor/最初のgoodsの有界保持・通常handoff、予約UI種類と両UI座標の最終照合で修正する。producerの前P1二件は限定再読でclosure済。

### C・producer・Pythonの限定closure

producerは旧death vetoと部分4個目のP1を実API Red→Greenで修正し、新11/関連18、98 Scene不変・3RIGHT・O0/O2一致を再確認。red1px案は実原を拒否したため不採用で、全componentの全bbox・幾何半分56以上の参照支持/precision.90で限定する。独立設計の限定再読で二件closure。

Cはinitial FLOOR/first goods各1枠と元sourceによるhandoff、予約UI種類/両座標のintent/finalbegin照合、次DEATHの基準画像引継ぎを追加。残った初期epochは保存済firstfloorから `begin_initial_view` 1回を追加し、現在UNKNOWNのUI metadataを巻き戻さず元E+12秒を維持。最終C4c91d825の新30件Green、前29 assert維持。通常27件の作者回帰は直前94e4 sourceでGreen、この1call後の同source再実行は選択CIで確認する。独立設計/安全P1は限定再読で閉鎖。

Pythonはstate/outcome/intentの各command/capture ID結合、IRG参照PNGの出版前必須化、fixtureのkind5と実RESTART credit分離を補強。各実Red→Green、旧protocol診断omissionは不変。実Python3.9.25で新34+旧74=108件Green・sourcebefore/after一致、独立網羅の第3周限定再読で全指摘closure。元原本/hashchain/PNGを再生成して都合よく修復しない。Runtime/Spoolの実callback・FS/現在Swiftコンパイルはまだ未実施で、これらの単体/読取合格へ含めない。

### Runtime候補の設計・安全レビュー（第1周）

P0なし。設計P1は製品coreへのenable_irregular欠落/HOSThelperへの誤挿入、OUTCOME最初PARTIAL原画の取消/terminal欠落。安全P1はIRG Ring分岐による戻り値/encode検査迂回、JPEG callback終了をdecode/解析完了と誤認するdrain不足。新query説明の旧schema/profileは共通P2。製品開始時enable、失格workerはCLASSIFICATION保持、必要cycle原画のterminal優先、実pipeline leaseとCHECKPOINT admission停止で修正する。root読取ではunknown fixture caseがretentionへfallbackして任意PASSでGreenになる資格不足も発見し、閉caseと要求caseのexact marker/全case完了だけproduct_passを要求した。これらはSwift未実行の読取結果で、実callbackは次のMacで検査する。

### Runtime最終候補・試験資格のclosureと封印

製品Runtime79a85bf3は実startでIRG enable、worker不整合/encode失敗をCLASSIFICATION保持、capture pipeline ID lease/admission停止/実drain、checkpoint durable後の新UI source待機、必要cycle/firstgoods原画のterminal優先を実装。Wire9014b1cf/Spool074d76fc/Exportf2afe945、registry16dbeb6d。設計・安全の限定再読でP0/P1/P2残0。Swift実行とは区別する。

網羅レビューはpending OK UNKNOWN/NEGATIVE、RS ACK後outcome fsync故障、全IRG参照PNG/rawhashの出版前照合を追加し、Spool5故障の実boundary到達/正確注入例外も確認。元26維持の最終29閉case、要求case exact marker、unknown fallback禁止、全case完了だけproduct_passを静的確認して指摘残0。combined fixture860e4ec5/128391 bytes、driver58cecc08、新IRG31f60997/Spooltest2de3332b。実Swift compile/callback/FS成功は次のMac CIで確認する。

最終seal48260847を作り、固定G1基準から実G2適用で36 source全bytes一致、変更10/保持26、新irregular cap/profile正値、旧API.16/cycle/strict compiler profile3を確認。G1/R12/Ring/Nav/feature/ELFを保持。seal utility既存47件Green、diff/初期context16103 bytesを確認。新manifest/fixture/sourceのCIはこれからで、実機改善は未確認。
