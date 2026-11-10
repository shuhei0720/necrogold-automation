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

## TEST065配布・実物検証

固定配布: [IPA build100](https://github.com/shuhei0720/necrogold-automation/releases/download/test065-build100/LoopCtrl.ipa)・[完全source ZIP](https://github.com/shuhei0720/necrogold-automation/releases/download/test065-build100/source.zip)。code `51f555d47b7d703935e8ae2c032ba1ff446a3f1a`、[Mac100/device](https://github.com/shuhei0720/necrogold-automation/actions/runs/42758476882)成功。[検証](reviews/test065.md)。TEST065の実機は未実施。

| 配布物 | 同一性 |
| --- | --- |
| 内部IPA | build100 / SHA `e33fee16d42cdaaa636ecc3ff9002100f46115078c722b67a482714e7cc8d6b7` |
| IPA外ZIP | artifact13736797666 / 17,842,408bytes / SHA `a73af05f1908f8f03dd12c29410bcb6a600552eeb0d56543d28f058cc376df55` |
| 診断ZIP | artifact13736558404 / 156,886bytes / SHA `3362a51ec4774ed59108637bb3551dd1b1d717b439ec045bfac51d5f3755996f` |
| native-host | artifact13736137901 / 7,525bytes / SHA `3bfef14672baaa189e0d8f7af59b5593b620bd3ebfaa9acdb84b276754f9cfda` |
| build-source | 全492tracked bytes/CRC/path一致、7,327,230bytes / SHA `3d5f6c46b1c6c86efbc7c234f76f784eb0f9b7bc476394eea2af80c7ecbaf605` |

新pending6+関連23のC29、selector3の32実行ID/生ログ/0skip/error/ABI/22seal前後が実IPAと一致。実4C/5Swift/6RSP/PBX/raw compiler引数と全9Mach-O/102 HOST・旧API marker非混入を照合。Controllerだけ変更、他21/R12原40/G1/API15/cap13/client v14/ABI不変。独立差分レビューP0/P1/P2なし。最終source差分はstatus/review/台帳の3文書のみを確認して固定保存する。全Runtime/world/不変clientは今回の配布前提にしない。

## 次の実機TEST065

SideStoreでIPA build100更新→LoopCtrl完全終了/起動→Start Server→通常VPN/disk。新しい通常オールゾーン1-1、金壁可視・左側が下/端0の開幕ポーズから。

```sh
mkdir -p /mnt/necro_test065
mount -t ios . /mnt/necro_test065
cd /mnt/necro_test065 && sh test_065.sh
```

folder pickerはsource ZIPを展開しtest_065.shが入るフォルダ。歩行中はゲーム前面、自動PAUSE後約5秒でiSHへ戻り「TEST-065: 終了」を待つ。商品可視位置への到達・停止した様子とruntime/test-065全ZIPを依頼する。回収済み064は再実行しない。

## TEST064の配布記録

[固定Release build98](https://github.com/shuhei0720/necrogold-automation/releases/tag/test064-build98)・[検証](reviews/test064.md)。Mac98/deviceとMac99固定公開成功、C27+selector3/実compiler/22seal/9Mach-O/全488source照合は過去結果として保持。現在の実機結果は上記3/4商品可視・2/4全商品可視判定、64の再ビルドは行わない。

## 運用

[最新方針](development-flow.md#最新の運用方針2026-11-10-日本時間): 実機ログ→局所修正→単体/関連回帰→必要なIPA/同一性確認→次の実機。固定時間なし/品質安全条件不変。通常レビュー1回。コード/資料は承認済みbranchへ保存、raw資料/秘密値はGit外。配布は期限付きでない固定Release asset。

ユーザーはMacを持たず通常利用はiPhone単体。添付接続エラーは[履歴](device-tests/README.md#test064-reported)へ保存、今回はZIP受領に成功したが根本原因を断定しない。初読3文書≤16KiB、追加資料は[索引](context.md)。
