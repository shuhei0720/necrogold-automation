# TEST120: 未開始の進路観測と近い閉扉へのFRESH

2026-11-25（日本時間）。基準はTEST119/build266、CODE617fc248、HEAD1d9a0a4、Controller `ef0fffaf67c77d42dd4ddf32b614e4fd93b4e2115ae25cb5dd51c35414558448`。[要件](../requirements/necrogold.md)・[native契約](../contracts/native-control.md)・[通路契約](../contracts/passage-approach.md)・[開発フロー](../development-flow.md)・[全体計画](test120-device-failures.md)に従う。**計画段階。製品・正式試験は未編集で、独立設計レビューとrootのGO前には着手しない。**

## 1. 概要

実機で停止した3つの所有状態を分けて修正する。723の既stationary waitからは、新しく確実に観測した進路へDATAだけを引き継ぐ。ca2の未開始GOLD vantage方向変更からは、旧票を撤回して別の有限な進路再観測へ入る。c41の閉扉2セル先・正FLOOR1歩の露出には、既FRESH契約内の限定した地形関係を追加する。

723/ca2の引継ぎ画像だけでは入力を許可しない。固定した新DATA anchorへ後続の独立画像が直接通常零・同じ完全判断を示し、通常の拍fitと将来拍の準備が成立した後だけ新IDを作る。旧sourceとのUNKNOWN、旧票の未送信、ACK自体には移動creditを与えない。c41は別拍へ探し直さず、元の物理拍・not-before・D・ordinal・準備epochを保つFRESHだけに限定する。

## 2. 背景と原本による原因

11ZIP/7run/4campaign、170PNG/203記録は欠損なく照合済み。原本受領receipt SHAは `9144fc79750d2c468b55d6598d1bcf308a5ce1980985869435f775534ef26436`。原PNG→通常Perception→Scene→通常Motion/Navと拒否関数を、exact旧CODEdca8ca3/Controller535a9f0eと119/Controlleref0fffafで比較した。今回の3境界のScene bytes・該当helperは旧新同一で、119のlive clear/refined票専用対策が扱わない別状態だった。全7runの未保存private状態を復元したという意味ではない。

| run / 原source | 保存結果と直接の拒否 | 追加する限定関係 |
| --- | --- | --- |
| 723 root / 323、329、330 | DOWN25/source323は324で確実未送信へ退役し、既stationary wait中。323→329は通常strict零、323→330はUNKNOWN、329→330は通常strict零。DOWN/reason10は同じでも、完全targetが(-2,1)→(-1,1)となり`stationary_wait_scene`の`same_choice`がROUTE10で拒否 | 旧worldと現在位置を保持した、1回だけのDATA route handoff。元source323を零へ読み替えない |
| ca2 child / 67→69 | 最初のLEFTはACK後の通常MOVEDで確認済み。次UP4はbegin0。通常零だが完全判断がUP/reason8/(0,-4)からLEFT/reason8/(-1,-2)へ変わりROUTE10。既side/vantage openingの具体形に該当しない | GOLDを保持した直交進路の限定再観測。旧UP4を変更・再送しない |
| c41 child / 122→123 | 6実MOVED後、UPの通常strict零・同方向/同FLOOR target(0,-1)。閉扉(0,-2)UNKNOWN→DOOR、右bracket DIRT→GOLDと遠方DIRT→FLOOR等によりGOLD8。旧`revealed_approach_terrain`は閉扉3先・FLOOR2歩だけを扱う | 閉扉2先・FLOOR1歩の具体形だけをFRESHへ。開扉/入店/MOVEDの証拠にはしない |

723のPはsource323+FRESHの `89057931518208`。Wは記録された実commitと元periodから推定した `89056107696335` で、W自体は未シリアライズである。330の実commit `89055324380500` は両方の内側。退役票25のD超過を停止原因としない。ca2/c41の保存capture/analysis endは元D前だが、実C入場時刻は未保存なので壁時計内訳を断定しない。

私的根拠はGit外の `test120-movement/movement-analysis.md`（SHA `1d41df9d9fdd77b6442a8d56e66a5f7bd9316e283a08ff6fd47cbd51a2b8613e`）、`raw-pairs.json`、`ca2-cause-analysis.json` / `ca2-public-cut*.json`、`c41-public-predicate-analysis.json` / `c41-causal-cut-limits.md`へ結ぶ。ca2の公開C cutは宣言HUD preludeと実Scene・最初のACK/MOVEDを使った限定cutである。c41の71/79/80は未保存で、6歩の完全再生を作らない。

