# TEST083受領とTEST084

2026-11-12（クライアント日本時間）。[計画](../plans/test084-mouth-icon.md)・[独立レビュー](test084-independent.md)。基準 `87cd98b6046154b8a6eb8da39ada31b31afb595f`、TEST083/build139。raw/Scene/JSON/解析ログはGit外 `analysis-evidence/received083` / `test084-*`。

## 実機結果

添付順でなくstarted_ns順に照合した。

| 実順 | run先頭 | native終了/PAUSE | inputs/moves/restarts | 原PNG/画像B |
| --- | --- | --- | --- | --- |
| 1 | 1a4bc9f8 | goods1/1 | 7/5/3 | 20/4,570,099 |
| 2 | e33b6505 | goods1/1 | 7/5/2 | 20/4,519,048 |
| 3 | da1051fd | goods1/1 | 9/7/0 | 20/5,523,155 |
| 4 | d6528e8d | screen17/0 | 9/7/4 | 20/4,320,973 |

4ZIP/80原PNG・計18,933,275画像BのSHA/ZIP・PNG chunk CRC/PIL verify-load/896×414/現API16閉schema/client_load/export全offset・hash・prefix・cursor/test069実公開gateを確認。全resolved/terminal/drained/回収完了、host error/cancel/capture failure/timeout0。全PAUSEではなく3/4。途中dispatch失敗1は最後の停止の直接原因と混同しない。正常見送り判断source9/9保持。実4の初期16/45だけnative bounded ring行が欠損、export metadata/画像は正常。omitted669/参照省略46で全取得画像保存ではない。追加回収や083再実行は不要。

rootと分析担当が原239/219/183/379で3商品の全体と価格50/63/100、100/150/200、50/150/200、100/250/100を確認した。人目の可視4/4とnative GOODS・PAUSE3/4を分ける。対象指輪の識別/通知受入ではない。旧083新helperの到達への寄与は保持画像だけで証明できず、全4到達を新helperの成功と断定しない。

入力begin中央値は実順524.3/519.4/519.0/526.1ms。実1と4に約1.04秒の間隔が各1つあり、前者は未送信期限からの再計画、後者はvisual schedule。実2/3の間隔は約510〜530ms。最後RESUME/RESTART ACKから初入力は約2.55〜2.66秒。ゲーム受付時刻や恒久毎拍の達成へ読み替えない。

## 見逃した3画像

実4原16/45の上左口(-2,-3)は上300pxが黒、下325pxの非黒が296/307pxで、下帯medianが元floor色/textureを満たす。全体median4/2/1・7/2/3で元black入口のUNKNOWNへ入り、DIRT限定の旧082部分床proofに到達しなかった。元UNKNOWN・black入口・full各RGB≤12/full.spreadに限る別proofで、固定上≥95%黒/下≥90%非黒・R16..52/元floor色/textureを全ANDする。旧palette/gate/wood/082三proof・商品/保護・full625 HUD/alphaは変更しない。

実1原75の左口(-3,-1)/外(-4,-1)は観測FLOOR、上脇DIRT・下脇UNKNOWN（611/625px黒）、同初期壁列の壁3。旧floor-mouthの両脇壁条件だけで落ちた。元二壁/UNKNOWN口分岐を保ち、FLOOR口＋外FLOOR＋一方DIRT/STONE壁＋他UNKNOWN＋壁列3の別分岐だけを追加する。固定上/左10口・保護cross/FLOOR経路・初期world/有限探索を維持し、UNKNOWNを壁や金へ変えない。原75は初FLOORから356.380ms後、16/45の初FLOOR行欠損から200ms経過を推定しない。

A5/B5の公開RGBA/Scene試験は事前証拠成立をassertしたimmutable083の意味Red→初回Green、fixture訂正0。実機画像257枚で通常材質差は95個のUNKNOWN→FLOOR/67画像のみ。全95を原画で床と確認、既材質の上書き0。候補mask差は指定16/45/75の3枚のみ、既bit喪失0/他254維持。初期見送りsource43中他40も維持した。これは校正であり未知実機の評価ではない。

## 商品到達後の停止と診断

実4MOVE18 UP/source275は元窓内begin/ACK済みだが、最後はgoods0/paused0/screen17・PAUSE票そのものがない。原275は部分商品矩形がpause HUDに接し拒否が正当。原379は3商品/価格がHUD外だが、pause記号だけが商人表示と重なりUNKNOWNとなって商品scanへ到達しなかった。全HUD消失という作者の一時視認は、左右HUD cropが275/379で全bytes同一というroot確認で撤回した。

元36×36/neutral/55・85の二cutoff/IoU.8とraw→13px→11px openingを保ち、9px openingだけを末尾へ追加。元379は11px時306/388=.788660、9px時315/388=.811856で元閾値を満たす。gap埋め/padding切出しや商品だけからの画面推定をせず、旧NEG11の新採用0。公開C5は独立raw/r6/r5不成立の意味Red→Green、8px拒否・9px成立を確認。公開RGBAから同ACK待ちの商品latch→PAUSE予約/ACKだけでは未成功→PAUSE画像でterminal/paused成功と追加入力なしを確認した。

