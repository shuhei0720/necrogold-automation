# TEST124: 同方向のrefined通路票を独立DATAへ退役する

2026-11-27（日本時間）。解析・設計段階。公開fixtureと出荷123の正式意味RedはGO済み。raw HUD履歴保持の追加設計を独立確認してから最小実装へ進む。基準はTEST123/build274/CODE578a9ef、保存HEAD fd5901d、検証済み全1243blobのbaseline123。要件SHOP-03/BEAT-02/STOP-01、[native契約](../contracts/native-control.md)、[開発フロー](../development-flow.md)に従う。

## 原因と原時刻

root4は初歩失敗ではない。id2/source71のLEFTはbegin 60540481486416（NB後3.298399ms、D前6.701601ms）、ACK 60540763697750、通常71→78はMOVED(-1,0)。原inputs1/moves1/lead確認1を保持する。ACKだけの加点ではない。

次ordinal2は78→79の遠方DIRT→STONE3セルでFRESH12、79→80でSAME2となり、別ID3/4/5を通じて元target/NB/Dを保持した。80→81は同完全LEFT/reason10/target(-2,-2)/FLOOR、両CLEAR/正の原点・次床、保護/金/ITEM/DOORなし、通常strict BLOCKED(0,0)。変化は両3×3外の(4,0)DIRT→STONEと(1,2)DIRT→FLOORだけである。

一方、immutable元78→81の通常MotionはUNKNOWN。raw零winner .4531083236が元.45を超え、closed/partial証明は0。追加stationaryもblur零 .2319002212に対して+1px .2213975277が上回るため元の厳密競合を満たさない。原UNKNOWNを変更しない。

`observe_at`の早いrefined-source検査が元78→81のstrict零を要求し、最新80→81のquietより先に失格になる。既`begin_refined_passage_route_wait`は方向変更かつDIRT→FLOORだけを扱い、同LEFTと混在するSTONEを認めない。その結果、id5はbegin0のままnot_sent(c81終了60540962869583)、finish(commit60540986278000)へ進む。chain/runは既に2/2であり、3回目のSAME/FRESHで救済しない。

stop_atはRuntimeがC呼出し直前に読むobserveStartで、C処理後の実時計ではない。原D60541005741453との差19.463453ms、NBとの差9.463453msは、この採用時計に対する差だけを表す。C-returnは未出力。原schedule60541530020651、visual60543821197416、walk/sessionは別の凍結上限である。goods job/P/holdは全0、WAITは未開始。publication実時刻、初歩MOVEDのactual commit、私的途中stateは補完しない。

Git外の原Scene/const cutは`test124-firststep/receipt.json` SHAd969880f、数値は`nav/receipt.json` SHA8531aa7c、原時刻は`timing.json` SHA8279626c。7枚の通常Scene、対象10helper bodyとconst結果は出荷122/123で一致し、Perception19ff0492/Nav e0c43a71/Beat809c40a7も同bytes。FR-115-PASSAGE-PRESEND-SOURCEとFR-119-REFINED-PASSAGE-WAITの適用境界が残った事象であり、123の削除回帰を示さない。未出力private状態の完全再生とは呼ばない。

## 別witnessの資格

旧route-change helperと元`passage_source_proof`を緩めず、同方向専用の新しいDATA資格を設ける。元票を送る資格、元画像の静止証明、移動creditには使わない。

- 公開lifecycleで実unitを確認済み、同level・固定mouth/bit/pending/inspected/unresolved/closed・position/visits/entrance・prefixが元refined worldと一致する。未開始state1、同event/command完全一致、begin/outcome0、他entry/upper/lower/商品credit/wait/pendingなし、owner/取消/終了/商品なしに限定する。
- 元`passage_source_world`は成立し、元strict proofの失格だけが入口になる。元source/票/period/schedule/visual/syncを先にfreezeし、元票D内でのみDATA退役を開始する。元sourceと最新before/sceneの関係、安定prefix、capture順序・非重複・鮮度を検査する。
- beforeとcurrentはCLEAR/GOODS_UNKNOWN、原点・次セルは正FLOOR、同5field Decision/reason10/FLOORである。原immutable anchor・既採用source/current全てでGOLD/ITEM/DOOR/protectionなしを要求し、既観測の保護対象を消す許可にしない。
- before→currentの通常Motionが直接strict BLOCKED(0,0)。全変化が原点と次床の両3×3外で、DIRT→STONEまたはDIRT→FLOORだけ。両種類が少なくとも1セルずつ存在する。単なる署名変化、DIRT→FLOORだけ、別方向/別target、近傍変化、FLOOR→UNKNOWN、STONE消失をこの新入口へ広げない。

入口の必要条件は原静的cutで確認できるが、元private world一致まで実runで再現したとは主張しない。公開fixtureは下記の正規lifecycleから別に獲得する。

