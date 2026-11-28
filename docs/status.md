# 最新状態

更新: 2026-11-28（日本時間）。現在は[TEST125起動準備修正1](plans/test125-startup-preparation.md)、client CODEc55192e。[検証](reviews/test125-startup-preparation.md)・[実行手順](device-tests/README.md#test125起動準備修正1)。[固定source](https://github.com/shuhei0720/necrogold-automation/releases/tag/test125-startup-fix1)公開済み。SOURCE48cc1be、1282blob/全byte・匿名全GET照合PASS。

実診断HTTP200/通知authorized・保存scan pendingを一律通知エラーにするclientを修正。元開始期限内のpending待ち・原因別表示、新14＋直接19合格/独立レビュー閉鎖。実機改善・別時点のserver停止原因は未確認。

IPAは既存TEST125/build278（CODEc18db303/SHA97a7c054）のまま。native/元期限/予算/UNKNOWN無再送は維持、新IPAは作らない。LoopCtrlを再起動せず元記録を保つ。次版もこのclient修正を継承する。
