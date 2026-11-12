# 最新状態

更新: 2026-11-12（日本時間）。TEST087/build148のPython3.9互換修正。参照:[短い計画](plans/test087-python39.md)・[受領/検証](reviews/test087-python39.md)。前版の[判定実装/校正範囲](reviews/test087.md)・[対象判定契約](contracts/target-assessment.md)を維持。

## 今回のエラーと修正

実機Python3.9で画像20/20保存後、指輪判定の `int.bit_count`（3.10追加）がAttributeErrorとなりZIP公開前に停止。互換性の検証漏れを修正し、3式を同値のbin countへ変更した。feature/閾値/判定schema/native/通常087 entryと元spoolは不変。

新 `recover_087.sh` はiSHの `~/.necroprobe/runtime/test-087` を読み、同UUID・元report/PNGを保持して判定/ZIP公開だけを再開する。lock→strict load→元certificate/prepare/publishを使い、ゲーム起動/新session/RPC0。空・未完・破損は拒否し、既出版なら同ZIPの検証だけ。SIGINT/TERMでデータ保持する。回収済みrunから新ゲームを開始しない。

実Python3.9.25で有効Red→対象6/回復3全Green。元086実3の原309校正画像もtargetを維持。[CI1/run43194860629](https://github.com/shuhei0720/necrogold-automation/actions/runs/43194860629)も実3.9で9件成功。同じ独立担当の差分レビューGO。native/R12と既entry等121pathは元build148とbytes一致、新IPA作成0、実機回復/iSH速度は未確認。

添付aeef427bは1回目の別runで20PNG/4,072,671画像B・全照合/ZIP公開済み。MOVEMENT10/GOODS0、LEFT実1歩後、ACK済みUPの変位確認8回UNKNOWNで停止。Python例外runとは別原因で、歩行停止は今回未修正。2回目の未公開ZIPを先に回復する。

## 配布と今回の実機確認

[修正版の固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test087-python39-fix1)・[完全source ZIP](https://github.com/shuhei0720/necrogold-automation/releases/download/test087-python39-fix1/source.zip)。source全671ファイルをclosing commitと照合し、公開後の固定assetを匿名全GET/SHA/CRC検証して返す。

**IPA更新・LoopCtrl再起動・ゲーム再実行は不要。保存済み結果の回復だけを依頼する。** 元iSHデータを残し、ZIP展開後 `recover_087.sh` があるフォルダをmount選択する。

```sh
mkdir -p /mnt/necro_test087_fix
mount -t ios . /mnt/necro_test087_fix
cd /mnt/necro_test087_fix && sh recover_087.sh
```

判定と全画像/ZIP照合の完了を待ち、表示された `runtime/test-087-<run_id>.zip` を返却依頼。今回は通常の `test_087.sh` で新しいゲーム試験を始めない。回復後、その実画像/判定と別件の歩行停止を確認して次の実機版へ進む。

既IPAは[build148固定asset](https://github.com/shuhei0720/necrogold-automation/releases/download/test087-build148/LoopCtrl.ipa)、0.3.4/build148/min16、17,629,270B/SHA `f4c9e9f1c02e76fb0921f31f5613f9a7986d825d2528e848aabbd82b00b33a76`。今回は再配布/再ビルドしない。

## 継続する限界と要件

同iPhoneの保存済み商品枠で絵と対象名の両一致だけ「のろいのゆびわ」target、絵のみcandidate、不足unknown。最大2枚、追加依存/外部画像送信/購入0、immutable sidecarは初ZIP前に保存し閉native report不変。陰性holdout4の誤検出0、不明4/校正3は未知陽性評価外。未知陽性精度・OS背景通知/対象なし循環は未受入（後2つは現active未実装）。

旧086実4の停止trigger355は未保存で具体guard未確定。今回087実1も別件として保持。入力権限・票/信用・旧W/P/50ms/10ms/8評価/全予算は緩めない。主指標は全商品確認までの実機到達率。恒久毎拍/人超えは未受入。以後の通常実機は1-1ポーズから「restart→金壁/通路候補→店→全商品/PAUSE」を一連とし、回収完了前に終了表示や新startをしない。raw/Scene/秘密値はGit外。[索引](context.md)。
