# 最新状態

更新: 2026-11-15（日本時間）。TEST105の実機停止3件・候補見逃し2件を修正し、TEST106/build202の実物照合まで完了。[計画](plans/test106-real-failures.md)・[受領/検証](reviews/test106.md)・[修正表](fix-records.md)。

実1は商品判定前の開扉後地形関係、実2は先行policy7の閉容器価格/背景識別、実3は最上段ITEM投影の追加が停止原因。見逃し62/72は左側の既知床vantageを追加。原253は正常完全陰性50.040403msとC採用を確認したが、校正であり実機改善完了ではない。

CODE c18427fの[CI202](https://github.com/shuhei0720/necrogold-automation/actions/runs/43719819990)は156件/24scope成功。同source IPAと完全source947filesを照合し、実物5gate/6attemptが成功。private検査helperの変数上書き1件は独立確認して修正、成功gateを再利用した。[TEST106/build202固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test106-build202)の公開・匿名GETは次工程。

変更nativeはC/Ring/Navの3つ。他33/Core ABI/Perception/Runtime/Wire・既feature/canonical15/ELF/G1/R12・元期限/予算・対象/候補保持・UNKNOWN無再送を維持。無関係な全Runtime/合成world・実ゲームE2Eは未実施。

次の実機は新IPAへ更新・LoopCtrl完全再起動/Start Server後、通常1-1ポーズから test_106.sh --until-target。候補探索→入店→下側を含む3商品確認→対象なし次周回を確認する。全画像/ZIP照合後の表示campaign ZIPを返却し全run原本を保持。実機到達率・未知精度・毎拍/人超え速度・耐久は未受入。
