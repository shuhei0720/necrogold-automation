# 明示的イレギュラー再試行契約

2026-11-17（日本時間）。[計画](../plans/test110-irregular-retry.md)の新規契約。実装・実機改善確認済みという意味ではない。通常入力の[契約](native-control.md)を維持し、以下の追加だけを明示選択する。

## 識別と互換性

APIは `1.98.16-ngg2`。追加capabilityは `necrogold_native_irregular_v1`、profileは `normal-1-1-irregular-v1`、queryは `necro_native_irregular`、envelope schemaは `ngg2-irregular-cycle-v1`、client journal revisionは `native-irregular-v1`。旧cycle capも必要。新queryは旧cycleと同じmode/引数の閉集合を持つが、別profileのrun/spoolを拒否する。`necro_native_start`への明示profile指定だけが選択権限であり、reply内のprofileからclientの権限を変更しない。

旧profile/query/envelopeの既存8 payload key・command kind1〜4・保存schemaは不変。新profileのstatus payloadだけ既存8 keyへ `irregular` を1個加える。既存Scene/ControllerStatus/Event/CycleStatusのlayoutは不変。新kind5は `DEATH_CONTINUE` であり、新profileの有効なcore以外は予約/begin/入力/受理しない。

## 同一画像からの別観測

`NG2Core.h` に次のABI1構造体を追加する。全fieldは32-bit、合計288 byte。旧 `ng2_analyze_rgba` の出力は変更しない。

```c
enum { NG2_IRREGULAR_IMAGE_NONE=0, NG2_IRREGULAR_IMAGE_DEATH=1,
       NG2_IRREGULAR_IMAGE_RESTART=2, NG2_IRREGULAR_IMAGE_ENEMY=3 };
enum { NG2_IRREGULAR_SCAN_RESTART=1 };
typedef struct {
    uint32_t abi_version,struct_size;
    int32_t kind,glyph_intersection,glyph_union,hud_mask;
    int32_t empty_hearts,matches,left,top,width,height;
    int32_t heart_inter[3],heart_union[3],heart_red[3],heart_dark[3],heart_bright[3];
    uint32_t enemy_mask;
    int32_t enemy_matches[4],enemy_inter[4],enemy_union[4];
    int32_t enemy_left[4],enemy_top[4],enemy_body_luma[4];
    int32_t enemy_body_saturation[4],enemy_red_outside[4];
    int32_t enemy_heart_count[4],enemy_width[4],enemy_height[4];
} NG2IrregularObservation;
int ng2_analyze_irregular_rgba(const uint8_t *,size_t length,size_t stride,
    uint32_t flags,NG2IrregularObservation *);
```

RGBAは896×414、stride/length/opaque alphaを通常decoderと同じ条件で検証する。不正入力はNONE・権限なし。flagsは0又は1だけ。restart scanは死亡続行ACK後の待機だけで1にする。kind優先はDEATH→RESTART→ENEMY。enemy indexはdirection−1（LEFT/RIGHT/UP/DOWN）、mask bitも同じ。matchesは0/1/2（2は2以上又は曖昧）で1だけ受理する。HUD maskはfooter1/zone1=2/floor1=4/pause icon8。Cはabi/size、全数値範囲、必要count/geometry/maskを再検証し、未知field値で権限を増やさない。

Runtimeはnewprofileのcapture workerで、同じimmutable RGBAから通常Sceneとこのcompanionを作る。既存のrun/generation/owner/取消・取得両端・stable/prefix・commit時計gateを通して同時にCへ渡す。別capture/run/prefixのboolを合成しない。

### 正のDEATH