## 3. 詳細設計

### 共通の所有・期限・優先順位

既に受理されるSAME/FRESH、stationary wait、旧side/vantage、119 refined passageの分岐を先に維持し、新fallbackはその具体的な既拒否状態だけに置く。新分岐のために`same_choice`、`monotone_terrain`、通常Motion/Perception/Navの一般的な意味を変えない。

双方のsource Sceneが正常FLOOR、商品UNKNOWNで、origin・旧/新next・新targetが両Sceneで正にFLOOR、全ITEM/保護なしであることを要求する。各形で許した新bracket以外の全旧GOLD・DOOR・特殊tileを保持し、通常chooserの完全Decisionを使う。owner開始/level・prefix・現在位置・inputs/moves/restarts・visits・entrance・passageのbitと全pending/inspected/unresolved/closed maskを凍結して照合する。固定world mouthを新targetへ置換しない。候補/商品優先、取消、終了、外部owner/世代の通常guardはそのまま働く。

723/ca2の新private route contextは最大1個とし、固定DATA anchor全Scene、id/start/end/prefix、完全choice、旧command/source identity、元period、元world snapshot、固定P/W、最新の独立零proof identityと一度消費した印を保持する。入力票/移動creditを保存する構造にはしない。既Sceneの旧source/`before`と退役eventは改変せず、新DATA anchorは別private Sceneへ置く。公開header/ABI/wireは増やさない。

Pは退役前に確定していたsource+FRESH、phase+FRESH、最後の実MOVED+12秒、既command sync、walk45秒、session180秒、既親期限の最小値で固定する。723は既stationaryのPとWをそのまま上限にする。ca2は既Wがない場合にだけ、退役時の元periodで `min(P, now+2*original_period)` を1度固定する。再anchor・後続画像・fit・publicationでP/Wを更新しない。新DATA観測、fit、publication、beginは共に保存したP/Wでclipする。旧票のtarget/NB/Dはeventに残し、旧Dを延ばさない。

DATA anchor以降はidが新しく、startがanchor end以降の非重複画像だけを使う。anchorからその現在画像への**直接の通常BLOCKED(dx=dy=0)**、同じ全tiles/保護と完全choice、正FLOORを毎観測で確認する。前画像をanchorに差し替える零の推移を使わない。正常UNKNOWNは静的条件が変わらず元W/P内の場合だけ無入力で待ち、proof/slotを撤回する。非zero・所有/地形/保護変更は拒否する。通常fitのmodel captureが最新proof以上で、現在prefix/ownerと元予算が生き、準備50msを持つ未来の物理拍が得られた場合だけ新IDを発行する。旧IDのbegin/completeは無副作用で拒否し、inputs/moves/visitsや未消費ordinalを増やさない。

新IDのpublicationでこのroute contextを一度消費し、以後は固定anchor・現在proof・新command identityを結んだ照合だけを許す。NOT_SENT/ACK/UNKNOWNから同じcontextを再armせず、真begin/取消/終了/resetで失効する。1つの実MOVED owner当たり再planは1回、既観測refreshのrun上限8を共有する。723は元stationary入場で消費した回数を再加算も返還もせず、同ownerの別refreshを許さない。ca2は通常の1回を消費する。

### A. 723: stationaryから同方向・別targetへDATA handoff

既waitがREADY、input0/currentID0、元MOVE eventがbegin0/outcome3で、直前のproof IDが最後の採用currentと一致する場合に限る。新画像の処理で既proofを撤回する前のcurrent Scene/metadataを照合し、元anchor→直前currentの通常strict零を再確認する。さらに直前current→新画像の通常strict零を別々に要求する。これらから元anchor→新画像の零を推論しない。

