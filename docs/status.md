# 最新状態

更新: 2026-11-14（日本時間）。TEST098実装・選択単体・差分レビュー済み、IPA/CI確認中。**実機改善・受入は未確認**。[計画](plans/test098-route-observation.md)・[受領/検証](reviews/test098.md)・[修正表](fix-records.md)。単体/過去対策を到達成功へ数えない。

## 実機根拠と変更

097の3ZIP/64PNGを全照合。実順は添付1→3→2。実1の判定は8.382ms/期限内採用だが部分結果UNKNOWN。最初の拒否画像は未保持で原因未確定、後の234→242は旧条件でも成立。実2は17.908ms/期限内採用後、遠方FLOOR→UNKNOWNを拒否。実3は隣接DIRT→FLOORで未送信DOWNからLEFTへ判断が変わり停止。候補135も実判断元で見送り。

Navは旧段を保持し、5壁と外側床を必要とする有限の上左角候補を追加。Controllerは旧未送信票を撤回し、独立静止・固定anchor・新IDを必要とする直交側方開口の再観測を追加。実ACK済み同方向開扉後だけ遠方FLOOR消失を許容し、静的条件が全て同じで動き判定だけUNKNOWNなら入力0のまま元期限内で独立画像を待つ。新FULL/FLOORは旧票を破棄して新分類へ渡す。

最初の表現可能なcycle拒否を既診断へ記録。材質差0/MOTIONだけ現API rootで対応し、旧API/再帰/欠落detail/入力許可を伴う0は拒否。Runtime/public ABI不変。Ring/Bank/判定資産/G1/R12も不変、全商品登録・購入・宝箱開封0、UNKNOWN無再送・元期限/累積予算を維持する。

## 確認と次の実機

新規の意味assert Red→Green、候補45/側方22/部分39を影響範囲で確認。最後の診断guard訂正後は該当12だけ再確認、clientは実Python3.9の5件成功。最終source全選択のCIとIPA/実compiler/36seal/完全source照合はこれから。旧全world/全Runtime故障を今回の配布前提へ追加しない。

次は新IPA更新→LoopCtrl完全終了/起動→Start Server/通知許可/通常VPN。通常1-1ポーズから候補までrestart→接近/入店→3商品が見える位置→のろいのゆびわ判定→対象なしなら次周回、最大4商店。停止通知後iSHへ戻り全画像/記録/ZIP照合の終了を待ち、表示runtime/test-098-<UUID>.zip全体を返却する。

iPhone到達率/毎拍・人超え速度/未知対象精度/長期耐久は未受入。実1の最初の原因も未確定。対応外layout/対象候補は保持。遅延positive通知P1・ledger自動整理なしP2は旧記録を維持。[索引](context.md)。
