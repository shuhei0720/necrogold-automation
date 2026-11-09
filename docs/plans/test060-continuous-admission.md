# TEST060: 連続歩行の次入力を新しい画像から予約する8項目計画

状態: 計画第2周・実装第3周の独立3観点clear。Mac91全体/配布物照合済み、TEST060実機試験待ち。2026-11-09（日本時間）。SHOP-02/GOODS-01/BEAT-01/STOPを維持する。

## 1. 概要

確認済み連続歩行の未予約candidateと、予約済み入力権限を分ける。次の同じ物理拍は保持し、初回reserveをnotBeforeの100ms前以降、sourceの取得開始をnotBeforeの200ms前以降へ限定する。古い移動確認画像を早期に次入力のauthorityへ固定することを避ける。予約後のSAME/FRESH・元ticket全期限・motion判定は変更しない。商品が見える位置への到達をゴールとして検証する。

## 2. 背景

原TEST059 ZIPは3,723,124bytes、SHA `900b06ffcaecb973a3c97a9b794702ac031cdc5f40437558ee19844e434dce0b`。active/current report同SHA `9079fe8f191308fb2cfccb3fffa7dbbb8fe9903c91bad92663cc60fa9504eecd`、run d411b59e938c40719be2c40ab4c77939はUP3/MOVED3・(0,-3)・商品0。別run8975は0入力/geometry20で混ぜない。currentは14完成PNGと60.part、16exportの回収途中でresolved=false/host_deadline。停止の直接証拠は揃っており追加回収の再実行は依頼しない。

第4MOVE7をsource54で先に予約し、同ACK6/prefixの55で遠方2cell FLOOR→DIRTを検出。次UP/FLOOR/reason7/target(0,-1)とgold/protectedは同じだが、54→55がUNKNOWNでvalidation11/SCREEN17停止した。observe終了時も元Dへ67.049ms残り、late/capture/dispatch failureではない。54→55の最良shift0 score .4781565は既存.45より高く、gap .263476は.08以上。8独立terrain領域は1rawpx縦ずれを支持し、単なる照明と断定しない。47→54、47→55、48→55は既存のUP unit MOVED。motion閾値を下げたりUNKNOWNをBLOCKEDと呼ぶ変更は行わない。

TEST059の次target/窓対更新は機能し、第3/第4の窓は成立していた。新方針では第2入力のsource40を維持し、第3もsource47（notBefore時のage167.283ms）を許して48への既存SAME/fallbackを保持できる。第4はsource54（age221.872ms）を使わず、55（age137.613ms）を元の次拍の初回sourceにできる時刻関係にある。これは計測値に基づく局所検証であり、欠落画像を補った完全Controller再生や実ゲーム到達の証明ではない。

## 3. 詳細設計

対象はlead確認済み/moves>0、input_state=0、replan/continuous pendingなし、次nominal/periodが確定済みの新ordinalの初回reserveだけ。notBefore=最新candidate target−選択済みleadとし、(a) now<notBefore−100ms、または(b) last_capture_start<notBefore−200msなら予約を出さず待つ。等号は許可する。差分比較で減算/加算overflowを避ける。last_captureは既存の安定した現ACK prefix Sceneのみで、未完了/交差画像を使わない。

100/200msは今回新設する連続初回予約の短縮方針である。initial専用100〜50msをそのまま流用する例外ではなく、連続は初歩選択/retuneや50ms最小準備条件を追加しない。200msはPERFの画像生成→判断p95の達成値でも、画面の揺れが必ず終わる物理保証でもない。取得/処理L≤85ms、次取得開始間隔C≤L+5ms≤90ms、AX/queue等の準備P≤20msという合成成功域を先に固定し、C+L+P+5ms余裕=200msとする。B=notBeforeとして最初の適格画像は遅くてもB−200+Cに取得開始、B−200+C+L≤B−25msに判断でき、P後もBへ5ms残る。初回版150msではL80/C85の通常位相で判断が元Dに届きAX後に失効するP1を認め、200msへ修正した。これは実IPC20ms保証ではない。成功域の全位相と独立worldの終端を検査し、それより遅い取得/準備は元Dで停止、BEAT/GOODS未達として別集計する。

待機中はTEST059の同nominal/元periodアンカー・8%以内target/窓の対更新を維持する。元次拍deadline超過を先に検査し、失効後の再選択/別拍への送り直しはしない。条件が成立した時点の最新通常plannerとSceneで最初のcommandを作り、初回reserve以後は既存の完全凍結とSAME/FRESH全検査を維持する。予算、取消/前面/owner、商品latch、ACK/MOVED、親motion期限、UNKNOWN入力無再送、元画像fallbackの資格を変えない。初歩/retuneは現行どおり、既存再予約はこの新待機で遅らせない。

実装第1周の安全P1で、capture endが元D前でもactual commit/tickがD後の時、HUD更新だけで候補Dを未来へ動かせることを確認。Cはcommit clockを直接受けないため、更新前Dをprivate guardへ最小保持し、次の実時計tickが元D内だと確認するまでauthorityを作らない。複数observeでは最小Dを保持する。新ordinalの移動確認時も親motion元Dを最初のactualtickまで保持する。capture end/既知lastnowがD後ならobserveで拒否し、goods/取消等の優先を維持する。予約済みには拡張しない。早期/遅着/複数observe/親motionのRedと等号/+1ns、旧D内tickでのguardクリアを追加する。