## DATAから新しい実unitまで

新しいprivate witnessは1level一回とし、使用済み印をslot清掃/再fit/新source/MOVEDで復活させない。追加stateはopaque C内だけで、POD/API/Scene/packet/Swiftを変更しない。固定world、退役票、元境界とpost-retirement proofのID/start/end、発行した新IDを所有する。全出口・level reset・終了時のactive解除を定義する。

入口で旧id5だけをnot_sentにし、eventの元target/NB/D/sourceを保存する。旧slot/continuous pending/preparation/reference/位相資格と移動creditを撤回する。元78の画像やUNKNOWNを最新画像へ付け替えず、原通常Motionを変更しない。現在81は固定DATA anchorとして保持し、その1枚から新ticketを作らない。退役自体はevent/入力/移動/reissue countを増やさず、既chain2/run8を緩めない。

旧modelも撤回するが、同owner/levelで通常`add_sample`が各採用時点の安定completed-prefixを通過させたimmutable HUD raw履歴とcountは保持する。過去の別prefixのScene/入力権限を継承する意味ではない。`NG2BeatSample`にprefixタグはなく、全保持sampleを現在prefix2へ偽装・限定しない。現在prefix固定は退役後A/Bと新票に適用する。既`cycle_rebind_top_wall123`と同じく、新DATA caller局所でcountを保存し、`clear_slots`/`clear_model`後にcountを戻す。sample配列bytesは不変、一般`clear_model`/`add_sample`/旧helperは変更しない。旧modelのtrackには戻らず、後続current sampleの追加から通常`ng2_beat_fit`のmode1を獲得する。Aで新fitが成立した後にBをその新modelで通常trackする場合も、Bの採用IDを証明する。

境界は入口で一度だけ凍結する。`P=min(元visual, 元sync, 元walk45秒, session180秒)`、`W=min(元logical source開始+2×元period, P)`。reissue source80や退役時刻から2periodを再起算しない。元scheduleは別に保持し、新票のdispatch Dとscheduleを元schedule以下へcapする。観測中はW未満、採用/ACK画像確認はP内、実tick/begin/completeとactual commitを既契約どおり検査する。W/P/scheduleが既に不足なら停止を維持する。境界の等号は既各APIの意味を保ち、DATAが未来の実時計を保証したとは扱わない。

退役後に取得を開始した独立A/Bを要求する（trigger81はA/Bに数えない）。observeStartを実C-returnへ読み替えず、最初のowner/前面/lock/期限を通過したactual tickで`retired_at`を一度だけ確定する。そのtick前の後続画像はA/Bに数えない。`retired_at≤A.start<A.end≤B.start<B.end≤actual_commit`、ID増加、同prefix/同固定world/同完全Decision、anchor81→Aとanchor81→Bの直接通常strict零を各々要求する。actual tickまでの処理費用も元W/P/scheduleを消費し、起算点は更新しない。A→Bだけの連鎖零や原78→81の上書きは禁止。比較がUNKNOWN/別判断になってもanchor/W/Pを更新しない。商品/候補/新金壁は既保持を優先し、この専用資格を追加MOVEへ流さない。

Bの後にだけ、新しいHUD採用ID≥B・通常fit/現在model・50ms準備・publication100ms/source200ms・10ms送信窓を満たす、旧targetより後のphysical beatを選ぶ。旧ID/epoch/ordinalの入力権限を復活させず、新IDを発行する。新票にも元schedule/visual/Pと累積入力/walk/sessionを適用する。ACKは入力数だけを進め、同source→実同方向unitの通常MOVEDと元visual内actual commitで初めて1歩creditを与える。UNKNOWN synthは凍結・無再送のままである。

独立設計確認はP0/P1なし。原schedule−原dispatchDから得る元period524,279,198nsを条件とすると、次physical target60541670020651/NB60541520020651/D60541530020651は元scheduleに入る。trigger採用clockからNBまで533.743ms、準備50ms境界まで483.743msである。この式は未収録のA/B・未来fit・実計算の成立保証ではない。新model/遅延でこの拍を逃した場合は、上限を伸ばさず停止することを公開fixtureで確認する。

履歴保持のBeat単体数式cutでは、宣言した同levelの2.4秒span/10rawと退役後A40ms・B80msを、旧modelを入力せず通常fitへ渡すとmode1/period524,279,198ns/last=Bを獲得し、上記次拍に入る。Aで新mode1→Bでその新modelのmode2という通常経路も同じ次拍になる。raw履歴を全消去するとA/B2件は元4件/2秒spanを満たせず、483,742,651nsの準備余裕へ入れない。これは元phase/clockを使ったprocedural算式であり、原runの未出力raw sample集合や実処理遅延を復元した結果ではない。Git外`test124-firststep/refit-math/receipt.json` SHAfc86d20c。公開earned fixtureではraw配列bytes/count保持・旧model0/slot0/epoch0→新A/B sample採用と通常fitの順を別に検証する。

