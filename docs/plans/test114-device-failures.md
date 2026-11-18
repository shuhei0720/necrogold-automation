# TEST114: TEST113実機5周の停止修正

2026-11-18（日本時間）。製品基準はTEST113/build230、CODE a565681、現在の保存HEADはdocsのみ更新した25d9f0d。原因を確定してから変更し、ソフト試験を実機改善完了とは扱わない。

## 受領と対応

11 ZIP＝5 campaign/6固有run、144 PNG/163記録。全CRC/path/hashchain/参照/PNG→原RGBA SHAを検証し、campaign内5ZIPは個別添付と完全一致した。原本はGit外。添付順ではなく端末の実started時刻で対応する。

| 利用者の周/回 | run先頭 | 確認済みの結果 |
| --- | --- | --- |
| 1/1 | 74cb | 商品可視後、通常UNKNOWN source164/job2、policy9/ROWS256、約18.48ms。最終SCREEN17 |
| 2/1 | f7ed | 通常UNKNOWN source251/job3、policy9/ENDCAP16、約43.18ms。未採用・最終SCREEN17 |
| 3/1 | 78e2 | 利用者が対象を確認。原236を通常producerでcandidate再現、C採用・候補保持・PAUSE241。TARGET確定とは区別 |
| 4/1 | b4fd | 正常リスタート後、restarted_budget handoffを許可し実際に次UUIDへ進行 |
| 4/2 | 9c57 | 新UUIDで方向入力/移動0。RESUME→探索PAUSE→RESTART後、live原91からPAUSE原92へ変化しSCREEN17。追加PAUSE命令は公開Cのeventにない |
| 5/1 | bedf | 商品可視後、通常UNKNOWN source98/job2、policy2/BOARD2+ROWS256、約11.91ms。最終SCREEN17 |

全journalはcancel_intent=false/last_error=null。前版のdraining応答拒否による取消と同じ原因とはしない。アーカイブのpublished=falseは公開前snapshotとしてそのまま保存し、判定を通すために書き換えない。

## 原因確認と修正範囲

1/2/5周は、通常producerの不完全理由、判定中の新画像、元sourceとの直接関係、worker終了・採用・PAUSE予約の順序を突き合わせる。FR-113-FULL-NORMAL-UNKNOWN/UPPER-HUD-VIEW/REVIEW-PAUSE-INVALIDATIONと比較し、同症状の継続・同根因・回帰を分ける。原画像で成立しない移動/不在を仮定せず、正常UNKNOWNを陰性へ変換しない。

4周2回目は、game側のPAUSE変化と既Runtime/G1の全入力経路・旧owner callback・前面状態を調べる。ユーザー操作と断定しない。原因が未記録なら未確定と明記し、意図不明のPAUSEを無条件で再開して停止契約を壊さない。

3周目は実画像の対象をcandidateとして検出・保持した成功を固定する。exact icon約.934が既policy16の.94に届かずTARGETにしないことと、検出してPAUSEしたことを区別する。価格250は画像上の観測であり数値固定/OCRの新条件にしない。今回この正例だけへ合わせてglobal閾値やbankを変更しない。

## 検証と進め方

### 限定設計: 同じ看板対と現在画像の再資格化

概要/背景: 1/2周は同じ実SHOP成分対から作られた数値行の重複で既存の完全証明へ到達しない。全数値行を残し、成分対・SceneのITEM投影が完全一致する場合だけ物理行の数を数える。全aliasの既存5セル・広域文字検査の和集合を維持し、既policy9/15の各数値証明は緩和しない。先行した不完全な別aliasだけで、後続の成立する既policyを遮らない。

詳細設計: 5周のsource98は判定中の変化で正しく無効になり、現在100もHUD遮蔽でUNKNOWN。同じ旧画像の入力権限を復活させず、元episode内の独立した最新FULL画像を共用DATA最大2回の1回として通常判定する。元hard無効化・親期限・旧MOVEのUNKNOWNは保持する。実worker drain後だけ開始し、current画像独自の3ITEM/正のUP床/保護/GOLD/固定HUD保存範囲を確認。旧履歴のcapture/jobを付け替えて入力証明にしない。

入力資格: 新anchorへ直接strict零となる独立した後続2画像、最後の証明以降の実sampleを含む新fit、元親期限内の新ticketが必要。anchorの移行や零の連鎖は不可。既一回の追加観測枠と元ordinal順を守り、旧未確認MOVEを加算しない。PAUSE予約の撤回は同一ownerの確実未送信だけに限定し、begin/ACK/不明なら再開しない。候補が先、実drainとowner/世代/prefix/全期限・予算を維持する。UP後も新画像の通常完全証明なしに陰性/RSへ進めない。

試験影響/新規ケース: Ringの重複対・別対・別投影・欠落商品/価格/床・alias端の対象/文字・元期限/取消を手続き的画像で確認する。Cは初回FULLの通常完全陰性の採用、および旧hardを残した独立current epochの正例と一枚だけ/連鎖零/旧fit/旧履歴の流用/PAUSE開始済み/予算・期限切れの拒否を公開APIで確認する。実164/250/251と候補236の通常producer校正は調整資料であり未知評価ではない。

順序/コミット前検査: 独立設計レビュー→新assertionの旧source Red→担当を分けたRing/Cの最小変更→直接関連回帰/候補保持→独立差分レビュー→変更した実Runtime境界だけMac結合→IPA/全source同一性確認。公開Cの論理pendingと実worker drainを混同しない。source250の初回job時刻とUP後の未来画像は未保存であり、ソフト試験を実機再現とはしない。

範囲外: 閾値/HUD除外領域の緩和、対象商品の追加登録、Nav/G1/R12変更、期限や入力枠の増加、ポーズ原因の推測による自動再開。4周2回目のPAUSE発生源は未確定で、停止前に利用者が触ったとは扱わない。

原因と必要なguardを実画像・時刻・状態から先に固定し、変更前assertion Red→最小修正→対象Greenと直接関連回帰を選ぶ。通常の独立差分レビュー1回を基本とし、入力権限や並行境界を大きく変える場合だけ該当設計・結合を追加する。既assert/拒否条件は削除せず、不可避の期待値変更は正本と前後両sourceの証跡へ限定する。

原3周目のcandidate保持と原4周目の正常保存/次UUIDを回帰基準にする。未収録の未来画像や応答を合成した試験は実機再現と呼ばない。native変更時は同じコードのIPA/実compiler/保持資材/完全sourceを照合し、固定Releaseと匿名取得まで確認する。提出時は各停止の原因・具体的な変更・確認方法・実機未確認を列挙する。

## 維持条件

対象候補の保持、自動購入禁止、UNKNOWN入力の無再送、owner/世代/prefix/取消、元source/親期限と16入力/12restart/45秒/180秒、Ringの既閾値・G1/R12/feature/ELFを維持する。明るさ設定・遠隔/iPhone8方式・全商品名登録・無関係な整理を混ぜない。
