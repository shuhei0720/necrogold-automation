# TEST097: 商品が見えるまでの継続と通路候補

2026-11-13（日本時間）。基準0f6953f、実装前の調査/設計中。[受領](../reviews/test097.md)・[要件](../requirements/necrogold.md)・[native契約](../contracts/native-control.md)。

## 1. 目的と背景

TEST096は実機4回とも受入未達。単体/CIの件数を到達率へ置き換えず、候補見逃し、移動確認、開扉後の部分表示からの商品可視までを修正する。全商品登録を増やさず、のろいのゆびわだけを判定し、完全な対象なしだけ次周回へ進む。

## 2. 根拠と過去対策

4 ZIP/85 PNGを全照合。実順はbc239→e503→4b8→6f62、添付3→4→2→1。実1の実UPをUNKNOWN8回、実2の空partialは保持、実3/4は期限内の判定後に部分観測の継続を拒否。096の新しい側方金1→2証明やPAUSE順序の不具合を全てへ当てはめない。FR079/081/096、FR094/095継続、FR084/086/094/095候補を照合する。

## 3. 修正範囲と設計

- 候補: 元UNKNOWNを床へ変換せず、上左の観測口と内側の床、外側の折れた口を有限の仮説として扱う。既存の観測FLOORだけの局所3歩vantageを使い、再観測ごとにchooserで接近する。全接近距離3歩の保証とはしない。壁の正支持・保護・見送りと世界の店なしの区別を維持。4枚別々の固定座標分岐にしない。
- 移動: 原178→196の保持Sceneで、既証明のどの十分条件が失敗するかを数値で確認する。既知のMOVED/BLOCKED/TWEEN/他方向・元ACK/prefix/一歩credit・UNKNOWN無再送を維持。閾値や回数/期限を下げて通さず、追加が必要なら独立した反例と根拠を先に示す。
- 継続: 原176→178/414→416の最新判断、全保護、材質差と静止証明を診断する。空の部分slotや見切れを対象なしへ変換せず、候補保持と安全な観測床の移動を区別する。一般UNKNOWNの無条件解除、元ticket復活、期限延長をしない。新たな観測継続権限が必要な場合は条件・拒否範囲を追記してから実装する。

### Navの具体的な限定条件（実装前）

候補Aは既bit0の上左口(-2,-3)と外(-2,-4)がUNKNOWN、外左壁(-3,-4)がDIRT/STONE、対岸の屋根(-1..2,-3)に壁2以上かつ反対側半分のx=1/2に壁1以上、左境界x=-3/y=-3..3に壁2以上を要求。内側と斜め2セルはUNKNOWN/FLOORに限定し、中央2×2のFLOORと既chooserの観測床vantageを必要とする。内側が既に床と見えていることを理由に見送らない。

候補Bは既bit5の左上口(-3,-2)FLOOR、直接外(-4,-2)UNKNOWN、斜め外(-4,-3)FLOOR、上flank(-3,-3)と内側屋根(-2,-3)/(-1,-3)の壁、下flank UNKNOWN、内側FLOORと既観測床vantageを必要とする。両方CLEAR・金/ITEMなし・全保護0。旧候補helper/chooserとUNKNOWN表現は不変。

候補Aの初版は新8methodで成功したが、関連の旧095が保持するsplit形状の転置拒否を破り、O0/strictO2の2条件で失敗した。近い屋根2セルだけを反対側の境界支持と誤って扱っていたため、屋根の反対側半分まで観測壁が続く正支持を追加する。旧assertは変更せず、新試験の屋根組合せに近い2セルだけの拒否を明示する。初版source/試験/失敗出力をGit外へ保存する。これは配布前の設計不足であり、実機の改善や未知配置の精度を証明する変更ではない。

実1の178→196はGOLD1→1、全旧STONE5・DIRT12を投影保持、raw unit .266/runner .649だが、旧下帯は支持不足・world/gradientの領域支持も不足。既096の金1→2の新側方入口条件には該当しない。旧段の最後がUNKNOWNの場合だけ、GOLD1→1の正支持・HUD外の全旧STONE2以上・非共線DIRT9・元9配置の一意unitと、raw≤.45/runner差.08以上・Sparseの同unit≤.45/.08/支持300/領域100・固定signed-axis95%/支持300/領域100/既15点leadをANDする。全73配置を検査し、最良とrunnerは有限。NaN/−INFは拒否、他の+INFは支持不足として票/架空marginへ使わない。元/投影ROIと原点/送信床/到着床、全商品/保護の拒否を維持する。独立した十分条件であり、失敗した旧world/gradientの閾値を下げない。

### Controllerの部分観測継続（実装前の限定条件）

