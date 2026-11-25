# TEST121: 商品可視後の対象なし証明を限定して補う

2026-11-25（日本時間）。出荷TEST120/CODE723c1c6（Ccf471/Nav6b4/Perception19ff/Ring7ef61f）を基準とする採用案。独立設計f18572e3・rootの限定GOを受領し、**以下の具体述語/数値を正式assertion Redと実装の前に固定する。** 原画像・元sourceは変更しない。merchant FGの追加案は採らず、相対glyph案一本に絞る。

## 1. 原因と元の成功

7ZIP/4run/99PNG/117記録は全照合済み。実順は3a4a、5572→a084、18c0。a084/source215と18c0/source125は正常UNKNOWN/incompleteを元D前52.925417/81.867833msにC採用し、PAUSE ACK・耐久保存後にGOODS終了した。未分類、返却遅れ、価格OCR/名称確認待ちではない。未知を陰性にしなかった判断は維持する。

- a084: 同じ右看板が文字により260/210画素の2非連結SIGNへ分かれた。左の完全な看板を含む3成分となり、policy6は右下片を採り右上片を余剰看板とした。同じ右枠へ数値上だけgroupした私有反実仮想cutでは商品3/価格3に進むが、次に左endcapの上半床証明が落ち、旧producer/consumerとも陰性0。
- 左capはfull中央値(36,21,20)、上半(43,25,22)。上半の元式は2365<=2355の10差で不成立。旧offerの色相比、旧momentのB:R生sum差3.1428397%も成立しない。full・lower・UL・LRは元floor式で正、URは負。原3%/floor閾値は変更しない。
- 18c0: 7GOLD/正確3ITEMとhalo、単看板・両endcapは成立。既policy7のmerchantは最高.919073510/.891812865、SHOPは95/104・余剰黒0で、ともに.94/.95未達。faceの30行自体は元structural_faceを通る。中心±2の5aliasでも改善しない。merchantの頭部124支持点は全一致する一方、背景等74点が不一致（うち38点が黒、白文字化0）。glyph欠落9画素は暖色で元<60黒条件外。全体の位置ずれや未登録商品が原因という根拠はない。

重要3sourceの旧119/120通常Scene・Ring全packet bytesは同じ。FR096-SHOP-AUTHの別構造proof、FR105-SIGN-FRAGMENT、FR109-OFFER-WITNESS、FR117-SINGLE-BOARD-FOOTPRINTの削除回帰ではなく、今回の成分分裂・floor支持・単看板の条件が既適用域外に残る。Cの通常FULL MOVEはACK observed214/124とjob source215/125のID不一致でも拒否されるが、この条件を緩めず、本案は通常producerの正しいNEG→独立C採用→耐久RSを主対象とする。

5572/source283は既policy17/layout1の正常完全陰性→元D余裕65.129834msで採用→durable→実RS24→新floor306→childを確認。unmatched_items=2/名称false3も合法な成功である。元TEST119のpolicy9/7/4、TEST118のpolicy17も保持する。

## 2. 同一看板の正のgroup

元partial_slots、全成分からのpositive探索、元row/partialの数値aliasは消さない。coverageだけに別の物理看板資格を置く。元4隣接観測でちょうど3成分、一つは元structural_faceを満たす完全anchor、残り二つは各150画素以上/元size範囲内で、同じx端/中心を持つ別成分とする。unionの幅/高さ/上下端がanchorと同じ29または30画素のfaceに閉じ、上片は上端・下片は下端へ接し、bboxの縦重なりが正、各fragmentは真の部分であることを全ANDで要求する。和countはunion面積以下、全pixelは観測ROI内、pair中心差は元72±2、元bottom_aligned_pairも成立、partitionは唯一とする。左右を反転しても同じ条件。今回の右unionは[359,103,29,29]/470画素である。

