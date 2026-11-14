# TEST098: TEST097の受領と停止原因

2026-11-14（日本時間）。実装/選択単体/独立レビュー済み、CI/IPA確認前、098未配布。[計画](../plans/test098-route-observation.md)・[修正表](../fix-records.md)。

3ZIP/64PNG、計14,364,202B。全CRC/SHA・manifest/record chain・画像metadata/登録集合・ZIP inventoryを照合し、全complete/terminal/drained、欠損0。session開始時刻の実順は添付1→3→2。

| 実順 | run | 実際の状態 | 判定 |
| --- | --- | --- | --- |
| 1 | 23aba266 | UP5歩/開扉後、部分観測の再開前にSCREEN。最初の拒否画像は未保持、保存234→242の全関係は成立 | Ring8.382ms、実採用は期限内。UNKNOWN/INCOMPLETEで対象なし未確定 |
| 2 | 6df6196e | LEFT6歩/開扉後、297→299の遠方(5,4)FLOOR→UNKNOWNを拒否。候補135も見送り | Ring17.908ms、期限内採用、UNKNOWN/INCOMPLETE |
| 3 | f8bce7bd | UP6歩後、221→223で隣接DIRTがFLOORに変わり、未送信のDOWNからLEFTへの完全判断変更を拒否 | 商品未到達・判定未実施 |

実1のterminal assessment_nsは後のcycle_failureで更新されている。実際の採用時刻は元worker期限内で、前回PAUSE遅延再発と誤読しない。最初の拒否時刻は保存242の撮影前なので、この画像を最初の拒否画像とは呼ばない。

実2は最新の完全判断LEFT/reason5/target(-1,0)/FLOOR、全保護と厳密0が成立。実3も厳密0/同GOLD/保護不変だが、完全判断がDOWN/reason8/(0,1)/FLOORからLEFT/reason8/(-1,-1)/FLOORへ変わった。移動UNKNOWN8や入力送信失敗ではない。各画像のPerceptionは一度、以後は不変Sceneを使う。候補135は実PAUSE cmd10の判断元で、角の外に観測床がある。

## 実装と検証範囲

候補6、側方開口8、部分再観測9、client診断2の新規25件は、基準sourceへ意味assert Redを取ってから実装した。環境/compile失敗はRedに数えない。候補は新6＋旧39=45、側方は新8＋旧14=22、部分は新9＋旧30=39を選択成功。診断guardの最終訂正後は新9＋直接関連C診断3=12だけ再確認した。clientは実Python3.9で新2＋関連3=5成功。過去GreenのC版を最終版と偽らず、最後の診断guardを含む全同sourceの111件はCIで確認する。

独立差分レビューはGO。非MOTION/mask0行を追加すると回収が拒否されるP1を検出し、意味Red1→最小guard→上記12 Greenで閉じた。既Runtime serializerのSceneChangeはrootのみで、再帰側へ例外を広げる実producerはないことを確認。診断は停止/入力許可を変えず、全拒否画像の保存を保証しない。

保持Sceneで候補135はmask32/既床4歩、221→223は旧同判断false/新側方true、297→299は部分継続成立。234→242は修正前から成立し、実1最初の原因は未確定のまま。校正済み結果を未知画像の精度や未来到達へ数えない。

CI selectorは未対応workflowでassert Red1→098優先選択の最小変更→5 Green。scopeはhost111/20＋selector5=116件。36native資産中の変更はController/Navの2つだけ、公開ABI不変、選択旧assert保持、test helper41のsource閉包と旧snapshot不要を確認。Runtimeは旧096の12callback、現API/spool/Exportを選び、全故障/全worldは追加しない。IPA/実compiler/配布物/全sourceの最終確認はこれから。
