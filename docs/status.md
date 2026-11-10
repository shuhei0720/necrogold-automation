# 最新状態

更新: 2026-11-11（日本時間）。TEST071全3run/48原画の商品全体可視0/3を受け、停止修正と金壁不可視の通路接近をTEST072へ実装。[計画](plans/test072-approach.md)・[検証](reviews/test072.md)・[限定契約](contracts/passage-approach.md)。実機の到達率/新パターン精度/完全毎拍は次の一連テストで確認する。

## 受領と変更

実行順88384bb8→2e398828→318e3f42（添付順と異なる）。全ZIP/48PNGのhash/CRC/manifest等を照合し全回収完了。1は商品保護が隣のGOLDに重なり開扉後停止、2は経路不変の遠方palette揺れでSAME上限停止、3は狭い地形の支持不足で実開扉をUNKNOWNとして停止。送信間隔約.505〜.526秒。raw/監査詳細はGit外と検証資料に保存。

072は不通行GOLD上の保護と歩行床を区別し、経路不変の未入店reason8は元ID/全clockを保持して不要な空拍を避ける。それ以外の資格ある未送信新観測は旧票撤回→独立静止pair→別IDへ。開扉UNKNOWNは専用detail/2帯で元300支持/95%/15ppを証明、開扉だけで歩数を増やさない。

新要件の12画像は上/左通路familyとして実装。観測床だけで固定した通路口へ接近し、明かりで見えた地形を各歩後に再評価。金壁が現れたら従来の商店経路で全商品可視位置へ。外側へ実到達し独立CLEARなら局所見送り→restart、未知のまま到達不能/不明金/商品候補は保持。普通扉/未知床へ盲目に進まない。restart前の終点画像を基準に新levelを証明し、座標/lead/予約を撤回。総入力/IDs/最初のwalk45秒等は保持する。

## TEST072配布

code `8a54beb6e5b046b7ec801afbe4e7339c2eb4e702`、[Mac114](https://github.com/shuhei0720/necrogold-automation/actions/runs/42849699171)成功。機能ごとの意味的Red→Green、選択CI58件と限定Runtime6呼出、独立3観点の最終差分レビューを確認。レビューのP1（初回未開始時計/不明金の見送り/実金tileとCLEARの不整合）は各Red→最小fixで閉じた。22seal/実compiler4C・5Swift・6RSP/全9Mach-O/全541build-sourceを照合。実ゲームCIは未実施。

Controller/Nav/Coreの3source変更、他19/Runtime/Perception/取得/閾値/API1.98.16/cap14/clientv15/wire/ABI/R12原40/G1不変。IPA0.3.4/build114、17,596,172bytes/SHA `1851faf6fa5ec694bfc756a3522c8b50cc37567e087ceef9e1a7a2908a70e0ea`。

[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test072-build114/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test072-build114/source.zip)・[SHA256SUMS](https://github.com/shuhei0720/necrogold-automation/releases/download/test072-build114/SHA256SUMS.txt)。最終sourceとの差分はstatus/本検証/台帳3文書だけ、全製品bytes同一。固定assetの匿名GET/全SHAまで照合する。

## 必ず依頼する一連の実機テスト

[最新指示](requirements/necrogold.md#2026-11-11-実機試験を一連の周回商品確認へ統合): 候補までリスタート→金壁または通路候補へ接近→商店へ移動→全商品確認を一回とする。途中の歩数/開扉を完了にしない。開始配置を金可視へ揃えず、毎回新しい通常1-1のポーズから、まず2回依頼する。

SideStoreで新IPAへ更新→LoopCtrl完全終了/起動→Start Server、通常のVPNを有効にする。source.zipを展開し、フォルダ選択では展開したsourceフォルダを選ぶ。

```sh
mkdir -p /mnt/necro_test072
mount -t ios . /mnt/necro_test072
cd /mnt/necro_test072 && sh test_072.sh
```

リスタート途中の短いポーズではゲームを前面に保つ。ポーズのまま5秒以上変わらなくなったらiSHへ戻る。`TEST-072: 終了。画像とZIPの保存・照合が完了しました。`を待ち、2回目は新しい通常1-1を用意して同じフォルダで最後の行を再実行。自動`runtime/test-072-<run_id>.zip`全回分と、リスタート/候補発見/入店/全商品可視/停止位置/拍間隔を返してもらう。上限/未判定/障害停止は商品確認成功にしない。回収済み071の再実行/追加回収は不要。

## 運用

同じiPhoneだけ、ユーザーはMacを持たず実機担当。必要な時間を使い品質を維持。実機ログ→局所修正→単体/関係回帰→必要なIPA/同一性→実機。通常フルRuntime/worldを累積せず、既知通路は毎拍、新地形で実際の経路判断が必要な1〜2拍だけ許容。未確認入力無再送/商品候補保持/全画像照合前の終了・次start禁止。raw/秘密値はGit外、既承認branchへ保存。初読3文書≤16KiB、[索引](context.md)から必要資料だけ読む。
