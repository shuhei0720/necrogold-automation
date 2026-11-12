# 最新状態

更新: 2026-11-12（クライアント日本時間）。TEST084/build142。[計画](plans/test084-mouth-icon.md)・[受領/検証](reviews/test084.md)。code `2d6a150e26975f0d5fa0f6818edcf20f8dd965ac`、run43139153631。TEST083の4run/80原PNGを全照合。全商品は人目可視4/4、自動GOODS・PAUSE3/4。全terminal/drained/回収完了、正常見送りsource9/9保持。実4初期16/45の古いnative ring行は欠損だがexport metadata/画像は正常。全取得画像保存ではない。

## 変更と根拠

元UNKNOWN/black入口/fullRGB各≤12/full.spreadだけで、固定上300pxの≥95%黒と下325pxの≥90%非黒・元floor色/textureを要求し、観測床を回復する。別途、観測FLOOR口/外FLOOR・片脇壁/他UNKNOWN・同初期壁列3だけを上/左候補へ加える。旧palette/二壁/UNKNOWN口・固定10口・保護/FLOOR経路・有限探索は保つ。257校正画像の通常95cell/67画像だけUNKNOWN→FLOOR、指定3見逃し画像のmask改善・既bit喪失0。

商品到達後、商人表示と重なったpause記号を元full36×36/neutral/IoU.8の9px openingで認識する。raw/元13・11px/他HUD gateを維持。原379だけScene state UNKNOWN→FLOOR/商品VISIBLEを回復、旧NEG11新採用0。最初拒否285の原画欠損は379で代用しない。同ACKの最初non-FLOOR拒否を既STATE4診断へ残し、入力/評価/期限/予算は変えない。保存成功は新実機前に未確認。

## 検証・配布

新18作者単体Red→Green。最初CI141は旧fixtureの10ms間隔が元period/10未満で1件失敗、基準083でも同じ失敗を確認。全assertと製品条件を保ちfixture時刻だけ訂正し、不適格間隔の評価不増も確認した。修正後同code host38/13scope全Green（native33/client2/self3）、Mac070旧Red1/現Green6・081保存Green6。既保存Red133は別証拠再利用。5実物verifier各1回PASS、実compiler4C/Swift5/RSP6・全9MachO237marker不在・全633source/IPA照合。同じ独立担当が静的/実物P0/P1/P2なしでGO。22seal3変更19不変、Runtime/core4・API16/cap15/client16/v2/旧回収維持。

[TEST084/build142](https://github.com/shuhei0720/necrogold-automation/releases/tag/test084-build142)。[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test084-build142/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test084-build142/source.zip)。IPA0.3.4/build142/min16、17625904B/SHA `ee4f62ad4ce11886989ae9ea2c14c12edaf96eb303f8e7ee50986586651f0495`。closingは文書3件のみ。固定3assetを公開後に匿名全GET/SHA/CRC照合して返す。

SideStore更新→LoopCtrl完全終了/起動→Start Server/通常VPN。展開したtest_084.shのフォルダをiSHへ選ぶ。

```sh
mkdir -p /mnt/necro_test084
mount -t ios . /mnt/necro_test084
cd /mnt/necro_test084 && sh test_084.sh
```

fresh通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認/PAUSEを5回。5秒以上ポーズならiSHへ戻り全画像/ZIP照合完了を待ち、runtime/test-084-<run_id>.zip全回分と商品全体可視/停止位置/候補見逃し/拍間隔を依頼。083再実行/追加回収不要。

旧081実5の金1→2移動確認は未解決。新版実機の到達率/見逃し率・恒久毎拍/人超え・対象識別/通知/対象なし循環は未受入。同じiPhoneのみ・実機主軸/品質維持/固定時間上限なし。raw/Scene/秘密値はGit外。[索引](context.md)。
