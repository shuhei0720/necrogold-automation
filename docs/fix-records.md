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


## TEST094の対策（配布版・実機改善未確認）

FR-088-CPU/089-KERNEL/089-EARLY/090-RING-COST/090-UNKNOWN-TEXT、候補見逃しのFR-084/085、初期画像のFR-081/091、FRESH/UNKNOWN/開扉後の旧対策を照合した。旧canonical kernel15 source・ELF・Perception閾値・旧profileを維持し、新profileの接続不足と従来の失敗を区別する。下表の「作成中」は配布前に検出した不一致で、実機改善確認ではない。

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-094-NATIVE-CYCLE | 2026-11-13 | 商品確認後の判定が本番周回へ接続しない | 旧nativeはgoodsでterminal、iSH後処理はtarget/candidate/unknownだけ | 専用cap/profileで直接RGBA分類、完全な陰性証明だけ耐久保存→再開 | [計画](plans/test094-native-goods-cycle.md)、新Controller/Runtime実callbackと実機で陰性→次商店を確認。iPhone未確認 | 未集計（094実機4回で陰性次周回未到達。FR-095-PARTIAL-DIRT等の接続段階を修正中） |
| FR-094-SHADOW-MOUTH | 2026-11-13 | 093原156の上左通路候補を見送り | 長い左壁と暗い上口が旧候補の観測床支持に入らない | 元UNKNOWNを保持し、既観測床3歩へ限定した仮説bitを追加 | [別計画](plans/test094-shadow-passage.md)、新6＋旧19のO0/strictO2。未観測先の店を推定しない、実機未確認 | 0（同原因確認0。094原146の別shape見逃しはFR-095-SPLIT-SHADOW） |
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
| FR-094-FIXTURE-CLOCK | 2026-11-13 | CI162のUNKNOWN mutationが別のintent待ちで失敗 | PAUSE観測だけで模擬時計220msを進め、pendingの分類を本来の100/150ms期限外へ飛ばす順序race | 採用済negative/statusOK/耐久checkpoint後だけ進め、parkした分類で元順序も検査。mutation単独選択、全Green11＋旧3維持 | CI162の実FAILを特定、製品の期限は不変。次Mac CIで修正後を確認、実機改善とは数えない | 0（試験側の配布前不整合、修正後再観測なし） |
| FR-094-FIXTURE-PAUSE | 2026-11-13 | CI162で陰性restartのintentに一度も到達しない | 専用HOST PAUSE描画がCONTINUEだけでRESTART文字を持たず、実parserはpause1/restart_label0 | 既RESTART maskも描く実UI相当の試験入力へ訂正し、実C parserで1/1を事前assert | 実Cの1/0→必要1/1 assertion Redを確認。Mac11＋旧3は次CI、製品閾値/条件は不変 | 0（新専用fixtureの入力不足、修正後未実行） |
| FR-094-FIXTURE-DRAIN-SAMPLE | 2026-11-13 | CI163のlease故障mutationが期待Redを検出しない | main/capture終了とterminal解放処理の終了を区別せず、後者より早く状態を検査し得る | HOST限定のterminal処理終了observerで同期し、park中workerと処理後leaseを検査。子returncodeも保存 | CI163の0-byteログとstatic順序を確認、旧returncodeは未確定。次Macで実行確認、製品の解放条件は不変 | 未確認（専用fixtureの同期不足。対策後CI未実行） |
| FR-094-FIXTURE-RESTART-MAP | 2026-11-13 | CI164のSEARCH restartが4秒で未確認終了 | GOLD除去後の試験地形は二小STONEとnoise平行移動だけで、新地形の指紋差条件を満たさない | 専用HOST generatorをSwift/実C probeで共通使用し、clear/partial/fullと指紋差を事前検査。製品の指紋/期限は維持 | CI164の26stable画像・UI ACK・指紋待ちのdiagnosticを確認。実C probe/次Macで確認し、実機成功と数えない | 未確認（新専用fixtureの地形不足、対策後CI未実行） |

TEST094最終確認: build165の限定host144・Mac Runtime新11＋旧3/API/spool/Exportと実物5検査は成功。上表のCI前の記録を履歴として残し、各対策の実機改善・再発率を確認済みへ変更しない。

## TEST095の対策（配布版・実機改善未確認）

094の4 ZIP/82 PNGを全照合し、FR-094-SHADOW、FR-083-LOWER-GOODS、FR-081-REFRESH、FR-085-CLEAR-STATIC、FR-090/091/092静止/移動証明、FR-094-CERT-JOINと照合した。旧対策を改善完了と扱わず、同じ症状でも適用外/別原因を区別する。

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-095-SPLIT-SHADOW | 2026-11-13 | 094実1原146の上左通路候補を見送り | 旧094長壁と異なる、分断された屋根/暗い曲がり口の条件がない | 観測支持と安全床3歩を必要とするbit0の有限仮説 | 新6＋旧25のO0/strictO2、原Sceneのmaskだけ変更。店の存在/実機到達は未確認 | 初観測1（旧長壁条件の同原因再発ではない） |
| FR-095-PARTIAL-DIRT | 2026-11-13 | 094実2/4で開扉・商品一部可視後に停止 | 正常判定後の継続で遠方DIRT変化まで全地図一致を要求 | 同判断/全保護/strict0を保持し、経路3×3外のDIRT→FLOOR/UNKNOWNだけ確認 | 意味Red2→新5＋旧29 Green、保持Sceneでfalse→true。未収録先の全商品/実機改善は未確認 | 同原因2（095対策後の実機は未実施） |
| FR-095-SINGLETON-ZERO | 2026-11-13 | 094実3で2歩後の未送信UPを再取得できず終了 | 固定元129の旧STONE1個は旧2STONE/2GOLD静止証明の適用外 | 確実未送信通路待機だけ、旧STONE1＋非共線DIRT9/unique9＋全強画素条件で別zero証明 | [限定計画](plans/test095-device-stops.md)。既知Motion/UNKNOWN/保護/各期限の拒否と作者Red→Green、実機未確認 | 初観測1（旧090/091unit・092GOLDzeroの同原因再発ではない） |
| FR-095-TARGET-ONLY | 2026-11-13 | 対象外の未登録品で周回が止まり、商品辞書の追加が必要になる | のろいのゆびわだけを探す要件に対し全商品識別を陰性の前提にした | 追加catalogを撤回。有限商品帯の主画像全探索と候補保持のpolicy2へ変更 | [計画](plans/test095-target-only.md)。新判定13/Controller5・関連回帰・Mac4と意味mutationが成功、実機未確認 | 初観測1（設計の変更。実機改善済みとはしない） |
| FR-095-RETURN-LABEL | 2026-11-13 | 新試験の保存/ZIP名が094のまま | 旧専用entryとprefixの固定文字列 | 095 entryと専用spool、厳格test-数字3桁のみラベル採用。旧default/回復は保持 | 意味assert Red1→実Python3.9の新3＋旧34 Green、通信とnative入力は不変 | 0（配布前のラベル対応、実機未確認） |
| FR-095-TARGET-WORD-VETO | 2026-11-13 | 作成中の対象だけ判定で、強い対象名が別の文字候補やpartial置換に隠れ得る | IoU最大とcoverage条件の順序、旧partial内の同じ順序を保持した | mode2の完全観測文字は両閾値を満たす配置を先に選び、元row/partialの対象情報を置換前に保持 | 交差する二文字候補・旧partialを合わせたassert Red→Greenと独立レビュー。実機未確認 | 作成中の対策後に同系統の残存1件を検出し修正（対策後実機未確認） |
| FR-095-FIXTURE-SHOP-COUNT | 2026-11-13 | CI167の新しい周回fixtureが商店数で失敗 | 陰性店だけを数える期待1にしたが、既契約は次の候補店も数え2 | 旧094同等fixture/Controllerと照合して期待2へ修正。他の入力/耐久/保持条件は維持 | CI167ログと独立レビューで確認、CI168の同一source Macで成功。製品変更なし | 0（新fixtureの誤期待。実機改善とは数えない） |
| FR-095-READER-WORKER | 2026-11-13 | 私有Mach-O検査が正常なIPAを拒否 | worker専用の新2文字列をmain hostにも必須とした | 実compileの所属に合わせ、基本7は両方、新2はworkerへ限定。9バイナリ/672禁止markerは維持 | 独立レビュー後、Mach-Oだけ第2試行。製品・IPA・合格済み3検査は不変 | 0（配布検査の初回誤り。製品不具合ではない） |

