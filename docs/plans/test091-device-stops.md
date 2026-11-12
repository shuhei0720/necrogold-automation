# TEST091: 実090の停止を分けて対策する

2026-11-13（日本時間）。基準c9e087050f5d6c7c30d8385014ea0909e534c963。修正前に[修正記録](../fix-records.md)と該当関数を照合し、既対策を改善完了の根拠にしない。今回も同じ独立担当1名で必要差分だけを確認する。

## 1. 受領・主指標

実順c4109c61/3c04c7df/ec411d6fの3ZIP/60PNGを全CRC/SHA/strict load/certificate/canonical sidecar/登録fileへ照合。全回収完了、全3商品確認0/3。実3原184は人ラベル/独立目視とも「のろいのゆびわ」だが、全商品は欠けている。実runはgoods0/sources=[]で個別判定未呼出。凍結した公開classifierの原184一回評価もno_complete_row/rows=[]でicon/name未実行。精度合格/誤判定とは呼ばず、この原画を以後の調整へ使う場合は未知評価へ流用しない。

## 2. 実1: 初歩前の拒否と欠落

0方向入力/0歩でLEFT14は未送信。元source174はCLEAR/候補mask160、最初の拒否175は画像が未保持で最終predicateは未確定。後187を175の代用にしない。FR-045-INITIAL/FR-061-SYNC/FR-074-FADE/FR-076待機の適用条件を照合する。

確実未送信の初歩だけを退役する。current event/command全field一致・state1/MOVE/begin0/outcome0/初歩票有効・元CLEAR通路reason10・level入力/移動/lead=0・固定原点(0,0)/入口未確認・正常FLOOR/商品UNKNOWN/原点FLOOR/保護なし・同prefix・非取消/非終了・元同期12秒以内を要求する。既初歩replan上限2回を消費し、旧票を永久not_sentへ、slot/model/commandを撤回してSYNCへ戻す。sync起点・initial view起点・walk起点・ordinal・session/全予算は延期しない。新規の独立した非交差current-prefix観測2枚で同じ候補mask/口脇30支持/金集合/完全chooseとstrict BLOCKEDを確認してから別IDの初歩を取得する。候補なしの2枚も同じ静止証明と、元候補の口が確かなDIRT/STONEへ閉じ、口/脇支持が独立2枚で一致する旧074の条件を確認してから見送りへ渡す。元候補の口がUNKNOWNのままなら陰性にしない。新actual GOLDも2枚確認を飛ばさない。元ticket/epoch/未確認移動creditは使い回さず、送信済みUNKNOWNやlead/MOVED後へ広げない。実1の拒否175欠落による原因未確定は維持する。

診断はprofile2だけ、run内のlead未確認・原点・CLEAR sourceの未送信MOVE SCREEN拒否raw1枚を追加保持する。前後のimmutable snapshotの一致MOVE/累積入力・移動不変/begin0/outcome3と、同prefix・拒否event終了時刻に一致するcurrent captureを照合する。診断側はlevel入力0を断定せず、初歩retune等も対象になり得るが回復/入力権限は与えない。mask0を架空のSceneChangeへ変えない。terminal/found・既診断最大5・map最大12の既保持順/保証を維持し、20pinの余剰1枠を使う（critical最大7→8、計20/10MiB不変）。profile1/既schemaは変更しない。新fixtureの作成/hash固定を製品変更前に行い、Swift不在の開発機では意味試験を実行済みにせず、Macの同一限定job内で固定c9 Runtimeのassertion Red→現Greenを実行する。

## 3. 実2: CLEAR通路の実UP1

source308→326は全旧STONE2/非共線DIRT17が唯一のunitで保持される。現17段はUNKNOWN。旧terrain blurはrunnerの左raw位相帯INFとblur8px競合の15pp不足、旧corner条件も不成立。rawの左右帯とworld/axisの上下領域を区別する。FR-090-HUD-STONEは隠れSTONE0で対象外。旧証明を緩めず、UNKNOWN専用の別証明を追加する。

