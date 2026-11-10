# 最新状態

更新: 2026-11-10（日本時間）。TEST061は商品確認0/2。実機を主に短く反復する最新指示をルールへ記録し、二つの停止原因だけを修正したTEST062を配布する。Mac94のdevice CI・実IPA照合完了、TEST062実機は未実施。[計画](plans/test062-device-cycle.md)・[検証](reviews/test062.md)。061/060は再実行しない。

## TEST062の配布物

| 項目 | 保存先・同一性 |
| --- | --- |
| code / CI | `afcb339624a4007390bbb326edabd3962057e758` / [Mac94](https://github.com/shuhei0720/necrogold-automation/actions/runs/42729732582) device成功 |
| IPA ZIP | Mac94→Artifacts→`loopctrl-ngg2-unsigned`（13724083342）。17,838,288bytes / SHA `cfb84047de76feed4e3c19384d8fb6cdbe51ee9cfc5f7664f263653cb988f241` |
| 内部IPA | `upstream/release/LoopCtrl.ipa` / build94 / SHA `645848e0d5d59b97e9338af586440df6f3f814008c56bb229e103bfb6e2eddd1` |
| 診断ZIP | artifact13724887405 / 158,348bytes / SHA `bc1b8d154b0662aae5eb362f6ecb176eeef3bf70466fa730dcfbcae26a023dde` |
| native-host | artifact13724880636 / 7,280bytes / SHA `a3d05f3f8823ebde782db60cf7b21cbfa39739021409f843feb1785cac640937` |
| build-source | [固定全コードZIP](https://codeload.github.com/shuhei0720/necrogold-automation/zip/afcb339624a4007390bbb326edabd3962057e758)。全479tracked bytes/CRC/path一致、7,287,498bytes / SHA `16d42e72a688b1725bb0c8db825c835e7f871b5703c6bc22a5241170bf54d726` |

最新ユーザー指定により、一時URLと期限付きActions artifactに代わる[固定配布](https://github.com/shuhei0720/necrogold-automation/releases/tag/test062-build94)へ切り替えた。[IPA直接取得](https://github.com/shuhei0720/necrogold-automation/releases/download/test062-build94/LoopCtrl-TEST062.ipa)・[全コードZIP](https://github.com/shuhei0720/necrogold-automation/releases/download/test062-build94/necro_test062-source.zip)。検証済みbuild94とsource5401c7dの同じbytesのみを配布し、raw実機資料/秘密値は公開しない。公開Release禁止という旧運用は、この固定ダウンロード指定で変更。

## 修正・今回の検証範囲

初歩の送信前50ms〜元Dで無害な遠方UNKNOWN/FLOOR/DIRT揺れをまとめる。両safe_floor、全gold/保護/近傍3×3不変、full5判断一致、同beforeへのstrict BLOCKEDを要求し、同ID/source/before/元期限を保持する。近傍・保護・経路等の変化は従来の再予約/拒否。上限2回を増やさない。

移動確認は初回即時、UNKNOWN/TWEEN後の2回目startは初回+元周期¼、3回目は初回+1周期以降。上限3評価、元visualD/実commit/次tick・同before/ACK prefix・商品優先・UNKNOWN無再送は維持する。早期に3回使い切らず、checkpoint前の完全画像も評価待ちになる。毎拍/速度達成とは主張しない。

API1.98.15-ngg2/cap13/client v14・公開ABI不変。native22seal中Controller.cだけ変更、他21・R12原40/G1不変。C SHA `8eab407b6baaa0f6c23ded1df9f1811323eba9fee52f2d179a40dcec035250f1`、manifest SHA `a87eb67fd11e14c5614ccd0284a2499da25cc420707ad9dcd5af24e71f178711`。

新11+関連12のC単体23、小workflow/selector12の35件を実IPAと同じpatched sourceで確認。独立差分レビュー1回、P0/P1なし、P2文言は修正済。実4C/5Swift/6RSP/PBX/profile/22sealと全9Mach-O/99 HOST・旧API marker非混入、全sourceを実物照合した。

今回、全Controller184/全Runtime故障/shop16/未変更Kit/client212は再実行していない。旧Mac93/client22の成功は過去結果。認識/並行/RPCコードはbytes不変で、変更したC条件を今回の単体で検証し、実機の商品到達を主指標に反復する。合成成功やCI件数で実機成功にしない。

## 次の実機TEST062

SideStoreで新IPA/build94更新→LoopCtrl完全終了/起動→Start Server→通常VPN/disk。新通常オールゾーン1-1、金壁全部/一部可視・左側が下/端0の開幕ポーズから。

```sh
mkdir -p /mnt/necro_test062
mount -t ios . /mnt/necro_test062
cd /mnt/necro_test062 && sh test_062.sh
```

folder pickerは展開先の`test_062.sh`が入るフォルダ。歩行中はゲーム前面、自動PAUSE後約5秒でiSHへ戻り`TEST-062: 終了`を待ち、`runtime/test-062`全ZIPを返却依頼する。商品が見えるまで進むか、扉開放/入店、拍の空きを確認する。

## 直前TEST061の受領事実

[受領台帳](device-tests/README.md#test061-received)。商品0/2、26PNG全検証、両run完了/drained。1回目0入力は遠方分類揺れで再予約2回を消費し、notBeforeの実commit4.924ms前にSCREEN17。2回目はユーザー2歩/C moves1、2入力目UPのACK後28/74/118ms開始画像が全UNKNOWN。ACK+156msでMOVEMENT10、visualDは約2.4秒残った。原参照でもUNKNOWNで認識閾値を下げない。未収録の次画像がMOVEDとは断定できない。

TEST061/build93配布物は[固定status](https://github.com/shuhei0720/necrogold-automation/blob/670cf33dc5a2ea1077c1b854ce67d021cd326dad/docs/status.md)・[review061](reviews/test061.md)。TEST060は[受領記録](device-tests/README.md#test060-received)。回収済みrunを追加回収目的で再実行しない。

## 運用と未受入

[最新方針](development-flow.md#最新の運用方針2026-11-10-日本時間): 実機ログ→局所修正→変更部単体/関連回帰→必要なIPA/同一性確認→次の実機。device既定、focused/fullは影響範囲/節目。固定時間なし、品質/安全条件は落とさない。

ユーザーはMacを持たず実機担当。CIの正規Macゲームは未導入、通常利用はiPhone単体。商品到達率・毎拍/人超え処理・指輪未知評価・通知・自動周回・耐久は未受入。初読3文書≤16KiB、必要資料は[索引](context.md)から。raw ZIP/画像/report/logはGit外。
