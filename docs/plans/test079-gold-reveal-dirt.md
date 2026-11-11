# TEST079: 金壁発見後の1歩と掘削予約の継続

2026-11-11（日本時間）。baseline `5e9a9bbdb0e16157c995d04e42066006b20c8313`（コードはTEST078/build126の954c6f39と同bytes）。通常の局所修正。Nav/Controllerの2箇所・新単体2module・関連回帰・独立レビュー1名・新IPA/固定Release・一連実機を対象とする。Runtime/Perception/JSON/全header/API16cap14v15/ABI/G1/R12/全閾値・期限・予算・UNKNOWN無再送は維持する。

## 根拠と期待

078追加3ZIPを前batchと混ぜずGit外received078bへ保存し、56原PNG/全hash/CRC/schema/manifest/prefix/cursor/実publication一致・全PAUSE/完収を確認。実順17a58a71→b73d5d78→388f19c6。原245で2回目の全3商品と価格8/13/50をrootが確認し、到達1/3。取得failure/timeout0、host error/cancel0/status40回max1.300秒。2の別cmd10 too_lateは最終停止と混同しない。raw/Scene/数値はGit外test079b-*。

1は3restart/5MOVED6入力・開扉0、source176→196/LEFTを実送信・ACK後8UNKNOWNでMOVEMENT停止。begin NB+1.918ms/D−8.082ms、最後もvisualD残約1.868秒。原画は実LEFT1歩。元singleton金(-2,-2)が最新(-1,-2)へ移り、最新で閉DOOR(0,-2)と反対金(1,-2)のbracketが揃う。残2セルの旧projectionはUNKNOWN。新たな開扉/入店をしたわけではない。

原raw最良(+9,0)=.41303681335/gap .33343805475、旧median259/bad1で支持300未達。既partial_matchは旧STONE5点中、保持3点以外の遠方2点がDIRT分類となり不成立。既078の新3依存面は405/bad5・upper118/lower287、全73の元strong条件が成立するが、old closedGate2ahead/GOLDexact/high-intensity専用のため対象外。72競合は支持300未満で、十分支持競合に実15pp差を測れたと一般化しない。

3は4restart/6MOVED6入力・開扉0。未送信cmd17/RIGHT/source272→273の前後でfull5 RIGHT/reason6/target(1,0)/DIRT、origin/実next/金/全保護/両3×3は同じ。遠方(-1,2)DIRT→FLOOR1点のみ、strict BLOCKED(dx=dy=0)成立。quietはDIRT掘削を対象外とし、genericのsafe-floorでもFLOOR validation7で停止する。新しい静止証明や送信後再送ではなく、既予約の遠方差許可を局所追加する。

## A. 新しい閉扉bracketが見えたunitを証明

全旧Nav判定後もUNKNOWNの場合だけ別補助を追加。両FLOOR/CANDIDATE/GOODS_UNKNOWN、全protected/ITEM0、旧origin/実入力先・最新originの観測FLOORを必須とする。raw最良が有限の同方向厳密unit、通常側score≤.45/gap≥.08、全73候補を使う。旧primary/partial_match/078補助の意味・本文を変更しない。

旧GOLDはsingleton1点、最新GOLDは2点で、その2点による閉DOOR/bracketが唯一。旧singletonは最新bracket片側へ対応し、門中心と反対金の旧projectionはUNKNOWNだけを許す。旧既知FLOOR/STONE/DOOR等を新door/goldへ置き換えて幾何を作らない。

old singletonと、同じtranslationで最新STONEへ実対応する『旧STONE由来』の相異なる2点が非共線であることを要求する。新STONEだけや消失点はanchorにしない。遠方の旧STONE差を一致証拠に数えない新しい別証明であり、旧関数の全STONE保持条件を外す変更とはしない。zero/±1/±2の全9候補で、異なる旧STONE組を使った場合も含めて対応が唯一であることを確認し、元rawunitと一致する場合だけ許す。

