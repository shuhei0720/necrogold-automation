# TEST072: 既存停止と不可視金壁の通路接近

2026-11-10（日本時間）。[計画](../plans/test072-approach.md)・[限定契約](../contracts/passage-approach.md)。baseline `605f2e5c526cf2da515235550a471133750dd05d`。既存停止Aを先に凍結し、新探索Bへ進める。ユーザー指定は必要なら数時間、品質を維持し金可視回の歩行と並行して新パターンを実機で磨くこと。

## TEST071受領と原因

3ZIPの添付順は実行順ではない。started_ns昇順で88384bb8→2e398828→318e3f42が1〜3回目。全48PNG（16/15/17）と全ZIPのCRC/SHA/bytes/896×414/manifest全offset/hash/cursor/時刻prefix/stable・inflight/active-report一致。全回収resolved/terminal/drained、dispatch_failureなし。raw/receiptはGit外received071。

| 実行 | ZIP bytes / SHA256 | 結果 |
| --- | --- | --- |
| 1 / 88384bb8 | 4,208,879 / `6dfc3a41a39b50feb676945af6eff92f6ee13715959986a54068976a13cfc4ff` | 5MOVED+1開扉、2商品/PARTIALでSCREEN |
| 2 / 2e398828 | 3,475,092 / `ff0a9973101507ab837cfee8445ecb16cb44c763c75a77000a7beb05acb0f663` | 2MOVED、SCREEN |
| 3 / 318e3f42 | 4,152,690 / `edc5aa290aef3b8c23f293e4dcfeeb3d8518ade30865284682d04b62906d9fc6` | 5MOVED+1送信、最後8評価UNKNOWN/MOVEMENT |

1の156→158は同LEFT/reason5/nextFLOOR/full5/全金/全保護・strictBLOCKED。(-3,-1)UNKNOWN→DIRTは既存near範囲外でquietのpalette条件を満たすが、next隣(-1,1)のGOLDに商品保護maskが重なり拒否した。元D−58.578ms。2の94→95も同UP/reason8/full5/全金/全保護/strictBLOCKED、遠方(2,2)DIRT→FLOORと(3,2)FLOOR→DIRT、旧SAMEchain2上限で元D−8.307msに拒否。

3の113→122/124/126/134は実DOOR→FLOOR、新金と商品が露出。原intensity zero .241〜.320/他候補INFINITYだがnormal texture支持167<300、expanded332/bad18で元95%に不足。旧beforeの可視地形が中央の狭い縦帯に集中し、旧3領域中2領域各100も満たさない。単純な閾値緩和やACKを開扉creditにする修正を避け、専用detail範囲で独立帯の証拠を追加する。送信間隔約.505〜.526秒でほぼ毎拍、ゲーム受信時刻がなく完全同期とは断定しない。

## 追加画像と要件

会話内12枚は視覚ラベル、ローカルrawパス未提供。順に左下/右上/左上/左上寄りの影/左下/左上/右上/左下普通扉/左下普通扉/左上/左上側/上右寄りの通路。いずれも開始部屋の上/左境界familyとして扱い、赤線を検出器の特徴や普通木扉を金正例にしない。探索済み負例はなく、店がある分類器としての正解率は算出しない。初期可視金のみの旧scopeを最新の通路接近要件へ更新した。

候補形をpure Nav、候補world座標/独立再観測/入力権限/level切替をControllerに分ける。Perceptionへ疑似GOLDを足さず、FLOORだけを歩く。外側目標へ実到達した後の独立CLEARのみ局所見送り。途中UNKNOWN/不明な金/商品/保護/期限切れを不在扱いしない。

## 重点プランレビュー

作成経緯を渡さない設計/網羅/安全3担当ともP0なし。P1/P2は次のように閉じた。

- 外側UNKNOWNでも、観測したFLOOR口と両壁があれば内側床へ接近できる。黒だけとは区別する。
- 探索開始/校正/未送信/ACK待ち/最終CLEARそれぞれの商品PARTIAL/VISIBLE・取消/前面/owner・UNKNOWN送信を限定public-C試験に固定。保持後の方向/RESTARTは0。
- 外側実到達+独立CLEARだけ候補完了。未到達は元期限内2拍まで観測し未判定へ分離、他候補後も残ればNO_PATH保持。
- restart比較は最初の画像でなくPAUSE直前の最新安定FLOORで凍結。RESTART ACK後の旧終点worldを新levelと誤認しない。
- native契約先頭から限定契約へ案内し、新mode/開扉領域/levelbaseを明記。
- 再レビューで見つかったwalk原点の矛盾は、最初のwalk_started_ns+45秒を保持、level同期の時計だけ別にして解消。総予算・一回/回数上限もlevelresetで巻き戻さない。

静的プランレビューは実機成功ではない。実装差分の最終レビュー・検証結果は確定後に記録する。

## TDDと検証範囲

Aの新観測2正例は固定071で9assertion FAIL/errors0、開扉は4方向×3seed×O0/strictO2の24assertion FAIL/errors0、保護GOLDは8assertion FAILから最小Greenへ。環境/compile失敗をRedへ数えない。新Nav純粋関数はcompile可能な機能未実装stubに対して52subcaseの意味的Red、探索Controllerは固定071で上0/左0/上右2の3subcaseがMOVEでなくPAUSEを返す意味的Redを確認した。

