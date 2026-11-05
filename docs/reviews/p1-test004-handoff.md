# TEST-004結果引き継ぎとTEST-005手順の独立レビュー

日付: 2026-11-05（日本時間）。実行コードを変更せず、受領済み結果と比較手順を整備する文書スコープ。P1.4の実装レビュー3周とは別の記録であり、第4周の実装レビューではない。

## 確認した正本

参照commit: `f8b8f100d778d81b72fea2b71c5350896576273d`。

- `AGENTS.md`、`README.md`、`docs/status.md`、`docs/development-flow.md`
- `docs/requirements/necrogold.md`、`docs/plans/rebuild.md`、`docs/video-2-analysis.md`
- `docs/plans/p1-owned-timer.md`、`docs/reviews/p1-owned-timer.md`、`docs/validation/p1-owned-timer-host-tests.json`
- `docs/rules/`の設計・テスト・レビュー、実機台帳、TEST-004手順、P1利用ガイド
- ユーザー指定AI-Driven-DevelopmentのCodex版（参照commitはdevelopment-flow.mdに記録済み）

## 第1周: 3観点の独立レビュー

作成経緯を渡さない新規コンテキストで、差分・原report・要件・計画・ルール・照合用コードを渡した。全担当はread-onlyで、実機通信は行っていない。

| 担当 | 観点 | 結果 |
| --- | --- | --- |
| handoff_design_review | 設計、SSOT、比較条件、根拠と断定 | P0/P1なし。P2: 実際の45秒指定の留保、古いiSH画像の識別基準 |
| handoff_evidence_review | 件数、ハッシュ、CLI、判定網羅 | P0/P1なし。P2: 古いiSH画像の識別基準 |
| handoff_safety_review | 共有範囲、秘密値、入力、停止 | P0/P1なし。P2: Ctrl+C無応答時の終了手順 |

主担当がP2を修正した。TEST-004は「手順指定45秒、実際の引数はreport未記録」と明示。保存画像と今回のコマンド/試行表示を比較し、判定不能は鮮度不明にした。同一静止画だけで鮮度を保証しない。Ctrl+C無応答時の既存サービス停止とiSH終了、途中reportの保全、終了確認前に圧縮しない手順を追加した。P2修正後の追加独立レビューは行っていない。P0/P1の未解決指摘なし。

## 確認した結果

- `test-004.zip`と`test-004(1).zip`のバイト一致、SHA-256一致。重複受領を追加実行として数えない。
- 原reportと派生JSONのevents/worker/件数、ハッシュ、画像0枚を照合。
- 単調時計の差から118888.205msを再計算。完了0、中断1、未実施11、合計12。
- P1.4の実パーサーでTEST-005の引数を検証。ゲーム自動起動なし、Python暗号、12試行、45秒。
- 変更は文書と派生JSONのみ。P1.4の98ホスト試験は以前の保存記録であり、今回再実行したとは扱わない。機能変更がないため新しいRed→Greenの実装試験は行っていない。

## 8工程と次の状態

P1.4の⑦人間レビューで受け取った実機結果を記録し、[TEST-005](../device-tests/005-ish-foreground.md)の比較条件・判定を独立レビューした。実装変更はなく、⑧の独立したリファクタリングも行っていない。全体の8工程完了や実機合格は宣言しない。

P1実機ゲートは未通過。TEST-005は未実行。ゲーム操作E2E、自動周回、取得の鮮度、入力座標、停止保証、速度・耐久性は引き続き未検証。iSH休止は候補であり、取得対象画面も変わる比較だけでは原因確定しない。
