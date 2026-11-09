# iPhone版ネクロダンサー 金商人周回の自動化

通常オールゾーン1-1で開幕の金壁を見つけ、ビートに合わせて商品が見える位置へ進み、「のろいのゆびわ」の候補でポーズして通知するプロジェクトです。同じiPhoneだけで完結し、人の手操作より速く回すことが必須です。自動購入は行いません。

**実用上の受入は未完了です。** TEST057は右1歩の後、再予約の前面確認が期限に間に合わず停止しました。TEST058で送信準備と商店到達の結合試験を改善中です。新IPAは未配布で、回収済みTEST057は再実行しません。[最新状態](docs/status.md)を参照してください。

AIの初期入口は約177KBから約11KBへ整理し、旧文書を完全保存しました。実記録評価器は実機の失敗と模擬試験の成功を区別します。Macの実ゲーム本体は未導入・未実施です。

## 読み始める場所

- 利用者: [最新状態](docs/status.md)、[実機試験と履歴](docs/device-tests/README.md)。iSHのCLIで実行し、別試験や旧操作サイトを同時に使いません。
- 開発者/AI: [作業指示](AGENTS.md)、[作業別の索引](docs/context.md)、[要件正本](docs/requirements/necrogold.md)。過去の台帳全体を常時読込しません。
- 開発工程: [ユーザー指定の8工程](docs/development-flow.md)、[今回の整理計画](docs/plans/context-refactor.md)。
- 実装・試験: [native契約](docs/contracts/native-control.md)、[試験の実行と証明範囲](docs/testing.md)、[取得元パッチ](patches/loopctrl/README.md)、[軽量iSHクライアント](necroprobe/native_walk.py)。

## 守る要件

ポーズから直接続行し、起動時のOptions操作を避けます。初版は開幕に部分金壁を含めて見える回を対象とし、見えない回は「開幕対象外」と記録します。未観測の商品を対象なしと判断せず、木/鉄扉や各方向の入口を通って確認します。候補を保持し、入力や通信の結果が不明なまま再送しません。

毎拍歩行、人より速い処理、指輪の未知評価・通知、自動周回、長時間耐久は、実機の証拠を伴って受け入れます。詳細の正本は [要件](docs/requirements/necrogold.md) です。

## 保存資料

`legacy/r12/` の40ファイルは [元manifest](docs/r12-source-manifest.json) のまま保存しています。`analysis/` は提供動画の出典・計測・ラベル、`docs/device-tests/` は版ごとの計画・結果です。生動画・実行ZIP・秘密値はGitへ追加しません。[整理前の4文書](docs/archive/context-pre-refactor/README.md) から以前の説明を完全に確認できます。

既存の第三者ライセンスは [保存文書](legacy/r12/LICENSE-LoopCtrl.txt) を参照してください。プロジェクト全体へ新しいライセンスを付与する判断はしていません。