## 関数と変更境界

| 場所 | 限定変更 |
| --- | --- |
| `begin_refined_passage_route_wait`直後 | 新same-direction witnessのconst資格検査とDATA開始helper。旧helper bodyは不変。新caller局所だけ既承認HUD raw/countを保持して旧model/slotを撤回 |
| `observe_at`早期refined-source拒否 | 旧route-change待機が不成立の時だけ新入口を試す。両者失敗は旧SCREEN |
| 新DATA更新helperと`update_passage_wait`入口 | 新witness activeだけを専用処理。固定anchor、退役後A/B、W/P・worldを検査し、一般ROUTEのanchor更新/releaseへ落とさない |
| `prepare_recovery_slot`/`reserve`/`begin` | 新witnessの未消費新IDだけ元schedule/visual/Pを短縮適用し、Bより新しいmodel/将来拍を要求。既経路の条件を変えない |
| 既`resolve_move`の新witness終了境界 | 実新ID/既ACK/通常unitの一回credit後にactiveを閉じる。ACK/UNKNOWN/未送信で解除して再使用しない |
| `reset_level`/終了 | usedは新levelでだけ初期化、active/古い入力資格は終了で撤回 |

root1担当とのC編集境界は調整済み。root1のquiet_gate付近と最終generic mask側に触れず、本件はearly passage proof/専用DATA/限定budget消費を担当する。共有関数へ複数担当が同時編集しない。

## 公開fixtureと検証

正式fixture案は`tests/test_native_refined_data124.py`。元raw/Scene/private stateは公開せず、既`test_native_passage115.py`/`test_native_passage_source119.py`の公開C lifecycleを参考に、固定mouth(-3,-2)のprocedural room/clock/signatureを宣言する。通常fit→初回LEFTのbegin/ACK/通常unit→未送信ordinal2→1回FRESHと1回SAMEを実APIで獲得し、同LEFT/同5field・混在remote material・current直接零・元anchor UNKNOWNという境界を、試験期待を変更せず満たす。内部structへprivate値を注入しない。

1. 出荷123で期待する「旧票not_sent→DATA待機/追加入力0」がSCREENになるassertion Redを先に実測する。原静的cutは別証拠で、公開fixture成功を原iPhone再生と呼ばない。
2. Aだけ/triggerをA扱い/同ID/取得重複/退役前capture/旧prefix/不安定/連鎖零/古いfitで新ID0。raw履歴の配列bytes/countを保持し、旧model/slot/epoch撤回後の通常mode1 fitとB採用IDを確認する。独立A/Bと新fit後だけ別physical beat/別ID、旧票全bytes/credit/reissue count保持、旧callback無作用を確認する。
3. 新票の実begin/ACK/通常MOVEDまで通し、ACK時moves不変・unit後だけ+1。元schedule直前/等号/後、元visual/P/W、C採用前後の遅延、50ms準備不足、別owner/前面/lock/cancel、state2/ACK/UNKNOWNからの入口拒否、一回使用済み、候補/partial/full/GOLD/ITEM/DOOR/保護/近傍/STONE消失を拒否する。
4. 旧FR119の方向変更6件、115のsource更新、076/113の固定待機・未送信、初歩unit/旧回復とUNKNOWN無再送を直接関連として選ぶ。対象successの全原Scene/packetと正常NEG→durable→実RSは担当側の保持検査を再利用し、本件がdurable完了や商品陰性の資格を追加しないことを確認する。

Runtime/Swift/通信/worker/writerは変更しない予定で、全Runtime worldの再実行は既定にしない。Cの新資格が既Runtime guardへ渡る境界はfirst normal unitまでの公開Cと既送信直前時計試験を選ぶ。変更がRuntime入力境界へ及ぶ場合は実装前に計画と限定Mac試験を追加する。独立差分レビュー1回、必要なIPA/seal/全source同一性確認、次の通常1-1実機へ進む。未収録の未来到達・全商品/RS・速度は実機未確認として残す。

## 実装・限定検証

raw履歴deltaを含む独立設計確認P0/P1/P2なし、root GO後に公開fixtureの第一意味Redを出荷123で確認した。正規cycle/irregular/continuous/初回RS→275ms ACK→新FLOOR→通常fit/LEFT unit→FRESH/SAME2/2を公開APIで獲得し、原UNKNOWN/現在strict零/同完全LEFT判断を満たして旧SCREEN17で失敗する。初版fixtureのoutside FLOORではtargetが1セル遠かったため、その前提失敗は別保存しRedに数えず、outside UNKNOWN/観測床だけの形へ訂正した。

