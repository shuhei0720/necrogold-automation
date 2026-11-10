# 最新状態

更新: 2026-11-10（日本時間）。TEST062はユーザーの商品可視1/2、プログラム完全商品判定0/2。3歩目の確実未送信期限切れだけを修正したTEST063を配布する。Mac96 device・実IPA照合完了、TEST063実機は未実施。[計画](plans/test063-unsent-deadline.md)・[検証](reviews/test063.md)。成功経路/全認識閾値は不変、回収済み062/061を再実行しない。

## TEST063の配布物

固定配布: [IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test063-build96/LoopCtrl.ipa)・[全コードZIP](https://github.com/shuhei0720/necrogold-automation/releases/download/test063-build96/source.zip)。一時署名URLを返さず、検証済み未署名IPA/sourceだけをRelease assetへ保存する。実機raw資料/秘密値は公開しない。

| 項目 | 保存先・同一性 |
| --- | --- |
| code / CI | `d7b42b627caa0e1c28b1c4a4900f2e0bc1a22323` / [Mac96](https://github.com/shuhei0720/necrogold-automation/actions/runs/42742052789) device成功 |
| IPA ZIP | artifact13729908405 / 17,840,993bytes / SHA `7c2eeb2517b651ccd40f262ab3c432d96ad4f440b8b7cac08df7f7543f7ac3de` |
| 内部IPA | `upstream/release/LoopCtrl.ipa` / build96 / SHA `61e0e40c0f78e226d64aae97dfc053aaba3638ca52d12014be268c21dcb09b06` |
| 診断ZIP | artifact13730535453 / 156,430bytes / SHA `b0af1d27e221fb65129f88c9eb1797a68051f40afa377acf20002673f314bca6` |
| native-host | artifact13729133020 / 9,086bytes / SHA `a827209142da184108576fa895bed9cacd88b42bb2f24e2a81eb73bb1f157902` |
| build-source | [固定全コードZIP](https://codeload.github.com/shuhei0720/necrogold-automation/zip/d7b42b627caa0e1c28b1c4a4900f2e0bc1a22323)。全483tracked bytes/CRC/path一致、7,302,154bytes / SHA `9cc4e37182d0d29e06a4f977426922fafe15e34ace32fc82a99ef40ff087242c` |

配布の最終sourceはこのcodeと文書だけの差分と確認する。固定配布処理は7入力をnetwork前に検査し、全SHAと空draft所有先、upload後3digest一致を確認して公開する。

## 修正と今回の検証

確認済みの位置から予約した連続MOVEが、開始しないまま元Dを超えた場合だけLATE/not_sentで撤回し、新しい将来拍へ戻す。state1/初回未送信、最新の同prefix、同一FLOOR world/gold/保護/full5判断、strict BLOCKEDと鮮度を要求する。取消/権限/商品・state2/3/4・不明入力・期限内complete0は対象外。同じ入力の再送や元D延長はしない。

実commitで確認したMOVED/開扉/茶壁開通から元12秒を数え、再失効でepisode/予算を増やさない。walk45/session180・未来拍の準備50msを保持。新しい実proofだけが新予算を作れる。モデルが有効なら新将来拍へ利用し、失効時だけ再取得する。

API1.98.15-ngg2/cap13/client v14/公開ABIは不変。22seal中Controller.cだけ変更、他21・R12原40/G1は不変。C SHA `f0ffaf8e3d4985bdf1ac99d4b8b258019673e2a7e7a19ca3373c80d2ff0e3878`、manifest SHA `fb1a064c469ff65eba0b2aa9d77978bba666e0009f3afccbbe36994410b58b32`。

新12＋関連23のC単体35、小CI検査15の50件を実IPAと同じpatched sourceで確認。独立差分レビューP0/P1なし、P2のsignature-only drift負例を追加。実4C/5Swift/6RSP/PBX/profile、22seal、全9Mach-O/100 HOST・旧API marker非混入、完全sourceを実物照合した。

全Controller184/全Runtime故障/shop16/未変更Kit/client212は今回再実行していない。過去のMac93/client22は過去結果であり新成功と書かない。原画98の自己比較は実CでBLOCKED、FLOOR/GOODS_UNKNOWN/GOLD_CANDIDATE/full5判断/同prefixを確認した。欠落HUDモデル/未来画像を補った完全再生ではない。

## 次の実機TEST063

SideStoreで新IPA/build96更新→LoopCtrl完全終了/起動→Start Server→通常VPN/disk。新しい通常オールゾーン1-1の金壁可視・左側が下/端0の開幕ポーズから。

```sh
mkdir -p /mnt/necro_test063
mount -t ios . /mnt/necro_test063
cd /mnt/necro_test063 && sh test_063.sh
```

folder pickerは展開した`test_063.sh`が入るフォルダ。歩行中はゲーム前面、自動PAUSE後約5秒でiSHへ戻り`TEST-063: 終了`を待ち、`runtime/test-063`全ZIPを依頼する。商品可視まで、扉開放/入店、拍の空きを確認する。

## TEST062受領事実と残課題

[受領台帳](device-tests/README.md#test062-received)。29PNG/全SHA/CRC/寸法/manifest一致、両run完了/drained。1回目は6入力=5移動+開扉1。149/151/152で商品と価格が見えるがCはPARTIAL1、その後pause-iconだけ不成立でUNKNOWN→SCREEN17。最後の入店MOVE11は未送信、開扉後の追加方向入力/購入0。ユーザーの商品可視1/2とプログラム完全商品判定0/2を区別する。

2回目は2入力/2実移動。3歩目SAME再予約のAXquery開始D+1.315ms、gateD+7.996msで未送信拒否→CAPTURE6。画像取得故障ではない。この条件を063で回復対象とした。完全商品判定/画面判定の安定化は残課題とし今回は閾値を変えない。

062の[固定配布](https://github.com/shuhei0720/necrogold-automation/releases/tag/test062-build94)と[旧status](https://github.com/shuhei0720/necrogold-automation/blob/8f21455fc1564279824175d848062775094a21d1/docs/status.md)は保持。回収済みrunを追加回収目的で再実行しない。

## 運用・未受入

[最新方針](development-flow.md#最新の運用方針2026-11-10-日本時間): 実機ログ→局所修正→単体/関連回帰→必要なIPA/同一性確認→次の実機。device既定、focused/fullは影響範囲/節目。固定時間なし・品質/安全条件は落とさない。配布URLは固定Release asset。

ユーザーはMacを持たず実機担当、正規Macゲームは未導入。通常利用はiPhone単体。商品到達率・完全商品判定・毎拍/人超え・指輪未知評価・通知・自動周回・耐久は未受入。初読3文書≤16KiB、必要資料は[索引](context.md)から。raw ZIP/画像/report/logはGit外。