TEST095最終確認: build168の選択host205・現sourceのMac接続試験・実物5検査は成功。対策後の実機改善や再発率を確認済みへ変更しない。

## TEST096の対策（配布版・実機改善未確認）

095の3ZIP/61PNGを全照合。実順は添付3→1→2。FR079-GOLD-REVEAL/FR081-SIDE-GATE、FR095-PARTIAL-DIRT/SINGLETON-ZERO、FR094-NATIVE-CYCLE/CERT-JOINと照合。branchが違うだけで別根因とせず、適用外・残存・回帰を区別する。

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-096-REVEALED-TURN | 2026-11-13 | 095実1/2の5入力目は1歩移動済みなのに8比較UNKNOWN停止 | 金壁/扉の新露出を証明する旧幾何が存続STONE2個に依存 | 旧金・旧STONE1以上・非共線DIRTと、既十分な独立画素面を組み合わせる限定証明を追加。閾値/比較上限を下げず未知入力再送0 | [計画](plans/test096-walk-cycle-repair.md)。各原画像1回の校正・保持SceneでMOVED、作者Red→Greenと現CIの関連回帰が成功。実機改善未確認 | 同系列2を今回確認。旧FR079/081からの通算は未集計。旧条件削除による回帰の証拠なし |
| FR-096-PAUSE-ADOPTION | 2026-11-13 | 095実3の判定は20.6msで終わるが採用期限切れ | 同期PAUSE約275msがcontrolQueueを占有、採用が約188ms遅れる。旧模擬入力に実遅延がない | 元100/150ms内の分類待ちだけticket発行前にtick順序を調整。失効/取消/予算超過は待たない | 実275msに対応する有限時計/同期待ちのMac Red→Greenを追加。計算終了時刻へ遡及せず、実機改善未確認 | 今回1を確認。094導入の結合条件漏れ、旧対策を完了扱いしない |
| FR-096-SHOP-AUTH | 2026-11-13 | 095実3の商品が見えても対象帯探索へ進まない | SHOP固定画素例に加え商人2画素例も描画差で不成立 | 全商品登録を増やさず、完全な商品帯と観測金壁/看板/価格の構造を認証する別proof3へ変更。余剰物は有界の診断だけとし対象の全探索は不変 | 原288の既glyph結果と商人1回・Scene1回校正。旧閾値を下げる/1画像だけ追加する対策は不採用。実機未確認 | 今回1を確認。既認証の未対応描画条件が残存 |
| FR-096-EXTRA-SIGN | 2026-11-13 | 作成中の証明3が48pxの余剰看板を見落とす | 選択看板用36px ROIの制限を余剰看板にも流用 | 既canonical18〜48pxの全余剰SIGNを数える。選択2面の完全ROI要件は維持 | 作者の反例Red→Green、独立した差分確認。旧経路/主探索は不変、実機未確認 | 0（未配布で検出。製品の実機再発率とはしない） |
| FR-096-FIXTURE-CLOCK | 2026-11-13 | CI170で陰性→再開→次候補の採用後、試験終了のPAUSEを待ち続ける | 試験時計がRESTART後34msしか進まず、既存200msのUI待機を満たさない | 095の既存helper同様、次候補の採用成功後だけ一度220ms進める。製品source/期限/assertは不変 | 原diagnosticと独立レビューで確認。旧Runtimeの意味Redと現Runtime最初の候補成功は保存。修正後12callbackを次CIで確認、製品の意味Redや実機成功には数えない | 0（新fixtureの時計不足、実機不具合ではない） |

TEST096最終確認: build171の限定host134、現Mac API/spool/Export・Runtime12と旧source意味Red、実物5種類が成功。FR-096-FIXTURE-CLOCKは製品不変で訂正後、次候補PAUSEまで成功。各対策の実機改善や再発率を確認済みへ変更しない。

## TEST097の対策（配布版・実機改善未確認）

096の4ZIP/85PNGを全照合。実順bc239→e503→4b8→6f62。過去の対策を除外せず照合し、旧条件が残っていても新周回経路への接続不足を残存として扱う。

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-097-MOUTH | 2026-11-13 | 実1の028/052、実4の130/254の候補を見送り | 旧094/095のUNKNOWN/壁列固定条件が、内側床の露出・暗い壁の欠落・斜め外床の口を扱わない | 2種類の有限観測口と既観測床vantageを追加。旧口/chooserと未観測セルの意味は維持 | 旧mask0を確認し、意味Red→新8＋旧31 Green。保持Sceneの最終mask1/32/1/1。未知精度・実機改善未確認 | 同系列4。旧候補対策の削除なし、通算は未集計 |
| FR-097-APPROACH-MOTION | 2026-11-13 | 実1の送信済UPをUNKNOWN8回 | 金1を保持する接近で下帯/旧world等の支持不足。096金1→2の側方入口証明は適用外 | 旧正支持/一意投影とraw・Sparse・signed-axisの独立ANDを追加。旧閾値/期限/比較回数は維持 | 原178/196各1回校正、公開Cの意味Red→新8＋旧24 Green。保持SceneでMOVED/UP1、実機改善未確認 | 移動判定系列1を今回確認。同じ096新証明の再発とは未確定 |
| FR-097-PARTIAL-RELATION | 2026-11-13 | 実3/4で部分判定後、商品可視へ進めず停止 | 実3は既開扉のshielded対角DIRT→FLOOR、実4は遠方STONE→DIRTが旧cycle095材質条件外 | 同完全判断/全保護/厳密零/元期限を保持して、旧071等の正当な材質関係をcycleへ限定接続 | 176→178/414→416の失敗predicateを分離。意味Red→新7 Green、全Controller55と保持Sceneの両relation成功。未来到達は未確認 | 遠方/開扉後の材質差拒否系列2が残存。FR095と照合、通算は未集計 |
| FR-097-CLIPPED-PARTIAL | 2026-11-13 | 実2は開扉後、商品slot0件で保持 | 上端でSHOPが切れてpartial adapterが実在商品を抽出できない。空結果は既契約どおり保持 | 空を安全/陰性へ変えず、実ACK済みUP開扉・観測床・正の上端ITEM/保護・既可視部の新規遮蔽なし・独立静止の別framing権限で1入力だけ接近 | 原167の保存Sceneと包絡を確認。意味Red8→Green8、引継ぎ反例を追加。独立した未来画像/到達は未収録、実機未確認 | 今回1を確認。前回PAUSE採用遅延の再発ではない |
| FR-097-CANDIDATE-ROOF | 2026-11-13 | 作成中の新候補Aが旧095の転置拒否を破る | 屋根2セルだけでは両方が口の近側に偏る場合を区別しない | 対岸の遠側x=1/2にも正の壁支持を必要にする。旧assertを維持 | 旧095の両profile失敗と新near-only反例Redを保存、条件強化後に新8＋旧31 Green | 作成中1（配布前検出、実機再発ではない） |
| FR-097-FRAMING-FULL | 2026-11-13 | 作成中framing待機中に新FULLが来ても旧空結果のまま保持 | OBSERVE_MOREのfull_seen guardが、新しい正常な分類jobへの引継ぎを欠く。初期案にはFLOOR条件も不足 | privateframing・入力0・独立した新FULL/FLOOR・current prefixだけ既cycle_latch/bindへ。旧移動権限は撤回し、新sourceの分類だけ開始 | 引継ぎの意味Red1→Green9。レビューで非FLOOR/FULL反例も追加。元ticket/旧jobの拒否、既予約後FULLの旧経路は維持 | 作成中2（引継ぎとFLOOR条件、実機再発ではない） |

TEST097最終確認: build173の選択137件/17scope、現Mac API/spool/Export・Runtime096の12callbackと旧source意味Red、実物5種類が成功。保持SceneのNav/Controller校正も成立。実機到達・見逃し率・未知対象精度は未確認で、各対策の実機改善や再発率を確認済みへ変更しない。

## TEST098の対策（配布版・実機改善未確認）

