# 最新状態

更新: 2026-11-12（クライアント日本時間）。TEST083/build139。[計画](plans/test083-first-gold-goods-view.md)・[受領/検証](reviews/test083.md)。code `2779b2b4f4aa38a741a8a75cb6896f3c11a236ae`、run43127850144。TEST082の4run/80原PNGを全照合、実2原494/実3原199で全3商品を確認し到達2/4。全PAUSE/完収、正常見送り判断16/16保持。実2の古いnative bounded ring3行は欠損、exportmetadata/画像は正常。全取得画像保存ではない。

## 変更と根拠

既DIRTのfullR/G/Bと固定upper300/同tile内outer-lower125の二つの床色/textureを要求する別proofで、商人HPが重なった床を確認。全750実依存pixelへ元HUD/画像範囲除外を適用する。旧palette/gate/wood/量子化082の3proof・商品/保護/可視条件を維持。177校正画像ではDIRT→FLOOR36セルだけ、全非tile bytes不変。

実入店/PARTIAL/grid内ITEMに限り、既入口半平面内の観測FLOOR経路から商品位置の画面端overflowを厳密に減らすgoalをGOLD接近より優先。world±16/商品・保護/入口通過/旧reason8全5fieldと1歩入力を維持、改善無しは旧chooserへ戻す。帯は位置ヒントであり成功は元VISIBLEだけ。

無金探索中の実1歩で初金1セルが新露出するケースへ、元投影UNKNOWN/旧STONE全保持・非共線DIRT unique9・raw有限unit/gap・原075 blur/独立phaseを全ANDする別motion補助を追加。元113の8px/後続INFは拒否し、元115の適格画像でLEFT1を確認する。開通/入店credit・UNKNOWN再送・元期限/8評価/予算は増やさない。

## 検証・配布

新16作者単体は有効Red→Green。同code host40/16scope全Green（native36/client1/self3）、Mac070旧Red1/現Green6・081保存Green6、過去の意味Red133は別証拠再利用。5実物verifier各1回PASS、実C4/Swift5/RSP6・全9MachO225marker不在・全622source/IPAを照合。同じ独立担当が静的/実物ともP0/P1/P2なしでGO。Runtime/Controller/core4・API16/cap15/client16/v2・22seal2変更20不変を確認。

[TEST083/build139](https://github.com/shuhei0720/necrogold-automation/releases/tag/test083-build139)。[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test083-build139/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test083-build139/source.zip)。IPA0.3.4/build139/min16、17624015B/SHA `f479dffd2d05f475ef004d591ab53a12c407cb3a11a7c9ca7e902db9210cd06f`。closingは文書3件だけで製品不変。固定3assetを公開後に匿名全GET/SHA/CRC照合して返す。

SideStore更新→LoopCtrl完全終了/起動→Start Server/通常VPN。展開したtest_083.shのフォルダをiSHへ選ぶ。

```sh
mkdir -p /mnt/necro_test083
mount -t ios . /mnt/necro_test083
cd /mnt/necro_test083 && sh test_083.sh
```

fresh通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認を5回。5秒以上ポーズならiSHへ戻り全画像/ZIP照合完了を待ち、runtime/test-083-<run_id>.zip全回分と商品全体可視/停止位置/逆方向/候補見逃し/拍間隔を依頼。082再実行/追加回収は不要。

旧081実5最後の金1→2移動確認は未解決で今回0→1と異なる。新実機の到達率/見逃し率・恒久毎拍/人超え・対象認識/通知/対象なし自動循環は未受入。同じiPhoneのみ・実機主軸/品質維持/固定時間上限なし。raw/Scene/秘密値はGit外。[索引](context.md)。
