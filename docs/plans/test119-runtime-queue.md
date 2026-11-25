# TEST119: entered-current の実 Runtime queue 境界

## 目的・対象

`entered-small-plan`の新しい late-unit/DATA bind は、後続framingを所有する `cycle_full_source` と job/capture/start/prefix を変える。C公開lifecycleだけでは、Runtimeが同じ新規画像を保持・queueし、旧workerのproducer/commit両return後にそのRGBAを普通のRingへ渡すことを検査できない。Runtime本体が不変でも、この新しいC↔Runtimeの組合せは今回確認する。

新Mac選択caseは **`entered_current_queue` の1件、normal/candidateの短い2subrun**。全world/全fault集合・TEST118物理520msモデル3caseの再実行はしない。未来MOVE/実RS/次childは公開Cの別lifecycleに分離する。新caseは現在CでのGreenを対象にし、旧Mac Redを追加しない。

## setupと薄い境界

HOST専用extensionをstaged Runtime末尾へ追加する既TEST101方式を使う。元 `NG2Runtime.swift` のbody全bytes/SHA `58c6de6535dbe204e0e9ae39958a5e4c0edfc80a92a428e5b29cb0843d44a420` は保持し、製品ファイルを編集しない。公開Cのconstructor/observe/tick/begin/completeで通常ACKまでをearnedする。前奏も全て公開手続きRGBA→通常PerceptionのSceneを使い、Cのprivate field・状態dump・結果oracleで対象late-entered/token/DATA状態を作らない。これは対象boundary前のscenario setupであり、実hardware ACKや全起動の試験ではない。earlyFULL以降は通常Runtime pipelineを通す。

前奏の各RGBAは通常Perceptionを通し、公開Cへ観測したものと同じData/ID/start/end/prefix/generationのimmutable Frameとして保存する。通常ACKまでのearned Controllerをcomponent setupに使い、Runtime bookkeepingはその同じ公開status/cycle/実入力履歴から整合させる。対象tokenやkernel結果をprepared coreへ注入してはならない。adapterが初期化するRuntimeの `prefix/captureID/acceptedStarted` とcycle companionは、その公開status/cycle・前奏の実入力履歴に一致させる。snapshotを捏造しない。owner/foreground/lockは既fakesの宣言条件。capture thread/UIを起動しないcomponentとして開始し、存在しないworkerのreturnを模擬しない。新しいframeは通常 `cycle(run)` のobserve/evidence更新へ渡し、new `cycle.frames` を直接注入しない。

このsetupは既harnessがそのまま提供する実機開始APIではなく、TEST101のHOST限定private-extension方式で組む新しいcomponent seamである。公開Cで前奏をearnedし、画像のC呼出とRuntime登録を同一データへ結合する点が診断用101のfabricated Scene/snapshotとは異なる。実前面取得/撮影backend/物理拍/全起動の新受入とはしない。

## caseのassert

1. Runtime自身の `serviceCycleAssessment` が元pendingの同sourceをleaseし、通常Ring(mode2/fast1・`classificationResult=nil`)を実行する。job/capture/start/prefix/level/元PとRGBA hashを前奏の公開状態へ結ぶ。
2. old正常UNKNOWNと両returnのdrain後、normal単位変位のlate-unit/current FLOOR画像を通常Cへ渡し、一回だけ元ACKへcreditする。新DATA sourceが旧sourceと異なり、元P/hold/owner/level・DATA2を保持することを確認する。
3. newDATA workerがpending中に独立したremoteGOLDの次frameを通常observeする。古いimmutable job/sourceは結果前に差し替えず、未発行framing/MOVE/RSは0。old producer/commit-return tokenが残る間は後続worker開始0。
4. **normal**: 同sourceの通常UNKNOWNをCが採用し、両return後に新queued frameを新workerへ渡す。新workerのRGBA/Scene/ID/start/prefixが確実にその新frameであり、通常Ring/C adoptionが成立することを確認する。後続framingのepisode/未発行leaseは新classified sourceに結び、旧sourceや元IDを再使用しない。未来のMOVE送信は必須にしない。
5. **candidate**: 同じ短前奏のpending sourceから普通のRingが候補/対象を返す。queued material frameよりその候補を優先し、元job/sourceの候補保持、後続worker/framing/MOVE/RSなしを確認する。候補は実pixel featureから出し、resultを注入しない。
6. 両subrunを公開cancel/stopで終了し、実classification queue→control queueの両closure return/token解除、leaseと全実workerのdrainを確認する。存在しないcapture threadを試験したとは書かない。結果・実subrun数・未実施を別記する。

## 時計と実費

前奏・capture/HUD/ACKの時刻は宣言した手続きモデルとし、実機178..180の再現や端末速度の受入にしない。可能なら前奏を同一monotonic時計の直近過去の手続きscenarioとしてearnedし、対象boundary以降はoffsetなしの実時計で全C/Perception/Ring・軽量ordering hook待機を元期限へ自然に課金する。virtual clockが必要ならRing内部のnow callbackを含む同一時計へ全実wall費用を一度だけ課金する。元source150ms/worker100ms/P/visual・元inclusive条件を変更せず、期限超過を成功へ書換えない。fixtureのclock後退、正画像差替、forcedNEG、既worker結果の偽装は禁止。

return順序は短い有界latchと同呼出/小さなPOD状態で確認する。deadline中の全文RPC・PNG復元・長いparkを避ける。observer負荷で失敗した時は原失敗を残し、guardや時刻を緩めずfixtureだけを切り分ける。

## 保存・レビュー・実装順

`check_runtime119.py`・`ngg2_runtime119_tests.swift`・必要な `ngg2_runtime119_queue_fixture.c` だけを新author対象とし、root以外はCI/commitを実行しない。独立planレビューP0なし→source preparation→独立diffレビュー→rootの選択Mac実行。Linuxで実Swiftが不可ならprepareのみを完了し、未実行を明記する。

proofはactual compiler argv/source/object/link hash、元Runtime bodyとHOST suffixの別hash、case/subrun/原source metadata/worker入場/D/P/通常Ring結果/実採用/return token/drainを結ぶ。既reader5gateの準備へこの1caseのsource・実記録bindingを加える。旧Runtime fault/Spoolは同bytesの歴史証跡として再利用し、新実行とは数えない。
