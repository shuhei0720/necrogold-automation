# TEST-011 読取専用の入力方式診断レビュー

2026-11-05（日本時間）。対象は[P1入力方式の計画](../plans/p1-input-path.md)。TEST-010で画像比率を確認した後、ゲームの続行対象がAX参照として取れるかを実機で調べる新しい変更単位。入力APIは追加しない。

## ②③ 計画・テスト網羅の独立レビュー

作成履歴を渡さず、計画・AGENTS・現行コード・固定取得元だけをfresh-contextの3担当へ渡した。1周目の指摘を計画へ反映。

| 担当 | 主な指摘 | 反映 |
| --- | --- | --- |
| test011_plan_design | capability名をgeometry値と混同しない、alternatives1件でも曖昧、全ツリーの一意性を保証しない | screenshot_image_geometry_v1完全一致、候補の報告有無に判定を限定 |
| test011_plan_tests | 後画像/保存の完了前に候補確認しない、専用report再読込、型/回数/保存失敗のRed | 完了判定を最終段階、fixed schema、全失敗後RPC0を契約へ追加 |
| test011_plan_security | 親SIGTERMの子終了経路、全RPCの固定params、応答/例外/再読込whitelist、画像取得後前面確認 | 親停止handler、strict allowlist、後確認後のみ画像保存 |

P0なし。独立reviewは端末試験の代わりではない。元のcapture/Client/R12を変更しない。

## ④⑤ 実装とテスト

新規モジュール、起動sh、36ホスト試験と専用fixtureを追加。P1.5既存runtime8ファイルはSHA-256一致を確認し変更していない。

- [実装前の挙動Red](../validation/p1-input-path-behavior-red.txt): 正常RPC列/失敗後停止の期待assert計10失敗。import失敗だけをTDDの証拠にしない。
- [1周目指摘Red](../validation/p1-input-path-review1-red.txt) / [Green](../validation/p1-input-path-review1-green.txt): AX矛盾と暗画像での候補確定を検出。
- [旧監視への隔離mutation Red](../validation/p1-input-path-spawn-mutation-red.txt): 生成直後SIGINT/SIGTERMの子残存を検出。
- [2周目指摘Red](../validation/p1-input-path-review2-red.txt) / [Green](../validation/p1-input-path-review2-green.txt): cleanup故障と輝度矛盾を検出。
- [新規36試験Green](../validation/p1-input-path-new-tests-round2.txt)。既存131件との最終全回帰は後段の最終記録を参照。

初回全回帰は既存deadline試験1件が復号開始前の期限切れで失敗した。[初回ログ](../validation/p1-input-path-tests.txt)と[単独再実行成功](../validation/p1-input-path-existing-timer-rerun.txt)を残す。既存コード・期待値は変更していない。

## ⑥ 実装の独立レビュー

1周目のfresh-context設計・試験・安全レビューを実施。

- 巨大整数の有限判定でOverflowError。実装担当の自己点検と設計担当が再現し、範囲判定を先に行う修正を適用。
- AXのvisibility=partial/offscreenかつhittable=trueの矛盾を親再読込で受理していた。Redで再現し、受信時と同じ整合条件で拒否へ変更。
- 主担当追加: 前後画像が暗画像でも候補を確認し得た。Red→非黒の両画像を候補確定の必要条件へ変更。
- 親SIGTERMがPopen直後に入ると子が残る窓を設計/試験担当が独立再現。既存superviseを変更せず、新しい診断側の停止フラグと生成〜回収の保護へ変更する。
- 停止後のRPC数テストが固定ファイルの比較だった。各RPCで共有ログを更新し、実際の増分を検査する。

2周目は固定SHAを指定し、3担当とも1周目の指摘解消を確認した。設計はfocused10件、試験はfocused15件、安全は新規32件を実行し成功。

