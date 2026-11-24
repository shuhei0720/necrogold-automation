# TEST118: TEST117実機4失敗への限定修正

2026-11-24（日本時間）。[計画](../plans/test118-device-failures.md)・[上部5歩](../plans/test118-upper-five-step.md)・[修正表](../fix-records.md)。現在は実装/関連検証済み、実Mac結合を修正・再確認中でIPA作成/配布前。iPhone受入は未実施。

## 元の失敗と変更

受領8ZIP/4run・96PNG/110記録を全照合。子run0は全て停止しており、回収完了を動作成功とは数えない。原本はGit外に保持する。

| 実機での失敗 | 確認した原因と実装 |
| --- | --- |
| 1周3歩、2周通路で停止 | ACK後の実画像を古い入力前sourceで比較するとUNKNOWN。確実未開始・独立同位置画像・通常strict零の時だけ、既SAME機構で新sourceへ1回更新。元MOVE/準備epoch/target/全窓/period/回数予算を保持し、開始済み入力を再送しない |
| 3周、商品可視でもRSせず | policy17の18ink未満価格断片除外の適用漏れを修正。別の床照明問題には、旧3%を上げずraw総和比と画素比中央値の両方を要求する別証明を追加。原106/107/108は通常完全陰性/Ring数値証明1 |
| 同3周、worker待ちでSCREEN | 同商品/保護/局所床と元source/worker/親期限が保たれる遠方材質差を、既DATA関係へ限定降格。判定結果を保ち、移動信用を付けない。候補優先・危険変更のsticky拒否を維持 |
| 4周、上部開扉後停止 | 同画像間の遠方壁露出と遮蔽材質差を合成できなかった。限定DATA合成と元source-end/worker返却fenceを追加。旧V1を保持し、row4の新V2だけHHDDD5で全3商品/下床まで進む。片面/高入口の14支点を新policy18でRing/C別々に検査 |

初回rootリスタート、新しい118実装cap確認、候補保持/購入なしを維持する。API16/native_v15/ABI/compiler profile3は変更しない。37native中変更はController/Ring/RPCの3sourceで、残34、Runtime/Ticket/Spool、R12全40、G1、保護特徴資産は不変。

## Redと関連検証

- preinput新11件は旧assertion Red後に合格。入力直前の実画像108/137を使う元時刻cutでも旧ID失効・新ID begin・ACK後unitを確認。4cの未保存107/元rolling model、006の次に必要な156は存在せず、その先の実機継続を証明したとは扱わない。
- 価格新4件、床moment新6件、policy18新7件は各旧assertion Red後に合格。真の第4価格、平均だけ合う異色混合、全支点/床/保護/価格欠落、target/candidate保持を含む。Ring直接関連と旧consumerを含む集合65件も合格。重複再実行を件数へ加算しない。
- pending FULL DATA新8件は旧Cで正常陰性がSCREENとなるassertion Redを確認。新8＋直接関連22の計30件が最終C/Ringで合格。陰性→耐久RS→次床、UNKNOWN保持、候補優先、危険材質/保護/局所床、sticky、元親期限を確認。
- 原3周のsource107/job3/元worker開始/108撮影時刻を固定する限定統合も確認。正常Ring107の新実測39.564msを課金し、worker開始から40.737ms、source150msには67.873ms残る。108が先着しても同job/親期限のまま陰性採用→公開PAUSE→durable確認→RS予約/intentまで成立。未記録mode0/retry1は到達可能な宣言条件であり、実I/O/実RS送信/次の実機床はこのcutでは証明しない。
- Cのpolicy18独立採用は通常Ring結果を旧Cへ渡す左右2assertion Red後、新4件が合格。14別支点・全3下床・exact halo・typed偽装/価格/NaNを再検査し、正常陰性→耐久RS→次床を確認。
- 上部新7件＋旧V1関連3件、配分境界14条件が合格。元clockの5歩componentは全57 C境界の実費、constructor832790ns、最終worker総slot100msを含めて約417.972ms残る。route上限は入場前に1周期分を一度だけ配分し、各jobの既境界による短縮は保持する。別実行でbeginが15.387msとなるホスト不合格も保存し、全負荷/端末速度の保証にしない。
- iSH clientは実Python3.9.25で新11＋旧65の76件が合格。旧cap/誤spoolではnative start前に拒否する。

