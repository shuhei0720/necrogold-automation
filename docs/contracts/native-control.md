# Nativeの不変条件

[要件](../requirements/necrogold.md)・[通路と限定変更](passage-approach.md)。[079計画](../plans/test079-gold-reveal-dirt.md)の2箇所以外は維持。

## 2. 保存

`legacy/r12/`40ファイルは[元manifest](../r12-source-manifest.json)とbyte一致。scope外G1/保護資産不変。raw/端末設定/pairing/秘密値はGit外。

## 3. owner/prefix/取消

端末monotonic nsを使用。取得両境界の同completed prefix・inflightなしの安定画像だけが入力権限。交差/旧世代/取消済みは拒否。CはcontrolQueue直列、main begin中caller同期停止。解析はcapture worker、Sceneはimmutable heap所有。observe/証跡は同owner/generation/cancel gateでcommitし、capture/解析/main実終了までdrain。最新優先/queue上限・EXIF1〜8・px/pt・alpha/sRGB/比率/stride/範囲/overlap検査を保つ。

main.sync/run lock外でAX照会、callback実returnまでlease保持。最終callbackにAX IPCを置かず、query-start≤end≤now・1秒以内を待機/IPC込みで検査。sample共有はC epochで証明された同logical MOVEのSAME/FRESH、同run/clock/owner/世代/PID/prefix・元拍/期限だけ（初歩/retune/ACK後不可）。synth直前に最新ID/方向/座標/実時計/前面/lock/owner/世代/取消/元ticketを検査し1回送信。旧IDは新状態不変、未確認input≤1。UNKNOWN再送/自動cleanup、停止後/別アプリへの旧画像入力は禁止。

## 4. 初期slot/再取得

初歩はlead+50ms準備の拍を選び、notBefore100〜50ms前に最新判断から公開。それ以前のticket/event/replan生成は禁止。元境界は§6。

再取得はinputs/moves/lead_confirmed=0・取消/商品/終了なしの未発行candidate/state1未送信初歩/pendingだけ。track/同拍8%補正/stale/準備窓/未送信D失効で旧IDをnot_sent、slot全field/initial_ticket/model/raw撤回。event/replan/入力予算不変、同observe refit禁止。後続HUDの2秒span/fitで別候補選択。旧ticket時刻/ordinal不変。

sync12秒は公開/begin/completeの等号で終了。TicketGuard短絡→complete0はstate1の純D超過だけ撤回。確認済連続/pendingは[065](../plans/test065-pending-unsent.md)。期限内complete0/state2/3/4/retune/権限失効は対象外。旧ID/状態検査は時計/予算更新より先。確認後同期は§8。

## 5. 未送信再予約

[066](../plans/test066-shop-action.md)・[071](../plans/test071-observed-entry.md)の限定quietは同ID保持。それ以外は初歩≤2回、continuousはchain≤2/run≤8。確実未送信・両Scene safe_floor/同gold/strict BLOCKEDが必須。初歩は同direction/origin・next近傍保護、continuousは全protected/元・保存の完全5field Decision/最新actionを検査。元target/notBefore/deadline/period/ordinal/horizon保持。reason8/FLOORは許可済み遠方target座標だけ変更可（direction/reason/obstacle/最新判断を再検査）。未知inputの次拍置換は禁止、初歩失効は§4で撤回。

FRESH（validation12）はlead確認済みcontinuousでSAME不成立時に最新判断へ替える。両FLOOR/GOODS_UNKNOWN/GOLD_CANDIDATE・origin FLOOR・全protected不変・source5field単一証明・strict BLOCKEDを要求。全230セルでUNKNOWN→FLOOR/DIRT/STONE/GOLD/DOOR、FLOOR→DIRT/STONE/GOLD/DOOR、DIRT→STONE/GOLD/DOORだけ許可。GOLD/STONE/DOOR/ITEM不変、新DOORはgold bracket必須。

通常plannerの1MOVEを別ID/latest sourceへ予約。pending全5field/最新direction・x・yを検査。FRESH→SAMEで元方向へ戻さず、SAMEとchain2/run8・同拍/ordinal/全凍結期限を共有。未予約FRESHの重複/元source・phase horizon延長は禁止。

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

[067](../plans/test067-motion-confirmation.md)の追加MOVED証拠/入口BLOCKED再fitは元閾値/予算・消去前snapshot維持。motion全73候補、強度.45/差.08、texture支持300/75%、構造補助95%/全候補15pp差/2領域各100を保つ。MOVEDは同方向unit変位のみ。開扉/茶壁破壊と進入を分け、開通で歩数を増やさない。partial/逆方向/未知/入力数で移動を捏造せず、観測gold/保護/入口を維持。

## 9. 元画像fallback

入力権限は最新Scene。immutable元Scene/capture・start・prefix/元ticket・period・期限/完全Decision/位置・visits・entranceはlead確認済/moves>0のcontinuous safe-floor logical MOVEだけ保持。資格付き未送信更新が必須。

