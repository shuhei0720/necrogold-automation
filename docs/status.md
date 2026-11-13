# 最新状態

更新: 2026-11-13（日本時間）。TEST096を実装中。095実機3回は途中停止2・商品可視後停止1。[今回計画](plans/test096-walk-cycle-repair.md)・[受領](reviews/test096.md)・[修正表](fix-records.md)。配布済みはTEST095 build168。**実機改善・受入は未確認**。過去の対策や単体合格を改善完了と扱わない。

## 変更

全商品登録の追加案を撤回。native mode2で「のろいのゆびわ」だけを探し、通常金商店の商品帯を完全に観測した対象なしだけ次周回へ進む。対象/候補/見切れ/故障は保持、宝箱開封・購入0。旧mode0/1・商品bank・canonical判定資産は保存。

094の候補146見逃しへ上左の有限仮説を追加。PARTIAL後の経路外DIRT変化を厳密な静止/同判断で確認し、未送信で退役した通路入力には旧STONE1個の限定静止証明を追加。UNKNOWN無再送・元期限・累積16入力/12restart/45秒walk/180秒sessionを維持。今回は最大4商店の有限試験。

## 検証と配布

code `288e1e7a470a7ac34e90813a763725c51408b07b`、run43409363287/build168。host205件/24scope、Macの実API/FS spool/Export6、旧Runtime14、新対象判定Runtime4と意味mutation2、実Cの5入力が成功。画素/時計/一部判定の注入を使う接続試験で、実ゲームやiPhone精度/速度ではない。36seal/6変更、実compiler・9Mach-O・旧判定15source/56,088B ELF・G1/R12全40・完全sourceを照合。CI167のfixture誤期待は記録し、製品条件を変えず訂正した。

[新IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test095-build168/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test095-build168/source.zip)。固定Release asset、hashは同ReleaseのSHA256SUMS.txt。新判定経路のためIPA更新が必要。

## 次の実機

IPA更新→LoopCtrl完全終了/起動→Start Server/通知許可/通常VPN。sourceを展開しtest_095.shのあるフォルダをiSHへ選ぶ。通常1-1ポーズから、候補までrestart→金壁/通路候補→商店→対象判定→対象なしなら次周回を確認する。途中の陰性PAUSEでは切り替えず、停止通知後にiSHへ戻り全画像/記録/ZIP照合の終了を待つ。表示されたruntime/test-095-<UUID>.zip全体を返却。入力UNKNOWN表示時は次回前にLoopCtrlを完全再起動する。

iPhone到達率/毎拍・人超え速度/未知対象精度/長期耐久は未受入。対応外layoutは保持。遅延positive通知P1・保持ledgerの自動整理なしP2は旧記録を維持。[索引](context.md)。
