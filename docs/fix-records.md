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
| FR-074-OPEN-GRADIENT | 2026-11-11、追加2026-11-13 | 開扉後2商品だけで停止 | 既開通の0変位を元面だけで確認できない。090実3もDOOR型は正しいがtexture不足でUNKNOWN | 旧証明を維持し091で独立blur絶対品質とraw/detail/unique bracketの別zero証明を追加 | [検証](reviews/test074.md)、[旧単体](../tests/test_native_motion074.py)、[091受領](reviews/test091.md)。旧46画像比較の合格を今回条件の解消と扱わない。未観測商品は未確認 | 過去未集計＋今回1（090実3の継続。旧対策削除による回帰は未確定） |
| FR-074-CLEAR-UNIT | 2026-11-11、追加2026-11-13 | 金なし通路の実unitをUNKNOWNと判定 | 旧地形証明の対象外条件が継続。090実2は左raw帯runner支持不足/blur競合差不足 | 旧証明を維持し091で全旧STONE保存・非共線DIRT・raw/world/axisをANDする別unit証明を追加 | [計画](plans/test074-visible-evidence.md)、[旧単体](../tests/test_native_motion074.py)、[091受領](reviews/test091.md)。過去の実変位と未来nextの安全性を別に確認。全通路への一般化は未受入 | 過去未集計＋今回1（090実2で適用外条件が継続。旧対策削除による回帰は未確定） |
| FR-075-STATIC | 2026-11-11 | 静止した次床の入力前確認がUNKNOWN | texture支持283で元300に不足 | UNKNOWN限定で旧強度・競合条件と独立zero証拠を追加 | [検証](reviews/test075.md)、[単体](../tests/test_native_static075.py)。全73 cacheの1,898比較同値。別方向移動をzeroにしない | 未集計 |
| FR-075-UNIT | 2026-11-11 | UP実1歩が8UNKNOWNで停止 | 元blur/texture面だけでは実unitを確認できない | 原画の明確な移動へ限定した独立unit証拠を追加 | [計画](plans/test075-motion-rpc.md)、[単体](../tests/test_native_motion075.py)。raw/phase/地形/別面をANDし、合成時計と原画像校正を区別 | 未集計 |
| FR-078-CLOSED-UNIT | 2026-11-11 | 金扉前へ実UP1歩進んで停止 | 閉扉の狭い画面では元の独立texture帯が不足 | UNKNOWN限定で全旧金exact/unique9/raw73と固定3面・2帯をAND | [検証](reviews/test078.md)、[単体](../tests/test_native_closed_gate078.py)。受領078の資格付きreferenceでMOVED採用を当該回に確認。全配置/開通/商品成功とはしない | 未集計 |
| FR-079-GOLD-REVEAL | 2026-11-11 | 実1歩で金壁・閉扉が新露出し8UNKNOWN | singleton金からbracketへの増加を旧motion幾何が扱わない | 旧金/旧STONE非共線・新2セル旧UNKNOWNと全強面の一意unit証明 | [計画](plans/test079-gold-reveal-dirt.md)、[単体](../tests/test_native_revealed_gate079.py)。旧known/partial全STONE条件は維持。新露出一般を許可しない | 未集計 |
| FR-080-SPARSE-GATE | 2026-11-11 | 狭い閉扉前で実unitを確認できない | 元phase全73がINF、旧強面の独立帯も不足 | 固定openingmask・全依存/UI除外による別phaseと旧強面をAND | [検証](reviews/test080.md)、[単体](../tests/test_native_sparse_gate080.py)。元算術/unit/強度/差/帯/全候補比較を保持。旧各helperは変更しない | 未集計 |
| FR-081-SIDE-GATE | 2026-11-11 | 実1歩で側方の金入口が出現して停止 | 元閉扉証拠がその側方幾何を対象外 | 側方bracketと旧固定面の限定unit証明を追加 | [計画](plans/test081-batch-stops-evidence.md)、[単体](../tests/test_native_side_gate081.py)。方向/非unit/保護の拒否を確認。候補見逃し全般の改善とはしない | 未集計 |
| FR-081-CLIPPED-ENTRY | 2026-11-11 | 上端で商品が一部見えても入店できない | 部分商品の入口視認と保護を旧条件が対象外 | 観測床と部分商品の幾何を限定して入口進入を保持 | [検証](reviews/test081.md)、[単体](../tests/test_native_clipped_entry081.py)。商品保護/元期限を維持し、一部表示を商品確認完了にしない | 過去未集計＋今回2（092の同配置2runで投影端/遠方差による適用外が継続。旧対策削除ではない） |
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
| FR-090-UNKNOWN-TEXT | 2026-11-13 | 実089-1の「不明」が商品判定失敗と受け取られた | のろい一致未確認と全商品名識別/対象なし確定の区別が伝わりにくい表示 | 「のろいのゆびわとの一致は未確認（対象なしとは未確定）」へ表示literalだけ訂正 | [既表示試験](../tests/test_target_publication087.py)と進捗2を実3.9で確認。2sourceを旧literalへ逆変換すると元全bytes一致。[旧対象判定契約](contracts/target-assessment.md)と照合、schema/閾値/陰性判定は不変。091実機で表示は確認したが、実施状態の区別は未解決 | 1（091で実施済み/未実施の区別がつかないとの再指摘。表示集約の継続、判定精度の再発ではない） |
| FR-090-CI-SCOPE | 2026-11-13 | 旧087 host selectorが089のclient変更を拒否する条件が残る | 旧版の不変pin/対象集合を現在版にも要求する | 新090 selectorで実patched source/22sealと変更部・関連だけを固定、旧Runtimeは不変bytesへ結合して今回未実行と明示 | [selector自己4試験](../patches/loopctrl/test_device_ci090.py)で旧pin/省略/重複を拒否するRed→Green。実CI/IPAの照合は別に記録し、過去のGreenを今回実行へ流用しない | 0（今回記録開始後の再観測なし） |
| FR-090-READER-PATH | 2026-11-13 | 実物検査がR12を38件と誤集計して停止 | Git name-onlyの引用された日本語2pathを改行分割のprefix判定で落とした | 列挙を-z/NUL/UTF8へ訂正し実40pathと全bytesを照合 | [検証記録](reviews/test090.md)。過去のパス/JSON/CI行を参照し別原因と確認。Unicode単体Red→Green、retainedだけ明示再実行してPASS、既PASS2は再実行0。IPA/製品変更なしの補助検査で、実機改善を示さない | 0（今回記録開始後の再観測なし） |