097の3ZIP/64PNGを全照合。実順は添付1→3→2。FR-095-PARTIAL-DIRT、FR-097-PARTIAL-RELATION/FRAMING-FULL、FR-079/081/090/093の未送信回復、FR-084/086/094/095/097候補を照合。旧条件の削除・PAUSE採用遅延の再発とは断定しない。

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-098-SOLID-CORNER | 2026-11-14 | 実2の候補135を見送り | 旧口は5壁で塞がる上左角の外床を扱わない | 5壁/外床/中央床/既3歩vantageを必要とするbit5仮説。壁/UNKNOWNの意味は不変 | 意味Red→新6＋旧39 Green、原Sceneでmask32/既床4歩。未来到達・未知精度は未確認 | 同系列1。旧対策削除なし、通算未集計 |
| FR-098-SIDE-OPENING | 2026-11-14 | 実3が6歩後、新しい側方床を前に停止 | 一セルDIRT→FLOORで未送信DOWNからLEFTへ完全判断変更。旧monotone/同判断refreshの適用外 | 厳密零/同GOLD/保護なし/直交reason8だけ別refresh。旧票撤回、新判断anchor固定、新IDと独立画像、元期限維持 | 意味Red→新8＋旧14 Green。保持221→223の新admission成立。最後の診断guard後の全同sourceを最終選択CIで確認、実機未確認 | 今回1。移動UNKNOWNや旧未送信回復の同原因再発と未確定 |
| FR-098-OPENED-FADE | 2026-11-14 | 実2が開扉後、下の商品へ進めず停止 | 遠方(5,4)FLOOR→UNKNOWNが旧材質関係外 | 実ACK済み同方向開扉/reason5/両3×3外・非保護だけ追加。同判断/厳密零/元期限維持 | 意味Red→部分新9と関連、原297→299で関係成立。未収録先の商品/実機は未確認 | 開扉後材質拒否系列1が残存。通算未集計 |
| FR-098-PARTIAL-REACQUIRE | 2026-11-14 | 実1が商品一部表示後に停止し次周回へ進まない | 再解析で継続許可後のrelation拒否と特定。失敗画像未保持のため内側の拒否条件は未確定 | 098のUNKNOWN待機/拒否記録は手前のOBSERVE_MOREだけで、実際の停止分岐には未接続。原不具合は未解決。原因不明のまま追加の挙動変更なし | 初回許可成功を回復count/旧Cで照合、prefix/期限を除外。原234→後242は正常で失敗再現ではない。独立した静的確認済み、実機未確認 | 同症状1、同原因再発数は不明（0にしない） |
| FR-098-DIAGNOSTIC-ZERO | 2026-11-14 | 新診断の材質差0を回収clientが拒否。レビューで非MOTIONの0行も検出 | 既schemaはmask1..15。新producerとparserの限定条件が不一致 | 現API rootの同ID/MOTION detail・全変化0・権限0だけ認める。非MOTION/mask0は記録せずfirst印を残す。legacy/再帰は厳格 | 実Python3.9の意味Red→新2＋旧3 Green。非MOTION反例Red→新9＋既C診断3 Green、独立レビューGO | 配布前2境界を検出。実機再発ではない |

TEST098最終確認: build175の現source選択116件/21scope、現Mac API/spool/Export・Runtime096の12callbackと旧source意味Red、実物5種類が成功。旧作者の側方22は訂正前C版、最終版は今回CIの新8＋旧14を根拠にする。保持Sceneの候補/側方/部分関係は成立。実1最初の停止原因は未確定。実機到達・見逃し率・速度・未知精度/各対策の再発率を確認済みへ変更しない。

## TEST098のiSH回収修正（実機回収改善未確認）

FR094の回収/出版/未開始回復、旧HTTP transport上限と照合。画像の撮影・歩行停止とは別の、回収時のエラーを扱う。IPA175/native・ゲーム挙動・指輪判定は不変。

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-098-HTTP-BULK | 2026-11-14 | 前run回収0/18枚の後にhttp_body_limit終了 | batch/manifestのHTTP512KiB制限が、内側base64のJSONスラッシュescapeと暗号化base64の増大を含めない。実機で超過したmode/応答本体は未取得 | batch/manifestだけ有限1MiBへ。single256KiB/他512KiB・MAC/ID/schema/hash/同run/prefix/期限を維持 | 実3.9の正常PNG4chunk暗号応答933,627Bで同エラーをassert Red2→Green。ヘッダでの上限拒否/MAC失敗も確認。全選択46件成功、実機の同run回収は未確認 | 今回1。同原因の旧版通算未集計 |
| FR-098-RECOVERY-ONLY | 2026-11-14 | 回収を明示しても、元runが公開済み/記録なしなら通常実行が新UUIDを開始し得る | 既run()は通常試験として次runへ進む仕様で、回収専用の入力経路がない | --recoveryは既device lock内で開始済みjournalを要求。未完了は同UUID/keepalive=false、公開済みは元receipt/ZIP検証後に同ZIPだけ再保存 | 実3.9の新5でassert Red3→Green、旧3関連も成功。元記録なし/未開始/公開済み/receipt欠落を確認。実機未確認 | 配布前の安全境界追加。実機再発数ではない |
| FR-098-SOURCE-UPLOAD | 2026-11-14 | 検証済みsourceの直接asset uploadが401で失敗 | 通常GitHub APIの保存は成功するがupload先の認証は成立していない。認証不成立の詳細は未取得 | 固定source/hash/空draft/tagだけを扱うGitHub側dispatch jobのcontents:write認証で配布。新IPA/製品変更なし | 凍結source835ファイル全照合、workflow YAML/Python構文・独立静的レビューと、公開後の匿名全GET/hash/tagを確認 | 今回1（配布経路のみ、実機の製品不具合と別） |

TEST098回収修正の公開確認: 元IPA175/nativeは不変。実Python3.9の46件、固定source835ファイルの全bytes/CRC、公開run43601345465、固定tag/匿名HTTP200/両asset hash一致を確認。実機での回収改善・元の歩行停止解消は未確認。

## TEST099の対策（配布済み・実機改善未確認）

098の全回収1runを確認した。FR098のHTTP回収はこの18PNG/20recordで完了を確認し、普遍的な改善完了とはしない。原097/098の停止は内側の拒否条件が未確定で、推測による許可条件/期限の緩和は行わない。

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-099-STOP-EVIDENCE | 2026-11-15 | 098の通路停止、097実1の継続許可後の停止で判断条件と原画像を特定できない | 既診断は途中分岐に届かず、cleanup後の画像だけが残る。待機kind/anchor/直近比較の情報がない | 別getterの初回停止snapshot/live待機anchorとcycle限定の有限画像保持。post-creditも内側の失敗条件を残す。歩行条件/旧停止は変えない | build183の新C/Mac成功、099実機3runで初回snapshot/全参照画像を照合し100の原因分析に使用。診断の3例成立と原停止改善を区別する | 採証不足2経路を確認。停止根因の同原因再発数は不明 |
| FR-099-HANDOFF | 2026-11-15 | 本番に近い周回を望むが旧試験は4商店/12restart等で終了する | 有限runの上限だけを外すと、残存NEGATIVEや別LIMITから危険な再開を作り得る | 元予算を保ち、正常陰性/確認済み新level見送りの2分岐だけで資格を凍結。実PAUSE/全drain/全回収/公開ACK後に通常の新UUIDへ | C正常A/B・過去陰性・新候補/UNKNOWN/取消/他LIMITの拒否、該当Mac接続を確認予定。実機未確認 | 対象範囲の拡張。実機再発ではない |
| FR-099-CAMPAIGN | 2026-11-15 | 複数runを手動で開始/返却する負担、crash後の公開済みjournalから新runを飛ばす危険 | 通常publication.runは公開済みjournalなら新UUIDを作る。campaignの索引/次intentがない | publishedでも先にrecovery_onlyで照合し、原子的な索引/次intentと元UUIDを突き合わせる。各run原本を保持し、索引＋最後のrunを返却ZIPにする | 実3.9の開始/停止/採用/中断/再回収/ZIPの意味Red→Green予定。入力不明は無再送。実機未確認 | 新機能の安全境界。実機再発ではない |
| FR-099-REVIEW-PROOF | 2026-11-15 | 配布前レビューでPNG未登録のhandoff参照と回復後pending残留を検出 | frame集合とmanifest画像集合の非対称、既索引rowの早期returnでpending解除を省略 | handoff参照を登録PNG/raw SHA/3画像同世代へ限定し、既row/ZIP/証明の一致後にpending印だけ解除 | 実3.9の追加3方法/5assert Red・エラー0→同3 Green、狭い差分レビューPASS。回復専用で次start0。最終22は配布CIへ、実機未確認 | 配布前2境界。実機再発ではない |
| FR-099-FIXTURE-OBSERVATION | 2026-11-15 | CI178の新snapshot試験が停止 | 未確定stopのobserved IDを0と誤想定。getterは実PAUSE観測IDを返す | checkpoint自身のPAUSE ID/登録画像/同jobと照合し、後のoverrideとの相違を要求。製品bytes不変 | 実Mac179の1case診断で7条件中0期待だけfalse（実2/後6）。他6条件維持、訂正後7caseは最終CIへ。製品不具合や意味Redに数えない | 1（新fixture、実機とは別） |
| FR-099-FIXTURE-RESTART-CLOCK | 2026-11-15 | CI180で新連続試験の2店目がPAUSE前に待機 | 模擬時計が実RESTART ACK後13.749msしか進まず、旧200ms UI待機を満たさない。PAUSE保存後だけ進めるfixtureの循環待ち | 実ACK/新level/同prefix/採用済み陰性に結ぶ一度の220ms進行。製品の期限・assert不変 | 元diagnosticを照合。残り3caseを独立Macで先に確認し、最終7caseを次IPAへ結合。実機不具合/製品Redと別 | FR-096-FIXTURE-CLOCK同種の新fixtureで1。旧対策の削除/回帰とは別 |
| FR-099-FIXTURE-HEARTBEAT | 2026-11-15 | CI181のclear-search試験がrestart7で停止 | 模擬時計を進めるがclientの接続維持を送らず、旧5秒watchdogが正しく停止 | 既認証status keepalive:trueを模擬時計1秒ごとに成功確認。製品/watchdog/期限は不変 | 原diagnosticで経過約5秒/heartbeat19を確認。negative callbackは実PASS、残り3を限定再確認 | 1（新fixtureのclientモデル不足、実機不具合ではない） |

