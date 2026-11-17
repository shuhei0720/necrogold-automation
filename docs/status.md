# 最新状態

更新: 2026-11-17（日本時間）。TEST109/build208の実物照合まで完了。[計画](plans/test109-device-failures.md)・[検証](reviews/test109.md)・[修正表](fix-records.md)。

TEST108の3固有run/73 PNG/82記録を照合。開扉直後の端partial ROI、入店準備を撤回する遠方床変化、余分な価格/局所床照明差、原323の観測口見送りを修正。実採用原275は通常対象なし/C検査1、未選択276や未観測はUNKNOWNを保持。

CODE270773bの[CI208](https://github.com/shuhei0720/necrogold-automation/actions/runs/44002618293)は130件/19scopeが失敗・skipなし。同source IPA/全977 source・実compiler・5実物gate/5attemptを照合。独立レビュー未解決P0/P1/P2なし。[固定Release準備中](https://github.com/shuhei0720/necrogold-automation/releases/tag/test109-build208)。

native C/Ring/Nav3件だけ変更、他33とAPI/cap/ABI・Runtime/Raster/Perception/features/canonical15/ELF/G1/R12は保持。旧Runtime/Mac191は歴史証跡。iPhone8/遠隔開発は再開しない。

メインiPhone11で新IPA更新・LoopCtrl完全再起動/Start Server後、通常1-1ポーズからtest_109.sh --until-target。入店→全3商品確認→対象なし次周回を確認し、全照合後のcampaign ZIPを返却、全run原本保持。522後の同prefix実画像は未収録。109の実機到達率・未知精度・毎拍/人超え速度・耐久は未受入。
