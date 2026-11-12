# 修正記録表

2026-11-13（日本時間）からの再発防止用台帳。対策の履歴と確認できた範囲を残す。**この表への記載、単体試験の合格、保存済み画像の校正、特定の実機回の成功は、問題の恒久的な解消や全配置での改善完了を意味しない。** 過去に対策を入れた問題も、新しいエラーの原因候補から除外しない。

- 修正日は資料で確認できたコード変更・対策導入の日付で、改善完了日ではない。日付を特定できない記録は「未特定」とする。
- 改善確認方法には単体、保存画像の校正、静的照合、特定実機回の実績を区別して記す。実機での再現や改善確認を台帳への記録の前提にせず、未確認は未確認のまま残す。
- 再発数は、対策変更後に同じ原因が再観測された回数。改善が実機で確認できていたことを前提にしない。継続・真の回帰・原因未確定の再発疑いを注記して区別する。同じ「停止」「UNKNOWN」だけで同原因と決めない。
- 過去は統一集計されていないため、根拠が揃わない数値は「未集計」とする。0も改善完了の根拠にはしない。回数を更新するときは対象版と根拠への参照を残す。
- 修正前に事象・原因・関連IDを検索し、リンク先の適用条件と未確認も読む。既対策を維持できる関連試験を選び、同原因なら既行の再発数と対策を追記する。別原因なら関連IDを付けて新行にする。

後方整理の範囲はTEST061〜089の主要な停止、認識、保存、判定。全ての変更を網羅したとはしない。TEST034〜060は確認できた主要記録を追加する。新規の修正は以降この形式で継続する。