TEST099最終確認: build182の残り3、同codeのbuild183でhost85・現Mac API/spool/export・Runtime096の12・099の7とIPA/実物5種類が成功。fixtureの誤想定/模擬時計/keepaliveは元assertと製品を保持して訂正した。配布readerの2つのrepo保持path不一致は狭く訂正し、package既PASSを再利用、5検査6attempt。各対策の実機改善・到達率・速度・未知対象精度・原停止の原因確定には読み替えない。

## TEST100の対策（配布版・実機改善未確認）

099の3run/73PNG/81recordは全照合。実順13e3→3444→9c66、campaignと個別ZIPは同じ3実行。FR-093/095/097/098の開扉・partial関係、FR-096構造証明、FR-084/086/094/095/097/098候補を照合した。旧対策の削除・回帰と断定せず、原因が分かった境界を限定修正する。[計画](plans/test100-observed-shop-stops.md)。

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-100-OPENED-GOLD | 2026-11-15 | 実1が開扉後、商品全部を見ず停止 | 232→233の遠方DOOR→GOLDが既opened-entry関係外。同Decision/静止/期限内でもFLOOR拒否 | cycle限定・実同方向開扉ACK・両3×3外・非保護・金bracketだけ正の壁再観測を追加。旧profile/旧期限保持 | 公開Cの意味Red→新7、旧拒否/元画像校正/関連回帰を最終同sourceで確認。実機未確認 | 新材質差1。旧開扉停止系列の同原因通算不明 |
| FR-100-PARTIAL-REBIND | 2026-11-15 | 実3が新商品露出後に停止 | 223→225の新ITEM/保護増加を旧partial静止関係で拒否。旧結果は新商品を覆わない | 旧証明/票を撤回し、strict零・同prefix/位置・safe床・単調remote新商品だけ最新sourceの新jobへ。元horizon/一度限り維持 | 意味Red→新6、新job/旧結果拒否・候補保持/元期限。限定Macで最新RGBAの通常worker受渡しを確認。実機未確認 | 同症状1。FR098未確定停止との同原因は断定不可 |
| FR-100-SIDE-SHOP | 2026-11-15 | 実2は3商品可視でもUNKNOWN停止 | glyph証明不成立、既policy3は下側金構造を要求し、側面入口下の7金形に非対応。剣先1pixelも旧価格群へ入る | 別policy4/board4で7位置/3ITEM/cap/faceと独立C再検証、共通価格baselineと真の4群拒否。旧1〜3/対象全探索は保持 | 原456旧/新各1回・UNKNOWN→完全陰性、host40.9ms/元100ms。新9/関連25・C偽造拒否を確認、実機の完全経路速度未確認 | 確認した新形1。過去UNKNOWN全部と同原因にはしない |
| FR-100-LOWER-FRINGE | 2026-11-15 | 実2の候補59を見送り | 左下口DIRTにより旧mouth候補から除外。外側床と短い内床経路は観測済み | 固定bit9の別fringe仮説だけ追加、DIRT/UNKNOWN維持・観測床vantageで再確認 | 意味Red→新6/関連45、保持Scene59 mask512/既床4歩。外床接続fixtureは旧bit7=128を保つ期待へ訂正、旧assert削除なし。実機未確認 | 同系列1。旧上左候補とは別の固定口 |
| FR-100-MAC-PREPARE | 2026-11-15 | Mac185が対象callback前の起動で拒否 | fixtureに通常prepare/ready待ちがない。通知準備前guardはsourceで確認、元error本体は未収録 | fixtureだけ通常prepare待ちとRPC error診断を追加。元assert/製品guard保持 | 185は対象意味Redなし。186で同じ限定caseの旧C named assertion Red/現C Greenが成功。通常workerへ最新画像Bが渡り旧job採用拒否/候補保持/input0/元horizon保持を確認 | 新fixture1。実機不具合や製品Redではない |

## TEST101の対策（配布前検証済み・実機改善未確認）

FR-083のfirst-gold、FR-093の上端投影、FR-095/097/098のpartial継続、FR-099採証、FR-100増加時再分類/側面形を修正前に照合。似た停止を同原因と決めず、100で過去成功を破壊したとの証明も未確認。単体/CIの成功で実機改善完了にしない。

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-101-TOP-ALIAS | 2026-11-15 | 100実2で部分判定後に商品可視のまま停止 | 546→549の上端代替ITEM投影縮退がcycle creditの同一材質条件外。下段実商品/近傍/判断/strict零は保持 | 下段と重複した上端別名の限定縮退関係。旧新商品増加/空framingは保持 | 公開C Red→Green、credit後の後続縮退から将来票までと保持済み下段商品/保護喪失反例を確認。最終同CODE選択98件に結合。実機未確認 | 確認した縮退1。旧上端系列のcycle未接続、通算未集計 |
| FR-101-FIRST-GOLD-PHASE | 2026-11-15 | 100実1が金壁露出直後、実ACK後に停止 | 528→553でraw次点が片phase帯135画素となり旧first-goldのfinite guardを拒否。他の正の一意移動証明は成立 | 旧段不変の別supported-phase証明、有限zero/単位支持/全raw/world競合を要求 | 公開LEFT/内部4方向・拒否・旧関連成功、原528→553を1回校正して旧UNKNOWN/新MOVED(-1,0)。最終同CODE選択CI成功。元欠損4枚のquiet根因は未確定、実機未確認 | 今回1。099から同motion bytesで継続した別支持条件 |
| FR-101-FULL-OBSERVE | 2026-11-15 | 100実3は商品可視でもUNKNOWN停止 | 右cap実遮蔽と2セル下の側面開口で完全陰性未成立、FULL後に追加観測する権限がない | 候補なし/新static/観測床/全potential ROI保存下だけ新しい局所MOVE1回。旧ACK17無加点、実MOVED後だけ最新job | 公開Cの一連・期限/候補/UNKNOWN/一度限り/partial後保持が成功。Mac191で通常dispatch→実MOVED→最新immutable worker→候補保持/input0。元217陰性不可/旧ACK17無加点、実機未確認 | 確認した未対応形1。旧開扉停止と同原因にはしない |
| FR-101-LOWER-GATE | 2026-11-15 | 同商店の開口offsetが旧3/4の形に入らない | 商品列より2セル下の側面開口。右capはまだUNKNOWN | 別policy5の12正GOLD位置と両cap/全pixelの完全証明。Controllerが独立再検証 | Ring新6＋関連34、Controllerの独立12位置/cap/数値証明・旧3/4保持が成功。最終CI成功、元217のUNKNOWN保持。実機/未知配置精度は未受入 | 確認した別形1。未知配置精度は未受入 |
| FR-101-UNSENT-SOURCE | 2026-11-15 | 100実1の最初の再取得で元436がなく空拍の内側原因を特定できない | 既coherent helperは原pairを照合するがobserved437だけ優先保持 | cycleだけ原sourceを任意1枚追加、旧priorityが満杯なら任意sourceを退役、24上限保持 | Mac191で通常保持/spool/export/hash、両pin経路の後着旧priority、24上限、旧profile20、満杯のmissing診断成功。採証を歩行改善としない | 元436不足1。後続462/488/502も欠損、個別根因未確定 |
| FR-101-MAC-CLOCK | 2026-11-15 | Mac189の現framingがACK後400captureでも先へ進まない | 試験時計をcontrol tick hookだけで進め、input3/capture待機中は呼ばれずtarget+80ms前のまま | fixtureだけcapture admission前へ時計進行を移し、最初のUNKNOWNと次のperiod/10を区別。製品の期限/待機guardは保持 | 189の失敗原本を保持。fixture時計のcapture admission前進行とUNKNOWN後period/10を訂正し、ACK telemetry訂正と合わせ191同限定scope成功。製品/実機改善の証明にしない | 新fixture1。ゲーム側の再発ではない |
| FR-101-MAC-ACK-ENUM | 2026-11-15 | Mac190も新MOVE ACK後の時計条件に入らない | fixtureがcomplete API引数のACK1とevent記録状態2を混同し、ack_prefixを更新しない。189分析ではこの条件を確認しきれていなかった | API結果1と実完了状態からtelemetryを記録、診断へack_prefixを追加。製品APIは不変 | 190の失敗原本/API値域/event ACKを照合しfixtureだけ訂正。191の限定同scope成功。190を成功へ書き換えない | 同じ試験停滞を190で継続観測。混同を新たに1箇所特定 |
| FR-101-CI-BASELINE | 2026-11-15 | 実機CIの開始前source同一性確認が失敗する条件をレビューで検出 | 新規test_device_ci101.pyを、存在しない旧b731の保存対象へ追加した | 旧test_device_ci100.pyを保存対象に戻し、新101は現fixtureとして別結合 | 全157保存pathのbaseline存在/現bytes一致、metadata6と最終同CODEの98件/19scope成功。旧assert保持 | 実行前1検出。製品や実機の再発ではない |
| FR-101-DELIVERY-PASS | 2026-11-15 | IPA照合のretained gateがMac Greenログで拒否 | readerが全体PASS1行だけを想定し個別2行を許容しない | 凍結元Swiftから個別2＋全体1の宣言を取り、正確な順序/末尾/無FAILを照合 | 独立静的確認後、passed2gateを再利用しfailed/未実施のみresume。5種類成功、試験/compile/分類の追加0 | 配布補助1。製品/実機の再発ではない |

