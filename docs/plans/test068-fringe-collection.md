# TEST068: 下端金壁への観測床1歩と回収の再保存

2026-11-10（日本時間）、baseline `0b8a4cce4a216c28d841de256393bbec56d52b9a`。

## 1. 目的

TEST067の1回目0歩と、2回目回収未完了で後続起動が回収だけになる問題を改善する。成功した2回目の3商品確認/ほぼ毎拍歩行を維持し、未観測の地形を捏造せず、回収のUNKNOWN無再送・同UUID・元予算を保つ。

## 2. 実機根拠

ZIP5,514,177bytes/SHA e5d9f4875aeab4f3023ad4cdb9ada2439c140c2713eca4043736a8a2462df5a2、2run/22PNGのSHA/bytes/CRC/896×414/manifest/時刻・prefix一致。1回目capture12/87〜90はFLOOR/GOLD_CLEAR/金tile0、実金は(-1,5)/(1,5)で25×25金436/373。現在地図y=-5〜4の外かつHUD除外に重なる。origin/DOWN次床/周囲は観測FLOOR・保護0。復帰後約94msで対象外PAUSEを送り未成立、native capture停止/0歩。実入力受信時刻なしでPAUSE不成立の物理原因は断定しない。

2回目173は人に3商品25/25/100、実CもGOODS_VISIBLE、最終native GOODS1/PAUSE1。安定確認175原画はexport省略、補完しない。7送信=5MOVED+1開扉+商品優先UNKNOWN1評価、間隔6中5は.509〜.531秒・1箇所1.044秒。初動4.618秒は候補周期513.671msが下限515ms外で初期再取得。

回収は90秒切れ後、同UUIDのread-only回収を繰り返し、ZIP時点ではresolved=true/全15選択PNG回収済み。新startは2回だけ。回収再開で保存済み画像も再write/両journal再保存し、最終回収でmanifestから残りchunkまで26.091秒空いた。成功後も履歴host_deadline表示が残り、native理由を隠していた。

## 3. 詳細設計

Perception: 元gold画素/280条件・mask/density閾値を保持。rawの25×25金>=280が72px離れて対になり、一意な下端入口候補として成立する場合だけ扱う。j5はgrid外のまま明示gold_state EDGE_DOWN=3へ、座標をgrid内へ偽装しない。j3/4で同対がHUDに重なっても実raw証拠が成立する場合だけ正しい座標のGOLD2セルを復元。原gridgoldが存在する通常経路は変えない。heart/矢印/単独gold/複数曖昧対をhintにしない。

Nav: EDGE_DOWN・gridgold0・未通過入口/原点・UNKNOWNgoods・観測originとDOWN次がFLOOR・保護なしのときだけDOWN1歩を新reason9で選ぶ。隠れた入口/先の床は作らず、観測床から見える範囲を増やす。Controllerはvalid enum上限と初期同期だけ明示拡張し、1run1回のedge送信だけ許す。既存safe_floor/retune/reference/SAME/FRESHのcandidate2ガードは一括で3へ広げない。未送信の同edge source/現Scene/全5field/床・保護・元時計・strictBLOCKEDが不変な遠方palette変化だけは、初期quietの限定edge経路で元IDを保持できる。UNKNOWN/既知BLOCKEDのedge再送・retune、実1歩後の残存edgeによる2歩目は拒否。元Dを過ぎた未送信ticketはobserve/tickの順によらずinitial_recoverへ渡して旧ID/元12秒を保つ。次画像で実gridgoldが見えれば通常plannerへ戻る。

Client: 保存済み完成画像をcursor/hash/PNG/header/dimensions/manifestで検証し、完成image_pathと同bytesならimage再write/per-image両journal再保存を省く。欠損/不一致/partのみは元publish経路、期限/cancel/checkpoint順は保持。回収開始の任意callbackで『今回は回収のみ、ゲーム起動なし』を明示。CLIはnative終了理由と回収完了状態を分け、成功後に残るhost_deadlineをゲーム失敗と表示しない。履歴events/stop_reason、resolved条件とRPC起動/UUIDは変更しない。

## 4. 互換と変更範囲

nativeはCore.h/Perception/Navigation/Controllerの4資産、ほか18不変。EDGE_DOWNとDecision.reason9は同一sealed build内のCだけで使用、Runtime/JSON wireは両値をserializeしない。Scene23864/Status192等layout・ABI1/API1.98.15/cap13/clientv14を維持し、形式的なversion更新を混ぜない。Runtime/Swift/取得・実入力・owner/queue構造は変更しない。90秒export/180秒・元12秒/45秒・16入力・商品/取消/権限を維持。

## 5. 試験期待

public proceduralのfringe画素/一意対/under-boundary/誤HUD、Nav observed床1歩、Controller初期edge・同期/同ID quiet・1回上限・実変位のみcredit・通常gold復帰・UNKNOWN/BLOCKED・prefix/商品/権限/期限をTDD。clientは保存済み/part/欠損/不一致・取消/期限/legacy・recover-only/noGET/noSTARTと表示を実暗号HTTPの公開fixtureで検査する。compile/環境失敗をRedに数えない。原画22/旧known画像はlocal証拠とし、未来画像や未収録の175を補わない。

## 6. 実装順

旧C/clientをGit外保存→新assertの意味的Red→Perception/Core・Nav・Controller・clientの最小Green→独立差分レビュー1回で設計/テスト/安全を確認。sourceはABI/新enumの互換性をread-onlyで独立確認済み。通常の局所分岐として進め、大きなABI/並行構造変更を混ぜない。

## 7. 配布前検証

変更単体と必要な公開回帰のみをdevice CIへ選択。原成功経路・初期/quiet・gold/motion閾値/閉schema/ABIを確認し、未変更Runtime/world全体は累積しない。native変更の新IPAを標準Macで実ビルドし、22seal/実compiler/全Mach-O/完全sourceを照合、固定Releaseで匿名GET/SHAを確認する。

## 8. 実機依頼とスコープ外

新IPA/完全source/再起動・Start Server/iSH test_068.shと終了後runtime/test-068全ZIPを必ず依頼し、下端金壁回と通常金壁回の到達・商品・歩行・回収を評価する。067は回収済みで再実行不要。汎用の画面外探索や未観測セル入力、PAUSE不成立原因の断定、初動profile閾値変更、速度/到達の実機成功保証は混ぜない。
