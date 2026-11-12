# TEST083: 初金露出の移動確認と部分商品の観測位置

2026-11-12（クライアント日本時間）。基準 `3db9d9d244084f4fcc95637717f9cb073b57571d`、TEST082/build137。実機主軸・固定時間上限なし・品質維持。単体/関連回帰と必要なIPA照合に絞り、同じ独立担当1名が計画/差分/実物を確認する。

## 受領と原因

実順は7eb9c53d/156d2950/d50399c6/41891edf。4ZIP/80原PNG・20,823,798画像Bを全hash/CRC/現schema/client_load/manifest/prefix/cursor/実ZIP公開gateへ照合、全PAUSE/完収、正常見送り判断16/16保持。実2の古い3captureはbounded ring行だけがなくexport画像/metadataは正常、欠損行を補完しない。host error0。実2原494と実3原199はstable prefixで全3商品/価格125-50-13と125-75-50を確認し到達2/4。対象指輪の識別成功ではない。

A: 実1は開扉後の実LEFT1でpublic entered_gateがworld(-5,0)/LEFTを証明。その後もgoods PARTIALのままLEFT/reason8、最後no_path。商品は下方にあり、price3/item3が成立する原297/343でも元heart/footer HUD領域と重なるためPARTIALが正当。旧GOLD距離の目的関数は下方向を選ばず、次DOWNの観測cellも商人heart帯でDIRTとなる。認識と目的関数の二因子を分ける。床を仮定したcounterfactualを実Perceptionや入力権限にしない。

B: 実4 cmd6/source104→113..126は実LEFT1、8UNKNOWNでmovement停止。104はCLEAR/金0、115は新CANDIDATE/金1で、旧B1/B2の両CLEAR条件に入らない。newGOLD(-3,-2)の元projection(-4,-2)はUNKNOWN。115は元全STONE6保持/非共線DIRT・全9translation unique、raw unit9px .57487/gap .27673、旧075 worldBlur396支持/1bad・帯230/166、独立両phaseのunit .536690/.535891と有限競合gap .408775/.292438が成立する。113はraw8px/gap不足で拒否維持。117以降の一部phase runnerupがINFでも、それを差の成功根拠にしない。

## Bの限定設計と着手順

Bを先行し、Aは後記pixel/経路設計の追記と同じ独立担当の確認後に実装する。

- 全旧motion後UNKNOWNのみ、両FLOOR/GOODS_UNKNOWN/全ITEM・保護0、before CLEAR/金0→after CANDIDATE/金exact1、その新金の元projection UNKNOWNに限定する。
- 元origin/実nextと最新originの観測床、raw同方向厳密9pxunit/high>.45・finite best/runnerup/gap.08、全旧STONE保持＋非共線DIRT/unique9、旧075固定21依存blur300/95%・camera52独立帯100/全73元15pp差、既082と同じ独立phase/finite runnerup条件を全ANDする。
- 旧helper本文/順序/閾値・旧known判定は不変、新helperを末尾へ追加。MOVED以外、開通/入店/商品credit、未知入力の再送、元期限/8評価上限/予算変更へ広げない。金を推定でSceneへ追加しない。適格115で成立することを校正として確認し、未取得の後続ゲーム応答を捏造しない。
- 公開ng2_motionの手続pixel fixtureで実装前assertion Redを実測し最小Green。4方向/O0・strictO2、同方向unitと旧stage UNKNOWN前提、新金2/元known投影/旧金あり、材質anchor一意性、ITEM/保護/商品/原点床、raw/blur/phase閾値と非有限を境界/拒否として選ぶ。新テストinventoryを作者が固定し、実画像自体をCI必須fixtureへ埋め込まない。

## Aの限定設計

### A1: 非重複の観測床pixel

既DIRTだけへ、full25×25の元texture成立と中央値の39≤R≤52、45R≤100G≤68R、25R<100B<44Rを要求する別proofを足す。固定upper12行25×12=300pxと、旧ROIの直下かつ同36px tile内のy=cy+13..+17の25×5=125pxを別々に読み、両方R≥16と元floor palette/textureを要求する。新金/商品/HP/PARTIALラベルは床根拠に使わない。

full625＋outer125の全750実依存pixelを、元HUD除外/画像境界の対象にする。非重複witness425pxを足すために旧625だけの除外を流用しない。solidDIRT/黒salt/単帯/texture無しから入力床を捏造しない。元palette/GOLD/gate/wood/量子化082の3proof本文とenum/Scene ABIは維持し、既商品処理のITEM/保護による上書きも維持する。

