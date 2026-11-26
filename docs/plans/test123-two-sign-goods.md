# TEST123: 二看板の同一商品列を正に全被覆する

2026-11-26（日本時間）。基準は出荷TEST122/build272、CODE `f5143e339a1e6efddb3c24a69dbea163fd1007de`。以下は承認計画で、rootの正式GO・独立レビュー後の実施結果を末尾へ追記した。実機改善・速度は未受入。[要件](../requirements/necrogold.md)・[対象契約](../contracts/target-assessment.md)・[native契約](../contracts/native-control.md)・[修正表](../fix-records.md)・[開発フロー](../development-flow.md)を保持する。

## 原因と適用範囲

新返却の正常Perception商品Scene31枚を同inputの旧121/出荷122で比較し、全Scene・全6112B packetが同値。FULL停止3件は全て正常OK/UNKNOWNを元 `min(source150ms, worker100ms)` Dより前に実採用し、PAUSE既知ACK→耐久保存→GOODS終了した。新21/4の回帰、producer未実行/未採用、時間切れ、独立Cによる完全NEG拒否ではない。各実配置は二看板であり、122の単一看板21/4とは別の正構造である。

| 実run/source | 出荷122の正常結果と拒否 | 正の校正根拠 |
| --- | --- | --- |
| 周1/f5a3/235 | policy2、BOARD/ROWS258。fullface自体 `[468,30,29,29]` は非HUDだが、探索用ROI `[464,24,36,40]` だけが既HUD `[429,0,465,45]` へ1px重なり `structural_face=0`。原row `(482,44)/(482,38)` は同整数world列 | fullface575px/右fragment260px・同top30。exact3ITEM/halo/下3FLOOR・選択fullrow両capは成立。fragment rowの左capは不成立のまま保持。直前234は既policy9 NEG/C1で、別sourceの採用履歴には置き換えない |
| 周2child/b6cb/106 | policy9、ENDCAP16。右cap25×25は正FLOORだが上半25×12の元材質条件を外れる。旧chroma/moment/121diagonalも拒否 | 固定の左12×25＋右13×25が全625画素を欠落なく覆い、両方で元floor/90%可視/bright条件が成立。105/108は既policy4 NEG/C1だが106の証明へ流用しない |
| 周4/4a98/169 | policy3、ROWS256。原row `(301,117)/(302,117)` を2列と数える。既 `offer_pair_components` はleft完全一致を要求 | 実同2看板・同整数world/同3ITEM列の1px横alias。両rowのexact footprintと両capは成立。168も同じ停止条件 |

実採用のD残は順に78.637/27.391/80.549ms。周3/636e/119はPARTIALの正常UNKNOWNで全3未観測を保持し、後段cycleのkernel書換えと分ける。別担当の上端投影DATA観測へ分離する。成功66c8/148は既policy15の正常完全NEG/Ring証明1/own-anchor C1→durable→実RS15/既知ACK→新floor168/169→childを保持する。

Git外の出典・PNG/RGBA/Scene/packet SHA・原metadata/prefix/clock/D/採用は `analysis-evidence/test123-goods/{cause-calibration,normal-results,guard-results,remaining-cap-results}.json`、右capは同 `cap106/cause-and-proposal.json`。原画像/packet/private記録をGitへ置かない。未知の旧job/private mode/counter/historyは補わない。

## 追加する正の二看板証明

旧完全陰性を先に返し、最後のUNKNOWN前にtarget-only専用の別coverageを加える。旧21や19/20/15の条件・閾値・順序を広げず、UNKNOWNを直接NEGへ変換しない。

