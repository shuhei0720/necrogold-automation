# TEST065: 未送信の再予約待ちで期限を超えた場合の再同期

2026-11-10（日本時間）。TEST064は実機の商品可視3/4、自動商品判定完了2/4。4回目は2歩後のMOVE5を1度も送らず、SAME再検証のC処理中に元Dを超過し停止。画像取得/入力不明ではない。成功した認識/歩行経路を維持し、この停止だけを修正する。

## 原因・変更

91→92の遠方DIRT→FLOORは既存SAME条件に適合し、旧MOVE5はnot_sent/outcome3/reasonSCREEN17/begin0へ撤回済み。capture endはD−25.952ms、C開始D−3.816ms、終了D+3.152ms、次tickはD+3.357ms。state0/currentID0/continuous_pendingのため、[063の確実未送信回復](test063-unsent-deadline.md)のstate1条件を通れず、再予約待ち分岐がLATE終了していた。

既存recover_unsent_continuousを、state0/currentID0でSAME/FRESH再検証済み・旧eventが確実not_sent/begin0の待機状態に限り適用する。tickの純D超過時だけ旧pendingを撤回し、既存post_moveの新将来拍を選ぶ。元eventの全bytesを保ち、旧ID/元Dでの送信やcallback復活を許さない。SAME/FRESH両方で再検証時の最新判断全5fieldをpending_choiceへ凍結し、回復時のbefore/最新判断と照合する。元source全5fieldの証明は既存再検証が維持し、SAME/reason8の許可済み遠方target driftも新しい保存判断で検査する。両SceneのFLOOR/商品UNKNOWN/金候補/origin床、全tile/保護不変・strict BLOCKED・fresh prefixを再検査する。

最後の実MOVED/開扉/掘削commitからの元12秒、継承command_sync_deadline、walk45/session180、再予約counter、最新HUDと将来拍の50ms準備を維持する。真の新proofなしにepisode/予算を増やさない。取消/owner/lock/商品VISIBLE/送信済み/UNKNOWN、期限内complete0、D内のmodel/horizon失効だけを回復対象にしない。Runtime/Nav/Perception/API15/cap13/ABI/client v14は不変。

## 期待・検査・配布

元92を実Cで評価し、full5とstrict motionの適合を確認する。新単体は旧Cのassertion Red→修正Green、SAME/FRESH pending・実commit越境・旧eventと旧callback不変・将来50ms・繰返し元12秒/45/180・権限/商品/prefix/署名/入力状態の負例を選ぶ。旧pending失効テストの期待は元D/旧ID拒否を保ち、新しい将来拍への有界回復へ根拠付き変更する。既存assertを隠す選択をしない。

064の初歩/入口成功経路とpending/063境界の関連回帰、独立差分レビュー1回、device IPA/22seal/実compiler/Mach-O/完全source照合後、固定ReleaseからTEST065の実機試験を依頼する。全Runtime/world/未変更clientを毎回の前提にしない。3回目は既知金集合が変わるため安全拒否し、商品が見えているという人の観察と自動完了を分ける。認識閾値/金ガードを今回緩めない。