今回の記録ルールは修正着手後に追加されたため、TEST090は提出前に過去対策を遡及照合した。以降は修正前の照合を必須にする。関連IDは同原因の証明ではなく、旧対策の維持と適用条件を調べるための参照である。

## TEST091の対策（実機改善未確認）

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-091-INITIAL-SCENE | 2026-11-13 | 090実1で初歩を送る前に0歩SCREEN停止 | 初歩票確定後のScene拒否を再観測へ戻せない。最初拒否175が欠け最終predicateは未確定 | 入力/移動/lead0・確実未送信だけ旧IDを撤回、既replan2回/元12秒/元walk/session内で独立2枚から新票を得る | [計画](plans/test091-device-stops.md)・[新単体](../tests/test_native_initial_scene091.py)。元時刻/prefix/取消/商品優先/無再送を維持。FR-045/061/074/076のscopeと照合。実機改善未確認 | 未確認（原因の一部未確定。旧175を後187で補わない） |
| FR-091-INITIAL-IMAGE | 2026-11-13 | 090実1の最初の拒否原画175が残らない | 初歩経路の早期拒否が既比較診断へ乗らず、末尾画像で置換される。原175のmaskは未確定 | profile2の余剰1pinに一致snapshot/prefix/拒否時刻の原点未送信拒否raw1枚、旧critical7/map12の保持は維持。診断側はlevel入力0や回復権限を証明しない | [計画](plans/test091-device-stops.md)の新公開Runtime fixture5と旧081関連6がMacでGreen、固定c9の有効Red1も確認。全20PNG/10MiB/schemaを維持し、停止解消とは区別。FR-056/082/084/087の保持scopeと照合 | 0（新対策の実機再観測なし。実機未確認） |
| FR-091-TERRAIN-AXIS | 2026-11-13 | 090実2の実UP1後に8UNKNOWN | 全旧STONEは保存されるが、旧有限左右raw帯/blur競合条件が不成立 | 旧17段を保ち、全旧STONE2/非共線DIRT9・unique9・有限raw全73/差・world95%・axis75%/旧15ppの別証明 | [091受領](reviews/test091.md)。旧FR-074-CLEAR-UNITに今回継続1を記録。HUD喪失0でFR-090-HUD-STONE適用外。新4単体/保存pair校正と現CI38件を確認。未来到達の確認ではない | 0（091新証明の実機再観測なし。旧通路問題の継続は上記に記録） |
| FR-091-OPEN-BLUR | 2026-11-13 | 090実3で開扉しても2商品だけで停止 | 型DOORは正しいが、rawzero .45546/旧detail95%/gradient支持の不足で開通0変位がUNKNOWN | 旧証明不変、有限rawzero/runner差・unique bracket・detail75%/二帯/旧競合比較・blurzero絶対品質の別AND | [091受領](reviews/test091.md)。FR-074-OPEN-GRADIENTへ継続1を記録。FR-090-THIN-IRONと異なる段階。新5単体/原pair校正と現CI38件を確認。開扉0歩、全3商品不可視を完了/対象なしにしない。実機改善未確認 | 0（091新証明の実機再観測なし。旧開通問題の継続は上記に記録） |
| FR-091-PUBLICATION-NAME | 2026-11-13 | 公開後の補助検査がasset名の集合比較で停止 | root作成の補助scriptがチェックサム名をSHA256SUMSと仮定。既publisher正本はSHA256SUMS.txtで配布物の破損ではない | 過去の配布検査/既workflow FILESを照合し実名へ訂正。3asset/全bytesの検査は維持 | [固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test091-build152)の実tagと全3assetの匿名GET200/全bytes/SHA一致を確認。初回は原asset読取前に失敗、実物5gate再実行0/製品・配布物変更0。公開後の文書追記のみ、固定tag/source731は維持 | 0（今回記録開始後の再観測なし。実機とは別の補助検査） |