## 4. 影響範囲

productionはNG2Controller.cの連続新ordinal初回reserveの時間/画像条件だけ。Runtime/Beat/Nav/Perception/header/ABI/API/cap/client v13と他native21、R12原40/G1は不変。新TEST060 launcher・14既知画像manifest/再生・CI/故障検出・seal・契約と資料を更新する。原ZIP/PNG/report/解析はGit外。既存mandatory189pathsは保持し、新14で203pathsとする。14完成とpart/未回収を分ける。

## 5. 新規試験と期待値

旧Cで新規first-ticketが早過ぎる/古いsourceで発行されるassertion Redを実装前に記録し、最小実装後Green。compile/環境errorをRedに数えない。公開Cで次を検査する。

- publication100msの等号/−1ns、source開始200msの等号/−1ns、nowがnotBefore/元Dの等号/+1ns。待機はevent/inputs/replan budgetを消費しない。
- nowだけ進めて古いsourceを新しく見せず、遅着/不安定/異prefixのSceneで発行しない。合格する最新Sceneで初回source/decisionを取得し、方向変更も最新通常plannerに従う。
- candidateの±HUD補正/同nominal非累積・算術境界、元deadline後の無復活、予約後HUD/再予約は凍結し、新待機の対象外。初歩/retune・取消/UNKNOWN/商品優先・親motion元期限を保持する。
- 原54/55の全Scene・all73score・UNKNOWN判定は不変、47/48からの既存MOVEDも保存する。原時刻のsource40/47/48/54/55によるeligibilityを公開Cの合成phase/ACKと結合し、実入力受付や完全原run再生と区別する。

既存Controller165の全method/assertを保持し、新policyと矛盾する『ACK後即時に次ticketを得る』setupだけを変更する。対象helperはnext_move、continuous_walk、continuous_vantage_drift、received_test055_replan、fresh_private_case/test055_contextの初回now、unreserved_slot_after_hud_drift/059正例。next_moveは合成world正例だけで明示再描画し、observed_resultのearliest/元Dは維持する。200msではsynthetic69の既存source start/end/seenと固定target/NB/Dは変更不要、publication nowだけを窓内へ進める。原PNG/原時刻、直接tickの境界/異常例、parent/reissue全凍結assertを自動前進で通さない。単にnowを未来へ飛ばして古いsourceで通さない。旧SAME/FRESH/fallbackの試験は必要な予約用Sceneを窓内へ置き、検証対象の再予約field/期限/予算/拒否assertを維持する。

商品到達は既存Swift独立shop world16を無変更で回帰する。追加の[TEST060 world期待表](../tests/test060-world-cases.md)は入口5歩、上下左右×木鉄8地形、6方向入力/5変位/開扉1/商品/PAUSE1を固定する。±2列の金壁を入口からプレイヤー側へ2セル延長し、DOWNの初期可視/移動証明も実Cで確認済み。L60/70/80/85ms・5critical capture位相・P20ms・synthACK280msの160終端実行は、world拍b,b+1,…,b+5の連続性まで検査する。全1ms位相は同じ公開Cの時間契約試験で追加走査し、値だけの理想算術で代用しない。遅過ぎる取得/準備は固定された3歩後停止条件で別検査する。地形/時刻/受付と商品遮蔽はworld自身の状態で定義しreport/Decisionをoracleにしない。原059の未収録未来画像ではなく合成worldであり、実ゲーム到達は主張しない。

新publicationの早期発行/source freshness欠落と、未予約deadline後HUD復活の3故障を別mutationで検出する。既存Runtime59＋058別2、新059のC別1・Raster3/C parity-field/暗号RPC/実compilerを維持する。

## 6. 順序

fresh3計画レビュー（修正込み最大3周）→旧C assertion Red→最小Green→Refactor→fresh3実装レビュー→local全必須/標準Mac CI→新IPA/全source実物照合→具体的TEST060実機依頼。閉じたTEST059レビューの第4周として扱わない。

## 7. 配布前

全203画像・native/controller/evaluator/client/package、旧故障集合・新故障・worldの対象commit/件数/未実施を照合する。22sealはCだけ変更/他21同一、R12原40/G1、実PBX/4C/5Swift/6RSP/実IPA9Mach-OのHOST非混入と全tracked sourceZIPを確認する。リンクはCIページ経由の手順と実取得を確認し、期限の短い直接URLだけを保存先にしない。公開releaseを新設しない。

TEST060は新IPAをSideStore更新→LoopCtrl完全終了/再起動/Start Server、通常VPN/ディスクイメージ、新しい通常1-1・開幕金壁可視・左側が下/画面端0のポーズから `sh test_060.sh`。歩行中はゲーム前面、自動ポーズ後はiSHへ戻り「TEST-060: 終了」後の `runtime/test-060` 全ZIPを依頼する。到達前停止を成功としない。

## 8. 対象外・未確認

motionの.08/.45/texture閾値の緩和、subpixelを厳密静止と捏造する新proof、原参考画像を使った未収録未来応答、既存ticket/親motion期限の延長、拍スキップ/UNKNOWN再送、購入/指輪/自動周回/耐久の完成。Mac正規ゲームは未導入であり、iPhone商品到達・全経路毎拍・人より速い実効処理は実機受入で確認する。
