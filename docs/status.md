# 最新状態

更新: 2026-11-13（日本時間）。TEST094を実装中、未配布・実機未確認。[計画](plans/test094-native-goods-cycle.md)・[通路修正](plans/test094-shadow-passage.md)・[修正表](fix-records.md)。単体合格や過去の対策を実機改善完了と扱わない。

## 093受領と094の変更

093の3ZIP/60PNGを全CRC/SHA・strict schema・certificate・sidecar・登録集合へ照合済み。実順4de4→ee2a→70cd。商品可視2回、restart上限1回。原326はコンパス/スピア/あかるいトーチ、原151はトーチ/ブラストヘルム/閉じた宝箱。旧個別判定は2回とも実施済みだが対象なし確定経路はなかった。見逃し156は上左の壁に沿う通路で、観測床3歩の接近候補を追加しUNKNOWNを床へ塗り替えない。

094は専用cap/profileで、同じiPhoneのRGBAから直接指輪を判定し、証明済み対象外だけPAUSE→耐久intent→RESTART→新floor確認へ戻す。画像回収/iSH判定を各周回へ挟まない。最新指示どおり宝箱は開けず対象外。候補/対象/未判定/故障は保持・自動購入0。16方向入力/12restart/45秒walk/180秒sessionは累積し、4商店までの有限試験とする。

## 検証状態

新C/回収単体・独立差分レビューを進行中。開発hostの実画像4件は分類11〜44ms、実対象の保持を確認したがiPhone速度ではない。原225の元画像で完全coverageの条件成立、原326/151はlayout不足の未判定を維持。有限bank外の品や未知配置の精度は未受入。Swift/Mac実callback・IPA実build・実物/完全source照合はこれから実行する。現在の配布物は093のまま。

[前版IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test093-build159/LoopCtrl.ipa)・[前版全コード](https://github.com/shuhei0720/necrogold-automation/releases/download/test093-build159/source.zip)。code7e6b9ba、run43362104103/build159の来歴は[093記録](reviews/test093.md)。094完成として使わない。

## 次の実機

094の新IPA/完全sourceを固定Releaseへ検証・公開してから依頼する。通常1-1ポーズから一回開始し、候補までrestart→金壁/通路候補→商店→個別判定→証明済み対象外なら次周回、を同じnative sessionで確認する。終了後に全画像・全記録・ZIP照合と出版ACKを完了し、表示ZIP全体を返却してもらう。回収済み093の再回収や稀な対象待ち周回は不要。[索引](context.md)。