- 実SIGN成分は正確2個。29〜30pxの完全faceをmasterとし、もう一つは既完全faceまたは同top・有限の短いfragmentとして、元componentのbbox/countと72px間隔へ結ぶ。余剰看板を捨てない。masterの実bbox/寸法/count/containment/中心の全元条件を要求し、実bboxと商品帯は元HUDから完全に外す。探索用36×40 ROIのHUD交差を、実観測faceの欠損へ代用しない。全体HUD規則は変更しない。
- seedは重心ではなく元observerと同じbbox中心である。exclusive bboxからside別に `left=x0+width/2−72*side, sy=y0+height/2` を整数演算でexact復元し、価格filterを使わず2board両seedのunique期待集合を作る。左faceが完全29〜30pxならそのseedをmaster、左がfragmentで右が完全なら右seedをmasterと決定する（他はUNKNOWN）。新22のrowはmaster先頭/selected_row=row_index=0、残seedは物理left/right side順の決定的な順序とする。Ring/Cが同じbbox/count/完全face規則から期待row配列を再構成し、row_countと全座標を欠落・余剰・重複・並べ替えなくexact比較する。提示rowの所属だけで完全性を判定しない。
- 元observerの全rowもその期待集合へ閉じることを確認する。旧observerの価格18以上によるrow_count/順位を新22の完全性に流用せず、価格不足で旧rowが無いseedもこの実bbox由来の独立探索へ含める。別セル/別看板/不正seed/元余剰row/上限超過はUNKNOWN。両seedは同整数worldセルを要求し、1px横差・fragmentの実中心差を固定許容値だけで一律許可しない。新fieldやmerchant欄の転用は不要。
- masterは元 `offer_footprint_scene_row` の全230セル、正確3ITEM/余剰ITEM0/全canonical halo、下3FLOOR、左右FLOOR、非HUDの180×67商品帯を要求する。全3本体の元明度支持も実測する。各aliasには同world/Scene footprintと全target/名前探索を要求し、masterのcap値をaliasの材質値へ偽装しない。商品名・価格・登録種類は必須にしない。宝箱の中身は判定しない。
- 全期待rowの5cell全整数pose・広い名前unionを既kernel/閾値/各sweep内のvisit順で最後まで探索する。新22のalias間順序は上記の決定的なrow順とする。partial配列はmaster両外2件を先頭、その後に各aliasの両外を新22 row順、最後に元alias union外partialを元順tailとして保存する。C/Ringがbboxから再構成した期待rowごとに両外の座標/slot/strip/proofをprefix `2*row_count` 件へexact比較し、alias行＋その両外をcountごと丸ごと削るpacketも拒否する。全体上限12・欠落/余剰/重複/順序変更/不正座標拒否を保持する。対象/候補/名称vetoは先に返す。新certificateが表現しきれないalias/partial/tailはUNKNOWNとし、落として通さない。
- masterの両元25×25capは旧完全証明を先行保持する。代替は今回の上半材質不成立だけに限定し、元full FLOOR/下半FLOOR・全体90%可視/bright/priceink/texture・ownScene正FLOORを保持した上で、固定・非重複12×25/13×25の双方に元material_floor/90%可視/面積比例bright上限を要求する。任意分割選択/ROI移動/閾値変更/未被覆quarterの免除は0。新packet内の代替capは最大1個とする。

## 新tag・数値表現・独立consumer

`policy_version=board_mode=22`、`layout_version=5`、`NG2_RING_FLOOR_VERTICAL_PROOF=3` を専用にする。現Ring/C/Swift/Python/testsの未使用検索をGit外 `new-tag-search.json` へ固定済み。構造体/fieldを追加せずRingResult6112B・POD/ABI/API/profile3を保持する。

全2物理boardの実bbox/countは既board欄、master/row_index/全元alias/partial/tail/実item_boxes/strip/実cap全体は各元欄へ保存する。`observed_items=non_target_items=3` はraw3存在と全target sweepを示し、商品登録ではない。`unmatched_items` は実測値を保持する。価格を用いない新tagだけ `observed_prices=unmatched_prices=0`・全price_boxes/name_boxes0。merchant/glyphを使わないためmerchant全欄・sign_iou/coverageは0。価格不存在や名前確認済みを意味しない。

