# 最新状態

更新: 2026-11-10（日本時間）。TEST067の2run/全22選択PNGを受領、SHA/bytes/896×414/全CRC/manifest/時刻prefix一致。1回目0歩、2回目3商品可視と自動GOODS/PAUSE成立。3回目以降は第2runのread-only回収で新startなし。現在は全15PNG回収済みresolved=true、次回はfresh UUIDで試験可能。[受領台帳](device-tests/README.md#test067-received)。

## TEST068: 下端金壁と回収の再保存

[計画](plans/test068-fringe-collection.md)。Core/Perception/Nav/Controllerの4資産とclientだけを変更。他18/API15/cap13/ABI/clientv14・Runtime/Swift/wire layoutは不変。

1回目は実金壁(-1,5)/(1,5)がgrid y=-5〜4の外かつHUD除外に重なり、GOLD_CLEAR/金tile0で対象外PAUSEを送ったが未成立。native capture/入力0/歩行未開始。raw金436/373 of625・観測origin/DOWN次床/周囲FLOOR・保護0を確認。PAUSE不成立の物理原因は未確定。

一意な下端raw金対の元280条件で、j5は地図外のままEDGE_DOWN=3。j3/4ではHUDに隠れた実座標のGOLD2セルだけ限定復元。heart/矢印/片側/曖昧対/商品/保護/既存gridgold時は元処理を維持。119原画で今回第1runの5枚だけgold_state1→3、他114全Scene bytes不変、全119O0/strictO2一致。

NavはEDGE_DOWN/gridgold0/原点/未通過/UNKNOWNgoods/保護0/観測DOWN床だけreason9で1歩。Controllerは全accepted current-prefix pre-send（mask0含む）で元source/full5/局所/全保護/strictBLOCKED/元clockを再証明、beginは最新captureIDを定数時間確認。actualbegin1回だけ、UNKNOWN/BLOCKED edge再送・retuneと実1歩後の残hint2歩目は禁止。元Dのobserve先行失効もinitial_recoverへ渡し旧ID/元12秒を保持する。新画像でgridgoldが見えれば通常plannerへ戻る。未収録の次画面は補完しない。

clientは完成cursor/全SHA/PNG/manifest/完成先samebytesを確認した画像だけ再write/両journal再保存を省く。partのみ/欠損/不一致は旧publish、cancel/90秒export/180秒・旧v/UUID/履歴を維持。回収のみを開始時に明示し、native終了理由と回収完了を分離。nonterminal時はhost原因を隠さない。API/cap等を形式的に上げない理由はScene gold_state/Nav reasonがwireに出ず、全Cは同じ22seal内でlayout不変なため。

## 検証と次の実機

新fringe6は旧Cで8semantic failures/errors0→Green6。newedge6は固定067 Cで18semantic failures/errors0→Green6。client新9は8semantic failures/errors0→関連25含む34Green、完成cursor開始前の不正skipと非terminal原因非表示の追加Redも修正。独立レビューP1のobserve-before-tick純D失効を既存method内Red1→修正Greenで確認、最終製品P0/P1/P2なし。CI選択46件（native26/client17/selector3）を確定、既存native14とselector3も実封印sourceでGreen。runner最終差分を同じレビュー内で追随する。

新21+関連/selectorをdevice CIへ選び、無変更Runtime/world全体は累積しない。新IPA/22seal/実compiler/全Mach-O/完全sourceを照合し固定Releaseから返す。TEST068は未配布・実機未実施。新IPA更新/LoopCtrl完全終了・起動/Start Server、新通常All Zones1-1金壁可視ポーズでtest_068.sh、終了後runtime/test-068全ZIPと下端/通常金壁の到達・歩行・回収を必ず依頼する。

## TEST067の成功と限界

945467…は0方向入力、Resume ACKから約94msで対象外PAUSE、未成立のままACK後4秒でnative capture停止。CLIのstopped/noneはhost理由nullでnative原因を隠していた。

ed9206…は3商品（リンゴ/ホルスター/ブロードソード、価格25/25/100）、原画173はinflight/不安定prefixだが実CもVISIBLE。安定確認175原画はexport省略、183はPAUSE確認。7送信=5MOVED/1開扉/GOODS優先UNKNOWN1評価、6歩目は捏造しない。間隔.531/.509/1.044/.519/.521/.520秒、可視後方向入力0。初動4.618秒は候補周期513.671msが下限515msを外れた初期再取得。ゲーム受信時刻なしで完全同期と呼ばない。

回収は初回90秒切れ・次status RPC期限で未完了、最後の再開で完了。保存済み再write等でmanifestから残りchunkまで26.091秒空いたが、FS/CPU各寄与は未計測。067は回収済みで再実行不要。[067固定Release build104](https://github.com/shuhei0720/necrogold-automation/releases/tag/test067-build104)・[検証](reviews/test067.md)は過去結果として保持。

## 運用

[開発フロー](development-flow.md#最新の運用方針2026-11-10-日本時間): 実機ログ→局所修正→単体/関連回帰→必要なIPA/同一性確認→実機。固定時間なし/品質安全条件不変、通常差分レビュー1回。承認済branchへ保存、raw/画像/report/log/秘密値はGit外。同じiPhoneだけ、ユーザーはMacを持たず実機担当。初読3文書≤16KiB、[索引](context.md)から必要資料だけ読む。
