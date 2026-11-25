# Nativeの不変条件

[要件](../requirements/necrogold.md)・[通路と限定変更](passage-approach.md)。[087](../plans/test087-target-pause.md)・[090限定差分](../plans/test090-device-stops.md)以外は維持。

## TEST094の専用profile拡張

旧API/cap15・profile1/2・Status/Event/Scene ABIは維持。専用cap/profileの端末内判定・陰性周回は[限定計画](../plans/test094-native-goods-cycle.md)、上左の観測床候補は[Nav計画](../plans/test094-shadow-passage.md)を適用する。companion ABIと閉schemaを分離し、正常な完全陰性証明/耐久保存/新規UI資格/実ACKと新floorだけ次levelへ進める。候補保持・UNKNOWN凍結/無再送・全worker実drain・元期限と累積予算は解除しない。診断回収の許可を入力解放と同一視しない。

## 2. 保存

`legacy/r12/`40ファイルは[元manifest](../r12-source-manifest.json)とbyte一致。scope外G1/保護資産不変。raw/端末設定/pairing/秘密値はGit外。

## 3. owner/prefix/取消

端末monotonic ns。入力権限は取得両端のcompleted prefix一致/非inflight安定画像のみ。交差/旧世代/取消拒否。CはcontrolQueue直列、main begin中caller同期停止。解析はcapture worker、Sceneはimmutable heap所有。observe/証跡は同owner/generation/cancel gateでcommitし、capture/解析/main実終了までdrain。最新優先/queue上限・EXIF1〜8・px/pt・alpha/sRGB/比率/stride/範囲/overlap検査を保つ。

main.sync/run lock外でAX照会、callback実returnまでlease保持。最終callbackにAX IPCを置かず、query-start≤end≤now・1秒以内を待機/IPC込みで検査。sample共有はC epochで証明された同logical MOVEのSAME/FRESH、同run/clock/owner/世代/PID/prefix・元拍/期限だけ（初歩/retune/ACK後不可）。synth直前に最新ID/方向/座標/実時計/前面/lock/owner/世代/取消/元ticketを検査し1回送信。旧IDは新状態不変、未確認input≤1。UNKNOWN再送/自動cleanup、停止後/別アプリへの旧画像入力は禁止。

## 4. 初期slot/再取得

初歩はlead+50ms準備の拍を選び、notBefore100〜50ms前に最新判断から公開。それ以前のticket/event/replan生成は禁止。元境界は§6。

再取得はinputs/moves/lead_confirmed=0・取消/商品/終了なしの未発行candidate/state1未送信初歩/pendingだけ。track/同拍8%補正/stale/準備窓/未送信D失効で旧IDをnot_sent、slot全field/initial_ticket/model/raw撤回。event/replan/入力予算不変、同observe refit禁止。後続HUDの2秒span/fitで別候補選択。旧ticket時刻/ordinal不変。

sync12秒は公開/begin/completeの等号で終了。TicketGuard短絡→complete0はstate1の純D超過だけ撤回。確認済連続/pendingは[065](../plans/test065-pending-unsent.md)。期限内complete0/state2/3/4/retune/権限失効は対象外。旧ID/状態検査は時計/予算更新より先。確認後同期は§8。

091は初歩state1のScene拒否だけ、同level入力/移動/lead=0・固定原点・同prefix・確実未送信・正常FLOOR/商品UNKNOWN/非保護下で旧票とslot/modelを撤回する。既初歩replan上限2回と元sync12秒/initial view/walk/sessionを保持し、独立2枚の新しい同候補支持（新actual GOLDも含む）が揃うまで別IDなし。送信済みUNKNOWN/移動後へ広げない。[限定計画](../plans/test091-device-stops.md)。

## 5. 未送信再予約

[066](../plans/test066-shop-action.md)・[071](../plans/test071-observed-entry.md)の限定quietは同ID保持。それ以外は初歩≤2回、continuousはchain≤2/run≤8。確実未送信・両Scene safe_floor/同gold/strict BLOCKEDが必須。初歩は同direction/origin・next近傍保護、continuousは全protected/元・保存の完全5field Decision/最新actionを検査。元target/notBefore/deadline/period/ordinal/horizon保持。reason8/FLOORは許可済み遠方target座標だけ変更可（direction/reason/obstacle/最新判断を再検査）。未知inputの次拍置換は禁止、初歩失効は§4で撤回。

