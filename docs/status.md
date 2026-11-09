# 最新状態

更新: 2026-11-10（日本時間）。TEST061の実装・Mac93/client22・配布物照合が完了。実機は未実施で、次に商品確認までの到達を受け入れる。[全体設計](plans/test061-verified-progress.md)・[検証記録](reviews/test061.md)。回収済みTEST060は再実行しない。

## TEST061の配布物

| 項目 | 保存先・同一性 |
| --- | --- |
| code / CI | `c8ad31f21f21f0d44bc79fc35b488005291a8aa8` / [Mac93](https://github.com/shuhei0720/necrogold-automation/actions/runs/42656077891)・[client22](https://github.com/shuhei0720/necrogold-automation/actions/runs/42656083101) 同commit成功 |
| IPA ZIP | Mac93 → Artifacts → `loopctrl-ngg2-unsigned`（13692033851）。17,837,425bytes / SHA `76be95054f992162846279d19165e289ade853d409ddbeb793e2a58c92b7efa7` |
| 内部IPA | `upstream/release/LoopCtrl.ipa` / build93 / SHA `2c9990545330c59072a0c6d46a7c1b55d458075693c11cd1d624ba8d9b4433c5` |
| 診断ZIP | artifact13693990304 / 3,378,082bytes / SHA `a08b1cd95745b172d8af7623f6a0094d096d4c9c8fc52dd07904810b45e9c1b6` |
| native-host | artifact13691564818 / 36,596bytes / SHA `269c327f5fe6745d6aea6cdca6d905ab969a1ec15784b74689c46b3c528da1da` |
| build-source | [固定完全ZIP](https://codeload.github.com/shuhei0720/necrogold-automation/zip/c8ad31f21f21f0d44bc79fc35b488005291a8aa8)。全472tracked bytes/CRC/path一致。7,266,989bytes / SHA `3220859a44bb2c35d4408299a7c6fb92fa3e266f8ea3d6e9d2c600e920a8accb` |

配布時の最終source ZIPはこのcodeと文書だけが異なることを確認する。公開releaseは作らない。IPAの一時直リンクが期限切れなら、SafariでGitHubへログインしてMac93のArtifactsから取得する。

## 修正と検証

初歩の確実な未送信失効は、旧IDを撤回し元12秒以内でlive HUDを再取得。ACK後は次拍の入力期限scheduleDと元source/phase各3秒・walk45秒・session180秒の画像確認期限visualDを分離。途中35pxはUNKNOWNのまま待ち、真の移動/開通後に次行動を決める。旧次拍が過ぎた場合は新将来拍へ同期する。実commitとC処理後tickも検査。再送・閾値緩和・移動の推測は行わない。

API1.98.15-ngg2/cap13/client v14。失効前model/sampleのfirst/latest snapshotを保持、旧v1〜v13 journalは保存API1.98.14で回収。全22seal一致、変更5/不変17。Beat/Nav/Perception/Raster/入力座標・R12原40/G1は不変。

旧Cで途中停止のassertion Red。修正後は独立world10ケース（四方向×木鉄8＋LEFT→UP＋処理遅延）で開扉→進入→商品/PAUSE成功。local Controller184全method保持（assert1014→1035）・新Recovery29成功。Mac93は公開Controller179/Recovery29/Beat12/world3/package266、実Runtime新公開結合/新4故障、既存独立shop16、LoopCtrlKitが成功。client22は212件成功。重いworld160/全Runtime59は今回未実行。

実compiler/PBX/4C/5Swift/6RSP、22seal、全9Mach-O/98HOST・旧API marker非混入、IPA/全source ZIPを実物照合。実Runtime producer5件→暗号client→両journalの診断完全一致、shop16のstrict v14検査も成功。合成時計/画像・fixture通信であり、実ゲームやiPhone到達/速度の合格ではない。

## 次の実機TEST061

新IPAをSideStore更新→LoopCtrl完全終了/起動→Start Server→通常VPN/disk。新しい通常オールゾーン1-1、金壁全部/一部可視、左側が下/端0のポーズから。展開先の`test_061.sh`をiSHで実行する。

```sh
mkdir -p /mnt/necro_test061
mount -t ios . /mnt/necro_test061
cd /mnt/necro_test061 && sh test_061.sh
```

folder pickerは`test_061.sh`が入るフォルダを選ぶ。歩行中はゲーム前面、自動PAUSE後に約5秒待ってiSHへ戻り、`TEST-061: 終了`後の`runtime/test-061`全ZIPを依頼する。扉開放/入店/商品確認、歩き始めと拍の空きを確認する。

## 直前TEST060と運用

[受領記録](device-tests/README.md#test060-received)。商品確認0/2。1回目inputs/moves0・BEAT、途中25画像/model/sample欠落で失効内訳は断定不可。2回目LEFT1・C moves0、28→32 UNKNOWN・適格確認画像1枚だけで元motion期限の2.603ms後に停止。原参照27でもUNKNOWN。両方lead_confirmed0。原060再実行は不要。

TEST060 code `04b213f27364bc9e5cf3c68f9caf031f842fba97` / [Mac91](https://github.com/shuhei0720/necrogold-automation/actions/runs/42632308407)。旧配布物は[固定記録](https://github.com/shuhei0720/necrogold-automation/blob/42e625b0311c79c6d3e6acf19a150b9316fcc2a4/docs/status.md)・[review060](reviews/test060.md#test060-final-mac)。Mac92はfixture時計同期失敗、Runtime旧API残存も配布前に修正した。Mac92全体成功/IPA配布には数えない。

[最新開発方針](development-flow.md#最新の運用方針2026-11-10-日本時間): 固定時間なし、品質を落とさず変更範囲で検証。focused手動既定、fullは節目。新実装返却では実機依頼・完全source/IPA・手順・全runtime回収を必須にする。

ユーザーはMacを持たず実機試験を担当。CIの正規Macゲームは未導入。通常利用はiPhone単体、商品到達率・毎拍/人より速い処理・指輪未知評価・通知・自動周回・耐久は未受入。初読3文書≤16KiB、必要資料は[索引](context.md)から。rawZIP/画像/report/logはGit外。