## TEST102の修正（CI・配布前照合済み、実機不合格継続）

TEST101の2run全原本を照合し、FR-097/098/100/101を修正前に確認。旧assertや安全境界を一律に削除せず、実配置の正の観測根拠と保護対象を区別する。[受領・検証](reviews/test102.md)。

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-102-CORRIDOR-FRAMING | 2026-11-15 | 101実1で鉄扉を開けた後、入店せず停止 | ITEMはrow-4だけで097空framingのrow-5必須を満たさずUNKNOWN保持 | 安全な観測床と商品候補領域の保存を証明する継続を実装。陰性化/旧assert削除なし | 原152の条件付きadmission校正、初回8＋episode12を含む最終C41成功。未来像は手続き的、実機未確認 | 開扉後停止の現象再観測1。同根因の旧版通算は未集計 |
| FR-102-NEAR-ITEM-FRAMING | 2026-11-15 | 101実2で商品可視でも次周回へ進まない | 商品UNKNOWN後の追加LEFTは非保護床だが、到着セル隣接の既保護セルを再度広げて拒否 | 観測一歩の実footprintと商品領域保存を実装。候補/未観測保持、旧18無加点/無再送を維持 | 原254と上界/履歴/保護を照合、新footprint4を含む最終C41成功。実結果の完全陰性もC採用。実機未確認 | 商品UNKNOWN保持の現象再観測1。101FULL後の別拒否境界で同原因通算未集計 |
| FR-102-BOARD-BASELINE | 2026-11-15 | 同じ101実2の商品が見えても完全陰性にならない | 下壁の正DOORが旧GOLD構造外、右看板の上側欠損で中心Y差5が旧2以内に入らない独立2条件 | 別policy6で12固定GOLD/正DOORと、完全anchor・同幅・共通底辺の有限証明を実装。旧価格/cap/全対象探索とC独立再検証は維持 | 原診断1回で原因を確認。新12＋関連27成功、原254の新通常分類1回が完全陰性（全対象探索/強語veto）。cached実Resultをpublic Cも採用。実機改善未確認 | 実2の別境界1。同じrunを追加実行数へ数えず、旧UNKNOWN通算未集計 |
| FR-102-ENTRY-EPISODE | 2026-11-15 | 配布前にAの一歩後も不明なら再度止まる設計不足を確認 | row-3の旧条件外/隣接保護/水平履歴に加え、新jobで最初の親期限を明示保存していない。候補上端13はまだpause HUD内の可能性 | 新102通路だけ最大2入力、親期限/領域/level/IDを保持し毎回最新判定/static/実MOVED。二歩後/商品不明は保持、旧一度限り経路は維持 | 追加計画/状態案GO、親期限/不明後の二歩目を意味Redで確認。新29＋関連12の最終41成功、親/二入力/候補/未知保持と正規UIまで確認。実機未確認 | 追加設計1。未来像は未収録で実機の同原因再発数は未確認 |
| FR-102-ENTRY-NEGATIVE-JOIN | 2026-11-15 | 追加episodeの通常完全陰性がHELDへ落ちる | default-denyのepisode結果処理が既存のNEGATIVE_PAUSEへ戻さない | 正常な独立証明済み陰性だけ既存の保存/intent/UIへ渡す | 普通のRing producerの実ResultでHELD7をassert Red、修正後はPAUSE/durable/intent/restart実ACK/新floor成功。最終41成功、実機未確認 | 追加実装中1。実機再発ではない |
| FR-102-ENTRY-PENDING | 2026-11-15 | 判定中FULLで旧対象結果を失う、入力親期限で正常workerも破棄する条件をレビューで検出 | 適格性検査前のjob/state更新と安全検査前のqueue再bind、MOVE親期限とworker期限の順序混同 | pendingのFIFO/旧候補優先、UNKNOWN全上界/強語検査、元worker期限保持。親失効は追加MOVE/再queueを禁止 | HOLD/ASSESS・対象/候補・不適格FULL・上界/強語・親失効の意味Red→限定修正→対象3 method成功。独立修正確認GO、最終41成功、実機未確認 | pending保全のレビュー検出1。実機再発ではない |

TEST102検証追記: DEVICE194/run43675514954、CODE0efbbf31で選択86件/16scope・IPA作成・実物5gate成功。FR-102各行の実機改善は未確認のまま。実機の再発数を0へ戻さず、単体試験成功を改善完了にしない。

## TEST103の対策（変更部確認済み・実機未確認）

FR-076/082の未送信静止、FR-066/084のicon、FR-100/101/102の完全判定/観測継続/陰性再開を修正前に照合。同症状でも今回の原因を区別する。TEST102の1店目は実陰性→次floorまで成功したが、配置全体の改善完了にはしない。

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-103-CLEAR-STILL | 2026-11-15 | 左2歩後、未送信待機で停止 | 141→149静止のnormal motionがUNKNOWN、旧CLEAR補助はSTONE1個だけで原配置の2個に未対応。回復期限は未失効 | 旧proofを保持し、元anchor/world/期限内の未送信待機へ別plural資格。物理zero/raw/world/axisと唯一unit blur競合の支持≥300を全積要求 | 固定原Sceneの限定診断、意味Red/変更部と関連回帰。実機未確認 | 今回1。旧静止UNKNOWNと同根因通算は未集計 |
| FR-103-ACK-OCCLUSION | 2026-11-15 | 商品表示後、判定前にscreen停止 | ACK済UP確認中のicon一時遮蔽でUNKNOWNとなり即終了。36.896ms後の原画は既floor条件成立 | 旧位相資格を撤回し同MOVE/元visualDの無入力待機を継続。次の通常FLOORだけ確認、閾値/ACK再送禁止を維持 | 状態全述語のpurepixel診断、public Cの待機/期限/取消/PAUSE/prefix/新入力0。実機未確認 | 今回1。FR066/084は同判定段階だが別遮蔽、同根因通算未確定 |
| FR-103-SAME-ROW-SHOP | 2026-11-15 | 全商品可視でもUNKNOWN停止 | 商品と同列入口の7金壁が旧offset条件外、右SIGN自体なし。旧policy1〜6では完全陰性不可 | 別有限policyに7固定GOLD/実fullSIGN1枚/旧強merchant/完全cap・3価格3商品/全対象探索を要求、C独立検査。旧policy/閾値不変 | 原494の旧通常診断1回と各阻害証明、意味Red/通常Resultから再開結合。実機未確認 | 今回1。同じ症状の別形でFR102の同原因再発とは断定しない |