新11件は凍結C156c5c95でGreen。旧123に最終同fixtureを渡すと14assertion失敗/errors0となる。履歴arraybytes/count保持と旧model0/slot0/epoch0、actual tick前captureの不採用、A新mode1/B新model採用、元schedule内の将来新ID、275ms ACKと元visual内の通常unit、実unit後もlevel一回、遅いfitの停止、actual commit越境の無加点、候補/取消/owner/UNKNOWN無再送を確認した。これは公開C componentのprocedural証明で、原iPhoneの未収録未来ではない。

直接関連は119の旧方向変更6件、115 source4件、076 passage未送信6件、076 stationary8件、123 raw保持1件の計25件を選択した。24件は合格し、076の旧`test_ready_or_issued_unknown_does_not_reopen_the_same_wait`だけ2subassertが不合格（期待SCREEN17/実際0）。exact出荷123Controllerでも同じ2失敗を確認した。後の115のREADY/ISSUED再観測と旧fixture期待の既存不整合で、今回はassert変更/skipや無関係な製品修正をしない。新DATAはcycle/irregular/yield限定で、この旧通常profileに資格を追加しない。

Git外`test124-firststep/implementation`へ凍結core、owned差分、Red/Green/関連・旧版限定比較を保存した。一般`clear_model`/`add_sample`、旧route-change/strict proof/quiet関係とNav/Perceptionのbyte不変を確認する。新actual tick fenceはCの専用modeだけで、Runtime/Swift/POD/APIを変更しない。独立最終差分レビューと統合sourceの確認は別に記録する。

## 独立レビューP1: DATA中に見えたactual GOLDの通常経路へ渡す

初回凍結C156c5c95の独立差分で、clear DATA handlerが新actual GOLDを単に待ち続け、旧`update_passage_wait`のGOLDへの移行を抑止するP1を検出した。公開earned反例ではstage1で新GOLD後Aの新fitが作られず、stage2では旧clear modelが撤回されない2意味Redを保存した。初回凍結を最終合格とはしない。

rootが追加差分をGOした。入力0・未発行のstage1/2だけ、clear入力資格を撤回して別GOLD modeへ渡す。新actual GOLD/正の原点/GOODS_UNKNOWN/既normal chooserの完全Decisionを要求し、新GOLD画像を別の固定DATA anchorにする。元退役票・位置/visits/mouth/prefix・元P/W/schedule/visual・usedと共有counterは不変。旧model/slot/proofは再び撤回し、raw履歴だけを保持する。actual tickの新barrier後に、GOLD anchor→独立A/Bの通常strict零、同全tiles/保護/全GOLD/完全normal Decision、新fitとB sample採用を再証明する。triggerのGOLD画像1枚だけで新票を出さず、clear proofへGOLDを追加許可しない。

B後だけ`passage_active=0`の通常shop chooserへ渡し、その完全Decisionが認めるFLOOR/DOOR/DIRT一回を元上限の新IDへ結ぶ。隣接扉/土壁を一律holdにする新しい退行は作らない。既通常Motionの実MOVEDだけ+1歩、実DOOR_OPENED/TERRAIN_OPENEDは0歩で新witnessを終え、既開通後処理へ渡す。ACKだけ、UNKNOWN/TWEEN、確実未送信・期限超過でusedや新GOLD資格を再armしない。発行済みstage3/begun/ACK/UNKNOWNを新GOLD DATAへ救済しない。normal chooser、旧開扉/retune helper、一般model/budget値とRuntimeは変更しない。

追加公開fixtureはstage1/2→新GOLD→独立GOLD A/B→通常FLOOR unitに加え、隣接DOOR/DIRT→既通常の0歩開通を確認する。proof不足/材質・GOLD差/保護/候補・取消/元期限・旧ID拒否も残す。新機能の数式上の可能性と元iPhone未来未確認を分け、追加差分を独立再確認する。

GOLD追加設計の独立確認P0/P1/P2なし、P1反例と隣接DOOR/DIRTの2＋2意味Redを製品差分前にC156c5c95で保存した。追加後の凍結C734e6bbbで公開14件と直接関連119/115/076の16件が合格した。DIRT fixtureの未到達末端にあったTERRAIN enum6の誤記はCore正本の4へ訂正し、誤記前後で前段の意味Redが同じ新fit不足であることを区別した。新GOLD modeはnormal chooserの全5fieldを使い、開通の0歩creditを元helperへ任せる。旧13helperとroot1所有helper/callerの保持を再監査し、最終独立差分でP1を閉じる。

最終独立差分はC734e6bbb/公開14件/関連16件の同一freezeを確認し、元GOLD P1解消・残P0/P1/P2なしで閉鎖した（Git外`test124-review/root4-final-review.json` SHA94f017ac）。元13helperとroot1新2helperのbyte保持も照合済み。root2/5と統合した最終shared C、CI/IPAと実機受入はrootの別工程で、ここで完了扱いしない。