固定box `(312,312,270,24)` 内の既存全文template522 bitに、通常neutral条件とgrey>=140を適用する。全box IoU>=.64、参照被覆率>=.90を両方必要とする。HUD mask15、既存continue labelなし、次の3heart全数の証明が必要。heart中心x=695/724/753、全shape box `(cx−12,6,25,25)`、参照382 bit、IoU>=.90かつ被覆率>=.95。内側 `(cx−8,10,17,18)` のred総数>=225、dark red `40<=r<=124,r−g>=25,r−b>=25` が192以上、bright red `r>=125,r−g>=45,r−b>=45` が48以下。黒領域や単なる赤減少を死亡証拠にしない。入力座標は全文box中心から通常の向き変換で `(90,447)`、この実観測boxにのみ従属する。

R12既知死亡画像での全文476/727・3shape374/397以上と、今回98枚/294heartの否定で校正した。今回の実機死亡/続行後menuは未受領である。

### 正の対象セルENEMY

方向ベクトルに対し `cx=448+36dx,cy=207+36dy`。red条件は `r>=125,r>=g+45,r>=b+45`。候補barの中心/bbox条件を維持しつつ、抽出には固定guard域 `[cx−68,cx+68)×[cy−43,cy−4)`（136×39）を使用する。8近傍連結componentの全体bboxを先に抽出し、切り抜いたcomponentを照合しない（「8」はcomponent数上限ではない）。1方向5304pixel、4方向21216pixelで有限走査する。qualified markerは参照被覆.93以上、すなわち128以上のinkを必要とし41個以下なので候補配列64で足り、overflow時も切り捨てず拒否する。各markerは全glyph137 bit/正確な15×13で全box IoU>=.90かつ参照被覆>=.93。markerの横step17..19、全chainのmax(top)−min(top)<=1で、同じ整列chainに属するqualified markerを全数含むmaximal barを作る。1〜3 markerのみ受理し、4以上/部分/曖昧barは拒否する。隣接ごとにtop差1でも全体で0,1,2と階段になるchainは拒否する。別chainの隣接batを当該barへ合併しない。中心付近の3markerだけを切り出す処理はなく、guard内の4個目を含めてmaximalityを検査する。左右の4個目が旧68px抽出域で切れる反例も4個chainとして拒否する。

実whole bar bboxはwidth `15+(17..19)*(N−1)`、height13..14、中心横差<=6、縦差 `T+H/2−cy∈[−32,−12]`、全bboxが有限探索域内。その方向に唯一の受理barでenemy_matches1、heart_count=N1..3とする。inter/unionはmarker個別boxの単純合計ではなく、gap/paddingも含むwhole bar bbox上に全参照を配置して測定する。参照bit数137*N、`enemy_red_outside=union−137*N` が64以下、aggregate IoU>=.90/参照被覆>=.93もCで再検証する。独立したbody域 `(cx−14,cy−9,29,24)` にgrey>=70を48以上、maxRGB−minRGB>=40を96以上必要とする。miniheartだけ、背後/別方向、複数の受理barは許可にならない。

今回98枚×4方向ではfe54の3枚RIGHTだけが正、実際に指示したLEFTは負。RIGHT入力後の閉塞を実機確認したとは扱わない。

### 死亡後のQuick Restart

既存全文181×28/223 bitを変更せず、neutralかつgrey>=180で照合する。中央ROI `[160,736)×[60,360)` 内のtop-left x=160..555,y=60..332を整数step1（108108 window）で有限走査。観測white数212..237を先に検査し、全box IoU>=.94かつ参照被覆>=.95。部分切り出し/scale変更なし。最良候補からChebyshev距離2以内だけを1clusterとし、2より遠い受理originが1個でもあればmatches2として拒否する。連鎖的なcluster結合はしない。

独立したfresh/current-generation/prefixの2画像で中心差<=2、死亡promptなしを必要とし、episode Dを更新しない。座標は中心 `(L+90.5,T+14)` から `touch=(414−centerY,centerX)`、.5を上へ丸める。既知box357,256は `(144,448)`。98枚の全走査では6枚PAUSEだけが唯一一致。他92枚は0、死亡後の未知menuを認識できたという証拠ではない。

## Controller追加API