FRESH（validation12）はlead確認済みcontinuousでSAME不成立時に最新判断へ替える。両FLOOR/GOODS_UNKNOWN/GOLD_CANDIDATE・origin FLOOR・全protected不変・source5field単一証明・strict BLOCKEDを要求。全230セルでUNKNOWN→FLOOR/DIRT/STONE/GOLD/DOOR、FLOOR→DIRT/STONE/GOLD/DOOR、DIRT→STONE/GOLD/DOORだけ許可。GOLD/STONE/DOOR/ITEM不変、新DOORはgold bracket必須。

通常1MOVEを別ID/latest sourceへ予約。pending全5field/最新direction・x・yを検査。FRESH→SAMEで元方向へ戻さず、SAMEとchain2/run8・同拍/ordinal/全凍結期限を共有。未予約FRESHの重複/元source・phase horizon延長は禁止。

090は前方3セルの旧DIRT→bracket DOORと旧金1→金2の露出、遠方DIRT→FLOORだけの限定関係を、元guard/完全source Decisionと同方向・同目標・FLOOR/reason8→7・strict BLOCKED後のFRESH12へ追加する。global monotone・旧時刻/予算・UNKNOWN無再送は変更しない。

## 6. 全期限・予算

| 項目 | 上限・境界 |
| --- | --- |
| 方向入力 / restart | 16回 / 12回 |
| walk / session | 45秒 / 180秒 |
| source画像 / 位相 / 前面query-start | 3秒 / 3秒 / 1秒 |
| MOVE入力窓 | 元notBeforeから10ms以内 |
| 状態遷移 / heartbeat | 4秒 / 5秒、watchdog100ms周期 |

初reserveでscheduleD=min(次拍notBefore+10ms,source/phase/walk/session期限)、visualD=min(source開始+3秒,phase sample+3秒,walk+45秒,session+180秒)を凍結。SAME/FRESH/初歩再予約の期限/原点延長禁止。scheduleDは高速次拍/限定fallbackの親期限、visualDは同ACK画像確認期限。model/source/phase/dispatchも短縮のみ。待機/保存後も期限/取消/主処理・停止・回収の専用期限を検査。

親motion/次ordinalを分離。同nominal/periodのcandidate target/窓を対更新し初reserveで凍結。continuous初回はnotBefore100ms前/取得開始200ms前以降。更新前Dを次actualtickまでmin保持、超過は発行拒否。[061設計](../plans/test061-verified-progress.md)。

[068](../plans/test068-fringe-collection.md)は観測床1歩。[069](../plans/test069-collection-gate.md)開扉/[071](../plans/test071-observed-entry.md)新床回復は各1run1回、独立静止/別ID/元予算必須。069はfreshfit、071は有効HUD/sample≥proof。未送信の開通credit禁止。

## 7. 拍/lead

通常1-1 profile（.515〜.530秒）はlive HUDで確認。動画.52秒/送信時刻を固定epoch・受付幅にしない。初期lead未確認、150/75/225/300/375/450/25msを各1回、安全床/ACK後strict BLOCKED/同gold・経路確認時だけ試す。UNKNOWN/partial/商品変化/gate/dirt/保護対象はretune禁止。同方向実1歩MOVEDでlead選択、全試行を元入力/walk予算へ算入。

## 8. ACK/変位確認

ACKだけで移動扱いしない。state3同MOVE/command/before・安定ACK prefix、取得開始≥max(ACK,target+80ms)、[070](../plans/test070-cadence-lighting.md)はUNKNOWN/TWEEN≤8評価。2〜7回は直前start+元period/10、8回は初回+元periodも必須、旧版≤3。全てvisualD内。before差替えで回数/期限を回復禁止。ACK中HUD失効は次入力の位相資格を撤回し同MOVE確認は継続。state4 UNKNOWN synthはUI凍結・再送/cleanup禁止。通常cleanupは最新ACK prefixの新鮮FLOOR必須。

RuntimeはC直前observeStartをobserve_atへ渡す。MOVED/DOOR_OPENED/TERRAIN_OPENED/BLOCKED-retuneはcapture終了≤actualcommit≤visualD、次actualtickまでvisualD保持。C中/直後の超過も新入力禁止。旧observeはmax(capture終了,last_now)。期限後GOODSは保持し移動creditを拒否。

高速確認は元continuous拍を保持。遅い真の移動/開通確認やACK中位相失効は旧次候補/reference/preparationを破棄して再同期（UNKNOWN/TWEEN不可）。新slotはmodel採用HUD ID≥proof ID・将来拍prep≥50ms必須。失効位相は新HUDでfit、episode元12秒は再失効でも不変、walk/sessionで制限。初歩/retune/開通後もprep必須。再取得の拍間隔を毎拍/速度受入と区別。

