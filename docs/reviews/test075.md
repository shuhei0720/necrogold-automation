# TEST075: TEST074受領と停止原因

2026-11-11（日本時間）。[計画](../plans/test075-motion-rpc.md)。baseline `488155f871a777652f9942af67d03b56b92546db`。raw/Scene/派生proofはGit外received074/test075-scenes/test075-rpcへ保持。

## 受領と停止

native started_nsで実順46efced0→0372e82b→1834cdebを照合。全3ZIP/54選択PNG（15/19/20）のbytes/SHA/全ZIP・PNG chunk CRC/896×414/manifest全offset・prefixhash/cursor/metadata/capture/active-report一致。v15/API16の_report/_result_metadata strict schemaは実validatorで成功、全回収resolved/terminal/drained。保持省略は未来画像で補完しない。2回目はretained20/export19、export4,152,859bytesで上限内。3回目のomitted_required IDs[4,8,11,17,116,130,140,154]をそのまま残す。追加回収目的の再実行は不要。

| 実行 / run | 元ZIP bytes / SHA256 |
| --- | --- |
| 1 / 46efced0 | 3,006,027 / `4bf5209dc54fe531151b56b22393751aba815ceb71fd75b36f4fdd94095e2c77` |
| 2 / 0372e82b | 4,321,137 / `5a594361461834ec6a45b801b2a0d140f8fd8a20d4ffe9091e78749cb8209f61` |
| 3 / 1834cdeb | 3,146,482 / `da3500d5025031935c0908cbf8008c410196dbcdbe2d27d94f73a40b7415d454` |

| 実行 | MOVED/方向入力 | restart | 停止 |
| --- | --- | --- | --- |
| 1 / 46efced0 | 4/4 | 0 | SCREEN17、最終PAUSE成立 |
| 2 / 0372e82b | 2/3 | 1 | MOVEMENT10、最終PAUSE成立 |
| 3 / 1834cdeb | 0/0 | 6 | CANCELLED2、最終PAUSE未成立、host取消確認 |

全商品可視0/3、全capture/dispatch failureはnull・取得timeoutなし。ユーザーの「リスタート時に金壁/候補を見逃さなかった」は今回の目視評価として保持し、全配置の認識成功へ一般化しない。

1は金を見つけて通常plannerへ切替済み。4UP後の次LEFT/reason8/target(-1,-1)/FLOORは未送信。56→57の全gold singleton(-2,-2)/保護0/full5/局所不変、遠方2cellだけSTONE→DIRT/DIRT→FLOOR。raw最良zero/.310936/差.48398は元閾値内、通常texture支持283<300でUNKNOWN。quiet→continuous検証11→各refresh拒否でSCREEN。C終了時のD残2.258888ms、capture終了基準44.552msと区別する。既存固定勾配は538支持/逆1/上下293/245/all73条件で強いzero証拠を持つ。

2の3入力目UPはNB+2.405719msに開始、282.0185msでACK。取得開始ACK後12.459/118.284/175.059/231.664/288.922/348.277/414.932/550.690msの80/82/83/84/85/86/87/89が全UNKNOWN、最終C終了にもvisualDが1.927秒残る。raw最良(0,+9)/score.58458/差.32166、実原画では世界が下36pxへ移りUP1tile成立。STONE0なので074石アンカーは対象外。旧detail/gradient/固定tile中央値は強95%未達。中心だけのblur/known union等を不採用とし、全21依存既知の新world面と独立phase・旧Lの一意unit対応を追加した。元閾値は維持する。

3はnative初歩公開窓の最早NB-100msより123.002783ms前、NBより223.002783ms前にhost cancelが届いた。native次target73389364471158は未送信で初歩eventなし、raw185は金壁2点が明瞭で実C LEFT/reason7を選べる。status RPCがresult_json段階で2秒を超え、clientが取消を1回送った。HTTP約50ms/復号約110msの後が支配的で、成功時の同段階も333/261/482/663/881/1205/1520msへ増える。host/nativeは別clock系で、絶対nsを相互の差分へ混ぜない。失敗reply平文bytesは非保持でexact replay/OS suspension影響を断定しない。

