# TEST125修正1後の起動未到達・接続拒否

2026-11-28（日本時間）。受領JSON246B/SHA256 `e5a39b425438121c3eb7d3d35265c50cb6b8708287422b6e09d232ae22a72641` は私的領域に原本と受領receiptを保存した。ファイル名のUTC保存stampは01:55:49、同日JST10:55:49。これはserver停止時刻の証明ではない。

利用者の画面には修正1のbanner・保存確認中表示・cycle_recovery_scan_pendingがある。待機/誤分類修正は適用されているが、ゲーム開始には未到達。後続JSONはphase=schema、connection_error、errno111/refused/connect、HTTP statusなし、samplesなし。既存HttpTransportの接続先は127.0.0.1:8300で、GET /schemaの接続時点で拒否された。pairing読取・認証prepareより前なので、今回の通知/scan状態は取得できていない。

利用者は現在の表示を一度Runningと回答した後、「すとっぷど」と訂正した。最新回答Stoppedを採用する。RunnerStatusはHTTP200+JSON以外/例外を全てStoppedに分類するため、表示だけでprocess終了を断定しない。今回のTCP refusedと合わせても、終了原因・Wi-Fi/VPN原因・scan負荷との因果は未確定。前回HTTP200のscan pending診断と同じRuntimeだったことも未収録である。

保存scanはserial queue上でunpublished探索を行い、正常returnでready、Swift throwでfailedとなる。scanからserver.stop/exitへ進む直接経路は確認できない。peer metadata反復読込/同時保持・画像hashは負荷候補だが、実peak/所要時間/OS終了記録なしにOOMやdeadlockを原因と確定しない。既存の待機延長・通知再設定・記録削除だけでは解決と扱わない。

固定上流6e25cf6の読取確認: OptionsViewのSettings→Diagnostics→App Logsはディスク上の全.logを列挙する。日次runnerのloopctrl-2026-11-28.logと今回のloopctrl-app-…pid….logを各個開き、右上共有→Shareで回収でき、Stoppedでもserver RPCは不要。Runner Logs画面は稼働中RPCが必要なので今回の回収には指定しない。

次に今回の起動失敗と同じ時刻帯の保存2種ログを照合し、Server failed/NWListener cancelled、明示Stop、listener went down、XCTest tearDown、前面/背面・終了記録を探す。旧受領ログは今回の時刻帯を覆わない。末尾途切れだけで死因を決めず、必要時にOSの終了/Jetsam記録へ進む。

新しい製品コード・IPA・試験は作成していない。既存33件の成功を実機改善へ置換せず、修正1の実機受入は未完了とする。独立担当2名が接続/ログUIとscan経路を読取確認し、どちらも端末停止原因は未確定とした。原本JSON・ログ・個人情報はGitへ保存しない。


## 同時刻の保存3ログ受領

2026-11-28。新日次ログ290行/18,869B/SHA `60757794d5df4293c7e408e11eba75377b6d8ec77649a3ad045cdb8edb66f16d` は旧224行の全bytesをprefixとして保持し、09:22と10:47の起動66行を追加している。app pid11645は680B/SHA `6e07c97f928271247843a8fc197de3d5df9df902016bb9af07320396373ae4f0`、pid11848は520B/SHA `62c847517d30b9f4bde9bab3ba7c5efe48d7d2d0a20eb19661dbe585391b3108`。原本3件とreceiptはGit外に保持した。同じ事象の追加証拠であり、新しい実機run件数には加算しない。

日次ログは10:47:23.671 listener ready/23.677 bootstrap OK、通知許可・local network granted。10:47:24.891背景→25.192既存の一度だけのbringback→25.544前面復帰→27.234背景で終わる。bringbackはbootstrap完了1.5秒後の既存fallbackで、25秒の再open成功を記録している。後の背景化をこの関数が起こしたと結び付ける証拠はない。明示Stop/Server failed/NWListener cancelled/listener went down/tearDown/exit/signalの記録は無い。

app pid11645は10:47:15起動、guardは23.648に解除。pid11848は10:57:56の別process起動でbootstrap記録なし。DDI先network probe200は内部serverの到達証明ではない。10:55:49の拒否と合わせても、前processの終了理由・正確な終了時刻、scan負荷/OOM・Wi-Fi原因は未確定。

次はOS側の終了記録を確認する。iPhone「設定→プライバシーとセキュリティ→解析と改善→解析データ」で同日10:47〜10:58のLoopCtrl…/JetsamEvent…を確認・共有する。Apple一次資料は[端末上のcrash/memory log取得](https://developer.apple.com/documentation/xcode/acquiring-crash-reports-and-diagnostic-logs#Locate-crash-reports-and-memory-logs-on-the-device)と[日本語設定名](https://www.apple.com/legal/privacy/data/ja/device-analytics/)。該当記録が無くても再起動/再試験/解析共有ONを形式的に要求しない。製品・試験・IPA変更0のまま、改善未受入を維持する。


scan開始時刻の限定: NG2Runtime.sharedは遅延singletonで、server callback登録はclosureを置くだけ。最初の認証RPCのlease検査で初期化され得る。通常fix1のschema確認にはtrial_support RPCが含まれ、その前後でscanが始まるため、10:47のserver readyから10:51の画面までの数分をscan時間と数えない。init自体は存在確認とasync dispatchで、同期queue待ちは無い。prepareは開始関数を呼ぶが同じsingletonでは一度だけであり、同processのlistener stop/startだけではsingletonを作り直さない。新processでのLoopCtrl再起動とlistener再起動を区別する。
