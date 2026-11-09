# TEST061: 商品確認まで継続できる制御の設計

2026-11-10（日本時間）。状態: 設計第2周の3観点clear、実装前。商品到達を実機で保証した記録ではない。最新ユーザー指示は品質維持・固定時間なし・影響範囲に応じた検証。

## 1. 概要

初歩の拍取得、発行済み入力、ACK後の画像確認、未発行の次拍を別の状態・期限にする。古い入力を再送せず、確実に未送信の初歩は古い候補/IDを撤回して再同期する。ACKが確定したMOVEは元画像で最大3回の変位確認を続け、真のMOVED/開通を確認してから次の行動へ進む。通常の高速経路は従来どおり毎拍、確認が遅れた場合は未発行の次拍を破棄して新しいlive位相から再開し、拍の間隔を診断へ残す。

## 2. 背景と証拠

原TEST060 ZIP SHA `86d8e4e6dab068d10a152292502a23d53caadc0af1dd682d3151ee83d8f4d2fd`。第1runはMOVE予約前のBEAT停止で、準備上限より117.948ms早い。具体的track内訳はmodel/sample未保持で未確定。第2runはLEFT ACK後、原motion期限まで227.408ms、最初の安定画像をACK後35.294msに取得し、その判定はUNKNOWN。残80.458msで次の確認が間に合わず期限+2.603msで停止した。

原32の地形は34〜35px移動、既存35px UNKNOWN/36px MOVEDの区別を維持する。原27へ戻してもUNKNOWN。静止字幕が原因という根拠もない。原27/28のplannerはLEFT、原32を仮に位置(-1,0)と置く限定probeでは次UP/前方4FLOORであり、Navを作り直す根拠はない。旧038/040/042の閉扉・商品認識は保持するが、開扉だけの中間実画像や未収録の次画像を成功の証拠にしない。

現在の次拍期限はlead450msではtarget後75〜90msとなり、画像確認earliest=target+80msとほぼ重なる。入力期限と視覚確認期限の結合は初歩以外の有限lead試行にも影響する。

## 3. 詳細設計

### 初歩の同期再取得

適用は最初の実MOVE開始前（inputs/moves/lead_confirmedすべて0、取消/商品/終了なし）。未発行candidate、またはC input_state=1の確実に未送信初歩とその未送信再予約pendingだけを対象にする。state2/3/4・retune・confirmed continuousには適用しない。

track拒否、同拍8%補正失敗、無効/古いmodel、未発行準備窓の取り逃し、初歩ticketの未送信期限切れで、旧IDがあれば元eventをnot_sentとして確定し、旧slot全field/initial_ticket/model/raw samplesを撤回する。replan回数・入力上限・旧eventを消さない。同じobserveでの即refitや旧IDへの期限追加はしない。次の適格HUDから既存2秒span/fit条件で別候補を選ぶ。

元sync開始+12秒、walk45秒/session180秒は再取得を跨いで不変。初回ticket公開前とbeginでも12秒上限を検査し、等号で終了。新しい候補の時刻は新しいlive取得へ結ぶが、既に発行した旧ticketのtarget/notBefore/D/ordinalを書き換えない。旧callbackは元ID不一致で拒否され、新しい状態/leaseを閉じない。retire時はevent内の旧ticketを残し、command/current IDを失効させる。begin/completeの旧ID・状態検査は時計/予算の更新より前に置く。

RuntimeのTicketGuardが期限超過を短絡してbeginを呼ばない場合にも対応する。complete(outcome=0,state1)で初歩の確実未送信かつ純粋な期限超過と確認できた時だけ同じretireへ接続する。期限内のoutcome0、権限失効/取消、state2/4を再取得に変えない。元sync12秒の検査はtick/begin/completeの各再取得入口に適用し、旧ID検査を先に行う。

### 入力と画像確認の期限分離

最初のreserve時に2期限を凍結する。

- scheduleD: 旧来の元次拍notBefore+10msとsource/phase/walk/sessionのmin。高速な次拍継続と限定fallbackの元親期限として保持する。
- visualD: 元source取得開始+3秒、元phase sample+3秒、walk開始+45秒、session開始+180秒のmin。新しい任意のms値は置かない。

SAME/FRESH/初歩再予約でも各期限と元source/phase原点を伸ばさない。MotionWait.deadlineは新しいvisualDを表し、旧scheduleDは別診断へ出す。ABIの既存layoutは変更せず、新capabilityで意味の変更を区別する。

ACK既知state3の同一MOVEだけ、同before・安定ACK prefix・取得開始>=max(ACK,target+80ms)・最大3評価・visualD内で確認する。UNKNOWN/TWEENは位置/leadを更新せず、追加方向入力を出さない。UNKNOWN synth(state4)は引き続きUI凍結・再送/cleanup禁止。

