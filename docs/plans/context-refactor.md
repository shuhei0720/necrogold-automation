# コンテキスト整理の8項目プラン

状態: 計画・実装の3観点レビュー完了、残P0/P1/P2なし。2026-11-09（日本時間）。ユーザーの「AIへのXを必要最低限十分にする」依頼による、挙動を変えない独立した整理工程。TEST054の実機不合格を成功へ読み替えない。

## 1. 概要・目的

常時読む指示から過去の版ごとの命令・検証履歴を分離し、現行要件・不変条件・最新事実・今回の計画へ短く辿り着けるようにする。過去を削除して短くするのではなく、必要な時だけ原記録を読む。実行コードの機能変更とTEST055の不具合修正は別工程にする。

## 2. 背景と基準

基準commitは `420c7ce3fb2e1fbe9f9ab7086891dd7e1118ba2e`。AGENTS/README/status/development-flow/requirements入口/videoの従来必読集合は177,127 UTF-8 bytes、実機台帳は510,324 bytes。古い版の「現在」「必ず次版を配布」が積み重なり、現行指示と競合する。

TEST054は1方向入力・1MOVED後、2歩目の未送信予約中に金壁/扉分類が変わりSCREEN停止した。元画像fallbackは初歩には適用されず、この実行で改善効果を評価できない。Macの55故障試験は模擬取得/入力を含み、実ゲームの到達率ではない。新しい原因分析・実ゲーム試験の実現性は最新statusに短く置く。

## 3. 詳細設計と責務

- `AGENTS.md`: 安定した作業ルール、読む順と条件、権限・安全・検証・報告。版ごとの履歴や過去の配布指示は置かない。6KiB以下。
- `docs/status.md`: 最新実機結果、現行code/IPA/clientの同一性、未達要件と次工程だけ。6KiB以下。旧 `test-011結果と今回の変更` anchorは短い履歴案内で維持する。
- `docs/context.md`: タスク→必要資料/コード/試験の索引。4KiB以下。通常の初期読込をAGENTS+status+contextの16KiB以下にする。関係のない台帳全体・動画分析・過去レビューを一括で読ませない。
- `docs/development-flow.md`: 原文の固定出典、8工程、fresh3観点/最大3周、実測Red→Green→Refactor、実機受入を残す。6KiB以下。
- `README.md`: ユーザー向け目的、現行版/未受入、実行手順への入口、正本/履歴の案内。6KiB以下。
- `docs/contracts/native-control.md`: 現行C/Swiftの入力権限・凍結期限/予算・取消/owner/prefix・商品優先・motion/fallback・ABI/診断・旧client回復とexport・compiler/sealの不変条件。12KiB以下。要件や過去検証値を正本として複製しない。
- `docs/testing.md`: 実コード/fixture/CIと要件の対応、実画像141pathとprivate16除外、既存Greenの意味、実トレース再生/実ゲーム/Mac/iPhoneの証明範囲、代表実行コマンド。8KiB以下。
- `AGENTS.md`、`README.md`、`docs/status.md`、`docs/development-flow.md` の4文書は `docs/archive/context-pre-refactor/` に**元bytesのまま**非AGENTS名で保存し、index/manifestに元path・SHA・基準commit・元位置で読めるGitHub固定URLを置く。snapshot内の相対リンクは元pathを基準に読む。現行指示ではないことをindexに明示する。
- 510KBの `docs/device-tests/README.md` は移動・分割しない。既存anchor/他文書からの参照を維持し、冒頭に「履歴・該当節だけ読む」と現在statusへの案内だけ置く。

正本 `docs/requirements/necrogold.md`、rules3文書、全体plan、動画資料、既存レビュー、R12/G1、全ソース/試験/launcher/workflow/native seal/IPAには変更しない。旧増分の「freeze後5文書のみ」は当該配布時の制約であり、今回ユーザーが依頼した新整理工程の新資料追加を妨げない。

## 4. テスト・参照への影響

実行挙動は同一。整理前にnative183（全141実画像path）/client190/package205のGreenを確認する。文書変更ごとに、元4snapshotの全bytes/SHA、非文書tracked filesが基準commitと全一致、R12全40・G1・22seal不変、内部相対リンク/既存fragment・予算・現行契約の移送を点検する。文書だけの変更のためIPAを再ビルドしない。実機不合格は別に保持する。

## 5. 検査ケースと期待値

1. 新規AIは16KiB以下の3文書から、要件/契約/対象試験/今回の計画/実機最新結果を特定できる。
2. 過去の「現在TEST0xx」や閉じたレビュー再開指示が通常の入口に混入しない。
3. 閾値、時間上限、unknown無再送、goods優先、latest authority、fallback限定条件、旧回復、export/compile証拠の必須条件を失わない。独立3観点が元の現行契約と比較する。 元AGENTSのcurrent9–18/安定規則97–124と元flow36–57を出典に、レビュー記録へ「要件/権限・R12/入力owner-prefix-取消/初期slot/再予約/全期限予算/retune/ACKとmotion/fallback/goods/ABI診断/旧client/export/compile-seal/fixture・実機範囲/開発工程/配布」の17行の移送表を置き、旧出典・新section・保持した値/意味を対応させる。入口から全行の正本へ到達することを独立確認する。
4. 過去4文書を完全に復元できる。R12/要件/コード/試験/CI/IPAはbytes不変。台帳の全既存anchorとstatus旧anchorを保持する。
5. 「模擬入力成功」「録画再生成功」「実ゲームを起動して到達」「iPhoneで性能受入」を区別する。未導入のMac実ゲームを実施済みとしない。

文書整理専用の実装を鏡写しするunit testは追加しない。既存Greenと上記の実ファイル比較・リンク/予算検査を証拠にする。

## 6. 実装順序

①既存Greenと基準hashを保存 → ②freshな設計/網羅/安全の独立計画レビュー（最大3周） → ③元4文書を保存 → ④索引/契約/試験資料を作り入口を短縮 → ⑤移送/リンク/全不変bytes/予算を検査 → ⑥独立実装レビュー → ⑦GitHub保存と完全source ZIP全byte照合。レビュー記録は `docs/reviews/context-refactor.md` 一つに集約する。

## 7. コミット前・配布前

`git diff --check`、whitelist、全snapshotと全非文書filesの比較、R12/G1/native seal、リンク/anchor/予算を確認する。コードが同一なら同じ試験を形式的に繰り返さず、Greenの対象commitと不変性を対応づける。新source ZIPはGitHubから実際に取得して全tracked files/CRC/pathを照合する。ここでいうGreenは既存自動試験のGreenであり、TEST054の実機1歩停止は未解消として保持する。

本工程の完了は文書整理の完了であり、既知の不合格TEST054/build71を修正版として再提示しない。その後、TEST054の停止原因修正を別のTEST055・8項目計画から続ける。最終応答ではMac実ゲーム試験の可否・実施範囲を説明し、その後続工程で検証した新成果物と具体的な実機テスト・返却ZIPを必ず依頼する。

## 8. スコープ外

本工程でのC/Swift/Pythonの分割や機能修正、金壁guard/閾値/期限の緩和、テスト期待の成功化、商用ゲームの自動取得/Apple ID認証/課金サービス導入、ゲームE2Eの合格宣言、過去の証拠削除。実ゲームの正規導入と操作環境が得られるまで、録画から未収録の反実仮想を生成しない。