## TEST092の対策（実機改善未確認）

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-092-STARTUP-PORTRAIT | 2026-11-13 | 091初回d503でゲーム表示前にgeometry停止 | 最初の828×1792/EXIF1の縦画像を約426msでaspect拒否。前面PIDと描画向き完了を分けない。raw未保持で画像内容未確定 | 既3秒の新取得期限/64回/50ms内だけ初期portraitを再観測、既2秒reply/drain・Raster・正常後failfastは維持 | [計画](plans/test092-startup-stationary-status.md)・[受領](reviews/test092.md)。旧FR-044接続/FR-047向き処理とは別段階。次実行で起動した実績と、恒久改善未確認を分ける。限定Mac公開fixtureで確認した CI157で基準Red1・現新9＋旧保存1が成功。最終fixture017d064aは訂正後、実機未確認。 | 0（新対策後の実機再観測なし。実機未確認） |
| FR-092-GOLD-STATIC | 2026-11-13 | 091実2で未送信静止拒否後BEAT停止 | 同位置の光/遠方材質差で旧raw/static95%証明が不成立、元anchorへ静止を証明できず再同期へ | 旧19段/旧条件不変、同GOLD2/全旧STONE/非共線DIRT・有限rawzero/world95/axis75/競合の別zero証明 | [受領](reviews/test092.md)。旧FR-076待機/FR-085静止/FR-082の競合条件を照合。旧CLR静止と異なるGOLD条件、旧対策削除による回帰は未確定。新4単体と元ticketの窓/ID/0credit単体がGreen。開通/移動creditへしない。実機改善未確認 CI157の同sourceで新4と元ticket窓を含むhost30が成功。 | 0（新GOLD証明後の実機再観測なし。旧問題の適用外条件が継続） |
| FR-092-UNLOCALIZED-GOLD | 2026-11-13 | 091実4で候補を見て0歩SCREEN停止 | 原280は上端金/CANDIDATE/peak158/GOLD tile0、通常店経路なし・通路がCLEAR専用。最初拒否279未保持で全predicate未確定 | 正の未局在候補のまま既観測mouth/床経路へ2独立画像で接近。CLEAR偽装/地図外GOLD/未知床/陰性restartへ変換しない | [計画](plans/test092-startup-stationary-status.md)。旧FR-074描画待ち/FR-091未送信初歩を照合、今回はMOVE未発行で後者scope前。新mode6＋窓1/旧関連7がGreen。原280校正/新制御単体は未収録未来の到達証明ではない CI157の同sourceで新class7を同process実行しhost30が成功。 | 0（新mode後の実機再観測なし。実機未確認） |
| FR-092-RING-STATUS | 2026-11-13 | 商品到達時と未到達停止時の判定ログが同じ | outcome unknownだけを表示し、sourcesあり/なしを区別しない | 暫定/正式の共通formatterで実施済み・一致未確認と未実施を分離。判定/authority/schema/ELF不変 | [新表示単体](../tests/test_ring_status092.py)5＋旧表示1が実3.9でGreen。有効Red先行、旧assert維持/不足mock metadata補足。関連progressのhost i386非対応は失敗と明記。旧FR-090-UNKNOWN-TEXTに継続1を記録 CI157のUI新5＋旧1も同sourceで成功。実機表示は次回確認。 | 0（092表示後の実機再観測なし。判定精度の合格ではない） |
| FR-092-HARNESS-RECOVERY-TYPE | 2026-11-13 | CI154の新class7同時実行でRecoveryStatus型エラー8件 | GOLD窓試験が共有CDLLのargtypesを別の同layout型へ設定し、後続の借用helperが他型を確保。作者6＋1の別実行では順序依存を検出できなかった | 新試験だけ、署名設定と同じ型の確保を一組にする既helperへ統一。void cast/型検査緩和/旧試験変更なし | 実runnerのimport順・同processの新7件を再現しerrors8→Green7/skips0、全8拒否assertを維持。製品/8core/manifest不変、CI154はMac/IPA作成前に停止。同source-bound CI157で全30件を確認した CI155/156/157のhost30件も成功。 | 0（試験修正後の再観測なし。製品の意味Red/実機改善とは別） |
| FR-092-DELIVERY-REFERENCES | 2026-11-13 | 新selector自己試験2件とexecutor静的確認で旧版参照を検出 | 091から092の補助コード作成時に旧entry/reader名が残存 | 092 entry/step/BASE/READER/SPEC/LEDGER/schema/hashのAST照合を追加し、全assertを維持して訂正 | selector自己4Green、executor静的レビューP0/P1なし、実artifact読取/gate試行前に訂正。製品変更なし。過去FR-090/091のreader記録と照合 | 1（selector訂正後にexecutorでも旧版参照を配布前検出。製品とは別） |
| FR-092-HARNESS-STARTUP-PHASE | 2026-11-13 | CI155の起動fixtureが正常画像解析後に失敗 | 縦画像待機中の入力禁止を、正常画像からの正規PAUSEにも要求した | 正常3caseで最初のC observe直前の無入力を確認し、その後はaccepted正常sourceだけの操作を要求。禁止系の入力0は維持 | host30合格/旧Runtimeのnamed Red/現Runtimeの正常raster解析を確認。fixture30873b95を独立静的レビュー、修正後MacはCI157で確認。製品/seal不変、初版だけ事前凍結であることを明記 CI157の新9＋旧保存1で成功、最終fixture017d064a。 | 0（修正後の再観測なし。実機停止とは別） |
| FR-092-HARNESS-WALL-BUDGET | 2026-11-13 | CI156の64portrait上限試験が57取得で終了 | 模擬時計1ms/取得とHOSTのdecode/queue/50ms待機を分けず、試験側8秒が先に切れた | HOST pumpだけ30秒へ。製品3秒/64回/50msとfixtureのexact64/最終failure64/入力0を維持 | CI156の正常回復case合格・57取得/論理57ms/無入力を確認。残りcaseの時刻更新順・取消/lease/hookを静的点検。CI157で上限試験を確認。製品不変 CI157でexact64/最終failure64/入力0を含む新9＋旧保存1が成功。 | 0（試験修正後の再観測なし。製品の意味Redではない） |

