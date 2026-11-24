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

差分全域のController変更23関数・Ring変更15関数を独立レビューしP0なし。上部初回配分/5歩とpolicy18は限定8項目設計・レビューを経た。新テストの成功だけで実機不合格を閉じない。

既109の「名前なし正画像＋同商品価格をCANDIDATEにする」期待は、111以降の正画像/価格要件と旧製品出力にも反していた。TARGETへ訂正し、score/実価格/wordなし/候補保持のassertを強化した。既budget8の即reason17期待も旧製品で有限観測待機へ移るため、旧命令側reason17/回数8/再送なし/期限内外入力なし/3秒鮮度切れを検査する形へ訂正した。どちらも製品の旧Redとは数えない。

私的cutのAPI ACK1とevent ACK2の混同、実費課金後の古いgetter時刻、新numeric testのSceneなしpolicy形状拒否期待は、元不合格を残して訂正した。返値だけを成功にせず、入力state・event・移動credit・採用statusまで確認する。PIL不足や誤COREパスのcompile失敗はRedから除外した。

## 配布前の残工程

選択したMac3境界は、旧queueの失効/同準備epoch、上部5歩の通常RGBA→Ring/C→耐久RS→次child、pending FULL DATAの同job受渡し。全Runtime故障集合の再実行とは区別する。現時点では実Mac結果、最終IPA/実compiler/全source照合、固定Release匿名全取得が未完了。

## 実Mac255の不合格と試験側の切り分け

CODE5db3148/run45398540174では、source封印・host105件・実Python3.9の76件が合格し、Swift/Cの結合コンパイルも成功した。Mac3ケースは不合格で、IPA作成へは進んでいない。この結果・原artifactを保持し、成功へ読み替えない。

preinput/current DATAは、ほぼ即returnするtickの実測がDarwinの時計量子で0nsとなり、各callを正値必須とした試験assertが止めた。0は0のまま課金し、実呼出数と終了時の合計実費を確認する形へ直す。架空の1usを付けない。

上部は2実lead→OPENED→H2まで到達。H2のworker結果を7.185ms跨ぐ画像82は初回用例外の対象外で、次画像では準備に遅れ、1拍後退すると残3DOWNが固定capを418.931ms超える。これは記録/既式で整合するが、未出力の全private分岐を完全除外したとは扱わない。分類前の検証hookがRuntimeで済んだPNG decode/Perceptionを重複実行して約15msの余分な負荷を加えていたため、同じ原画像の検査を終了後へ移して再確認する。カメラ/ACK/物理phase/元T・D/製品route capは動かさない。各jobの早期snapshotを一般化する製品案は保留し、まず検証処理が製品の実行時間へ混入する点を正す。