独立の画像証拠は既078固定H→Vの3実依存feature/全使用点mask/UI/known・同材質/符号・contrast6、camera52/両frame51,52除外・1画素1支持・300/95%/各帯100/全73元15ppをそのまま再利用する。新しい面/帯/値の探索はしない。実pairの新幾何9候補でも(+1,0)だけが適合することをread-onlyで確認済み。

成立してもMOVEDのunitだけを返し、開通・入口・商品creditは作らない。最新の次セルやNavの方向が変わっても、過去の到達と次の権限は分離する。次は通常Navの観測床/開扉へ返し、未知セルへの新権限・元beforeの交換・期限延長・UNKNOWN入力再送を追加しない。

## B. 閉金扉手前のDIRT予約だけを同ID保持

既quiet_gate_observationへ、lead確認済み/moves>0/continuous有効・未入店・確実未送信state1のreason6/DIRT・target=実nextを追加する。旧/最新の2*directionが閉DOOR、その両脇GOLDは入力軸に垂直で同じ法線であることを明示し、source/最新で保持する。gate_at(bool)だけで法線を検査したと呼ばない。

両FLOOR/CANDIDATE/GOODS_UNKNOWN、全GOLD/全protected集合・材質/ITEM不変、origin/実next・両3×3不変・full5一致・strict BLOCKEDを要求する。許す差は保護外で両3×3の外のUNKNOWN/FLOOR/DIRT/STONE間だけ。GOLD/DOOR/ITEM/商品/保護や実stepの変化、UNKNOWN/TWEEN/nonzeroは不可。既quietの他scopeの意味やnear/shielded例外を変えない。

元before/同ID/ticket全bytes/target/NB/D/ordinal/epoch/source/位相/元horizon・model補正/同期/walk/session/owner/prefix/取消条件はすべて保持。新ID/再予約回数・retune/safe-floor/reference/FRESH資格・入力/移動/開通creditを増やさない。begin後/送信UNKNOWN/期限超過を対象外とし、商品優先を維持する。

## 単体・レビュー・配布

新Nav単体（目標8methods）は、独立帯の非重複明点をunit移動させる手続fixture等で旧compile成功の公開UNKNOWN→期待MOVEDのRedを先に実測。4方向・新露出のGOLD/DOOR projection、非共線/異なるanchor組の複数解、新STONEだけ/旧金削除、known/rawzero/逆/2tile/8/8.5px・score/gap境界、全保護/商品/次Nav/未入店、既固定3面/全73閾値の維持を確認する。原PNGはGitへ入れず、private helper欠如/compile失敗をRedへ数えない。

新Controller単体（目標6methods）は公開Cで同票全bytes保持→元NB begin/ACK→DIRT→FLOOR/TERRAIN_OPENEDまで進め、moves/entrance/DOOR credit0と次の進入/開扉分離を確認する。4方向・門法線/full5/near/新金/保護材質・未校正/started/UNKNOWN・元D等号/超過/owner/prefix/goods優先を拒否境界にする。

関連回帰は旧Nav3/078閉扉2/071shop5/071terrain2/Controller2/072passage2/ABI1の関連17methodsを明示選択。既assert/旧guardを削らず、全Runtime/worldを積み増さない。受領原Sceneの純分類/guard適合と、欠落future/live全状態の再現は分ける。通常1名が計画と最終差分を独立レビューし、数値/元契約/既known不変を確認する。

fresh G1→sealでNav/Controller2変更・他20不変、実compiler/全MachO/IPA/全tracked sourceを照合。固定Releaseを匿名全GET確認後、新IPA更新・LoopCtrl完全終了/起動・Start Server/VPN・test_079.shを示し、通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認をまず2回依頼する。全画像/ZIP照合後runtime/test-079-<run_id>.zip全回分と全商品/停止位置/拍間隔を返してもらう。