## parserの局所修正

validation.py SHA `bffea44e8ba7bbf4d71a42a4c117e7d6cfe25ffa7db63d3cba034961fd1fc363`、新test_json075.py SHA `ecd3b5fb039c9898d0b5cca0fa7a8db368e7c5f158d27c8ecb04e515dd784692`/5メソッドを凍結。Python逐字scanをC regexのtoken検索と既存scanstringへ置換し、短い通常keyをまとめて走査、長い/escaped keyは元経路。parse前depth16/nodes10000を維持し、finiteFloatはparse時に記録、duplicate/root型後に拒否して旧error優先を保つ。全tree二重走査を省く。size/UTF8/重複/非finite/overflow/2秒/再送/heartbeat/API/wireは変更しない。

1000同nodesの1桁/19桁nsでPython work比が増幅しない新代理試験は、旧parserで意味的Red1/errors0→新5Green.012秒。既存Protocol3/authenticated duplicate1/実OwnedRpcTimer result_json段階1の関連5Green。HTTP2はsandbox socket禁止という環境error後、その2だけ通常外で再実行し機能Redに数えない。最終実ソースで正常403/異常20と別corpus10,222の返値・errorが旧と一致。

最終実ソースの59KB status形JSONで155,425→54,687 Python行実行（64.8%減）、Linux中央値3.52→1.90ms（1.85倍）、長nsで3.62倍。途中prototypeの72%削減とは区別する。CPU代理/Linuxと実iSHを混同せず、端末2秒内成立は次の実機で確認する。ネイティブの初歩失敗をparser変更で直したとは呼ばない。

## Navと独立差分レビュー

最終Nav SHA `5b3fb3e8bfcc3586d65ce5576a12f9c4fc35a685891f8b8398a12c054ffcfd91`。既知結果を上書きせずUNKNOWNだけへ、金/局所/保護不変の強zero BLOCKEDと、金なしの完全旧L・左右raw位相・full21既知blur面の同方向unit MOVEDを追加する。旧primary/旧proof/数値/UNKNOWN無再送/予算を保持。新world上下境界だけはcamera原点52/半径2gap50..53へ実装前に固定、旧opening/zero65不変。

新静止5は旧sourceで意味的Red34/error0→Green。新MOVED10はcompile成功の旧074で4方向×2profileがUNKNOWNとなる意味的Red→Green8.749秒、テストSHA `5dd21443f52efa37b8ed9f7e2ead69c26af584f66d221627626c688fc8362805`。最新追加negative前のmotion10+static5+旧07411の同製品26Green21.455秒、追加後motion10を別途Green。assert削除/skipなし、O0/strictO2の両方を検査。実画像20組（同command応答19+未送信56→57）の差分は56→57 BLOCKED・73→83/85/86 MOVEDだけ。原83はACK後175.059ms開始の画像で580支持/逆11/上下413/167。原85/86も強度/全73差を満たす。80/82はphase、84/87/89は競合差でUNKNOWN。512組の同level保持FLOOR・全方向診断は上記と同一56→57の別方向静止だけが変化し、未保持応答や未知配置の成功とは呼ばない。

独立担当1名が計画・最終Nav/parser/runner・新単体の設計/拒否/運用を確認。初期候補上書きharnessでunit候補が重複し負例が偽GreenになるP1を、指定候補とのswapで全73位置を保存する修正により解消。文字出現消失・left静止/8/8.5/rightunitを追加して再Green、最終製品/試験に未解決P0/P1なし。世界内文字はblur観測には含むが、左右位相は元maskを3×3依存まで除外する。全8.5pxを識別できるという一般保証はしない。

### zero計算の同値整理

