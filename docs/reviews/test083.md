# TEST082受領とTEST083

2026-11-12（クライアント日本時間）。[計画](../plans/test083-first-gold-goods-view.md)・[独立レビュー](test083-independent.md)。基準 `3db9d9d244084f4fcc95637717f9cb073b57571d`、TEST082/build137。raw/Scene/JSON/解析ログはGit外 `analysis-evidence/received082` / `test083-*`。

## 実機の結果

添付順の2/3件目と実順は異なり、started_ns順で照合した。

| 実順 | run先頭 | native終了 | inputs/moves/restarts | 原PNG/画像B |
| --- | --- | --- | --- | --- |
| 1 | 7eb9c53d | no_path12 | 11/10/4 | 20/5,984,691 |
| 2 | 156d2950 | goods1 | 10/8/10 | 20/4,932,363 |
| 3 | d50399c6 | goods1 | 6/4/2 | 20/4,885,152 |
| 4 | 41891edf | movement10 | 4/3/0 | 20/5,021,592 |

4ZIP/80原PNG・計20,823,798画像BのSHA/ZIP・PNG chunk CRC/PIL verify-load/896×414/現API16閉schema/client_load/export全offset・hash・prefix・cursor/test069実公開gateを確認。全resolved/terminal/drained/paused、host error/cancel0、capture failure/timeout0。全server build表示は2026-11-11 16:19でbuild137の記録と整合する。実1のcmd12だけdispatch too_lateがあるが、後続MOVEは成功しており最後no_pathの直接原因と混同しない。

正常見送り判断sourceは実順4/10/2/0、16/16保持。全選択PNGにmetadata/hash/安定prefixがある。実2の古いcapture20/49/81だけnative bounded ring行がなく、取得行を再構成せずexport metadataと分ける。omitted_image_count計719/参照省略79で全取得画像保存ではない。全画像/ZIP回収は完了しているので追加回収や082再実行は不要。

到達は**2/4**。実2の原494はstable prefix31/非inflight、125/50/13の全3商品。実3の原199はstable prefix13/非inflight、125/75/50の全3商品をrootと作者が元画像で視認。price3/item3・元HUD除外も成立する。指輪の対象識別/通知成功を意味しない。実1は一部の原画で3商品の価格を目視できても下部HUDと重なるため、商品確認完了には数えない。

native入力begin間隔は実1/2/4に各1区間の約1.03/1.04/1.05秒、他は大半約.51〜.54秒、実3は全5区間.515〜.531秒。入力間隔をゲーム受付時刻や実毎拍の達成へ読み替えない。開扉は歩数に含めない。今回は可視化と停止の二原因を優先する。

## A: 部分商品を見せる位置

実1は272でgoods PARTIAL、原285以降もPARTIALを維持した。原297/343はprice3/item3でも商人signから見積もる商品矩形がheart/footerの元粗HUDに重なり、VISIBLE拒否が正当。309/321/332では実際に順に価格が隠れる。LEFTを続けても商品y≈345/価格y≈376は変わらない。

source272→285の実LEFT1はpublic ng2_entered_gateがworld(-5,0)/LEFTの実入店を証明。既strictMOVEDイベントからの座標/visitsとこの入口を使う公開ng2_chooseでも285..332全てLEFT/reason8、343はno pathとなり実記録と一致する。空入口の仮定や私的Controller状態を実再現へ混ぜない。

要因は二つ。次DOWNの実cellは商人HP表示でmedian44/23/16〜49/24/15等となり旧DIRTへ入り、床限定経路にならない。さらにScene copyのDOWN床だけ/店内帯をFLOORと仮定しても旧chooserはGOLD距離優先でLEFTを選ぶ。このcounterfactualは因果の切り分け用で、実Perception出力や入力権限にしない。VISIBLE latchを無視した不具合ではない。

新床候補のGit外prototypeは、既DIRT/fullR39..52・G45..68%R・25%R < B < 44%Rと、固定upper12行300px/同36px tile内outer-lower5行125pxの非重複床witnessを要求する。両witnessはR≥16と元floor palette/texture、full625+追加125の全750pxをHUD除外する。HP/PARTIALラベルから床を推定しない。新80枚の8画像35セルと旧97枚の1画像1セルだけがDIRT→FLOOR、全36を元画像で視認し、全177の非tile bytes/商品/保護/拍/署名等は不変。量子化082の3proofや元paletteを変更しない。これは設計の校正段階で、製品/新実機の成功とは分ける。

## B: 初金露出中の実移動

実4のcmd6はLEFT/source104→113..126で実1歩、ACK後8UNKNOWN、reference補助不適格のまま元評価回数上限で停止した。最終CreturnにもvisualD約1.96秒が残り、host期限で止めたのではない。082の新C拒否診断は未発行stationary独立proofが対象で、このACK待ちや別のactual tick失効を対象にしないためtrace0は仕様どおり。

source104はFLOOR/CLEAR/金0、後続では初めて金1(-3,-2)が現れてCANDIDATEとなる。元projection(-4,-2)はUNKNOWN。実115は全旧STONE6/非共線DIRT・全9translationの一意unitを保持し、raw9px .57487/gap .27673、原075 worldBlur396/1bad・固定帯230/166、独立phase unit .536690/.535891と有限競合gap .408775/.292438を満たす。stable prefix6、取得開始ACK+89.2115ms、前113から87.8846ms>period/10で元attempt2・visualD内に適格。