```c
int ng2_controller_enable_irregular(NG2Controller *); /* 最初のobserve前に1回 */
void ng2_controller_observe_irregular_at(NG2Controller *,const NG2Scene *,
    const NG2IrregularObservation *,uint64_t id,uint64_t start,uint64_t end,
    uint64_t prefix,int32_t stable,uint64_t commit_ns);
int ng2_controller_irregular_status(const NG2Controller *,NG2ControllerIrregularStatus *);
int ng2_controller_irregular_ring_settled(NG2Controller *,uint64_t episode,
    uint64_t job,uint64_t source_capture,uint64_t prefix,const NG2RingResult *,uint64_t now);
int ng2_controller_irregular_durable(NG2Controller *,uint64_t episode,
    uint64_t trigger_capture,uint64_t prefix,uint64_t now);
int ng2_controller_irregular_intent_commit(NG2Controller *,uint64_t episode,
    uint64_t command,uint64_t source_capture,uint64_t prefix,uint64_t now);
int ng2_controller_irregular_outcome_commit(NG2Controller *,uint64_t episode,
    int32_t action_kind,uint64_t command,uint64_t capture,uint64_t prefix,uint64_t now);
int ng2_controller_irregular_storage_failed(NG2Controller *,uint64_t episode,uint64_t now);
typedef struct {
    uint32_t abi_version,struct_size;
    int32_t enabled,kind,stage,held_reason,episodes;
    uint64_t episode_id,trigger_capture_id,before_capture_id,live_baseline_capture_id,prefix;
    uint64_t trigger_ns,parent_deadline_ns,proof_capture_id;
    uint64_t continue_command_id,continue_capture_id,pause_capture_id;
    uint64_t restart_command_id,next_floor_capture_id;
    uint64_t durable_ns,continue_intent_ns,continue_outcome_ns;
    uint64_t restart_intent_ns,outcome_ns;
} NG2ControllerIrregularStatus;
```

StatusはABI1。kind NONE0/STALLED1/DEATH2。stage IDLE0/QUIESCE1/CHECKPOINT2/PAUSE3/DEATH_CONTINUE4/WAIT_MENU5/RESTART_READY6/WAIT_RESTART7/OUTCOME8/HELD9。hold NONE0/MENU_UNRECOGNIZED1/DEADLINE2/STORAGE3/CANDIDATE4/UNKNOWN_INPUT5/INVALID_UI6/CLASSIFICATION7/BASELINE_UNAVAILABLE8/LIMIT9/CONTROL_INVALID10。JSON `irregular` はstruct_size以外の上記fieldと同名の閉objectで、kind/stage/held_reasonは上記大文字を小文字にしたstring、enabledはbool、残りはboolではない非負int<2^63。追加/欠落key、未知enum、負数/float/bool-as-intをclientが拒否する。`prefix` はこのsnapshotの現在の既知completed prefixで、既知ACKと対応するfresh観測だけで進む。triggerの元prefixはimmutable trigger frameに保存する。各commit APIのprefixはその操作のsource/outcomeの実prefixと照合する。

## Trigger・phase・入力状態

同一MOVEの既知ACK、入力前lead確認と元period、immutable-beforeのorigin/進行先が観測された非保護FLOORを必要とする。元beforeへの通常strict BLOCKED(dx=dy=0)を独立2画像で確認し、両方で指示方向の正のenemy/bodyが必要。現在originはFLOOR、進行先はFLOOR又は正のenemy/bodyがそのセルを遮る場合だけUNKNOWNを許す。他のGOLD/ITEM/保護は安定。UNKNOWNは床に補完せずWALKにも使用しない。

新profileは最初の通常BLOCKED確認を旧 `finish`/`stationary_gate_refit` より前で捕捉する。残りの元8比較だけで2枚目を待つ。2枚目は1枚目+元period以降、元earliest+元period以降、元visual D内。attempt7/8や期限不足で収まらなければ再試行権限を作らず旧失敗/保持へ戻す。MOVEDは通常確認へ、UNKNOWN/TWEEN/非零は静止に丸めない。敵証明なしのソフトウェア停止やSCREEN全般はtriggerにならない。

