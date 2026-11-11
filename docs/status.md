# 最新状態

更新: 2026-11-11（日本時間）。TEST073の6run/114原画で全商品可視0/6。実restart計13回は成立したが、暗い開始画像の金見逃し/誤通路固定、開扉/実移動のUNKNOWN停止があった。TEST074で局所修正し新IPAを配布。[計画](plans/test074-visible-evidence.md)・[根拠/検証](reviews/test074.md)。074実機は未実施。

## 根拠と修正

実順4bc9e087→7414d4ee→0c7d26c2→2e5edcd9→c73a3854→5772e818。6ZIP/114PNGのhash/CRC/manifest/prefix/cursor/report一致、全回収resolved/terminal/drained/最終PAUSE成立。1/2/4/5は描画直後の通路候補が初歩前に消失し壁へ戻るが旧口へ歩いた。1の31は暗い左金壁がpeak58/CLEARで見送り。3は実開扉後2商品のみ、6は実LEFT1tile後UNKNOWN8評価で停止。保持省略を未来画像で補わずrawはGit外。

074はUI後の最初のFLOORから200ms以上の独立stable/current-prefix新観測で初期分類を確認。初歩前同原点・level0の候補は2画像の同mask/口/脇で再検査し、確かな壁に戻った旧口の未送信票/slotsを撤回する。初期待機中の正常な不確実FLOORは旧proofを失効して元4秒/同期12秒内で待ち、新gold/商品を優先。200msのfade十分性は未実測。

動作primaryと元閾値を維持し、UNKNOWNだけへ既知地形の補助証明を追加。開扉は唯一gold bracket/zero/DOOR→FLOOR/強い中心半差勾配、金なしunitは全旧STONE2+一意translation/非共線DIRT/強いexpanded detail。全73候補/支持300/95%/競合15pp/独立2領域100を維持（競合支持300未満は旧ルールで候補外）。未来nextの未知/壁は過去の到達creditと分離し、次入力は最新Navで判断。19実入力の46原画像比較で3/6の2pairだけ改善、旧nonUNKNOWN21は同一。未知評価/実機到達ではない。

## TEST074配布

code `5eff462fa0b53c01c3246c840b606ac8a8a9e02f`/[Mac118](https://github.com/shuhei0720/necrogold-automation/actions/runs/42934281012)成功。新view10/motion11/限定関係/selectorの実CI33件、限定Runtime Red1/Green6呼出、独立差分レビュー未解決P0/P1/P2なし。22seal/実compiler4C・5Swift・6RSP/全9Mach-O/全552build-source bytes・CRCを照合。Controller/Nav2変更・他20、Runtime/Perception/元閾値/API16cap14v15/ABI/wire/全予算/UNKNOWN無再送/R12原40/G1不変。

IPA0.3.4/build118、17,598,661bytes/SHA `24032b923fd1201e3b282ce815031791dfc9490f9fa1b3dc7b4526f6274cc5d3`。[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test074-build118/LoopCtrl.ipa)・[全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test074-build118/source.zip)・[SHA256SUMS](https://github.com/shuhei0720/necrogold-automation/releases/download/test074-build118/SHA256SUMS.txt)。最終source差分はstatus/検証/台帳の文書3件だけで製品bytes同一。公開後の匿名全取得/全SHAまで照合する。実ゲームCI・074実機の到達/毎拍/人超えは未受入。

## 必ず依頼する一連の実機テスト

通常1-1ポーズから、候補までrestart→金壁/通路候補へ接近→入店→全商品確認を一回としてまず2回。途中の歩数/開扉だけを完了にしない。SideStoreで新IPA更新→LoopCtrl完全終了/起動→Start Server、通常VPNを有効にする。

source.zipを展開し、フォルダ選択はtest_074.shがあるフォルダ。

```sh
mkdir -p /mnt/necro_test074
mount -t ios . /mnt/necro_test074
cd /mnt/necro_test074 && sh test_074.sh
```

短いrestartポーズ中はゲーム前面を維持し、ポーズが5秒以上続いたらiSHへ戻る。全画像/ZIP保存・照合の完了表示を待ち、自動`runtime/test-074-<run_id>.zip`を全回分と、実restart/候補接近/開扉/入店/全商品/停止位置/拍間隔を返してもらう。回収済み073の追加回収・再実行は不要。

同じiPhoneのみ、ユーザーはMacを持たず実機担当。実機主軸の局所反復・品質不変/固定時間なし、無関係な全Runtime/world累積なし。既知通路は毎拍、新地形の判断が必要な1〜2拍のみ許容。商品候補保持/全画像照合前の終了・次start禁止、raw/秘密値はGit外。初読3文書≤16KiB、[索引](context.md)から必要資料だけ読む。