TEST118の限定例外は[最後D3](../plans/test118-upper-last-slot.md)から[実unit後の統合計画](../plans/test118-upper-postunit-slot.md)へ改訂する。V2・既return fence有効・正常H1/H2/D1/D2後の次H2/D1/D2/D3だけ、最新eventと保持command/counter/画像が同じ通常unitで、現在の直接零/非保護床・同route/現在modelの全証明が揃い、既定50ms slotがその次physical beatを一拍飛ばす場合に限る。既定の残経路が元Pに入らないか、最新unitの凍結anchor end−不変targetの実測offsetで末端を予測しても元Pを越すことを必要性filterにする。この予測は未来費用の保証でも入力権限でもない。候補自身は元budgetへ適合し、未発行NBがまだ未来なら準備50ms未満を許可する。初回H1・開扉・V1・他routeには適用しない。publication100ms/source200ms、tailの50ms鮮度余裕、schedule/visual/元P/入力上限と送信10ms、実AX/Runtimeのguardは保持する。旧ticketやNOT_SENT/UNKNOWNを復活させず、reserve不成立で追加slot状態を残さない。

[067](../plans/test067-motion-confirmation.md)の追加MOVED証拠/入口BLOCKED再fitは元閾値/予算・消去前snapshot維持。motion全73候補、強度.45/差.08、texture支持300/75%、構造補助95%/全候補15pp差/2領域各100を保つ。MOVEDは同方向unit変位のみ。開扉/茶壁破壊と進入を分け、開通で歩数を増やさない。partial/逆方向/未知/入力数で移動を捏造せず、観測gold/保護/入口を維持。

090の追加proofだけは、元可視STONEちょうど1個が投影先の心臓HUDでUNKNOWNとなる場合を扱う。残る可視STONE≥2/非共線DIRT≥9・9候補唯一・旧raw/band/world95%/axis75%/全73差を全て要求する。HUD外消失や既知矛盾は許可せず、旧16段の判定/閾値を変更しない。

## 9. 元画像fallback

入力権限は最新Scene。immutable元Scene/capture・start・prefix/元ticket・period・期限/完全Decision/位置・visits・entranceはlead確認済/moves>0のcontinuous safe-floor logical MOVEだけ保持。資格付き未送信更新が必須。

元画像から送信前の全安定current-prefix画像へ直接strict BLOCKED(dx=dy=0)を確認。mask0/HUD/signatureのみ/pending→reserveも含む。両FLOOR/GOODS_UNKNOWN/GOLD_CANDIDATE・safe_floor、全gold/保護、元/保存/最新5field Decision、位置/visits/入口/prefix/全凍結境界を検査。初不成立で同MOVE中の資格は永久失効。

FRESH後の旧referenceは再作成/SAME復活禁止。primary UNKNOWN時だけ元画像で既存ng2_motionを補助し同方向unit MOVEDのみ採用。TWEEN/BLOCKED/既知/開扉等を上書きせず、初歩/retune/次ordinalへ流用しない。fallbackはscheduleD/元位相で失効しvisualDへ延長しない。reference失格だけでreason8再予約/primary確認を追加拒否しない。

## 10. 商品優先

商品latchを追加入力より優先。適格な同一商品frameの移動確認は1回credit可、UNKNOWN/TWEENも商品保持して終了。earliest前/期限後は移動を捏造せず最終実評価診断を残す。不可視≠対象なし、候補保持/購入禁止/通知を維持。

TEST116の限定例外: 開扉後の既知UP ACKが最初のFULLで通常UNKNOWNになっても、商品を優先して旧入力待機を閉じたまま、元before/同command/prefixから後続FULLへの通常同方向unitを元visualD・評価数/間隔・actualcommit内で一度だけ採用できる。早期FULLからの静止や移動へ置換せず、既候補/未終了worker・開始済みの新入力・不明synthがあれば採用しない。元eventと主MotionReferenceを実際の後続captureへ結び、同じ位置/visit更新を一度だけ行う。新しい入力を再送せず、元親/同期/共用DATA枠内の独立した現在DATA・直接零2枚・新fit・未消費の一回観測UPだけへ進む。早期FULLの通常UNKNOWN結果は保持し、後続の完全陰性を別に証明する。