この検証は、実画像の停止点校正、限定C時刻cut、公的な独立future、Python clientを区別する。元private current mode/retryやjob1/2のsource・返却順を推測で復元しない。実機の商品到達率と毎拍速度は次のiPhone試験で評価する。

## 独立レビューと試験の訂正

初回差分のController23関数・Ring15関数に加え、追加cacheの11関数も独立レビューしP0なし。重複を除くController変更は31関数。上部初回配分/5歩とpolicy18は限定8項目設計・レビューを経た。新テストの成功だけで実機不合格を閉じない。

既109の「名前なし正画像＋同商品価格をCANDIDATEにする」期待は、111以降の正画像/価格要件と旧製品出力にも反していた。TARGETへ訂正し、score/実価格/wordなし/候補保持のassertを強化した。既budget8の即reason17期待も旧製品で有限観測待機へ移るため、旧命令側reason17/回数8/再送なし/期限内外入力なし/3秒鮮度切れを検査する形へ訂正した。どちらも製品の旧Redとは数えない。

私的cutのAPI ACK1とevent ACK2の混同、実費課金後の古いgetter時刻、新numeric testのSceneなしpolicy形状拒否期待は、元不合格を残して訂正した。返値だけを成功にせず、入力state・event・移動credit・採用statusまで確認する。PIL不足や誤COREパスのcompile失敗はRedから除外した。

## 配布前の残工程

選択したMac3境界は、旧queueの失効/同準備epoch、上部5歩の通常RGBA→Ring/C→耐久RS→次child、pending FULL DATAの同job受渡し。全Runtime故障集合の再実行とは区別する。現時点では実Mac結果、最終IPA/実compiler/全source照合、固定Release匿名全取得が未完了。

## 実Mac255の不合格と試験側の切り分け

CODE5db3148/run45398540174では、source封印・host105件・実Python3.9の76件が合格し、Swift/Cの結合コンパイルも成功した。Mac3ケースは不合格で、IPA作成へは進んでいない。この結果・原artifactを保持し、成功へ読み替えない。

preinput/current DATAは、ほぼ即returnするtickの実測がDarwinの時計量子で0nsとなり、各callを正値必須とした試験assertが止めた。0は0のまま課金し、実呼出数と終了時の合計実費を確認する形へ直す。架空の1usを付けない。

上部は2実lead→OPENED→H2まで到達。H2のworker結果を7.185ms跨ぐ画像82は初回用例外の対象外で、次画像では準備に遅れ、1拍後退すると残3DOWNが固定capを418.931ms超える。これは記録/既式で整合するが、未出力の全private分岐を完全除外したとは扱わない。分類前の検証hookがRuntimeで済んだPNG decode/Perceptionを重複実行して約15msの余分な負荷を加えていたため、同じ原画像の検査を終了後へ移して再確認する。カメラ/ACK/物理phase/元T・D/製品route capは動かさない。各jobの早期snapshotを一般化する製品案は保留し、まず検証処理が製品の実行時間へ混入する点を正す。

## 実Mac256の追加切り分け

CODE2fe4bfb/run45402106245もhost105/Python3.9の76件・Swift/C compileは合格し、Mac3ケースは不合格、IPAは未作成。原本を別保存した。

preinputはFakeのwalkXが既にtile単位なのに36で割っていたため、先行2入力がBLOCKEDとなる試験画像だった。さらにrefreshのBoolがcommit待ちの旧画像52へも適用され、計測費用後に同じ予定時刻へ戻そうとした。tile単位と対象のexact capture IDを保ち、予定cut以上かつ元not-before未満の実時刻を検査する。元ticketの全時刻を動かさない。

DATAは、最初の正常UNKNOWN producerを2枚の後続画像が揃うまで止める人工的な順序fenceが、実worker100msを12.509ms超過した。最初の結果は自然に返し、既current DATAを実queueした後の1遠方画像だけを待つ。画像/Perception検査は終了後へ移し、同じsource/job/元worker deadlineと親を保った採用を要求する。

