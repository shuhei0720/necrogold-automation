# 最新状態

更新: 2026-11-10（日本時間）。TEST070の3回/41画像を受領し、商品全体可視1/3。[TEST071計画](plans/test071-observed-entry.md)・[検証](reviews/test071.md)。TEST071を固定Releaseへ保存した。実機の到達改善/完全毎拍は次の試験で確認する。

## TEST070受領と修正

添付順と実行順が逆で、device started_ns/原画から4ae60e18→c94d9812→3c1a844dが1〜3回目。全ZIP/41PNGのCRC/SHA/bytes/896×414/manifest/cursor/時刻prefix/active-report一致、全回収resolved=true。

1回目は5MOVED+1開扉+商品優先UNKNOWN1、3商品可視/GOODS/PAUSE。方向間隔.514〜.530秒でほぼ毎拍、ゲーム受信時刻がなく完全同期とは断定しない。2回目は開扉後2商品/PARTIALが正しく、同reason5/FLOOR/full5/金/全保護/strict BLOCKEDでも金bracket背後斜めのDIRT→FLOORでD−89.610msに停止。3回目は未送信reason6/DIRTの次セルがreason7/FLOORへ見え直し、TERRAIN_OPENED zero vectorでD−36.326msに停止。送信失敗/期限超過や商品認識閾値の誤りを原因にしない。

071は開扉ACK直後・未入店・両PARTIALの同入口票だけ、金壁で隔てられたforward2/lateral±1のFLOOR↔DIRT揺れを許す。元ID/全期限/full5/金/全保護/実next床/strict BLOCKEDは維持。2商品を完了扱いしない。

未送信dig対象が新床へ変わった回は旧票を撤回し、独立した後続画像の静止/full5/金/全保護を確認して、新ID・将来拍prep50ms以上・最新model sampleから判断し直す。1run1回、元verified12秒/旧sync/walk45/session180/16入力、送信UNKNOWN無再送・旧ID/epoch無効・未観測creditなしを維持。有効HUDを再利用する。Controller1件だけ変更、他native21/Runtime/Ticket/Nav/Perception/各閾値/API1.98.16/cap14/clientv15/wire/ABI不変。

## TEST071配布

code `6cab2f625b17bedb3cc8540ca4d8f717a3dc68d5`、[Mac112](https://github.com/shuhei0720/necrogold-automation/actions/runs/42832680834)成功。変更正例の固定070での意味的Red、新単体11件と既存関連32のGreen、CI選択23件と限定Mac dispatch/取消6呼出を確認。独立レビューP0/P1なし。22seal/実compiler4C・5Swift・6RSP/全9Mach-O/532build-source全bytes/CRCを照合。全Runtime/worldは累積せず、実ゲームCIは未実施。

IPA0.3.4/build112、17,589,531bytes/SHA `88c2ed0987dddf6514dad10a2d953f0418b04876b9192feaf2c83507b64a8144`。[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test071-build112/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test071-build112/source.zip)・[SHA256SUMS](https://github.com/shuhei0720/necrogold-automation/releases/download/test071-build112/SHA256SUMS.txt)。最終source差分はstatus/検証/台帳の3文書だけ、全製品bytes同一。固定assetの匿名GET/全SHAまで照合する。

## 必ず依頼する実機手順

SideStoreで新IPAへ更新し、LoopCtrlを完全終了→起動→Start Server、通常のVPNを有効にする。source.zipを展開。新しい通常1-1の金壁が見えるポーズから、まず2回依頼する。展開したsourceフォルダを選ぶ。

```sh
mkdir -p /mnt/necro_test071
mount -t ios . /mnt/necro_test071
cd /mnt/necro_test071 && sh test_071.sh
```

ゲームを前面に保ち、自動ポーズ後約5秒でiSHへ戻り、`TEST-071: 終了。画像とZIPの保存・照合が完了しました。`を待つ。2回目は同じフォルダで最後の行を再実行。`runtime/test-071-<run_id>.zip`全回分と、全商品可視/停止位置/既知通路の拍間隔・新地形での待ちを返してもらう。全画像/ZIP照合前に終了/次startしない。旧原本は保持し、回収済み070の再実行は不要。

## 運用

[要件](requirements/necrogold.md#2026-11-10-明かりによる新可視地形と歩行間隔): 新照明で経路判断が必要な1〜2拍のみ許容、それ以外は毎拍。[開発フロー](development-flow.md#最新の運用方針2026-11-10-日本時間): 実機ログ→局所修正→単体/関係回帰→必要なIPA/同一性→実機。品質安全条件不変/固定時間なし、通常差分レビュー1回。既承認branchへ保存、生ZIP/原画/report/log/秘密値はGit外。同じiPhoneだけ、ユーザーはMacを持たず実機担当。初読3文書≤16KiB、[索引](context.md)から必要資料だけ読む。
