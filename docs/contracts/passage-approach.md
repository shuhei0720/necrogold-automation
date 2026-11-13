# TEST072の限定追加と通路接近

2026-11-10（日本時間）。[要件](../requirements/necrogold.md#2026-11-10-金壁不可視の側方通路へ接近)・[計画](../plans/test072-approach.md)が出典。本書は[native契約](native-control.md)§4/5/7/8/9の適用条件への限定追加。元16入力/12restart/45秒walk/180秒session、owner/prefix/取消/期限/商品保持/UNKNOWN無再送/全ABI/wireを維持する。

## 1. 保護と新観測

保護されたorigin/実nextは常に拒否。近傍のprotectedは、両画像で同じ不通行GOLDにのみ重なる場合、歩ける商品床と区別する。Navもorigin近傍のGOLD重複を危険床にせず、pathsは保護床へ進まずGOLDは不通行。全protected集合の比較を省かず、UNKNOWN/FLOOR/DIRT/DOOR/ITEMの保護は除外しない。

未入店・lead/実MOVED確認済みのreason8/FLOOR・両GOODS_UNKNOWNは、旧quietの3×3局所不変/全金・全保護/同full5/strictBLOCKED/元ID・全clockを満たす遠方palette揺れだけ同IDを保持できる。SAME回数や元期限を更新せず、ルート不変の余分な空拍を避ける。SAME/FRESHの旧chain2/run8と凍結ticketは不変。別modeの観測再判断は、確実未送信state1/イベントbegin0/outcome0・実MOVEDとlead確認後・旧/最新の同full5/金/全保護・同goods UNKNOWN又PARTIAL・origin/nextFLOOR・旧→最新strict BLOCKED zeroの場合だけ。変化はUNKNOWN/FLOOR/DIRT間のみ、GOLD/STONE/DOOR/ITEMの変更と、全protectedセルの材質変更は拒否。

旧票を永久not_sentへ撤回してepoch/slot/referenceを無効化し、最新Sceneをanchorとする。後続の独立非交差current-prefix画像で静止/full5/金/全保護/同goods/次床を証明するまで新票なし。新ID/将来拍prep≥50ms/model sample ID≥最新proof必須。有効HUDを再利用できるが元verified+12秒/旧command_sync/walk/sessionのminを固定する。前回verified時刻ごと1回/session8回、既存closed/terrain各一回は別管理。未送信の開通/歩数credit、送信UNKNOWN救済、旧ID/期限/epoch復活はない。

## 2. 開扉専用の画像証拠

通常motion/MOVED/旧mask/既存閾値は不変。primary UNKNOWNにだけ、原intensityでzero最良・score≤.45/gap≥.08/全73候補と唯一の金bracket、同方向DOOR→FLOOR、旧bracket保持、両originFLOOR、origin/next保護なしを要求する追加DOOR_OPENED証明を設ける。商品はUNKNOWN→PARTIALの新露出を許すがVISIBLEは保持が先。

この補助だけexpanded mask下端79→85、detail閾値6の証拠面を使い、総支持300以上・一致95%以上・全73候補との15pp差を維持する。旧3領域を流用したと偽らず、disjoint上下band y<65/y≥65で各100支持を要求。UIだけ/単帯/元金bracket消失/非zero/閾値不足は拒否する。開扉だけで移動・lead校正creditを作らず、同一ACK/元visualD/最大8評価を維持する。

## 3. 通路の局所候補

Sceneに疑似GOLDや新enumを作らず、明瞭なFLOOR/GOLD_CLEAR/GOODS_UNKNOWNだけで開始する。初期world原点の上(k,-3)/左(-3,k)、k=-2..2の計10口を固定bitへ対応させる。FLOORの口＋両脇観測DIRT/STONE壁は、外側UNKNOWNでも内側床へ近づける候補。口UNKNOWNなら外側観測FLOORと少なくとも一方の脇壁、初期の同壁列(-3..3)にDIRT/STONE3セル以上の支持を要求。黒だけ/普通木扉だけ/赤線/minimap/将来画像は根拠でない。右/下の一般出口を無差別に探索しない。

候補mouth/world外側目標を固定し、複数候補のpending/到達済/未判定を分ける。pure Navは観測FLOORのみの経路と実nextFLOORを返す（private decision reason10）。外側目標が未観測なら、目標へ近づく既知床vantageだけを選ぶ。金根拠なしのDIRT/DOOR/UNKNOWN進入は禁止。全候補0は従来の開幕見送り、候補1/複数は既知経路長と決定的順で選ぶ。

## 4. 探索の入力権限と終了

Controller private modeとmode-aware chooser/safe_stepで初歩校正と通常拍へ接続する。初歩/retuneは観測床・現candidate/world口・同prefix・旧clock/leadを確認し、実MOVEDだけでleadを校正する。通常shop safe_floorと元画像fallback資格は拡張しない。探索用の旧referenceをshopへ持ち込まない。

各安定観測/送信直前でnext床/保護/候補/モデルを再検査。新金壁が現れたら未送信探索票を撤回して通常plannerの新判断へ。ACK待ちの間は同じ送信を解決するまで追加入力しない。商品VISIBLEは保持、PARTIALで金根拠なしは保持停止、金ありは通常の全商品可視化へ進む。探索開始/校正/未送信/ACK待ち/最終CLEARの全段で商品/取消/owner/前面/UNKNOWN送信を優先する。

外側目標へ実到達し、その後の独立stable current-prefix GOLD_CLEAR/GOODS_UNKNOWNを確認して初めてその候補を局所見送りとする。世界全体の店なしではない。UNKNOWNで到達不能なら既知内側vantageから最大2拍、元予算内で新露出を待つ。なお不能なら未判定、他候補を確認しても未判定が残ればNO_PATH保持停止。全候補到達後の独立CLEARの場合だけ既存PAUSE/RESTARTへ進む。PAUSE/RESTART予約とACK待ちでも商品/保護/新金候補を再検査し、候補が分かった後の見送りを禁止する。未送信の見送り票は撤回できるが、送信UNKNOWNを既知へ変換したりRESTARTを再送したりしない。GOLD_UNKNOWN/商品/保護/期限切れを不在にせず、予算を伸ばさない。

TEST080の[閉口局所見送り](../plans/test080-sparse-gate-closed-mouth.md)は、外側への到達確認とは別の限定追加。最後のACK実MOVEDで固定mouth内側隣接へ到達し、BLOCKED待機中input0・旧anchorと後続独立stable/current-prefixのstrict BLOCKED・origin床・口同DIRT/STONE・両脇壁・全GOLD/商品/ITEM/保護なし・両観測に床経路なしを元2拍/旧horizon内で確認した候補だけをprivate closedへ退役する。外側UNKNOWNや変化を陰性にせず、inspected(実到達)・unresolved(未判定)と混ぜない。他候補へ進み、未判定が残れば従来NO_PATH、全候補が到達確認済み又は閉口確認済みで初めて既PAUSE/RESTARTへ戻る。新金/商品/保護/取消/owner/prefix/期限/UNKNOWN送信は従来優先、閉口を世界全体の店なしや掘削権限にしない。closedもstart/level切替/初期候補更新で撤回し、stationary snapshot/recheckは対称に保持する。

## 5. levelの切替

PAUSE直前の最新安定current-prefix FLOORをrestart fingerprint基準に凍結する。探索開始画像を基準にしない。実RESTART ACK後・取得開始≥ACK・独立stable current-prefix FLOORがこの基準から変わったと確認して初めてlevelを切り替える。旧終点world/UNKNOWN/状態4/取消/owner失効から切り替えない。

level切替時に座標/visits/入口、lead/初歩slot/visual期限、model、replan/continuous、gate/terrain/観測refreshのactive/pending/proof、motion reference/epoch、探索候補を撤回する。新levelの総inputs/movesのbaseを保存し、初歩・retune・replan・edge・initial visual等のlevel内0を総数から区別する。総physical inputs/moves/events/ID/session/取消、最初のfirst_move_ns/last_ordinalは不変。gate/terrain/stationary各used、観測refresh8回、continuous8回、初歩replan2回等のsession上限と既存edge単一権限をresetしない。総16入力・12restart上限は巻き戻さない。walk_started_nsと最初のwalk+45秒の凍結期限はrestart後も保持する。level初期同期用の起点は別に持ち、12秒syncも旧walk/sessionのminで制限する。旧ID/callbackは新levelを変更できない。


## 6. TEST074の描画確認と限定動作証拠

[074計画](../plans/test074-visible-evidence.md)は暗い最初のFLOORを確定した陰性/探索権限にしないための追加。RESUME/RESTARTのACK・newlevel fingerprint証明を消費した後、最初のFLOOR取得起点から200ms以上に開始した独立stable current-prefix新観測で初期分類を確認する。単なる時計経過は権限でなく、起点/同期/元総予算を再延期しない。初期待機中の同原点level0・未送信・商品/保護なしだけ、正常FLOORのGOLD_UNKNOWN/不整合CANDIDATEから旧票/slot/初期proofを撤回し元4秒/同期12秒内の新観測待ちへ。移動後/送信後の旧停止を広げない。新金/商品は見送りより優先する。初歩前・同原点・level入力/移動0で候補が後続2独立画像の同mask/口/脇で確かなSTONE/DIRTへ消失した場合、旧未送信票/slotを撤回して最新候補へ更新する。単独UNKNOWNで候補を廃棄せず、移動後camera原点で口を検出し直さない。

動作のprimary判定と元閾値を保持し、primary UNKNOWNだけへ2つの独立補助を追加する。開扉は唯一gold bracket/旧GOLD・DOOR→FLOOR・raw最良zero/差≥.08・非保護origin/next・商品UNKNOWN→PARTIALまでで、既知同材質（新露出/DOOR/ITEM/保護/player除外）の中心半差contrast6符号を使う。支持300/95%/全73への15pp差/独立上下帯各100を要し、zero-onlyで移動creditにしない。金なしMOVEDはCLEAR/金0/商品0/全保護0・旧origin/入力先と最新originの観測床・同方向raw厳密unit/差≥.08・全旧STONE2+と非共線DIRTによる一意translation、既存expanded-detailの同強証明を要する。最新の新STONEは証拠に使わず追加可とし、旧集合の複数translation成立は拒否する。最新画像でさらに先がUNKNOWN/壁/扉でも過去のMOVED証拠とは分離し、次の入力権限は既存Nav/safe_stepが確認する。詳しい証拠面と拒否境界は074計画/試験を正本とする。UNKNOWN無再送・元visualD/最大8評価・ACKと実変位の区別は維持。

TEST075は[計画](../plans/test075-motion-rpc.md)の追加証拠だけをUNKNOWNへ適用する。金/局所不変の強zeroをBLOCKEDへ、金なしで完全旧Lの一意unit対応・左右raw位相・全21依存既知の強blur面（固定camera原点上下）をMOVEDへ使う。旧primary/旧補助/閾値/元予算は維持し、UNKNOWN再送や未観測商品を陰性にする権限を加えない。

TEST076の[限定計画](../plans/test076-stationary-recovery.md)は未送信のreason8/固定通路reason10だけに追加する。UNKNOWNで旧票を撤回して入力を止め、固定元anchorへの後続strict BLOCKEDを親期限P/短期待機W内で確認するまで新票を出さない。CLEAR通路の確実未送信lateも全材質/全5field/保護/静止が同じ場合に限り旧票を廃棄して元予算内の新拍へ。元D・不明送信・姿勢/入力creditを変更せず、送信済UNKNOWNには適用しない。

TEST077の[限定計画](../plans/test077-shop-visibility.md)は、固定通路の無入力待機に限り、実origin/nextがFLOOR・全保護/フル5/world不変なら、他の近傍セルのUNKNOWN/FLOOR/DIRT/STONE間の見え方の差を許す。shop待機の近傍拒否やGOLD/DOOR/ITEM拒否、元anchor strict0/P/W/別ID条件は維持。開扉済み/実入口確認後のPARTIAL移動は、元と直前accepted GOLDを保持し、両3×3/保護外UNKNOWN/DIRTからの遠方GOLD増加だけを同票へ許す。strict0/全5field/保護/元票全期限を保持し、追加金の消失はmask0も含め一般refresh前に撤回する。

TEST078の[限定計画](../plans/test078-closed-gate-motion.md)はUNKNOWNにだけ閉金扉への厳密unit到達証明を追加する。両CANDIDATE/GOODS_UNKNOWN・全保護/ITEM0・旧origin/nextと最新origin床、旧2セル先の閉扉/同法線金bracket→最新1セル先、旧全金exact保持/unique9/raw全73の最良unit/high-intensity/gapを必須にする。新面は各frameで固定H→Vの最初の有効軸の3実依存だけを読み、全点mask/UI/knownと同材質/符号を候補非依存featureへ保存する。camera52の両frame51/52を除外し1画素1支持、300/95%/帯100/全73元15pp条件を維持。旧5依存/65帯/既known分類を変えず、閉扉への到達と開通/進入を分け、次の入力は通常Navへ返す。元期限/予算/不明再送禁止は維持。

TEST079の[限定計画](../plans/test079-gold-reveal-dirt.md)は旧判定後UNKNOWNだけへ、単一金から新閉扉/金bracketが露出したunitの別証明を追加する。両CANDIDATE/GOODS_UNKNOWN・全保護/ITEM0・旧origin/実nextと最新origin床、全73 rawの同方向厳密unit/score≤.45/gap≥.08、旧金1→最新金2/閉扉1・旧金対応・新門/反対金の旧projectionがUNKNOWN、旧金と保持旧STONE2点の非共線・全9translationで異なるanchor組も含め唯一を要求。078固定3依存面の300/95%/帯100/元15ppをそのまま併用し、旧partial全STONE条件/既knownを変えない。MOVEDだけを返し開通/入口creditは作らない。

079のquiet追加はlead確認済みcontinuous・未入店・確実未送信state1のreason6/DIRT/target=実nextだけ。両Sceneの2*direction閉DOOR/入力軸に垂直な両GOLD、全GOLD/保護集合と材質/ITEM・両3×3・full5不変、strict BLOCKEDを要し、保護外かつ両近傍外のUNKNOWN/FLOOR/DIRT/STONE差だけ許す。同ID/全ticket bytes/元before・clock/epoch/prefix/owner/取消/全凍結期限を保持し、新予約/移動/開通creditは増やさない。旧quiet他scopeは不変、started/UNKNOWN送信/期限超過/商品優先を広げない。


TEST080の[狭い閉金扉unit証明](../plans/test080-sparse-gate-closed-mouth.md)は、全旧Nav後UNKNOWNかつ元73phaseがすべて正INFの場合だけ追加。有限/NaN/負INFは対象外。両FLOOR/CANDIDATE/GOODS_UNKNOWN・全ITEM/保護0・旧origin/実nextと最新origin床、閉DOOR2ahead→adjacent/同法線・GOLDexact2/unique9・保持旧STONE2点と旧門中心の非共線を要する。新phaseは固定openingmaskの全実3×3依存が両frame既知同材質・非DOOR/ITEM/保護である点だけを元normalized intensity算術/支持300/mean6/contrast2.5/gain.65..1.55で全73採点し、元unit/score≤.45/gap≥.08を要求。固定65帯各100（両frame64/65中心除外）で独立2領域をphase側に課し、さらに078固定H→V3feature/camera52の総300/95%/全73元15ppを併用する。旧strong52帯100と全旧関数は変更せず、この新結合だけへ限定。unit以外や開通/入口credit、元期限/予算/未知入力再送は追加しない。


## TEST092の正の未局在金候補

[092計画](../plans/test092-startup-stationary-status.md)のFLOOR/CANDIDATE/peak≥135/商品UNKNOWN/GOLD0/原点FLOOR/全ITEM・保護0だけ、既観測mouthと床経路へ接近できる。独立2枚の同分類/mask/口脇支持が必要で、SceneをCLEARへ変えず地図外GOLDを作らない。入力は現在Sceneの既safe_step/完全Decision/静止/prefix/元期限で証明し、mouth/world原点を移動後に再検出しない。private positive意図は陰性restartを拒むだけで、actualGOLD/商品/finish/level切替で撤回。候補mask0やlocalgoalで金未局在なら未判定保持し、旧CLEAR通路の局所見送りとは分ける。UNKNOWN送信の再送/未知床/掘削/新enum・ABI・予算拡大はない。