最初のstable ACK後285は原画欠損で、末尾379を最初の拒否画素へ代用しない。285はACK+34.159ms・元earliest後/visualD内、native終了は285.end+約4.005秒。379を適時MOVE creditや新版実機成功へ数えない。

Dは有効な現ACK MOVE待ち・元取得/commit期限・fullcommand/source一致・before FLOOR/現non-FLOORの最初の拒否だけを既STATE4/replan0の比較行へ残す。元SCREEN停止・event/MotionWait/Referenceの未評価/既評価値・入力credit/期限/予算を変えない。元非FLOOR cleanup後は重複なし。公開3methodsの意味Red→Green後、未開始MOVEの旧INITIAL_REJECTED3保全を追加した編集methodだけ再確認。元UNKNOWN評価attempt1も保つ。既Runtimeの比較画像priority/20枚10MiBをそのまま使い、次実機前に原285相当の保存成功を主張しない。

## 最終sourceと検証範囲

Perception `944a04b6a1c396769cfd283080ab325ee4ebde13188de144bf45a701764174cf`、Nav `51143732558a9430d974a7e18a2e366fc2b7a96b84e7a0245b5de8c49ef794cf`、Controller `1385374510f287b724217d96c4d633aec2cff566428652120cb1aa441863e807`。新native18作者単体Green、初回freezeまで旧意味試験のローカル重複0。CI141失敗1件だけの診断再現は次節に分ける。selector自己3は作者1回Green。選択CIは38methods/13scope（新native18/旧native15/client2/self3）。新C/Swift seam0、旧225 marker prefixを保ち新12を加えた237を実物で検査予定。

rootが同8C/Hを一度C99・Perception/Nav strictO2/Beat・Controller O0でcompile、lib SHA `e45b509633a0af80401146c4c8235600dd8abed840b91d545c06cc08f74b619f`。257原画のScene stateの旧UNKNOWN→FLOOR精密化は原379だけで、新たな68材質cell/商品/拍を解析できる。通常の95材質cell変化と分け、他非tile差0。最初の比較oracleがこの68cellを通常材質差へ混ぜassert失敗したため初版JSONを保持し、既結果をstate別へ分離した。製品/単体変更・再compile/画像再解析は0。保守的stable ACK-prefix組128の旧known88は全一致、motion差0。native終了又はsource+3秒を越す379組を除外し、私的な元visualDを再構成しない。

fresh pinned Git checkout→G1→seal/apply成功。22中Perception/Nav/Controller3変更・他19不変、manifest `c34c3b29d954ab9eee9afbb9c096d42100c0744c4761d6d5d7e933fbff9a46b6`。Runtime048a…/core4・API16/cap15/client16/v2/旧v1回収・G1/R12を維持。無変更Runtimeの新Redや全故障/worldは追加せず、固定保存Red133と今回Mac Greenを分けて使う。同一code CI/実IPA/5実物verifier/固定Release/匿名全GETはこの時点で未実施。

旧081実5最後の金1→2移動確認は別pixel証明が必要で未解決。新版の実機到達率/見逃し率・恒久毎拍/人超え・対象識別/通知/対象なし循環は未受入。配布時は通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認/PAUSEの5回と、全run別ZIP返却を依頼する。

## CI141で検出した旧fixture時刻の不整合

最初のcode066a4a…/run43138286437/build141では新18と先行旧回帰はGreenだが、既test_motion_wait_diagnostic_retains_each_eligible_capture_and_fixed_deadlineの第2観測が失敗した。10ms間隔でattempt2/lastcapture29を期待したのに、既resolve_moveはperiod520msの1/10=52ms未満を評価せずattempt1/28を保持する。FLOOR同士の経路なので今回Dのnon-FLOOR診断は呼ばれない。IPA buildはskipされ、失敗log/API/066aのverifier guardFalse snapshotをGit外へ残した。実物verifierは未実行。

immutable083全8C/Hと現084で当該methodだけを各1回実行し、CIと同じtupleで両FAILを確認。製品/閾値/元assert/選択methodを変えず、同method内だけ2/3回目を52ms間隔へ合わせた。元periodとretry52msの前提assert、初回後の旧10ms観測ではMotionWait/event全bytesが変わらない対照を追加し、attempt/lastID/fixedD/MOVED/creditの元assertを全て残した。変更methodだけ基準083/現084で各1回Green（2.205/2.086秒）、他単体の再実行0。fixture SHA `a3326511593a77b98d5e6019c99c0e7e56c8a6a3beff7e1959d2f6267f8ccdb6`。同じ独立担当が最小test-only案を確認し、製品8C/H/seal/C4/257原画比較は全不変なので再compile/再解析しない。失敗結果を成功へ上書きせず、修正後codeの限定CIを改めて行う。
