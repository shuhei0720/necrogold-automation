# TEST084: 通路候補の見逃しと商品到達後の画面認識

2026-11-12（クライアント日本時間）。基準 `87cd98b6046154b8a6eb8da39ada31b31afb595f`、TEST083/build139。実機主軸・品質維持・時間上限なし。原因に関係する単体/関連回帰とIPA同一性へ絞り、同じ独立担当1名が差分と実物を確認する。

## 受領と原因

実順は1a4bc9f8/e33b6505/da1051fd/d6528e8d。4ZIP/80原PNG・18,933,275画像Bを全hash/CRC/現schema/client_load/manifest/prefix/cursor/実公開gateへ照合、全terminal/drained/回収完了・host error0。商品全体の人目可視4/4と、自動GOODS完了・PAUSE3/4を分ける。見送り判断9/9保持、実4の初期16/45だけnative bounded ring行は欠損でexport画像/metadataは正常。欠損の時刻/画素を補完しない。

A: 実4原16/45の上左口(-2,-3)は下325pxが現に床（median21/14/14と30/19/16・非黒296/307）、上300px全黒。full中央値4/2/1・7/2/3が元black入口に入りUNKNOWNとなり、DIRT限定の旧082partial proofへ到達しない。両脇壁は観測済み、outsideはUNKNOWNで元mask0。

B: 実1原75の左口(-3,-1)と外(-4,-1)はFLOOR、上脇DIRT・下脇UNKNOWN、同初期壁列には壁3cell。floor-mouthの両脇壁条件でmask0だが、より弱いunknown-mouthには外床＋片脇壁＋壁列3という既分岐がある。未知脇を壁に推定せず、この非対称だけを補う。75は初FLOORから356.380ms後で早切りの根拠なし。16/45の初FLOOR行欠損から200ms経過を推定しない。

C: 実4最後MOVE18 UP/source275は元窓内begin/ACK済み。goods0/paused0/screen17/attempts0/observed0でPAUSE票そのものがない。後続原379はfooter/zone1/floor1/death除外・rawbeatが成立するがpause iconだけ不成立。全HUDが消えたという作者の一時視認は、左右HUD cropが275/379で全bytes一致する実数確認により撤回した。商人重畳でiconだけが変わる。原379はr5@55で306/388=.788660、r4@55は左barの実9px断片を復元して315/388=.811856。full36×36/元IoU.8を満たしgap埋め/padding切り出しなし。元066のNEG11例はr4新採用0。

最初のACK後UNKNOWN285の原画はなく、末尾379の値を285へ代用しない。最初stable prefix18の285はACK+34.159ms・元earliest後/visualD内だが、native終了は285.end+約4.005秒。原379で同種の画面認識欠落を確認したことと、最初の拒否画素を確定したことを分ける。

## A: 低い全体中央値でも観測したpartial床を確認

- 元UNKNOWNかつ元black入口(R<6又はG<3)、full R/G/B各≤12と元full.spread成立だけへ別proofを追加。旧DIRT部分床補助/元palette/gate/woodは変更しない。
- 固定上12行300pxの≥95%黒、下13行325pxの≥90%非黒・medianR16..52・元floor palette/textureを全AND。黒と非黒の定義・floor/textureは旧082を維持。full625pxの元HUD/画像範囲とalpha検査を保つ。黒だけ/色壁/片帯/texture無しを床にしない。
- Git外AB prototypeは257原画（081=97/082=80/083=80）のUNKNOWN→FLOOR95cell/67画像だけを追加。95を原画で床と視認、保護/既GOLD/STONE/DOOR/ITEM上書き0、全非tile bytes不変。実増分full値は最大R8/G4/B3で追加低域条件を満たす。これは校正で未知評価ではない。
- 公開RGBAで旧UNKNOWN/bit0対必要FLOOR/候補bit0のassertion Red→最小Green。full各12/13と元入口、上285/284・下293/292、floor色/texture/R16、黒salt・既材質/gate/wood/ITEM/保護・HUD/alphaを境界/拒否へ対応する。

## B: 観測床が既にある片脇の口

- 元FLOOR口の旧両脇壁分岐は保つ。追加はmouthFLOOR＋outsideFLOOR＋正確に一方DIRT/STONE壁かつ他方UNKNOWN＋同初期壁列DIRT/STONE≥3だけ。
- 既固定上/左の10口、passage_scene、inboardへの非保護FLOOR経路と口/外のpassage_clearを維持。UNKNOWNを壁や金に変えない。既UNKNOWN口分岐・右/下除外・world原点/初期時だけのdetector使用・有限探索/旧restart条件を保つ。
- 公開手続Sceneで原75形bit6のRed→最小Green。上下左の正例/壁側反転、外UNKNOWN/両脇UNKNOWN/他脇FLOOR・木扉・壁列2/保護/到達不能・gold/goods/不正状態を拒否し、選ばれる次入力は既観測FLOORだけであることを公開choose_passageで確認。