実3の176→178は全5fieldのLEFT/reason5/target(-1,0)/FLOOR、全保護と厳密な0変位が一致する。DIRT→FLOORの4差のうち(-2,-1)だけが次セルの3×3に入り、095の遠方DIRT条件を拒否する。旧071の`quiet_gate_observation`には同じ「開扉後の金bracket背後の対角」条件が残っているが、新しい周回のPARTIAL処理はticket発行前に拒否するため旧処理へ届かない。旧対策の削除ではなく、新経路への接続不足として扱う。

`cycle_partial_relation`の材質関係だけを次の二つで拡張する。旧DIRT→FLOOR/UNKNOWNは従来の遠方範囲のまま残す。

- 開扉後の対角: 保存された完全Decisionがreason5・隣接FLOORの入口で、現在の最終ACKが同方向MOVEのDOOR_OPENED（実0変位）であることを必要とする。変更セルの方向内積が2、直交距離が1、1セル手前は両SceneでGOLD、変更セルは両Sceneで非保護の場合だけ、旧071と同じFLOOR↔DIRTを許す。原点・実際の次FLOOR・bracket・商品・保護は変更しない。開扉の送信成功だけ、別方向の開扉、過去の開扉履歴だけでは許可しない。
- 遠方材質: 実4の(-2,+4)STONE→DIRTだけを材質対として追加し、原点/次セルの両3×3外・両非保護を必要とする。STONE→UNKNOWN/FLOOR、近傍STONE差、GOLD/DOOR/ITEM差へ広げない。旧071の遠方材質の一部を新経路へ接続し、一般的な地図変更の許可にはしない。

両条件とも元sourceを固定したまま、両PARTIAL/FLOOR・実GOLD・同じ完全Decision・全保護一致・独立した厳密BLOCKED(dx=dy=0)を再検証する。新しいticketへ進む場合も既存の元continuation horizon、sync/walk/session、prefix/owner/取消、将来拍の準備条件を維持する。受領実3の拒否時点から元分類期限までの余裕は約12.011msだが、これを延長したり分類時刻へ遡及したりしない。期限切れ後の旧ID/元票復活、UNKNOWN入力の再送は0。

新Controller単体は実装前の意味Redとして、(1)開扉後の4方向/両側の対角、(2)遠方STONE→DIRT、(3)実際のACK/方向/金bracket/局所範囲の拒否、(4)許可外材質/保護、(5)完全Decision/厳密0変位、(6)元prefix/独立観測/取消/期限、(7)新しい票の不変窓と旧ID拒否を確認する。実2の空slotはこの材質関係だけでは許可しない。未収録の入店後画像や商品到達をこの単体で証明しない。

### 上端商品へ1歩だけ接近する観測権限（実装前）

実2の原167は商店の看板上部が画面外で、正常なUNKNOWN/INCOMPLETEでもrow/partialが各0・`partial_safe_no_positive=0`となる。空結果を対象なしや安全判定へ変更せず、明示した別のprivateな観測framing権限で既存OBSERVE_MOREの1入力へ接続する。Ring/判定出力・ABI・既非空partial経路は変えない。

採用条件は元期限内の正常な当該job/capture/prefixでstatusOK・outcomeUNKNOWN・coverageINCOMPLETE・row0/partial0・safe flag0・selected row/partial各-1。候補/完全表示/未証明restart/停止/未解決入力・現在の発行済み票は拒否する。元SceneはFLOOR/PARTIAL/GOLD_CANDIDATEで実GOLDを持ち、最終の実ACKは同level/current-prefixのUP DOOR_OPENED・変位0、完全な`cycle_partial_choice`がUP/reason5/target(0,-1)/FLOORであることを必要とする。原点/次セルと既cross近傍に商品/保護を許可しない。

上端の正のITEM/保護を必要とし、全ITEMが保護済みでy=-5/-4だけ、少なくとも1個はy=-5、全保護はy=-5..-3だけとする。固定座標例の一致ではなく、その全ITEMと保護から次の有限包絡をO(230×5)で再計算する。セル中心Cx=448+36x/Cy=207+36yに対しITEM由来の量子化±18pxを含むicon包絡は[Cx-43,Cy-42,Cx+43,Cy+56)、priceは[Cx-29,Cy+3,Cx+30,Cy+59)、partial対象名は[Cx-78,Cy-86,Cx+78,Cy+16)、保護セルは[Cx-18,Cy-18,Cx+18,Cy+18)。Perceptionは配列外ITEMからも端の保護を作るため、各保護セルの自分/4近傍を「その保護の由来となり得るITEM中心」として配列外を切らずに同じ3包絡へ含める。仮説中心は包絡の上限だけで、SceneへITEMを追加したり入力の正支持へ使ったりしない。各ITEMの元探索範囲と全保護/その由来仮説の合併をE、画面をV、既固定HUDをHとし、T(x,y)=(x,y+36)についてT((E∩V)\H)⊆V\Hを必要とする。