離れた第3看板、外部へ続く成分、異なる中心/上下端、不明なunion、二つの物理pairは拒否する。既bottom_door_scene_rowと正確offer footprintの両方を要求する。groupを理由に余剰物を単に捨てない。各元aliasの5cellと広い名前unionを既dense sweep/word vetoで確認し、どこかのTARGET/CANDIDATEを保持する。

## 3. 固定cap内の別の正のfloor証明

既endcap/offer/momentが通る経路はそのまま先に使う。別証明は同じ固定25x25で、fullとlowerが元floor式で正、upperだけが負である場合に限定する。UL12x12/LR13x13は互いに非重複で元floor式/textureが正。upper/URには元r>38..52・G/B上限・色差/textureを保持し、負のblue下限gapだけをPerception既別証明と同じ1..77へ限定する（URが通常floorならその正証明でよい）。whole/upper/UR/UL/LRの90%可視と面積比例のbright<24/625、whole price ink<18、同Sceneの正FLOOR/保護/店構造を全ANDで要求する。全target探索は維持する。

これは未検証の別証明であり、upperを通常floorだと偽らない。対角patchの欠け、別色、暗い/未観測の隠れ商品、gap0/78、Scene不一致を拒否できることを読取校正/設計確認する。既UR/LLや3%を広げず、新group専用policyで一方のcapだけに適用し、他方は元endcapを必須とする。両cap同時の新証明へ広げない。

## 4. 単看板の描画差と正の認証

18c0は正のSIGN背景と元SHOP形状の相対contrastだけを追加する。global黒<60、元4glyphの全形状/探索ROI/.94/.95、元merchant2phaseは不変。一つの元4隣接SIGN成分・150画素以上、29..30の完全face、元structural_face、glyphboxの完全内包を必要とする。その成分だけのR/G中央値（rank n/2）、同中央値の元SIGN色資格から、2*pixel_R<=median_R AND 2*pixel_G<=median_Gで観測glyph maskを作る。欠落/余剰pixelを全て含め元IoU/coverageを計算し、pixelを塗り替えず、都合の悪い点を除かない。

比1/2/元支持150/元ROIは評価前の私有候補b9f1388bへ固定済み。元543成分から137/144・coverage1のauth-only校正が成立し、glyph全消去/14支持点消去/背景なし暗板は拒否。最初のbbox内非連結pixel混入を訂正したattempt1も保持する。これは新正常producerやC採用の成功ではない。偽SHOP、白文字重なり、部分glyph/face、少数/異色背景、target/candidateを含む全条件の確認はまだ必要である。

この別認証にも、既single_sign_scene_rowの5セルsolid side＋対向2post/同段入口と、既offer_footprint_scene_rowの全3ITEM・下3FLOOR・全Sceneの正確halo/余剰ITEM0を結合する。一つの完全SIGN、両側の元endcap、元価格3/商品3/余剰物検査、5cellと全aliasの対象画像/名前vetoを全ANDで要求する。構造だけでmerchantを削る変更はしない。未観測壁/商品は補わず、十分な新認証が成立しなければUNKNOWNを保持してrootへ返す。既physical board_frameも今回は不成立で、成功した代替には数えない。

## 5. 数値policyと独立Cconsumer

新単看板認証はpolicy19/layout1/board_mode19とし、実relative glyphのbox/IoU/coverageをsign既fieldへ保存、merchant値は0、単看板の実box/countを保存する。capは全て元proof値1のみ。group＋別床はpolicy20/layout1/board_mode20、実unionの2box/countを保存し、一方のfloor_upper=2を上記別証明、lower=1、他方のcapは元値1だけとする。旧policyへ19/20/値2を通さず、producerとC双方が新tag/数値の全ANDを検査する。

新19/20だけ、先頭2partialの既5cell証明に加え、全元aliasのunion外にある元partialを末尾へ順序どおり残す（2..12）。超過/重複/不正座標・box・非finiteはUNKNOWN、切捨てなし。末尾の対象/候補/名称vetoも優先し、末尾を追加商品被覆の根拠へ転用しない。旧policyのpartial==2条件は維持する。最初の実装で全元partialの5cell内所有を要求した過剰guardは私有attemptを保持し、root承認のこの限定訂正を実装前に固定した。

