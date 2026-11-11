# 最新状態

更新: 2026-11-11（日本時間）。TEST074の3run/54原画を受領し、静止UNKNOWN・実UP未確認・iSH status JSONの2秒超過を修正。TEST075/build120の限定CI・実IPA照合完了、実機未受入。[計画](plans/test075-motion-rpc.md)・[根拠/検証](reviews/test075.md)。

## 今回の根拠と変更

実順46efced0→0372e82b→1834cdeb、全商品可視0/3。3ZIP/54PNGのhash/CRC/manifest/prefix/cursor/report/strict schemaと全回収を確認。1は金発見後の次未送信LEFTが静止UNKNOWN、2は3入力目の実UP後も8評価UNKNOWN、3は6restart後の金可視で初歩公開窓前にhostが取消。取得/dispatch failureは全null、保持省略を補わない。回収済み074の追加回収・再実行は不要。

Navは既知結果/旧proof/閾値を維持し、UNKNOWNへ金/局所不変の強zeroと、金なし完全旧L・左右raw位相・full21既知blur面の厳密unitを追加。原20評価で変化は56→57 BLOCKEDと73→83/85/86 MOVEDだけ。全73のzero特徴cacheは1,898比較で中間数値不一致0、最終static5/motion10 Green。限定Linux経路はreferenceなし5.487→3.455ms、あり8.071→6.709ms。実iPhoneの速度保証とは区別する。

JSONはvalidation.pyの逐字scan/全tree再walkを省き、depth16/nodes10000/size/UTF8/duplicate/nonfinite/error優先/RPC2秒を維持。新5/関連5Green、10,222差分で返値/error一致。59KB status形のPython work64.8%減/Linux1.85倍、実iSHは未確認。独立差分レビューとcache追加確認で残P0/P1/P2なし。API16cap14v15/ABI/元予算/UNKNOWN無再送/商品優先/G1/R12原40を維持。

## 配布と検証

[TEST075/build120](https://github.com/shuhei0720/necrogold-automation/releases/tag/test075-build120)、code `445929566f34268eca6a70356667abce4844de02`。IPA0.3.4/build120、17,604,425bytes/SHA `8d1c8b6e6891948bb4739c097284ef8e3501fe0232ec4a1d7ac34e9f1eb3a064`。[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test075-build120/LoopCtrl.ipa)・[全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test075-build120/source.zip)。固定assetを匿名全GETしSHA/CRCを照合して返す。

標準public Ubuntu/Macの限定CI43件はfail/error/skip0。実compiler4C/5Swift/6RSP、22seal中Nav1変更/他21不変、実TEST070の意味的Red1/現Runtime6call、全9MachO/133fixture marker無混入を実5verifier各1回で確認。code全source ZIPの559 tracked bytes/CRC一致。最終sourceは閉じる文書3件のみ変更し製品bytesを維持、全Runtime/world累積は行わない。

## 次の実機

新IPAをSideStoreで更新→LoopCtrl完全終了/起動→Start Server、通常VPN。新しい通常1-1ポーズから候補までrestart→金壁/通路候補→接近/入店→全商品確認を一連としてまず2回。展開sourceのtest_075.shがあるフォルダをiSHでmountして実行する。短いrestartポーズ中はゲーム前面、ポーズが5秒以上続いたらiSHへ戻り全画像/ZIP保存照合完了を待つ。自動runtime/test-075-<run_id>.zip全回分と全商品/停止位置/拍間隔を依頼する。実機の商品到達/毎拍・人超えは未受入。

同じiPhoneのみ、ユーザーはMacを持たず実機担当。実機主軸・品質不変/固定時間なし、既知通路は毎拍、新地形の判断が必要な1〜2拍のみ許容。raw/秘密値はGit外、初読3文書≤16KiB、[索引](context.md)から必要な資料を選ぶ。
