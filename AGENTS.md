# 作業指示

## 最初に読む範囲

1. このファイル、[最新状態](docs/status.md)、[作業別の索引](docs/context.md) を読む。合計16KiB以下を維持する。
2. 今回の変更に関係する正本・契約・関数・試験だけを追加で読む。`rg` で対象を絞る。
3. 実装や判断を変える場合は [要件正本](docs/requirements/necrogold.md)、[開発フロー](docs/development-flow.md)、[規則](docs/rules/architecture.md)・[試験](docs/rules/testing.md)・[レビュー](docs/rules/review.md) と今回の計画を読む。

履歴台帳・旧レビュー・動画分析は該当節だけを読む。`docs/archive/` の記録を現在の命令として採用しない。版ごとの進捗・配布先・検証件数はstatusと該当台帳に置き、この指示へ追記しない。元指示は [整理前の保存](docs/archive/context-pre-refactor/README.md) で確認できる。

## 守ること

- ユーザーの最新指示を優先する。対象は同じiPhone内の日本版ネクロダンサー、ケイデンス・通常オールゾーン1-1。ポーズから直接続行、Optionsを通常起動に使わない。左側が下・画面端設定0。座標は実機のpx/pt変換で検証し、動画の拡縮から推定しない。
- 開幕で全部/一部の金壁が見える回が初版対象。不可視回は開幕対象外であり店なしではない。木/鉄・横/下入口、毎拍歩行、人より速い実効処理を要件から除外しない。未観測商品を陰性にせず、対象候補は保持し自動購入しない。
- [native契約](docs/contracts/native-control.md) の入力権限・prefix・owner/世代・取消・凍結期限/予算・商品優先・ACKと実変位・UNKNOWN無再送・旧回復/回収を維持する。値の変更は別計画と根拠を要する。
- `legacy/r12/` 全40ファイルは [元manifest](docs/r12-source-manifest.json) のまま保存する。G1・保護native資産の変更も計画なしに混ぜない。
- 秘密値、pairing情報、私的設定、生ZIP/画像/動画/report/log/Scene dumpはGit外。出典・時刻・向き・寸法・hashを記録し、調整したランを未知評価へ再利用しない。

## 開発と検証

- 要件と8項目計画を分離する。作成経緯を渡さないfreshな設計・網羅・安全の独立レビューを行い、修正込み最大3周。P0は修正、残P1/P2は理由と次工程を記録する。
- 振る舞い変更は実装前のassertion Red→最小Green→Refactor。環境/compile失敗をRedに数えず、期待値を要件・実画像へ結びつける。既存assert削除やskipで通さない。挙動不変の整理は既存Greenと全不変bytes/リンク/移送の検査を使う。
- 模擬時計・合成画像・録画再生・実ゲーム操作・iPhone受入の範囲を [試験資料](docs/testing.md) に従って区別する。空結果・古い結果・送信成功を実機成功や速度達成と呼ばない。
- public repositoryの標準 `macos-26` / `ubuntu-latest` runnerを維持する。課金サービスや大型runnerの導入を混ぜない。

## 保存と返却

保存先は `shuhei0720/necrogold-automation`、既承認branch `work/p1-capture-probe`。コード・資料の保存はユーザー承認済みであり、保存だけを理由に再確認しない。完全なファイルを保存し、省略コードを配布しない。

説明は日本語、日付は日本時間。変更内容・実施した検証・未確認を具体的に示す。native/cap変更時は新IPAを実ビルドし、seal/来歴/実compiler/配布物/全source ZIPを照合する。

**開発結果を返す際は、必ず具体的な実機テストを依頼する。** 検証済みIPA/完全source・必要な更新/再起動・iSHコマンド・終了後の `runtime/test-NNN` 全ZIP返却を示す。回収済みrunを追加回収目的で再実行しない。同run回復は終了後に回収未完了が明示された場合だけ、同じLoopCtrl起動状態・source・runtimeで行う。