性能確認で、当初zeroの単発コスト増がreference併用時の2回呼出しを上回る懸念を確認した。実56/57と既知pose/visitsの限定suffixはreferenceなし旧5.487→当初6.315ms、あり旧8.071→当初12.557ms。snapshot/未保持履歴がなく実機全observeの再現とは呼ばない。配布前にzero専用で5依存材質/保護/axis/contrast/signを先計算し、before強特徴だけを全73照合へ再利用。旧gradient/旧opening/MOVED/Controllerを変えず、実20+手続6pair×73=1,898比較で支持/逆/上下数の不一致0。最終製品のstatic5+motion10 Green、追加cache同値assertを含め12.145秒。独立担当は追加差分だけを確認してP0/P1なし。Linux単発は当初6.374→3.040ms（旧2.696ms）、iPhoneの期限成立とは区別する。同一suffixのnew側のみ再測定し、referenceなし3.455ms/あり6.709msとなり、両枝とも旧5.487/8.071msより短縮。old再実行はせず、実機の全状態/期限成立とは区別する。

## 検証範囲と配布準備

runner SHA `91087876d3be0f9041fdb308d85e9395ee5df68b25947028b1b8a5e315a4cf33`。限定CIはNative32（静止5/移動10/旧07411/Controller3/原all73・067primary・ABI各1）、client8（JSON5/authenticated clock・結果JSON期限段階・復号後重複各1）、selector3の計43をactual methodへAST照合。5clientモジュール/HEAD blob、実JSON呼出4参照、実CORE、両074/075baseline envを空値でも拒否。selector3と未重複ABI1はローカルGreen、旧既済試験を追加再実行しない。全Runtime/worldは選ばず、未変更のfault集合を既定に積まない。

封印22sourceのうちNav1だけ変更、他21/API16cap14v15/ABI/G1/R12原40を維持して新IPAを作る。標準public Mac/Ubuntuの限定CI・実compiler/配布IPA/全sourceの照合結果は確定後に追記する。実機の商品到達/毎拍・人超えとiSH2秒は未受入。

## 実CI・IPA照合（build120）

code `445929566f34268eca6a70356667abce4844de02`、[run42949339514](https://github.com/shuhei0720/necrogold-automation/actions/runs/42949339514)。標準public Ubuntu/Macのdevice lane成功。Native32/client8/selector3=43件はfailure/error/skip0、実HEAD/blob・5client module・実JSON4参照と元ABIを束縛。実source-specific compilerは4C/5Swift/6RSP、raw log/pbx/args/hashを一致させ、Perception/Nav strictO2と他C O0/Swift Onone、hostmacro無混入を確認。未変更RuntimeはTEST070既存意味的Red1と現6callの境界だけを検査し、全Runtime故障/worldは未実施。

22sealのNav1変更/他21不変、G1/R12原40不変、API16cap14v15をIPA来歴と照合。IPA0.3.4/build120/minOS16.0/top.ebato.loopctrl、17,604,425bytes/SHA `8d1c8b6e6891948bb4739c097284ef8e3501fe0232ec4a1d7ac34e9f1eb3a064`、全CRC/安全path/重複なし。全9MachOで旧128+075fixture5=133 marker混入なし。実5verifierを各1回のみ実行し、追加product試験やrepo編集なし。rootもinner IPA全bytes/SHA/CRC/plistを独立照合した。

unsigned artifact13823804187は17,880,738B/SHA `f1257445e169ef5a48ac99765425bd0997e9e8d4fd8d948aed6c872d27110820`、validation13823789086は1,241,050B/`d5bef47f4350d9e5668a313c3b9adab376ef255975b1921bea341d36cc224429`、host13824795748は11,039B/`ba6ee627e121e055770dbfd39a589ad2cdf58c7f82bd030bfe1f8e5e68492b77`。APIのrun/head/branch/digestと取得全bytes/CRC/pathsを一致。code source ZIPは7,586,054B/`395637a42ad0c320f7d3c30ffd0e579c8609e37eb8ad94e476b8364cd283a8c4`、全559 tracked files一致。

[固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test075-build120)へ検証済みIPAと最終全sourceを保存する。最終sourceはstatus/本記録/実機台帳3文書だけを閉じ、製品bytesをcodeと一致させる。公開後の匿名全GET/SHA/CRCと実API digestを照合してから返却し、実iPhoneの全商品到達・毎拍・iSH2秒は次の一連試験で確認する。