090の薄鉄検出は既FLOOR/上下金bracket/商品UNKNOWN・非原点/非保護/全ROI非HUDの固定縦線だけをDOORへ回復する。開いたSceneは変えず既DOOR_OPENEDの0歩creditを使う。商人/看板露出やPARTIALは商品確認完了ではない。

## 11. ABI/診断

Status192B/Event128B/Scene23864Bは不変。MotionWait48B layoutも不変だがdeadline_nsはvisualDへ意味変更（cap13で識別）。SceneDetail.validation=2 SAME/12 FRESH_ALLOWED。MotionReference80B別query/ACK MOVE≤16行（[12key閉schema](../../necroprobe/native_walk.py)）。

観測前observed=全motion=0・attempted=false・selected=authority。reference_prefixは同MOVE前の最終ACK（未送信event除外）。未適格fallbackの評価済表示禁止。通常event/trace observed一致、goods=1最終ACK MOVEだけ未評価/最後のUNKNOWN・TWEEN traceと後の商品event observedとの差を許す。

TEST116の上記late-unitは、元ACK event/主traceのobservedを同じ実後続captureへ更新する。主sourceは元MOVE authorityのままでfallbackは実行しない。早期FULLのRing source/job/raw証拠を後続unitのsourceへ偽装せず、以後の独立DATAは新source/jobとして残す。

