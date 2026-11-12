# 最新状態

更新: 2026-11-12（日本時間）。TEST088保存後処理修正・既LoopCtrl build148。[計画](plans/test088-postprocess.md)・[検証](reviews/test088-postprocess.md)・[対象判定契約](contracts/target-assessment.md)。実機は画像取得後無表示、再実行も「前回のZIP保存を再開」から進まない。今回は同088の未出版結果を保持して改善する。

## 修正と証明範囲

実機の滞留箇所/秒は未確認。コードではcertificate/判定完了まで無表示で、開発実3.9 profileはiconが約96.5%。_iconだけRGBのtuple sumと元式の厳密な最大値上界による省略へ等価最適化する。探索順/同率box/丸め/feature/閾値/schemaは維持。原086校正309の全fieldも一致。未知陽性やiSH速度は未受入。

出版に段階表示、判定の既cancelチェックへ透過wrapperで初回/概ね5秒ごとの経過表示を追加。時間はstdoutだけでreport/sidecar不変、別thread/新依存/入力0。既immutable sidecar/ZIPは再分類・追記しない。未完を別番号で飛ばさず、時限unknownや陰性を作らない。

有効Red→実3.9で新性能2/既target6/新進捗2/旧回復3の13件成功。関連出版4は開発Python3.12.14で成功、計17methods。原309は校正で全field exact、精度holdoutではない。native/IPA不変のため新Mac/C/IPA作成0。Python3.9のbit_countエラーは前版で修正済み、今回も維持する。

## 配布と今回の実機確認

[固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test088-postprocess-fix2)・[修正版完全ZIP](https://github.com/shuhei0720/necrogold-automation/releases/download/test088-postprocess-fix2/source.zip)。完全source/全blob/CRCと匿名全GET/SHA/actual tagを照合して返す。以前の公開087/088 assetは変更しない。

IPA更新不要。現在のiSH待機はCtrl+Cで止め、元データを消さない。新ZIPを展開しtest_088.shがあるnecro_test088フォルダを選択する。同じ088の永続原本を読むのでmount先名を変えても前回runを再開できる。

```sh
mkdir -p /mnt/necro_test088_fix2
mount -t ios . /mnt/necro_test088_fix2
cd /mnt/necro_test088_fix2 && sh test_088.sh
```

まず前回分の保存完了を実機確認する。初回は「前回ZIP保存を再開」でゲームが開かなくて正常。照合/判定経過/ZIP保存のどこまで進むか確認し、完了表示後runtime/test-088-<run_id>.zipを返却依頼。未完なら最後の表示と経過秒を依頼する。完了後は通常1-1の新ランをポーズし、同コマンドでrestart→金壁/候補→店→全商品PAUSE/判定/ZIPを3回依頼。5秒以上ポーズならiSHで完了まで待ち、全run ZIP/商品可視/停止位置/見逃し/所要時間を返却する。

既IPAは[build148固定asset](https://github.com/shuhei0720/necrogold-automation/releases/download/test087-build148/LoopCtrl.ipa)、0.3.4/build148/min16、17,629,270B/SHA `f4c9e9f1c02e76fb0921f31f5613f9a7986d825d2528e848aabbd82b00b33a76`。新IPA/更新は不要。後処理回復ではLoopCtrl再起動も不要。

## 未解決と継続要件

087 aeef427bのLEFT実1歩後UPの8UNKNOWN停止と旧086実4 trigger355欠落は未修正/未確定。今回のiSH後処理修正と区別する。088新版到達率/実所要時間・恒久毎拍/人超えは未受入。

同商品枠の絵/対象名両一致だけtarget、絵のみcandidate、不足unknown。最大2画像・外部送信/購入/候補破棄0、閉native report不変。陰性holdout4の誤検出0、不明4/校正3は未知陽性評価外。OS背景通知/対象なし循環は現active未実装。入力権限・票/信用・旧W/P/50ms/10ms/8評価/全予算は緩めない。主指標は実機の全商品確認までの到達率。raw/Scene/秘密値はGit外。[索引](context.md)。
