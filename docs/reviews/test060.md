# TEST060 レビュー・検証

2026-11-09（日本時間）。[計画](../plans/test060-continuous-admission.md)・[長経路の期待](../tests/test060-world-cases.md)。原059のUP3/商品未達を受け、連続新ordinalの初回authorityを作る時刻と画像を修正する。実機受入ではない。

## 受領と因果

原ZIP SHA `900b06ffcaecb973a3c97a9b794702ac031cdc5f40437558ee19844e434dce0b`、active/current report SHA `9079fe8f191308fb2cfccb3fffa7dbbb8fe9903c91bad92663cc60fa9504eecd`。別0入力geometry runと、UP3のd411を区別。後者はSCREEN17/PAUSE/drainedで、4th MOVE source54→55のmotion UNKNOWNが直接原因。画像には共通1rawpxの地形ずれがあり、照明だけ/厳密静止とは呼ばない。最新の床経路・gold/protectedは同じだが、既存motion score.478>.45は正当にUNKNOWN。次入力窓は成立しobserve後もDに67.049ms残るので059の空窓やlateではない。[受領台帳](../device-tests/README.md#test059受領結果2026-11-09-日本時間)。

14完成PNGのbytes/SHA/CRC、O0/strictO2/Pillow全Scene・15pairs/all73scoreが一致。60.part/59未回収を完全16枚と扱わない。原2run ZIPのstrict評価はinvalid/unknown/exit2、商品未達を評価器の合格へ変えない。原画像/ZIP/report/解析はGit外。

## 計画のfresh独立レビュー

第1周: 安全clear、設計P1は100/150ms案が通常L80ms・capturegap5ms・AX約11msでも位相によって判断が元Dに達して失敗する反例。網羅P1は長経路worldの拍連続性・固定遅延・停止位置の期待未固定。第2周でsource200msをL85+cadence90+prep20+margin5から導き、公開C全1ms位相と160終端world、遅いcapture/prepで第4未送信停止を固定した。3担当とも残P0/P1/P2なし。実IPC20msや全実機条件の成功保証ではない。

長経路はworld入口5歩・4床→開扉→進入の6入力。単純距離5のDOWNは金壁がHUDに隠れ不成立だったため、新caseの±2金壁列を手前2セルへ延長する地形へ固定。既存world16は無変更。実装前studyで四方向×木鉄/Q7の初期候補、全6操作Nav/Motion/商品をO0/strictO2で確認。左右の最終goods Sceneは商品保護がoriginへ及びentered_gate.valid=0だが、world位置gateとgoodsの期待を満たす。入口validを全ケースへ強要しない。

## TDD・実装（進行中）

旧Controller165件は33.596秒/skip0でGreen。新公開C2methodは旧Cのまま指定assertion Red（2failure/errors0）を確認。publication100ms、source_start200msを未予約の連続新ordinalだけに適用する最小変更と、既存helperのpositive合成時刻setupを実装中。元PNG/reportの時刻を新captureとして偽装せず、guard/期限/再予約/fallbackの旧assertを保持する。全回帰・新C故障2・新world160/停止2・実装fresh3レビュー・Mac/実compiler/IPA・全sourceの検証は未完了。

新IPAを実ビルド・照合した後、TEST060の実機試験を必ず依頼する。iPhone入店/商品到達・毎拍・人より速い性能・指輪/周回/耐久は未受入。回収済059は再実行しない。


## 実装第1周の追加指摘

設計/網羅の静的第1周は追加なし、安全P1は未予約待機の元D後にobserve/HUD補正が候補Dを未来へ動かし、tick/beginで復活するケース。D+5msでの最新captureに加え、capture end=D−1ms/既知tick=D−2ms/actual commit=D+2msという69ms取得＋3ms後処理でも再現した。単にmax(end,last_now)を使うだけでは防げない。

旧f434 Cで早期end・遅着commit・複数observe・親motion遅着の4semantic Redを固定。private8Bのpending旧Dをmin保持して次actualtickが旧D内と確認するまでauthorityを拒否し、親resolveから最初のtickも元motionDで保護する最小C修正を追加した。ABI/API/cap/他21sourceは不変。実装レビュー第2周と全183/315phase/world160+2を同じ新Cで最終確認する。新C故障はpublication/sourceの2＋expiry1の3として別集計、固定旧b3 Redは最初の2policyを対象とする。

長worldの負例は独立格子とCfitの約2ms差を保つため、CAPTURE sourceをworld B−210ms/L160、PREPをL85/C90/phase0の実公開B−35.5ms＋60msへ固定し直した。200ms±1nsや理想B−20msの境界は公開Cへ分け、worldのsource/clockをCtargetへ同期しない。3歩・第4未送信・元Dlate・商品未達/holding PAUSEの期待は保持する。


## local最終検証と実装第2周

Controller旧165＋新19＝184件、51.566秒/skip0で成功。旧956assert call・全methodを保持し、phase-staleをD内で単独失効させるprivate合成model（+10秒・6period前・合法2秒span/valid model）へsetupだけ変更、旧reason8期待も維持した。追加315位相は独立5ms timerで実Cへcapture/commitを時系列投入し、準備余裕最小6ms・全begin=notBefore、元Dへ10ms残る。最終C SHA `3a16d0b675061dd60b632f419437094e9fea82e90e9027efe01c61910f73f7cb`、test SHA `bc1b38f9060c3f341ee3e5c4e2d30cce2981d87cc5441103252466af6591fa6a`。

実装第2周は設計/安全clear、網羅P2は「旧D内tickでguardを解除したが未予約待機のまま→次observeで補正後D内に予約できる」正例不足。現C Green/解除削除mutant Redを確認する新1件を追加しP2解消、3担当とも残P0/P1/P2なし。これは旧guardの永久保持による誤停止を検出する許可側試験で、production変更はない。

他native/evaluator102件・203既知pathsは136.814秒、client197件は52.596秒、package228件は最終sealで1.619秒、すべて成功/skip0。新worldは3method/160正常＋停止2が最終Cで138.275秒成功。全160で6入力/5移動/開扉1/goods/PAUSE1と連続6拍を確認し、今回は未評価最終ACK例外は未使用。caseごとのCfitとworld時刻の約±2ms差も保存し、時計の同期や未来captureは行わない。原1px揺れを再現した試験ではない。

合計native/evaluator/worldは289method、公開CI対象258/private厳密31除外。旧C fixed b3は長い合成goal自体に到達するため「旧goal不合格」と捏造せず、ordinal2〜6のpublication/sourceの各5違反を独立集計する。新policy2＋expiry1、旧059 C rollback1、Runtime59＋058別2は別集計。Mac全体・実compiler/IPA・配布source照合はこれから実施する。


## 最終Mac開始

正式code `f4162d91eb28fd016340b877746436ea61b301e9` をpush。[Mac88](https://github.com/shuhei0720/necrogold-automation/actions/runs/42620754044)でnative258/新C3故障/旧C1故障・全Swift/Runtime/実compiler/新IPAを実行中。[client20](https://github.com/shuhei0720/necrogold-automation/actions/runs/42620758236)は同codeで成功。標準公開runnerを維持する。

build-source ZIPは7,198,806bytes、SHA `620e243e4e895527350414aa8b0898774967870776719f9d38775a255dcfa319`、462全tracked bytes/CRC/path一致。設計が原ZIPを独立再照合し、Controllerのみ変更/他21/R12原40/G1も保持。最終delivery/contracts検証器は059の条件を維持。安全が実compiler検証器とMach-O旧81 marker＋test060_（82）を点検し、通常/-Oの合成selfcheckで88拒否/8magicを確認した。actual IPAはまだ検証していない。


## Mac88の失敗（成功扱いしない）

native-host258件/31除外、旧0593variant、新060旧policy2/current3/3故障、world160＋停止2はCI実artifactで成功し、独立網羅が全行・source/test/profile・GitHub metadataを照合した。artifact13676331469は778,206bytes/SHA `c636bd394b784922ab71414e436058fd10b3883632a06c521f2e1cb52961c984`。client20も実artifact197件成功。

Mac88はqualified準備15/新2故障/独立world16を通過した後、主Runtime positiveのtestContinuousRevalidationCallbacksPublicで `fixture_current_move_not_late_before_admission` 失敗。remoteVariant1の(-10,1)FLOOR→STONEのSAME再予約4が未送信で、capture45 observe時の元D残36.347203msに対して次capture46が模擬時計を82ms進め、実admission時はD+45.652797ms。targetDriftの(-1,-1)FLOOR→DIRTとは区別する。元D/10msを緩めず、保持callback解放前のcapture再開とboundary時計の順をHOST fixtureで同期する。主Runtime59故障/LoopCtrlKit/RPC/IPAは未完了で、Mac88全体を成功と数えない。

修正前validation artifact13675264534は287,109bytes/SHA `1e0606ba2b1d9f91f23ed60999f29283b84dc81df46466cb5524d2b8618209b9`。原log/snapshot/解析はGit外。production C3a16/22seal/他native21・public C289/world160は固定したまま、HOST修正を実装第3周の設計/網羅/安全レビューで確認し、Mac全体を再実行する。


## 実装第3周: HOST clock/callback同期

`ngg2_runtime_tests.swift`だけを修正、SHA `5615df1e2a35368619b39578d215688073bda8644abaca79b166073492655e3f`。4同形fixtureに共有HOST境界を使い、permit判定と通常80ms進行をFake.lock内で一体化。capture停止中も明示時計要求だけlock外で処理し、PNGは取得せず、境界処理後に80msを重ねない。newIDの実afterTicketReturnedでのみ解除し、oldIDでは解除しない。OriginalReferenceのearlyGoods境界→解除、FRESHのACK確認→cancel→解除も維持した。

元require375ブロック（入れ子込み377式）の全bytes/順序を保持し、元D・10ms・2秒時計待機/fixture pump期限・owner/取消/lease/drainのpredicateを変更しない。EVIDENCEは欠損fieldでもtrapせず、旧mutantの指定assertをログが隠さない。package228/1.544秒とdiffcheck成功。limit設定前に既に進んだ取得は巻戻さず元assertでfail closedとする限定を残す。

設計/網羅/安全の第3周は追加P0/P1/P2なし。C3a16/Runtime/他native21、seal3b768、Controller184/315位相/world160+2/clientのソースは不変。新helper2名はtest060_ prefix、Mach-O検査の82markerへ含め、自己検査は46HOST宣言/88拒否/8magicを確認。実Swift/59故障の各指定RedとIPAは次のMac全体で実確認する。

## Mac89の出力形式失敗と第3周HOST補足

[Mac89](https://github.com/shuhei0720/necrogold-automation/actions/runs/42625173334) / code `beb2160e5fd4fca5c1cbc348faa9f5e3c8fac6b6` はnative258/新world160＋停止2・旧059/新060 C故障を再び成功。native artifact13677398975は778,204bytes/SHA `8f94d0c732f0cda62e9969e956f408aa1a574b27ed2864f22f7e290b3c896c95`。qualified準備15/058別2/独立world16と主Runtime positiveの全assertを通過したが、追加したEVIDENCE18行が元PASSより前へ出て、厳格な `stdout.startswith('PASS production Runtime public API/')` に不適合となった。30行のstdoutは末尾に元PASS、FAIL0。`checked(green)` は成功しており、ゲーム処理の新たな失敗とは混同しない。

診断artifact13679126732は283,641bytes/SHA `b8cae93e14ff297a951d3412c7c7c75fc5cc39643e8ab3ba4690b0db627028bd`。Runtime59 mutationは未開始、LoopCtrlKit/RPC/IPAも未実施で、Mac89全体は失敗として保持する。HOST診断の出力順だけを直し、checkerの先頭PASS/空stderr・375require・元期限とproductionは変えず、実装第3周の補足として独立照合して再実行する。

補足後HOST source SHA `8661cdd1c35d2b49ca7016f667abc5de96207a37edcc196ccfc6c31e364cb8d6`。元時点で作った文字列だけ専用lock付きbufferへ保存し、full成功の既存最終PASS直前にflushする。先頭の元054PASS/末尾の元全体PASS、REPORT順序・375require全bytes/順序・checkerを保持。選択fixtureではmainのflushを含めず、旧故障の末尾指定FAILへ出力を足さない。package228/1.712秒成功。設計が旧047診断modeの型検査互換P1も発見し、旧hash固定fakeにないfixedClock/fixedCaptureAdvanceの新分岐だけを既存LEGACY_CAPTURE_BASELINEで除外した。旧fake/checker/current構成は不変、旧modeの実Swift再実行は未主張。外部Mach-O自己検査は新3helperを含む47HOST宣言/82marker/88拒否/8magicに更新し、通常/-Oとも成功。

第3周HOST補足の最終8661版を設計・網羅・安全が独立照合し、上記legacy互換P1の解消を含め残P0/P1/P2なし。現行構成の元条件を維持し、実Swift全体/59指定Red/新IPAの再確認へ進む。