実時計付きの追加API ng2_controller_observe_atを導入し、RuntimeはC呼出し直前のobserveStartを渡す。capture終了<=commit開始<=有効visualDをMOVED/開通/BLOCKED-retuneの全分岐で検査する。旧observe ABIは残し、既知last_nowとcapture終了の大きい方を使う。さらに全proof後の次actualtickまでvisualDを保持し、C呼出し中/直後にDを越えた場合も新入力へ進めない。GOODSは期限切れでも保持し、移動creditだけを与えない。

ACK後のHUD追跡失効は次入力の位相資格を失わせるが、同MOVEの純粋な視覚確認を終わらせない。失効を記録し、次入力前にはlive位相を再取得する。optional原画像fallbackは従来のscheduleD/位相等で自然失効させ、visualDへ延長しない。

### 確認後の継続と再同期

真のMOVED/DOOR_OPENED/TERRAIN_OPENEDだけで位置/開通を更新する。実時計tickがscheduleD・元の次candidate D・valid modelを満たす高速経路は既存の連続拍を維持する。

遅い確認やACK中の位相失効では、旧次候補/未使用reference/preparation資格を破棄して再同期状態へ入る。証明がUNKNOWN/TWEENのまま入ってはならない。旧visualDが実時計上失効した場合は停止し、timestampだけで次入力を復活させない。

新slot即選択にはmodelへ実際に採用されたHUD capture IDがproof画像ID以上であることを要求する。単にbeat_validや古いmodelが有効なだけでは足りない。位相が有効で、確認後の適格live HUDへ追跡できている場合は、そのmodelから準備50ms以上の新しい将来拍を選べる。位相が失効している場合は新しいHUD集合でfitし直す。再取得episodeは最大12秒で、途中の失敗で起点をリセットせず、walk/sessionでさらに制限する。入力開始前の元candidateの失効を新ticketで隠さず、撤回と新規選択を記録する。retune/初歩開通後の新規拍も準備余裕を確保し、旧ticketの取り直しとは混同しない。

通常の毎拍成功と再取得による拍間隔を区別する。再取得で間隔が空いたrunを毎拍・人より高速の受入に数えない。GOODSは画像確認/再取得より優先し、その後方向入力/購入は0。部分商品と保護セル/入口は従来規則を維持する。

### 診断と互換

既存Status192B/Event128B/Scene23864B/MotionWaitのlayoutは維持し、別getterのRecoveryStatusと最大13sampleのqueryを追加する。診断はmodel/raw消去前にsnapshotし、runの最初と最新の2件だけを保持する（1件なら1件）。単調sequence、episode ID、全記録件数/上書き件数で欠落を示す。再fit・最終PAUSE・export後も原snapshotを保持する。

wire `recovery` の閉schemaを次で固定する。topは initial_reacquisitions/post_move_reacquisitions/episode_id/mode/schedule_deadline_ns/visual_deadline_ns/ack_ns/record_count/dropped_records/records。modeは0通常/1初歩再取得/2確認後再取得。recordsは最大2件、各件は sequence/episode_id/reason/clock/at_ns/capture_id/command_id/abandoned_target_ns/sync_deadline_ns/model/samples。reasonは1TRACK/2ALIGNMENT/3MODEL_STALE/4PREPARATION/5UNSENT_DEADLINE/6VISUAL_SCHEDULE/7VISUAL_PHASE/8SYNC_BUDGET、clockは1capture_end/2actual_tick/3actual_commit。modelはNG2BeatModelの全named field、samplesはNG2BeatSampleの7named fieldを最大13件。ns/countはboolでない非負int<2^63、型・有限double・enum・件数・sequence/record_countを検査する。初期はcounter/ns=0、mode0、records=[]。定数payloadで生成を代用しない。

API1.98.15-ngg2/capability necrogold_native_v13/client native-walk-v14。v14の完全native reportはrecovery必須（accepted空応答の補完は応答copyだけ）。新規起動は新cap/APIを要求し、旧IPAを誤って実行させない。v1〜v13既存journalは保存literal/API1.98.14に基づくpreflight/status/result検査で回収を維持する。単にglobal API_VERSIONへ追従させたり全版で両APIを許可しない。旧revisionは新診断の不在可、存在時は同じ閉schema検査を行う。回復時GET0/start0・元UUID/clock/ownerを維持する。


## 4. 影響範囲

Controller.c/h、Runtimeのactualcommit clock/未送信完了経路/snapshot/reportと新公開fixture、clientの互換/診断、RPC version/cap、seal、TEST061 script、focused CI/配布検証、契約/資料。Beat/Nav/Perception/Raster/入力座標/認識閾値は不変。R12原40/G1と保護資産を維持する。主要制御契約の変更なので、設計・網羅・安全の独立重点レビューを行う。

## 5. 新規試験と期待

実装前に旧Cでsemantic assertion Redを記録し最小Green。原060の欠落25画像を補った完全再生とは呼ばない。

