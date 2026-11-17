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

RGBAは896×414、stride/length/opaque alphaを通常decoderと同じ条件で検証する。不正入力はNONE・権限なし。flagsは0又は1だけ。restart scanは死亡続行ACK後からRESTART begin前の有限待機だけで1にする。WAIT_MENUに加え、custom menuのRESTART_READY・intent保存中/確実未送信予約中も最新画像を再検証し、元episode Dは延長しない。STARTED以降は次UIのためにscanを続けない。kind優先はDEATH→RESTART→ENEMY。enemy indexはdirection−1（LEFT/RIGHT/UP/DOWN）、mask bitも同じ。matchesは0/1/2（2は2以上又は曖昧）で1だけ受理する。HUD maskはfooter1/zone1=2/floor1=4/pause icon8。Cはabi/size、全数値範囲、必要count/geometry/maskを再検証し、未知field値で権限を増やさない。新全文death glyphだけが正でheart不十分の場合、kindはNONEのまま固定death bbox・matches1・glyph countsを保存する。この権限なしのdeath-present観測はMENU/PAUSE/live baseline/changed floorの各UI資格を拒否する。旧の非neutral死亡matcherだけが正で新全文coverageが不足する場合も、NONE・固定death bbox・matches2・旧非neutral全文countsを保存し、旧IoU.64の曖昧なveto専用証拠とする。matches2からDEATH_CONTINUE権限を作らず、strong DEATHはmatches1・新全文・全heartを維持する。

Runtimeはnewprofileのcapture workerで、同じimmutable RGBAから通常Sceneとこのcompanionを作る。既存のrun/generation/owner/取消・取得両端・stable/prefix・commit時計gateを通して同時にCへ渡す。別capture/run/prefixのboolを合成しない。

### 正のDEATH

固定box `(312,312,270,24)` 内の既存全文template522 bitに、通常neutral条件とgrey>=140を適用する。全box IoU>=.64、参照被覆率>=.90を両方必要とする。HUD mask15、既存continue labelなし、次の3heart全数の証明が必要。heart中心x=695/724/753、全shape box `(cx−12,6,25,25)`、参照382 bit、IoU>=.90かつ被覆率>=.95。内側 `(cx−8,10,17,18)` のred総数>=225、dark red `40<=r<=124,r−g>=25,r−b>=25` が192以上、bright red `r>=125,r−g>=45,r−b>=45` が48以下。黒領域や単なる赤減少を死亡証拠にしない。入力座標は全文box中心から通常の向き変換で `(90,447)`、この実観測boxにのみ従属する。

R12既知死亡画像での全文476/727・3shape374/397以上と、今回98枚/294heartの否定で校正した。今回の実機死亡/続行後menuは未受領である。

### 正の対象セルENEMY

方向ベクトルに対し `cx=448+36dx,cy=207+36dy`。red条件は `r>=125,r>=g+45,r>=b+45`。候補barの中心/bbox条件を維持しつつ、抽出には固定guard域 `[cx−68,cx+68)×[cy−43,cy−4)`（136×39）を使用する。8近傍連結componentの全体bboxを先に抽出し、切り抜いたcomponentを照合しない（「8」はcomponent数上限ではない）。1方向5304pixel、4方向21216pixelで有限走査する。qualified markerは参照被覆.93以上、すなわち128以上のinkを必要とし41個以下なので候補配列64で足り、overflow時も切り捨てず拒否する。各markerは全glyph137 bit/正確な15×13で全box IoU>=.90かつ参照被覆>=.93。markerの横step17..19、全chainのmax(top)−min(top)<=1で、同じ整列chainに属するqualified markerを全数含むmaximal barを作る。1〜3 markerのみ受理し、4以上/部分/曖昧barは拒否する。隣接ごとにtop差1でも全体で0,1,2と階段になるchainは拒否する。別chainの隣接batを当該barへ合併しない。ただし全componentが下記の次slotへ完全包含され部分shapeも成立する場合だけ、別barでも曖昧として拒否する。中心付近の3markerだけを切り出す処理はなく、guard内の4個目を含めてmaximalityを検査する。左右の4個目が旧68px抽出域で切れる反例も4個chainとして拒否する。未適格な部分markerも無視しない。全8近傍componentのmembershipを保持し、選択full chain端の次slot（横step17..19・縦top±1）の15×13全windowにcomponent全bboxが包含され、bbox≤15×13・width15又はheight13・56≤count≤152・参照intersection≥56・precision `100*inter>=90*count` を満たす未採用componentがあれば曖昧としてその方向matches2/mask0にする。採用full markerのlabelは除外する。56は137bit glyphの上下左右の幾何半分の最小inkで、noise最大値から選ばない。候補は96個、overflowは拒否、全componentのfirst-N打切りはしない（5304/56<95）。単なるred1px案は既知3枚RIGHTを拒否したため不採用。56未満/full一軸欠落/全消失は真の3markerと区別できる保証がなく、未確認とする。残る中央3個だけをwhole barと認定しない。

