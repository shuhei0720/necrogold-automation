# TEST081受領とTEST082

2026-11-12（日本時間、11日受領）。[計画](../plans/test082-materials-motion.md)・[独立レビュー](test082-independent.md)。baseline `7d4f8f435ad54daca79a1ec89b04dfdc6d30e625`、TEST081/build135。実機5回の報告を原画/時刻/状態へ照合した。実機の原資料・Scene・JSON・検証ログはGit外 `analysis-evidence/received081` と `test082-*`。

## 受領と到達

started_ns順は下表。添付順の先頭2件と異なるため、ファイル名の順を実行順としない。

| 回 | run先頭 | native終了 | inputs/moves/restarts | 選択PNG | PNG bytes |
| --- | --- | --- | --- | --- | --- |
| 1 | 1316c4ca | movement10 | 3/2/4 | 20 | 3,368,265 |
| 2 | 8e384afb | screen17 | 1/1/2 | 17 | 2,444,554 |
| 3 | b2166957 | goods1 | 7/5/5 | 20 | 4,746,002 |
| 4 | 48d5cb3c | screen17 | 6/6/0 | 20 | 4,919,201 |
| 5 | 8529e709 | movement10 | 6/5/7 | 20 | 4,469,464 |

5ZIP/97原PNG・計19,947,486画像Bを全SHA/ZIP・PNG chunk CRC/PIL verify-load/896×414/現API16閉schema/client_load/manifest全offset・hash・cursor・prefix/test069実公開gateへ照合した。全resolved/terminal/workers_drained/paused、全最終原画GAME PAUSE、選択画像のnative metadata欠損0。capture/dispatch failureとnative timeoutは0。商品到達は**1/5**。3の原275はstable prefix19、スピア100/レザーアーマー50/チタンシャベル100の全3商品をrootと独立担当が視認した。原273にも全3商品があるがinflight/unstableなので判定権限の根拠にはしない。対象アイテム認識の成功ではない。

5だけhost result_jsonのrpc_deadline4件（status2/cancel2）、取消2回。各request→記録は約2.01秒、HTTPは約83〜165ms、decrypt後→記録約1.30〜1.67秒。最終cancel_confirmed=true/native_cancel_requested=trueで完収済み。nativeのACK→8UNKNOWN→保持PAUSE ACK→movement終了を、後のhost期限/取消と混同しない。単調時計の異なる絶対値を直接差し引いていない。回収の再実行は不要。

## 画像保存の実績

正常見送りPAUSE→RESTARTの判断sourceは実順4/2/5/0/7の**18/18枚を保持**。5の初回source21も原画/metadataを照合できた。最終critical（terminal、最新2scene comparisonのsource/observed、latest MOVE source）も全5runで欠落0。全画像は各512KiB以内/20枚以内/10MiB以内で、後3runは旧4MiBを超える。v2の追加保存と完収が実資料で成立している。

全取得画像保存ではない。omitted_image_count計696、missing reference計70。3の古いcmd16/observed240は省略されている。2の128/129は既scene_change経路に残らず、取得行はあっても原画がない。歩行中の入力前後/比較/停止画像の保存自体は継続しており、新しいC診断ではこの未収録の拒否経路を限定して補う。

## 原因と限定修正

### A: 床・石のpixel証拠

4の原111→112は同じ次床がmedian RGB44/26/23→47/28/24となり、旧bright FLOORのB下限余裕+35→−30でDIRTへ変わった。これにより通常NavのUP→DOWNが変わり、全6ACKのMOVED記録と原120の実DOWN1が一致する。原120→121でも同じ世界床が45/27/24→47/28/24へ揺れている。全保護/ITEM0、strict BLOCKED。旧080/新081の全6ACKは最初のgeneric判定でMOVEDであり、新081side gate補助が逆転を起こしたのではない。DIRT一cellだけの診断用counterfactualは元UP full5へ戻るが、これを実Perception出力や実機再現とは呼ばない。

5の初回source21は上左口(-2,-3)に下半分の床textureが見える一方、上半分の黒でfull中央値が7/3/3となり旧DIRTへ入った。旧口候補の他条件は満たすが、mouthがFLOOR/UNKNOWNでないためmask0。最初FLOOR17→source21開始は232.662msで、元200ms資格不足ではない。原21を使った追加pixel証拠のC prototypeでは口だけFLOORとなり候補bit0、既Navの観測床path5/first LEFTへ進める。外側(-2,-4)はUNKNOWNのままで、未知への入力権限は増やさない。

