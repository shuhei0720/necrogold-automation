# LoopCtrl取得元の画像寸法修正

対象は公式v0.3.4 commit `6e25cf6a9f65bc86c372cdce94bdb151d0cf6767`。TEST-009の実機server_versionは1.98.14で公式リリースのAPI版と一致するが、バイナリ同一性は未証明。

現在は実装前のRed確認段階。`check_baseline.py`は固定された元ソースから実際の寸法式を取り出し、Swiftでコンパイルして、キャッシュ414×896で横長896×414を期待すると失敗することを観測する。コンパイル失敗はRedに数えない。UIKit描画、キャプチャ、iPhone性能の試験ではない。

macOSでの実行:

```sh
python3 patches/loopctrl/check_baseline.py /path/to/LoopCtrl /tmp/ng-geometry-baseline
```

コード本体・unsigned IPAはまだ作成していない。CIの結果を記録してから[計画](../../docs/plans/p1-source-geometry.md)の明示geometryモードを実装する。現行iPhoneのアプリ削除・更新は不要。