| stage | 受理できる入力event/観測 | 禁止/終了条件 |
| --- | --- | --- |
| IDLE | ACK済MOVEの上記2証明、又はfresh正DEATH | RESERVED/STARTEDはtriggerせず実callbackを待つ。UNKNOWNは保持 |
| QUIESCE | 実worker/main/capture callbackのdrain、同jobのRing結果 | 新規MOVE/通常shop job/通常negative処理は禁止 |
| CHECKPOINT | 完全storage予約とfsync成功の同episode durable callback | 保存失敗/取消/owner等変化はHELD、入力なし |
| PAUSE | fresh生存FLOORから通常kind2予約/begin/ACK、fresh PAUSE+label | UNKNOWN/誤prefix/lateは次入力を作らない |
| DEATH_CONTINUE | fresh正DEATHからkind5を1回、durable intent後begin/ACK | 同command再送禁止、失敗STARTEDはUNKNOWN凍結 |
| WAIT_MENU | continue ACK後の最初のfresh画像をoutcome保存。fresh PAUSE+label、live FLOOR→PAUSE、又は上記2枚menu | continue outcome durable前にRESTART禁止。未認識はD後HELD |
| RESTART_READY | fresh UI sourceに従属するkind3、別intent durable後begin | 同episode候補/UNKNOWN/保存失敗/全gate変化はHELD |
| WAIT_RESTART | ACK後fresh正1-1 FLOOR、死亡なし、以前の正live baselineからfingerprint変更 | ACKだけではrestart creditなし。変化なし/UNKNOWNは保持 |
| OUTCOME | 上記new floorとACKをfsync、同episode outcome commit | FULL/PARTIAL/対象が写ってもdurable前は通常shop開始禁止 |
| HELD | drain/診断/回収だけ | 自動復帰/再送/次run開始なし |

最初からDEATHで以前の正live FLOOR baselineがない場合はBASELINE_UNAVAILABLE保持。候補/対象は全stageに優先する。Runtimeは `classificationOutstanding` を消す前・通常negative side effect前に `irregular_ring_settled` を呼ぶ。既に受理した同generation/prefix/job/sourceのbounded workerのpositive/candidate hintは期限後でも保守的保持に使う。キャンセル/deadline/invalid/allocation/kernelはCLASSIFICATION保持。OK UNKNOWN/NEGATIVEは診断だけとしてpendingを閉じ、completed_shops/陰性数を増やさない。

episode Dはtrigger時 `min(trigger+既存4秒transition,walk45秒,session180秒)` で固定。trigger証明の元visual Dは別に維持する。保存/再観測で延長しない。既存12restart/16方向、heartbeat/取消/前面/lock、owner/generation、実input gateを維持する。旧slot/model/ticketを失効させ、実drain後にのみUIを開始する。restart/level数だけをoutcome durable後に増やし、completed_shopsを増やさない。

## 保存の予約・閉payload・回復

旧spool record schema/hashchain/命名規則を変えず、追加kindは `irregular_checkpoint`, `irregular_continue_intent`, `irregular_continue_outcome`, `irregular_restart_intent`, `irregular_restart_outcome`。すべて既存のserialized persistence workerでfsyncし、同run/generation/owner/prefix/取消gate内のC commitだけが権限を進める。

最初のPAUSE/CONTINUE前にepisode予約tokenを作る。重複IDを除き最大16 raw役割（last live baseline/before/zero1/zero2/trigger/Ring source/queued source/fresh death/continue outcome/menu1/menu2/live pause source/pause ACK/restart source/new floor/terminal）、1枚1483776 byte、最大23740416 byteを予約する。44 raw/64MiB・metadata2MiB・memory pin24は増やさない。既存分+予約分が1つでも超えればUI前にSTORAGE保持。既にdurableな同IDは再計上しない。一般writerも未消費予約creditを使えない。

