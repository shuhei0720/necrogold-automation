# TEST-002: 子プロセスの終了診断と暗号初期化の比較

状態: 実行済み、reportと終了画面受領。結果: **worker_failed / SIGSYS、画像取得0/12**。対象: P1.2（コードcommit `cfcb70b61cea995e360eea0ad1378878a7f64c40`）。TEST-001の3回の失敗はそのまま残す。

P1.2は子の終了コードと最後のcheckpointを追加する修正版であり、TEST-001の実機原因を解消したと保証する版ではない。取得条件は同じ12試行・45秒。今回だけ`--python-crypto`でnative暗号を使わず、差を観察する。これで動いてもnativeが唯一の原因と断定しない。Python処理の速度を完成版の性能と評価しない。

TEST-001の3reportではnative_i386選択後、最初のdevice_infoイベントの開始記録が残り、完了前にworker_failedとなっている。今回はまずdevice_infoの完了可否と子終了コードを比較する。P1.1からP1.2への終了診断変更もあるため、成功だけでnative単独の因果関係を確定しない。

## 手順

1. P1.2のZIPを旧版と別に展開。`start_probe.sh`が直下にあるフォルダをiSHの別マウント先へ選択する。

```sh
mkdir -p /mnt/necro_p12
mount -t ios . /mnt/necro_p12
```

2. 版を確認する。表示は`P1.2`。

```sh
cd /mnt/necro_p12
python3 -c 'import necroprobe; print(necroprobe.VERSION)'
```

3. LoopCtrlと接続条件・ゲーム設定はTEST-001と同じにする。ゲームは通常オールゾーン1-1のGAME PAUSE、左側が下。次を一度実行する。

```sh
sh start_probe.sh --python-crypto --samples 12 --seconds 45 --output runtime/test-002
```

4. ゲームが開いたら触らず約1分後にiSHへ戻る。エラーが先に出たらそのまま結果を残す。終了画面の「子プロセス: 段階=… / 終了コード=… / シグナル=…」も含めて送る。
5. 展開先`runtime/test-002/probe-…`を圧縮して送る。TEST-001の3reportは受領済みなので再送不要。接続鍵は不要。

## 新しい診断の意味

- `stage`: 最後に保存できた処理開始前の地点。その処理の完了・故障原因ではない。
- `spawn_requested`: 子を起動する前に親が保存。子がそこまでしか進まなかったと断定せず、終了コードと合わせる。
- `pairing_load` / `crypto_initialize` / `capture_collection`: ペアリング読込・暗号初期化・収集の開始前。
- `returncode`: 回収できた子の終了コード。負値だけsignalへ変換。期限やCtrl+Cで親が停止した理由とは別に記録する。
- `report_read_ok: false`: 子の記録を親が読めず、件数を初期予定へ戻した。実際の未実施数の証拠にしない。
- `checkpoint_error`: stageの保存に失敗した場所。次の処理を開始せず停止する。
- `exception_type`: 固定した例外分類。例外メッセージやstderr本文は秘密値を避けるため保存しない。

## 結果

2026-11-05 15:27:01（日本時間、フォルダ名のUTCから変換）。P1.2、`--python-crypto --samples 12 --seconds 45`。取得0、エラー0、未実施12。暗号engineはpython、stage=capture_collection、子returncode=-31、SIGSYS。最初のdevice_infoイベントの開始記録だけがあり、完了・launch_app・screenshotの記録なし。ゲームが開かないという報告と整合する。report_read_ok=trueで、親の初期件数へのフォールバックではない。

全体8,385.825ms、device_info開始前8,118.924ms、開始記録から親の終了まで266.901ms。これらは子起動・保存・終了回収を含み、RPC時間やゲームの速度ではない。画像ファイルは0。

元資料: `test-002.zip` / `IMG_8524.png`。派生数値・SHA-256は[test-002-results.json](test-002-results.json)。元ZIP・画像は添付で保持し、GitHubへ複製しない。

Python暗号でも再現するため、ネイティブ暗号だけを原因にはできない。毎RPC前の`getitimer`がiSHで未実装である互換性不具合をコードと公式ソースから発見し、[P1.3修正](../plans/p1-ish-timer.md)へ進む。端末ビルド・syscall traceは未受領なので、実機の唯一の故障原因は未確定。P1全体とゲーム操作E2Eは未通過。

操作サイトが開かない点は別で、P1.2にはHTTPサーバーが実装されていない。旧版の画面を期待させた案内不足を訂正する。次は[TEST-003](003-ish-timer.md)。
