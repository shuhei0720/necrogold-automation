# TEST063: 確実未送信の期限切れ回復

2026-11-10（日本時間）。[短い計画](../plans/test063-unsent-deadline.md)。実機062はユーザーの商品可視1/2、プログラム完全商品判定0/2。前者の経路と認識を保ち、2回目の3歩目未送信だけを修正する。

旧Cの新規単体でCAPTURE終了の意味的assertion Redを確認、compile/errors0。修正Cの新12methodが2.169秒で成功、前後C/H/Beat/Nav/Perception/test SHA一致。complete0/begin/tick、SAME/FRESH、旧callback、未来拍と50ms準備、実commit/12秒/45/180秒、取消/UNKNOWN/商品/権限優先、実MOVED/開扉/茶壁proofだけの予算更新を含む。

独立差分レビュー1回でP0/P1なし。P2は同一tile配置のsignature-only driftがstrict BLOCKED不成立となる拒否の直接検査不足で、既存negative methodへsubcaseを追加し、同一grid/full5・actual motion UNKNOWN・回復拒否を明示して12件2.135秒で再確認した。既存assertを削除せず、広いRuntime/world/全clientを前提にしない。device CIは今回の新12＋前回の関連23、小CI検査15を実IPAと同じsourceへ結ぶ。

固定ダウンロードは汎用publish-downloadへ変更し、7入力をnetwork前に検査、固定repo/filenameと全SHA、空draft/tag/target所有、upload後3digest一致を確認してから公開する。ゲームコード/ABI/API15/cap13/client v14はController.c以外不変。CI/実IPA/全sourceの結果は配布前に追記する。

local device runnerも実patched sourceの22seal/ABIを前後照合し、C単体35＋小CI検査15の50件が成功。既存23の回帰は保持し、今回変更した境界に限定した。
