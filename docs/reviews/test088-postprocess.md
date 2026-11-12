# TEST088: 保存後処理の負荷と進捗

2026-11-12（日本時間）。[計画](../plans/test088-postprocess.md)。基準20171ccecfb9bfcdac7b1dcc275f40fd8575faac。スクリーンショットの表示は同088の未出版run再開。test069.run→_publishのcertificate/prepareを同期実行し、完了まで次noticeがない。対象判定も全classify後にだけ結果表示する。再実行でsidecar作成前の処理は再計算される。実機の停止箇所/秒は未確認で、画像取得不良・deadlockと断定しない。

## 等価性能修正

実CPython3.9 profileの合成shop1枚はclassify3.60sのうち_icon3.475s（96.5%、profile overhead込み）。sample RGBのnested generator/zip/sliceをtuple sumへ置換し、各Python版のsum(float)挙動を保持。shapeを先に計算し、元評価順の最大matches/outline上界<=raw bestの場合だけ追加比較を省く。探索順・同率時最初のbox・丸め・shape/feature/閾値/schemaと_icon以外のAST不変。

有効Redは元互換結果の全field一致を先に確認後、候補配置ごとに定数上限を置くgenerator再開数の期待に違反（getstats集計8,597,172>20,808、環境失敗0）。時間閾値でGreenにせず、新2は実3.9で全Green。元outputの互換期待は認識精度の正解とは別。既target6を実3.9で最終1回/28.265秒全Green。原086実3の宣言済み校正309（PNG SHA11c471f849da6f7f670f74c8783566df758624c65edda61b961ab8f54faf467a）も1回、弱slot/boxを含む全field exact一致（target/中央.953305062/word1.0）。未知陽性・実iSH速度を証明しない。

作者freezeはGit外test088-target-performance/freeze.json。target SHA7dd5f16709f7f05f45029457a165fc1becad05f3b4745ce67f0d2f6da39101a4、新性能単体41398098a87cf03e3bd327a678a9a50a6ca3f46419e96c7e1ae0a6613f9da995。generator再開カウント0で、nativecompile/raw全scan/新依存0。

## 保存/進捗と取消

新進捗2methodsはpublic test088.mainの同run再開で、証明前・長い判定前/途中に通知する期待が元コードではAssertion Red（3subfailure、import/setup成功）。修正後は実3.9で進捗2＋旧回復3=5件/3.591秒全Green。実SIGINT/TERMの透過・handler復旧・元report/PNG/UUID保持・未完ZIP非公開・新device/session/RPC0を確認した。時間を模擬した進捗試験で、iSHの実時間試験ではない。

変更した出版hookの関連旧4（certificate→prepare、invalid native非判定、frozen sidecar/ZIP/receipt不変、既entryの3state表示）を開発Python3.12.14で1回/0.167秒全Green。実3.9のtarget6/性能2/進捗2/回復3の13件と合わせ計17methods。旧9を重ねてCIや全Mac/Cで再実行しない。元native/R12・core client/feature・088entry/shは不変。test069/test087は進捗のため変更したので元bytes不変へ数えない。

同088 label/spoolと正常出版を維持する。既sidecar/ZIPは変更しない。時限でunknownを作る/対象候補の破棄/別番号で未完runを飛ばす処理は追加しない。CPUの無駄と無表示を減らす変更であり、実機の滞留原因・速度/到達率の受入は次の実機で確認する。独立差分/実物と固定Releaseの結果は後続工程へ記録する。raw/profiler詳細はGit外。

## 同人の最終製品差分レビュー

TEST086以降と同じ独立担当が全製品差分/計画/作者証跡をread-only確認し、P0/P1/P2なしでGO。独立意味試験/compile再実行0、製品/試験/他文書への編集0。target7dd5f167/test069e2fe6fa1/test087369fb952、新性能41398098/進捗93b35686はfreezeと同一。targetは_icon以外の全定義/定数/importが元20171cceのASTと一致し、feature/schema/source選択は不変。

3chは直接+へ替えずtuple sumを残すため、3.9の左結合と3.12以降のsum挙動をそれぞれ維持する。shapeの元下限0、raw best・探索順/同率first box・最後の丸めを保持。上界は元評価順に最大matches=count/outline=len(dark)を代入した非負有限演算で、単純な.55/factor1へ丸めていない。upper<=raw bestの位置だけを省くため、その位置は元更新条件score>bestを満たさない。弱slotでは省略が少ない可能性があり、開発機profileを全入力/iSHの完了時間保証へ広げない。planのclamp表現は元下限0/上限1を追加しない旨へ訂正済み。

元全field一致後のgenerator再開数の有効Red、最終性能2Green・target6Greenの実ログ、原309全field一致を確認。新進捗の元3subfailure/最終進捗2+旧回復3Green、Python3.12の出版関連4Greenも確認し、計17件を重複再実行しない。原309は宣言済み校正、進捗clockは模擬であり、実機の秒や未知認識精度は未受入。

出版はcertificate前/prepare前の段階表示だけを追加。heartbeatは既取消チェックを1回そのまま呼んで結果を返し、未取消時のみ概ね5秒ごとのstdoutを追加する。新thread/タイムアウト/判定状態/画像優先/入力権限を追加せず、時刻をreport/sidecarへ入れない。同088の未出版runは元lock/loadから同UUID/原PNG/reportで先に保存し、未完を別番号のstartへ替えない。SIGINT/TERM・handler復旧・未完ZIP非公開・immutable再利用・新session/RPC0を選択した公開試験で確認している。

native/R12全40を含む119保存path（変更したtest069/test087は除外）と既088entry/shは元配布と全bytes一致。native/IPA新ビルド0、元148を再利用する。最初3文書16,152B/native契約12,277B・diffcheck PASS。source-only stage/公開前後の全677source・固定asset/actual tagの実物確認は以後に同人で行う。今回の滞留が必ずCPUだった、deadlockが解決した、歩行停止が直ったとは主張しない。
