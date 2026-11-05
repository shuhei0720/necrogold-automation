# TEST-002: 子プロセスの終了診断と暗号初期化の比較

状態: 未実行。結果: 未判定。対象: P1.2。TEST-001の2回の失敗はそのまま残す。

P1.2は子の終了コードと最後のcheckpointを追加する修正版であり、TEST-001の実機原因を解消したと保証する版ではない。取得条件は同じ12試行・45秒。今回だけ`--python-crypto`でnative暗号を使わず、差を観察する。これで動いてもnativeが唯一の原因と断定しない。Python処理の速度を完成版の性能と評価しない。

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
5. 展開先`runtime/test-002/probe-…`を圧縮して送る。TEST-001の`runtime/test-001`に残る2実行分のreport.jsonも受領できれば、前後比較に利用する。接続鍵は不要。

## 新しい診断の意味

- `stage`: 最後に保存できた処理開始前の地点。その処理の完了・故障原因ではない。
- `spawn_requested`: 子を起動する前に親が保存。子がそこまでしか進まなかったと断定せず、終了コードと合わせる。
- `pairing_load` / `crypto_initialize` / `capture_collection`: ペアリング読込・暗号初期化・収集の開始前。
- `returncode`: 回収できた子の終了コード。負値だけsignalへ変換。期限やCtrl+Cで親が停止した理由とは別に記録する。
- `report_read_ok: false`: 子の記録を親が読めず、件数を初期予定へ戻した。実際の未実施数の証拠にしない。
- `checkpoint_error`: stageの保存に失敗した場所。次の処理を開始せず停止する。
- `exception_type`: 固定した例外分類。例外メッセージやstderr本文は秘密値を避けるため保存しない。

## 結果

実行日時、端末条件、起動結果、stage、終了コード、シグナル、画像結果、各時間、受領資料とハッシュ: すべて未受領。P1全体とゲーム操作E2Eは未通過。
