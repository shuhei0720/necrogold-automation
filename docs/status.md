# 最新状態

更新: 2026-11-26（日本時間）。TEST121実機8ZIP/4root/96PNGを照合し、[TEST122の4原因修正](plans/test122-device-failures.md)・単体/直接関連・独立差分レビューを完了。実機は全商品可視2/4・商品後RS0/2のまま。通路ACK後unit、価格独立21/4、V2初回観測、FULL halo DATAを修正し旧成功5packetを保持。[検証](reviews/test122.md)。37nativeの5変更32保持を封印、実IPA/CIと実機改善は未確認。

前回配布は[TEST121/build270](https://github.com/shuhei0720/necrogold-automation/releases/tag/test121-build270)。CODE4574786/CI270、host88・実Py39 75・実IPAの5確認が合格。37nativeは5変更32保持、API/native_v15/POD/profile3を維持。

[検証](reviews/test121.md)・[計画](plans/test121-device-failures.md)。TEST120実機7ZIP/4run/99PNGを照合し、扉前の壁色差による取消、看板分断/床支持/暖色文字の商品UNKNOWN、capture1左上候補を修正。旧成功5packetと初回RS/連続周回を保持。269画像のNav差は指摘1件だけ。

IPA SHA671bb82f。SOURCEd2fae5c/全1215blob・同native、固定3assetの匿名全GET/全bytes/SHA/CRC/実tagを確認済み。IPA更新→LoopCtrl完全終了/起動→Start Server/通常VPN。通常1-1ポーズから `sh test_121.sh --until-target`。終了表示後の全run/campaign ZIPを返却してもらう。実機到達・毎拍/速度の受入は未完了。