旧完全capは `floor_full/upper/lower=1`。新capは実full/lower=1を保持し、`floor_upper=3` が「元上半材質は不成立、固定vertical全被覆で別証明」の専用markerとなる。単なる上半FLOOR1への書換えではない。独立Cがmarkerだけを信頼しないため、**新22/5下だけ**次の既存配列をvertical実測値として明示解釈する。

| 既存field（cap side別） | 新marker3時の意味 |
| --- | --- |
| `sign_boxes[side][4]` | 左12×25の実r/g/b/black_count（glyph bboxではない） |
| `board_edge_counts[side][4]` | 右13×25の実r/g/b/black_count（board edgeではない） |
| `board_corner_counts[side][4]` | 左bright/右bright/左spread/右spread |

patchのcount300/325・bboxはmaster capから一意導出し、面積300+325=625、左右black合計=元cap.black_count、左右bright合計=元cap.bright_countを要求する。RGBは各0..255、blackは各0..count、spreadは元1を要求し、各patchの元material/90%可視/bright/textureとglobalcap全条件を独立に検査する。median RGBの加算一致は意味がないため要求しない。旧完全capでは上記配列は全0。`board_exterior_count` は0を保持する。専用のvertical-stat accessor名を使い、marker3下の配列をboxとして誤検証しない。旧policyに新配列/markerを混用しない。

`ng2_ring_negative_certificate` と `cycle_negative_witness` に専用dispatch/validatorを加える。Cは自分のcycle_anchorのFULL/FLOOR、exact3ITEM/halo/下床/同master world列・非partial/非candidate・全packetの数値/期待全rowset/各alias両外prefix/tailを再検査し、producerのverdictやSceneを信用して陰性にしない。独立Cは画素を再取得/再分類するものではなく、immutable frameを読む正常producerの実component bbox/count/画素探索値が既source/job/ownerへ結ばれている前提で数値・自己anchor構造を検証する。この範囲を原観測の独立復元と呼ばない。既source/job/run/prefix/owner/世代/clock/Dのguard、耐久保存と通常PAUSE/RS資格を維持する。商品担当のC所有は新negative helper/dispatchだけで、control123の投影DATA helper/callerと重ねない。

Swift `NG2CycleWire.certificate/boxes` はint tupleをJSON配列へ出し、`NG2CycleSpool` のlevel5を含むpayloadはopaque canonical JSONとして保存する。checkpoint/terminal、iSH collector/ZIP/recoveryは既int/arrayをそのまま保存し、商品判定を再実行しない。全consumerを検索し、このmarker3を旧box解釈する経路がないことと新専用Ring/Cだけが数値意味を解釈することを固定する。新field意味を明示し、実3.9で22/5・価格0・marker3/実配列の保存/復元bytesを確認する。未知tagを旧policyへ正規化しない。

## 実装・検証の順序

同immutable呼出の `OfferSweepProof[4]` を渡し、元row-index/row座標/strip/完了資格が完全一致する既済み探索だけ再利用する。新22の決定的な順に対して元indexが違えばnoReuseとし、旧proofのindexを書き換えて信用しない。原3sourceではmasterは元row0なので、特にD残27.391msのb6cbで完了済み主row探索の再利用を優先する。新alias/tailの未完了画素だけ元checkpoint付きで走査し、全出口で有限memoを解放する。追加pose/bound/visit/checksの実数とreuse hitを記録する。noReuse/localMemo有無を比較し、実走査数以外の証拠値・候補・pixel/word順・checkpointを保持する。