実形はCLEAR passage、reason10/FLOOR、同じ方向・固定mouth、完全targetだけが変わる場合。元anchorからの差は、origin/next外の旧target1セルFLOOR→UNKNOWNと、遠方1セルUNKNOWN→FLOORの2セルだけに限定する。直前currentでは遠方の露出を既に観測しており、新画像との差は旧target喪失の1セルだけ。新targetは元anchor・直前current・新画像の全てで正FLOORで、通常plannerが同方向の短い経路を選ぶ。origin/nextや旧blocker/GOLD/ITEM/保護の喪失を認めない。

新画像330に相当するSceneをDATA anchorに固定し、旧stationary qualification・support・slot/epochを全て撤回する。既stationaryのREADY/ISSUED権限は新modeへ持ち込まない。旧source323→330がUNKNOWNのままでも旧票を復活させず、後続の独立330→新currentの通常零を待つ。旧Wが既に切れている場合はREADYの残PからOBSERVEを開き直さない。

### B. ca2: 未開始GOLD vantageの別route再観測

input1のexact未開始MOVE/eventと元continuous ticket、通常の時刻/fit/準備所有が有効で、旧accepted各分岐が成立しなかった場合だけ追加する。両Sceneは実GOLD2・GOLD_CANDIDATE/商品UNKNOWN、同じ全旧GOLD、ITEM/保護なし。旧新Decisionはreason8/FLOORの直交方向で、新targetと旧/新nextは双方に正FLOOR。元source→新画像に直接通常strict零を要求する。

差のrecipeは方向相対の具体形に限定する。旧方向`d`の3セル先のFLOOR→DIRTが1セル、後方`-2*d`のDIRT→FLOORが1セル、origin/旧新nextの近傍と新target外の遠方UNKNOWN→FLOORが1セル、同じ除外域外の遠方STONE→DIRTが1セル、それ以外は同じ。最後の材質変更はblocking→blockingであり、STONE全般の消失や任意のDIRT開口を許す規則にはしない。実67→69の4差をこのrecipeへ結ぶ。

旧UPを確実未送信へ退役して新画像を固定DATA anchorへ置く。1枚の方向変更や自己比較だけではLEFTを作らない。後続の独立anchor直結零・同完全choice・通常fit・未来拍・元P/Wと新IDの全条件は共通設計に従う。既side openingとvantage replanが扱う正常系をこの新modeへ迂回させない。

### C. c41: 閉扉2先・正FLOOR1歩のFRESHだけ

`continuous_validation`の既FRESHが地形/GOLD関係で拒否する場合に、pure helperで追加資格だけを作る。未開始の正常continuous lead、実MOVED所有、両FLOOR/CANDIDATE/商品UNKNOWN、ITEM/保護なし、origin/next FLOORの保持を前提とする。旧choice reason8→新reason7、同方向/FLOOR/同target=`1*d`を要求する。既の元source full Decisionと新Decisionの計算は各1回とし、失敗したold plannerを別callで救済しない。

形は閉扉`2*d`がUNKNOWN→DOORのちょうど1セル、左右の既GOLD片側を保持し、反対側DIRT→GOLDがちょうど1セルで新しい閉bracketが実見する場合だけ。全旧GOLD・既DOORを保持する。追加開口はorigin/next各3×3外かつManhattan距離6以上のDIRT→FLOORちょうど1セルに限定し、他差は既通常monotoneが認める普通のreveal/restrictionだけにする。実(0,1)等のDIRT→STONEはblocking restrictionなので一律の近傍差禁止にはしないが、origin/nextと新door/bracketは専用guardで固定する。

通常の元source→現在画像の直接strict零を経て、既FRESHへだけ返す。新source/newIDでも元target/NB/D/ordinal/period/準備epochとchain2/run8をそのまま保存する。元Dが切れた場合はこのvariantでは救済せず、新しいwaitや別拍を作らない。door3先/2FLOORの旧variant、通常monotone、旧SAME/FRESHを先に維持する。旧DIRTからdoor2先など、今回実見していない別形を追加しない。

### 予定hunkと同じCを扱う担当の境界

route担当の製品変更は `patches/loopctrl/ngg2/NG2Controller.c` の次の箇所だけを予定する。関数名は既関数を示し、新helper名は実装freezeで確定する。