field/POD追加なし、API/native ABI/strideは保持する。3.9 collectorの静的確認では既intをそのままwire/recordへ保存し、新enum検査追加は不要。承認後の新producer packetで実3.9の保存/ZIP/recovery原bytes保持を小fixtureで確認する。旧118/119/120履歴・validatorは変更しない。field/サイズ変更が必要なら別設計へ返す。

Ringの新producerとng2_ring_negative_certificate、およびControllerのcycle_structural_witness/scene検査へ同じ限定資格を独立に実装する必要がある。Cは自分のcycle_anchorの全ITEM/halo/正床/GOLDと、全packetの数値・box・alias・候補・価格・capの範囲を再検査する。producerがcompleteを返しただけでは採用しない。merchant/SHOPを満たしたと偽造しない。既negative/durable/intent/RS関数は変更しない。

## 6. 所有範囲と保持素材

候補の製品範囲はNG2Ring.cのcoverage/限定raw proof/negative consumerと、NG2Controller.cの商品negative witnessだけ。policy共有定数が必要ならNG2Ring.hのenum追加を明示するが、struct寸法は変えない。runtime担当はquiet_gate_scene周辺だけで、C全体の上書きをしない。

Perception、Navigation、Beat、Runtime、kernel、canonical15、既feature/bank/G1/R12、価格/target閾値は変更しない。source150/worker100、元D/P/10ms、取消/owner/prefix、UNKNOWN無再送、初回RSと候補保持は保持する。追加観測MOVEのhistory資格を本案へ混ぜない。

## 7. 校正・Red/Green・関連範囲

計画の独立確認後、まず私有read-only probeで原sourceの新しい正述語が全ANDで成立するか、余剰本物/欠け/別色/候補が通らないかを確認する。反実仮想cutは正常新producerのGreenへ数えない。次に出荷120の正式assertion Red→最小実装→Greenへ進める。

新caseはgroupの正例/本物第3看板等の拒否、固定floorの正例/境界と各支持欠落、単看板の完全offer正例/各構造欠落、全aliasの対象/候補保持、Ring数値witnessと独立Cの改ざん拒否、公開Cでの正常NEG→耐久→RS資格を必要最小に選ぶ。元原画215/125が新正常producerでNEGになり、対応Cconsumerが採用することを別々に確認する。元119/118/5572の成功packetは旧branch先行・extra処理0/全bytes同値を確認。固定機同条件old/newの原215/125 walltimeを記録し、新19/20の完全alias sweepは同じimmutable invocationに限り(canonical sprite index, exact x, exact y)→元binary_pose_boundのdoubleを局所memo化する。4aliasの有限unionから最大184x87、積のoverflowを検査しheap/validityを全exitで解放、allocation失敗は元正常計算へ戻す。元binary_primary/kernelはbytes保持し、全座標の訪問順/先頭候補/実時計checkpoints/全alias wordvetoは変えない。cacheなし同sourceとの全packet/訪問domain・counter・全7caseの同値を確認し、flaky時間assertは加えない。元worker100/source150を変えない。無関係な全bank/whole worldは再展開しない。

native変更後のcap121/client識別・選択関連host/Py39・実IPA/compiler/seal/全source同一性はroot工程で必要範囲を決める。Runtimeや送信境界を変えない限り、新しい全Runtime集合を自動で配布条件にしない。

## 8. 未確認と判定点

計画固定時点の製品はUNKNOWNのままであり、新NEG、独立C採用、実RS、iPhone到達率/速度は未実証。限定GOの範囲で正式Red→最小実装→Greenを進め、成立しない述語はrootへ返す。元job1や未出力private mode/history、将来の画像を復元したと主張しない。生資料/Scene/診断コード/反実仮想packetはGit外のtest121-goodsへ保存する。