source150ms/worker100ms/minD・取消/所有・UNKNOWN無再送を保持する。原rawの全alias既kernel校正はnon-targetで完走したが、Linux追加368checks/約25〜28ms、b6cb追加185checks/約22msを元iPhone費用へ足し引きして合格にしない。原sourceのcapture/worker時刻の差を保持してhost単調時計へ原点だけ平行移動し、元100/150ms内の通常producer完走→独立C1を原3sourceで実clock校正する。固定時計/元limits延長/終了後の時計差し替えで合格を作らず、実iPhone消費は次の実機まで未確認とする。

GO後、まず出荷122へ原235/106/169の「通常producer→完全NEG22/5→Ring証明1/own-anchor C1」を期待する意味Redを置く。compile失敗や手加工NEG/cutをRed/Greenへ数えない。最小実装後に同原inputをGreenへ結び、原66c8成功全6112B、既5成功・19/20・新21原画の正常packetを保持する（現122の8原画再producerは既SHA一致/Ring/C各1を確認済み）。原119はPARTIAL UNKNOWNを維持する。

予定公開fixtureは `tests/test_native_two_sign_goods123.py`。測定seedの縦fragment/横1px alias/価格非表示でも全bbox seed保持、固定vertical全域、未観測3商品/halo/下床/真正extra board/別grid/actualHUD、alias外縁とtailの対象・名前候補、alias行＋対応両外の丸ごと削除/期待row・両外のmissing/extra/duplicate/reorder、markerだけの偽装/片側patch欠落・重複/面積・合計矛盾/各field改竄/patch範囲・境界/旧tag混用、元D前・等号・後/取消を確認する。全alias両端を保存する表現とconsumerを同時に検査する。正常producer→公開durable→通常RS資格は既lifecycleで別に確認し、実iPhone成功と区別する。

直接関連21/19/20/既二看板・consumer・保存をrootが選択し、独立差分レビュー1回→nativeビルド/封印/完全source同一性確認へ進む。通常入力・Runtime構造・取得/queue境界は変えず、無関係な全world/全故障試験を追加しない。実機の商品判定/RS/次周回・毎拍/速度は次の実機返却まで未受入。

## 実施と限定した性能差分

rootの正式GOと独立planレビュー後、原235/106/169の通常producer期待は出荷122で3件の意味Red、公開新8件もRed11/error0。新22/5の最小実装は原3件で通常NEG/Ring証明1/own-anchor C1となり、新8＋直接旧11の19件がGreen。全seed/alias両外削除・vertical統計・候補・期限を確認した。独立レビューで発見したrow0算術前boundsとfresh/reuseのword_slot差は、追加Red→新22限定の最小修正→同19Greenで閉じた。旧5成功＋19/20/21の8原画、66c8成功15、636e未観測PARTIALは各原6112Bを保持し、実3.9.25の22/5/marker3統計の保存・復元も同値。

b6cbの原時差をhost時計へ移した校正は新alias primary約21.6msが主体だった。新22だけ、元30probeの包含条件をx/y別の正確なbitmaskへ分け、ANDしたbitを元と同じ昇順で調べる挙動不変の `binary_primary123`/専用alias helperを採用する。元kernel・bound・全pose/visit/checkpoint・ready優先/候補順を変えず、旧121/19/20/21 helperは全bytes保持する。原3全6112B、全pose/bound/visit順hash/checkpoint、10alias target＋tail word1、取消/期限6cutは同値、独立差分レビューはP0/P1/P2なし。新8のGreenを最終sourceで1回確認し、旧直接11は無変更helperと前段19Greenを根拠に再実行しない。

非重複の交互3対ではb6cbの元D内producer＋C完走はmask2/3、基準1/3、中央値は約2.16ms改善したが、`allwithin=false` のまま保存する。Linuxの平行移動診断を全期限安定達成・実iPhone費用/速度へ読み替えず、3/3になるまで反復して選別しない。cache確保だけを省く案と旧offerへexact-bound memoを延ばす案は不採用。元source150/worker100/input10ms/Pと全未確認保持を維持し、次の実機で商品判定→実RS→次周回を評価する。
