# 最新状態

更新: 2026-11-12（日本時間）。TEST089・LoopCtrl build148継続。[計画](plans/test089-native-ring.md)・[検証](reviews/test089.md)・[対象判定契約](contracts/target-assessment.md)。TEST088の実機判定128秒超を受け、証拠ZIPの20原PNG/実行記録を全照合した。対象入力は最終authority235の1枚。開発実3.9 profileはicon70%・PNG復元27%で、画素ループを同じiSH内の静的i386 helperへ移す。

## 今回の変更

Pythonは厳密PNG検証/有限inflateと最大4行×3slotの集約、同梱Cは復元・商品行・icon/nameの画素処理を担当する。全source/feature/ELF/toolchainをmanifestへ結合し、検証した56,136BをiSHの専用homeへ自動配置する。任意実行path/遅いPython fallbackなし。故障/取消/30秒期限では子を回収して固定理由を示し、通常pendingを保持する。閾値を緩めず、同slot絵と名前が一致した場合だけtarget、絵のみcandidate、不足unknown。未知は対象なしではない。

TEST089では最終ACK PAUSE画像を先に回収して暫定結果を表示する。全画像の保存・照合を継続し、最終certificate後にcacheを再検証して通常sidecar/ZIPを確定する。歩行診断画像は残す。早期結果・全保存完了を分け、未完了を終了と表示しない。iOS native/API/入力/歩行/IPA148・旧immutableZIPは変更しない。

実3.9/3.12のbridge、実i386/QEMUの分類・保存境界、固定実8runと合成例を選択検証する。8run全field/canonical bytesは旧判定と一致、人陰性4の誤target0、不明4は採点外。新合成5caseは明度/位置/第三slot/名前の欠けを確認。校正正例と同featureの変形を未知陽性評価へ数えず、未知陽性holdout0。稀な対象を出す周回はユーザーへ依頼しない。実iSH秒・人超えは未受入。

## 配布と実機確認

[完全ZIP](https://github.com/shuhei0720/necrogold-automation/releases/download/test089-native-ring/source.zip)・[固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test089-native-ring)。配布時に同toolchain再build同一性・全tracked blob/CRC/SHA・匿名全GET/actualtagを照合して返す。IPA更新不要。現処理が残る場合だけCtrl+C後promptを確認し、原データは消さない。新ZIPを展開してnecro_test089を選ぶ。

```sh
mkdir -p /mnt/necro_test089
mount -t ios . /mnt/necro_test089
cd /mnt/necro_test089 && sh test_088.sh
```

最初に同088 pendingの指輪判定と通常ZIP保存を完了する。ゲームが開かなくて正常。証拠回収用evidence_088.shは繰り返さない。完了後、LoopCtrlのStart Server/通常VPNを確認し、通常1-1ポーズから `sh test_089.sh` でrestart→金壁/通路候補→商店→全商品確認を3回。商品到達後にiSHへ戻り、暫定指輪表示と全画像/ZIP完了までの時間を別に確認する。runtime/test-088-<uuid>.zip と test-089-<uuid>.zip全回分を返却依頼。

## 維持する未解決

[IPA148](https://github.com/shuhei0720/necrogold-automation/releases/download/test087-build148/LoopCtrl.ipa) は17,629,270B/SHA `f4c9e9f1c02e76fb0921f31f5613f9a7986d825d2528e848aabbd82b00b33a76`。087 aeef427bの8UNKNOWN歩行停止と旧086実4 trigger355欠落は未修正/未確定。新版到達率・毎拍・人超え・未知陽性精度・OS背景通知/対象なし循環は未受入。自動購入0、候補保持、入力権限/UNKNOWN無再送/元期限・予算は維持。raw/秘密値はGit外。[索引](context.md)。