| FR-103-LOWER-SHOP | 2026-11-15 | 2回目の遮蔽後、通常FLOORへ復帰しても完全判定できない | 後続281は2fullSIGN成立だがglyph不足、下入口10固定GOLD形が既構造外 | 別policy8で10固定位置/center床/実2fullSIGN/完全rawcap・価格・商品帯を証明しC独立検査、旧glyph閾値不変 | 原281の旧通常分類1回・pure幾何条件、意味Red/正常Result→保存再開結合。実機未確認 | 同じ実2に独立阻害1、実機run数へ二重計上しない |

| FR-103-NUMERIC-MAPPING | 2026-11-15 | policy7の数値証明だけがproducer外の半セルrowを受ける条件をレビューで検出 | validatorでproducer/Cと同じ両軸mapping・支持範囲を再検査していない | 同じ有限条件を追加し、全座標+55の変造を拒否。producerと旧policyは不変 | 意味Red1→限定3Green、既2Result pure検証成功。C独立拒否がありUI解放には至らないP2、独立確認で解消 | レビュー検出1、実機再発ではない |

TEST103確認追記: C最終40成功、Nav29はO0/strict O2成功。Ring59fcの53成功＋numeric7限定差分3成功を区別し、最終128件/23scopeをCIで確認する。元494/281の通常完全陰性とC公開採用は校正、元141149の新補助資格も校正で、各行の修正後実機改善は未確認のまま。再発数を0へ戻さない。

| FR-103-DELIVERY-METADATA | 2026-11-15 | host照合が表示labelと正規license資料で終了 | root作者metadataが表示labelを持たず、readerの拡張子制限が2license名を想定していない | 検証済green_scope表示fallback、2basenameだけの文書許可。canonical path/SHA/上限/specは維持 | 独立静的確認後、package成功を再利用しhost/未実施だけ再開。5種類/7attempt成功、検査の追加実行0 | 今回の配布補助2条件。FR101のGreen行照合とは別原因、実機再発ではない |

TEST103/build196確認: 最終同CODEの128件/23scope・IPA作成・実物5gate成功。修正後の実機改善は未確認のまま保持する。

## TEST104の対策（実機改善未確認）

TEST103の4runを全照合。開扉後停止は3run、完全判定不成立は1run、通路候補見逃しは実4の別levelで1件。FR-095/097/098/100/101/102/103を修正前に確認し、旧対策の削除回帰と今回の適用条件不足を分ける。[計画](plans/test104-shop-continuation.md)・[受領/検証](reviews/test104.md)。

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-104-PARTIAL-REFRESH | 2026-11-15 | 上部入口で開扉直後/一歩入店後、商品が十分見える前に停止 | 正常PARTIAL UNKNOWN後、遠方材質差/新GOLDで旧anchorの全セル関係が拒否。3pair全てstrict零変位で、ITEM/保護/同選択は維持 | 旧credit/確実未送信票を撤回して最新sourceの通常判定へ。既GOLD/近傍/保護/strict零/元prefix・親期限、新判定後の独立確認を要求 | 原3pairの通常Motionと全述語、意味Red→C新14＋直接18成功。繰り返しでも親期限不変/新候補保持/未送信撤回、LEFT→DOWNを確認。実機未確認 | 今回同原因系列3。FR098未確定停止と同原因かは未確定、通算未集計 |
| FR-104-OFFER-COVERAGE | 2026-11-15 | 3商品が見えていても判定不明で次周回へ進まない | 商品帯の被覆と店外壁形状が結合。2full SIGN/両rawcap/3価格/3商品presenceは成立、旧3..8形状と固定glyph/merchantは不成立 | 別policy9で正の店観測と3商品の価格床/正確なITEM・保護/非HUD完全商品帯を分離。旧対象探索/veto/余剰検出/数値境界・C独立検査を維持 | 原205pure診断、意味Red→Ring新8＋旧53/C新14＋旧18成功。原205の通常分類1回が完全陰性約41ms、同Resultを公開Cも採用。校正であり実機未確認 | 今回1。旧完全陰性の削除とは確認されず、旧構造外の別形 |
| FR-104-OBSERVED-MOUTH | 2026-11-15 | 通路候補capture116を見送りリスタート | 既上左occludedの口UNKNOWN条件が、観測FLOORの口を除外。他の元支持条件は成立 | 両flank壁/元壁支持/外側UNKNOWN/既床3歩を必要とする別guard。未知床へ進まず旧branch/旧assertを保持 | 意味Red→新7＋旧関連16がO0/strict O2成功。原116新Navはmask0→1、Scene不変。未来の到達と実機改善は未確認 | 今回1。同系列の見逃し通算は未集計 |
| FR-104-LOWER-FRAMING | 2026-11-15 | 配布前の追加確認で、一歩DOWN後も下の商品が見切れたままUP票を発行 | Navのrow±2と全商品/価格ROIの可視境界が異なる。広い7ITEM投影では既保護の再膨張も安全な次床を拒否 | 入店実証/正確な投影/全potentialの幾何的必要DOWN数・元親期限を固定。各最新判定/独立零/実足元の既床/実MOVEDだけで進み、全商品帯へ到達後の不明は保持 | coherent公開連鎖の意味Red。3ITEM/原332相当7ITEM投影→FULL3/通常policy9→保存/intent/実RESTART ACK/次floorの開発3件成功。追加9＋直接13＝22件が最終同sourceで成功。実機未確認 | 配布前の新確認1。実機の新たな再現数へ数えず、今回3ROUTE停止とも分ける |
| FR-104-LOWER-BRIDGE | 2026-11-15 | 追加観測のレビューで、data-only FULL差替え後に位置資格を再獲得できる条件を検出 | 旧source→新FULLの零変位確認がなく、新source同士の零比較だけで元world offsetを維持 | 不明/非零bridgeで資格をsticky無効化。datajob/対象・候補/独立陰性は保持し、新UNKNOWNからMOVEへ戻さない。実MOVEDだけ進捗 | direct/queuedの意味Red 1method/2assert失敗・error0→開発3件成功。既StopDetailへ元pairを保存しUNKNOWN保持時だけ凍結。追加9＋直接13＝22件が最終同sourceで成功。実機未確認 | 配布前レビュー1。既entryと同型の資格不足で、過去対策を改善完了と扱わない |

TEST104/build198最終確認: CODE47e695eの現Cを含む140件/29scope・IPA作成・実物5gate/5attemptが成功。初期C32(d886)と追加C22(e336)の作者履歴を区別し、最終CIで旧32も現Cへ結合した。単体/校正/CI/配布物の成功を実機改善完了へ変更せず、各行の実機未確認/再発数を維持する。

## TEST105の対策（実機改善未確認）

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-105-PROTECTED-WALL | 2026-11-15 | TEST104実3で開扉後、全商品可視前に停止 | 正常PARTIAL後の178→180で、ITEM投影の保護と重なる遠方UNKNOWN/DOOR→GOLDを旧静的関係と104のdata refreshが拒否。strict零・同Decision・ITEM/全保護/既金・両3×3は維持 | 同方向開扉ACK・遠方・UNKNOWN/DOOR→GOLDだけ最新通常jobへ。旧credit/確実未送信票撤回、新結果＋別strict零・元prefix/親期限を保持 | [計画](plans/test105-partial-wall-refresh.md)。意味Red1→新4＋直接旧15の作者検証成功。原pairの通常Motion/choose校正と、公開Cの手続き的な再判定/独立零/実MOVED/最新jobを区別。次画像や実機到達は未確認 | 同材質系列の今回1。旧非保護金壁対策の削除回帰とは未確認、通算未集計 |
| FR-105-SIGN-FRAGMENT | 2026-11-15 | TEST104実1で3商品が見えるが次周回へ進まない | 表示名の重なりで右SIGNが上端だけ残り、旧両中心y一致が不成立。通常UNKNOWNのためRESTART未発行 | 正常な片側看板と同じ上端・幅差2以内の実成分で商品行を固定する別の正の証明。既寸法/画素数・全商品帯の対象探索・価格/床/保護を維持し、Cも独立検査 | [計画](plans/test105-offer-proof.md)。Ring/Cの意味Red→正常producerから保存・intent・RESTART ACK・次floorまでの手続き的試験。最終統合と原画像校正は今回レビューへ記録、実機改善は未確認 | 今回この条件1。FR104商品不明の同症状継続、同一原因の通算は未集計 |
| FR-105-CLOSED-PRICE-FLOOR | 2026-11-15 | TEST104実2で価格まで見えるが次周回へ進まない | 閉じた赤色宝箱の直下セルがUNKNOWNで旧3価格床証明が拒否。既灰黒/紫の容器featureとも不一致 | native限定の閉じた赤色容器の正の識別と別policy10を追加。識別された1容器だけ直下UNKNOWNを許し、通常商品の床/全対象探索/候補保持・既閾値を維持。元Sceneを補完せず開封/購入しない | Ring/Cの意味Red、3slotの正常producer接続、欠損/色/形状/価格/対象/候補/証明偽造の拒否。最終結果と原270の校正は今回レビューへ記録。1run校正で未知精度/実機改善は未確認 | 今回この条件1。旧床証明対策の削除回帰とは未確認、同症状の通算は未集計 |