## 起動・同期・入力予約・再観測

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-061-SYNC | 2026-11-10 | 初歩前BEAT停止・0歩 | 公開前の拍追跡失効を初歩の停止へ直結 | 確実未送信の初歩だけ元12秒内でslot・modelを撤回し再取得 | [計画/限界](plans/test061-verified-progress.md)、[検証](reviews/test061.md)。公開C/合成時計で境界確認。次の061実機は0歩を含み、全体改善は未確認 | 未集計 |
| FR-061-VISUAL | 2026-11-10 | ACK後UNKNOWN/次拍期限で停止 | 入力窓と画像確認の期限が混在し、真の確認後の次位相を選べない | schedule/visual期限を分離し、真の移動確認後だけ新しい位相選択へ | [検証](reviews/test061.md)。入力成功と変位を区別した単体/Runtime補助。061実機の別UNKNOWN停止を成功へ読み替えない | 未集計 |
| FR-062-QUIET | 2026-11-10 | 初歩直前の遠方揺れで再予約枠を使い切る | 判断が変わらないDIRT/UNKNOWN差でも初歩票を撤回 | full5判断・金・保護・近傍・厳密静止が不変な揺れだけ同ID保持 | [計画](plans/test062-device-cycle.md)、[単体](../tests/test_native_device061.py)。元期限/actual commit境界を確認。適用外の揺れは未解決として残す | 未集計 |
| FR-062-SAMPLING | 2026-11-10 | visual期限が残るのにACK後3評価を使い切る | 確認が早い画像へ集中 | UNKNOWN確認を元周期の¼/1周期へ分散 | [検証](reviews/test062.md)。公開Cの評価時刻と元visual期限を確認。後続画像の実MOVEDを捏造しない | 未集計 |
| FR-063-UNSENT | 2026-11-10 | state1の未送信MOVEが純期限超過でCAPTURE停止 | 10ms窓を越えた確実未送信に回復経路がない | 同world/判断/厳密静止で旧IDを退役し、新しい将来拍へ戻す | [計画](plans/test063-unsent-deadline.md)、[単体](../tests/test_native_unsent_continuous.py)。送信済/UNKNOWN拒否と旧期限・旧callback不活性を確認 | 未集計 |
| FR-064-INITIAL | 2026-11-10 | 再fit後も初歩前SCREEN停止 | 旧quiet50msの外側にある無害な遠方差を拒否 | 公開済み初歩のquietを100ms準備窓へ揃える | [検証](reviews/test064.md)、[単体](../tests/test_native_device064.py)。actual commit/旧期限・権限の境界確認。実機の0歩一般解消とはしない | 未集計 |
| FR-064-ENTRY | 2026-11-10 | 開扉後、下商品へ近づく前に未送信停止 | PARTIALを含む同入口床の再検証をsafe_floor条件が拒否 | 実移動/lead確認済み・同入口床1歩に限定し遠方palette差を保持 | [計画](plans/test064-stationary-step.md)、[検証](reviews/test064.md)。同full5/金/保護/局所/厳密静止を単体確認。下商品未観測は完了にしない | 未集計 |
| FR-065-PENDING | 2026-11-10 | 2歩後にstate0/pendingの純期限超過でLATE停止 | FR-063-UNSENTはstate1だけで、撤回済みSAME/FRESH待機を対象外 | 確実未送信pendingだけ旧proof予算内の新将来拍へ戻す | [計画](plans/test065-pending-unsent.md)、[単体](../tests/test_native_device065.py)。元event/期限/旧ID不活性と入力credit不変を確認。stateの違いを同原因再発へ即加算しない | 未集計 |
| FR-066-ACTION | 2026-11-10 | 入店後PARTIAL/reason8、または閉扉reason5で停止 | quietが入口reason5の次FLOORだけに限定 | 実進入後PARTIALの同床、または同DOORに限り遠方材質差を保持 | [計画](plans/test066-shop-action.md)、[単体](../tests/test_native_shop066.py)。元ID/全期限/保護/同判断を確認。商品未観測は保持 | 未集計 |
| FR-067-GATE | 2026-11-10 | 既知の床入口でBLOCKED後に終了 | 安全な静止入口を別IDで再評価する手段がない | 1run1回の独立静止・fresh HUD・新将来拍で入口を再取得 | [検証](reviews/test067.md)。旧event/歩数と元12/45/180秒、再送禁止を公開Cで確認。物理的未移動の原因が不明な回は不明のまま | 未集計 |
| FR-069-GATE | 2026-11-10 | 開扉前の未送信票を静止UNKNOWNで拒否 | 旧quietの静止証拠が不足する閉DOOR場面 | 旧IDを撤回後、独立静止pairとfresh HUDで1run1回の別ID再観測 | [計画](plans/test069-collection-gate.md)、[単体](../tests/test_native_gate069.py)。ACK/UNKNOWN再送と元期限延長を拒否。開扉・進入・商品を別確認 | 未集計 |
| FR-070-CADENCE | 2026-11-10 | 約2拍/3拍に一度の移動 | 最後の確認を1周期待つ評価配置と、前面/再検証の10ms窓超過 | 元visual期限内に最大8回の短間隔確認。準備証拠を保持し重い画像整理を入力後へ移す | [計画](plans/test070-cadence-lighting.md)、[単体](../tests/test_native_cadence070.py)、限定Runtime。元最終機会/全期限維持。特定実機の毎拍区間は全経路合格ではない | 未集計 |
| FR-071-SHIELD | 2026-11-10 | 開扉後2商品だけ見えて入店前停止 | 金壁背後の斜め2セルFLOOR/DIRT差で同入口票を撤回 | 開扉ACK後・未入店・両PARTIALの同入口床に限りshielded差を保持 | [検証](reviews/test071.md)、[単体](../tests/test_native_shop071.py)。同full5/全保護/厳密静止/全旧時刻を確認。2商品を全体確認にしない | 未集計 |
| FR-071-TERRAIN | 2026-11-10 | reason6/DIRT→reason7/FLOORの新判断で停止 | 旧未送信票が最新の開通判断と一致しない | 旧票を永久撤回し、独立静止/完全判断後に別ID・将来拍へ | [計画](plans/test071-observed-entry.md)、[単体](../tests/test_native_terrain071.py)。開通を歩数creditへ変換せず、元期限/入力予算を維持 | 未集計 |
| FR-072-PROTECTED-GOLD | 2026-11-11 | PARTIAL商品の保護maskが隣の金壁へ重なり入店拒否 | 不通行GOLDと進入する床の保護を一律扱い | 保護GOLDと歩行床を分け、同じ観測入口床だけ保持 | [検証](reviews/test072.md)、[単体](../tests/test_native_observation072.py)。商品床/近傍の保護を維持し、保護された商品への進入を許さない | 未集計 |
| FR-072-OBSERVE | 2026-11-11 | 経路不変のreason8でSAMEchain2に達し停止 | 遠方palette変化だけでも同一床の再予約を消費 | 元ID quietと、確実未送信の独立再観測を元予算内で追加 | [計画](plans/test072-approach.md)、[単体](../tests/test_native_observation072.py)。元anchor/同判断/厳密静止/元12秒・chain/run予算を確認 | 未集計 |
| FR-073-PAUSE | 2026-11-11 | 候補なし時の再開直後PAUSEが画面に反映しない | RESUME/RESTART ACK直後に、描画後の新FLOORなしで予約 | 既知ACK後200msと、その後のstable/current-prefix FLOORを要求。新候補を未送信skipより優先 | [計画](plans/test073-restart-pause.md)、[単体](../tests/test_native_ui073.py)。元入力権限/商品優先を確認。200msの端末最短受付・十分性は未受入 | 未集計 |
| FR-074-FADE | 2026-11-11 | 暗い初期候補が消えても旧口へ進む | 描画途中の初期候補を固定したまま歩行を開始 | UI後の独立新観測と初歩前の同原点2画像で候補再確認 | [計画](plans/test074-visible-evidence.md)、[単体](../tests/test_native_view074.py)。旧票/slot撤回と金・商品優先を確認。全候補見逃し率の改善とはしない | 未集計 |
| FR-076-STATIONARY | 2026-11-11 | 通路・通常床で未送信静止UNKNOWNを終了扱い | 不確実画像を待つ間の元anchor/PW保持経路がない | 無入力で独立再観測し、元anchor/PW/時刻内でだけ再判断 | [検証](reviews/test076.md)、[単体](../tests/test_native_stationary_wait076.py)。移動/UNKNOWN入力の再送を拒否。未収録未来の成功は未確認 | 未集計 |
| FR-076-PASSAGE | 2026-11-11 | 金なし通路の未送信lateがCAPTURE停止へ進む | 既回復条件が金可視床だけを想定 | 厳密CLEAR・既知床通路の確実未送信late回復を追加 | [計画](plans/test076-stationary-recovery.md)、[単体](../tests/test_native_passage_unsent076.py)。元期限・旧ID・UNKNOWN無再送を確認 | 未集計 |
| FR-077-PALETTE | 2026-11-11 | 通路へ2歩後、off-step近傍palette差で停止 | 固定通路の無入力待機でも局所差を一律拒否 | 元口/外床・元anchor/PW固定の限定局所差だけ許可 | [検証](reviews/test077.md)、[単体](../tests/test_native_passage_palette077.py)。次セル/壁/保護/元期限の拒否を確認 | 未集計 |
| FR-077-NEW-GOLD | 2026-11-11 | 開扉後、新しく見えた遠方GOLDで未送信停止 | 金集合の追加を同票の変更として拒否 | 開扉後/実進入後PARTIALの同票に、元・直前金を全保持した遠方新金だけ許可 | [計画](plans/test077-shop-visibility.md)、[単体](../tests/test_native_open_entry077.py)。既金消失/保護変化/近傍変更を拒否。全種類の新金を許すものではない | 未集計 |
| FR-079-DIRT | 2026-11-11 | 遠方DIRT→FLOORで未送信の掘削票が停止 | reason6/DIRT票のquietが床票だけに限定 | 閉金扉2ahead・垂直金pairと両近傍不変の同DIRT票だけ保持 | [検証](reviews/test079.md)、[単体](../tests/test_native_dirt_ticket079.py)。full5/strict0/元期限・入力credit不変を確認 | 未集計 |
| FR-080-CLOSED-MOUTH | 2026-11-11 | 通路候補の口が壁と分かった後もNO_PATH停止 | 到達済みの閉口を候補から退役できない | ACK実MOVED到達と独立2観測・静止・同壁口を証明した候補だけprivate closedへ | [計画](plans/test080-sparse-gate-closed-mouth.md)、[単体](../tests/test_native_closed_mouth080.py)。未知口/壁掘削/世界全体の店なしを拒否 | 未集計 |
| FR-081-REFRESH | 2026-11-11 | 閉入口へ向かう床票が遠方STONE差で停止 | 元観測再取得が遠方STONEのpalette変化を対象外 | 入口の固定幾何・近傍・同判断を保持する限定再観測 | [検証](reviews/test081.md)、[単体](../tests/test_native_closed_refresh081.py)。元票の退役/旧ID不活性・全予算を確認 | 未集計 |
| FR-085-SCHEDULE | 2026-11-12 | 真のMOVEDを確認した直後、次票の予約資格不足で停止 | 遅い確定が次拍source200ms条件に間に合わない | 元proof/D/準備窓と未発行nextに限り既再同期へ移す | [計画](plans/test085-verified-scheduling.md)、[単体](../tests/test_native_proof_scheduling085.py)。同拍の時刻延長や未確認移動creditを拒否。金扉前の全待ち時間短縮は未確認 | 未集計 |

