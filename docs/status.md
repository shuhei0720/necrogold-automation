# 最新状態

更新: 2026-11-12（クライアント日本時間）。TEST086/build146。[計画](plans/test086-vantage-gold.md)・[受領/検証](reviews/test086.md)。code `ba7abcd8fdd683001c2d7ae8b05cc4256b765e17`、run43170890633。TEST085の4run/80原PNG・18,473,950画像Bを全照合。全3商品可視2/4、全paused/terminal/drained/回収完了。見送りsource16/16保持だが093の既知見逃しを含む。選択native行欠損0、全取得画像保存ではない。

## 修正

原093は左角の口/外が床でも内側UNKNOWNのため候補から落ちた。UNKNOWNを床へ分類せず、固定4corner・観測口/外床/両壁/壁列3・金なし/元保護条件に加え、room内側endpointへの旧最短床path3がある場合だけ候補保持。元chooser/Controllerの有限接近で観測床へ向かう。原093以外の校正416Scene/既bitを保持した。

実4はACK後に実UP1と整合するが、単金1→1移動が旧15段でUNKNOWN。最後UNKNOWNだけへ同方向unitの別proofを追加。単金保持/全旧STONE最低2/非共線DIRT9/一意geometry・観測次床・raw73finite/9px/gap.08・元phase・blur95%/300/2帯100・axis75%/300/2帯100/元競合15ppを全AND。全期限・8評価・予算・UNKNOWN無再送、Controller/Perception/Beat/Runtime/core4は維持。

## 検証・配布

新12作者単体Red→Green。同code host37/11scope全Green。原417Scene全bytes不変・旧known全保持。Mac070旧Red1/現Green6・081保存Green6、無変更Runtimeの固定保存Red133は分離再利用。5実物verifier各1回PASS、実4C/Swift5/RSP6・全9MachO260marker不在・全651source/IPA照合。22seal1変更21不変、同じ独立担当静的/実物P0/P1/P2なしGO。

[TEST086/build146](https://github.com/shuhei0720/necrogold-automation/releases/tag/test086-build146)。[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test086-build146/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test086-build146/source.zip)。IPA0.3.4/build146/min16、17630155B/SHA `f3c8da2f68cd0abc842751d2b45d61024de9322e67349cb956cee9c541641a49`。closing文書3件のみ。固定3assetを公開後に匿名全GET/SHA/CRC照合して返す。

SideStore更新→LoopCtrl完全終了/起動→Start Server/通常VPN。展開したtest_086.shのフォルダをiSHへ選ぶ。

```sh
mkdir -p /mnt/necro_test086
mount -t ios . /mnt/necro_test086
cd /mnt/necro_test086 && sh test_086.sh
```

fresh通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認/PAUSEを5回。5秒以上ポーズならiSHへ戻り全画像/ZIP照合完了を待ち、runtime/test-086-<run_id>.zip全回分と商品可視/停止位置/候補見逃し/拍間隔を依頼。085再実行/追加回収不要。

新版実機到達率・恒久毎拍/人超え・対象識別/通知/対象なし循環は未受入。旧081実5金1→2/newDOOR確認は新proof対象外・未解決。同じiPhoneのみ・実機主軸/品質維持/時間上限なし。raw/Scene/秘密値はGit外。[索引](context.md)。
