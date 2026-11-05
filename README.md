# NecroGold automation

iPhone版ネクロダンサーで、通常オールゾーン1-1で、開幕に金壁が見える回の金商人の商品を高速に確認し、目的の「呪いの指輪」の候補で停止するためのプロジェクトです。

**P1の画像取得・遅延計測ツールを実装しました。自動周回はまだ実装・実機合格していません。** 保存したR12は不具合が報告された旧版です。新ツールは取得経路を診断し、ポーズ解除やリスタートのタップは行いません。

- [計測ツールの使い方と結果の見方](docs/p1-probe-guide.md)
- 次回の実機試験: [TEST-007のコマンド全体](docs/device-tests/007-native-crypto.md)（既存P1.4・既存ペアリングのまま）。`sh start_probe.sh`単体には今回必要な継続処理は含まれません。
- ホスト試験: `python3 -m unittest discover -s tests -v`
- 完全な新規ソース: `necroprobe/`。旧版40ファイルは未変更。
- P1.1の検証: ホスト54試験と3観点の相互レビューを通過しましたが、[TEST-001](docs/device-tests/001-capture.md)の実機3実行はworker_failedでした。3reportを受領し、最初のdevice_infoの開始記録までで完了していないことを確認。ホスト通過を実機合格とは扱いません。
- P1.2の[TEST-002](docs/device-tests/002-worker-diagnostics.md)はPython暗号でもゲーム起動前にSIGSYSで終了しました。
- P1.3の[TEST-003](docs/device-tests/003-ish-timer.md)は`timer_already_in_use`でゲーム起動前に停止、取得0/12でした。
- **現在P1.4**: iSHの`setitimer`旧値を使用中判定・復元に使う処理を廃止。専用worker内でタイマーを明示的に所有します。[修正計画](docs/plans/p1-owned-timer.md) / [全ホスト試験ログ](docs/validation/p1-owned-timer-tests.txt) / [実機確認手順TEST-004](docs/device-tests/004-owned-timer.md)。TEST-004はゲーム起動応答まで完了したが、取得0/12、約119秒でsession_deadline。実機ゲートは未通過です。[TEST-005](docs/device-tests/005-ish-foreground.md)ではiSH画像を11/12取得、約45秒で期限終了。保存3枚を目視確認済みです。[TEST-006](docs/device-tests/006-game-keepalive.md)では継続処理付きで12/12取得、約32.9秒で正常終了し、保存3枚全てでゲームのポーズ画面を確認しました。座標・鮮度・取消は未確認です。次は同じP1.4で[TEST-007: 既存ネイティブ復号の比較](docs/device-tests/007-native-crypto.md)を行います。
- **P1診断版にはSafariの操作サイトがありません。** ゲーム起動要求と原画像の取得を行い、「ゲームを続行」はまだ押しません。旧版の操作サイトを併用しないでください。
- [実機テスト台帳](docs/device-tests/README.md)と[実ゲームE2Eの合格条件](docs/device-tests/game-e2e.md)を管理します。

## まず読むもの

- [要件・実装検証計画](docs/requirements.md) / [図を含むPDF](docs/archive/requirements-plan-v1.pdf)
- [追加動画の分析と要件への反映](docs/video-2-analysis.md)
- [採用したAI駆動開発フロー](docs/development-flow.md)
- [8項目の実装検証プラン](docs/plans/rebuild.md)
- [現在の状態と次に検証すること](docs/status.md)
- [Codexへの引き継ぎ指示](AGENTS.md)

## 保存内容

| 場所 | 内容 |
| --- | --- |
| `legacy/r12/` | 既存ZIPから取り出した全40ファイル。省略や修正なし |
| `docs/r12-source-manifest.json` | 元ZIPと各ファイルのSHA-256 |
| `analysis/manual-video-1/` | 1本目の動画の計測コード、42回分の区間、画像ラベル |
| `analysis/manual-video-2/` | 追加動画の時間索引、代表フレーム、再抽出コード |
| `evidence/` | R12で取得された黒画像の不具合資料 |

元動画はチャットに添付されたものを出典とし、ファイル名・識別子・SHA-256を各分析フォルダのmanifestに記録しています。録画全体はこのリポジトリには含みません。

## 守る要件

1. 起動時はゲームのポーズ画面から「ゲームを続行」を直接押す。通常起動でオプションを開かない。
2. 人より速く回すことを最優先とし、画像取得から入力反映までと、毎分の商品確認完了回数を実機で計測する。
3. 初版は開幕に金壁が一部でも見える回を扱う。見えない回の探索は省き、木と鉄の扉、横や下からの入口へ対応する。
4. 商品を確認できる位置まで進む。商品が隠れている状態を「目的の品なし」にしない。
5. 目的の品の候補で入力を止めて保持する。自動購入しない。
6. 黒画像・古い画像・座標未検証・別アプリへの切り替えを区別する。
7. 模擬テストの合格と実機での成功を区別し、未測定の速度や成功率を達成済みと書かない。

速度の具体的な合格基準は要件書の**提案値**です。まだ達成していません。最初の検証は、現在のiPhone環境で新鮮な画像を十分速く取得でき、正しい座標に入力できるかの確認です。

## 旧版について

`legacy/r12/` 内の起動手順や検証結果は、旧版作成時点の記録です。現在の推奨手順とは扱いません。既存の第三者ライセンスは `legacy/r12/LICENSE-LoopCtrl.txt` に保存しています。プロジェクト全体に新たなライセンスを付与する判断はしていません。

作成日: 2026-11-05（日本時間）