AB prototypeの全257候補mask変化は指定3のみ（16/45はAでbit0、75はBでbit6）、既bit消失0・他254画像と初期見送り43source中40のmaskは不変。将来の金出現や到達を推定しない。

## C: 元icon証拠面を保つ9px断片

- 元raw二cutoff55/85、元13px/11px openingを同じ順序で保ち、その後9px opening（radius4）だけを追加。radius3は追加しない。
- 同じ36×36全ROI/元referenceとIoU≥.8・neutral条件を維持。gapを埋めず、paddingを切らず、商品やfooterだけをpause iconの代用にしない。既continue優先/zone1/floor1/footer/非death・RGBA/alpha検査も保つ。
- 公開RGBAの元raw/r6/r5不成立を先に確認した9px断片正例で意味Red→最小Green。元NEG11/単bar・色・移動/低IoU・cutoff/8対9断片・paddingノイズ/メニュー・death・他floor/alpha等を選択する。
- 元379の新FLOOR/既merchandise VISIBLEを確認し、公開Controllerの同prefix ACK待ちへ認識結果を渡してgoods latch→PAUSE予約/ACK→PAUSE画像確認・追加入力なしを結合する。Controller/Runtimeの入力権限、UNKNOWN無再送、フロー未送信/不明送信/ACK区別、元期限/予算を変更しない。

## 所有・検証・返却

A/Bはcandidate担当、Cはcontroller担当。Perceptionの材質helper/呼出と上部icon loopを別地域として限定applyし、全ファイル置換をしない。repo製品適用は同独立担当の計画確認と各公開assertion Red後に行う。旧意味試験をローカルで形式再実行せず、新作者試験と関連exact名をdeliveryへ渡す。

Runtime/core4/API16/cap15/client16・R12/G1は維持予定。rootは最終C4/257原画と適格保持ACK組の旧known回帰を照合し、元UNKNOWN画面からのFLOOR精密化を普通の非tile不変と混同しない。新sourceをfresh pinned Git checkoutのG1からseal/apply、独立差分GO→同code限定CI/実IPA→5実物verifier各1回→固定Release IPA/全source→匿名全GET/SHA/CRC照合へ進む。無変更Runtimeの全故障/worldや新Mac Redを加えず、既Red133と今回のMac Greenは区別する。

## D: 最初の非FLOOR拒否の比較画像

原285欠落で最初の拒否画素を確定できないため、今回の拒否に直接関係するC診断だけを追加する。入力回復やPAUSE救済ではない。既STATE validation4/replan_allowed0を使い、MOTION評価済を装わない。event.observed/motion/dx/dy/outcome、MotionWait評価回数/ID、MotionReferenceのunassessed0、停止/商品/入力credit、全ticket/期限/予算は変更しない。

- 元observerが有効なScene/current stable ACK prefixを受理した後、既入力state3・同ACK MOVEだけ。goods/finish要求なし・pending/replan0、event/current/waitのcommand/source IDとfullcommand bytesが一致、begin/end実在・outcome2、before FLOOR/current non-FLOORを要求する。
- 原beforeは同state3中に代入される経路がない既制御構造で不変を保証し、別authorityかもしれないmotion_reference_sceneを元anchorの代わりにmemcmpしない。新Scene copy/slot/期限を作らない。
- 観測IDはsourceより後、取得開始≥ACK end/source開始、end>start、actual commit≥endかつ元visualD以下（等号可）。真のscene_change maskが非0のときだけ、既record_changeのSTATE4でsource/観測を別診断行へ残す。ng2_motionを呼ばず、eventやMotionWaitへ観測済IDを代入しない。
- 既非FLOOR経路がstate3を撤回した後は再記録しない。既first1/latest2の上限とwire schemaを保つ。既Runtimeは画像追加後に比較source/observedをpriorityへ組むため、その経路をそのまま使う。全20枚/10MiB・availability/oversize規則を増やさず、first285が必ず保存されたと実測前に主張しない。

公開3methodsで、元SCREEN17/input0/paused0とevent/票/credit/未評価MotionWait/Referenceを先にassertした意味Red（期待STATE比較1対旧0）→最小Green。未送信/ISSUED/UNKNOWN synth/UI action/不正prefix・時計/期限超過/商品優先を拒否し、visualD等号/＋1ns・後続観測の重複なしを確認する。既report/SceneChange/SceneDetailとMotionReference-event validatorに通す。旧Runtime比較優先と保存試験の再利用を根拠付きで選び、新Runtime branchや新Mac Redを足さない。同じ独立担当がこの追記を確認するまで製品へ適用しない。

新実機の候補発見/商品可視/PAUSE成立・恒久毎拍/人超え・対象識別/通知/対象なし循環を先取りしない。通常1-1ポーズからrestart→候補→商店→全商品確認/PAUSEの具体的な複数回実機テストと、全run別ZIP返却を必ず依頼する。
