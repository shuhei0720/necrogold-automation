# 最新状態

更新: 2026-11-12（日本時間）。TEST087/build148。[計画](plans/test087-target-pause.md)・[受領/検証](reviews/test087.md)・[対象判定契約](contracts/target-assessment.md)。code `8553efb7a487b71e9be333a054465f76f4017111`、run43184318092。TEST086の4ZIP/80PNG・19,260,301画像Bを全照合。商品3点可視3/4・全paused/terminal/drained/回収完了、見送りsource21/21保持。実2は回収RPCdeadline3/cancel2、実4原16はnative行欠損を伴うがPNG/export正常。全取得画像保存ではない。

## 修正と限界

同iPhoneのiSH内で、既nativeポーズ・画像保存照合後に「のろいのゆびわ」を判定。同じ商品枠の絵と対象名が共に一致した場合target、絵だけならcandidate、不足はunknown。価格/固定run位置を使わず最大2枚、追加依存/画像外部送信/購入/リスタート0。判定を表示しimmutable target-assessment.jsonを初ZIP前に保存、閉native reportは不変。source/ACKの結合と保存中断の同run再開を確認した。

原086実3は新判定でtarget、別ringの実1はunknown。現在3runは校正。調整に使わず固定した旧8runは明示陰性4で誤検出0、不明4は陰性へ数えず、陽性holdout0。未知陽性精度/iSH処理速度・OS背景通知/対象なし循環は未受入（後2つは現active未実装）。

実4の歩行停止は未解決。取消trigger355が未保存で最初の具体guardは未確定。閾値/期限を緩めず、通路の実差分があるUNKNOWN静止待ち入口を既診断へ記録し比較画像を優先保存する。signature-only mask0は対象外。入力権限・票/信用・旧W/P/50ms/10ms/8評価/全予算を維持。

## 検証と配布

新15（native3/target6/出版6）と関連旧15・self3、同code host33/10scope全Green。5実物各1回PASS・実4C/Swift5/RSP6・9MachO268marker不在・全664source/IPA照合。22seal Controller1変更21不変。Runtime/Nav/Perception/Beat・core client3/API16/cap15/client16/旧v1維持、test069は変更。同じ独立担当静的/実物P0/P1なしGO。

[固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test087-build148)・[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test087-build148/LoopCtrl.ipa)・[全コードZIP](https://github.com/shuhei0720/necrogold-automation/releases/download/test087-build148/source.zip)。IPA0.3.4/build148/min16、17629270B/SHA `f4c9e9f1c02e76fb0921f31f5613f9a7986d825d2528e848aabbd82b00b33a76`。closingは文書3件のみ。公開後3assetを匿名全GET/SHA/CRC照合して返す。

SideStore更新→LoopCtrl完全終了/起動→Start Server/通常VPN。展開したtest_087.shのフォルダをiSHへ選ぶ。

```sh
mkdir -p /mnt/necro_test087
mount -t ios . /mnt/necro_test087
cd /mnt/necro_test087 && sh test_087.sh
```

新しい通常1-1ポーズからrestart→金壁/候補→店→全商品/PAUSE→対象判定/ZIPまで5回。5秒以上ポーズならiSHへ戻り判定と全保存照合完了を待ち、runtime/test-087-<run_id>.zip全回分と対象表示/商品可視/停止位置/見逃し/拍間隔を依頼。086再実行/回収不要。新版実機到達率・恒久毎拍/人超えは未受入。raw/Scene/秘密値はGit外。[索引](context.md)。