procedural地形/後続画面は実機の欠落画像を補うものではない。既知318の追加証明は新mask85/detailで支持320〜325/bad8〜12、上下band各131〜135/187〜192、95%/全73候補15pp成立。通常motion/旧MOVED/旧maskの閾値は変更しない。比較可能な既知motion10pairは318の1pairだけUNKNOWN→DOOR_OPENED、他9同一、欠落4pairは補完しない。

変更単体と初歩/校正/再予約/商品/取消/restartの関係回帰を選ぶ。Runtime/HTTP/取得は不変なので全world/全故障集合を累積せず、既存の限定Mac dispatch/取消境界を新Cへリンクして確認する。native変更の新IPA/22seal/実compiler/全Mach-O/完全sourceと固定Release匿名GETを別途照合する。新072の実機/実ゲームCIは未実施。


## 2026-11-11の実機試験範囲

ユーザー追記により、次から「候補までリスタート→金壁または通路候補→商店へ移動→全商品確認」を一つの実機試験とする。通常1-1のポーズから同コマンドをまず2回、開始配置を手動で金可視/不可視へ揃える依頼はしない。Controllerに同native sessionのprocedural一連ケースを追加し、途中のrestart/開扉だけで完了扱いしない。元有限予算/UNKNOWN無再送/商品保持は維持し、実機では全run別ZIPを返してもらう。


### 経路不変の遠方揺れを待たせない

実2eはreason8/FLOOR/両UNKNOWN・未入店・同full5/金/保護/strictBLOCKED、遠方2paletteだけだった。一般refreshを使うとD−8msから新将来拍へ待つため、経路不変は毎拍という既存指示に合わせてquietの限定対象を追加する。既存3×3/全金/全保護/full5/原ID・全clockは不変。初回設計の新観測回復は、quiet不適格なreason7等の別正例で維持し、SAMEchain2/run8を増やさない。Bの探索19件・旧budgetを保ってこの性能差分を最後に検査する。


## 最終コードと重点レビュー

最終Controller `46f9bae206bd9e85d5b8c1cd1ed0d9ce366a1138ef82c0dcaa617ac4be509f21`、Nav `1c37c3d01c592554e9b426888805dbeeea9e20b47aeaee4048aa38a9f30727ef`、Core `77f7abf7db10db58468a3723f39aaaa0f1cbd6afc454c06b4589aa99e64c8ef1`を凍結した。変更native3、他19/API16/cap14/v15/wire/ABI/Runtime/Perception/取得/元閾値は不変。

新規はdoor7/observation8/passage Nav8/Controller22の45メソッド。Nav8はO0/strictO2の両profile。B22は最小修正後Green4.588秒、旧restart/時計関連6件Green3.576秒。最後のquiet1件は固定Bで意味的Red5assert/errors0→最小bool追加Green、3回以上の遠方描画更新でも元ID/全command bytes/epoch/期限/events/予算非消費を検査した。

独立第3passでP1を3件検出し、それぞれ意味的Red→最小修正で閉じた。初回0歩から未送信PAUSE中に金が現れる場合は実uptime1000秒/32746秒で2FAIL、未開始walk/syncを初回Scene endでだけ開始。GOLD_UNKNOWN後の見送り権限、CLEAR enumと実GOLDセルの併存では初期/最終/PAUSE/RESTART予約の9例をRed9assert/errors0で固定し、明瞭CLEAR判定で保持へ分けた。通常PAUSE UIのUNKNOWN対照は元からGreen、ACK済RESTARTの新level/timeoutも維持。CLEAR+GOLDは壊れたSceneだけでなく、実Perceptionの280gold色px→peak98/CLEAR・tileGOLDでも成立をproceduralRGBAで確認した（端末画像ではない）。

旧Shop071の5variantは、旧quiet票のnot_sent/begin0・無credit・独立proof前MOVE0を保持し、一般観測待機を即終了と区別する期待へ更新。旧Controllerのmixed SAME/FRESH予算1methodはfar変化が新quietとなるため、2セルだけ3×3内の(1,1)へ移し、元8/2/期限/旧ID全assertを保持した。skipやassert削除はない。

設計担当が最終hashで新4module+旧Shop071の50テストを独立実行しGreen20.001秒、diffcheck成功。安全担当も最終hashで限定修正/追加境界を照合し、未解決P0/P1/P2なし。網羅担当も最終hashのCLEAR+GOLDtile拒否/見送り票撤回/新9境界を照合し、3観点とも未解決P0/P1/P2なしで第3passを閉じた。実Mac/IPA配布物照合結果は確定後に追記する。これらの成功を実機の到達率や毎拍達成へ置き換えない。


配布用host選択は新45＋関係10＋selector3の58メソッド。関係10は旧shop0712・Nav73候補parity1・Controller準備/unchanged restart/clock3・SAME/FRESH mixed cap1・cadence2・ABI1。重複済みの新機能群を再実行せず、未確認の関係6+selector3だけ最終sealed sourceでGreen8.165秒、22source前後不変。manifest SHA `0f3fea5511bf9a2f01e22e7cb60f887d40afc40da02bc949f0e616a0a789de9f`。CIでは全58とnative_walk/test069/test072のHEAD/blob/delegate同一性をbefore/afterに束縛する。標準MacのIPA作成と既存限定Runtime6呼出はこれから実行する。