## TEST093の対策（実機改善未確認）

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-093-PROJECTED-ENTRY | 2026-11-13 | 092実1/再試行で2商品だけ見えて入店前停止、のろい判定未呼出 | 開扉は成功。上端ITEM/protected投影の端と遠方材質差が旧081条件外。最初はearly lost-GOLD guard、再試行はPARTIAL一般FRESH拒否 | 観測ITEMの中心/十字1セル投影に限定した別FRESH権限へ。旧ID保持をせず全判断/保護近傍/静止/元窓を検査 | [計画](plans/test093-opened-entry.md)・[受領](reviews/test093.md)。旧071/077/081 helper/assertは保持。現保存Cで実2pairはstrict0/同判断、未保持244/245を補わない。新6単体の477版Green、P1修正後のCI159で新6＋旧8＋selector4全18が合格。実機改善未確認 | 0（新対策後の実機再観測なし。旧081継続2は旧行へ記録） |
| FR-093-INNER-FLOOR | 2026-11-13 | 092実4で開扉後に入店票を拒否 | UNKNOWNの入口奥2セルDIRT→FLOOR/遠方STONE→DIRTが旧071対角PARTIAL条件外、一般FRESHも不適格 | 同ACK開通/次FLOOR・同完全判断・GOLD/保護保持とstrict0下で軸2セル目だけを別FRESHへ | [計画](plans/test093-opened-entry.md)。FR-071-SHIELD/077-NEW-GOLD/090-THIN-IRON/091-OPEN-BLURを照合。開通成功を再発に数えず、次の未送信段階を区別。新6単体の477版Green、P1修正後のCI159で新6＋旧8＋selector4全18が合格。実機改善未確認 | 0（新対策後の実機再観測なし。別適用条件） |
| FR-093-EXPIRED-ENTRY | 2026-11-13 | 遅い入店再判断で、元窓を保つだけでは再び停止し得る | 092実4はC commitからDまで10.719539ms。旧expired回復はUNKNOWN/完全一致のみでPARTIALを扱えない | 完全一致の同開通済みPARTIAL床だけを既確実未送信回復へ追加。元visual/12秒/45秒/180秒を上限に独立した将来権限を再取得 | 元旧ID/窓/epochを延長せず、遅い実begin/complete0・独立画像/HUD/準備50ms・全拒否を新単体で確認。段階別の意味Red→477版Green、CI159全18が合格・実機改善未確認。発生済みの別停止理由とは断定しない | 未確認（現092で期限超過停止は未観測。既知の狭い残時間に対する境界対策） |
| FR-093-QUIET-PRIORITY | 2026-11-13 | 新実装の配布前レビューで旧081の同ID保持を壊す回帰を検出 | mask非zeroの時だけquiet成功が新refreshを撤回し、元sourceへ戻るmask0では新FRESHへ進む | quiet成功をmask0でも優先する1行だけを修正。旧helper/旧assert・新fixtureは維持 | 旧081のsource-mask-return1methodが意味Red fail1/errors0、修正後C ab3fe447を独立静的確認。CI159の18件で旧assertを変更せずGreenを確認。配布済み092の停止とは別 | 1（093作成中に配布前回帰を検出、実機未配布） |