5の旧STONE(6,4)→latest(7,4)は50/39/27→51/38/27となり、元B条件の余裕+50→−3でDIRTへ変化していた。STONE対応の修正だけで最後の移動を証明できるとはしない。

提案は既gate/wood変換後・商品前の既DIRTだけを対象にする3proof。brightは元full floor条件のB下限だけの差1…77と二つの固定非重複分割、半可視は上12行95%黒/下13行90%非黒と元floor texture、STONEは元R/GとB差0…76・固定非重複対角領域を使う。各floor witnessには元入口R≥6/G≥3も必須。rootがGit外prototypeの入口漏れを指摘し、salt-blackの公開API誤FLOOR反例を修正後にDIRT維持へ戻した。旧palette行/元閾値とGOLD/gate/wood/保護を変更しない。

校正97原画では29cell（FLOOR20/STONE9）の追加だけで、26原画の全29箇所を材質視認した。非tile Scene bytes/商品/保護/拍/署名は不変。見送り18枚では原21だけ候補0→1、他17は0維持。調整に使った同じ資料を未知評価と呼ばない。

### B: 無金通路の実unit

1のcmd12 UP/source160→178は元10ms窓内begin/ACK後8UNKNOWN。原画は実UP1、最後のCreturnでもvisualD残約1.868秒。raw unit best .471720965/gap .386339215で通常.45を外れるが、旧074の全旧STONE保持/非共線DIRT/全9translation一意、旧075のworldBlur477支持/10bad/帯372・105と左右phaseの有限unit/競合が成立する。材質prototype後も同じ限定ANDが成立した。

旧判定後UNKNOWN・両FLOOR/金CLEAR/商品UNKNOWN/保護・ITEM・金0・元origin/実next床に限り、上の既証拠を追加ANDする。high raw>.45/有限best+runnerup/gap.08/正しい9px unit、旧21依存/52帯300・95%・帯100・全73/15ppと独立phaseを保持する。旧helper全文/順序/閾値を変えず、MOVED以外や開通/入口creditへ流用しない。

5の最後cmd22 LEFT/source341→360は元窓内begin/ACK後8UNKNOWN、Creturn時visualD残約1.898秒。原画では実LEFT1だが、材質案で2STONE対応が戻っても旧known phase約.597>.45、fixed52は239/23bad/帯86・153、別固定面も95%や支持条件を満たさない。これを無理にMOVEDへ変えない。今回この金壁caseの移動確認は未解決として残す。

最終素材/移動の合成後、97原画/36保持ACKの比較で、既known27/UNKNOWN9のうち2のsource116→126だけ既LEFT1MOVED→UNKNOWNへ回帰した。source116の該当床2点は既にFLOORで、応答126の床補正は正当。追加STONEのsource側は固定heart HUDへ91px交差するUNKNOWNであり、HUDを解除して回避しない。

原因は、旧075 worldBlurで従来support<300だった8px競合が正しいFLOOR復元により384へ増え、9px unit574/18badとの一致率差が4.416ppになったこと。STONE追加自体は結果に影響しない。raw unit .598053/gap .179268、旧075唯一L、左右有限phaseの最小gap .095074とblur95%品質は維持する。そこで旧5依存raw gradient（884/63bad・65帯666/218）の全73最小15.4539pp識別を別にANDするB2を計画へ追加し、同じ独立レビュワーが着手GO。blurの95%品質と別gradientの75%品質/15pp競合を別々に要求し、支持を合算せず、旧blur15ppが成立したとは書かない。旧helper本文/閾値と材質補正を維持する。公開意味Redと局所Green、修正後の保持pair確認が済むまでP1解消・最終GOとはしない。

### C: 未発行stationaryの拒否証跡

2はcmd7がcapture128でbegin0のまま退役し、VISUAL_SCHEDULE/clock3の独立静止観測へ移った。128/129原画がなく最初の拒否は未確定。保持126→130には床/石と経路先の変化があるが、これを実128/129の代わりにして成功を主張しない。081のB/C例外は今回1/2/5には該当しない。

新C診断はstationaryのOBSERVE/READY・退役旧MOVE・元beforeと固定anchorの全bytes一致・同world/current-prefix/独立観測・真mask非0だけで既record_changeを加える。ROUTE10/MOTION11の拒否をその観測IDと結ぶ。mask0/署名だけ、ISSUED、metadata/時計/独立性不成立には偽行を追加しない。理由/入力/票/期限/予算/ACK専用MotionReference、既3行first1/latest2は維持する。既Runtimeの比較優先を使う診断であり、2の到達改善を確定したとは呼ばない。

## 新単体と最終固定差分