実whole bar bboxはwidth `15+(17..19)*(N−1)`、height13..14、中心横差<=6、縦差 `T+H/2−cy∈[−32,−12]`、全bboxが有限探索域内。その方向に唯一の受理barでenemy_matches1、heart_count=N1..3とする。inter/unionはmarker個別boxの単純合計ではなく、gap/paddingも含むwhole bar bbox上に全参照を配置して測定する。参照bit数137*N、`enemy_red_outside=union−137*N` が64以下、aggregate IoU>=.90/参照被覆>=.93もCで再検証する。独立したbody域 `(cx−14,cy−9,29,24)` にgrey>=70を48以上、maxRGB−minRGB>=40を96以上必要とする。miniheartだけ、背後/別方向、複数の受理barは許可にならない。

今回98枚×4方向ではfe54の3枚RIGHTだけが正、実際に指示したLEFTは負。RIGHT入力後の閉塞を実機確認したとは扱わない。

### 死亡後のQuick Restart

既存全文181×28/223 bitを変更せず、neutralかつgrey>=180で照合する。中央ROI `[160,736)×[60,360)` 内のtop-left x=160..555,y=60..332を整数step1（108108 window）で有限走査。観測white数212..237を先に検査し、全box IoU>=.94かつ参照被覆>=.95。部分切り出し/scale変更なし。最良候補からChebyshev距離2以内だけを1clusterとし、2より遠い受理originが1個でもあればmatches2として拒否する。連鎖的なcluster結合はしない。

独立したfresh/current-generation/prefixの2画像で中心差<=2、死亡promptなしを必要とし、episode Dを更新しない。死亡promptのvetoは旧死亡matcher又は上記の正の全文glyph証明（heart条件とは独立）で成立し、心臓が不完全でも新glyph証明をMENU資格へ上書きしない。座標は中心 `(L+90.5,T+14)` から `touch=(414−centerY,centerX)`、.5を上へ丸める。既知box357,256は `(144,448)`。RESTART予約時のUI種類（通常PAUSE/別result menu）をprivateに固定し、intent commitと最終beginの両方で現在UI種類と現在座標を再検証する。PAUSE側も `(144,448)` を必須とし、種類が変われば座標が偶然同じでも旧票を無効にして保持する。98枚の全走査では6枚PAUSEだけが唯一一致。他92枚は0、死亡後の未知menuを認識できたという証拠ではない。

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

新profileは最初の通常BLOCKED確認を旧 `finish`/`stationary_gate_refit` より前で捕捉する。この時点からstatusのproof_capture_id=zero1/before_capture_id=元before/live_baseline_capture_idを保存用IDLE hintとして公開する（episode/input権限なし）。Runtimeはzero1 rawを即座に有限cacheへ保持する。trigger成立後もproof_capture_id=zero1、trigger_capture_id=zero2を維持し、DEATHのproof_capture_idは0とする。新MOVE begin/MOVED/不正/attempt/D切れでは未成立hintを撤回する。残りの元8比較だけで2枚目を待つ。2枚目は1枚目+元period以降、元earliest+元period以降、元visual D内。attempt7/8や期限不足で収まらなければ再試行権限を作らず旧失敗/保持へ戻す。MOVEDは通常確認へ、UNKNOWN/TWEEN/非零は静止に丸めない。敵証明なしのソフトウェア停止やSCREEN全般はtriggerにならない。

