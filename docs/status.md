# 最新状態

更新: 2026-11-17（日本時間）。TEST108/build206を固定配布済み。[計画](plans/test108-real-failures.md)・[検証](reviews/test108.md)・[修正表](fix-records.md)。

TEST107の4固有run/97 PNG/107記録を照合し、開扉直後の入店一歩・未予約FULLの静止待機・単一看板の商品被覆・移動照合・未送信進路変更・原70の候補見逃しを修正。未知床や未観測商品を補完せず、元期限/予算と対象保持・UNKNOWN無再送を維持する。

CODE e8c4bb8の[CI206](https://github.com/shuhei0720/necrogold-automation/actions/runs/43935103938)は159件/22scopeが失敗・skipなし。同source IPA/全967 source・実compiler・5実物gate/5attemptを照合。独立レビュー未解決P0/P1/P2なし。[固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test108-build206)のIPA/完全source/hash表は匿名GET200・全hash一致。配布source595f5bbは閉じ文書3件だけ追加。

native C/Ring/Navの3件だけ変更、他33・API/cap/ABI・Runtime/Raster/Perception/features/canonical15/ELF/G1/R12は保持。旧RuntimeのMac191は歴史証跡。iPhone8/遠隔環境の開発は再開しない。

新IPA更新・LoopCtrl完全再起動/Start Server後、通常1-1ポーズから test_108.sh --until-target。候補探索→入店→全3商品確認→対象なし次周回を確認し、全照合終了後のcampaign ZIPを返却、全run原本を保持。新108の実機到達率・未知精度・毎拍/人超え速度・耐久は未受入。
