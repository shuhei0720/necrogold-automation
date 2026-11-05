# P1 計測ツールの使い方

このツールは、黒画像と取得遅延の原因を調べるためのものです。**Safariの操作サイトは起動しません。新しい自動周回版ではありません。** ゲームを開く要求を送りますが、「ゲームを続行」は押しません。オプション、移動、リスタート、購入も行いません。TEST-006/007で実機のゲームのポーズ画像取得を確認済みです。入力座標・鮮度・ゲーム内入力は未検証です。

現在はP1.5です。取得元NG-G1のビルドとP1.5全131ホスト試験を通過しました。今回の実機手順は[TEST-010](device-tests/010-source-landscape.md)を使用します。LoopCtrlをSideStoreで更新し、`sh test_010.sh`で一時継続処理付きの横長取得を測ります。TEST-009までの履歴は[実機台帳](device-tests/README.md)に保存しています。

## 標準CLIの起動仕様

以下はCLI単体の説明です。指定なしは従来の取得経路、`--source-geometry`は新capability必須の取得元寸法モードです。今回実行するのはTEST-010の手順です。CLI単体には継続処理がないため、通常の診断ではtest_010.shを使います。

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
| `same_bytes_as_previous` | 直前の試行との同一バイト判定。3形式/縮尺を交互に取得するため、falseでも同じ形式内の反復を否定しない。静止画かキャッシュかは未確定 |
| `frame_age_ms: null` | 端末生成時刻を検証できないので鮮度は未計測 |
| `pairing_missing` | 既存のローカル接続用の鍵が見つからない。再ペアリングは自動実行しない |
| `pairing_ambiguous` | ローカル接続に複数の鍵が該当。適当な端末を選ばず停止 |
| `connection_failure_limit` | 3回連続で通信が失敗 |
| `session_deadline` | 設定した全体時間に到達。未実施・中断を残す |
| `timer_setup_failed` / `timer_cleanup_failed` / `timer_unusable` | RPC期限を管理できず停止。次の通信へ進まない |
| `response_mac_mismatch` / `response_id_mismatch` | 応答を信用できないため即停止 |

`gate.P1`は常に`not_passed`です。取得速度だけでは画像の鮮度、タップ座標、送信済み入力の取消、長時間動作を証明できません。

条件別の`success_only_timings`は成功した試行の時間だけです。必ず`counts`の失敗・未実施数と一緒に読みます。`captures_completed_per_second`はホスト上の診断取得数で、ゲーム操作の速度や有効観測Hzではありません。

## 追加の測定コマンド（参考・現在は実行不要）

以下はCLI機能の一覧です。今回依頼する試験はTEST-010です。追加取得や10分取得は現在不要です。

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

Python 3.9以降、Pillow、POSIXのsetitimerとプロセス終了APIを使います。getitimerは使用しません。P1.4は専用worker内でSIGALRM/ITIMER_REALを所有し、setitimerの旧値を読み取り・復元しません。reportの`timer`に方式、終了状態、継続利用不可の状態（poisoned）、cleanup_errorを記録します。TEST-006で継続処理付きのゲームのポーズ画像取得は確認できました。TEST-007では既存ネイティブ復号の実機利用と今回条件での時間短縮を確認しました。画像の鮮度・座標、ゲーム続行の入力は未検証です。次の実装判断は今回の実機レポートを根拠にします。

