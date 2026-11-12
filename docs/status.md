# 最新状態

更新: 2026-11-12（日本時間）。TEST088・既LoopCtrl build148。[計画](plans/test087-python39.md#最新指示-test088として通常の実機試験を出し直す)・[検証](reviews/test087-python39.md)・[対象判定契約](contracts/target-assessment.md)。ユーザーは元ファイル削除済みで通常の実機テストを要求。保存再開の依頼を取り下げ、088の新しい実行記録で通常試験を出す。旧087 hidden原本/receiptは削除せず、087回復へ戻さない。

## 修正と検証

画像20/20保存後のPython3.9 AttributeErrorは、対象判定のint.bit_count（3.10追加）が原因。3式を同値のbin countへ修正済み。実3.9.25で有効Red→対象6/回復3全Green、[CI/run43194860629](https://github.com/shuhei0720/necrogold-automation/actions/runs/43194860629)でも9件成功。feature/閾値/閉schema/native不変。

TEST088はtest069.mainへtest_number=088・test087._prepareを渡す薄いentryと、087の番号だけを置換したsh。旧087の未出版結果と別spoolになり、通常088内の全画像/ZIP照合・未完優先・取消は既存処理を使う。実Python3.9 --checkとsh -n成功、同人差分レビューを行う。共有判定/出版の既9件は同bytesの過去結果として再利用し、意味試験/Mac/IPAを繰り返さない。

## 配布と今回の実機確認

[固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test088-python39-fix1)・[実機テスト用完全ZIP](https://github.com/shuhei0720/necrogold-automation/releases/download/test088-python39-fix1/source.zip)。全673sourceを保存commit/CRCと照合、公開後の匿名全GET/SHAを確認して返す。前087固定Releaseは変更しない。

**IPA更新不要。既build148を使用する。** LoopCtrlを完全終了→再起動→Start Server・通常VPNを有効化。通常1-1の新しいランをポーズする。ZIP展開後、test_088.shがあるnecro_test088フォルダを選択する。

```sh
mkdir -p /mnt/necro_test088
mount -t ios . /mnt/necro_test088
cd /mnt/necro_test088 && sh test_088.sh
```

「金壁/通路候補までrestart→商店→全商品/PAUSE→指輪判定→全画像/ZIP照合」を一連で3回依頼。5秒以上ポーズならiSHへ戻り完了表示まで待つ。表示されたruntime/test-088-<run_id>.zipを全回分と、商品可視/対象判定/停止位置/見逃しを返却依頼。旧runの回復や通常回収を終えるための追加再実行を求めない。

既IPAは[build148固定asset](https://github.com/shuhei0720/necrogold-automation/releases/download/test087-build148/LoopCtrl.ipa)、0.3.4/build148/min16、17,629,270B/SHA `f4c9e9f1c02e76fb0921f31f5613f9a7986d825d2528e848aabbd82b00b33a76`。native/R12等121pathは元build148不変、新IPA作成0。

## 未解決と継続要件

087添付aeef427bはMOVEMENT10/GOODS0、LEFT実1歩後ACK済みUPの変位確認8回UNKNOWNで停止。20PNG/4,072,671画像B・出版正常で、Python例外runとは別件。今回の歩行停止は未修正。旧086実4 trigger355も未保存で具体guard未確定。088実機到達率/iSH速度は未確認。

対象は同じ商品枠の絵/名前両一致だけtarget、絵のみcandidate、不足unknown。原086実3は校正陽性で、陰性holdout4の誤検出0、不明4/校正3は未知陽性評価外。未知陽性精度・OS背景通知/対象なし循環は未受入（後2つは現active未実装）。最大2枚・追加依存/外部画像送信/購入0、immutable sidecarは初ZIP前、閉native report不変。

主指標は全商品確認までの実機到達率。毎拍/人超えは未受入。入力権限・票/信用・旧W/P/50ms/10ms/8評価/全予算は緩めない。raw/Scene/秘密値はGit外。[索引](context.md)。
