# 最新状態

更新: 2026-11-10（日本時間）。TEST065の4run/67PNGを受領し全SHA/bytes/896×414/CRC/manifest一致、全run terminal/drained/resolved、active=4回目を確認。1回目は自動全商品可視とPAUSE、2回目は入店したが2商品しか見えず、3回目は3商品が見えるが自動PARTIAL、4回目は店前で停止。回収済み065を再実行しない。[受領台帳](device-tests/README.md#test065-received)。

## TEST066: 開扉・店内歩行とアイコンの断片

[計画](plans/test066-shop-action.md)。Controller/Perceptionだけ変更した。Runtime/Nav/Beat/API15/cap13/client v14/ABIと入力・同期・商品保護の基本条件は維持。

- 4回目141→142: nextDOOR/LEFT/reason5の全5field・金/保護/局所・strict BLOCKED不変。遠方2cellのSTONE→DIRTだけでFLOOR限定quietから漏れた。既存同IDquietへ同DOOR不変の開扉1操作を追加し、開扉と進入を別に確認する。
- 2回目166→167: 実入口通過済み、PARTIAL、reason8/FLOORの同判断。遠方1cellだけの変化でも停止した。entrance.valid=1/両PARTIAL/同full5・origin/next床・金/全保護/近傍・strict BLOCKED・元時刻/予算を満たす次1歩だけ同ID維持。入口未通過の同形PARTIALは拒否する。
- 3回目143: 取得画像のラベル付近でアイコンのバー支持が11/12pxへ分断。既存opening13を優先し、失敗時のみ11を検査。明度55/85、IoU0.8、全HUD/continue・death条件は維持。67原画中143だけUNKNOWN→FLOOR/PARTIALへ改善、他66は全Scene bytes同一。修正後141/143は全tile/保護/金/判断/strict BLOCKEDが同じで、そのframeの別変化拒否はない。未収録の先の商品可視は実機で確認する。

既存safe_floor/lead校正/retune/再予約/referenceは拡げない。旧ID/元source/拍/全期限、元proof12秒/45・180秒、50ms準備、UNKNOWN無再送・商品/取消/owner/lock/prefixを維持する。

## 歩行の確認と優先順位

送信23操作は20MOVED/3開扉。送信済みのBLOCKED/UNKNOWN/逆移動0、全beginは元10ms窓内でNBから0.287〜9.440ms。通常間隔約0.514〜0.532秒、空き約1.04〜1.57秒、初回の再fit待ちは3.124秒。初動はfloor→begin約2.13〜2.25秒。

初回のVISUAL_PHASEで候補周期532.068msがprofile上限530msを外れて同期資格を撤回。他にも未送信期限切れや遅い実変位確認で再取得していた。空拍と送信済み失敗を区別する。ゲーム受信時刻/動画がなく『拍ずれゼロ』は断定不可。ユーザーは現速度を暫定許容し得ると述べ、今回は停止と商品確認の安定化を優先。毎拍/人超えの恒久免除とはせず、識別/通知/自動周回/耐久も未受入。

## TEST066の配布と実機確認

導入確認待ち: SideStoreが`Archive appears to be corrupt: LoopCtrl.ipa`と表示。端末表示サイズ17.5MBだけでは欠損判定不可。公開IPA再取得は17,582,349bytes/元SHA一致・全CRC正常、正常065とZIP構造/全4plistはbuild番号以外同じ。端末上の実bytesと展開処理は未確認。SideStore自身の1DAYを更新し、新規ローカル保存から導入を切り分ける。IPAの再ビルド/差替えは行っていない。

code `d16367570d12456c668648584253d721880b9e41`、[Mac102](https://github.com/shuhei0720/necrogold-automation/actions/runs/42774588299) device34件成功。新door6/shop4/icon6は旧Cで意味的Red→Green、独立レビュー最終P0/P1/P2なし。実IPA/build102 SHA `080acc55eb847baaf1ea3a9db53a6b89fe7d94ec00dff50acecaeb9052f550c5`。host全ID/生ログ/ABI/22seal前後、実4C/5Swift/6RSP、strictO2 profile、全9Mach-Oの103禁止marker非混入を照合。Controller/Perception以外20source、R12原40/G1は不変。build-source全498tracked bytes/path/CRC一致。実ゲームCIと066実機は未実施。

[新IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test066-build102/LoopCtrl.ipa)・[完全source ZIP](https://github.com/shuhei0720/necrogold-automation/releases/download/test066-build102/source.zip)・[SHA256SUMS](https://github.com/shuhei0720/necrogold-automation/releases/download/test066-build102/SHA256SUMS.txt)。固定Releaseへ配置する。最終sourceはビルド対象から文書3件だけ異なり、code/launcher/testsは同じ。詳細は[検証](reviews/test066.md)。全Runtime/world/不変client/private画像群をCIへ累積しない。

SideStoreで新IPA更新→LoopCtrl完全終了・起動→Start Server、通常のVPN/ディスク設定。source ZIPを展開し、新通常All Zones 1-1の金壁可視ポーズからiSHで実行する。フォルダ選択は`test_066.sh`のある展開先。

```sh
mkdir -p /mnt/necro_test066
mount -t ios . /mnt/necro_test066
cd /mnt/necro_test066 && sh test_066.sh
```

歩行中はゲームを前面に保つ。自動ポーズ後約5秒でiSHへ戻り`TEST-066: 終了`を待つ。`runtime/test-066`全ZIPと商品3品が見えるか/停止位置を返してもらい、到達率を評価する。複数回は新しい通常1-1で行い、既収録065は再実行しない。

## 受領した065の要点

自動可視完了1/4。1回目は63/200/100の3品、2回目は下端125/75の2品だけで第三枠が未表示。3回目は13/13/50の3品が人に可視だが、アイコンの誤拒否で停止。4回目は未開扉。画像に見えない商品を対象なしとせず、候補/購入禁止を維持する。

[065検証](reviews/test065.md)は過去結果として保持し、新規再ビルドしない。

## 運用

[最新方針](development-flow.md#最新の運用方針2026-11-10-日本時間): 実機ログ→局所修正→単体/関連回帰→必要なIPA/同一性確認→次の実機。固定時間なし/品質安全条件不変。通常差分レビュー1回。承認済みbranchへコード/資料を保存、raw ZIP/画像/report/log・秘密値はGit外。配布は固定Release asset。

通常利用は同じiPhoneだけ、ユーザーはMacを持たず実機担当。初読3文書≤16KiB、追加資料は[索引](context.md)。
