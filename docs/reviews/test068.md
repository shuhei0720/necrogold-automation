# TEST068: 下端金壁への観測床1歩と回収改善

2026-11-10（日本時間）。[計画](../plans/test068-fringe-collection.md)。TEST067は1回目0歩、2回目商品3品/自動GOODS・PAUSE成功。全22選択PNGのSHA/bytes/CRC/896×414/manifest/時刻prefix一致、最後のread-only回収で全画像保存済みresolved=true。3回目以降の新startは無い。現場結果とhost_deadline履歴を分ける。

## 原因と局所設計

1回目の実金壁は(-1,5)/(1,5)、raw625画素中436/373。grid y=-5〜4の外でHUDにも隠れ、GOLD_CLEARとして対象外PAUSEを送った。原点/Down次床/周囲FLOOR・保護0は実画像で観測。PAUSE不成立の物理原因は未特定、約94msの復帰後受付間隔のせいと断定しない。

CoreにEDGE_DOWN=3を追加（layout不変）。Perceptionは元色/280閾値・全mask/densityを保持し、原gridgold0/UNKNOWNgoods/全保護0の一意raw対だけ扱う。j5はenumのみで座標を偽装せず、j3/4はHUD重複UNKNOWNの実2セルだけ復元。中央金/片側/曖昧対/heart/矢印/商品/保護時は採用しない。119既知原画のうち今回第1runの5枚だけgold_state1→3、他114全Scene bytes不変。全119でO0/strictO2一致。未収録の1歩後の画面は合成して実機成功としない。

Navは明示hint/gridgold0/原点/未通過/UNKNOWNgoods/全保護0/観測Down床からreason9/target(0,1)だけ。Controllerの初期同期とvalid enumだけを明示拡張、既存safe_floor/retune/reference/SAME/FRESHのcandidate2境界は不変。全accepted current-prefix pre-send（mask0含む）で元source/全5field/局所床/全保護/strictBLOCKED/元時計を再証明し、beginは最新証明capture IDだけ定数時間検査。actualbeginで1回消費、UNKNOWN/BLOCKED edge再送・retune、実1歩後の残hint2歩目を禁止。通常gridgoldが見えれば既存plannerへ戻る。

clientは元cursor/prefix+全SHA/header/dimensions/manifest/完成先bytesを確認後、開始時から完成済みの画像だけper-image再write/両journal再保存を省く。partのみ/不一致/欠損/未完cursorは旧publish順、全deadline/cancel/進捗checkを維持。回収開始callbackはlock内初save後/status前に任意通知し、default無出力/schema不変。CLIをnative理由と回収状態へ分離し、回収のみ/完了後は次回freshを明示。履歴events/stop_reason/UUID/旧v/90秒export/180秒とresolved条件は維持する。

## TDDと独立レビュー

newfringe6は旧Cで8semantic failures/errors0/.659秒→Green6/.708秒。newedge6は固定067全C/hで18semantic failures/errors0/1.312秒→Green6/1.509秒。Nav陽性/拒否、edge1歩→通常gold復帰/残hint拒否、元未送信ID・budget、UNKNOWN/Blocked/入力状態、prefix/goods/owner/lock/前面/実commit期限を公開Cで確認。遠方quietの元ID/全command bytes保持も含む。

client新9は旧v14で8semantic failures/errors0/1.220秒→新9+関連25の34Green10.431秒。開始時未完cursorが途中完成した場合の不正skipを追加Red1→修正、既存method内の非terminal原因表示P2もRed1→terminal時だけnative理由優先へ修正。localhost server不可だった最初のsandbox試行は環境失敗として除外し、許可したloopbackで正式Red/Greenを実行。旧tests期待は変更していない。

独立レビューP1: edge未送信D後にtickより先にobserveが来るとSCREENで終了。既存method内にtick/observe先行を追加して意味Red1/errors0→initial_recover(UNSENT_DEADLINE/ACTUAL_COMMIT)へ渡す修正。元12秒・旧ID/event・oldcallback無作用・将来IDを保持、最終edge6独立Green1.427秒。商品finish/prefix/state2/4の既存除外順も維持。client P2: unknown/running/noneがhost_deadlineを隠す表示を修正し対象CLI1独立Green。製品最終P0/P1/P2なし。CI選択helper最終差分は同レビュー内で追随する。

