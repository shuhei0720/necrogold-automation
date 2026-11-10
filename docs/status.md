# 最新状態

更新: 2026-11-10（日本時間）。TEST064 ZIPを正式受領し解析再開。ユーザーの商品可視3/4、自動の全商品可視判定完了2/4。1/2回目はGOODS保持とポーズ成立、3回目は商品可視だが自動未完了、4回目は2歩後にLATE。全59PNGのSHA/bytes/CRC/896×414とmanifest一致、4run terminal/drained/resolved、active=4回目を確認。回収済み064を再実行しない。[受領台帳](device-tests/README.md#test064-received)。

## TEST065: 再予約待ちの未送信期限切れ回復

[計画](plans/test065-pending-unsent.md)。4回目の3歩目MOVE5は原画91→92の遠方(2,2)DIRT→FLOORをSAME再検証で許可し、元eventをnot_sent/begin0へ撤回済み。capture endはD−25.952ms、C開始D−3.816ms、C終了D+3.152ms、次tickD+3.357ms。state0/currentID0/pendingのため旧063のstate1回復を通れずLATE終了。原画はFLOOR/商品UNKNOWN/金候補/全5field UP reason8 target(-1,-2)/床/strict BLOCKEDが成立していた。

state0のSAME/FRESH再検証済み・旧event not_sent/begin0/reasonSCREENに限定し、actualtickで元Dを超えた時だけ既存post_moveへ戻す。再検証時の最新判断全5fieldを両modeで保存し、回復時のbefore/最新判断、全tile/保護/金/strict BLOCKED/fresh prefixを再照合する。旧event全bytes/旧ID拒否を保ち、新将来拍を選ぶ。SAME reason8の許可済み遠方target driftも保存判断で検査する。

最後の実proof commitから元12秒/継承sync、45/180秒、再予約counterと将来50ms準備を維持。真の新proofなしにepisode/予算を増やさず、商品/取消/owner/lock/UNKNOWN/送信済みを除外。期限内失敗/model失効だけの回復を広げない。Controllerだけ変更、Runtime/Nav/Perception/API15/cap13/ABI/client v14と064成功経路は不変。

## TEST064で実機確認したこと

- 1回目2eef…は6入力/4確認移動/開扉1、原画149で3商品・価格100/100/100が見え、goods保持→自動PAUSE成立。商品後の方向入力0。
- 2回目4cb4…は7入力/5確認移動/開扉1、下方商品へ追加LEFT後に商品可視。原画205はVISIBLEだがprefix不安定、reportの安定206で保持・ポーズ成立。206原画はexport省略を区別する。商品後の方向入力0。
- 3回目d8c5…は7入力/6移動/開扉1、原画で3商品・価格25/100/100が見える。看板等が画面外で自動はUNKNOWN。167→168遠方DOOR→GOLDで金集合が変わるため契約通り入口MOVEを未送信拒否。認識/金ガードは今回緩めない。
- 4回目070f…は2入力/2移動、入力不明/画像取得障害なし。再予約待ちC処理の期限越えを065で対象にする。

2回目の歩行入力間隔は約0.508〜0.529秒。他の回には約1.04秒の空きがあり、開始待ちも残る。毎拍/人より速い全体要件、対象指輪の識別/通知/自動周回/耐久は未受入。

## 065の確認・返却

旧Cで新pending6methodの意味的Red（compile/errors0）を確認。新6+旧expiry1の7件Green、独立差分レビューP0/P1/P2なし。変更単体/関連回帰、device IPA/22seal/実compiler/Mach-O/完全sourceの照合後、固定Releaseで新TEST065実機を依頼する。全Runtime/world/不変clientを毎回の前提にしない。

## TEST064の配布記録

[固定IPA build98](https://github.com/shuhei0720/necrogold-automation/releases/download/test064-build98/LoopCtrl.ipa)・[固定全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test064-build98/source.zip)、[検証](reviews/test064.md)。code3d8334249394ae81ed8d449d4925dc2eb85c35d3、source7824214960db9c5d523af64fdc545db75402f279、Mac98/device成功、Mac99固定公開成功。

IPA SHA `34a588f1e53808f97e62681df83513b9d1b38456d66dfda8bc0e5a4992af0c53`、全source SHA `84ba53699e0687240df2f4775ac8c8a0bdc07b25fe2c6ece53f3603517fa56b8`。064のC27+selector3、実compiler/22seal/9Mach-O/488tracked source照合は過去の確認として保持。064の新規再ビルド/試験は依頼しない。

## 運用

[最新方針](development-flow.md#最新の運用方針2026-11-10-日本時間): 実機ログ→局所修正→単体/関連回帰→必要なIPA/同一性確認→次の実機。固定時間なし/品質安全条件不変。通常レビュー1回。コード/資料は承認済みbranchへ保存、raw資料/秘密値はGit外。配布は期限付きでない固定Release asset。

ユーザーはMacを持たず通常利用はiPhone単体。添付接続エラーは[履歴](device-tests/README.md#test064-reported)へ保存、今回はZIP受領に成功したが根本原因を断定しない。初読3文書≤16KiB、追加資料は[索引](context.md)。
