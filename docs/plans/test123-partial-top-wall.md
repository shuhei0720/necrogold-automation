# TEST123: 上端の商品投影と観測済み金壁railの穴を新DATAで確認する

2026-11-26（日本時間）。基準は出荷TEST122/build272/CODE `f5143e339a1e6efddb3c24a69dbea163fd1007de`、保存HEAD `c7e0944`。[要件](../requirements/necrogold.md)・[native契約](../contracts/native-control.md)・[開発フロー](../development-flow.md)と修正表のFR-105-PROTECTED-WALL/FR-106-TOP-PROJECTION/FR-107-PARTIAL-COMPOSITION/FR-118-UPPER-COMPOSED-REFRESH/FR-122-UPPER-MATERIALを照合した。rootが承認したのは原因解析と本短計画まで。**製品・正式試験・CIの変更/実行は次のroot GOまで0。**

## 原本から確定した停止

周3 `636e6203` はUP10が既知ACKし、原119の通常 `DOOR_OPENED` で開扉1・実移動4・位置(0,-4)となった。ACKは0歩で、開扉後のMOVE beginは0。原119/job1/prefix10は正常OK/UNKNOWN/incomplete、partial4/row0/partial-safe1を採用済みである。正常release `52274601100583` は元D `52274675758875` より74.658292ms前。source150msがDを決め、worker100msのWは `52274686289000` である。

原120は取得開始 `52274589634375` がreleaseより11.466208ms前で、通常OBSERVE_MOREの独立currentとしては使わない。原121はstart `52274628042208`、end `52274637416041`、analysis end `52274659385416`、実停止commit `52274659423083`。取得開始はrelease後、prefix10・stable・非inflightで、実commit時のcurrent ageは31.380875ms。元P `52277198688916` まで2.539265833秒、旧job Dまで16.335792msを残し、停止のvalidationはROUTE10である。最後のcycle `assessment_status=kernel` / `assessment_ns=stop` は `cycle_failure` による後上書きであり、正常producer未採用/時間切れではない。

原119→120/121は通常Perceptionで、row-4の連続5ITEMを全保持し、同列のrow-5へ5ITEMと説明可能な左右haloが現れ、同時に(1,-2)がUNKNOWN→GOLDとなる。通常Motionは元119から直接strict BLOCKED(0,0)、通常選択は双方UP/reason5/next(0,-1)FLOORで一致する。新GOLDは旧GOLD(1,-3)/(1,-1)に挟まれたrailの穴1セルで、原点とUPnextのcardinal十字外・双方のITEM/保護域外である。ただし**UPnextの旧3×3近傍内の対角**なので「既遠方金壁の条件へそのまま入る」とは言わない。

旧 `cycle_partial_top_roles` は支持された上端投影を扱えるが、残セルのquiet関係が新GOLDを拒否し、top projection growthも0となる。新GOLDだけを元へ戻した診断用Sceneではtop role ITEM2/growth1となるが、これは原画像でも正式試験でもない。反対に新GOLDだけでも旧changed-partialの3×3 guardを通らない。今回の対策は、単に既正資格2件をORする変更ではなく、**上端投影に伴って正に完成したrailの穴だけを新DATAへ渡す追加資格**とする。上端role内(1,-5)の旧GOLD→ITEMは既top役割の限定許可に含まれ、role外の旧GOLD/DOOR/ITEMは全保持する。

旧121/出荷122の原111/119/120/121 Scene bytes・関連8helper body・const cutは同一で、削除回帰の証拠はない。FR106/107の投影と材質の合成系列が別条件で継続した1件として扱い、同根因通算は不明。FR122のV2左右入口row+4/初回H1前材質はvariant0、FULL halo DATAはPARTIALでdata-scene0のため、今回の保持画像では適用外。

Git外根拠は `test123-control/original-timing.json` SHA `0369d1be024f0349cc62363b840d14ba0de82213c845073ab5da2bd20abf4788` と `test123-control/guard/receipt.json` SHA `15b82cb51cf6b3192b25c7bc543f48a75467c3611c44ea0104529da09d08aba4`。const contextのempty entrance/visits/非active route等は宣言した最小モデルであり、未出力private flag/stage/counter/slot/modelの実履歴を復元したものではない。新DATA以後の実商品画像と応答は未収録。

