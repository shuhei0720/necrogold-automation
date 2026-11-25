# 最新状態

更新: 2026-11-25（日本時間）。TEST119/build266の修正・実IPA照合済み。[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test119-build266/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test119-build266/source.zip)。固定公開の匿名取得確認は別途追記する。[今回計画](plans/test119-device-failures.md)・[検証](reviews/test119.md)・[修正表](fix-records.md)。

TEST118実機9ZIPの通路判断変更、PARTIAL入口、価格縦断片/低い配置、松明床、遅延入店/新DATA所有と実周回の処理順を修正。3fの実陰性→RS→child継承と成功判定packetを保持。初回RSと`--until-target`を維持。

製品CODE617fc248、CI266/run45534392534。関連host130・実Python3.9の53・Mac1case/2subrunが合格。実compiler/profile3・37native（4変更/33保持）・全ソース・9MachO等の6照合も合格。Macは手続き画像のcomponent確認であり、iPhone到達/毎拍・人超え速度/精度は未受入。通常1-1ポーズから新版で一連を試験し、終了後`runtime/test-119*.zip`を全返却してもらう。