RecoveryTrace192B/RecoveryStatus456Bの別getterで消去前model/raw samples≤13をsnapshotしrefit/最終PAUSE/export後も保持。最初/最新≤2件、sequence=1/record_count、dropped_records=record_count−保持件数。mode0通常/1初歩/2確認後、reason1〜8、clock1capture_end/2actual_tick/3actual_commit、episode0の失効記録も可。[061閉schema/enum](../plans/test061-verified-progress.md#診断と互換)の全named fieldを保存し、ns/countは非bool非負int<2^63、model/sample型/有限double/enum/件数/sequenceと余剰key拒否を検査。初期counter/ns=0・mode0・records=[]。accepted空診断の補完は応答copyだけで保存report/lifecycle不変。既存診断/初故障も保持。

## 12. 起動/旧client回復

092は最初の正常decode前だけ、既activation3秒内の新取得/64回/50msで厳密portrait反転aspectを再観測する。既発行captureの2秒reply/drainは維持、正常後/他failure/Raster/EXIFは不変。世代/owner/取消/lock/前面を再検査し再launch/入力しない。[限定計画](../plans/test092-startup-stationary-status.md)。

新規v16/API1.98.16-ngg2/cap15、cap14互換。081計画§5のrevision対応。v1〜15=profile1、v16=profile2。全応答APIはv1〜13=.14、v14=.15、v15/16=.16。v12〜16はmotion_references、v14〜16はrecovery必須。旧診断不在可/存在時同閉schema。motion_wait≤8はAPI.16/v15・16のみ、旧版≤3。v10〜16は4chunk、v9は1、v1〜8はlegacy。started回復は元UUID/clock/owner・GET0/start0、新cap不要。未開始旧journalは同UUIDでv16へ移行。unknown start無再送。fresh preflight許可transientは最大4試行/計8秒/各2秒。

## 13. Export

profile1 `normal-1-1-v1` は旧initial/優先・PNG≤20/各512KiB/計4MiB・legacy/paged同一。profile2 `normal-1-1-evidence-v2` は各map最終正常見送りsource≤12＋既critical≤7に、091で一致snapshot/拒否時刻/prefixを証明したlead未確認・原点・CLEAR sourceの未送信MOVE SCREEN拒否raw最大1枚（累積入力/移動不変。level入力0の証明や回復権限にはしない）を追加する。既criticalの順序/保持は維持し合計critical≤8/20pin、PNG≤20/各512KiB/計10MiB、paged-only/bulk拒否。profile/予算はrun固定、wireから拡張禁止。欠落/oversizeを記録。chunk64KiB、manifest wire512KiB/chunk wire256KiB、batch≤4chunk/256KiB。各chunk検証/取消/期限、検証済prefixだけhash/cursorへ反映。atomic fragment→journal順保存、再中断も未検証suffix保持、active journalが回復権限。暗号/HTTP上限不変。

RPC2秒/結果8秒。unsafe/非pagedは90秒を残session180秒内へ。[069](../plans/test069-collection-gate.md)のterminal/drained・input0/3・非inflight/非凍結pagedは独立300秒。同UUID/cursorのread-only、start/入力/keepalive/cancelなし。旧返信cache消去・未知input解決の誤認禁止。local原本保持、全画像検証/ZIP公開前の終了/次start禁止。§3排他。

TEST116の新cap/明示`continuous_campaign:true`だけは[連続化計画](../plans/test116-continuous-campaign.md)を適用する。旧正常完全陰性→実RS/newFLOOR/outcomeの耐久保存・候補veto・全実callback return・端末内全原本の封印と容量予約が揃った時だけ、新UUIDを無PAUSEで開始できる。hostへのPNG転送/ZIP公開を入力資格にせず停止後へ遅延するが、原本をRAMだけに残して継続しない。子ごとの旧予算、root絶対期限/総容量、同owner/取消/前面/lockを検査し、古い画像/位相/入力権限は継承しない。通常mode・旧yield・読取回復の禁止は維持する。再起動後の封印/予約情報は保存容量と読取回収だけに使い、自動再開・入力権限を復活させない。全childのZIP/公開を照合する前に回収完了と表示しない。

## 14. Compileと封印

profilev2はPerception/Navigation strict O2（-fno-fast-math/-ffp-contract=off）、Beat/Controller O0、Swift Onone。native_v6/profilev1互換を保つ。22seal/PBX/raw args/RSP/profile/manifest/IPAは同code。app/runner API/cap・全Mach-O HOST/fixture/spy除外、全tracked sourceZIP bytes/CRC/path照合。標準macos-26/ubuntu-latest。

## 15. 検証

[試験区分](../testing.md)。画像不足/hash不一致はlocal失敗、CI除外と区別。模擬/未測定は実機成功/速度達成にせず、run別評価。

## TEST117の指定初回リスタート

2026-11-18の利用者の明示指定を受け、`initial_restart:true`をirregular profileのstartへopt-inする。省略の旧開始契約は維持する。同owner/UUIDのmodeはimmutable。初回rootだけ、現在のPAUSEからRS、または有効FLOORの商品候補保持を優先したPAUSE→RSを行う。初回専用の状態で元UI資格・ACK・新floor確認を経て通常処理へ戻す。商品陰性の耐久保存/yieldとは混同せず、既新floorを継ぐcontinuous successorへflagを渡さない。期限/予算/取消/UNKNOWN無再送を維持する。

TEST117 current DATA mode2は同FULL3ITEM/正確halo/両cap/全下床/元GOLDを保ち、商品/実player近傍外の有限material変化だけで最新DATAを取り直す。元parent/2DATA/current一回・同prefix・旧worker候補先/実returnを保つ。通常Motionをzeroとせず、MOVE/UP/移動信用を与えない。新UNKNOWNはHELD、最新画像の完全陰性/独立C証明/耐久保存ができてから既UI資格でRSする。

## TEST121の追加商品証明

[限定計画](../plans/test121-goods-coverage.md)。新cap121に結び、公開POD/ABI・既profile3・元source150ms/worker100ms/D/Pを保持する。layout1/board_mode同値のpolicy19/20を旧policyへ偽装しない。

- 19は唯一の観測SIGN成分のcount/実bboxを照合し、同成分の背景と元4SHOP文字形の相対明暗で認証する。元一致率を保持し、sign既fieldへ実box/有限scoreを保存、merchant全値は0。両capの元floor値1を要求する。
- 20は元3成分を捨てず、唯一のpartitionで2物理看板へ結ぶ。片capだけの`floor_upper=2`は、全体/下半/非重複UL・LRの元床支持と有限の上半色差を要求する別証明で、通常の上半床1を意味しない。他capとfull/lowerは1。旧policyと19へ値2を通さない。
- 全numeric aliasの5cellと広い名前領域を、床の失敗で打ち切る前に対象探索する。先頭2partialは選択rowの両端、残りは元領域外partialの保持情報とし、新19/20だけ総数2..12を許す。切捨てず、超過は未確認のまま。tailは追加商品の被覆証明にせず、候補/名称vetoを維持する。各aliasとtailの座標・box・score・word整合を独立Cでも検査し、未観測/非有限値を陰性にしない。
- 同じimmutable画像の同じsprite/整数座標のboundだけを、当該呼出内の有限heapで再利用できる。元kernel値・全訪問順・対象優先・clock checkpoint・取消/期限を維持し、全出口で解放する。cache不足は元計算または非OKで、入力権限やNEGを作らない。

正常producerの完全陰性、独立C証明、耐久保存と既UI資格が揃ってからRSへ進む。新証明は追加MOVE・UNKNOWN再送・未観測商品の陰性化を許可しない。