| stage | 受理できる入力event/観測 | 禁止/終了条件 |
| --- | --- | --- |
| IDLE | ACK済MOVEの上記2証明、又はfresh正DEATH | RESERVED/STARTEDはtriggerせず実callbackを待つ。UNKNOWNは保持 |
| QUIESCE | 実worker/main/capture callbackのdrain、同jobのRing結果 | 新規MOVE/通常shop job/通常negative処理は禁止 |
| CHECKPOINT | 完全storage予約とfsync成功の同episode durable callback | 保存失敗/取消/owner等変化はHELD、入力なし |
| PAUSE | checkpoint durable後に取得開始したfresh生存FLOORから通常kind2予約/begin/ACK、fresh PAUSE+label | UNKNOWN/誤prefix/lateは次入力を作らない |
| DEATH_CONTINUE | checkpoint durable後に取得開始したfresh正DEATHからkind5を1回、durable intent後begin/ACK | 同command再送禁止、失敗STARTEDはUNKNOWN凍結 |
| WAIT_MENU | continue ACK後の最初のfresh画像をoutcome保存。fresh PAUSE+label、live FLOOR→PAUSE、又は上記2枚menu | continue outcome durable前にRESTART禁止。未認識はD後HELD |
| RESTART_READY | fresh UI sourceに従属するkind3、別intent durable後begin | 同episode候補/UNKNOWN/保存失敗/全gate変化はHELD |
| WAIT_RESTART | ACK後fresh正1-1 FLOOR、死亡なし、以前の正live baselineからfingerprint変更 | ACKだけではrestart creditなし。変化なし/UNKNOWNは保持 |
| OUTCOME | 上記new floorとACKをfsync、同episode outcome commit | FULL/PARTIAL/対象が写ってもdurable前は通常shop開始禁止。初回floor proofと最初のqualified goods各1枠を固定し、UNKNOWNtailで消さない |
| HELD | drain/診断/回収だけ | 同invocation/campaign内の自動復帰/再送/次run開始なし |

CのtriggerはRing pendingがあればQUIESCE、なければCHECKPOINTへ入る。CHECKPOINTはdurable待ちを意味し、Swift callbackのdrain完了を主張しない。RuntimeはCHECKPOINTでもclassification/main/inflightと当該capture callbackの実drainを別に確認してから予約/writerを開始する。pendingがある場合はring_settledで閉じた後CHECKPOINTへ進み、durable APIはCHECKPOINTのみで受理する。

IDLEでも最初の適格enemy零画像の `proof_capture_id` とbefore/live baselineを保存用hintとして公開する（episode_id0でも非零可）。Runtimeはこの時点から必要ID集合だけのimmutable RGBAを保持し、period離れの25枚以上後続captureでも最初の証拠を失わない。hintだけでUI権限を作らない。trigger後proofはzero1、triggerはzero2へ固定し、最初からDEATHのproofは0とする。

STALLEDのcheckpoint durable後、stagePAUSEかつinput0（未予約）でfresh強DEATHが来た場合だけ、同episode/trigger/親D/旧証拠/全予算を維持してkindDEATH・stageDEATH_CONTINUEへ切替できる。初回checkpointのSTALLED原本は書換えず、kind5 intentにそのsourceのfresh_death rawと全観測を必須保存する。最初のzero1 proofも保持する。RESERVED/STARTED/PAUSE ACK待ちはこの切替を行わず保持し、新しいcallback境界やepisode/Dを作らない。

OUTCOME中のfirst normal floorはrestart成功証明として固定する。最初のqualified FULL/PARTIALも別1枠でScene/ID/start/end/prefixを固定し、既cycle queued tripleをpending0/job不変のdata-only raw保持hintとして使う。durable後だけ同sourceを通常cycle latch/bindへ1回渡し、初期epochも保持する。後続UNKNOWNで消さず、source clock/Dを更新しない。

最初からDEATHで以前の正live FLOOR baselineがない場合はBASELINE_UNAVAILABLE保持。候補/対象は全stageに優先する。Runtimeは `classificationOutstanding` を消す前・通常negative side effect前に `irregular_ring_settled` を呼ぶ。既に受理した同generation/prefix/job/sourceのbounded workerのpositive/candidate hintは期限後でも保守的保持に使う。キャンセル/deadline/invalid/allocation/kernelはCLASSIFICATION保持。OK UNKNOWN/NEGATIVEは診断だけとしてpendingを閉じ、completed_shops/陰性数を増やさない。