安全担当が終了処理自体の故障を追加注入し、terminate/killのOSErrorやkill後waitのTimeoutExpiredで固定終了結果を残せない問題を検出。生例外には合成command値が含まれた（実秘密の漏洩を確認した意味ではない）。terminate失敗後もkill/期限付き回収へ進み、終了未確認を固定コードで記録する修正へ戻った。親専用parent-result.jsonへ最終結果を保存し、未終了の子が親の停止結果を上書きしないようにする。第3周で最終確認する。

spawn境界の初回Redは独立レビュー3担当が実子の残存を再現した。実装担当の初回ログはツール打切りで空だったため証跡に数えない。修正後に旧監視へ戻す隔離mutationでSIGINT/SIGTERMの2試験が失敗したログは、追加の回帰証拠として記録する。

## ⑦⑧

端末TEST-011は未実施。完成配布物と正確な試験手順を人間レビューへ提示する。候補参照の確認はゲーム再開/入力取消/速度/P1の合格ではない。人間レビュー後に必要な整理だけを行う。


## 第3周の最終レビュー

対象input_path.py SHA-256 `473952bb19389f8e12d4a20f92d91a5f9808b5e7f1e818d1bbac72c658dbb213`、test_input_path.py `b74a08c73a328b0916b4dd851577a830b41049d395d1c8e8c7e1eaf02dc55691`を固定。

- 設計担当: 変更設計とRed/Greenを確認し追加指摘なし。
- 安全担当: 関連11試験成功。terminate/kill/wait故障をmain経由で独立再現し、固定結果・kill試行・任意文字列非出力を確認。P0/P1追加なし。
- 試験担当: cleanup/luma等の変更にP0/P1なし。限定10件中、新deadline試験だけ段階到達前に期限終了して失敗。単独再実行成功し、find中のsession_deadline/SIGKILL/exit_confirmed=trueを確認。

残P2: `input_path_driver.py`の期限試験は起動を含む2秒に依存するため、負荷次第で対象RPCへの到達を検証する前に終了し得る。成功時は対象段階への到達と停止を検証しており、今回失敗を成功扱いしていない。開始通知との同期によるfixture改善は未実施。第4周の独立レビューは行わない。

ホスト検証はiSH/実ゲーム結果の代わりではない。端末の取得、AX参照、停止はTEST-011の未実施範囲。端末側の入力期限/取消は今回実装しておらず、ゲーム内入力のない読取診断である。


## 3周後の主担当による試験fixtureの修正

最終全回帰で既存の200ms試験が再び復号前に期限となった。主担当はruntimeを変えず、この1試験を仮想単調時計と明示的なタイマー通知へ変更した。暗号/HTTP/復号の各80msを進め、総200msで3段階目が中断する期待は維持した。実SIGALRM配送とHTTP中断は既存の実時間試験で検査する。[fixture Green](../validation/p1-input-path-timer-fixture-green.txt)。各段階で200msを再設定する故障を隔離コピーへ入れると期待例外が消え、[mutation Red](../validation/p1-input-path-timer-fixture-mutation-red.txt)で失敗することも確認した。成功するまで単純再実行した結果とは区別する。

その後の全回帰では、既存stop fixtureのmarkerが空の瞬間に読まれる競合を観測した。[失敗ログ](../validation/p1-input-path-marker-race-red.txt)。旧/新両fixtureでSIGTERM無視の設定を先に行い、markerの全文を一時ファイルへ書いてからrenameで公開する方式へ修正した。観測する停止の期待値やruntimeには変更なし。第4周の独立レビューは行わず、変更後の全回帰で確認する。


## 最終全回帰

fixture修正後の`python3 -m unittest discover -s tests -v`は**167/167成功（56.656秒）**。[全ログ](../validation/p1-input-path-all-green.txt) / [最終結果・ソースhash](../validation/p1-input-path-host-tests.json)。新規36件を含む。`sh -n test_011.sh`成功、既存runtime8ファイルとR12 treeは未変更。実機TEST-011は未実施。
