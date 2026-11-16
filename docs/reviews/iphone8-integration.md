# iPhone 8の同C診断・capture-only結線

2026-11-16（日本時間）。本番iPhone 11の既source/座標/閾値は変更しない。8だけの新規診断と独立overlayを確認した。実機資料・端末識別子・鍵・詳細ログはGit外。

新規`tools/iphone8_geometry.py`はG1画像専用の校正診断で、既Cの公開`ng2_analyze_rgba`だけを呼ぶ。実FOV・HUD・明示遮蔽に重なるセルをUNKNOWNへ落とし、公開CのUNKNOWNを部品呼出しで迂回しない。部分観測2セルのassert Redから実装し、新10件＋旧raster15件が成功。独立レビューでprovenanceからの資格上書きとUI遮蔽coverageの不足を修正し、再確認で残指摘なし。既22資産のhashは不変。

同じ校正資料でFLOOR/beat・PAUSEが成立した一方、footer負guard36画素、Restart表示、direct原JPEG/CoreGraphics位相、実motionの資格は未確定。全出力の`input_authorized`・`automation_ready`・`profile_qualified`はfalse。校正画像を未知評価へ流用しない。

capture-only overlayの8許可pathは、固定6e25＋旧G1/G2の実preimageとの差分だけを独立レビューした。HTTP pair403と閉route、暗号open後のtyped token出典、同process限定管理出典、初期化前の通常producer回避、全constructorの同mode/coordinator、App/test identity、所有listenerだけの異常停止処理を確認。配線7件＋listener1件は意味Red→8件Green。新applier31件、完全source packager4件も成功し、残P0/P1なし。

この時点のServiceは最小stubで、`service_status_runtime`の実Mac assertion Redを先に確認する。新Service実装のレビュー、全結線の実Swift/iOS compile、actual compiler argv/target/source/IPA/完全source二重封印、8のfresh-process原JPEG取得は未実施。Info値一致だけでcompiled flagを証明しない。通常workflow・TEST107配布・既定launcher・R12は変更しない。8の成功は11実機受入の代用ではなく、旧資料移送も未解決。