metadata予約は厳密に1304KiB：compact5 record×32KiB、raw envelope16×4KiB、terminal512KiB、PNG metadata44×4KiB、manifest384KiB、receipt8KiB。前2項224KiBはepisode、後1080KiBは最終回収に残す。各上限はpayload単体ではなくschema/run/sequence/hashchain等のenvelopeを含めたcanonical保存byte全体に適用し、実byte数を上限検査する。full reportをcompact recordへ重複しない。既存space preflightに未保存PNG最大88MiBまでの残り・予約raw/metadata・既存temp2MiBも含める。OS空き容量検査は他processに対する排他的な物理予約ではないため、実write/fsync失敗では即保持し次入力しない。

全reservationはrun/episode/prefix/generationへ結合し、実書込分を消費済として計上、未使用episode分だけabort/outcome後に解放する。finalization分はterminal/manifest/receiptまで保持する。releaseは書いた画像/記録を消さず、取消中のwriterが返る前にtokenを別episodeへ再利用しない。pin不足を暗黙の枠増加で解消しない。

各record payloadの閉keyは `irregular`, `generation`, `resources`, `frames`, `observations`, `command`, `ack`, `proofs`, `assessment_hint`。`irregular` は上記status。`generation` は非負整数。`resources` は `{raw_slots,raw_bytes,pin_slots,episode_metadata_bytes,final_metadata_bytes}` の閉非負int object。`frames` は最大16個の `{role,capture_id,start_ns,end_ns,prefix,generation,rgba_sha256}`。roleは上記16役割をsnake_caseにしたもの、SHAはlowerhex64。`observations` は最大5個の `{capture_id,value}` でvalueは288B観測の全fieldをarray含め同名で表現し、frames内の同captureへ結合する。DEATH checkpoint/fresh continue source、2 enemy proof、2 restart menu proofのうち当該recordに使う観測を省略しない（同captureは1回）。`command` はnull又は既存cycleCommandの閉12 field、STALLED checkpointは元MOVE kind4、intent/outcomeは操作に応じ3/5。`ack` はnull又は `{command_id,kind,started_ns,completed_ns,outcome}`、outcomeは `acked`/`unknown`。`proofs` は最大2個の `{capture_id,start_ns,end_ns,normal_motion,dx,dy,enemy}`、normal_motionは `blocked` のみ、dx/dyは0、enemyは上記288B観測の全fieldをarray含め同名で表現する。`assessment_hint` はnull又は `{job_id,capture_id,prefix,status,outcome}`、enumは既存Ringの閉集合。record種別は必須nonnull項を制限する：checkpoint=frames/observations/proofs（DEATH時proofs空可）、intent=command、continue outcome=kind5 ack+最初の後続frame、restart outcome=kind3 ack+new floor。raw hashchain原本をclient都合で書き換えない。

新session provenanceだけ `native_profile` を保存し、absenceは旧profile。未知値/別queryは拒否。continueとrestartの各intent/outcomeを別に検査し、どちらかのdangling intent・unknown ACK・不明inputは回復後も凍結する。古いcallbackや別episode/prefixでcommitを再生できない。exportへimmutable profile/schemaを明示渡し、raw manifestのprofile/hashを維持する。

## 選択試験と実装境界

追加sourceはCore/Controller header+Controller/Perception既存C、Runtime/CycleWire/CycleSpool/CycleExport、NG-G2 registry/cap/owner行、明示protocol specを渡すPython cycle/client/campaign/publication、新TEST110 entry。G1/R12/旧NativeWalk parserを変更しない。

現在sourceの実Swift Runtime fixtureでcapture→analysis→control→main→save callbackとRing positive/quiesce、取消/owner/generation/prefix/storage/UNKNOWN/recoveryを検査する。旧Runtimeに対するpublic新profile prepareの実assertion Redを先行させ、未定義C symbol/compile失敗をRedと数えない。Python3.9は旧閉schema、cap不足start0、cross profile/journal拒否、同UUID回復/UNKNOWN無再送、原本hashとイレギュラー非陰性を検査する。死亡後未知menuやenemy多様性は実機未確認として残す。