- `NG2StationarySupport`近傍の新private `NG2RouteObservation120`とController field。既stationary/PARTIAL proofの構造自体は書き換えない。
- `stationary_wait_scene` / `start_observation_refresh`近傍へ、A/Bのpure shape guardとroute contextのstart/update/current-proof/clear helper。`revealed_approach_terrain`近傍へCのpure near-approach helper。
- `update_stationary_wait`の既拒否直前でAを試すhunk。旧正常waitとgold handoffの順序を保持し、旧proofを消す前の正current identityを渡す。`start_observation_refresh`の既全admission拒否後でBを試すhunk。
- `update_gate_refresh`の新private route modeだけのdispatch、`continuous_validation`のC限定資格と既old/new chooser結果の照合。旧mode本体や一般`monotone_terrain`は変更しない。
- `ng2_controller_tick` / `reserve` / `ng2_controller_begin`の新modeのproof・P/W・発行identityの照合/消費だけ。`ng2_controller_observe_at`では既採用current/prefixと結ぶ新modeの失効だけ。通常入力・clock・preparation getterの順序は変えない。
- `reset_level` / `finish` / `terminal` / `ng2_controller_cancel`と既clear/reset箇所へ、新route fieldの失効だけを追加する。共有関数は小hunkで順番に統合し、全体置換しない。

goods担当の [普通PARTIAL proof cache計画](test120-partial-proof-cache.md) が所有する `NG2PartialStaticProof`、anchor end、`cycle_bind/latch/failure`、`cycle_partial_*`、PARTIAL observe stampとbeginのPARTIAL消費は変更しない。共有reset/finish/beginの追加位置はrootのGO時に分担し、双方のprivate clearを独立した1行hunkで統合する。新試験はroute担当の `tests/test_native_route_observation120.py` 1ファイルを予定する。既119 fixture/checker、Runtime/Beat/Nav/Perception/Ring、header/ABI/G1/R12は所有範囲外。

## 4. テスト影響範囲

新route ownershipをOBSERVE・READY・publication・begin・取消へ結ぶ公開C lifecycleを主にする。元実RGBA cutでは各Scene/normal Motion/Nav/拒否guardを旧119と同じ条件で保持し、全旧private state再生や未保存の未来画像は要求しない。private guard cutの宣言contextと、公開APIでearnedした試験を別artifactへ保存する。

関連回帰は既stationary wait/unsent（076）、passage/source（115/119）、stationary support/qualification（117）、side opening（098）、vantage replan/revealed motion（108）、revealed route（090）、revealed domain/ACK/closed floor（113）、preinput refresh（118）のうち変更helperへ直接到達するassertを選ぶ。各新shapeが成立しない旧正常SAME/FRESH/waitも明示的に維持する。rootが確認済みの3成功rootの通常陰性packetとC採用→耐久保存→実RS→newfloor/childの契約を変えず、policy7の許容unmatchedを一律0にしない。旧118/policy17と119/policy4の成功を保持する。

C-only routeのために全Runtime world/故障集合を再実行しない。新private modeの票が通常Runtimeの既getter/prepare/beginへ届く境界は、rootが必要な最小caseを選んで確認する。goods cacheが選ぶPARTIAL hot callbackとは別scopeで、既Runtime58cの本体保持と意味的な票/clock検査を混同しない。native変更に必要な実IPA/build/seal/配布物確認はroot工程で実施する。

## 5. 新規テストケースと正式Red

実装前に旧119 exact Controllerを固定し、`test_native_route_observation120.py`の公開API assertion Redを保存する。公開create/start/通常fit/予約→begin/既知ACK→通常MOVEDから必要なownerをearnedし、private setterで票・visits・qualified stateを作らない。手続きScene/時計のpreludeは独立した意味的モデルで、実機raw全履歴再生とは呼ばない。環境/compile失敗やhelper単体の常時成功をRedに数えない。

