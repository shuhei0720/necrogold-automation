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

## 5. levelの切替

PAUSE直前の最新安定current-prefix FLOORをrestart fingerprint基準に凍結する。探索開始画像を基準にしない。実RESTART ACK後・取得開始≥ACK・独立stable current-prefix FLOORがこの基準から変わったと確認して初めてlevelを切り替える。旧終点world/UNKNOWN/状態4/取消/owner失効から切り替えない。

level切替時に座標/visits/入口、lead/初歩slot/visual期限、model、replan/continuous、gate/terrain/観測refreshのactive/pending/proof、motion reference/epoch、探索候補を撤回する。新levelの総inputs/movesのbaseを保存し、初歩・retune・replan・edge・initial visual等のlevel内0を総数から区別する。総physical inputs/moves/events/ID/session/取消、最初のfirst_move_ns/last_ordinalは不変。gate/terrain/stationary各used、観測refresh8回、continuous8回、初歩replan2回等のsession上限と既存edge単一権限をresetしない。総16入力・12restart上限は巻き戻さない。walk_started_nsと最初のwalk+45秒の凍結期限はrestart後も保持する。level初期同期用の起点は別に持ち、12秒syncも旧walk/sessionのminで制限する。旧ID/callbackは新levelを変更できない。
