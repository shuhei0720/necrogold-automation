# 最新状態

更新: 2026-11-17（日本時間）。[TEST110/build217](https://github.com/shuhei0720/necrogold-automation/releases/tag/test110-build217)を固定配布済み。[検証](reviews/test110.md)・[修正表](fix-records.md)。

TEST109の8添付=4固有run/98 PNG/108記録。ACK比較前のgold UNKNOWN拒否、FULLの商品画像待ち、対角DOOR→GOLDによる入店拒否、SHOP表示と重なるpause iconを修正。Ring閾値は維持。原250は未変更Ringで完全陰性/C検査1。

新profileの敵/死亡再試行は、正の証拠・各intent/outcome・保存/実drain・UNKNOWN無再送を実装。Mac214のdurable後の公開回数更新漏れも修正。215/216の誤fixtureは資格拒否として保存し、原本不変・凍結回収・実PNG照合を確認した。

CODE cdff284/run44044340448/build217でnative173+selector7、実Python3.9の108件、Mac Runtime29、Spool productionと2故障感度検査が成功。IPA18,184,294 bytes/SHA677ce1d1、CODE完全source1000filesを照合。実物5gate/5attempt成功。native36/変更10・保持26、seal f4551161、G1/R12/Ring/Nav/feature/ELF保持。

publisher218/run44047487420成功。IPA/完全source/hash表を匿名GET200・全bytes/SHA一致まで確認。メインiPhone11の通常1-1ポーズから test_110.sh --until-target で実機へ返す。110の実機の商品確認到達率、対象外の次周回、敵/死亡、未知精度・毎拍/人超え速度・耐久は未受入。[旧109](https://github.com/shuhei0720/necrogold-automation/releases/tag/test109-build208)を保存。iPhone8/遠隔開発は再開しない。
