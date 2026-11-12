# 最新状態

更新: 2026-11-12（クライアント日本時間）。TEST085/build144。[計画](plans/test085-verified-scheduling.md)・[受領/検証](reviews/test085.md)。code `97a8cbe5177d85be080a33107fd799599c045b83`、run43149743552。TEST084の4run/80原PNG・17,923,256画像Bを全照合。商品可視/自動完了2/4、全paused/terminal/drained/回収完了・正常見送りsource7/7保持。host/cancel/capture failure/timeout0、選択native行欠損0。全取得画像保存ではない。

## 修正

実2は最後の実歩がqualified reference133→141でMOVED確定したが、画像の取得→commit171msで次拍source200ms条件に9.153ms不足。元proofを消費する最初tickで、同ACK/確定MOVED・未発行next・最新proof・元P/D・100ms公開窓/200ms源不足を全ANDし、既有限再同期へ戻す。旧票/credit/元episode・command_sync/歩行/session・新50ms準備を保持。一般の期限失効やUNKNOWNは救済しない。

実3はビート品質ではなく、無金通路で独立静止が成立せず元2拍Wで停止。新zero-only proofは無金/金扉item保護なし・近傍/旧STONE保持・DIRT9/uniquezero幾何、raw73有限zero/gap.08、依存closure blur73zero最良/.45、world95%/300/帯100、axis75%/300/帯100/元競合15ppを全AND。元14stageとW/P/入力窓は維持。公開OBSERVE→元W内proof→元P/freshslotを確認。実4の金扉前待機はこの追加対象外で、短縮達成とはしない。

## 検証・配布

新12作者単体Red→Green。同code host33/10scope全Green、Mac070旧Red1/現Green6・081保存Green6。無変更Runtimeの固定保存Red133は別証拠再利用。5実物verifier各1回PASS、実4C/Swift5/RSP6・全9MachO249marker不在・全642source/IPA照合。同じ独立担当が静的/実物P0/P1/P2なしでGO。22seal2変更20不変、Runtime/core4・API16/cap15/client16/v2/旧回収維持。

[TEST085/build144](https://github.com/shuhei0720/necrogold-automation/releases/tag/test085-build144)。[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test085-build144/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test085-build144/source.zip)。IPA0.3.4/build144/min16、17626327B/SHA `ae16b4f3774b7c6bd2911e77165e6476342455313fc21f2d1e818c778f7a53d7`。closingは文書3件だけ。固定3assetを公開後に匿名全GET/SHA/CRC照合して返す。

SideStore更新→LoopCtrl完全終了/起動→Start Server/通常VPN。展開したtest_085.shのフォルダをiSHへ選ぶ。

```sh
mkdir -p /mnt/necro_test085
mount -t ios . /mnt/necro_test085
cd /mnt/necro_test085 && sh test_085.sh
```

fresh通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認/PAUSEを5回。5秒以上ポーズならiSHへ戻り全画像/ZIP照合完了を待ち、runtime/test-085-<run_id>.zip全回分と商品可視/停止位置/扉前待ち/候補見逃し/拍間隔を依頼。084再実行/追加回収不要。

新版実機の到達率・恒久毎拍/人超え・対象識別/通知/対象なし循環は未受入。旧081実5の金1→2移動確認は未解決。同じiPhoneのみ・実機主軸/品質維持/固定時間上限なし。raw/Scene/秘密値はGit外。[索引](context.md)。