新規はA7/B8/C3の計18methods。Aは公開analyze_RGBAの3positiveで旧DIRT→要求FLOOR/STONEの意味Red（compileclean/error0）を先行し、最小apply後7Green。後の境界追加は編集した6methodsだけ再Green。元Perception本文は新helpers/callを除くと旧e3ba…へ完全復元する。brightness77/78は整数RGBとR39…52で実現不能なため最近接75許可/85拒否、STONE76/77・上黒285/284・下非黒293/292も公開境界で確認した。salt-blackのwitness入口漏れは製品適用前に修正済み。

B1は公開O0/strictO2×4方向の意味Red8→mainGreen、残5のうち4Green。phaseの正例をdouble上の.6+.08−.6が.08を下回る値で作ったfixtureを、表現可能な>=.08と下回り拒否へ訂正し、そのmethodだけ再Green。B2は手続fieldと厳密9px真値・旧Lunique/原074false・blur品質/blurlead不成立・gradient品質/全73lead・finite phaseの全前提を満たす公開意味Red2→mainGreen。境界methodはUP入力へhorizontal aliasを作ったfixtureの方向だけ訂正し、そのmethodだけGreen。両newhelpers/calls以外の旧Nav全bytesとB1の既本文は不変。新8methodsの既Greenを形式的に全再実行していない。

Cは元SCREEN17/元票・credit・Recovery/MotionWait/Refs不変を先にassertしてから、診断行1件対0件で旧C意味Redを確認し、最小apply後Green。残2は開始時に既generic行があるshop fixtureを既0行の公開noGold passage fixtureへ訂正したmethodだけGreen。新ROUTE/MOTION行は既native_walkのscene_changes/scene_change_details validatorsにも通過した。新C seamは追加していない。既関連のローカル重複実行はない。

最終Perception SHA `2818660c755078d24785b8ae7424de1b3c236a29a3eab5de21ce183075539dd2`、Nav `dce5f19e9efa38e390c1f71c4d82019ddcf339a395e6da58ed08388e1043c19e`、Controller `12d3a59a29ccd465c4e3983c637b2e8bf6cefa4c5ed166005be840b90d740250`。対応新testはA `3880719e32a83303226d632f293bcb8253ee5bd2bb705c4431cfacb5a252f8f4`、B `f9585ba8c5e1c54f8205722e492e92068a343fd8fb99d2242eeb9450438bf099`、C `1edd1f401872745a8e4d4fa45602839df85c9ecb44f4d7d0eaba4dd65abc8e07`。

B2後の新C4/97原画/36保持ACK比較は旧結果を上書きせず再実行し、旧known27すべて完全維持・回帰0、旧UNKNOWN9は実1/cmd12/source160→178だけUP1MOVEDへ改善、残8UNKNOWN（実5/cmd22を含む）維持を確認した。実2/cmd6/source116→126は旧LEFT1MOVEDへ復旧した。最終比較JSON SHA `93f207a625967ca9990d53683d5b5e714c1ae0ca658d52afd5b10827347d20fb`。これは新source変更に対するP1確認であり、同じ資料を未知実機評価へ読み替えていない。

freshG1→seal/applyも生成済み、22中Perception/Nav/Controller3変更・他19不変。manifest SHA `bcaaddac06624802266e404cabae5382e706f20be05df27a1c1b6af8e1128b71`。Runtime048a…、API16/cap15/client16・4core client・G1/R12の同一bytesを維持する。新selectorの実ASTは43methods/18scope（native36=新18+旧18、client4、selector3）。selector自己3はGreen、native/clientの意味再実行は最終same-code CIでだけ実施する。

## 単体・最終検証・配布

この時点では新公開単体/固定sourceまで確認済みで、同codeのhost CI/実compiler/IPA/固定公開GETは未完了。独立した同じ1名がP1回帰の修正・作者ログ・最終保持比較と固定3source/selectorを確認し、残P0/P1/P2なしで静的最終GO。作者の実ログと最終ビルドに結び付いた結果だけを後で追記する。Perception/Nav/Controller3source変更・他19、Runtime048a…/API16/cap15/client16/4core client同一bytes。新Runtime Mac Redは不要。旧070/081保存fixtureの今回実行と過去Red133の再利用を区別する。

新IPA/完全sourceを固定Releaseへ保存し、全source/IPA/匿名全GETを照合してから、通常1-1ポーズからrestart→候補→商店→全商品確認の5〜6回を依頼する。元081の追加回収/再実行は不要。今回の改善で全配置の到達/見逃し率・恒久毎拍/人超え・対象認識/通知/対象なし周回を受入済みにしない。
