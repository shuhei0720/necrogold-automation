# TEST107: 商品投影と地形変化の合成・初歩前の観測再取得

2026-11-16（日本時間）。TEST106の8添付を4実行へ照合し、104 PNG/118記録/230 rawの原本をGit外へ保持した。要件・native契約・対象判定契約・FR104/105/106を適用し、旧単体成功を実機改善完了と扱わない。

## 原因

実1/2/4後半は、正常なPARTIAL UNKNOWNを採用した後の `cycle_observe` / ROUTE10で停止した。結果のKERNEL表示は後の継続検査失敗による上書きで、Ringの分類失敗ではない。商品帯は上端で切れており、さらにUPへ入店する必要がある。実1は上端ITEM投影増加と遠方DIRT→UNKNOWN、実2は既に許した上端alias縮退と金壁で遮蔽された対角床変化の同時発生。全Sceneを検査する独立述語のORでは、各々許可済みの変化を合成できない。実4後半は、下段ITEMが支持する保護された最上段セルのUNKNOWN→FLOORだけで拒否した。

実3はMOVE未送信のまま、起動直後の暗い原40とのMotion不明が続き、元待機Dで停止。原40→107だけUNKNOWNで、元D内・同prefixの原87→88は通常Motionの厳密零。古い画像からの零変位を捏造せず、初歩前に限って元D内で最新の独立2画像から観測を再取得する。

実4前半の原197は通常policy9の完全陰性・全3商品/3価格・flags0。保存→intent15→実RESTART ACK15→新floor225まで原記録で成立した。判定器を陰性へ緩める変更は不要。

## 変更の範囲

1. PARTIALの上端投影をセルの役割として分離する。旧新の正確なITEM保護mask、不変のrow−4の連続ITEM列3以上、ITEMが上端2行以外に存在しないこと、移動原点/次床・完全Decision・独立厳密零・同開扉ACK・元prefix/Dを要求する。投影域以外の旧GOLD/ITEM/保護を維持し、残セルは既存のdistant_dirt/shielded条件で検査する。任意の旧特例を無条件に合成しない。
2. 最上段の新ITEM投影は、直接下段ITEMで支持された役割域だけを扱う。旧GOLDを含む背景ラベルの重なりもこの域以外へ漏らさない。既一用のdata rebindへ渡し、新しい正常判定と別の静止確認を得るまで旧結果でMOVEしない。直接下段に支持された保護topセルの非ITEM材質変化も、新対象を見逃さないよう同じ一用再判定へ渡す。alias縮退と既許可の残セル変化は静的関係として合成する。`cycle_refresh_safe`、対象/候補/強語/新FULLの優先、one-use/元親期限を保持する。
3. 実3は初歩前・物理MOVEなし・位置/lead/input stateが初期・商品/保護なし・actual GOLDの限定条件でdata-only再取得を開始する。古い票/候補経路の権限を撤回し、最新画像をデータ基準にして、次の独立画像の同GOLD/同Nav選択/厳密零で通常の新sourceへ戻す。既replan枠をepisodeごとに消費し、確定済みの元待機D/horizon/同期epoch/歩行・session予算を更新しない。観測Beat modelは通常の鮮度/位相資格で維持する。MOVED/非零、古prefix、商品候補、送信中・初歩後などでは許可しない。

既entry episodeの一斉拡張は、非空入口・longrail・潜在ROI・全セル一致の4境界変更が必要なので今回採用しない。Ring/Nav/Perception/Runtime/Wire/公開ABI/cap/API/既feature/canonical15/ELF/G1/R12は同一bytesを保持し、nativeはControllerだけを変更する。

## 検証

新しい期待値と全実行依存sourceを実装前に凍結し、assertion Red→最小Green。新関係の合成、下段支持欠落・他下段ITEM・保護loss・非alias GOLD/近傍・偽mask・非独立/非零・prefix/D/取消/古票の拒否を確認する。新ITEM/data再判定→最新正常結果→別静止→UPの実ACK/MOVED→最新正常判定をつなぎ、完全陰性が成立した合成配置では保存/intent/実RESTART ACK/次floorまで確認する。最初の一歩だけを実機到達の改善としない。

旧101の `test_real_lower_item_and_protection_loss_are_not_duplicate_top_aliases` のoutside subcaseだけは、支持されたalias縮退＋従来許可の遠方STONE→DIRTが新しい合成証明で適格になるため、理由/旧新SHA/限定diffを残して期待を更新する。他のlower ITEM/保護loss/近傍fault・旧105 protected_floorなどの拒否assertは保持する。

初歩前再取得は元D/episode回数、MOVEDのsticky失効、古票/古prefix/商品/初歩後・非独立の拒否と、新しいsourceによる将来拍の票まで確認する。新しい構造を必要とする境界だけ関連結合を追加し、無関係な全Runtime/合成world/全Ring試験は増やさない。独立差分レビュー1回・選択CI・新IPA/source/実compiler/実物照合後、固定Releaseで通常1-1ポーズから連続実機テストを依頼する。校正/単体/CIを実機改善完了や速度達成にしない。
