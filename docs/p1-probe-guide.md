# P1 計測ツールの使い方

このツールは、黒画像と取得遅延の原因を調べるためのものです。**Safariの操作サイトは起動しません。新しい自動周回版ではありません。** ゲームを開く要求を送りますが、「ゲームを続行」は押しません。オプション、移動、リスタート、購入も行いません。実機で開くことを今回確認します。

現在はP1.3です。TEST-001の3実行に加え、TEST-002もゲーム起動前にSIGSYSとなりました。iSH未実装のgetitimer呼出しを除去し、停止期限を維持した修正です。今回は[TEST-003の手順](device-tests/003-ish-timer.md)を使ってください。実機原因の解消は未確認です。

## 起動

GitHubの`work/p1-capture-probe`ブランチからCode → Download ZIPで取得し、旧版とは別フォルダへ展開してください。iSHにマウントした展開先で、次を実行します。展開済みなのでZIPを再展開するコマンドは不要です。

```sh
sh start_probe.sh
```

LoopCtrlは以前使った状態で起動しておきます。既存の`~/.loopctrl/token.json`を読み取るだけで、再ペアリングや鍵の書き換えはしません。標準ではゲームの起動要求を1回送り、3条件×4回の取得を最大45秒間測ります。ゲームに切り替わったらそのまま待ち、終了後にiSHへ戻ってください。停止はiSHでCtrl+Cです。LoopCtrl側で停止した場合も接続障害として終了する仕組みですが、iSH実機での挙動は未検証です。

Pillowがなければ、起動時に表示される`apk add py3-pillow`で入れてから再実行します。ツール自身はパッケージのインストールやOS設定変更をしません。

## 出力

毎回別の`runtime/probe-日時-識別子/`に保存します。表示時刻はフォルダ名にUTCの`Z`を付けています。

- `report.json`: 条件別の件数、通信・復号・画像処理の時間、停止理由。秘密鍵・token・生のRPC本文は含めません。
- 画像: 加工前のJPEG/PNG。各取得条件で黒・非黒を最大1枚ずつ、合計最大6枚です。
- 画面取得元が返すpx/ptと、実ファイルのpxを別々に記録します。縦画像を勝手に伸ばしません。

診断結果を渡す場合は、この1フォルダだけで足ります。ペアリング用の`.loopctrl`フォルダは含めないでください。画像は実画面なので、ゲーム以外が写っていないか確認してから共有できます。診断ツールから外部へアップロードはしません。

## 読み方

| 結果 | 意味 |
| --- | --- |
| `blank_or_dark` | 取得ファイル自体が黒に近い。金壁なしではない |
| `decoded_nonblank` | 画像を展開でき、明るい画素がある。ゲーム画面の認識成功ではない |
| `metadata_issues` | 返された寸法等と実画像の食い違い・型不正 |
| `same_bytes_as_previous` | 同一ファイルが続いた。ポーズの静止画かキャッシュかは未確定 |
| `frame_age_ms: null` | 端末生成時刻を検証できないので鮮度は未計測 |
| `pairing_missing` | 既存のローカル接続用の鍵が見つからない。再ペアリングは自動実行しない |
| `pairing_ambiguous` | ローカル接続に複数の鍵が該当。適当な端末を選ばず停止 |
| `connection_failure_limit` | 3回連続で通信が失敗 |
| `session_deadline` | 設定した全体時間に到達。未実施・中断を残す |
| `timer_setup_failed` / `timer_restore_failed` / `timer_cleanup_failed` | RPC期限を管理できず停止。次の通信へ進まない |
| `response_mac_mismatch` / `response_id_mismatch` | 応答を信用できないため即停止 |

`gate.P1`は常に`not_passed`です。取得速度だけでは画像の鮮度、タップ座標、送信済み入力の取消、長時間動作を証明できません。

条件別の`success_only_timings`は成功した試行の時間だけです。必ず`counts`の失敗・未実施数と一緒に読みます。`captures_completed_per_second`はホスト上の診断取得数で、ゲーム操作の速度や有効観測Hzではありません。

## 追加の測定コマンド

ゲームを自動で開かずに取得する場合:

```sh
python3 -m necroprobe capture
```

最大10分の取得を準備する場合（試行上限600、期限600秒）:

```sh
sh start_probe.sh --samples 600 --seconds 600
```

600試行が先に終了した場合は10分未満で終わります。このコマンドだけで10分耐久合格とはなりません。iSHがバックグラウンドで停止・休止するかも実機で確認します。

保存済み画像だけを検査する場合:

```sh
python3 -m necroprobe inspect evidence/start-failed.jpg analysis/manual-video-2/frames/002000-pause.jpg
```

全ホスト試験:

```sh
python3 -m unittest discover -s tests -v
```

Python 3.9以降、Pillow、POSIXのsetitimerとプロセス終了APIを使います。getitimerは使用しません。実際のiSHでの動作、ネイティブ暗号処理の速度、ゲームへの復帰は未検証です。次の実装判断は今回の実機レポートを根拠にします。
