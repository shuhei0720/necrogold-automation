# 最新状態

2026-11-16（日本時間）。[全体引き継ぎ](handover-2026-11-16.md)。旧私有資料は未移送。

接続: [VPN/SSH](plans/windows-ssh-tailscale.md)受入済み。[iPhone8環境](plans/iphone8-device-lab.md)はNetwork/DDI/原寸capture成功、診断37件成功。WireGuard＋EMProxyで疎通。SideStoreのxctest失敗を検査済IPAの直接導入で回避し、LoopCtrl/XCTest/暗号RPC成功。8の限定リスタート4回を確認。USB・native入力/商品到達は未受入。

本番はiPhone11、8は検証専用。11の既存座標/画面処理を保護し、8は別profile。11への接続・導入は行っていない。

最新要件: 新規リセマラ/実機検証はゲーム停止・確認→起動→スタート→ホームのオールゾーン階段→通常1-1。Game Centerは初回だけ。[START-03](requirements/necrogold.md)は未実装。旧ポーズ/回復互換を保つ。

現配布はTEST107/build204。[計画](plans/test107-partial-composition.md)・[レビュー](reviews/test107.md)・[修正表](fix-records.md)。TEST106の複合変化/初歩前フェードを修正し、既知MOVED拒否を維持。

cfdb690のCI204は52件/12scopeがskipなしで成功。IPA/全source955files・compiler5gate/5attempt照合、P0/P1なし。固定Release・校正・配布aeee520の来歴は[レビュー](reviews/test107.md)。

保護native/ABI/cap/feature/canonical15/ELF/G1/R12・旧予算/候補保持/UNKNOWN無再送は不変。全E2E未実施。

旧TEST107入口はLoopCtrl再起動/Start Server後の1-1ポーズ。新規入口START-03は未実装。全照合後のZIP/原本を保持。商品到達・未知精度・毎拍/人超え速度・耐久は未受入。