## 地形・候補・開扉・実変位

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-066-PAUSE-ICON | 2026-11-10 | 商品が見えるのにFLOORをUNKNOWNと判定 | pause縦棒が11/12pxに分断し元13px openingが不足 | 元13px優先を維持し11px fallbackを追加 | [検証](reviews/test066.md)、[単体](../tests/test_native_icon066.py)。受領67原画中143のみ補正・他66 Scene一致。全表示条件の認識完了ではない | 未集計 |
| FR-067-CLOSED-UNIT | 2026-11-10 | 閉入口へ実1歩進んでもUNKNOWN | 元textureの95%条件不足 | UNKNOWN限定の閉入口一意unitに、強い地形detailの独立証拠をAND | [計画](plans/test067-motion-confirmation.md)、[単体](../tests/test_native_motion067.py)。元73候補/強度/差/支持/2領域を保持。未確定の他原画はUNKNOWN維持 | 未集計 |
| FR-068-LOWER-GOLD | 2026-11-10 | 下端の金壁が見える回で0歩 | 金対がgrid外またはHUD除外内で金候補にならない | 下端の一意raw金対をhintにし、観測済みDOWN床だけ1run1入力 | [計画](plans/test068-fringe-collection.md)、[単体](../tests/test_native_fringe068.py)。119原画中該当5枚だけ補正。未観測gridや次2歩目を作らない | 未集計 |
| FR-072-NARROW-OPEN | 2026-11-11 | 狭い通路で扉が開いても8UNKNOWN | 元textureの支持不足でDOOR→FLOORの0変位を証明できない | 元開通条件に独立したdetail2帯を追加 | [計画](plans/test072-approach.md)、[単体](../tests/test_native_door072.py)。開扉0歩、進入別確認。FR-090の薄鉄型誤認とは別条件 | 未集計 |
| FR-074-OPEN-GRADIENT | 2026-11-11 | 開扉後2商品だけで停止 | 既開通の0変位を元面だけで確認できない | primary UNKNOWN時だけ既知地形の強いzero勾配証拠を追加 | [検証](reviews/test074.md)、[単体](../tests/test_native_motion074.py)。46画像比較で対象開通/実移動pairのみ変化、既nonUNKNOWN21維持。未観測商品は未確認 | 未集計 |
| FR-074-CLEAR-UNIT | 2026-11-11 | 金なし通路の実unitをUNKNOWNと判定 | 入口向け幾何では旧STONE/地形移動を証明できない | 旧STONEの一意translation・非共線DIRT・強いdetailをAND | [計画](plans/test074-visible-evidence.md)、[単体](../tests/test_native_motion074.py)。過去の実変位と未来nextの安全性を別に確認。全通路への一般化は未受入 | 未集計 |
| FR-075-STATIC | 2026-11-11 | 静止した次床の入力前確認がUNKNOWN | texture支持283で元300に不足 | UNKNOWN限定で旧強度・競合条件と独立zero証拠を追加 | [検証](reviews/test075.md)、[単体](../tests/test_native_static075.py)。全73 cacheの1,898比較同値。別方向移動をzeroにしない | 未集計 |
| FR-075-UNIT | 2026-11-11 | UP実1歩が8UNKNOWNで停止 | 元blur/texture面だけでは実unitを確認できない | 原画の明確な移動へ限定した独立unit証拠を追加 | [計画](plans/test075-motion-rpc.md)、[単体](../tests/test_native_motion075.py)。raw/phase/地形/別面をANDし、合成時計と原画像校正を区別 | 未集計 |
| FR-078-CLOSED-UNIT | 2026-11-11 | 金扉前へ実UP1歩進んで停止 | 閉扉の狭い画面では元の独立texture帯が不足 | UNKNOWN限定で全旧金exact/unique9/raw73と固定3面・2帯をAND | [検証](reviews/test078.md)、[単体](../tests/test_native_closed_gate078.py)。受領078の資格付きreferenceでMOVED採用を当該回に確認。全配置/開通/商品成功とはしない | 未集計 |
| FR-079-GOLD-REVEAL | 2026-11-11 | 実1歩で金壁・閉扉が新露出し8UNKNOWN | singleton金からbracketへの増加を旧motion幾何が扱わない | 旧金/旧STONE非共線・新2セル旧UNKNOWNと全強面の一意unit証明 | [計画](plans/test079-gold-reveal-dirt.md)、[単体](../tests/test_native_revealed_gate079.py)。旧known/partial全STONE条件は維持。新露出一般を許可しない | 未集計 |
| FR-080-SPARSE-GATE | 2026-11-11 | 狭い閉扉前で実unitを確認できない | 元phase全73がINF、旧強面の独立帯も不足 | 固定openingmask・全依存/UI除外による別phaseと旧強面をAND | [検証](reviews/test080.md)、[単体](../tests/test_native_sparse_gate080.py)。元算術/unit/強度/差/帯/全候補比較を保持。旧各helperは変更しない | 未集計 |
| FR-081-SIDE-GATE | 2026-11-11 | 実1歩で側方の金入口が出現して停止 | 元閉扉証拠がその側方幾何を対象外 | 側方bracketと旧固定面の限定unit証明を追加 | [計画](plans/test081-batch-stops-evidence.md)、[単体](../tests/test_native_side_gate081.py)。方向/非unit/保護の拒否を確認。候補見逃し全般の改善とはしない | 未集計 |
| FR-081-CLIPPED-ENTRY | 2026-11-11 | 上端で商品が一部見えても入店できない | 部分商品の入口視認と保護を旧条件が対象外 | 観測床と部分商品の幾何を限定して入口進入を保持 | [検証](reviews/test081.md)、[単体](../tests/test_native_clipped_entry081.py)。商品保護/元期限を維持し、一部表示を商品確認完了にしない | 未集計 |
| FR-082-MATERIAL | 2026-11-12 | 逆方向へ向かう/初回候補を見送る | DIRTの色境界で床・半可視床・石を誤認 | 旧DIRTだけに固定raw pixel・独立帯・分散等の追加証拠 | [計画](plans/test082-materials-motion.md)、[単体](../tests/test_native_materials082.py)。97原画の材質変化と下記FR-082-REGRESSIONを確認。未解明停止をこの対策で改善済みにしない | 未集計 |
| FR-082-CLEAR-UNIT | 2026-11-12 | 無金通路で実UP1を確認できない | 原rawが旧.45条件外、既地形/別面の組合せが対象外 | 既074/075証明へ旧STONE/非共線DIRT/一意性・独立面を追加AND | [検証](reviews/test082.md)、[単体](../tests/test_native_passage_motion082.py)。旧known27維持、旧UNKNOWN9中1だけ校正変化。残8を成功にしない | 未集計 |
| FR-082-REGRESSION | 2026-11-12 | 既確認LEFT1が素材補正後にUNKNOWNへ回帰 | 正しいFLOOR復元で8px競合支持が増え、旧blurの15pp差を失う | 旧helper/材質補正を維持し、別のraw gradient強条件をANDするB2を追加 | [原因と追試](reviews/test082.md)、[単体](../tests/test_native_passage_motion082.py)。source116→126の公開Redと修正後の旧known27全保持を確認。配布前に検出した回帰1件の記録であり、恒久再発なしの保証ではない | 未集計（配布前回帰1件を本行に記録） |
| FR-083-LOWER-GOODS | 2026-11-12 | 下の商品が未観測のまま左へ歩く | 商人HP下の床がDIRT、旧GOLD距離目標が左へ偏る | 独立2帯の床証拠を追加し、実入店/PARTIAL/ITEMだけ画面端overflowを減らす床目標へ | [計画](plans/test083-first-gold-goods-view.md)、[単体](../tests/test_native_outer_floor083.py)・[商品目標](../tests/test_native_shop_framing083.py)。原297/343でDOWN選択。未収録先の可視は未確認 | 未集計 |
| FR-083-FIRST-GOLD | 2026-11-12 | CLEAR金0→CANDIDATE金1の実LEFT1がUNKNOWN | 単金初露出は旧unit証拠の対象外 | 旧全STONE/非共線DIRT/unique9/raw有限unit/blur/phaseの専用AND | [検証](reviews/test083.md)、[単体](../tests/test_native_first_gold083.py)。適格原115だけ変化、旧113/INF/UNKNOWNを保持 | 未集計 |
| FR-084-MOUTH | 2026-11-12 | 黒上半/床下半や上左の口候補を見送る | 粗いtile判定では観測床・片壁/他UNKNOWNを拾わない | raw床・口/外床・壁の別証拠で限定候補を回復 | [計画](plans/test084-mouth-icon.md)、[単体](../tests/test_native_shadow_floor084.py)・[候補](../tests/test_native_supported_mouth084.py)。257原画の通常cellを保持し指定3候補だけ校正変化 | 未集計 |
| FR-084-PAUSE-ICON | 2026-11-12 | 商品可視後もポーズせず停止 | pause記号が9px断片になり旧13/11pxでも不足 | 元fullROI/IoU.8下で9px断片の追加証拠 | [検証](reviews/test084.md)、[単体](../tests/test_native_icon084.py)。原379の認識を確認。全表示圧縮条件への一般化は未受入 | 未集計 |
| FR-085-CLEAR-STATIC | 2026-11-12 | 無金通路の再観測待機が不成立 | 元2拍W内に静止を確定する独立背景証拠がない | zero-onlyの背景proofを追加し元W内の独立静止を確認 | [検証](reviews/test085.md)、[単体](../tests/test_native_stationary_texture085.py)。移動creditへ流用せず、金扉前の待ち時間とは別に扱う | 未集計 |
| FR-086-CORNER | 2026-11-12 | 角通路候補を見送りリスタート上限へ | 旧口候補が固定cornerの床/壁形状を対象外 | 観測口/外床と両壁・壁列支持、最短床3以内のvantageだけ接近 | [計画](plans/test086-vantage-gold.md)、[単体](../tests/test_native_corner_vantage086.py)。原417 Scene/旧known維持、既知誤陰性093だけ候補差。見逃しゼロではない | 未集計 |
| FR-086-SINGLE-GOLD | 2026-11-12 | 単金1→1を保持した実歩で停止 | 既unit幾何がこの金集合を対象外 | 旧15段のUNKNOWN後にraw/phase/blur/axis/geometry全ANDの専用unit | [検証](reviews/test086.md)、[単体](../tests/test_native_single_gold086.py)。原101/110を校正、他適格6画像UNKNOWN維持。旧081実5の金1→2とは別に未確認を残す | 未集計 |

