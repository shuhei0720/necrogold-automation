# 最新状態

更新: 2026-11-10（日本時間）。TEST067の2run/全22選択PNGを受領、SHA/bytes/896×414/全CRC/manifest/時刻prefix一致。1回目0歩、2回目3商品可視と自動GOODS/PAUSE成立。3回目以降は第2runのread-only回収で新startなし。現在は全15PNG回収済みresolved=true、次回はfresh UUIDで試験可能。[受領台帳](device-tests/README.md#test067-received)。

## TEST068: 下端金壁と回収の再保存

[計画](plans/test068-fringe-collection.md)。Core/Perception/Nav/Controllerの4資産とclientだけを変更。他18/API15/cap13/ABI/clientv14・Runtime/Swift/wire layoutは不変。

1回目は実金壁(-1,5)/(1,5)がgrid y=-5〜4の外かつHUD除外に重なり、GOLD_CLEAR/金tile0で対象外PAUSEを送ったが未成立。native capture/入力0/歩行未開始。raw金436/373 of625・観測origin/DOWN次床/周囲FLOOR・保護0を確認。PAUSE不成立の物理原因は未確定。

一意な下端raw金対の元280条件で、j5は地図外のままEDGE_DOWN=3。j3/4ではHUDに隠れた実座標のGOLD2セルだけ限定復元。heart/矢印/片側/曖昧対/商品/保護/既存gridgold時は元処理を維持。119原画で今回第1runの5枚だけgold_state1→3、他114全Scene bytes不変、全119O0/strictO2一致。

NavはEDGE_DOWN/gridgold0/原点/未通過/UNKNOWNgoods/保護0/観測DOWN床だけreason9で1歩。Controllerは全accepted current-prefix pre-send（mask0含む）で元source/full5/局所/全保護/strictBLOCKED/元clockを再証明、beginは最新captureIDを定数時間確認。actualbegin1回だけ、UNKNOWN/BLOCKED edge再送・retuneと実1歩後の残hint2歩目は禁止。元Dのobserve先行失効もinitial_recoverへ渡し旧ID/元12秒を保持する。新画像でgridgoldが見えれば通常plannerへ戻る。未収録の次画面は補完しない。

clientは完成cursor/全SHA/PNG/manifest/完成先samebytesを確認した画像だけ再write/両journal再保存を省く。partのみ/欠損/不一致は旧publish、cancel/90秒export/180秒・旧v/UUID/履歴を維持。回収のみを開始時に明示し、native終了理由と回収完了を分離。nonterminal時はhost原因を隠さない。API/cap等を形式的に上げない理由はScene gold_state/Nav reasonがwireに出ず、全Cは同じ22seal内でlayout不変なため。

## TEST068の配布と実機確認

code `fe395d7b0c202715b253541c1b5f468091a302d9`、[Mac106](https://github.com/shuhei0720/necrogold-automation/actions/runs/42794069145) device46件成功（native26/client17/selector3）。新21は旧実装で意味的Red→Green。独立レビューP1のobserve先行失効・P2の非terminal理由表示を修正、最終P0/P1/P2なし。実IPA/build106 SHA `42448a2d8de1c8c61b13af8f5e48874b6f553a0d2980456700e5c110d27d671a`。host全ID/生ログ/ABI/22seal前後・clientの実driver/Git blob/SHA、実4C/5Swift/6RSP/strictO2、全9Mach-Oの105禁止marker非混入、全510build-source bytes/path/CRCを照合。他18/R12原40/G1不変。実ゲームCIと068実機は未実施。

[新IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test068-build106/LoopCtrl.ipa)・[完全source ZIP](https://github.com/shuhei0720/necrogold-automation/releases/download/test068-build106/source.zip)・[SHA256SUMS](https://github.com/shuhei0720/necrogold-automation/releases/download/test068-build106/SHA256SUMS.txt)。固定Releaseへ配置。最終sourceはビルド対象から文書3件だけ異なり、code/launcher/tests/clientは同じ。[検証](reviews/test068.md)。無変更Runtime/world全体をCIへ累積しない。

SideStoreで新IPA更新→LoopCtrl完全終了・起動→Start Server、通常のVPN/ディスク設定。展開した`test_068.sh`のあるフォルダを選び、新しい通常All Zones 1-1の金壁可視ポーズからiSHで実行。

```sh
mkdir -p /mnt/necro_test068
mount -t ios . /mnt/necro_test068
cd /mnt/necro_test068 && sh test_068.sh
```

歩行中はゲーム前面、自動ポーズ後約5秒でiSHへ戻り、前面のまま`TEST-068: 終了`まで待つ。終了後runtime/test-068全ZIPと下端/通常金壁での3商品可視・停止位置・歩行間隔・回収表示を返してもらう。回収のみの表示なら同runを回収し、完了後の次回実行から新しい試験となる。回収済067の再実行は不要。

## TEST067の成功と限界

945467…は0方向入力、Resume ACKから約94msで対象外PAUSE、未成立のままACK後4秒でnative capture停止。CLIのstopped/noneはhost理由nullでnative原因を隠していた。

ed9206…は3商品（リンゴ/ホルスター/ブロードソード、価格25/25/100）、原画173はinflight/不安定prefixだが実CもVISIBLE。安定確認175原画はexport省略、183はPAUSE確認。7送信=5MOVED/1開扉/GOODS優先UNKNOWN1評価、6歩目は捏造しない。間隔.531/.509/1.044/.519/.521/.520秒、可視後方向入力0。初動4.618秒は候補周期513.671msが下限515msを外れた初期再取得。ゲーム受信時刻なしで完全同期と呼ばない。

回収は初回90秒切れ・次status RPC期限で未完了、最後の再開で完了。保存済み再write等でmanifestから残りchunkまで26.091秒空いたが、FS/CPU各寄与は未計測。067は回収済みで再実行不要。[067固定Release build104](https://github.com/shuhei0720/necrogold-automation/releases/tag/test067-build104)・[検証](reviews/test067.md)は過去結果として保持。

## 運用

[開発フロー](development-flow.md#最新の運用方針2026-11-10-日本時間): 実機ログ→局所修正→単体/関連回帰→必要なIPA/同一性確認→実機。固定時間なし/品質安全条件不変、通常差分レビュー1回。承認済branchへ保存、raw/画像/report/log/秘密値はGit外。同じiPhoneだけ、ユーザーはMacを持たず実機担当。初読3文書≤16KiB、[索引](context.md)から必要資料だけ読む。
