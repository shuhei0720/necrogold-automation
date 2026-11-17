# 最新状態

更新: 2026-11-18（日本時間）。TEST113を修正中。対象はメインiPhone11の通常1-1、のろいのゆびわ。[計画](plans/test113-device-failures.md)・[修正表](fix-records.md)・[検証](reviews/test113.md)。

TEST112の9回/18ZIP、216PNG/243記録を照合。5/9回目は正常完全陰性・実リスタート・新床ポーズ・継続許可まで成立。client取消意図で継続せず、終了途中drainingの応答拒否を再現した。商品UNKNOWN3件と歩行停止4件も原因別に解析した。

clientの終了待ちと取消時のエラー保持を修正、新8＋関連114件が実Python3.9で成功。C/Navの商品18件・歩行20件と独立レビューを保存。最終C1df5/Navfd172の36nativeを固定し、変更2/保持34を照合。閾値・元予算・候補保持・UNKNOWN無再送は維持、実機改善は未確認。

最新配布は[TEST112/build228](https://github.com/shuhei0720/necrogold-automation/releases/tag/test112-build228)。113のnative/実Mac/IPA/配布確認は未完了。G1/R12/既feature/ELFを保持し、遠隔開発は再開しない。
