# P1.4 / BUG-P1-003: 専用workerで期限タイマーを所有する

## 1. 概要
TEST-003はP1.3でtimer_already_in_useとなり、device_infoのHTTP送信より前に停止した。setitimer戻り値を使用中判定/復元へ使う設計を廃止し、専用workerに明示的な所有オブジェクトを設ける。

## 2. 背景
受領reportはpython暗号、取得0/12、device_info error、worker終了0・signalなし。ユーザーの操作やLoopCtrlの不具合とは判定しない。iSH公式util/timer.c（blob 63b19a99a95bad228b64d9950b2a30323c4bcb99）はtimer_newでend/intervalを初期化せず、timer_setはactive状態によらずend-nowとintervalを旧値として返す。解除後も次の旧残秒が負になり得る。実機の戻り値そのものは記録していないため、端末値を推測で埋めない。

初回だけの初期化、負値の丸め、使用中チェックだけの削除では解決契約が曖昧なため採用しない。広範なHTTP/暗号の書換えを伴うタイマー非依存化と比較し、今回は子プロセスの既存分離を利用する。

## 3. 詳細設計
- OwnedRpcTimerは専用workerのmain threadで明示的に生成/開始する。Clientへ必須注入し、所有者なしではタイマー/HTTP前にtimer_owner_requiredで拒否。汎用Clientから暗黙に既存タイマーを取得しない。
- 同一プロセスの所有者は1個、RPCも1個。同じ所有者の再開/ネスト/別PID/別threadの利用はOSタイマーを触る前に拒否する。所有者のPython状態だけで使用中を判定する。
- worker生存期間でSIGALRM handlerを1つ設置。setitimerの戻り値は初期解除/arm/disarm/closeすべてで無視し、未知の旧タイマー値を復元しない。初期化時、外部のcallable/不明handlerがあれば触る前に拒否する。SIG_DFL/SIG_IGNは専用workerでのみ所有可能とする。
- 所有は新規Popen child内だけで行う。iSH kernel/fork.cのtgroup_copyもitimer=NULLにする。親や他プロセスのタイマーは変更しない。一般の他用途タイマーを共用・保存するAPIではない。
- 各RPCは単調時計の絶対期限とactive状態を保持。handlerはactiveなしの通知を無視する。期限前は、旧RPCの通知か現在のone-shotの早期発火か区別できないため残り単調時計時間で再armする（旧値は無視、失敗時poison+固定エラー）。期限到達時だけrpc_deadline。処理終了時にも期限を検査して、signal未配送での遅い成功を拒否する。
- RPC終了ではactiveを先に解除してからdisarm。worker所有終了ではdisarmとSIG_IGN化で遅延通知がSIG_DFL終了を起こさないようにする。旧handlerをRPCごとに戻さない。所有者終了後の再利用は禁止。
- setup/cleanup失敗はpoisoned状態と固定エラーコードにして後続RPCを禁止。deadline自身から伝播する例外を明示的に管理し、呼出し元の外側except状態を誤参照しない。元の例外/KeyboardInterruptがあるときはそれを保ち、cleanup_errorを別の固定値で記録する。初期化途中のKeyboardInterruptも所有をcloseして元理由を保つ。例外本文・旧タイマーの未初期化値は出力しない。
- 親の全セッション期限・TERM→KILL、許可RPC、暗号、無加工保存、UIなし/入力なしは維持。timer_initializeのcheckpointとtimer診断（方式/poison/cleanup_error）をreportに保存する。

## 4. 影響範囲
期限処理を専用moduleに分離し、protocol.Client/workerの接続を更新する。既存の汎用タイマー復元テストは契約変更として置換し、P1.3コード/結果はGit履歴と旧ログに保存。R12は変更しない。

## 5. 新規・更新テスト
- 旧戻り値が毎回負値、巨大正値、周期あり、不正値でも、所有者での認証RPCと連続captureが通る。getitimerは禁止、SIGSYS注入も継続。
- 明示所有者なし/未開始/終了済/poison/別PID/thread/二重owner/ネストの拒否、外部handler非変更。
- 未活動・期限前のSIGALRM、RPC間のpending SIGALRMを実子プロセスで確認。期限到達/遅い復号後の成功拒否。slow header/bodyと合算期限を回帰。
- arm/disarm/close/handler設定失敗、cleanup前失敗、KeyboardInterruptとcleanup失敗同時で元理由保持・固定診断・後続HTTP0件。
- workerを含む親子＋実ローカルHTTP模擬試験で起動1回→12取得→画像原バイト→完了reportを確認。単なるClient呼出しのmock成功で代用しない。

## 6. 実装順
独立調査/設計/安全レビュー→期待値を固定しRed→小さな実装→Green/回帰→独立実装レビュー最大3周→GitHub保存と完全ZIP→TEST-004。先に実機合格を宣言しない。

## 7. コミット前確認
全unittest、Python3.9構文、R12全40ファイルhash、配布ZIPの全ソース照合、変更ファイルGitHub hash照合。TEST-003は不合格として台帳へ追記、TEST-004は未実行。

## 8. スコープ外
ゲーム内タップ、操作サイト、自動周回、購入、背景設定変更、ホスト試験を実ゲームE2E扱いすること。修正後にゲームが実際に開くか、画像が有効かは端末で確認する。
