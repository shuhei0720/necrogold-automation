# 実機テスト台帳

手順を用意しただけの試験は、実行済み・合格にしません。受領した資料から結果を追記し、再実行は別の実行として残します。元の失敗結果は上書きしません。

| ID | 目的 | 対象コード | 状態 | 結果 |
| --- | --- | --- | --- | --- |
| TEST-001 | ポーズ画面の取得、黒画像・寸法・遅延の切り分け | P1.1 / `1f78c4ba4f213e843b9b76503ccb7988c4be30ae` | 終了画面2実行に加え、ZIP内の3実行分のreportを受領・確認 | 全3回worker_failed。device_info開始記録あり、完了・ゲーム起動・画像取得の記録なし |
| TEST-002 | 子終了診断の追加とPython暗号での比較 | P1.2 / `cfcb70b61cea995e360eea0ad1378878a7f64c40` | report1件と終了画面を受領 | Python暗号でも最初のdevice_infoでSIGSYS(-31)、取得0/12、launch未到達 |
| TEST-003 | getitimer不使用版でゲーム起動・原画像取得 | P1.3 / `2ed85f29d65d81d249dfd780182ea2df989ddd01` | report1件と終了画面を受領 | timer_already_in_use、取得0/12、画像なし・launch未到達。worker終了0は成功ではない |
| TEST-004 | 専用workerのタイマー所有方式でゲーム起動・原画像取得 | P1.4 | 同一実行のZIPを2回受領、1実行として記録 | device_info・launch_app応答完了。取得0/12、1中断・11未実施、118888.205ms、session_deadline/SIGTERM。ユーザーはゲーム表示を報告 |
| TEST-005 | 同じP1.4でiSHを前面に維持して取得 | P1.4・コード変更なし | 手順準備・未実行 | 未判定。起動を省くため取得対象画面も変わる。原因を断定する試験ではない |

[TEST-001の手順と記録欄](001-capture.md)

[受領reportから抽出した数値と出典ハッシュ](test-001-results.json)。元ZIP・画像本体はチャット添付のまま保持する。

[TEST-002の比較手順](002-worker-diagnostics.md) / [実際のゲーム画面でのE2E計画](game-e2e.md)

[TEST-002の派生結果](test-002-results.json) / [TEST-003の派生結果](test-003-results.json) / [TEST-004の結果](004-owned-timer.md) / [TEST-004派生JSON](test-004-results.json) / [次のTEST-005](005-ish-foreground.md)

結果を受け取ったら、実行時刻、資料名とハッシュ、実際の端末条件、観察、条件別の予定/完了/失敗/中断/未実施、時間の中央値/p95、問題と次の対応を追記します。端末での操作はこのチャットから直接観測できないため、資料受領前に結果を補完しません。秘密の接続情報を含むファイルは保存しません。