元画像から送信前の全安定current-prefix画像へ直接strict BLOCKED(dx=dy=0)を確認。mask0/HUD/signatureのみ/pending→reserveも含む。両FLOOR/GOODS_UNKNOWN/GOLD_CANDIDATE・safe_floor、全gold/保護、元/保存/最新5field Decision、位置/visits/入口/prefix/全凍結境界を検査。初不成立で同MOVE中の資格は永久失効。

FRESH後の旧referenceは再作成/SAME復活禁止。primary UNKNOWN時だけ元画像で既存ng2_motionを補助し同方向unit MOVEDのみ採用。TWEEN/BLOCKED/既知/開扉等を上書きせず、初歩/retune/次ordinalへ流用しない。fallbackはscheduleD/元位相で失効しvisualDへ延長しない。reference失格だけでreason8再予約/primary確認を追加拒否しない。

## 10. 商品優先

商品latchを追加入力より優先。適格な同一商品frameの移動確認は1回credit可、UNKNOWN/TWEENも商品保持して終了。earliest前/期限後は移動を捏造せず最終実評価診断を残す。不可視≠対象なし、候補保持/購入禁止/通知を維持。

## 11. ABI/診断

Status192B/Event128B/Scene23864Bは不変。MotionWait48B layoutも不変だがdeadline_nsはvisualDへ意味変更（cap13で識別）。SceneDetail.validation=2 SAME/12 FRESH_ALLOWED。別query MotionReference80B/ACK MOVE≤16行（[12key閉schema](../../necroprobe/native_walk.py)）。

観測前observed=全motion=0・attempted=false・selected=authority。reference_prefixは同MOVE前の最終ACK（未送信event除外）。未適格fallbackの評価済表示禁止。通常event/trace observed一致、goods=1最終ACK MOVEだけ未評価/最後のUNKNOWN・TWEEN traceと後の商品event observedとの差を許す。

RecoveryTrace192B/RecoveryStatus456Bの別getterで消去前model/raw samples≤13をsnapshotしrefit/最終PAUSE/export後も保持。最初/最新≤2件、sequence=1/record_count、dropped_records=record_count−保持件数。mode0通常/1初歩/2確認後、reason1〜8、clock1capture_end/2actual_tick/3actual_commit、episode0の失効記録も可。[061閉schema/enum](../plans/test061-verified-progress.md#診断と互換)の全named fieldを保存し、ns/countは非bool非負int<2^63、model/sample型/有限double/enum/件数/sequenceと余剰key拒否を検査。初期counter/ns=0・mode0・records=[]。accepted空診断の補完は応答copyだけで保存report/lifecycle不変。既存診断/初故障も保持。

## 12. 起動/旧client回復

新規v15/API1.98.16-ngg2/cap14、完全reportのrecovery必須。v12〜15はmotion_references、v14/15はrecovery必須。旧診断不在可/存在時同閉schema。preflight(ready含む)/status/result_metadataはv1〜13=API.14、v14=API.15、v15=API.16へ固定。motion_wait≤8は期待API.16/保存v15のみ、旧版≤3。v10〜15は4chunk batch、v9は1、v1〜8はlegacy。started回復は元UUID/clock/owner・GET0/start0、unknown start無再送。未開始旧journalは同UUIDでv15へ移行。fresh preflightだけ許可transientを最大4試行/計8秒/各2秒で再確認。

## 13. Export

PNG≤20枚/各512KiB/計4MiB、初期/商品/停止/最新比較優先。chunk64KiB、manifest wire512KiB/chunk wire256KiB。batch≤4chunk/256KiBも各chunk検証/取消/期限必須。検証済prefixだけhash/cursorへ反映、atomic fragmentをjournalsより先に保存。再中断も未検証suffix全体保持、active journalが回復権限。

RPC2秒/結果8秒。unsafe/非pagedは90秒を残session180秒内へ。[069](../plans/test069-collection-gate.md)のterminal/drained・input0/3・非inflight/非凍結pagedは独立300秒。同UUID/cursorのread-only、start/入力/keepalive/cancelなし。旧返信cache消去・未知input解決の誤認禁止。local原本保持、全画像検証/ZIP公開前の終了/次start禁止。§3排他。

## 14. Compileと封印

profilev2はPerception/Navigation strict O2（-fno-fast-math/-ffp-contract=off）、Beat/Controller O0、Swift Onone。native_v6/profilev1互換を保つ。22seal/PBX/raw args/RSP/profile/manifest/IPAは同code。app/runner API/cap・全Mach-O HOST/fixture/spy除外、全tracked sourceZIP bytes/CRC/path照合。標準macos-26/ubuntu-latest。

## 15. 検証

[試験区分](../testing.md)。画像不足/hash不一致はlocal失敗、CI除外と区別。模擬/未測定は実機成功/速度達成にせず、run別評価。


配布/実機は[AGENTS](../../AGENTS.md#保存と返却)。