Git外full-pipeline校正は新80枚の8画像35セル＋旧97枚の1画像1セルだけDIRT→FLOOR。全36を元画像で視認し、UNKNOWN/GOLD/STONE/DOOR/ITEM変更0、全177非tile/商品/保護/署名/拍bytes不変。これらは変更に使った資料で未知評価ではない。

公開RGBAの実装前Redで、元DIRT/中央値49-24-15に固定2帯の床証拠がある場合をFLOORへする。4〜5methodsを目安に、両帯の元色/texture/16境界、fullR/G/B整数境界、片帯・黒salt・solidDIRT/wood/STONE、GOLD/DOOR/ITEM/商品保護、拡張ROIのHUD/alpha/画像範囲を確認する。CIへ実機rawを埋め込まない。

### A2: 部分商品を見やすくする観測床目標

既valid_scene/VISIBLE/原点保護/gold/入口検査と入口halfplane maskの後で、実入店entrance.valid1・goods PARTIAL・現在Sceneのgrid内ITEM≥1（既商品処理の位置候補を含む）だけを対象にする。保護だけ/ITEM無し/grid外だけ/無入店/invalid入口/商品UNKNOWNには広げない。ITEM hullは位置のヒントであり、ITEMとprotectedは常に通行禁止セルのまま。

ヒントの視認帯をlocal grid x=-6..6/y=-2..2に固定する。canonical中心232..664/135..279はinventory右端143/minimap左717の内側。実297の商品矩形317..382はDOWN2で245..310へ移り、heart開始321/footer380から上がる。これは位置選択のヒントであり、未観測の価格や全可視の証明ではない。成功は引き続き元Perception VISIBLEだけで決まる。

既paths(s,0)で全経路が観測FLOOR/非保護のreachable goalだけを列挙し、origin/passed入口とworld goalが既[-16,16]外のものはgoalから除く。既入口halfplaneを通して逆戻りを許可しない。候補qへ進んだと仮定したITEM hullのoverflowを

`L(q)=max(0,-6-(minX-qX))+max(0,maxX-qX-6)+max(0,-2-(minY-qY))+max(0,maxY-qY-2)`

と定め、originより厳密に減るgoalだけを選ぶ。最小L→縦overflow→最短path→visits最小→既lexical[first]→lexpoint(goal)の順とする。改善無し/帯内の場合は元chooserの結果を保つ。成功時だけ既reason8/obstacleFLOOR/観測goalのfull5を返し、旧GOLD gate/vantageより優先する。旧gate/距離/tie本文を変更しない。

実297の全床資格を別途満たした場合は下y4の商品に対してgoal(0,2)/firstDOWNとなる。複数入力を予約せず、各実MOVED/最新Scene後に再選択する。DIRT/UNKNOWN/STONE/GOLD/DOOR/ITEM/保護への入力、purchase、VISIBLE/HUD緩和、新Controller例外/enum/期限/予算は追加しない。

新公開6methodsで上下/左右/低位置と全4入口、帯境界/改善無し、最短/visits/既lexical/lexpoint、全pathの非床/保護拒否・回り道、source/visits/入口bytes不変、旧無入店/invalid/UNKNOWN/VISIBLE/item無しのfull5保持、公開Controllerの開扉→ACK実入店→部分商品への床予約→VISIBLE優先取消を確認する。pure Navの条件付き手続Sceneと、A1の実pixel床判定を混同しない。

A1/A2はこの追記を同じ独立担当が確認してから、各作者が公開assertion Red→最小Greenを行う。Perceptionはcandidate担当、Nav chooseの前半だけはcontroller担当、B motion末尾はnav担当で所有を分け、同ファイルの全体置換をしない。

## 検証と返却

各作者が意味Red→局所Green、編集した試験だけを再検証しログを保存。rootは最終同sourceの保持原pairで既known回帰と新適格証拠を確認。CIは新単体＋影響する既関連/selector自己だけ、ABI queryを含める。Runtime/core4/API16/cap15/client16・全期限/予算/UNKNOWN無再送/R12/G1維持を前提に、無変更Runtimeの全故障/worldを追加しない。固定旧Red133再利用と今回のMac Greenを区別する。

native最終sourceをfreshG1からseal/applyし、独立差分GO→same-code host/IPA→5実物verifier各1回→固定Release IPA/全source→匿名全GET/SHA/CRC照合へ進む。新実機の到達率/毎拍/人超え/対象認識/通知/対象なし循環は先取りしない。通常1-1ポーズからrestart→候補→商店→全商品確認の具体的な複数回テストとrun別ZIPを必ず依頼する。