## 未整理・未確定の扱い

初期版の全件と、各対策後の同原因発生回数は未整理。複数の似た停止、未収録原画、単体だけで確認した変化を、根拠なく「同原因再発」や「改善完了」に寄せない。特に旧081実5の金1→2、旧086実4の最初の拒否、未観測商品/候補見逃しの未確定は、それぞれのレビューで追う。


## TEST094の対策（実装中・実機改善未確認）

FR-088-CPU/089-KERNEL/089-EARLY/090-RING-COST/090-UNKNOWN-TEXT、候補見逃しのFR-084/085、初期画像のFR-081/091、FRESH/UNKNOWN/開扉後の旧対策を照合した。旧canonical kernel15 source・ELF・Perception閾値・旧profileを維持し、新profileの接続不足と従来の失敗を区別する。下表の「作成中」は配布前に検出した不一致で、実機改善確認ではない。

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-094-NATIVE-CYCLE | 2026-11-13 | 商品確認後の判定が本番周回へ接続しない | 旧nativeはgoodsでterminal、iSH後処理はtarget/candidate/unknownだけ | 専用cap/profileで直接RGBA分類、完全な陰性証明だけ耐久保存→再開 | [計画](plans/test094-native-goods-cycle.md)、新Controller/Runtime実callbackと実機で陰性→次商店を確認。iPhone未確認 | 未確認（旧後処理の構造不足、新経路は未配布） |
| FR-094-SHADOW-MOUTH | 2026-11-13 | 093原156の上左通路候補を見送り | 長い左壁と暗い上口が旧候補の観測床支持に入らない | 元UNKNOWNを保持し、既観測床3歩へ限定した仮説bitを追加 | [別計画](plans/test094-shadow-passage.md)、新6＋旧19のO0/strictO2。未観測先の店を推定しない、実機未確認 | 0（追加後の実機再観測なし） |
| FR-094-FAST-PROBE | 2026-11-13 | native直接化だけでは分類100msを超え得る | 低い対象scoreでも旧色差探索を全実行 | 旧kernel不変、安全上界が候補閾値未満の場合だけ新probeで省略、非exact/上界を明示 | 新数値/境界・4実画像の全23上界対照。host11〜44msはiPhone速度の合格ではない | 0（新probeの実機未確認） |
| FR-094-CLOSED-CHEST | 2026-11-13 | 宝箱も中身不明として保持する設計 | 最新対象範囲が未反映 | 閉じた宝箱を独立sprite/形状で正に識別しignored_containerへ。開封/購入/中身判定0 | 黒/紫2poseと対象/別ring交差、破損形状拒否。最新ユーザー指示に対応し、宝箱の中身をnon_targetへしない | 0（新policyの実機未確認） |
| FR-094-CERT-JOIN | 2026-11-13 | 証明rowの不一致、余剰SHOPやfull iconを誤扱い | 選択row未結合、全画面外物未列挙、brightness帯とfull template extent混同 | exact row/独立余剰列挙・全候補veto。既探索pose/全footprint/非重複/stripをControllerと共通化 | 新単体の各Red→Green、原225の実RGBA完全coverageを校正。原326/151は未判定を維持 | 作成中3件（同じrow/幾何接続段階で検出、実機未配布） |
| FR-094-SEARCH-RESTART | 2026-11-13 | 最初の見送りrestartが進まず、次floorの商品可視でもACKしない | SEARCHを陰性用保存へ接続、ACKにgoods UNKNOWNを必須化 | 陰性state/commandだけintent gate、通常SEARCHを旧経路へ。変化したFLOORのPARTIAL/VISIBLEを耐久outcome後に別levelで保持 | Cの2境界Red→GreenとRuntimeの3CLEAR見送り→候補fixture。実機未確認 | 作成中2件（新profileの別接続不一致） |
| FR-094-DECISION-EVIDENCE | 2026-11-13 | cycle profileで初期見送り/未送信拒否画像を落とす | 旧evidence profileだけを保持対象にした | 新profileにも元12判断/20terminal pinの条件と上限を適用 | Runtime fixtureで初/末判断がrecent4から退役後も残ることを確認。実機未確認 | 作成中1件（配布前レビュー） |
| FR-094-READONLY-UNKNOWN | 2026-11-13 | UNKNOWN/frozenの終了を回収できず、回復時はinput0と誤表示 | clientが入力解放と診断回収を混同、danglingintentの再構成不足 | terminal/drained/no-inflight下だけstate4も回収。未解決intentはUNKNOWN/frozenで明示し入力再開0 | 新3.9回収Red→Green、Runtime別owner回復fixture。実機未確認 | 作成中2件（parserとnative証拠再構成） |
| FR-094-JOURNAL-RENAME | 2026-11-13 | 二つのjournal更新の中断で永久回復不能 | 個別atomic write二回を一体のtransactionとして全bytes一致要求 | per-run fsync済journalを正本、activeをUUID選択mirrorとして回復 | 中断注入assert Red→Green、開始POST前の耐久intent/取消guardは維持。実機未確認 | 作成中1件（配布前レビュー） |
| FR-094-EXPORT-IDENTITY | 2026-11-13 | PNG再生成によるexport変化、壊れた回復ledger再選択、不正rangeによる全回収poison | encoded bytes未固定/弱い回復再利用/要求誤りと保存破損を同じ全体故障へ | PNGを一度耐久固定、回復は別ledgerと全hash検証。不正rangeは要求単位で拒否し全体を壊さない | 実FS/全PNG・record・ZIP・receipt、同owner/別owner再回復・壊れた旧ledger保持のMac限定fixture。実行結果は[検証](reviews/test094.md)へ | 作成中3件（別境界で検出、実機未配布） |
| FR-094-RETURN-ZIP | 2026-11-13 | stored PNG回復で返却ZIPが肥大 | ZIP_STORED固定で画像を再圧縮しない | 終了後にC zlib deflate6でstream作成、全member bytes/CRC/hash照合 | 3.9の圧縮方式/全bytes assertion Red→Green、既完成ZIPは上書き0。高entropy最大量の添付サイズ保証ではない | 作成中1件（配布前レビュー） |
| FR-094-BUILD-DEPENDENCY | 2026-11-13 | shared feature header不足・patch contextの行数不整合 | canonical feature_sha.hの依存漏れ、blank contextを再集計しない補助編集 | canonical7件をpin、固定upstream+G1へ実patch check。Ring profile3/専用API・Callback checkerを追加 | installer46 Greenと実patch check。compile失敗/構文検査を製品の意味Redには数えない。IPA実検証は別 | 作成中3件（配布前、shared header/patch行数/compiler profile binding。実機問題ではない） |
| FR-094-UNSTARTED-RECOVERY | 2026-11-13 | 準備/通知拒否後の再実行でゲームを開始できない | start_intent0のjournalも回収扱いし、認証済み未受付-32095までUNKNOWNへ丸める | 未開始と通信不明を分け、次の明示実行だけ同UUID開始。malformed/未知は旧UNKNOWN保持 | 意味Red2→実Python3.9の33 Green、暗号HTTPの保存不能-32096を誤pollしないRed1も確認。実機未確認 | 作成中2件（同じ未開始の接続段階、実機未配布） |
| FR-094-FIRST-FLOOR-GOODS | 2026-11-13 | SEARCH restart直後に商品が見えるとACK待ちのまま分類/ポーズ不可 | goods latchがnormal restart baselineを失いcapture0へ | 元ACK/prefix/4秒/指紋を保存して先にUI待ちを閉じ、変化成立だけ新level credit。未証明は保持のみ | 新4methodの6assert Red→C29＋旧11の40 Green。Runtime firstPARTIAL/VISIBLEも限定Mac fixtureへ。実機未確認 | 作成中1件（先のnegative-next-floor条件とはSEARCH側の別分岐） |
| FR-094-INITIAL-SPOOL-RECOVERY | 2026-11-13 | 初期保存故障後にspool0のままpending反復、回復ACK後も開始gateが残る | 未作成spoolのcurrentとread-only cache、current.publishedの結合漏れ | 同UUIDの停止・drain確認後にread-only診断へ。保存不能は非pending32096、回復ACKは同UUIDの停止currentにも結合 | initial file_sync故障/合成入力0/同UUID診断/ACK fixtureをMacへ追加。保存不能を正常完了とはしない、実機未確認 | 作成中2件（同じ回復の接続境界、実機未配布） |
| FR-094-HARNESS-ORIENT-LINK | 2026-11-13 | CI161 Export試験のarm64 link失敗 | 実Rasterを使う新runnerにPerception objectを入れない | 専用fixtureにも実NG2Perception.cをstrict O2でlink、4検査を独立実行 | CI161のAPI/spool成功とundefined ng2_orient_rgbaを特定。compile/link失敗は意味Redに数えず次CIで実行確認 | 0（対策後の同原因再観測なし、製品変更なし） |
| FR-094-LATE-ASSESSMENT-TEXT | 2026-11-13 | terminalだけに残る遅延判定を未実施と表示し、未採用negativeを確定扱いし得る | checkpointだけを表示しassessment_adoptedを見ない | terminalも読んで同job/captureを重複排除、未採用を明示。UNKNOWN/frozenは画像保存の完了と動作成功を分ける | 表示の意味Red1→実3.9全34 Green、実機未確認 | 作成中1件（配布前。旧FR-090/092表示と別の新profile採用状態） |
| FR-094-DRAINED-UNKNOWN | 2026-11-13 | 実行済UNKNOWNの回収をinflightとして拒否、有限試験の終了が不明 | 歴史的UNKNOWNと実callback実行中を同じ値へ投影、positiveだけ通知 | 全worker/lease/capture/main/saveの実drain後だけ専用native_inflightを閉じ、input4/frozen/global poisonを維持。terminal/drain後に一度終了通知 | 失敗fastTap→state4→drain→manifest/ACK→新start拒否の実Runtime fixtureをMacへ。旧projectionのassert Redも確認予定、実機未確認 | 作成中1件（回収projectionの接続不足、UNKNOWN再送0） |
