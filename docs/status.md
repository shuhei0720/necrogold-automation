# 最新状態

更新: 2026-11-10（日本時間）。TEST065の4run/67PNGを受領し全SHA/bytes/896×414/CRC/manifest一致、全run terminal/drained/resolved、active=4回目を確認。1回目は自動全商品可視とPAUSE、2回目は入店したが2商品しか見えず、3回目は3商品が見えるが自動PARTIAL、4回目は店前で停止。回収済み065を再実行しない。[受領台帳](device-tests/README.md#test065-received)。

## TEST066: 開扉・店内歩行とアイコンの断片

[計画](plans/test066-shop-action.md)。Controller/Perceptionだけ変更する。Runtime/Nav/Beat/API15/cap13/client v14/ABIと入力・同期・商品保護の基本条件は維持。

- 4回目141→142: nextDOOR/LEFT/reason5の全5field・金/保護/局所・strict BLOCKED不変。遠方2cellのSTONE→DIRTだけでFLOOR限定quietから漏れた。既存同IDquietへ同DOOR不変の開扉1操作を追加し、開扉と進入を別に確認する。
- 2回目166→167: 実入口通過済み、PARTIAL、reason8/FLOORの同判断。遠方1cellだけの変化でも停止した。entrance.valid=1/両PARTIAL/同full5・origin/next床・金/全保護/近傍・strict BLOCKED・元時刻/予算を満たす次1歩だけ同ID維持。入口未通過の同形PARTIALは拒否する。
- 3回目143: 取得画像のラベル付近でアイコンのバー支持が11/12pxへ分断。既存opening13を優先し、失敗時のみ11を検査。明度55/85、IoU0.8、全HUD/continue・death条件は維持。67原画中143だけUNKNOWN→FLOOR/PARTIALへ改善、他66は全Scene bytes同一。修正後141/143は全tile/保護/金/判断/strict BLOCKEDが同じで、そのframeの別変化拒否はない。未収録の先の商品可視は実機で確認する。

既存safe_floor/lead校正/retune/再予約/referenceは拡げない。旧ID/元source/拍/全期限、元proof12秒/45・180秒、50ms準備、UNKNOWN無再送・商品/取消/owner/lock/prefixを維持する。

## 歩行の確認と優先順位

送信23操作は20MOVED/3開扉。送信済みのBLOCKED/UNKNOWN/逆移動0、全beginは元10ms窓内でNBから0.287〜9.440ms。通常間隔約0.514〜0.532秒、空き約1.04〜1.57秒、初回の再fit待ちは3.124秒。初動はfloor→begin約2.13〜2.25秒。

初回のVISUAL_PHASEで候補周期532.068msがprofile上限530msを外れて同期資格を撤回。他にも未送信期限切れや遅い実変位確認で再取得していた。空拍と送信済み失敗を区別する。ゲーム受信時刻/動画がなく『拍ずれゼロ』は断定不可。ユーザーは現速度を暫定許容し得ると述べ、今回は停止と商品確認の安定化を優先。毎拍/人超えの恒久免除とはせず、識別/通知/自動周回/耐久も未受入。

## 066の検証と返却

新door6/shop4/icon6をそれぞれ旧Cで意味的Red→修正Green。shop/doorと旧gateは16件Green、icon6+既存syntheticguard1もGreen。独立レビューでP0/P1なし、P2の入口未通過PARTIAL負例をpublic ACK+MOVED系列で既存negativeへ追加、4method不変でGreen。device CIの34件と実IPA/22seal/実compiler/Mach-O/完全sourceを照合後、固定ReleaseのTEST066を依頼する。全Runtime/world/不変clientやprivate画像群をCI既定にしない。

## 受領した065の要点

自動可視完了1/4。1回目は63/200/100の3品、2回目は下端125/75の2品だけで第三枠が未表示。3回目は13/13/50の3品が人に可視だが、アイコンの誤拒否で停止。4回目は未開扉。画像に見えない商品を対象なしとせず、候補/購入禁止を維持する。

[065固定Release build100](https://github.com/shuhei0720/necrogold-automation/releases/tag/test065-build100)・[検証](reviews/test065.md)。Mac100/device32とMac101固定公開成功、2asset変更前の22seal/全9Mach-O/492source照合は過去結果として保持。065の新規再ビルドは行わない。

## 運用

[最新方針](development-flow.md#最新の運用方針2026-11-10-日本時間): 実機ログ→局所修正→単体/関連回帰→必要なIPA/同一性確認→次の実機。固定時間なし/品質安全条件不変。通常差分レビュー1回。承認済みbranchへコード/資料を保存、raw ZIP/画像/report/log・秘密値はGit外。配布は固定Release asset。

通常利用は同じiPhoneだけ、ユーザーはMacを持たず実機担当。初読3文書≤16KiB、追加資料は[索引](context.md)。