episode Dはtrigger時 `min(trigger+既存4秒transition,walk45秒,session180秒)` で固定。trigger証明の元visual Dは別に維持する。保存/再観測で延長しない。既存12restart/16方向、heartbeat/取消/前面/lock、owner/generation、実input gateを維持する。旧slot/model/ticketを失効させ、実drain後にのみUIを開始する。capture leaseはrequest admissionからJPEG callback後のdecode/両解析・latest handoff/control処理まで保持する。QUIESCE/CHECKPOINTでは新capture admissionを止め、既存leaseとlatestがdrainしてからwriterへ進む。trim直前にも全drainを再検査し、durable後にcaptureを再開する。最初のPAUSE/CONTINUEはdurable_ns以降に取得開始した新しいUI画像をC tick前に待ち、古いsourceの予約を消費してから拒否する形にしない。restart/level数だけをoutcome durable後に増やし、completed_shopsを増やさない。

## 保存の予約・閉payload・回復

旧spool record schema/hashchain/命名規則を変えず、追加kindは `irregular_checkpoint`, `irregular_continue_intent`, `irregular_continue_outcome`, `irregular_restart_intent`, `irregular_restart_outcome`。すべて既存のserialized persistence workerでfsyncし、同run/generation/owner/prefix/取消gate内のC commitだけが権限を進める。

通常観測だけで歴史memory pin24が満たされ得るため、UI前の実callback drain後、serialized persistence workerで既pinの歴史raw・metadata・hashをSpoolへ実fsyncして移送できる。既登録rawとのID和集合と将来未定IDで44/64MiB・metadata2MiB等を検査し、失敗/不足/lateではUIなし保持。同run/owner/generation/episode/prefix/元Dを実callbackで再検査した成功後だけactive before/zero1/zero2/livebaseline等以外の歴史memory pinを外す。raw原本はSpool/全manifestに残し、削除しない。通常pin処理が同じ歴史IDを再挿入してfuture creditを横取りしないよう抑止する。枠や元Dを増やさない。

最初のPAUSE/CONTINUE前にepisode予約tokenを作る。重複IDを除き最大16 raw役割（last live baseline/before/zero1/zero2/trigger/Ring source/queued source/fresh death/continue outcome/menu1/menu2/live pause source/pause ACK/restart source/new floor/terminal）、1枚1483776 byte、最大23740416 byteを予約する。44 raw/64MiB・metadata2MiB・memory pin24は増やさない。既存分+予約分が1つでも超えればUI前にSTORAGE保持。既にdurableな同IDは再計上しない。一般writerも未消費予約creditを使えない。既存record上限512も独立に予約し、未書込compact最大5件とrun最終terminal/published各1件（最大7slot）を確保する。frame/PNG envelopeはrecordListの件数には加えず、metadata枠で管理する。最終2slotはrun poolとして重複計上せず、他writerの横取りを禁止する。

metadata最大予約は1304KiB：compact5 record×32KiB、raw envelope16×4KiB、terminal512KiB、PNG metadata44×4KiB、manifest384KiB、receipt8KiB。これは最大値であり、既保存/既予約分を再び加算しない。実予約式は `E=32KiB×未書込compact件数(最大5)+4KiB×future raw件数(最大16)`、`F=512KiB+4KiB×(44−既保存PNG件数)+384KiB+8KiB`。Fはrun単位の1poolで、既に有効なF予約があればepisodeの度に再予約しない。最大E224KiB/F1080KiB。既登録raw IDはfuture raw/envelope credit0、重複したknown roleも1 ID、まだIDが決まらない各future roleだけを最悪1 IDとして予約する。pinも同様に既pin IDを重複計上せず、現在8 pinが全く重複しなくても最大16 future pinなら24内、known roleと3 ID重複すればfuture13以下になるため早期episodeが常に枠不足になる計算ではない。

各上限はpayload単体ではなくschema/run/sequence/hashchain等のenvelopeを含めたcanonical保存byte全体に適用し、実byte数を上限検査する。full reportをcompact recordへ重複しない。実書込byteだけを通常使用量へ移し、完了roleの余剰creditは解放する。未完了roleのcreditとFは保持する。既存space preflightに未保存PNG最大88MiBまでの残り・予約raw/metadata・既存temp2MiBも含める。OS空き容量検査は他processに対する排他的な物理予約ではないため、実write/fsync失敗では即保持し次入力しない。

