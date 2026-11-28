# TEST125修正1後の起動未到達・接続拒否

2026-11-28（日本時間）。受領JSON246B/SHA256 `e5a39b425438121c3eb7d3d35265c50cb6b8708287422b6e09d232ae22a72641` は私的領域に原本と受領receiptを保存した。ファイル名のUTC保存stampは01:55:49、同日JST10:55:49。これはserver停止時刻の証明ではない。

利用者の画面には修正1のbanner・保存確認中表示・cycle_recovery_scan_pendingがある。待機/誤分類修正は適用されているが、ゲーム開始には未到達。後続JSONはphase=schema、connection_error、errno111/refused/connect、HTTP statusなし、samplesなし。既存HttpTransportの接続先は127.0.0.1:8300で、GET /schemaの接続時点で拒否された。pairing読取・認証prepareより前なので、今回の通知/scan状態は取得できていない。

利用者は現在の表示を一度Runningと回答した後、「すとっぷど」と訂正した。最新回答Stoppedを採用する。RunnerStatusはHTTP200+JSON以外/例外を全てStoppedに分類するため、表示だけでprocess終了を断定しない。今回のTCP refusedと合わせても、終了原因・Wi-Fi/VPN原因・scan負荷との因果は未確定。前回HTTP200のscan pending診断と同じRuntimeだったことも未収録である。

保存scanはserial queue上でunpublished探索を行い、正常returnでready、Swift throwでfailedとなる。scanからserver.stop/exitへ進む直接経路は確認できない。peer metadata反復読込/同時保持・画像hashは負荷候補だが、実peak/所要時間/OS終了記録なしにOOMやdeadlockを原因と確定しない。既存の待機延長・通知再設定・記録削除だけでは解決と扱わない。

固定上流6e25cf6の読取確認: OptionsViewのSettings→Diagnostics→App Logsはディスク上の全.logを列挙する。日次runnerのloopctrl-2026-11-28.logと今回のloopctrl-app-…pid….logを各個開き、右上共有→Shareで回収でき、Stoppedでもserver RPCは不要。Runner Logs画面は稼働中RPCが必要なので今回の回収には指定しない。

次に今回の起動失敗と同じ時刻帯の保存2種ログを照合し、Server failed/NWListener cancelled、明示Stop、listener went down、XCTest tearDown、前面/背面・終了記録を探す。旧受領ログは今回の時刻帯を覆わない。末尾途切れだけで死因を決めず、必要時にOSの終了/Jetsam記録へ進む。

新しい製品コード・IPA・試験は作成していない。既存33件の成功を実機改善へ置換せず、修正1の実機受入は未完了とする。独立担当2名が接続/ログUIとscan経路を読取確認し、どちらも端末停止原因は未確定とした。原本JSON・ログ・個人情報はGitへ保存しない。
