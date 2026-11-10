# TEST067: 移動確認の遅れ・文字変化・入口の既知未移動

2026-11-10（日本時間）。baseline `0a7062aeccc9fe10eda931223c6c75f000266bf2`。TEST066の2run/全30収録PNGはSHA/bytes/CRC/896×414/manifest/時刻prefix一致。両run native terminal/drained/input0/PAUSE。2回目回収は未完了（選択5枚欠損、35.part）、1回目判定125はexport省略。未収録の画像/ゲーム応答を補わない。

## 原因と期待動作

1回目は6送信/5MOVED+最終BLOCKED、入店/商品を確認できずmovement停止。入力間隔約1.04秒、5回とも確認後の予定再取得。2回目は4送信/3MOVED+最終UNKNOWN、間隔1.562/1.048/.515秒。10入力とも元10ms窓内。初動約2.5秒。送信済み失敗/未確認2件を065の成功23件と混同しない。

初画像UNKNOWN後の第2評価が元周期1/4待ちで、約60msの取得間隔と重なり次拍に間に合わない。第2評価を元周期1/10（約52ms）へ変更、第3は元1周期、最大3評価/元visualD/同ID/ACK・prefix/UNKNOWN無再送は維持。未収録の中間画像で早期MOVEDが成立するとは断定しない。

2回目69→83は背景が正方向1tile動くが説明文字の消失を含み、元高score補助のtexture bad7.65%でUNKNOWN。元経路は保持し、UNKNOWN時だけ高contrast（median差6以上）の追加証拠を許す。原73候補/最良score/gap.08を維持し、正方向exact9・両FLOOR/GOODS_UNKNOWN/GOLD_CANDIDATE・床/保護なし・closed translationとunique gate両方が必須。300支持/95%/他全72候補へ15pp差/2独立領域各100を弱めない。原画83は支持518/bad21/2領域で成立、75/77は未確定のまま。静止/逆/2tile/金変化/保護/非床/低texture/曖昧像を拒否する。

1回目125の物理的な未移動原因は未特定。lead確認済み・実移動後、観測済み金bracketの同FLOOR入口reason5だけ、両Scene/判断全5field/全tiles/全金/全保護/近傍不変・ACK-known/strict BLOCKED・元visualD内なら、1run最大1回だけmodelを撤回してfresh HUD fitと将来拍から新IDを選ぶ。旧BLOCKED event/歩数/開扉/lead/latest_verifiedは不変。UNKNOWN再送、初期retune、非入口、DIRT/DOOR、2回目BLOCKEDは対象外。入力16/元verifiedから12秒/45秒/180秒と商品/取消/owner等を維持。診断reason6 VISUAL_SCHEDULEは実行予定の再取得とし、拍推定失敗は捏造しない。observeのACTUAL_COMMITで消去前model/rawをsnapshotしてから撤回し、最初tickの親visualD検査と記録不変を維持する。freshfit後の新ticket発行前とaccepted predispatch画像で元入口/全5field・全tile/金/保護/strictBLOCKEDを再証明し、DIRT等へのFRESH変換も拒否。限定許可はactualbeginまで保持し、beginは最新証明capture IDを定数時間確認、終了時は撤回する。

## 実装・検証・返却

Controller/Navigationだけの局所修正。Perception/Runtime/Raster/Beat/API15/cap13/ABI/client v14は不変。新cadence/blocked/motion public単体で旧Cの意味的Red→最小Green。元cadenceの期待は第2境界だけ根拠付き更新し、全assert/拒否・第3境界を保持する。関連gate/quiet/pending/ABIとmotion公開回帰を選び、Runtime/world全体は変更しないため既定実行しない。並行/取得/入力経路自体は不変。

独立差分レビュー1回後、標準Macで変更単体/関連回帰と新IPAを実ビルドし、22seal/実compiler/全Mach-O/全sourceを照合して固定Releaseへ配置。到達率・毎拍・安定性は新しい実機で評価し、TEST067の新IPA/完全source/再起動・Start Server/iSH手順/終了後runtime/test-067全ZIPを必ず依頼する。回収済066を追加回収だけのために再実行しない。