既082の両CLEAR補助だけでは0→1金露出に適用されないため、計画Bの別helperを末尾へ追加する。最初113の8px/gap不足を拒否し、117以降の一部raw runnerup INFも従来どおり救済しない。geometry単独/ACK単独をMOVEDへせず旧075の全pixel条件・元期限/8評価/予算を維持する。

## 前回の未解決との区別

旧081実5/source341→360は金1→2で今回Bの0→1と異なる。今回あらためて既082 C4で原画像を再解析し、前回Sceneと全bytes一致を確認した。追加検討した原5依存gradientも225支持/18bad・帯103/122で総300不足、右phase unitは+INF。fixed52は239/23bad・86/153、worldBlur162/2bad・29/133で不足する。競合支持が300未満でもunit自体の支持不足を成功にせず、現資料の既証拠の単純ANDでは未解決とする。製品/試験編集・再compile・単体重複は0。別のpixel証明設計が必要で、旧runの回収再実行を要求しない。

## 新単体と最終固定source

新規はA1五件/A2六件/B五件の計16methods、全て作者Green。A1の初回fixtureは下帯125の二色差4が分散3.999744で旧texture4未満となり前提不足だったため、そのRed/failed Greenをsupersededとして保存した。製品閾値を変更せず差6の実textureへ修正し、両固定witnessの公開FLOOR/中央値/分散8.999424以上が先に成立する有効baseline Red→最小Greenを実測した。事前assertを加えた変更positiveだけ再検証し、残4methodsのAST/既Greenは維持した。最終comment変更は意味bytes不変で再実行しない。

A2は旧chooserの公開Red6subcases（compileclean/error0）→主Green。残りの迂回fixtureだけgoal(0,2)の誤期待を、全FLOOR/非保護/単位連結と両goal L0・経路長3対4を独立assertして最短(-1,2)へ訂正し、その編集methodを再Green。追加の境界/assertも編集methodだけ確認し、製品の最短path優先を歪めていない。公開Controllerは開扉ACK→実入店MOVED→PARTIAL framingのfull5(4,8,0,2,FLOOR)→1歩→次のDOWN予約をVISIBLEで取消まで成功し、元ticket/epoch/credit・購入/追加入力なしを確認した。Controller本文の変更は0。

Bは公開O0/strictO2×4方向で、全旧13stage UNKNOWN/原phase・blur/geometry前提成立後、期待unit対UNKNOWNのassertion Red8→主Green。残4methodsもGreenで、新5methodsをfreezeした。原104→115は新LEFT1、113と117..126はUNKNOWNを保持。旧B1/B2/13stage本文・順序・閾値はbyte不変。

最終Perception SHA `4f6737fbfcd68f6539a709df0444c9c3c4ead1d6e2dd1922b24efbda440ad19b`、Nav `99c0f6108f3f4b7bfb621ff8b5e9cfe1939ceef13603f1aeb0c7f61ce0a9f28b`。新A1 test `3ca6f68e79d63a34a132be7be7d854aea94fb846bc71f6c3d77e102c304abfd9`、A2 `377a9a3a2888ec4418a6041e0f64d1b55deb1f14a827357b37fa1d97f3b765df`、B `65912181f5084cd9304b02d713de2479fb4aa14a860049a797d5c873d4d9ca57`。

rootは同8C/H snapshotをC99・Perception/Nav strictO2/Beat・Controller O0で一度compileし、lib SHA `1353bb07eff4bb89cece589934836bd4a45568e74e55191520a09841e0249658`へ固定。原177枚/83適格ACK組を旧082との全pipelineで比較し、旧known59全部維持・回帰0、UNKNOWN24は実4/104→115だけLEFT1へ改善、他23維持。9原画36材質セルだけ4→1で全非tile bytes不変。これは校正/既記録の比較で、新実機の到達率ではない。

原実入店/姿勢/visitsを保持した新public chooserは、実1原285ではfirstLEFTを保ちながらgoalを(-1,2)へ変え、実際のそのLEFT後の原297ではDOWN/goal(0,2)を選ぶ。原343の旧no_pathもDOWNとなる。309/321/332は元経路の別位置でfirstLEFT/下goalを選ぶが、分岐後の未知実機画像へ読み替えない。単に全原画をDOWNへ強制したのではない。

fresh pinned Git clone→G1→seal/apply成功。22中Perception/Nav2変更・他20不変、manifest SHA `e4d3f75a8f83a478be22f634a8bc09f5ab3eaea7f9773d58c30f2fb09577e126`。Runtime048a…/Controller12d3…/core4・API16/cap15/client16/v2・G1/R12を維持した。最初のroot作業copyはgit archiveで.gitがなくseal setupが失敗したため、失敗copy/記録を保持して正しいcloneへ置換。意味Redに数えず、製品修正や試験の全体再実行で隠していない。診断scriptのimport path不足も修正し、製品/単体の失敗とは分けた。

## 単体・最終検証・配布

最終selectorは40methods/16scope（新16＋旧native20＋公開gate1＋self3）。selector自己3は初回Green、native/clientの局所重複実行0。device workflowは083 runnerへ参照1行だけ変更し、旧070/081 Mac保存stepsを維持する。Runtime/Controller/core4と旧082履歴の全bytes不変を確認した。

最終same-code host CI/IPA/5実物検証/固定公開GETはこの時点で未実施。同じ独立担当が製品・作者ログ・原画比較・seal・selectorの全差分を確認し、残P0/P1/P2なしで最終静的GO。codeと全sourceを固定し同codeの実ビルドへ進む。Runtime本文/旧保存fixtureは同bytesなので新Runtime Redを増やさず、旧意味Red133再利用と今回のMac Greenを区別する。