| 機能 | 正常期待 | 必須の拒否/不変条件 |
| --- | --- | --- |
| A: 旧waitからDATA handoff | 旧anchor→新画像UNKNOWNを維持、直前currentの直接零と具体2差/1差で無入力の新anchorへ。後続独立零・同choice/fit後だけ未来新ID | 直前currentの証明不在/ID不一致、normalUNKNOWN/非zero、origin/next/新target喪失、違うmouth/pos/visits/masks、旧W/P切れ、旧票begin/ACK/UNKNOWN、複数handoff拒否 |
| B: GOLD vantageのDATA再観測 | 元source直結零と具体4差で旧UPを撤回。独立証明までtick0、旧ID拒否、新LEFTのACKだけではmovesを増やさない | 任意STONE変化/多い差/非直交、新旧next未観測、旧GOLD/ITEM/保護変化、same prefixでない画像、重複/重なり画像、旧owner/fit/時刻無効、旧variant横取り拒否 |
| DATA ownerの寿命 | 新anchor/元P/W/period/回数は固定、proof撤回時は無入力、現在fitと準備後の未消費ordinal・別物理拍/新ID | 反復UNKNOWNでW/Pを延ばさない。取消/reset/候補/商品で失効、NOT_SENT/UNKNOWNから再arm0、publication/beginでsource/identityを変えると拒否。旧callbackは新票を壊さない |
| C: 近い閉bracket FRESH | reason8→7、同方向/target1、normalzero、新source/newID、元物理拍/NB/D/ordinal/period/epoch・chain budget不変 | door/bracket欠け、旧GOLD/DOOR喪失、未観測next/ITEM/保護、近傍DIRT開口、遠方開口2個、別target/方向、非zero、元D/P/phase切れを拒否。旧door3 variantと通常SAME/FRESHを維持 |

境界は元W/Pの直前/等値/直後、準備50ms不足、model captureがproof未満、chain2/run8、1owner再plan1回を含む。回復の新票が公開された後のACK→実MOVEDは独立した将来意味モデルで確認し、723の331以降/ca2の70以降/c41の124以降を実保存画像として補完しない。原本cutと正式lifecycleが異なる条件を明記し、未知精度や実機到達率へ算入しない。

## 6. 実装順

この8項目計画の単一独立設計レビュー→rootのowned hunk/GO→3機能それぞれの正式Red→private contextとAの最小Green→Bの限定admissionとGreen→Cの限定FRESHとGreen→直接関連回帰→独立最終差分レビューの順に進める。新modeは共通所有/失効を先に実装し、A/Bで似た予算を別々に再計算しない。goods担当と共有関数のhunkを都度通知し、商品cacheの条件は触らない。

原本から要する条件が新たに判明した場合は、試験を弱めず差を計画へ記録する。元P/W延長、未知入力の再送、別world mouth、一般的地形緩和、未保存private状態の注入が必要なら本計画では実装せず、根拠と別scopeをrootへ返す。

## 7. コミット前テストと証跡

新公開C Red/Greenと選んだ直接関連assertの結果、実compiler/flags/source SHA、旧119との同入力packet/normalMotion/Nav/票・期限・所有counter差分を保存する。原画像と実機時刻は改変しない。通常Scene producer・通常Motion・全GOLD/ITEM/保護の拒否guardが保持されたことを検査し、期待値削除/skip/巨大な待機時間でGreenを作らない。

Controller以外のRuntime/Beat/Nav/Perception/Ring/headerの保持bytes、共有reset/取消の全失効、原success packetと既票/negative/RS境界の選択回帰を照合する。新モードに必要なRuntime境界だけをrootが選び、実Python3.9・native IPA・seal・actual compiler/profile・完全source/固定Releaseの同一性確認へ結ぶ。hostの合成成功・静的レビュー・Mac callbackとiPhone受入は別欄にする。現時点で新正式Red/Green、製品差分、CI/IPA/実機改善はいずれも未実施。

## 8. スコープ外と次の実機受入

商品の画像/価格/名前認識、全商品登録、候補方位追加、PARTIAL cache本体、119 entered token/yield、Runtime queue、capture bridge、入力座標、source150ms/worker100ms/10ms窓、16inputs/12RS/45秒/180秒、R12/G1/特徴資産は変更しない。capture62の候補位置は最新のユーザー訂正で左上であり、右側への拡張は本計画にも混ぜない。

3成功rootは維持するが、そのchild失敗を成功へ付け替えない。c41の未保存前段や各停止の未来画像、実C内訳・実機性能は未確認である。次のTEST120を返す際は、何をどう直したか、維持した成功、実施検査と未確認を具体的に示す。通常1-1ポーズから初回RS→候補/通路→商店→全商品観測→対象なしの正常判定/保存/実RS→次周回をiPhoneで依頼し、終了後の全run ZIPを受領して商品到達・継続を判定する。