## 保存・診断・対象判定

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-068-REWRITE | 2026-11-10 | 同UUIDの回収再開が長く、次ゲームが開かない | 完成画像も同bytes再write/両journal保存していた | 全source/prefix/hash検証後に完成画像の再writeを省く。native結果と回収状態を分離表示 | [検証](reviews/test068.md)、[回収単体](../tests/test_native_collection068.py)。既完成/fragmentだけ/欠損/変化を区別。初回共有保存負荷は別のFR-069-SPOOL | 未集計 |
| FR-069-SPOOL | 2026-11-10 | 12/16画像など未回収でも終了表示 | 共有mountへの細かいatomic保存が90秒枠を消費 | iSH local原本と安全terminal独立300秒回収、全画像確認後に単一ZIPを共有へ公開 | [計画](plans/test069-collection-gate.md)、[回収](../tests/test_native_collection069.py)・[出版](../tests/test_native_publication069.py)。全保存/receipt前の終了・次startを拒否。対象判定の長時間化とは別 | 未集計 |
| FR-075-JSON | 2026-11-11 | 初歩前にhost cancelされる | iSHのstatus result_json処理がRPC2秒を超える | strict schemaを保持したJSON同値高速化 | [計画](plans/test075-motion-rpc.md)、[単体](../tests/test_json075.py)。10,222差分一致・新/関連parser確認。受領075のstatus46回エラー0は当該回だけで、恒久2秒以内ではない | 未集計 |
| FR-081-DECISION-EVIDENCE | 2026-11-11 | 初期候補見逃しを調べる原画像がない | 歩行/停止画像優先で各map判断sourceがexportされない | v2で各map最新見送りsource≤12とcritical≤7を20pin内に保持 | [計画](plans/test081-batch-stops-evidence.md)、[単体](../tests/test_native_profile081.py)・限定Runtime保存6case。全取得画像保存ではなく、見逃し自体の対策完了とはしない | 未集計 |
| FR-082-WAIT-TRACE | 2026-11-12 | 未発行stationary拒否の最初の根拠を追えない | 無入力待機中の地形変化拒否が診断に残らない | 真の非zero差だけ既診断へ結合 | [計画](plans/test082-materials-motion.md)、[単体](../tests/test_native_wait_diagnostics082.py)。mask0/署名だけ/旧権限を拒否。停止改善ではなく原因確認のための対策 | 未集計 |
| FR-084-NONFLOOR-TRACE | 2026-11-12 | 最初拒否画像が省略され停止原因が不足 | 非FLOOR拒否と保持された末尾原画を直接結べない | 同ACK/元期限内のnon-FLOOR拒否を既STATE診断へ追加 | [検証](reviews/test084.md)、[単体](../tests/test_native_nonfloor_diagnostics084.py)。欠損285を後の画像で代用しない。元停止原因未確定は維持 | 未集計 |
| FR-087-WAIT-ENTRY | 2026-11-12 | 通路で非zero待機に入った最初の根拠が不足 | 旧診断が通路待機入口の真の差を残さない | 非zeroの待機入口だけ既診断へ追加 | [計画](plans/test087-target-pause.md)、[単体](../tests/test_native_wait_entry087.py)。mask0を対象外とし、旧086実4の歩行停止は未確認のまま | 未集計 |
| FR-087-PY39 | 2026-11-12 | 画像20/20保存後にAttributeErrorで通常ZIPが未完成 | `int.bit_count`はPython3.9にない | 同値のbin countへ置換し、同087保存を再開する入口を追加 | [計画](plans/test087-python39.md)、[判定](../tests/test_target_assessment087.py)・[回復](../tests/test_recover087.py)。実3.9の有効Red/9件Green、原正例維持。歩行停止は別 | 未集計 |
| FR-088-CPU | 2026-11-12 | 画像取得後の指輪判定が無表示/長時間 | Pythonのicon画素探索が開発profileの約96.5% | tuple sum/安全上界による意味不変軽量化と経過表示 | [計画](plans/test088-postprocess.md)、[性能](../tests/test_target_performance088.py)・[進捗](../tests/test_target_progress088.py)。実3.9/原309同値。fix2実機は128秒超が継続し、改善完了とは扱わない | 1（fix2後に同じ判定待ち継続。回帰とは未確定） |
| FR-088-EVIDENCE | 2026-11-12 | 判定が終わらず原画像も返せない | 通常出版が判定完了の後に直列化 | 判定を呼ばない別証拠ZIP/別receiptで全原画像だけ回収 | [計画](plans/test088-evidence.md)、[単体](../tests/test_evidence088.py)。実3.9/元bytes・mtime不変、通常pending維持。判定の性能対策完了ではない | 未集計 |
| FR-089-KERNEL | 2026-11-12 | 088軽量化後も実機判定が128秒超 | 原235 profileでPython icon70%/PNG復元27%の画素ループ | 同iSHの固定static i386へ画素処理を移し、Pythonで厳密PNG/有限集約を保持 | [計画](plans/test089-native-ring.md)、[kernel](../tests/test_ring_backend089.py)・[protocol](../tests/test_ring_native089.py)・[精度境界](../tests/test_ring_accuracy089.py)。保存packet全field同値、陰性4/不明4/未知陽性0を区別。実iSH/人超えは未受入 | 未集計 |
| FR-089-EARLY | 2026-11-12 | 商品到達後も全診断画像の回収が判定を待たせる | authorityが回収順の途中で、判定自体も全回収後 | authority優先取得/暫定表示、全certificate後にmemory cacheを再結合して正式出版 | [検証](reviews/test089.md)、[早期](../tests/test_ring_early089.py)・[出版](../tests/test_ring_publication089.py)。実3.9/i386/暗号HTTPで順序・回復・故障保持を確認。全画像回収時間や人間速度の合格とはしない | 未集計 |

