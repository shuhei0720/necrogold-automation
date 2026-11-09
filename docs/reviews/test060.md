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