TEST105/build200最終確認: CODE3a5042dの現C8167/Ring000961を含む選択CI104件/15scope、IPA作成、実物5gate/5attemptが成功。途中sourceのC作者19/延長4と最終CIを区別して結合。原234/270の通常判定とC採用は校正成功であり、実機改善完了へ変更せず各行の未確認/再発数を維持する。

## TEST106の対策（実機改善未確認）

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-106-PREGOODS-GROWTH | 2026-11-15 | 実1で開扉後、商品が見えていても判定前に停止 | goods UNKNOWNの235→236で遠方UNKNOWN→GOLDを旧opened-entry関係が拒否。同選択・厳密零・両移動近傍は不変 | 同開扉ACK・旧金隣接・保護/旧金保持の遠方増加を既FRESHへ。元入力窓/予算を延長しない | 原pairと実Decision、凍結Red→新4/関連旧13。全33作者検証へ結合、最終結果は106レビュー。実機未確認 | 今回条件1。同症状は継続、同根因の通算未集計 |
| FR-106-SHARED-CLOSED-PRICE | 2026-11-15 | 実2で3商品が見えてもUNKNOWN、RESTART未発行 | policy7が先に価格差で失格。105のpolicy10限定対策が先行経路へ適用されない | 既閉容器9/10/11の正の識別を共通価格処理へ。通常品の9px共通条件、実価格3群/余剰0・pose下端以後の閉容器価格を要求 | 凍結した通常producerのRed、C採用/保存/intent/RESTART ACK/次floor、原253の校正。最終結果は106レビュー、実機未確認 | 105対策の適用漏れを今回1確認。同症状通算は未集計 |
| FR-106-CLOSED-BACKGROUND | 2026-11-15 | 同じ閉容器でも背景/色境界で識別を拒否 | 原253のRGB .99898、灰色原310も .99861だが、全ROIのmask unionと硬い色境界が旧IoU/被覆を拒否 | 旧layout1を保持。layout2で既厳密証明またはRGB .995＋参照画素数95%整数下限/最大1画素余裕・到達可能比率/IoU整合を独立検査 | 同じ既featureを使用、背景差/離散境界/1画素超過/蓋・色・ずれ/対象・候補・数値偽造を検査。旧v1拒否と他assertを保持し、旧UNKNOWNの1件だけ正のv2証明へ更新。実機未確認 | 今回異なる既容器2条件。同系列の通算未集計 |
| FR-106-TOP-PROJECTION | 2026-11-15 | 実3で商品上段が見えた後、未送信UPの検査で停止 | 310/312→313で直接下段ITEMに支持された最上段投影と保護が追加。旧creditは材質だけの変化を想定 | 旧票撤回/最新通常job/別静止。元ITEM・金・保護とone-use/元親期限を維持し、投影追加を移動成功に数えない | 原2pair厳密零、凍結Red→新4/直接旧12、全33作者検証へ結合。実機未確認 | 今回条件1。FR100/104/105の全体改善は未確認 |
| FR-106-OBSERVED-LEFT | 2026-11-15 | 実2原62を候補として拾わずリスタート | 104の観測口条件が上方向専用。旧左条件は不成立 | 独立した左壁/屋根支持と既床3歩でbit5のvantageへ。未知の口へ入力しない | 原mask0→32、凍結Red→新Nav5＋旧21をO0/O2で成功。旧弱い転置拒否保持、実機未確認 | 今回1。FR104の方向適用外、通算未集計 |
| FR-106-SPLIT-LEFT | 2026-11-15 | 実3原72を候補として拾わずリスタート | 外側床がまだUNKNOWNで既fringe/側方条件が不成立 | 独立柱と上下の壁端を要求し、既床3歩でbit8のvantageへ。外床を補完しない | 原mask0→256、同Nav26成功。原Scene不変、未来の露出/到達は未確認 | 今回1。同系列の通算未集計 |

| FR-106-DELIVERY-SHADOW | 2026-11-15 | 配布前の保持source検査がTypeErrorで終了 | private helperのloop内currentがnative辞書をsource bytesで上書き | bytes変数だけsource_rawへ改名。全検査/製品/IPA/spec不変 | 独立差分確認後、成功2gateを再利用し失敗・未実施だけ再開。全5種類/6attempt成功、追加製品試験0 | 配布前helper不備1。実機再発ではない |

TEST106/build202確認: 最終CODEc18427fの選択156件/24scope、同source IPA作成、実物5gate/6attemptが成功。途中作者履歴と最終CIを区別し結合。原253の通常完全陰性50.040403msとC採用は校正で、各行の実機未確認/再発数は維持する。

## TEST107の対策（実機改善未確認）

修正前にFR104/105/106のPARTIAL/上端投影/初歩前再取得を照合した。TEST106の3停止は分類後のROUTE10であり、正常Ringを後の制御失敗がKERNEL表示へ上書きしていた。実4前半の正常完全陰性→RESTART ACK/新floor成立は、後半の停止と分ける。[今回計画](plans/test107-partial-composition.md)。

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-107-PARTIAL-COMPOSITION | 2026-11-16 | 実1/2/4後半で開扉後、商品全体可視前に停止 | top ITEM投影と既許可の遠方/遮蔽材質変化を全Scene述語のORで検査し、同時変化を拒否。実4は支持された保護top材質だけで拒否 | 下段ITEM支持/旧新exactmask/安全な足元と同選択を要求し、top役割と残セルの既材質関係を分離・合成。新ITEM/保護top素材は元D内の一用data再判定、新正常結果/別静止まで入力しない | 凍結Red6/7fail→最終C新7/旧17の24成功、UP実MOVED後の通常producer→陰性/保存/実RESTART連鎖を確認。原3pairの役割・新source184/440の正常safe PARTIALも校正。実機未確認 | 今回条件3。FR106投影/関係対策の合成不足が継続、同症状通算は未集計 |
| FR-107-INITIAL-FADE | 2026-11-16 | 実3で一歩も動かず待機期限で停止 | 初歩前の暗い原40へ静止基準を固定し、同prefixでも点灯後の画像とMotion不明が続く | 旧入力/候補経路の権限を撤回し、初歩前の限定条件で最新独立2画像の観測を再取得。元D/同期epoch/予算を維持し通常の新sourceへ | 原40→107だけUNKNOWN、元D内87→88は厳密零。元D確定の正本Red7/3fail→最終C新7成功＋旧15別成功。postRESTART→新source票/実MOVEDと拒否条件を確認。実機未確認 | 今回1。旧初歩前再取得は未送信MOVE用でpassage_waitを対象外、過去改善完了とは扱わない |
| FR-107-INITIAL-MOVED | 2026-11-16 | 配布前の独立点検で、episode前の既知MOVED後にUNKNOWNから再取得し得る不足 | sticky失効をepisode開始後だけに限定していた | 初期GOLD waitの既知MOVED/非零をepisode前から失効させ、後のUNKNOWN/零で取り戻さない | 元D確定/MOVED/UNKNOWN入口を資格化したRed1/error0→最終新7/旧15へ結合。実機未確認 | 配布前レビュー1。新しい実機再発へ数えない |

TEST107/build204確認: CODEcfdb690の最終C fdbc142、選択52件/12scope、同source IPA作成、実物5gate/5attemptが成功。原3pairの役割証明・再判定原184/440の正常safe PARTIALは校正であり、実機改善完了と扱わず各行の未確認/再発数を維持する。

## TEST108の対策（実機改善未確認）