上部はOPENED/H1までで、full routeは未確認。次画像80の終了自体が直前拍の準備に間に合わず、保存next targetでは残経路が固定上限を超える。新per-job例外はこの不足を直さないため製品案を保留する。入力中の2回の全文report取得と過剰な試験pollを、実gesture pathの一回消費/撮影ごとのpose凍結と通常の有界heartbeatへ置換して検証する。撮影・ACK待ち・物理phase・元期限は保つ。停止Spoolの型/包含guardも分離してMacの既知path aliasを限定正規化し、原資料が欠けたまま成功扱いしない。

CODE3の上部モデルは、入力中のC再照会をやめ、実際に渡ったgesture pathを撮影境界で一度だけ消費する。旧版は278ms待機前にposeを更新していたため、破棄対象のinflight画像は変わり得る。この差を全pixel不変とは書かない。権限を持つstable/noninflight sourceは実ACK済path/prefixとposeを照合し、8実入力のsource/実変位画像が全て検査対象に入ることを要求する。普通のcampaign_statusは小さな応答であり、2回の全文reportと混同しない。

## 実Mac257の原因確定と追加修正

CODE3229fc9/run45407428441ではhost105/Python3.9の76件・Swift/C compileが合格。preinputは実Runtimeでも先行2MOVED、旧予約の失効、同準備epochの新予約、実beginを確認した。残る上部/DATAは不合格で、IPAは未作成。原artifactと停止Spoolを保存した。

上部はH2のC begin成功後、実送信直前の時計検査が元Dを249,740ns超過した。main入場はnot-beforeから7.730ms後、C begin時の残り2.270msに対し、C beginと後続guardの実費が2.520msだった。同じanchor62/current64の通常Motionをobserveとbeginで二度計算していたため、[限定計画](../plans/test118-upper-begin-cost.md)に従い、C所有の全画像bytes/metadata/episodeが一致する場合だけ確定済みの直接strict零を再利用する。新画像・別anchorは通常Motionを実行し、入力窓/Runtime最終guardは変えない。新8件と上部/V1関連10件が合格。原RAWによるLinux単発のstatic部分は3.277msから0.010msへ短縮したが、Mac全beginから差し引いた成功とは扱わない。

DATAは、旧UNKNOWN結果が新source46の観測開始より20ms先に返り、pending FULLの新画像受渡しを試験が作れていなかった。最初の旧workerだけ新画像の実C observe一件を待ち、worker内の待機/通常Ring/軽量guard実費を元100ms内へ課金する。旧256の二件待ちには戻さない。元source/job/期限・通常UNKNOWN/新陰性・危険差の拒否・実RS/次childのassertを保持し、順序13項目を証跡へ残す。商品判定を強制したり、製品期限を広げたりしない。

追加変更の実Mac結合・IPA・iPhone受入は、まだ未確認である。

## 実Mac258: 二境界合格と上部の初回限定漏れ

CODE8336f22/run45414144439はhost113/Python3.9の76件・Swift/C compileが合格。歩行予約更新とpending FULL DATAは実Runtimeでも合格し、後者は通常UNKNOWN→新陰性→耐久記録→実RS→次childまで進んだ。上部だけ不合格で、IPAは未作成。

上部はH1後のjob2/source68の通常UNKNOWNを正しく採用したが、直後の画像69は返却3.848ms前に撮影開始していた。69は元68終了後36.445ms・worker開始後14.662msに独立撮影され、終了/commitは返却後。同prefix/非inflightの元資料を確認した。既早期画像条件がinputs0の初回限定のため採用されず、次70では準備cutを過ぎ、一拍後退すると残H2＋DDDが固定上限を419.141ms超える。H2予約は未発行で、257のbegin/send期限超過とは別原因である。

各jobの同条件を一度だけ使う限定修正を、独立設計/差分レビュー後に実装。新3件は旧Cで6条件のassertion Red後に合格し、直接関連21件も合格した。実unit後のbridge0新job・V2・既Runtime return fence有効時だけ、凍結source-end/owner/level/opening/current prefix/歩数と元worker-returnを結ぶ。同job再結果や素材bridge1では再armしない。初回旧mode/V1/finite feature-off、元親期限/準備50ms/送信10msを保持する。