## 旧経路の主要な関連記録（TEST034〜060の抜粋）

この節は旧Python制御からnativeへ移る前後の記録。現在と同じ停止表示でも、同じコード・適用条件・原因かを別に調べる。日付が明記されないものに、受領日を修正日として流用していない。

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-036-LUT | 2026-11-07 | 旧移動比較が約1秒 | 73候補×256値のgain表をPythonで丸めて生成 | 同じties-to-evenを保つi386 C LUTへ移す | [台帳TEST036](device-tests/README.md)、[単体](../tests/test_motion_stats.py)。全LUT byte/境界double/実035全73score同値。新090のiconとは別モジュールで、同コードを戻した証拠はない | 未集計 |
| FR-038-ANCHOR | 2026-11-07 | 照明が変わる実1歩をUNKNOWNとして停止 | 強度上限と単一金壁のため旧閉扉構造証拠が対象外 | 単一金から増加する場合にGOLD/複数STONEの一意対応を強い質感とAND。観測範囲外の旧STONEは支持外、観測済み別ラベル矛盾は拒否 | [台帳TEST038](device-tests/README.md)。原105→107と逆方向/矛盾/共線/競合の単体・校正。現在のCLEAR通路/HUD喪失と同根本とは断定しない | 未集計 |
| FR-044-PREFLIGHT | 未特定（TEST044） | ゲームを開かず接続失敗で終了 | 開始前の接続失敗の下位分類と経過が失われる | UI不要のGET版/cap確認と開始前だけ有限再照会・固定診断 | [台帳TEST044](device-tests/README.md)、[接続単体](../tests/test_native_connect.py)。認証/不正metadata/取消/総8秒とstart1回。開始後の再送は許さない | 未集計 |
| FR-045-INITIAL | 未特定（TEST045） | Scene差で初歩0入力、結果画像も未回収 | 経路外差でも全Scene比較で失効し、結果RPC枠も入力系と共通 | 確実未送信の初歩を最大2回、同拍・元期限下で最新Sceneの別IDへ。read-only回収枠を分離 | [台帳TEST045](device-tests/README.md)。旧票永久失効/prefix/厳密静止/新choose/取消の単体。未観測の先を改善済みにしない | 未集計 |
| FR-046-OBSERVE | 未特定（TEST046） | ACK後35pxの途中像で即停止 | 4px間引き署名ではUNKNOWNだが、続く36px像を観測しない | 同command/before/prefix・元絶対期限内でUNKNOWN/TWEENを合計3回まで再観測 | [台帳TEST046](device-tests/README.md)。実13→16/17・3評価/期限/商品優先を確認。ACK不明入力は無再送 | 未集計 |
| FR-047-RASTER | 未特定（TEST047） | 実機EXIF8でgeometry/stale、0歩 | Swiftの向き全画素コピーが約986ms、旧向き1 fastpathは不適用 | 向き2〜8の同じRGBA整数写像をCへ移す | [台帳TEST047](device-tests/README.md)、[単体](../tests/test_native_raster.py)。全8向き旧map全画素同値と長さ/overlap/overflowの書込前拒否。全端末速度は未受入 | 未集計 |
| FR-049-PERCEPTION-O2 | 未特定（TEST049） | 実歩が見えるのにobserve期限後 | decodeとPerception純解析が重く、Debug O0 | Perceptionだけstrict O2にし、他C/Swift・アルゴリズムを保持 | [台帳TEST049](device-tests/README.md)。原PNG全Scene同値、実compiler/RSP/PBX/IPA profile照合。最適化だけで全停止改善とはしない | 未集計 |
| FR-050-NAV-O2 | 未特定（TEST050） | MOVED後の次拍が期限超過 | Navigationの73候補処理がO0 | Navigationだけstrict O2、observe開始時刻を追加 | [台帳TEST050](device-tests/README.md)。全score/field同値と実compiler、時刻/schema/旧互換を確認。入力窓自体は緩めない | 未集計 |
| FR-051-SAME | 未特定（TEST051） | 経路外のScene差で未送信連続票まで停止 | 全Scene差を同MOVEの失効と扱う | 同direction/完全Decision・金/保護・厳密静止・元時刻下でSAME別ID更新 | [台帳TEST051](device-tests/README.md)、[公開Controller単体](../tests/test_native_controller.py)。元ticket/旧ID不活性と全権限を確認。全palette差の許可ではない | 未集計 |
| FR-052-TARGET | 2026-11-08 | reason8の遠方目標だけ変わり停止 | 次の同じ床1歩と遠方targetの違いを分けていない | 同actionを維持するtarget差だけ許し、保存beforeの完全5field検証を維持 | [台帳のTEST052計画/試験補足](device-tests/README.md)。公開C/判断変異の確認。新しいdirection/障害物を同action扱いしない | 未集計 |
| FR-052-BATCH | 2026-11-08 | iSHの逐次画像保存が90秒で打切り | 小chunkごとの保存/チェックポイント負荷 | v10の最大4chunk/256KiB batchと進捗表示、未照合suffix/旧v9互換を保持 | [台帳TEST052](device-tests/README.md)、[単体](../tests/test_native_export_batch.py)。各chunk検証/中断回復を確認。後の初回共有I/OはFR-069-SPOOLとして別追跡 | 未集計 |
| FR-053-PREP | 2026-11-08 | 初歩を早く予約して再plan枠消費、AXは遅れる | 準備開始と最新Sceneから公開する時点が未分離 | lead+50msでslot先決め、NB50〜100msで初ticket公開 | [台帳TEST053](device-tests/README.md)。固定時刻/新source/未送信/元期限の単体。実ゲームの受付幅や毎拍の全体合格ではない | 未集計 |
| FR-054-REFERENCE | 未特定（TEST054） | 新authorityと実変位の比較でUNKNOWN | 確認元の描画差が同logical MOVE比較に影響 | 元referenceから全新Sceneへ直接厳密静止を証明し、primary UNKNOWN時だけ補助 | [台帳TEST054](device-tests/README.md)、[単体](../tests/test_native_motion_references.py)。同prefix/時刻/同判断/失格後復活なしを確認 | 未集計 |
| FR-055-FRESH | 2026-11-09 | 新GOLD/DOORで変わった未送信判断を一律拒否 | SAMEでは新しい経路判断を扱えない | monotone観測と全guard下で新最新判断のFRESH別IDへ | [計画](plans/test055-latest-plan.md)。公開Cで完全Decision/時刻/旧ID/予算を確認。旧054はUP/FLOOR→LEFT/DIRT、090同一床目標とは別の条件 | 未集計 |
| FR-056-STOP-EVIDENCE | 2026-11-09 | 停止比較125/126/127などが未収録 | pin20/選択20で必要な比較sourceが落ちる | 最新2比較とlatestMOVE等を保持/選択の両側で優先 | [計画](plans/test056-stop-evidence.md)。保持上限・参照画像/SHA/旧互換確認。全取得画像保存や原因解消ではない | 未集計 |
| FR-057-FLOOR-BAND | 2026-11-09 | 明るい床のB/R境界で誤った往復 | bright bandのB下限が実床色を外す | bright bandのB下限だけ校正 | [計画](plans/test057-floor-quantization.md)。原画の材質/経路と旧境界反例を確認。後続dark bandは別条件、回帰と即加算しない | 未集計 |
| FR-058-DISPATCH | 2026-11-09 | 同MOVE再予約後、main移送で10ms窓超過 | AX/準備/JSONの直列費用が送信直前へ集中 | 資格付きprepare共有、JSONを入力後へ、dueを直接実行 | [計画](plans/test058-shop-dispatch.md)。dispatch/取消/旧source/元窓の公開結合。ACKを実変位にしない | 未集計 |
| FR-059-SLOT | 2026-11-09 | 次target補正と旧期限の間に空の入力窓 | 親motion確認と次slot更新の時刻が混在 | 親motion/次slot分離、target/窓の対更新とreserve凍結 | [計画](plans/test059-next-slot.md)。元target/ordinal/期限の境界とactual tickを確認。旧窓の延長ではない | 未集計 |
| FR-060-ADMISSION | 2026-11-09 | 次ordinalの初予約が早く1px描画差で失効 | 遅い次拍まで早過ぎるsourceを保持 | 同元拍のNB100ms/source200ms以降へ初予約を限定 | [計画](plans/test060-continuous-admission.md)。元Dをactual tickまで保持する単体。060実機は別の初歩同期/ACK後UNKNOWNで未到達だった | 未集計 |