[今回計画](plans/test108-real-failures.md)。107の7添付を4固有runへ照合した。過去のFULL/PARTIAL/価格床/候補対策を照合し、同じ見た目の停止と同一根因を分ける。

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-108-OPENED-FULL | 2026-11-17 | 開扉後に3商品が見えるが入店せず停止 | 原157の通常品直下が暗く、Ringは正常UNKNOWN。既FULL一歩観測は開扉後もう一度MOVEした履歴と現在位置の金壁を要求し、入口手前を扱わない | 正の開扉ACK・次FLOOR/入口金壁・正確ITEM保護/全ROIを根拠に既一度限りの入店観測へ。旧履歴との直積を拒否 | 原157の通常結果再現、正本Red1/2failと対向Red1。新7/旧9成功、最終Cで待機7/開扉7/旧9の23成功。未収録の次frameや実機改善は未確認 | 今回条件1。開扉後停止の同症状継続、同根因通算未集計 |
| FR-108-REVEALED-MOTION | 2026-11-17 | LEFT一歩が実画像で成立したのに扉に着く前に停止 | 原256→279の一意unit地形とraw planeは成立するが、独立pixel面の支持不足。FR079/096の既幾何は成立しており削除回帰とは未確認 | 既world全依存閉包の全73実支持/有限値・unit/.45/.08と旧地形投影/texture300・95%・両領域100を結合。旧閾値不変、maskを1回cache | 原通常Motion UNKNOWN→MOVED(-1,0)。cache前新10/旧33、cache後新12成功、80case全score/支持/結果不変。品質/bandだけの私有変異各1fail。実機未確認 | 今回条件1。旧Motion系列の同根因通算未集計 |
| FR-108-FULL-VIEW-CHANGE | 2026-11-17 | 入店後の商品分類がUNKNOWNとなり、追加観測で停止 | 単一看板/offset入口と未観測の右capで全被覆が不成立。続く描画材質の揺れで未予約FULL一歩観測も即失敗。近傍差向きの記録/校正差は未解明 | 新11は正の金壁/face/footprint/全B/3価格/cap/v2証明、未観測は陰性化しない。未予約stage1/2だけ固定anchor直接UNKNOWN/零を元D内で無入力待機、旧モデル権限を撤回し新fresh零とfitまでMOVE0 | 新11は13/旧13成功、原236/238はENDCAP16の正常UNKNOWNを維持。待機Red1/2fail→最終C23成功、full_static本体不変。未来frame/実機改善は未確認 | 今回条件1。FULL系列同根因通算未集計 |
| FR-108-UNSENT-ROUTE | 2026-11-17 | 追加runで歩行途中に未送信のまま停止 | 原198→199は厳密零だが、観測床vantageがRIGHTからUPへ変化。旧票の同Decision検査がROUTE10で停止 | 旧票を撤回し、新旧の正規選択/観測床/一歩近傍/厳密零と限定材質関係を満たす別refresh modeへ。独立全tile一致/同Decision/将来拍、元予算を要求 | 最終新10を旧Cへ結合して24assert失敗→新10/旧16成功。原events由来world/visitsで純述語適格、私有非active仮定をRuntime証明にしない。実機未確認 | 今回条件1。利用者の周番号との対応未確定、同根因通算未集計 |
| FR-108-SPLIT-ROOF | 2026-11-17 | 金壁候補の原70を見送り実リスタート | 観測された上左のsplit roofが旧095/097等の別形状条件に当たらずmask0。候補対策削除とは未確認 | 独立壁/屋根・暗い口・内側既床を要す新witness。既床3歩のvantageだけ許し、未知口へ進まない | 旧Nav新7で5assert失敗→新7/直接旧26成功（O0/strictO2）。原70はmask0→1/既床3歩、原Scene不変。実機未確認 | 今回1。FR106左/上観測系列の適用外、同根因通算未集計 |

TEST108/build206確認: CODEe8c4bb8の最終C8f071469/Ring0a767a0d/Nav34f1fae6、選択CI159件/22scope、同source IPA作成、実物5gate/5attemptが成功。固定Release test108-build206を公開し、IPA/完全source/hash表の匿名GET200・全hash一致まで確認。配布source595f5bbの追加は閉じ文書3件のみ。原画像校正/手続き試験と実機を区別し、各行の実機未確認・再発数を維持する。次はメインiPhone11のtest_108.sh --until-targetで入店/3商品確認/対象なし次周回を確認し、全照合後のcampaign ZIPを受領する。

配布準備の修正（製品の実機再発へ数えない）:

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-108-DELIVERY-REFERENCE | 2026-11-17 | 新私有helperが未配置の旧番号readerを参照 | underscoreを含むhelper名の置換漏れ。AST/GO拒否だけでは相互参照を確認できなかった | 新readerへの参照を修正し、意図的な旧107履歴readerと区別。単一producer Redから2Greenクラスへの対応も明示し別Redを捏造しない | 35source/445参照/34生成予定出力/7schema対の静的閉包、元Red source/hashと6作者→7classの集合一致、実物5gate初回成功 | 配布前1。実機再発ではない |

## TEST109の対策（原因確認・実機改善未確認）

[計画](plans/test109-device-failures.md)。TEST108の3固有run/73画像/82記録を照合。FR104〜108を確認し、過去の補助試験合格を実機改善完了と扱わない。

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-109-DARK-SIDE-MOUTH | 2026-11-17 | 観測口のある原323を候補として拾わずリスタート | 外/内側と側方壁がUNKNOWNで旧106/108の別shapeに該当せずmask0 | 独立屋根4/下側壁3・観測口/内側既床・暗い側方を要求する別witnessから既bit5へ。既床3歩の観測位置のみ | 変更前1method/1assert失敗→新7/旧12がO0/strictO2成功。原mask0→32/chooser既床3歩、他15保存PAUSE不変。実機未確認 | 今回確認1。利用者の番号との対応は未確定、同系列通算未集計 |
| FR-109-PARTIAL-REMOTE | 2026-11-17 | 開扉後2商品だけ見え、入店せず23job後に期限停止 | 元画像との通常strict零/同判断でも、遠方UNKNOWN→DIRT/FLOOR等でROUTE10となり分類/準備を反復 | 既開扉safe PARTIAL・正確ITEM/全GOLD/保護/一歩近傍/完全Decisionを保ち、遠方3材質だけ別quiet証明。各比較は固定元anchorへの直接strict零、元D/入力条件を保持 | 最終testで変更前1method/2assert失敗→新8/開扉7/直接旧45の60成功。原227固定の後続20枚は通常零/同判断/staticNONE。外側4GOLDを要求し非公開flagを仮定しない。実機未確認 | 今回条件1。FR107のPARTIAL合成とは別の遠方関係不足、同症状継続・通算未集計 |
| FR-109-OFFER-WITNESS | 2026-11-17 | 3商品可視でもUNKNOWNで保持しリスタートしない | 11白画素を第4価格と数え、有効価格の18支持条件と不整合。端のfull床は成立するが半分の同色相照明差で固定palette不成立 | 正の価格支持を統一。既full床/Scene FLOORとhalf独立可視/texture/色度/輝度関係を要する局所offer証明を追加。global閾値/候補保持/余剰品拒否は維持 | 旧Red3method/5assert失敗→新12/直接旧33成功。実採用source275は正常NEGATIVE/証明1/C独立検査1、公開C保存/RESTART連鎖も確認。後続PAUSE用276はUNKNOWN保持。実機未確認 | 今回条件1。正常UNKNOWN保持は仕様通りだが検出不足が継続、同根因通算未集計 |
| FR-109-OPEN-EDGE | 2026-11-17 | 開扉後3商品が見えても入店せず停止 | 新108の正の開扉条件は成立したが、壁付近のpartial unionのleft135が旧安全域143から外れFULL一歩を拒否 | 直後開扉のpartialだけ、中央にある実icon coreと可視unionを失わず中央へ移す横一歩の別証明。旧row/ITEM ROI・上下・HUD拒否と一用/元Dは保持 | 最終testで変更前1method/2assert失敗→新7/遠方8/直接旧45の60成功。原522の通常結果と実履歴でadmission1、後続同prefix原画像なし。候補/元D/UNKNOWN無再送維持、実機未確認 | 今回条件1。FR108開扉履歴の削除回帰ではなく後続ROI条件不足、同症状継続・通算未集計 |

配布準備の確認不備（製品の実機再発へ数えない）:

| ID | 修正日 | 事象 | 原因 | 対策 | 改善確認方法 | 再発数 |
| --- | --- | --- | --- | --- | --- | --- |
| FR-109-DELIVERY-COUNT | 2026-11-17 | seal/適用成功後の一時集計assertが失敗 | 36 nativeをadditionsだけの件数と誤認。正しくは既patch9＋additions27 | 元manifestと同じ和集合36を照合し、変更3/保持33と全metadataを検証 | 正しい集合で全一致。seal/適用/製品sourceを作り直さず、件数確認だけ修正。native実行0 | 私有確認1。実機再発ではない |