両Scene FLOOR/CLEAR/商品UNKNOWN・原点/次セルFLOOR・保護なし・全旧STONE≥2保存/旧DIRT≥9非共線・全固定HUDサンプル外・0/±1/±2の9候補で唯一の同方向unitを要求する。有限global raw全73のunit最良/gap≥.08、world blurの95%・二領域各100、signed-axis75%・二領域各100・全73競合15pp優位を全てANDする。既finite-band/旧blur競合条件そのものは変更せず、異なる証拠一式として分離する。旧known/TWEEN/逆/多格/矛盾/共線/競合/片帯不足を拒否する。

## 4. 実3: 木扉の開通0変位

source166→184はfront DOOR→FLOOR、同GOLD bracket2/unique zero、goodsUNKNOWN→PARTIAL。薄鉄型誤認FR-090-THIN-IRONとは異なり、旧FR-072-NARROW-OPEN/FR-074-OPEN-GRADIENTの開通証拠不足の継続に当たる。旧rawzero .45546、detail355/不一致37、gradient223で既条件を満たさない。

旧17段・95%証明/閾値を変更せず、UNKNOWN専用の追加zero証明を末尾へ置く。両FLOOR/未完goods非減少・同GOLD bracket/unique zero・front DOOR→FLOOR・原点/endpoint非保護、既raw73候補の有限zero最良/有限runnerとの差≥.08、独立blurzero有限≤既定.45、既opening detail≥300/75%一致・二領域各100・全73を旧texture_leadで比較する条件をANDする。blurはzeroの絶対品質だけを担当する。rawの+INFやdetail支持300未満の競合は支持不足であり、肯定的な優位証拠と呼ばない。全73有限とはしない。NaN/負INFを拒否し、有限な同率/優越候補は許さない。75%だけへ変更するものではない。実unit/非zero/保護/金矛盾/商品減少/blur不成立を拒否し、開扉0歩の既経路へ渡す。未収録の進入後商品画像は合成しない。

## 5. 所有・TDD・既修正保持

Navigationはmotion091が一元編集し、shop091は開扉blockと新単体を分担する。初歩/診断は別担当が計画確定後に編集する。変更ごとに公開C/controller/必要Runtimeの有効assertion Red→Greenと関連単体を選ぶ。生Sceneは校正、元時刻/画像/実入力応答の足りない全runを再現したとは呼ばない。旧stage/monotone・入力窓10ms・UNKNOWN無再送・候補保持/全予算・API16/cap15/ABIを維持する。

## 6. 判定・回帰範囲

Python/feature/kernel/word/閾値と56,088B ELFは変更しない。稀な対象を出す周回は依頼せず、原184の調整前出力を保存する。到達前停止を個別matcherの再発に数えない。旧090のHUD/新bracket/薄鉄と今回の条件を区別し、同じ根本原因が再観測された行は継続として更新する。過去の未整理回数は0にしない。

## 7. CI・実物・配布

090の汎用検証を再利用し、091はc9基準と確定した新/関連methodだけに固定する。090の表示例外/icon例外は持ち越さない。必要な単体/関連とIPA作成のみ標準Mac/Ubuntuで実行し、全Runtime故障や旧全33群は実行しない。Runtime保存を変えた場合だけ該当する公開保存境界を追加する。

22seal/実compiler・RSP/PBX/全MachO/全source/IPAを実物で照合。5gate readerは日本語NUL列挙の修正版を継承し、旧293禁止markerを保持して新fixture集合を追加する。既成功は新CODE/run/SHAへ結合し、前回PASSを今回実行へ読み替えない。固定Releaseへ完全source/IPA/SHAを保存し匿名全GET/actualtagを確認する。

## 8. 返却

修正日・確認方法・再発/継続数を更新する。単体/校正/静的reviewは改善完了ではなく実機未確認とする。新IPA更新/LoopCtrl完全終了・再起動/Start Server/通常VPNから、一連の候補探索→商店→全商品確認と全run ZIPを依頼する。090追加回収/稀な対象待ちは不要。実到達率/毎拍・人超え/未知陽性精度は未受入。