## 最小案と権限

既 `cycle_partial_static` / top役割 / 通常MOVE / 旧refreshの拒否を保持し、別のconst geometry helperと、OBSERVE_MOREの旧refresh失敗後だけに置く専用callerを提案する。通常PARTIAL sourceを新jobへbindする**DATA-only**であり、FULL専用mode2や現在PARTIALの旧empty-framing一UP資格は使わない。

geometryは同UP開扉のPARTIAL、双方の正確なITEM保護、固定row-4の連続ITEMと既top役割が説明する上端投影増加だけを要求する。全ITEMを新たな実商品と数えず、上端の直接下にある不変ITEMが支持する場合だけ扱う。残セルの追加差は1セルのUNKNOWN→GOLDだけとし、座標はUPnextの側方対角(±1,-2)、双方でその上下(±1,-3)/(±1,-1)がGOLDであることを要求する。新GOLDは旧/新の保護域外で、原点/UPnextのcardinal十字の全tileと保護は完全不変、両中心は非保護の正FLOORとする。他の旧GOLD/DOOR/ITEM、別の保護変化、追加の材質変化は拒否する。元anchor→currentの通常strict BLOCKED零、完全Decision一致を別に要求し、素材関係でMotionを合成しない。

callerは既yield/drain対応が有効なprofileだけとし、元job/level/prefix/owner、正常safe UNKNOWN/incomplete採用済み、partial1/full0、OBSERVE_MORE、pending0、候補なし、input_state0/current_command_id0を要求する。原UP10の既知ACK/開扉履歴は保持し、旧ACK/UNKNOWN/予約MOVE/未送信PAUSEを再解釈しない。新経路はSEARCH credit・state1予約中へ広げない。entry/lower/upper/current/retry routeなし、pause開始/ACK・durable・intent・restart不明・finish/terminal/storageなし、投影one-use未消費、共有DATA使用数<2を要求する。これらは正式公開lifecycleでearnedする資格であり、原private値の推定とはしない。

独立currentはID/start増加、start≥元release、同completed prefix・seen/currentの全metadata一致、end≤actualcommit、source150ms内、actualcommit≤元Pを要求する。旧source119のUNKNOWNを再ラベルせず、現在121相当のimmutable新jobを `cycle_latch` / `cycle_bind` の既所有/退役経路で作り、投影one-useと共有DATAを各1消費する。元P/hold/sync/level/位置/歩数/入力/ordinalを保存または短縮、旧slot/model/creditを撤回する。同level/ownerの既immutable HUD sample配列とcountだけは既 `cycle_current_bind` と同じ形で保持する。旧model/slot/epochを入力へ流用せず、新正常結果の後に別の独立currentを観測し、その通常 `add_sample` が新fitを成立させてから将来票へ進む。旧MOVEを救わず、新worker固有のsource150ms/worker100ms/Dを元Pでclampする。元Dや元Pを伸ばさない。

Runtimeの既 `classificationOutstanding=false` かつ `classificationDrainTokens.isEmpty` のdispatch guardと、classificationQueue→controlQueueの実return fenceをそのまま利用し、旧worker実return前に次worker/UIを発行しない。正常な新UNKNOWNは保持し、対象/候補は最優先で凍結する。新正常結果と別の独立current・通常strict零/最新床・通常fitから将来票が成立するまで追加MOVE0。完全陰性を証明し耐久保存・通常PAUSE/実ACK・既UI資格を経るまでRS0である。

## 正式Redと関連範囲の案

新 `tests/test_native_partial_top_wall123.py` を候補とし、公開C lifecycleで通常fit→実unit→UP開扉の既知ACK/通常DOOR_OPENED→row-4 PARTIALの正常safe UNKNOWN採用をearnedする。原119→121に対応した正のtop投影/rail穴/不変crossを宣言した手続きSceneで与え、出荷122の新DATA未発行/ROUTE停止を意味assertion Redにする。private stateを注入せず、新job/source/元P/hold/sync/一用/DATA枠・MOVE0を公開status/commandへ結び、必要なcounter確認は公開でearned後のread-only suffixに限る。原const cutのgeometry校正と手続きcallerを別receiptへ分ける。