原RAW68→69の通常strict零と全床/保護/GOLD支持は別途確認。原metadataは新資格を満たし、新公開testはその相対時刻でprepareへ進む。近傍の保存fitから計算した69commitの準備余地は約28msだが、未保存live modelの完全再現とは扱わない。既合格二境界・未改変のrendererは固定し、追加修正の実Mac/IPA/iPhoneは未確認とする。

## 実Mac259: 未送信境界の診断不足

CODE6548509/run45419240354ではhost116/Python3.9の76件が合格。Macの歩行更新/DATAは二回とも合格したが、上部は初回H1、変更なしの一度の再実行ではH2が未送信で停止した。IPAは未作成で、両不合格の原ZIPを保持した。再実行ではH1実MOVED後、跨ぎ画像69からH2予約を確認しており、各job一回の追加条件は実際に行使された。

初回は同じ直列controlQueueの画像116観測がH1のDを125,486ns超えて終了し、その後の実行は既に期限外。H1はC begin前にCAPTURE/NOT_SENTへ落ちた。二回目H2もbegin0/CAPTUREでD後165,801nsに終了したが、直前観測はDの23.336ms前に完了している。古い別命令のfirst-only dispatchFailureしかなく、H2のmain到着・最終guard時刻・準備epochを識別できない。二回目を同じ観測跨ぎやC begin計算費用が原因とは書かない。

upperは実monotonic時計・offset0で、固定時計用の20ms加算やC費用の二重課金は適用されない。画像生成はbackground、mainの定期keepaliveも軽い応答であり、CPU/queue/mainのどこへ遅延が寄ったかは未確定。汎用asyncAfterの許容遅延というAPI上のリスクと、今回の唯一の原因の確定を分ける。

次は製品条件を変える前に、upperだけの有限整数ledgerで実予約・main到着・既C beginと準備getterの実引数/返値を記録する。元Runtime/Controller/Ring、時計/phase/10ms/全assert、通過済み二ケース本体は保持する。診断を入力資格へ使わず、hot pathのRPC/画像処理や追加の資格getter呼出も加えない。同じ条件の再試行を繰り返す代わりに、失敗分岐を特定する。

## 実Mac260: 最後の未発行D3を特定

CODE694231e/run45426550873ではhost116/Python3.9の76件が合格。実Macでも歩行予約更新とpending FULL DATAは合格を維持した。upperの有限ledgerは1778行/drop0で、H1/H2/D1/D2の全C beginと実MOVEDを記録した。最後D3だけ未発行で停止しており、この実行の原因を259の未送信やFULL用early snapshot条件とは混同しない。

D1後の画像80は撮影に78.596791msかかり、D2が一拍後になった。D2後の正常FULL UNKNOWNはsource93/job5で採用され、次94の撮影開始はworker返却後3.926084msだった。原93→94は通常BLOCKED零、床/保護一致と全GOLD保持、次DOWNは観測済み非保護FLOORである。最終保存fit換算では94の次tickが直前拍の準備50ms境界を約4.384ms過ぎた。既定の一拍先target185648580613の公開入口は、lead150ms/publication100msを引いた185398580613で、元P185313080237より85.500376ms遅い。未保存の94当時modelまで再現したとは扱わない。

[最終slot計画](../plans/test118-upper-last-slot.md)は独立設計P0なし、旧Cの公開lifecycleで左右2条件の意味Redを確認した。V2の最後D3だけ、最新D2の通常unit/ACKと現在の直接零・床・modelを結び、未発行の次physical beatがまだ未来なら準備50msの例外を評価する。通常50ms、publication100ms/source200ms、tail鮮度余裕、元Pと送信10ms、実AX/Runtimeの全入力guardは保持する。一般の再同期条件を残し、この限定例外を契約へ明記した。新3＋直接関連21の計24件が合格。guard対応表では新subcase・既比較の再利用・静的検査・専用negative未実施を分けた。独立差分レビューは2関数とprivate stack型を確認しP0/P1なし。Runtime/fixture/phaseを変更せず、新Mac・IPA・iPhone受入へ進む。
