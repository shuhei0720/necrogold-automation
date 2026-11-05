# BUG-P1-003: timer_already_in_useの根拠と検証限界

確認日: 2026-11-05（日本時間）。対象P1.3からP1.4への修正。

## 実機で観測した事実

[TEST-003派生記録](../device-tests/test-003-results.json)に原資料のSHA-256と数値を記録した。P1.3/python暗号、device_infoがtimer_already_in_use、12試行すべて未実施、画像0、launch_app未到達。worker終了0/signalなしは捕捉した失敗のreport保存を示す。OSタイマーの実際の戻り値やiSHビルドは記録されていない。

## 公式ソースの確認

GitHub connectorで取得したiSH公式ソース。以下はソース上の契約の確認で、ユーザー端末のsyscall traceではない。

| 出典 | 取得blob SHA | 確認内容 |
| --- | --- | --- |
| [util/timer.c](https://github.com/ish-app/ish/blob/master/util/timer.c) | `63b19a99a95bad228b64d9950b2a30323c4bcb99` | timer_newはmalloc後にactive等を設定するがend/intervalを初期化しない。timer_setはactiveの確認なしでend-nowとintervalをoldspecへ返す。解除後の旧残秒も負になり得る |
| [kernel/time.c](https://github.com/ish-app/ish/blob/master/kernel/time.c) | `d46c8d5f86566258ccb0204e7fe615c9e3de3a22` | sys_setitimerの旧値返却は上記timer_setを通る |
| [kernel/fork.c](https://github.com/ish-app/ish/blob/master/kernel/fork.c) | `d5869fc1cda872a89044452547b7f2f6901356c1` | tgroup_copyは新しいプロセス側のitimerをNULLにする |

P1.3は旧値が(0,0)でないと使用中と判定し復元した。非活動や未初期化の値でも停止できるため、使用中の証拠として利用できない。TEST-003の失敗と整合する実装上の欠陥だが、端末で返った数値まで特定したとは言わない。

## Red → Greenと設計変更

実装前に実setitimerを実行してから、比較・展開・真偽判定すると例外になる旧値を返す故障を注入した。P1.3の連続取得試験は旧値比較で失敗（[Redログ](p1-owned-timer-red.txt)）。修正後は専用workerのOwnedRpcTimerをClientへ明示的に渡し、旧値の取得・判定・復元を全廃する。SIGALRM handlerをRPC間でも保持し、単調時計の期限で発火を判定する。早期通知では残り期限で再armする。iSH util/timer.cがCLOCK_REALTIMEを使うため、早期にone-shotが消費された場合も期限を失わないようにした。

負の旧値、巨大な正値/周期値、NaN/Infinity、読み取り禁止オブジェクトを注入して、認証済みローカルHTTPで起動要求1回→画像12回→原バイト保存を試験。getitimerを呼ぶとSIGSYSになる子プロセスでも確認する。実親子workerを通した試験も含む。遅延SIGALRM、初期化/arm/disarm/close失敗、cleanup失敗とKeyboardInterruptの同時発生、親の全体期限とTERM→KILLを別途検証する。

汎用プロセスの外部タイマーを保存・復元するAPIではない。同じworkerの二重所有、同時RPC、別PID/thread、閉じた所有者、故障後の再利用を拒否する。worker終了時はSIG_IGNとして、遅延signalでreport保存中に終了しないようにする。

レビューで早期発火・cleanup例外判定・初期化途中の中断を追加指摘。4個の失敗を先に確認（[追加Redログ](p1-owned-timer-review-red.txt)）し、再arm、局所的な例外状態管理、初期化中断時のcloseへ修正した。

## 言える範囲

ホストのLinux/Python3.12での故障注入・模擬通信経路の検証。Python3.9は構文検査のみ。iSH本体、実LoopCtrl、実ゲーム画面、入力の反映、新鮮さ、実機速度は未確認。現在の目的はTEST-004の起動/取得経路を確認できる状態へ直すことであり、自動周回の完成を示さない。
