# TEST098: TEST097の受領と停止原因

2026-11-14（日本時間）。CI/配布物照合済み、実機改善未確認。[計画](../plans/test098-route-observation.md)・[修正表](../fix-records.md)。

3ZIP/64PNG、計14,364,202B。全CRC/SHA・manifest/record chain・画像metadata/登録集合・ZIP inventoryを照合し、全complete/terminal/drained、欠損0。session開始時刻の実順は添付1→3→2。

| 実順 | run | 実際の状態 | 判定 |
| --- | --- | --- | --- |
| 1 | 23aba266 | UP5歩/開扉後、部分観測の再開前にSCREEN。最初の拒否画像は未保持、保存234→242の全関係は成立 | Ring8.382ms、実採用は期限内。UNKNOWN/INCOMPLETEで対象なし未確定 |
| 2 | 6df6196e | LEFT6歩/開扉後、297→299の遠方(5,4)FLOOR→UNKNOWNを拒否。候補135も見送り | Ring17.908ms、期限内採用、UNKNOWN/INCOMPLETE |
| 3 | f8bce7bd | UP6歩後、221→223で隣接DIRTがFLOORに変わり、未送信のDOWNからLEFTへの完全判断変更を拒否 | 商品未到達・判定未実施 |

実1のterminal assessment_nsは後のcycle_failureで更新されている。実際の採用時刻は元worker期限内で、前回PAUSE遅延再発と誤読しない。最初の拒否時刻は保存242の撮影前なので、この画像を最初の拒否画像とは呼ばない。

実2は最新の完全判断LEFT/reason5/target(-1,0)/FLOOR、全保護と厳密0が成立。実3も厳密0/同GOLD/保護不変だが、完全判断がDOWN/reason8/(0,1)/FLOORからLEFT/reason8/(-1,-1)/FLOORへ変わった。移動UNKNOWN8や入力送信失敗ではない。各画像のPerceptionは一度、以後は不変Sceneを使う。候補135は実PAUSE cmd10の判断元で、角の外に観測床がある。

## 実装と検証範囲

候補6、側方開口8、部分再観測9、client診断2の新規25件は、基準sourceへ意味assert Redを取ってから実装した。環境/compile失敗はRedに数えない。候補は新6＋旧39=45、側方は新8＋旧14=22、部分は新9＋旧30=39を選択成功。診断guardの最終訂正後は新9＋直接関連C診断3=12だけ再確認した。clientは実Python3.9で新2＋関連3=5成功。過去GreenのC版を最終版と偽らず、最後の診断guardを含む全同sourceの111件は最終CIで確認した。

独立差分レビューはGO。非MOTION/mask0行を追加すると回収が拒否されるP1を検出し、意味Red1→最小guard→上記12 Greenで閉じた。既Runtime serializerのSceneChangeはrootのみで、再帰側へ例外を広げる実producerはないことを確認。診断は停止/入力許可を変えず、全拒否画像の保存を保証しない。

保持Sceneで候補135はmask32/既床4歩、221→223は旧同判断false/新側方true、297→299は部分継続成立。234→242は修正前から成立し、実1最初の原因は未確定のまま。校正済み結果を未知画像の精度や未来到達へ数えない。

CI selectorは未対応workflowでassert Red1→098優先選択の最小変更→5 Green。scopeはhost111/20＋selector5=116件。36native資産中の変更はController/Navの2つだけ、公開ABI不変、選択旧assert保持、test helper41のsource閉包と旧snapshot不要を確認。Runtimeは旧096の12callback、現API/spool/Exportを選び、全故障/全worldは追加しない。IPA/実compiler/配布物/全sourceの最終結果は次節。

## 最終CIと配布物

code `7b7d7515cd1a394d1215f1c619c4e41bf7b9fe16`、run43537002612/build175。最後の診断guardを含む現sourceのhost111/20scope＋selector5/1scope＝116件/21scopeが成功。過去の側方22件の作者試験は訂正前C版の証拠として保存し、最終C版への適用は今回CIの新側方8＋関連14を根拠にする。現Mac API owner/schema・実FS spool・Export、既Runtime096の12callbackと旧Runtimeの指定assert Redが成功。旧094のobsolete Runtime fixture/別095全fixture/全worldは未実行で、今回の証拠へ数えない。

実物5種類を計5試行で照合。36seal/2変更、実C8/Swift5/profile3のRSP/FileList・9Mach-O、旧827＋新248＝禁止1075marker、canonical15source/56,088B ELF・旧Bank/Coverage・G1/R12全40、build source831ファイルの全bytes/CRCを確認。IPA 18,016,283B、SHA `eee593f93146d4892a7f56790705c9bbd44495e34be3418d648361191a35cae3`。実物検査の詳細/再試行数はactual spec/ledgerへ結び、未取得の値を補わない。

保持Sceneで候補135のmask32/既床4歩、実3の221→223の限定admission、実2の297→299の部分関係が成立。実1の234→242は修正前から成立するため、最初の停止原因は未確定のまま。再観測待機や診断追加が実際の根因を解消すると断定せず、全拒否画像の保存も保証しない。校正済みSceneや模擬clock/pixels/classifierを未知画像精度・実ゲーム到達・速度の受入へ数えない。

closingはstatus/本レビュー/修正表/device-tests索引だけを変更し、製品/試験/seal不変。[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test098-build175/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test098-build175/source.zip)を固定Releaseへ保存する。公開後の匿名全GET/SHA/実tag/closing source全bytesは別途照合する。次の実機は通常1-1ポーズから候補までrestart→接近/入店→3商品可視→対象だけ判定→対象なしなら次周回。停止通知後iSHの全保存/ZIP照合終了を待ち、表示run ZIP全体を返却してもらう。実機到達・速度・未知精度は未確認。

## 配布後の再解析: 実1の停止段階の訂正

2026-11-14（日本時間）。ユーザーから原因未確定のまま修正するのかと指摘を受け、旧097のCと原checkpoint/terminalを読み直した。追加の製品変更・試験・Perception/Ring再実行なし。

実1は最初のOBSERVE_MORE判定に成功した後、SEARCH/partial credit中の再検査で停止している。根拠はpost_move_reacquisitions=2/episode_id=2、initial=0、record_count=1/dropped=0。旧097の各増加箇所を照合すると、回復記録を増やさないのはOBSERVE_MORE成功分岐だけで、唯一の回復記録は前のcmd7。MOVE14の予約はmodeをNORMALへ戻しており、以後のMOVEはなく、15は停止後のPAUSEである。

job1/source234/full_seen=falseのまま、prefix14は継続資格と一致し、停止時刻は元continuation期限内。このため旧C2699–2703の継続許可後のcycle_partial_relation失敗へ絞れる。Runtimeからの直接失敗はreason6であり、今回のSCREEN17とは異なる。独立した静的確認でも同じ結論となった。

ただし、内側の経路・材質差・保護・動き判定のどれが失敗したかは、未保持の判断画像/Sceneがなければ特定できない。後の保存242を失敗画像と見なさない。098のUNKNOWN待機と拒否画像記録はOBSERVE_MOREだけにあり、今回特定した継続許可後の分岐には入っていない。したがって098が実1の停止を修正/採証するという根拠はない。前の解析は停止段階の確認が不足していた。原因未確定のまま許可条件を緩めず、追加修正を行っていないことを明記する。