## CI選択と互換性

device46= native26（新fringe6/edge6＋関連14）+client17（新9＋関連8）+selector3。通常の成功商品/ほぼ毎拍・Perception閾値/HUD/goods・Nav73/motion/拒否・067成功経路・collector atomic/cancel/deadline/旧journal/UNKNOWN terminalを選び、無変更Runtime/world/全過去suiteは累積しない。local既存native14は実sealed sourceでGreen11.930秒、selector3Green.010秒、22source前後一致。新21はlocal重複実行せずMacで最終確認する。

client __file__は実driver内、bytesはHEAD Git blobと同一、fixture.nativeが同moduleを指すこととAPI15/cap13/v14を前後確認する。newgold_state/Decision.reasonはwireに出ず、Scene23864等layout/ABI1と旧client契約は不変。全Cは同じ22sealに入りRuntime/Swift/RPC変更なし。YAML/publisherも不変。

## 封印・配布待ち

LoopCtrlUITests/NG2Controller.c: `e39cba3cdb1e75f7b09d7654a0561445b3603a2aedf54615376a610902aefb77`。
LoopCtrlUITests/NG2Core.h: `5ffd94fb7cf20bcf2e846942c7c36ef0c4a536cb7b5129d058f30c117319f1b0`。
LoopCtrlUITests/NG2Navigation.c: `71e00d050eaec6c9e3e60409fba649c30d371501c600f7bf8aa5def668e0326c`。
LoopCtrlUITests/NG2Perception.c: `e3ba569f13026a3325df33628d6c71e22c107a6ce80492e497866e08f37105b0`。

manifest SHA `fc8b5135675a8af009258b4db62d368a7e4e1dcd6f4e31a4e30e16930dc8c9a4`、client SHA `a953a4548cbf5d8582f64b79aa94e9c4af0c218f968e8eea7e2296a52cb783d9`。native4差分/他18・R12原40/G1保持、固定upstream6e25へG1+G2適用済み。Mac/実IPA/実compiler/全Mach-O/全sourceは完了後追記する。TEST068実機は未実施。[配布と実機依頼](../status.md)に従う。


## 最終Mac106・実配布物

code `fe395d7b0c202715b253541c1b5f468091a302d9`、[Mac106](https://github.com/shuhei0720/necrogold-automation/actions/runs/42794069145) device成功。新IPA/build106（0.3.4/top.ebato.loopctrl）SHA `42448a2d8de1c8c61b13af8f5e48874b6f553a0d2980456700e5c110d27d671a`、外ZIP SHA `a64c12b6240b65beb2b5bda292f4c93b307d4363e9bade7fc437b3d7a5d510e4`。

host46の全実行ID/生ログ/command/0fail/error/skip/xfail・選択/省略理由、ABI実query、22seal前後が実IPA sourceと一致。clientの実driver path/HEAD blob・SHA `a953a4548cbf5d8582f64b79aa94e9c4af0c218f968e8eea7e2296a52cb783d9`/fixture module/API15cap13v14を前後照合。baseline0b8からnative4だけ変更、他18/R12原40/G1不変。実4C/5Swift/6RSP/PBX/raw compiler引数、Perception/Nav strictO2・Controller/BeatO0・SwiftOnone/HOST macroなしを照合。全9Mach-Oで従来104+068の計105marker非混入。Runtime/world全体は不変で未実施。

build-source全510tracked bytes/path/CRC一致、7,391,824bytes/SHA `8f652fcdb292a26a8382f83803e57b78492bfadeb4d7608c0fcccd4a6d20f56a`。最終sourceとの差分を文書3件だけに限定し、固定Releaseのsource.zip/SHA256SUMSへ保存。公開後は匿名GET/SHAで両asset確認。raw/画像/log/receiptはGit外。新しい068で下端候補1歩→商品到達・通常成功経路・回収時間/表示を実機評価し、未収録の先を合成結果で成功へ置換しない。[手順](../status.md)の新IPA更新/再起動/Start Serverから開始し、runtime/test-068全ZIPを必ず依頼する。
