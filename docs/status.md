# 最新状態

更新: 2026-11-13（日本時間）。TEST091開発中。基準c9e0870。[今回計画](plans/test091-device-stops.md)・[受領/検証](reviews/test091.md)・[修正記録](fix-records.md)。実機未確認を改善完了と扱わず、修正前に過去の同じ事象/原因を照合する。

## 実090の結果

実順c4109c61/3c04c7df/ec411d6f、3ZIP/60原PNGを全CRC/SHA/strict load/certificate/canonical sidecarへ照合、全回収完了。全商品確認0/3。

- 実1はLEFT初歩を送る前に0歩SCREEN停止。元174は候補、最初拒否175が未保持のため最終predicate未確定。後187を代用しない。
- 実2はUP1を確認できず8UNKNOWN。全旧STONE2/非共線DIRT17は保持されるが、旧左raw帯のrunner支持/blur競合差が不足。090のHUD喪失例とは別条件。
- 実3は木扉DOOR→FLOORの開通0変位を確認できず8UNKNOWN。2商品だけ見え、3商品は未確認。のろいのゆびわは人目で確認したが正式個別判定は未呼出。調整前の一回診断はno_complete_rowで、icon/name精度の合格ではない。

## 今回の限定対策

初歩は入力/移動/lead0の確実未送信票だけを撤回し、元12秒/既replan2回/全予算内で独立2枚から再取得する。拒否原画1枚はv2の余剰20番目pinへ追加し、既critical7/map12を削らない。

通路は全旧STONEを保持する別unit証明、開扉は独立blur絶対品質と既raw/detail/unique bracketの別zero証明を追加する。旧17段・既閾値/UNKNOWN無再送・入力窓・元期限を保持する。classifier/ELF/feature/authorityは変更しない。過去通路/開扉問題の適用外条件が継続しており、旧対策削除による回帰とは未確定。

## 試験・配布

変更部の単体/関連回帰、変更したRuntime保存境界の限定Mac試験、必要なIPA/source同一性照合を行う。全Runtime故障/旧全33群は通常反復の前提にしない。現段階は新IPA未配布で、TEST090 build150が直前配布版。新実装の検証/固定URLは確認後に更新する。

次の実機は新IPA更新/LoopCtrl完全再起動/Start Server/通常VPNから、通常1-1ポーズでrestart→金壁/通路候補→商店→全商品確認を一連に実施し、表示された全run別ZIPを返却する。090追加回収/同088再実行/稀な対象待ちの周回は不要。

## 未受入

実機到達率・毎拍/人超え・未知陽性精度・OS背景通知/対象なし循環は未受入。単体/校正/CIを実機成功にしない。候補保持/自動購入0/UNKNOWN無再送/全画像保存と旧API16/cap15/ABI/G1/R12を維持する。[索引](context.md)。
