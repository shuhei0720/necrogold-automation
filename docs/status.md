# 最新状態

更新: 2026-11-18（日本時間）。TEST113/build230の固定公開・匿名取得の照合が完了。メインiPhone11・通常1-1・のろいのゆびわが対象。[計画](plans/test113-device-failures.md)・[修正表](fix-records.md)・[検証](reviews/test113.md)。

TEST112の18ZIP/9run、216PNG/243記録を照合。商品再確認・上端HUDの観測位置、歩行停止4条件、終了途中応答の読取待機を修正。元5/9回目の正常判定と実リスタートを比較基準にした。最初の実client例外は未保存で、全取消の発火源を確定済みとはしない。

CODE a565681、CI230/run44154202349でhost150（native142＋selector8）、実Python3.9の122件、現Mac2ケースが成功。実公開status2件・Spool2件/48合成PNG→実3.9を照合。5実物gateは5attemptで全成功し、再試験・再compileなし。

36nativeはC/Navの2変更・34保持、Runtime/Ring/HUD/閾値・G1/R12/feature/ELF・元予算を維持。CODE完全source1053filesを照合済み。固定配布は[TEST113/build230](https://github.com/shuhei0720/necrogold-automation/releases/tag/test113-build230)。配布source8c96c77はCODEからdocs3件だけの更新。IPA/完全source/hash表は匿名GET200・全bytes/SHA一致。実機改善は未確認。
