# NecroGold automation

iPhone版ネクロダンサーで、通常オールゾーン1-1で、開幕に金壁が見える回の金商人の商品を高速に確認し、目的の「呪いの指輪」の候補で停止するためのプロジェクトです。

**現在はTEST-048を開発しています。** TEST047では回転処理が短くなりましたが、最初の移動予約時刻に画像解析が重なり、方向入力が未送信で停止しました。純粋な画像走査を既存撮影workerへ移し、前面アプリの確認を予約直後へ先行します。元の拍・10ms期限・取消/ロック/鮮度・再送禁止は維持し、拒否時刻を固定診断へ保存します。新clientはAPI `1.98.14-ngg2`とcapability `necrogold_native_v5`を必要とするため、**TEST048の新IPAへの更新が必要です。** 配布物・Mac/CI最終検証と[TEST048実行手順](docs/device-tests/README.md#test-048実行手順)は既存実機台帳末尾へ保存します。毎拍1歩と人より速い動作の実機受入は未合格です。

前版TEST-042は商品表示・最終ポーズに成功しましたが、速度は未合格でした。report開始→初入力23.831秒（04118.587秒）、walk26.229秒（04121.874秒）。拍の再同期で7.329秒、扉前の再観測で4.701秒の空白があり、full撮影＋解析だけで約1.25秒かかりました。[実機結果と原因](docs/device-tests/README.md#test-042受領結果2026-11-07-日本時間)を残し、この観測待ちを短縮するためNG-G2へ進んでいます。配置差があるため全時間差を変更の効果とはしません。

- [計測ツールの使い方と結果の見方](docs/p1-probe-guide.md)
- **TEST-048の実機確認をお願いします。** [実行手順](docs/device-tests/README.md#test-048実行手順)で新IPAへ更新し、LoopCtrlを完全終了/起動してStart Serverを確認します。新しい通常1-1を画面端操作0・左側が下の向きでポーズし、iSHから `sh test_048.sh` を実行。終了後は `runtime/test-048` のZIPと、初動・各歩と拍・商品・最終ポーズの確認結果をこのチャットへ返してください。開発ブランチは`work/p1-capture-probe`です。
- 今回の対象試験: `PYTHONPATH=tests python3 -m unittest test_native_perception test_native_navigation test_native_beat test_native_controller test_native_raster test_protocol test_http_and_cli test_http_diagnostics test_native_walk test_native_connect test_native_results -v`。固定したTEST034〜042の66画像は`NECRO_TEST043_FIXTURE_ROOT`、TEST045の8画像は`NECRO_TEST046_FIXTURE_ROOT`、TEST046の5画像は`NECRO_TEST047_FIXTURE_ROOT`でGit外の場所を指定します。必須画像の不足・hash不一致は失敗にします。CIのprivate8試験の明示除外とローカル全件、旧回帰の外部画像不足skipは分け、最終集計は既存実機台帳を参照してください。
- 完全な新規ソース: [native C/Swiftと取得元パッチ](patches/loopctrl/README.md)、[軽量iSHクライアント](necroprobe/native_walk.py)、[起動スクリプト](test_048.sh)。旧版40ファイルは未変更。
- P1.1の検証: ホスト54試験と3観点の相互レビューを通過しましたが、[TEST-001](docs/device-tests/001-capture.md)の実機3実行はworker_failedでした。3reportを受領し、最初のdevice_infoの開始記録までで完了していないことを確認。ホスト通過を実機合格とは扱いません。
- P1.2の[TEST-002](docs/device-tests/002-worker-diagnostics.md)はPython暗号でもゲーム起動前にSIGSYSで終了しました。
- P1.3の[TEST-003](docs/device-tests/003-ish-timer.md)は`timer_already_in_use`でゲーム起動前に停止、取得0/12でした。
- **P1.4時点の履歴**: iSHの`setitimer`旧値を使用中判定・復元に使う処理を廃止。専用worker内でタイマーを明示的に所有します。[修正計画](docs/plans/p1-owned-timer.md) / [全ホスト試験ログ](docs/validation/p1-owned-timer-tests.txt) / [実機確認手順TEST-004](docs/device-tests/004-owned-timer.md)。TEST-004はゲーム起動応答まで完了したが、取得0/12、約119秒でsession_deadline。実機ゲートは未通過です。[TEST-005](docs/device-tests/005-ish-foreground.md)ではiSH画像を11/12取得、約45秒で期限終了。保存3枚を目視確認済みです。[TEST-006](docs/device-tests/006-game-keepalive.md)では継続処理付きで12/12取得、約32.9秒で正常終了し、保存3枚全てでゲームのポーズ画面を確認しました。座標・鮮度・取消は未確認です。[TEST-007](docs/device-tests/007-native-crypto.md)はnative_i386で12/12非黒取得、約26.3秒で正常終了。保存3枚はゲームのポーズ。JPEG小サイズの取得→検査中央値は751.430→409.465ms、同じ画像データでも復号時間の短縮を確認しました。[TEST-008](docs/device-tests/008-display-reference.md)で通常画像1792×828とAPI原画像の相対配置を比較し、単純な回転ではなく縦横の縮尺差を確認しました。入力ptの対応は未確認です。
- **実機試験はiSHのCLIで実行します。** TEST-013など別の試験を同時実行せず、旧版の操作サイトも併用しないでください。
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
| `analysis/heart-timing/` | 2本の動画から測った51拍のCSVと再計測コード。元動画は含まない |
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

TEST043の商品保持は限定的な増分です。目的の指輪の未知画像評価・通知、対象なし確認後に戻る自動周回、長時間耐久と同条件の人比較は引き続き受入が必要です。開発結果を返すときは、ユーザーの指示に従い毎回具体的な実機テストを依頼します。

速度の具体的な合格基準は要件書の**提案値**です。まだ達成していません。最初の検証は、現在のiPhone環境で新鮮な画像を十分速く取得でき、正しい座標に入力できるかの確認です。

## 旧版について

`legacy/r12/` 内の起動手順や検証結果は、旧版作成時点の記録です。現在の推奨手順とは扱いません。既存の第三者ライセンスは `legacy/r12/LICENSE-LoopCtrl.txt` に保存しています。プロジェクト全体に新たなライセンスを付与する判断はしていません。

作成日: 2026-11-05（日本時間）

