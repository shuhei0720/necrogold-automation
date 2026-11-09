# TEST061 設計・検証記録

2026-11-10（日本時間）。[計画](../plans/test061-verified-progress.md)。初歩同期、入力/観測期限、次行動再取得、商品到達までを一つの状態遷移として検討する。原060は受領台帳に記録済み。

## 独立設計レビュー

第1周は設計P1(期限短絡後complete0経路)/P2(診断保持寿命)、網羅P1×2(ACK中track失効、実producer→暗号client)/P2×2(確認後episode境界、独立world経路)、安全P1×2(全proofのactualcommit時計、保存revisionとAPIの回復)/P2(必須閉診断schema)。P0なし。

第2周は当該差分だけ再確認し全指摘解消、3担当とも残P0/P1/P2なし。初歩旧callback無効化、元12秒、actualobserve_atと全proof後tick、snapshot消去前のfirst/latest保持、旧API回復、v14診断必須を計画へ明示した。静的設計レビューであり、実装・実機成立の証明ではない。

## 選択する検証

Controller全methodは変更が広いため実行。変更した境界の新C Red/Greenと関連Swift公開結合、client互換/両journal、独立地形worldの必要経路を選ぶ。未変更のNav/Perception/Beat/Raster・入力座標はbytesと過去の実画像結果を結ぶ。world160/全Runtime59を毎回起動せず、focused CIで実ビルド/実compiler/22seal/全9Mach-O/source ZIP同一性は維持する。未実施を成功としない。
