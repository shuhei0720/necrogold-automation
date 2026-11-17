# 最新状態

更新: 2026-11-17（日本時間）。TEST109の修正・作者試験・独立レビュー済み、CI配布準備中。[計画](plans/test109-device-failures.md)・[検証](reviews/test109.md)・[修正表](fix-records.md)。

6添付を3固有run/73 PNG/82記録へ照合。開扉後FULLのpotential ROI拒否、PARTIALの遠方床変化による再分類反復、3商品可視時の余計な価格/端床検出を分けて修正する。原323の候補見送りも確認。見逃し番号は未記載で利用者指定との一致は未確定。

基準7fe34ff、旧[TEST108検証](reviews/test108.md)・[配布](https://github.com/shuhei0720/necrogold-automation/releases/tag/test108-build206)は保存。108の159件/22scope・IPA/完全source照合はソフト確認であり、今回の実機失敗を改善済みと扱わない。109の新CI/IPA/固定配布は未実施。

元期限/予算・観測床・対象候補保持・未観測不陰性・UNKNOWN無再送を維持。private実機資料はGit外、API/cap/ABI・Runtime/Raster/Perception/features/canonical15/ELF/G1/R12は今回scope外。iPhone8/遠隔開発は再開しない。

次は原因ごとのRed→最小Green/直接関連・独立差分レビュー・同source IPA照合後、通常1-1ポーズからtest_109.sh --until-target。全照合後のcampaign ZIPを受領し、全run原本を保持する。主指標は実機の商品確認到達率/対象なし次周回。109の実機到達率・未知精度・毎拍/人超え速度・耐久は未受入。