整数の十分条件は包絡のminX≥143、maxX≤663、maxY>0、maxY+36≤315。これで左/右HUDと下部HUDを除外し、残るpause HUD[429,0,465,45)の逆像の画面内部分[429,0,465,9)は元pause HUD内となり、新しく隠れる既観測画素がない。元画面外や元HUD内の画素は依然未観測であり、包絡全体が観測済み/商品が全て見えるという主張にはしない。原167の包絡はITEM/保護セルだけなら[262,-59,562,122)、配列外の由来仮説を全て含む強化版で[190,-95,634,194)、既画面内の射影[190,36,634,230)となり、強化版もこの十分条件を満たす。これはSceneと既固定ROIの静的な保持条件であり、商品名や未来画像を判定した結果ではない。

この採用だけでは入力しない。元source/完全Decision/全ITEM/全保護とcontinuation horizonを固定し、release後に取得を開始した別IDの独立した安定prefix画像で、ITEM/保護の同一性、完全判断、既材質関係、厳密BLOCKED(0,0)と同じ包絡を再検証してから、将来の拍・新IDへ進む。既分類workerの100/150ms期限と入力用continuation horizonを混同せず、後者は元source/位相3秒・sync/walk/session/開通親の最小のまま。自分自身の原167比較や古い前取得画像を独立証拠にしない。

privateなframing印は1回のMOVE beginで消費し、既partial credit同様にACK中のprefixだけ引き継ぐ。次の独立したPARTIAL/FULL観測は新しい通常jobへ送り、同じ空結果で2入力目を許可しない。候補/positive/完全表示/故障は保持を優先する。framingから対象なし・リスタート・full_seen・completed_shopsを作らず、入力ACKから変位creditを作らない。cancel/終了/失敗/level切替でも印を撤回する。実装前の新8単体で正常1回と、実ACK/結果種別/候補・故障/上端包絡/完全route/新HUD遮蔽/独立観測/1回消費・全期限の拒否を確認する。原167後の独立したFLOORは未保存なので、実機の商品到達は未確認とする。

配布前の境界確認で、OBSERVE_MOREの待機中に全商品が見えた場合も旧部分結果のままKERNEL保持する不足を検出した。新framing印があるOBSERVE_MORE・入力0・候補保持/未証明restartなしだけ、元captureより新ID・取得開始≥release・元cycle prefixで届いたFLOORの完全表示を通常の`cycle_latch`/`cycle_bind`へ渡す。呼出元のvalid Scene・安定current ACK prefix検査を保ち、実際の新しいFULL観測から新jobと分類100/150msを作る。非FLOORと完全表示の組合せは保持の根拠にできても、新しい分類sourceへ結合しない。旧MOVEや入力horizonを復活/延長せず、framing印を撤回し、古いworker/結果callbackは状態不変で拒否する。SEARCHに移った後や未送信ticket発行後のFULLは既存のglobal latchが票を退役するため、その処理を変えない。新9件目はこの両段階と非FLOOR拒否を確認する意味Red→Greenとし、既8件のassertを維持する。

## 4. テスト影響範囲

Navの該当候補/移動単体、Controllerの部分観測/開扉後の入力資格と旧関連だけを選ぶ。RuntimeやRingの境界を変更した場合だけ、その境界の有限Mac結合を選ぶ。全world/全故障集合を通常修正へ追加しない。旧Runtimeの同一bytes・前回結果の再利用は過去結果と明示する。

## 5. 新規試験と期待値

各機能で実装前assertion Red→最小Green。実際の観測口/床/時刻を期待値へ結びつけ、UNKNOWN先への移動、候補廃棄、商品未観測の陰性、非unit/他方向/競合・保護・取消・prefix/世代/期限の拒否を保存する。原画像は各一度の校正、保持Sceneは不変。録画外の未来到達を合成成功で埋めない。

## 6. 実装順とレビュー

受領/原因診断→具体的な条件と短い設計を確定→独立差分レビュー→該当Red/最小修正/関連Green→native封印/必要なIPAビルド。通常は独立担当1回を基本とし、新規の入力権限だけ実装前に重点確認する。修正確認は指摘箇所へ限定する。

## 7. 保存と配布前確認

修正表へ事象/原因/対策/改善確認方法/再発を記録。canonical15 source/ELF・旧bank・G1/R12全40を保護。実compiler/36seal・9Mach-O・全source/IPA同一性と固定Releaseの実ダウンロードを確認する。生ZIP/画像/log/SceneはGit外。

## 8. 次の実機と未確認

通常1-1ポーズから候補探索→商店→3商品が見える位置→のろいのゆびわ判定→対象なしなら次周回を依頼する。終了通知後iSHで全保存/ZIP照合終了を待ち、表示run ZIP全体を返してもらう。実機での改善、毎拍/人超え速度、未知精度は未確認。今回の4回は成功へ数えない。
