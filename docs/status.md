# 最新状態

更新: 2026-11-11（日本時間）。TEST077の2run/38原画を受領、全商品可視1/2を原画像で確認。[TEST078計画](plans/test078-closed-gate-motion.md)は独立レビューGO、新8単体・独立レビュー残0・限定CI25件・新IPA build126の実物照合を完了。[検証](reviews/test078.md)。078実機未受入。

## 実機の根拠と修正対象

実順92742894→587d35cc。1は7restart/5MOVED/7入力/1開扉、原372に3商品75/125/65が可視。入力間隔.510〜.532秒、実ゲームの受付時刻・恒久毎拍達成とは区別。2は7restart/6MOVED/7入力/開扉0。最後のUP395→419で実1歩進んだがUNKNOWN8評価でMOVEMENT停止。閉金扉と両脇金が2セル先から1セル先へ厳密対応し、次NavはUP/DOOR。入力は元10ms窓内、最終画像確認もvisualD残約1.953秒で期限超過ではない。

旧gate補助は最新さらに次がFLOORである条件と、画像の独立2領域の不足で不成立。旧条件を削らず、閉金扉2ahead→adjacentのUNKNOWN限定unit証明を追加する。旧全GOLD/閉扉/法線の一意対応・raw全73/元gap・実origin/元next床・商品/保護を維持し、新しい固定3依存feature（frameごとH→Vの最初の有効軸）とcamera中央52の独立2帯を使う。旧5依存案は全UI排除後250で不採用。新しい単一仕様は支持322/bad5/upper150/lower172、72競合は支持300未満。95%/300/2帯100/全73の元15pp規則は維持する。

全2ZIP/38PNGのSHA/CRC/schema/manifest/prefix/cursor/実publicationは一致し両PAUSE/完収。2の初期PNG1に対応するcapture行だけ256行ringから欠落、画像自体は検証済みで行を補完しない。取得failure/timeout0、host status33回エラー/取消0/max1.407秒。別cmd21 too_lateと最終停止を混同しない。

## 配布と次の実機

code `954c6f39725a6b593566fa214e8cc5faa159fc6b`、[CI build126](https://github.com/shuhei0720/necrogold-automation/actions/runs/42992892650)。新8/関連14/selector3=25件failure/error/skip0。freshG1/22seal Nav1他21・actual4C/5Swift/6RSP・Runtime070 Red1/現6call・全9MachO141marker/新C11不在・全576source bytes/CRCを実5verifier各1回で照合。全Runtime/world積み増しなし。

[TEST078/build126](https://github.com/shuhei0720/necrogold-automation/releases/tag/test078-build126)の固定[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test078-build126/LoopCtrl.ipa)・[全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test078-build126/source.zip)。IPA0.3.4/build126、17,608,587B/SHA `8daf50aa751a8e09f8ebe079292557943fa5fc7de29f15fbe8ea391cbc6dde95`。最終文書3件だけで製品を維持し、返却前に固定3assetの匿名全GET/SHA/CRCを照合する。
新IPA更新→LoopCtrl完全終了/起動→Start Server、通常VPN。展開した全sourceのtest_078.shを含むフォルダを選択し、iSHで実行する。

```sh
mkdir -p /mnt/necro_test078
mount -t ios . /mnt/necro_test078
cd /mnt/necro_test078 && sh test_078.sh
```

新しい通常1-1ポーズ→候補までrestart→金壁/通路候補→商店→全商品確認をまず2回依頼する。短いrestartポーズはゲーム前面、5秒以上ならiSHへ戻り全画像/ZIP保存照合完了を待つ。runtime/test-078-<run_id>.zip全回分と全商品/停止位置/拍間隔を依頼。077の追加回収/再実行は不要。到達率・毎拍・人超えは新実機で評価する。

同じiPhoneのみ、ユーザーはMacなしで実機担当。実機主軸/品質維持/時間上限なし。raw/Scene/秘密値はGit外、[索引](context.md)から必要範囲を読む。