全reservationはrun/episode/prefix/generationへ結合し、実書込分を消費済として計上、未使用episode分だけabort/outcome後に解放する。finalization分はterminal/manifest/receiptまで保持する。releaseは書いた画像/記録を消さず、取消中のwriterが返る前にtokenを別episodeへ再利用しない。pin不足を暗黙の枠増加で解消しない。

各record payloadの閉keyは `irregular`, `generation`, `resources`, `frames`, `observations`, `command`, `ack`, `proofs`, `assessment_hint`。`irregular` は上記status。`generation` は非負整数。`resources` は `{raw_slots,raw_bytes,pin_slots,episode_metadata_bytes,final_metadata_bytes}` の閉非負int object。`frames` は最大16個の `{role,capture_id,start_ns,end_ns,prefix,generation,rgba_sha256}`。roleは上記16役割をsnake_caseにしたもの、SHAはlowerhex64。`observations` は最大5個の `{capture_id,value}` でvalueは288B観測の全fieldをarray含め同名で表現し、frames内の同captureへ結合する。DEATH checkpoint/fresh continue source、2 enemy proof、2 restart menu proofのうち当該recordに使う観測を省略しない（同captureは1回）。`command` はnull又は既存cycleCommandの閉12 field、STALLED checkpointは元MOVE kind4、intent/outcomeは操作に応じ3/5。`ack` はnull又は `{command_id,kind,started_ns,completed_ns,outcome}`、outcomeは `acked`/`unknown`。`proofs` は最大2個の `{capture_id,start_ns,end_ns,normal_motion,dx,dy,enemy}`、normal_motionは `blocked` のみ、dx/dyは0、enemyは上記288B観測の全fieldをarray含め同名で表現する。`assessment_hint` はnull又は `{job_id,capture_id,prefix,status,outcome}`、enumは既存Ringの閉集合。record種別は必須nonnull項を制限する：checkpoint=frames/observations/proofs（DEATH時proofs空可）、intent=command、continue outcome=kind5 ack+最初の後続frame、restart outcome=kind3 ack+new floor。raw hashchain原本をclient都合で書き換えない。

新session provenanceだけ `native_profile` を保存し、absenceは旧profile。未知値/別queryは拒否。continueとrestartの各intent/outcomeを別に検査し、どちらかのdangling intent・unknown ACK・不明inputは回復後も凍結する。回復invocationは同UUIDの読取だけで0startとする。現在プロセスのUNKNOWN poisonは別UUIDの入力も拒否する。ユーザーがゲームを通常1-1ポーズへ戻し明示実行する別の実機テストを恒久禁止する契約ではなく、自動campaignから環境再設定を仮定して次runを作ることは禁止する。古いcallbackや別episode/prefixでcommitを再生できない。exportへimmutable profile/schemaを明示渡し、raw manifestのprofile/hashを維持する。

## 選択試験と実装境界

追加sourceはCore/Controller header+Controller/Perception既存C、Runtime/CycleWire/CycleSpool/CycleExport、NG-G2 registry/cap/owner行、明示protocol specを渡すPython cycle/client/campaign/publication、新TEST110 entry。G1/R12/旧NativeWalk parserを変更しない。

現在sourceの実Swift Runtime fixtureでcapture→analysis→control→main→save callbackとRing positive/quiesce、取消/owner/generation/prefix/storage/UNKNOWN/recoveryを検査する。旧Runtimeに対するpublic新profile prepareの実assertion Redを先行させ、未定義C symbol/compile失敗をRedと数えない。Python3.9は旧閉schema、cap不足start0、cross profile/journal拒否、同UUID回復/UNKNOWN無再送、原本hashとイレギュラー非陰性を検査する。死亡後未知menuやenemy多様性は実機未確認として残す。

新profileのkind5 ACKをstatus・export内controller snapshot・保存journal再読込まで通し、既知ACK prefixは進むがMOVE credit・motion-reference行・restart成功数・商品陰性数は増えないこと、旧profileでは同eventと新companionを各境界で拒否することを検査する。
