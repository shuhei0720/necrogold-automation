# 最新状態

新環境への移行は[全体引き継ぎ](handover-2026-11-16.md)。私有資料の移送完了とは区別する。

更新: 2026-11-16（日本時間）。TEST106の4実行/5商店遭遇の停止を修正し、TEST107/build204の実物照合まで完了。[計画](plans/test107-partial-composition.md)・[受領/検証](reviews/test107.md)・[修正表](fix-records.md)。

実1/2/4後半の正常PARTIAL後ROUTE10は、上端商品投影と既地形関係を分離・合成して修正。新ITEM/上端dataは一用再判定へ。実3の初歩前フェード固定は元D内の最新2画像から再取得し、既知MOVEDはsticky拒否。実4前半は原記録で正常完全陰性→実RESTART ACK15→新floor225まで成立を確認した。

CODE cfdb690の[CI204](https://github.com/shuhei0720/necrogold-automation/actions/runs/43732679433)は52件/12scopeが失敗・skipなしで成功。同source IPA/完全source955files、実compiler等5gate/5attemptを照合済み。独立レビューは未解決P0/P1なし。原3pairの役割と再判定原184/440も校正。[TEST107/build204固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test107-build204)を公開済み。IPA/source/SHAの匿名GET200・全bytes/hash・tagを照合した。公開CI205成功、配布sourceはaeee520でCODEとの差はdocs3filesだけ。

Cだけ変更し、他35 native/公開ABI/cap/既feature/canonical15/ELF/G1/R12・元予算/対象保持/UNKNOWN無再送を維持。無関係な全Runtime/合成world/実ゲームE2Eは未実施。

次の実機は新IPA更新・LoopCtrl完全再起動/Start Server後、通常1-1ポーズから test_107.sh --until-target。候補探索→入店→全3商品確認→対象なし次周回を確認する。全照合終了後のcampaign ZIPを返却し、全run原本を保持。実機到達率・未知精度・毎拍/人超え速度・耐久は未受入。
