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
