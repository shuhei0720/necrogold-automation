# 最新状態

更新: 2026-11-11（日本時間）。TEST077の2run/38原画を受領、全商品可視1/2を原画像で確認。[TEST078計画](plans/test078-closed-gate-motion.md)は独立レビューGO、新8単体とNav局所修正を凍結し、最終レビュー・限定CI25件/新IPAを準備中。[検証](reviews/test078.md)。078実機未受入。

## 実機の根拠と修正対象

実順92742894→587d35cc。1は7restart/5MOVED/7入力/1開扉、原372に3商品75/125/65が可視。入力間隔.510〜.532秒、実ゲームの受付時刻・恒久毎拍達成とは区別。2は7restart/6MOVED/7入力/開扉0。最後のUP395→419で実1歩進んだがUNKNOWN8評価でMOVEMENT停止。閉金扉と両脇金が2セル先から1セル先へ厳密対応し、次NavはUP/DOOR。入力は元10ms窓内、最終画像確認もvisualD残約1.953秒で期限超過ではない。

旧gate補助は最新さらに次がFLOORである条件と、画像の独立2領域の不足で不成立。旧条件を削らず、閉金扉2ahead→adjacentのUNKNOWN限定unit証明を追加する。旧全GOLD/閉扉/法線の一意対応・raw全73/元gap・実origin/元next床・商品/保護を維持し、新しい固定3依存feature（frameごとH→Vの最初の有効軸）とcamera中央52の独立2帯を使う。旧5依存案は全UI排除後250で不採用。新しい単一仕様は支持322/bad5/upper150/lower172、72競合は支持300未満。95%/300/2帯100/全73の元15pp規則は維持する。

全2ZIP/38PNGのSHA/CRC/schema/manifest/prefix/cursor/実publicationは一致し両PAUSE/完収。2の初期PNG1に対応するcapture行だけ256行ringから欠落、画像自体は検証済みで行を補完しない。取得failure/timeout0、host status33回エラー/取消0/max1.407秒。別cmd21 too_lateと最終停止を混同しない。

## 配布と次の実機

現行[TEST077/build124](https://github.com/shuhei0720/necrogold-automation/releases/tag/test077-build124)、codef1ddc786/closing63ca426。077の33CI/5実物verifier/全571source/固定3asset匿名全GET照合済。078はbaseline63ca426、Nav1/他21・Controller/Runtime/JSON/API16cap14v15/ABI/G1/R12/閾値/元予算を維持する通常局所修正。新単体Red→Green/関連回帰・独立差分レビュー・IPA/固定配布の実物照合後に返す。全Runtime/worldは追加しない。

新IPA更新→LoopCtrl完全終了/起動→Start Server、通常VPN。展開sourceのtest_078.shから新しい通常1-1ポーズ→候補までrestart→金壁/通路候補→商店→全商品確認をまず2回依頼する。短いrestartポーズはゲーム前面、5秒以上ならiSHへ戻り全画像/ZIP保存照合完了を待つ。runtime/test-078-<run_id>.zip全回分と全商品/停止位置/拍間隔を依頼。077の追加回収/再実行は不要。到達率・毎拍・人超えは新実機で評価する。

同じiPhoneのみ、ユーザーはMacなしで実機担当。実機主軸/品質維持/時間上限なし。raw/Scene/秘密値はGit外、[索引](context.md)から必要範囲を読む。
