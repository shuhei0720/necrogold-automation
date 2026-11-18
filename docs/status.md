# 最新状態

更新: 2026-11-18（日本時間）。TEST115の実機結果を受領しTEST116を開発中。[全体計画](plans/test116-device-failures.md)・[商店](plans/test116-shop-continuation.md)・[連続化](plans/test116-continuous-campaign.md)・[修正表](fix-records.md)。メインiPhone11・通常1-1・のろいのゆびわが対象。

7ZIP/3campaign/4固有run、96PNG/110記録を全照合。1周0084・2周e0b8→134e・3周36b6。e0b8は正常完全陰性45.157ms→実RS→新床まで成功し、旧予算handoffの意図的PAUSE/回収待ちで次UUIDまで84.306秒。残3runは開扉後に停止し実機不合格。

原因はcredit後の現在PARTIAL移行漏れ、逆top投影、早期FULL時の元ACK確認境界。capture25は観測床の口の両脇が暗く既形状外。限定修正と、最新指示に従う端末内保存/新UUIDの無PAUSE連続化を設計・検証する。旧対策の合格を改善完了にしない。

基準は[TEST115/build237](https://github.com/shuhei0720/necrogold-automation/releases/tag/test115-build237)、CODE1028137/source4765027、seal766070e1。IPA SHA107e3db9・実物照合/固定公開の詳細は[115検証](reviews/test115.md)。TEST116のIPA・実機改善・速度はまだ未確認。