- 初歩未発行/確実未送信のtrack・補正・stale・prep/期限失効から、旧IDを再送せず新HUDだけで再取得。旧イベント/元replan budgetを保持。state2/3/4・取消/owner/前面/lock/商品・同期12秒の等号/+1nsで拒否。
- 初歩callbackをD+1nsで実行し、TicketGuardのbegin短絡→complete0から再取得へ入る公開Swift経路を検査。sync12秒以後の遅着、期限内complete0、state2/4、取消/権限失効は再取得しない。retire直後/fit中/新ticket中/新ACK後の旧callbackがstatus/events/時計/期限/preparationを変更しない。
- ACK後track拒否→UNKNOWN→同beforeの真MOVEDをvisualD内で確認し、再取得済み位相までは次入力0。MOVEDとtrack拒否が同observeの場合も検査。valid旧model+proofHUD拒否→即slot0→後続HUD採用後に許可、proofHUD採用済みなら2秒fitを不要とする。
- 原060の時刻と28→32のUNKNOWNを維持し、旧scheduleD通過だけではACK視覚確認を閉じない。明示した合成35px UNKNOWN→36px MOVEDでvisualD内の確認と新規同期を検査。未収録の実次画像とは呼ばない。
- 高速確認は元の連続拍/全凍結fieldを維持。遅いcapture/遅いactualcommitでは旧次拍を出さず、visualD超過なら停止。source/phase/walk/sessionの等号/+1ns、最大3UNKNOWN、UNKNOWN synth無再送、原before/attempt/旧reference/旧IDを復活させない。
- capture終了D-1ms/actualcommit D+1ms、C処理後のactualtick D+1nsを、MOVED/DOOR_OPENED/TERRAIN_OPENED/BLOCKED-retuneすべてで拒否しGOODS優先は維持。確認後episodeの複数失効を跨ぐ元12秒と将来拍prep50msの等号/+1nsも固定する。
- 初歩/retune/木鉄扉/茶壁/continuous/SAME/FRESH、開通0歩→進入1歩、LEFT→UPの曲がり→扉出現→商品/PAUSEまでを関連C/Swift結合で確認する。部分商品/全保護/取消/drain/manifestの境界も該当scopeへ含める。
- 商品までの結合は既存SmallShopWorld等の独立地形/位置がoracleのfocusedケースを使う。「1入力後の指定時刻で商品を表示する」.walk fixtureは経路成立の代用にしない。world160/全59の再実行はこの根拠だけで要求しない。
- 新client v14/.15の旧IPA mismatch、started v13/.14のready preflightを含む旧回収、v1〜8 legacy/v9単chunk/v10〜12batch/literalの既存回帰を対応させる。recovery欠落・余剰key・bool/int混同・非有限値・範囲外・14sampleを拒否する。
- 実Runtime/Cがcapture失効とactualtick失効で生成したmodel/sample/reason/clockを、消去→refit→最終PAUSE後も保持し、暗号結果→client→両journalまで結合する。固定payloadだけでproducer成立を主張しない。新境界のrollback faultは指定assertionで検出する。

## 6. 実装順

設計重点レビュー→CのRed/期限・同期分離/新診断→Runtime公開経路とclient/互換→関連単体と結合・独立実装差分レビュー→focused標準Macビルド→配布物/全source照合→具体的TEST061実機依頼。レビュー修正は最大3周。試験基盤の無関係な修理や広いリファクタリングを混ぜない。

## 7. コミット前・配布前の検査

Controller全methodは変更領域が広いため実行し、期待の変更は新契約へ対応させた箇所だけ理由を記録する。新/関連Beat・実PNGの35/36境界・client互換・新Swift公開結合・seal/packageを選ぶ。Beat/Nav/Perception等の不変bytesと過去結果を結び、大規模world160/全Runtime59を毎回は起動しない。

focused CIをdefaultの手動dispatchとし、fullは明示手動の節目へ残す。pushで意図しないfullを開始させない。新fixtureだけを選ぶCLIは未登録/0件/skip/compile errorを合格にしない。IPA build/rawPBX/4C/5Swift/6RSP/22seal/APIcap/全9Mach-OのHOST非混入/完全source ZIP照合は維持する。試験sourceとIPA sourceは同じpatched upstreamへ結ぶ。

配布後は新IPA更新/完全再起動/Start Server/VPN・disk、通常1-1金壁可視・左側が下/端0のポーズからTEST061。歩行中はゲーム前面、自動PAUSE後にiSHで終了表示を待ちruntime/test-061全ZIPを依頼する。原060再実行は依頼しない。

## 8. 未確認・対象外

次の実機での絶対成功、未測定の毎拍/人超え性能、原32の強制MOVED化、失効ticketの期限延長、UNKNOWN入力再送、購入、指輪判定/周回/耐久の完成は主張しない。Mac実ゲームは未導入。商品到達は実機受入で判定し、到達前停止を成功にしない。
