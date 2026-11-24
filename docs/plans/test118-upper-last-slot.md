# TEST118: V2最後の未発行観測slot

## 1. 目的と限定範囲

V2のHHDDDの最後D3だけ、既定の50ms準備を含めて選んだ未発行slotが元route上限に入らない場合に、同じ現在modelのまだ未来にある拍を一度予約できるようにする。V2・既`restart_yield.enabled`・stage2・steps5/horizontal2/down2/inputs4に限定する。V1、先行4歩、通常の50ms準備、route上限P、入力上限、Runtimeは変更しない。旧ticketの時刻を書き換える変更ではない。

## 2. 原失敗と証拠の限界

CI260ではH1/H2/D1/D2の実MOVED後、source93の正常RingがFULL/UNKNOWN/INCOMPLETEを返した。94はrelease後3.926084msに撮影を開始しているため、PARTIAL用early snapshot条件は停止原因ではない。原93→94は通常MotionのBLOCKED零、tiles/保護一致、原GOLD保持、次DOWN実FLOOR非保護、全slot上限<.80である。D1後の80はcaptureに78.596791msかかり、D2は一拍後になった。最後の94のobserve/次tickは、最終保存fit換算の直前拍50ms準備境界を約0.919ms/4.384ms過ぎた。保存next_target185648580613はP185313080237より後で、発行可能入口はT−lead150ms−publication100ms=185398580613となり、Pが先に切れた。

原証拠は`ci260-upper-cause.json`と`ci260-original-scenes.json`に私的保存する。最終保存fitを94当時の未保存rolling modelの再現とは呼ばない。新試験は元の相対時刻を使う公開Cの独立modelとし、次の実Mac全経路とiPhone受入を分ける。

## 3. 資格と変更関数

製品差分は新private helperと`upper_tick`の呼出し順だけを予定する。新field・pending proof状態・ABIは追加しない。helperは既定`prepare_recovery_slot`が計算した未発行slotを必要とし、そのtargetと現在periodによる残routeの予測が元P−80msを越す場合だけ評価する。既定slotが適合する時、既定slotが未計算/失効した時、または旧50ms経路で既にfinishした時は適用しない。

資格は`upper_identity`、V2の最後D3 counter、freshな有効model/`model_capture_id>=proof_capture_id`、最新current/anchor全bytesとjob/episode/metaに結ばれた`upper_same_zero`、既world/floorを全て満たすこと。cycleは正常UNKNOWN/INCOMPLETE採用済み・worker/assessment非実行・positive/candidateなしとし、input_state/current_command_idは0とする。**最新eventそのもの**が同routeのD2で、DOWNのACK/通常MOVED dx0/dy1、元`upper.issued`/last_completed/cycle prefix/upper prefix/現commandのIDとordinalが一致することを要求する。nowはそのACK end以降、current sourceもそのACK end以降でseen/metaが一致する。D2後に予約eventが一つでもあれば最新event条件で失格となるため、旧D3の発行済み/NOT_SENT/STARTED/UNKNOWNや失効ticketを復活させない。D2より前の起動時NOT_SENT履歴は無関係とする。

## 4. 新slotと元境界

同じ現在modelから`ng2_next_target(model, now, lead)`で新候補をlocalへ計算する。新NBは厳密にnowより未来、残準備は旧`INITIAL_PREPARATION`未満、新targetは既定targetより前とする。さらに、D2の不変targetと凍結command periodから一拍後を求め、既`corrected`の同physical-beat写像と新targetの一致を要求する。単なる過去targetとの大小比較ではなく、D2の次の未発行physical beatだけを使う。既定targetの不適合と新targetの`upper_budget`適合を両方確認する。period/target/next/加減算は既NS_LIMIT内でoverflowを先に拒否する。

新deadlineは新NB+既10msと既計算済みslot deadline/fresh horizonとのminとする。visual horizonは旧slot visualと現在source/model鮮度、session/root、walk45、cycle continuation、upper Pのminより増やさない。scheduleは旧schedule、新target+periodの通常schedule、visualのminとする。新NBにも既`INITIAL_PUBLICATION`100msと`CONTINUOUS_SOURCE`200msを適用し、一般のFRESH3sで代用しない。`tail=lead+50ms`の鮮度余裕は準備例外と別であり維持する。全guardとlocal値の整合が成立してから未発行recovery slotをpublishし、その同じtick内で既`reserve`を通す。元P・model phase・source・future floor・入力権限は増やさない。

## 5. 実入力境界と失敗

新しいcommand IDだけが既Runtimeの実AX query、generation/owner/foreground/lock/authority freshness、C begin、実clockでのpost-begin/send gateを通る。queryが遅れたら旧と同じNOT_SENTで止まり、10msを延ばさない。begin/ACK/通常MOVEDの前に次の入力を許さず、NOT_SENT/UNKNOWNの再送や同拍への再予約はしない。資格不成立は既定停止へ戻し、新しい不確かなpending状態を残さない。

## 6. TDDと限定回帰

公開C lifecycleで実HHDDの4MOVEDを作り、CI260の93/94の相対capture/worker/release/commit/tick間隔を与える。通常producer形状/元phaseに従う独立modelで、旧版はD3を発行できず、新版は同modelの未来NBと元10ms/P内の新D3を発行する意味Red/Greenを記録する。実AX/sendの成功は公開C試験の範囲に入れず、実Macで別確認する。

新3method内のsubcaseは、左右の最後D3、既定slot適合時の通常50ms、feature-off、先行D2、prefix/有効HUD phase矛盾、正候補、未知/保護床、過去NB/元P失効、公開済み/NOT_SENT/UNKNOWNの再発行拒否、通常MOVED後だけのD3 creditを実行する。Pとcounter不増、source/target/10ms固定も確認する。既upper7、begin cache8、snapshot3、直接V1関連3を合わせた**全24method（新3＋既21）**を限定回帰とする。

guardごとの区分は私的検証receipt`last-slot-guard-map.json`へ対応付ける。anchor/job/current全bytes等の既proof比較や、owner/cancel/beginの既境界は関連回帰と静的source確認を分けて記録する。publication100ms/source200ms/tail50ms、個別session/walk/input cap、reserve0清算等は新経路の専用negative注入を全て実行したとはせず、未実施部分と静的proofを明記する。新3の合格で全guardを個別に動的実証したことにはしない。

## 7. 順序と保存

8項目設計の独立P0解消とroot承認の後、旧意味Red→最小C→限定Green/回帰→正式source/test/function SHA freeze→同fixture/clock/ACK/phaseの実Macへ進む。原失敗を保存し、旧Redを成功試験で上書きしない。元相対時刻の公開modelと原live clockを区別し、実MacのHHDDD→正常FULL判定→耐久RS→次childを確認するまで全経路成功とはしない。

## 8. リスクと対象外

50ms未満では実AX準備が間に合わない可能性があり、失敗は既NOT_SENTで閉じる。CI260 Macでの短いquery費用はiPhone保証にしない。P/worker/source/10msの延長、一般の準備50ms変更、数値20ms/45ms等の新しいmagic threshold、Runtime/renderer/camera/ACK/phase変更、新periodへの付け替え、未来画像や床の補完、既発行/失敗ticketの復活、通常profile/V1への拡大は対象外とする。
