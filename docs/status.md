# 最新状態

更新: 2026-11-17（日本時間）。TEST109実機の4停止を受領し、TEST110を修正中。[計画](plans/test110-device-failures.md)・[修正表](fix-records.md)。

8添付を4固有run/98 PNG/108記録へ照合。時刻順8d78→9bf5→fe54→80c6。ACK比較前のgold UNKNOWN拒否、FULLの古い画像待機、対角DOOR→GOLDでの入店拒否、SHOP表示が重なるpause iconを各別に修正する。原250は既Ringで完全陰性/C検査1、元Dまで約795ms。Ring閾値は変更しない。

最新ユーザー指定の敵による進行不能/ゲームオーバー再試行を要件へ追加。対象なしと別の正の証拠/理由・各UI資格・元期限を要求し、今回の4通常停止を敵と断定しない。新入力境界は独立重点レビュー・現在Runtimeの選択結合が必要。

基準c2f7624、[旧109検証](reviews/test109.md)・[配布](https://github.com/shuhei0720/necrogold-automation/releases/tag/test109-build208)は保存。109の130件/19scope・IPA照合は補助試験で、今回の実機失敗を改善済みとしない。110のCI/IPA/配布は未実施。rawはGit外、G1/R12/既feature/ELFを保持し、iPhone8/遠隔開発は再開しない。

次は確認済み原因ごとのRed→最小Green/関連回帰、イレギュラー設計と境界検証、差分レビュー、同source IPA照合、固定配布。テスト依頼へ何をどう修正したかを明記する。主指標は実機の商品確認到達率/対象なし次周回。110の実機到達率・未知精度・毎拍/人超え速度・耐久は未受入。