新jobの通常producer→UNKNOWN保持/候補優先、別静止/currentで通常将来UP票→既知ACK/実unitまでを限定componentとして確認する。商品全可視/完全陰性/RSの未収録未来を原実機再現へ加えない。完全陰性/保存/RS連鎖の既直接関連を保持し、必要以上の全worldを追加しない。

拒否側は下段ITEM支持欠落/追加ITEM、top外のITEM・GOLD・DOOR喪失、余分/消失保護、穴2セル/別座標/旧FLOOR・DIRT・STONE・DOORから新GOLD/片側GOLD支持欠落、cardinal cross/next変化、別Decision、normal UNKNOWN/非零、古prefix/owner/job/ID/current metadata不一致、capture start<release、commit<end/source150超過/P前・等号・後、analysis<Pかつactualcommit>Pを含める。P等号の新DATA可否は既DATA契約の≤へ揃え、その後のworker/inputも個別に元Pを検査する。DATA枯渇・投影消費済・二度目/別jobでの再arm、未送信予約/begin/ACK/UNKNOWNの入力、pending/候補/PAUSE/durable/intent/取消を拒否する。

直接関連は106 top projection、107 partial roles、105 partial-wall、115/116 current PARTIALの指定methodを選ぶ。旧122upper material/FULL haloはhelper不変bytesと旧直接関連結果を根拠に再利用し、当該hunkを変更した場合だけ追加する。Runtimeは既dispatch/return guardのsourceを保持し、新しいrouteのdispatchを妨げる具体的境界が見つかった場合だけ対応する既callback fixtureをrootが選ぶ。全Runtime故障/巨大world/フルCIは既定にしない。製品実装と正式Redは次のroot GO後、独立差分レビュー1回、native実IPA/封印/実compiler/完全source/配布物同一性確認はroot工程とする。

時間境界の追加確認（root GO）: 原121のP残2.539265833秒に対し、新worker100ms＋次current31.380875ms＋新規2秒spanを全て待つと、原UP10のperiod520308009ns/lead150msの次NBの50ms準備を455227ns逃す。次拍の最早visualはPを391967824ns越える。この旧clear-model/count0案の不成立を校正として残し、sample履歴だけ保持する差分を正式Redにする。bind直後model/slot/epoch0・samples全bytes/count保持、新正常結果だけではMOVE0、独立current後の新fit・通常静止からUPの実unitまでを元Pのまま確認する。保持samplesは同owner/levelの既公開lifecycleに属する過去HUDで、未来/stale/別owner/level/元P超過に入力資格を与えない。原残時間/period/lead/ACK費用の平行移動componentと未収録未来HUDを区別し、最早例・予算100ms例・次拍へ遅れた場合の不成立を別に報告する。

rootの正式GO後の局所実装・作者確認: 旧helper16bodyを保持し、新const geometry/callerの2関数とOBSERVE_MORE call1行だけを追加した。公開earnedの最終新11methodはGreen、同凍結testの出荷122は19意味assertion failure/errors0、直接関連25methodもGreen/skip0。初版のUNKNOWN辞書不備とprofile前提不足、knownACKの既goods-first普通latchを誤禁止したoracleは訂正前logを保存し、有資格の実装前Redとは数えない。profile不足は最初の製品hunk後に発覚したため、修正fixtureのexact旧再Redという時系列を残す。sample保持deltaは別に製品変更前の12→0 countの意味Red1→Greenを確認した。

原phase/period/leadと原ACK/capture/analysis費用を平行移動した公開componentでは、current age31.380875ms・新worker100ms・新正常結果後の別currentから新fit→UPの通常実unitを、元Pより59.880231ms厳しいearned P内で確認した。unit時にearned P1.514994417秒/原mapped P1.574874648秒を残す。worker1nsの最早例は原P2.095182657秒残。未来HUDとその費用は宣言したcomponent入力で、未来phoneの保証ではない。DATA枠はearned0→1・返金/再armなしを確認したが、counter==2だけで拒否する独立公開earned caseは未構築とする。別levelのsample失効とowner境界は不変のreset_level/constructor/owner gateに結び、private注入や未実施caseの成功扱いはしない。作者freeze/owned hunk/原const校正・全初稿はGit外 `test123-control/implementation/final-receipt.json` に保存。実IPA/CI/実機改善はrootの次工程である。