## TEST090の対策（実機改善未確認）

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-090-HUD-STONE | 2026-11-13 | 実089-2でUP1後に8UNKNOWN停止 | 旧STONE1個が移動先の心臓HUDへ入り、全旧STONE保持条件を満たさない | 固定HUDへのexact1喪失だけを残STONE2/非共線DIRT9と独立raw/world/axisの全強条件で確認 | [新5単体](../tests/test_native_hud_unit090.py)・[根拠](reviews/test090.md)。原8観測は初2UNKNOWN保持/後6UP1。FR-038-ANCHOR・FR-074-CLEAR-UNITの関連条件と照合し、既対策の適用外と同原因再発は未確定。実機改善未確認 | 0（今回記録開始後の再観測なし。実機未確認） |
| FR-090-REVEALED-ROUTE | 2026-11-13 | 実089-3で同じ次LEFTを未送信拒否 | 新bracket扉/金と遠方DIRT→FLOORで元monotone不成立、reason8→7へ変化 | 同方向/同目標/FLOOR・厳密静止と元未送信票の全期限/予算下だけ既FRESHへ移す | [新3単体](../tests/test_native_revealed_route090.py)の4方向/拒否12/予算2、関連3。FR-055-FRESH・FR-081-REFRESHと照合しglobal monotoneは保持。実時計model未保存のため合成時計、実機改善未確認 | 0（今回記録開始後の再観測なし。実機未確認） |
| FR-090-THIN-IRON | 2026-11-13 | 実089-4で開扉をBLOCKEDとして入口停止 | 薄い鉄閉扉が中央値でFLOORとなり、旧DOOR→FLOOR条件へ入らない | 金bracket内の限定縦線をDOORへ回復し、既開扉0歩経路へ渡す | [新3単体](../tests/test_native_thin_gate090.py)・原108の1byte型訂正/原115不変と公開DOOR_OPENED。FR-072-NARROW-OPEN・FR-074-OPEN-GRADIENTはDOOR型を前提とする別段階。進入/下商品と実機改善は未確認 | 0（今回記録開始後の再観測なし。実機未確認） |
| FR-090-RING-COST | 2026-11-13 | 指輪先行判定までの待ちが残る | icon内の同じ浮動積/64bit累積が冗長。実5.276秒区間の全内訳は未確定 | 安全上界内のint32累積/同じ256値の積を再利用する意味不変整理 | [計画](plans/test090-device-stops.md)、原309/235/204のmode0/1全6packet同値・実3.9 backend1・異cwd再build同一。FR-088-CPU・FR-089-KERNELと照合。開発単発約18%を実iSH/人超えにしない。実機改善未確認 | 未集計（待ち全体の原因内訳は未確定） |
| FR-090-UNKNOWN-TEXT | 2026-11-13 | 実089-1の「不明」が商品判定失敗と受け取られた | のろい一致未確認と全商品名識別/対象なし確定の区別が伝わりにくい表示 | 「のろいのゆびわとの一致は未確認（対象なしとは未確定）」へ表示literalだけ訂正 | [既表示試験](../tests/test_target_publication087.py)と進捗2を実3.9で確認。2sourceを旧literalへ逆変換すると元全bytes一致。[旧対象判定契約](contracts/target-assessment.md)と照合、schema/閾値/陰性判定は不変。実機表示未確認 | 0（今回記録開始後の再観測なし。実機未確認） |
| FR-090-CI-SCOPE | 2026-11-13 | 旧087 host selectorが089のclient変更を拒否する条件が残る | 旧版の不変pin/対象集合を現在版にも要求する | 新090 selectorで実patched source/22sealと変更部・関連だけを固定、旧Runtimeは不変bytesへ結合して今回未実行と明示 | [selector自己4試験](../patches/loopctrl/test_device_ci090.py)で旧pin/省略/重複を拒否するRed→Green。実CI/IPAの照合は別に記録し、過去のGreenを今回実行へ流用しない | 0（今回記録開始後の再観測なし） |
| FR-090-READER-PATH | 2026-11-13 | 実物検査がR12を38件と誤集計して停止 | Git name-onlyの引用された日本語2pathを改行分割のprefix判定で落とした | 列挙を-z/NUL/UTF8へ訂正し実40pathと全bytesを照合 | [検証記録](reviews/test090.md)。過去のパス/JSON/CI行を参照し別原因と確認。Unicode単体Red→Green、retainedだけ明示再実行してPASS、既PASS2は再実行0。IPA/製品変更なしの補助検査で、実機改善を示さない | 0（今回記録開始後の再観測なし） |

今回の記録ルールは修正着手後に追加されたため、TEST090は提出前に過去対策を遡及照合した。以降は修正前の照合を必須にする。関連IDは同原因の証明ではなく、旧対策の維持と適用条件を調べるための参照である。

## 未整理・未確定の扱い

初期版の全件と、各対策後の同原因発生回数は未整理。複数の似た停止、未収録原画、単体だけで確認した変化を、根拠なく「同原因再発」や「改善完了」に寄せない。特に旧081実5の金1→2、旧086実4の最初の拒否、未観測商品/候補見逃しの未確定は、それぞれのレビューで追う。
