# 最新状態

更新: 2026-11-12（日本時間）。TEST088証拠回収専用・LoopCtrl build148継続。[計画](plans/test088-evidence.md)・[検証](reviews/test088-evidence.md)・[判定/診断契約](contracts/target-assessment.md)。fix2実機は全画像照合後、指輪判定で128秒以上継続。前の軽量化では不十分で、判定性能は未解決。

## 今回の対応

指輪判定を一切呼ばず、保存済みの同088の全原画像と実行記録をverified診断ZIPへ回収する。新evidence088入口は既publication.lock下のstrict load→元certificateを使い、active/report/登録全PNGだけを別storage/別receipt/別evidence ZIPへ保存する。通常_publish/_inventory/classifier/prepare/Client/session/RPC0。

全CRC/SHA/sizeと元sourceを照合後に診断回収完了と表示する。元report/PNG/sidecar/parts・通常ZIP/receiptのbytes/mtimeを維持。既診断の再実行/別保存先、破損/foreign/未回収/symlink拒否と取消を確認。通常の未出版状態は残し、新ゲームstartを許可しない。対象判定成功/陰性や通常出版完了とは呼ばない。

実Python3.9で新4methodsが有効Assertion Red→Green。旧判定/通常entry/全native/IPAは無変更で、旧17/全Mac/C/IPA作成を再実行しない。同じ独立担当が差分/実物を確認する。追加C-iterator試作は1.43倍程度で不十分として未採用。native数値kernelの試作は製品外で今回配布を待たせない。

## 配布と今回の実機確認

[固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test088-evidence-recovery)・[証拠回収用完全ZIP](https://github.com/shuhei0720/necrogold-automation/releases/download/test088-evidence-recovery/source.zip)。全source/blob/CRC/匿名全GET/SHA/actualtagを確認して返す。以前の公開assetは変更しない。

IPA更新・LoopCtrl/VPNの再起動・ゲーム操作は不要。現在の処理をCtrl+Cで止め、prompt復帰を確認し、元データは消さない。新ZIPを展開しevidence_088.shがあるnecro_test088_evidenceフォルダを選択する。

```sh
mkdir -p /mnt/necro_test088_evidence
mount -t ios . /mnt/necro_test088_evidence
cd /mnt/necro_test088_evidence && sh evidence_088.sh
```

今回はこの回収だけを実機確認する。保存済み全画像/ZIP照合の完了後、runtime/test-088-evidence-<run_id>.zipを返却依頼。指輪判定やゲーム開始は行わない。重いtest_088.shの再実行や新しいゲーム試験は、実データを解析する前には要求しない。通常pendingは保持し、受領後に実画像の候補数/処理位置から根本修正を進める。

## 維持する状態と未解決

既IPAは[build148固定asset](https://github.com/shuhei0720/necrogold-automation/releases/download/test087-build148/LoopCtrl.ipa)、0.3.4/build148/min16、17,629,270B/SHA `f4c9e9f1c02e76fb0921f31f5613f9a7986d825d2528e848aabbd82b00b33a76`。全native/R12・core client/feature・通常entry/shは元c3ac8eb不変。bit_countの3.9例外は既に修正済み。fix2の進捗表示は動くが、実機128秒以上を性能合格にはしない。

087 aeef427bの8UNKNOWN歩行停止と旧086実4 trigger355欠落は未修正/未確定。新版到達率・iSH判定速度・毎拍/人超えは未受入。同slot絵/対象名の両一致だけtarget、絵のみcandidate、不足unknown。最大2画像、候補破棄/購入0、閉report/既immutableZIP不変。陰性holdout4の誤検出0、不明4/校正3は未知陽性評価外。OS背景通知/対象なし循環は現active未実装。入力権限・票/信用・旧W/P/50ms/10ms/8評価/全予算は緩めない。主指標は実機の全商品確認到達率。raw/Scene/秘密値はGit外。[索引](context.md)。
