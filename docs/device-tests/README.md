# 実機テスト台帳

最新: [TEST-009](009-source-info.md)の結果受領済み。実機API1.98.14/build2026-11-01 16:49。次は[取得元の寸法修正](../plans/p1-source-geometry.md)のCI検証。追加の端末操作は現在不要。

手順を用意しただけの試験は、実行済み・合格にしません。受領した資料から結果を追記し、再実行は別の実行として残します。元の失敗結果は上書きしません。

| ID | 目的 | 対象コード | 状態 | 結果 |
| --- | --- | --- | --- | --- |
| TEST-001 | ポーズ画面の取得、黒画像・寸法・遅延の切り分け | P1.1 / `1f78c4ba4f213e843b9b76503ccb7988c4be30ae` | 終了画面2実行に加え、ZIP内の3実行分のreportを受領・確認 | 全3回worker_failed。device_info開始記録あり、完了・ゲーム起動・画像取得の記録なし |
| TEST-002 | 子終了診断の追加とPython暗号での比較 | P1.2 / `cfcb70b61cea995e360eea0ad1378878a7f64c40` | report1件と終了画面を受領 | Python暗号でも最初のdevice_infoでSIGSYS(-31)、取得0/12、launch未到達 |
| TEST-003 | getitimer不使用版でゲーム起動・原画像取得 | P1.3 / `2ed85f29d65d81d249dfd780182ea2df989ddd01` | report1件と終了画面を受領 | timer_already_in_use、取得0/12、画像なし・launch未到達。worker終了0は成功ではない |
| TEST-004 | 専用workerのタイマー所有方式でゲーム起動・原画像取得 | P1.4 | 同一実行のZIPを2回受領、1実行として記録 | device_info・launch_app応答完了。取得0/12、1中断・11未実施、118888.205ms、session_deadline/SIGTERM。ユーザーはゲーム表示を報告 |
| TEST-005 | 同じP1.4でiSHを前面に維持して取得 | P1.4・コード変更なし | reportと原画像3枚、終了画面を受領 | 11/12非黒取得、1中断、45115.262ms、session_deadline/SIGTERM。保存3枚で今回のiSH表示を確認。P1全体は未合格 |
| TEST-006 | 一時的な継続処理付きでゲーム取得 | P1.4・診断コード変更なし | report・原画像3枚・終了画面を受領 | 12/12非黒取得、32908.814ms、completed/子終了0。保存3枚全てゲームのポーズ。座標・鮮度・取消は未確認 |
| TEST-007 | 同じゲーム取得条件で既存ネイティブ復号を比較 | P1.4・診断コード変更なし | report・原画像3枚・終了画面を受領 | native_i386、12/12非黒、26274.969ms、completed/子終了0。保存3枚はゲームのポーズ。同一画像バイトでも復号時間短縮を確認 |
| TEST-008 | 通常スクリーンショットで表示形状の基準を確認 | 新しい実機コマンド実行なし | IMG_8531.png受領・オフライン比較済み | 標準1792×828、API414×896/828×1792。同方向の文字配置に縦横別の縮尺差を確認。入力座標・鮮度・原因確定は未完了 |
| TEST-009 | 横長取得修正に必要な実機版/build/対応機能の特定 | P1.4と新規の単体補助 | 端末出力IMG_8533.png受領 | API1.98.14/build2026-11-01 16:49、native_i386、video_stream/stream_ticket申告。画像取得・ゲーム操作なし |

[TEST-001の手順と記録欄](001-capture.md)

[受領reportから抽出した数値と出典ハッシュ](test-001-results.json)。元ZIP・画像本体はチャット添付のまま保持する。

[TEST-002の比較手順](002-worker-diagnostics.md) / [実際のゲーム画面でのE2E計画](game-e2e.md)

[TEST-002の派生結果](test-002-results.json) / [TEST-003の派生結果](test-003-results.json) / [TEST-004の結果](004-owned-timer.md) / [TEST-004派生JSON](test-004-results.json) / [TEST-005の結果](005-ish-foreground.md) / [TEST-005派生JSON](test-005-results.json) / [TEST-006の結果](006-game-keepalive.md) / [TEST-006派生JSON](test-006-results.json) / [TEST-007の結果](007-native-crypto.md) / [TEST-007派生JSON](test-007-results.json) / [TEST-008の結果](008-display-reference.md) / [TEST-008派生JSON](test-008-results.json) / [次の改修計画](../plans/p1-geometry-validation.md)

結果を受け取ったら、実行時刻、資料名とハッシュ、実際の端末条件、観察、条件別の予定/完了/失敗/中断/未実施、時間の中央値/p95、問題と次の対応を追記します。端末での操作はこのチャットから直接観測できないため、資料受領前に結果を補完しません。秘密の接続情報を含むファイルは保存しません。



## 次の端末試験: TEST-010

[取得元の横長出力](010-source-landscape.md)。LoopCtrl NG-G1とP1.5を組み合わせ、SideStore更新後に原画像寸法・比率・時間を測る。未実施。TEST-009の結果受領は完了している。
