# iPhone 8: capture-only buildによるproduction原JPEG probe

2026-11-16（日本時間）。**設計レビュー完了 / 実装・host検証中 / 未配布 / 入力権限なし**。Round 3の独立レビューと、実装で判明した完了境界の限定確認を記録する。実機受入は未実施。

**最優先制約:** 完成版は8/11同一IPA・共通gameplay処理、端末別geometry/input profileとする。本書の8専用capture-onlyは原画観測を終えるまでの一時診断で、本番実機検証の別実装へ発展させない。本incrementでは11へ接続・導入せず、TEST107配布tag/既定launcherを変更しない。通常build/11の座標・capture/raster・認識閾値・既API/ABI/cap/profileを保持する。8/hostの成功を11受入に代用しない。

native基準は `95eb3b9a94abd053cadb17b756667598aaff09c7`、調査時のdocs-only HEADは `f64e694`（nativeはTEST107から無変更）、固定upstreamは `6e25cf6a9f65bc86c372cdce94bdb151d0cf6767`。実装前に最新commit/diffを再固定する。正本は `AGENTS.md`、要件 `docs/requirements/necrogold.md`、native契約、開発フロー、architecture/testing/review規則、`docs/testing.md` と本書。Git外のgeometry草案を必須入力にしない。

## 1. 概要

**明示した8専用capture-only実験build**を作り、組込みXCTestからproductionと同じ `XCTScreenshotRequest` / `public.jpeg` / quality要求0.6 / `CGRectNull` で原JPEGを一回だけ読む。通常serverへ診断modeを動的に切り替える機能は加えない。

このprocessではlegacy UI automation/capture/stream/preview/cycle/native producerを一度も生成・登録・開始しない。新probe専用bridgeだけを実行し、旧 `requestJPEG` 本体・ObjCException/ScreenStream/VTの既capture処理へdrain hookを加えない。通常App root・認証/health等の無関係なUIは作り直さず、capture producerへ到達する入口だけを分岐させる。full coexistence案は今回の正式scopeから外す。

probeはController/Beat/Sceneを生成せず、tap/swipe/launch/terminate/rotate/UI設定/商品判定/購入/ゲーム通知を行わない。UIImage再encode/PNG化/896×414 normalize/aspect拒否も行わない。成果物は私有JPEG原bytesと閉metadataであり、入力geometry・ゲーム操作・START-03・商品到達の成功ではない。

## 2. 背景と設計選択

iPhone 8/iOS16.7.7でTEST107導入/版一致・Start Server・bootstrap/setup・暗号pair/config/logsは成立したとの親担当の実測連絡がある。8でnative runはまだ開始していない。production direct JPEGは未取得。ScreenshotService PNG750×1334とG1 screenshotのUIImage resize/再encodeは別経路である。

既 `NG2CaptureBridge.m:20–76` はdisplay IDのmain prepareと原JPEG request、`NG2Runtime.swift:1986–2005` はnative内呼出しと2秒超過後の実reply待ちを持つ。原JPEG単独RPCはない。既pendingはcallback冒頭で減り、sendのthrowもdaemon終了証明ではない。共存方式では旧app worker/async encode/VTまで完全drain観測が必要になるため、入力未資格の8でproducerを起動しない専用buildを先行する。

旧共存案はGit外に完全保存済み（30,018B、SHA256 `8f44df294edbdbb96f21b21bbaa7a334ea0ecd4c68bad54e1799fe2d9a8157e0`）。source比較memoもGit外に保存し、現正式計画へ旧案の実装を混在させない。旧11資料移送・FR-047-RASTER/FR-092-STARTUP-PORTRAITの問題は未解決のまま区別する。

## 3. 詳細設計

### 3.1 immutable modeとtarget境界

専用buildのSwift compilation conditionを `NG8_CAPTURE_PROBE_BUILD` として明示する。通常buildでは未定義。Kit側の新 `NG8CaptureMode.swift` に純Swift/Foundation値 `RPCServiceMode`（normal/iphone8CaptureOnly）を置き、compile opt-in AND raw `hw.machine == "iPhone10,1"` の時だけcapture-onlyを選ぶ。判定はprocess開始時に一度固定し、unknown/読取失敗/11はnormal。通常buildはsysctlを追加実行せず旧pathへ入る。launch env/RPC/config/profile文字列による有効化・動的切替・自動fallbackはない。

同じKit sourceはApp/AllInOne/UITest/KitTestsへ別々にcompileされ、UITest専用ObjC bridgeはApp/Macから見えない（固定upstream `project.yml:23–29,65–70,117–118,147,229–247`）。Kitからbridge getterを直参照しない。hardware判定はDarwinのraw sysctlだけで、Macはnormal。`UIDevice.model`/marketing-name fallbackを使わない。

serverはinit時の `let mode` を持ち、mode付きschema生成へ同じ値を渡す。process所有のNG8 coordinatorはserver/listenerより長く生存し、listener再生成でも同じinstanceをbindする。既init/default/schemaはnormalを既定として旧field・値・method/cap順序を維持する。global mutable providerを作らない。UITest coordinatorだけが新ObjC entryを呼ぶ。Appとembedded testのcompile opt-in/build identityをarchive/sealで照合し、不一致はbootstrap前に拒否する。

今回の配布は既in-process AllInOne構成に限定し、既trusted local App admin出典を起動前提とする。分離runnerへのloopbackをtrustedに読み替えない。同process出典をbindできない場合はcaptureを開始せず、別の認証経路を即席に加えない。

8 capture-onlyは `service_mode=iphone8-capture-only-v1`、`necrogold_capture_probe_v1` を明示し、実装しないnative/G1/stream capを広告しない。通常build/11のAPI `1.98.16-ngg2`・旧cap/profile/Status/Event/Scene/companion ABI・canonical15/G1/R12/ELF/feature/閾値・元期限/累積予算/UNKNOWN無再送は不変。旧client parserを緩めず、8専用modeでnative cap不足なら入力前に拒否させる。

buildは独立 `patches/loopctrl/iphone8_probe/` overlay/assets/manifest、新applier・dual-seal verifier・専用 `.github/workflows/iphone8-capture-probe.yml` とする。旧G1/G2 applier・manifest・ngg2.patch・NG2資産・通常workflow/source bytesは変更0。固定upstreamへ旧G1/G2を適用し旧sealを検証した後、列挙済preimage/final hashだけをoverlayする。新Kit sourceはshared directoryのApp/AllInOne/UITestへ入り、Mac KitTestsだけexplicit membershipを追加する。新ObjC bridgeはUITestだけへ置く。

overlay projectのglobal compilation conditionは `$(inherited) NG8_CAPTURE_PROBE_BUILD`、AllInOne側の `$(inherited) LOOPCTRL_ALL_IN_ONE` を保持する。command-lineの置換で既flagを消さない。実generated project/全targetの実compiler引数とIPAで確認する。旧sealの例外を緩めず、最終treeは未変更旧pathの旧hash＋列挙overlay pathの最終hash＋全追加sourceの二重封印で検査する。旧verifierをpristine siblingで実行した結果だけをoverlay IPAの証明にしない。

### 3.2 fresh process・旧資料・producer開始0

更新導入で旧processを終了し、専用buildの**新process**で開始する。最初のfresh-process受入を単なるserver Stop/Start、parked runner、既processへの後付けmode変更で代用しない。親担当の「8でnative run未開始」を私有preflight記録へ結合し、前run/未回収の有無が不明なら導入・probeを進めない。通常11や旧run一般の回収をこのmodeで行う設計にはしない。

新processはnormal producerを一度も起動していないことを構造とspyで証明する。新build/hash、runtime ID、process起動情報とinit traceを実機で照合するまでfresh process成立を実測済みとしない。modeを選んだ後に通常初期化を行って停止する方式は採らない。

| 起動入口（固定upstream、native追加はngg2.patch） | capture-onlyで行うこと/開始0条件 |
| --- | --- |
| `AppState.swift:23–55` | persisted autoStartServerはcapture自体を行わないがprobe listenerとportを競合する。capture-onlyではこのnormal app server開始だけ抑止する。通常App root/認証/healthは保持 |
| `RemoteServiceStore.swift:46–53,310–318` / relay・RunnerClient経路 | autoConnectはrelay channelであり直接captureの出典ではないためconstructor/rootを置換しない。転送先のHTTP/RPC/in-processも専用mode gateを必ず通し、producer開始0を検証する |
| `SettingsView.swift:267` / `BroadcastViews.swift:25–72` | ReplayKit開始元はBroadcastRow/Pickerのpress。capture-onlyではこのrow/pickerとsetBroadcast操作だけを構築/実行しない。status/config/log polling等の純読取を作り直さない |
| `LoopCtrlUITests.swift:69–102,392–465` | setUpでmodeを固定し、ActionHandler生成/normal dispatch・capture wiringより前に専用callback設定へ分岐する。既bootstrapの認証/health/log処理を無関係に再設計せず、probe受付前に完了させる |
| `ngg2.patch:37–44,62–64`、`NG2Runtime.swift:417–424` | `NG2Runtime.shared` を生成し得るnative lease/owner-change wiringを登録しない。native/cycle scan/prepare/Controller/通知worker0 |
| `LoopCtrlUITests.swift:660–665,1667–1727`、`ScreenStream.swift:119–142` | normal configure/ScreenStream.shared/grab/onScreenStream/onTouch/nudge/LiveActivityを登録0。persisted broadcast=trueでもstream/broadcast listener/encoder/VT0 |
| `LoopCtrlUITests.swift:493–550` とbootstrapのStart/再Start/URL | 既in-process出典だけのtyped local adminへ分け、§3.3の読取/revoke/pause/限定listener管理以外を拒否する。通常UI/producer dispatchや認証owner偽装への迂回を作らない。probeからURL/app openを起動しない |
| `LoopCtrlUITests.swift:660,922,1929,2555,2599`（全5 server constructor）＋ `AppState.swift:37` | 5箇所を同じmode付きfactoryへ通し、既NG8 coordinator/runtime ID/seen/generationを引き継ぐ。AppStateのnormal listenerは抑止。Start/再Start/port移動/LAN切替でnormal defaultへ落ちないことをassert |
| `JSONRPCServer.swift:558–660,1166–1214` | HTTP `/stream`/`/remote` とbuilt-in stream_ticket/page_update/control等も専用route/method gateで通常handlerより前に拒否。onRPCRequest差替えだけで済ませない |
| `project.yml:74–86,177–198` | 既target/extension/compiler profileは保持し、上記picker/stream listenerの開始入口0を証明する。extension embedの削除やtarget構成変更を既定にしない |

capture-only coordinatorは固定AppSupportの `NGG2Cycles` を**読取だけ**で検査する。ENOENT又は安全に検査できた空directoryだけclean、何かentryがある/symlink/不正type/読取失敗は `old_evidence_blocked` としてstartを拒否する。名前/旧rawをwire/logへ出さず、旧spoolの復元・削除・公開済み推測・新receipt作成をしない。既 `NG2CycleSpool.recover/unpublishedRunIDs` を呼ばず、read-only presence検査だけを行う。受付前にも再確認する。

従って旧status/cancel/results/cycle回収を専用modeの同processで継続する必要は発生しない。旧資料を検出した場合はbusy/deferredとし、通常の既回収環境へ引き継ぐ。新8 buildへの更新で旧memory-only資料を失わせないことは、導入前の8未開始事実で確認する。未知を「資料なし」にしない。

### 3.3 認証基盤と閉じた通過lane

今回は**既承認済みtoken/keyだけを再利用**する。更新導入前に既認証接続・expected install identity・既データ継承条件を確認し、導入後も同じkeyによる暗号認証/identity照合が成立するまでcaptureを許可しない。不明/不一致/継承失敗なら導入又は起動を停止する。新pairが必要ならcapture-only processを終了して通常modeの正規pairingへ戻す別作業とし、このmodeから自動fallback/auto-approvalしない。既install IDの正本は `NearbyIdentity.deviceID`、最終照合は認証済 `config{}` の `nearby.device_id` とGit外expected install ID。tokは認証sessionでありinstall IDではない。未認証whoami/headerだけを根拠にしない。

capture-onlyの `POST /pair` は常時固定 `pairing_disabled_in_capture_only`（HTTP403）で返し、AuthManager.requestAuth・承認UI・notification・approval job・single-auto-approvalを呼ばない。AppのConnect/Allow/Recent Allowはこのmodeではunsupported表示/操作無効とする。既tokenの暗号開封/失効判定は従来どおり使い、鍵やpairing storeを作り直さない。device_infoはAX app.frameを伴うため許可しない。

remoteの認証済 `config{}` は純読取だけとし、server付与peer field以外のcaller keyを拒否する。応答はexpected install確認に必要なNearbyIdentity metadataへ限定する。一方、既Appの `RunnerAdmin.loadClients`（125–131行）はsessions/visibility/LAN/pairing等を読むため、trusted localの `config{}` は従来の `sessions,allow_remote_access,nearby,lan_addresses,pairing,relay_preapprovals` 等の読取shapeを維持する。pending承認を新規作成せず、pairing操作unsupportedをUIへ明示する。local readをremote用の最小応答へ置換してclient一覧/healthを消さない。

trusted localの正本は既 `InProcessRunnerControl.rpc` / pause / listener設定通知を受けた**同processの専用handler出典**とする。そこだけがtyped `trustedInProcess` contextを作り、remoteの暗号RPCとは別の限定admin dispatchを呼ぶ。このhandlerはprocess所有とし、listener停止中もserver?.onRPCRequestへ依存せずstatus/revoke/pauseを処理できる。callerの `_peer_source`/owner/actor/任意origin field、loopback IP、通常onRPCRequest呼出しだけではこのcontextを作れない。HTTP/relayからlocal privilegeへ昇格しない。App rootを再設計せず、既RunnerAdmin経路をここへ接続する。

| trusted local操作 | capture-onlyで許可する範囲 |
| --- | --- |
| config/status/logの純読取 | 既Appが必要なshapeを保持しAX/captureなし |
| `config{revoke_session_id:<existing ID>}` / `config{clear_sessions:true}` | 余剰keyなしの厳格allowlist。同じrunnerのAuthManagerへ適用し、対象probe ownerを即失効扱いにする。App側別cacheだけを消して完了にしない |
| owner pause/resume | 既local出典からRemoteSessionとNG8 gateへ反映し、pause/revoke後の新request/commit/exportを拒否。実jobはdrainまで保持 |
| Stop/再Start、port/LAN/nearbyの既local設定 | 下記listener管理だけ。game/UI/capture producer・pairing承認・native開始を許可しない |

listener管理は一つのmode付きserver factoryに集約し、Stop時はprobeをcancelしてrawを消すが、同processのNG8 coordinator/runtime ID/accepted IDs/history/generationと未終了job/ticketを保持する。再Startは同instanceへ再bindし、旧IDから再captureしない。port/LAN/nearby切替はlistenerだけを再bindし、probeのowner/期限/TTL/seen/取消状態をresetしない。全5 constructorとURL/in-process経路でこの条件を試験する。local UIのStop失敗からURL fallbackでnormal起動しない。実装でこの不変を満たせないStop/port操作はmode中unsupportedと明示して拒否し、所有者revoke/pauseは有効のままにする。通常process終了・更新によるfresh startは別の明示操作である。

HTTP/RPC allowlistは暗号開封後かつbuilt-in branchより前にも置く。capture-onlyではnative全method、screenshot/AX/UI入力/app lifecycle/rotate、stream/preview/broadcast、cycle prepare、ゲーム通知、remote config更新、reset、page_update、URL game commandを拒否する。trusted local adminの例外を通常RPC allowlistへ混ぜず、in-processからprobe ownerを作らない。旧normal serverのdispatch・回収・pause意味は変更しない。

新method専用 `_necro_probe_owner` を暗号開封済token identityから上書き注入しcaller owner/actorを除去する。既 `NG2AuthenticatedOwner` のmethods集合/bytes/意味は保存する。各prepare/request/commit/exportはactive token、非pause、同runtime/probe/generation/cancel epochを再検査する。pause中の新methodは画像なしstatus/cancelだけ。

### 3.4 RPC・有限state・process identity

閉schemaは `ngg2-capture-probe-v1`。processごとのrandom `runtime_id`（32 lowercase hex）を生成し、probe IDも同形式。generationは受付順1..128、cancel_epochは取消時に一度だけ進める。

| 新method | 閉params/意味 |
| --- | --- |
| `necro_capture_probe_status` | `{}` は認証済画像なしbootstrapでcurrent runtime/mode/old-evidence gate。`{runtime_id,probe_id}` は同ownerのcached state。AX/capture/keepaliveなし |
| `necro_capture_probe_start` | `{runtime_id,probe_id}`。runtime不一致は受付前拒否。同owner/accepted IDはcached又はconsumedを返し再取得しない。新IDだけ一回を非同期受付 |
| `necro_capture_probe_cancel` | `{runtime_id,probe_id}`。新prepare/request/commit/exportを禁止しrawを破棄。未終了job中はlease保持。反復はidempotent |
| `necro_capture_probe_results` | `{runtime_id,probe_id,mode:"manifest"}` 又は `{runtime_id,probe_id,mode:"chunk",sha256,offset,limit}`。ready・同owner/runtime/generation・非pause・TTL内だけ。任意path/URL/bulkなし |

accepted ID集合はprobe専用128件、画像なしterminal履歴64件。上限到達は新IDを `limit_reached`、履歴退役後の同IDは `consumed_id` としてcapture0。busy/不正拒否はIDを消費しない。別ownerへstate/rawを返さない。旧nativeのseen/history/予算とは共用しない。

clientはruntime/probe IDを送信前に私有保存し、HTTP start失敗を自動再送・新ID置換・新runtimeへ付替えない。statusで元受付を調べ、runtime変更は元probe unavailableとして終了する。旧要求をrestart後に新captureとして受けない。

stateは `accepted → preparing → capturing → ready`、terminalは `cancelled|failed|expired`。別にdraining/lease_heldを持ち、最初のfailure/cancelをlate成功で上書きしない。status固定fieldsは `schema,service_mode,runtime_id,old_evidence_gate,probe_id,generation,cancel_epoch,state,failure_code,clock_id,accepted_ns,deadline_ns,request_start_ns,callback_body_handoff_ns,callback_return_verified,ready_expiry_ns,draining,lease_held`。未発生値はnull、callback_return_verifiedは常にfalse。owner/raw/端末IDなし。

同時に一probe/一worker/一prepare job/一原bytes。coordinatorの一lockでcheck-and-grant/cancel/commit/raw消去をatomicにする。native/captureとの共存arbiterは作らず、禁止producerが一つでも登録/実行されたら前提違反で固定failure/以後start拒否にする。

### 3.5 新8 bridge entry・取消・完全drain

既 `NG2CaptureBridge.requestJPEG` 本体/quality/旧pending増減位置とファイルbytesは変更しない。独立overlay資産 `NG8CaptureBridge.h/.m` に新entry（例 `requestJPEGWithReply:drained:`）を加え、同XCTrequest形式・API検査・原bytes8MiB上限を持たせる。既native8 callsiteも今回は変更しない。新bridgeを呼ぶのはcapture-only coordinatorだけ。

main prepareは旧production bridgeと同じXCUIScreenの `displayID` descriptor読取だけを新NG8 classのprivate stateへ保存する。旧 `NG2CaptureBridge.m/.h` は完全bytes不変とし、旧private static変数を参照/変更しない。AX app.frame/app.activate/device_info/UI snapshot/public screenshot fallbackを追加しない。capture workerは一requestだけを行い、ImageIO metadata/hash以外の解析をしない。

private send前に専用ticketを設置し、sendの実return/unwind、daemon callback到着、data/getter/copy/例外処理とprimary reply consumerの終了を別に記録する。semaphore signal/consumer reply/既pending減算だけを完了証明にしない。最初のcallbackだけがraw/error候補を提供し、duplicateはgetter/consumerを再実行しない。

この新しい読取専用capでは、上記の全owned work終了後の**最終handoff**をbridge完了境界とする。通知後はdata/getter/consumer/ticketのmutable workを行わない。受け側はnonblocking enqueueだけを行い、AX・解析・hash・待機・coordinator lockをcallback内で実行せず、受け側jobの実終了も別に追跡する。SDKにpost-return ACKはなく、daemon blockのliteral stack returnやdaemon内部cleanupは証明できない。`callback_body_handoff_ns`はこのhandoff時刻、`callback_return_verified=false`を固定し、draining=falseをliteral return成功と呼ばない。これはproducer開始0の8専用probeだけの境界で、旧nativeのdrain契約・lease・入力資格は変更も再解釈もしない。

同期callbackが終了してもsend未returnなら保持し、sendが戻ってもcallback body実行中なら保持する。sendがblock保持後throwした時はrequest_exceptionをラッチし、synthetic errorをdaemon終了としない。保持有無を証明できないthrow枝は実callback finallyが来るまで未解決ownershipとして閉じる。API不在等private send未呼出しを証明できる枝だけdaemon待ちなしで終了できる。強制解放/再送はしない。

受付時 `deadline_ns=accepted_ns+2秒` を固定し、main投入前に独立watchdogを開始、main実行直前/request直前/ready commitで再検査する。reply期限はrequestから2秒か受付deadlineの早い方。queued mainが期限後に動いても新prepare/requestをせずreturnし、実main returnまではleaseを保持する。ready成功で取得watchdogを止め、延長しない300秒artifact TTLへ移る。

leaseは保持raw又は未終了main/worker/send/daemon/callback ticketがある間保持する。readyはdraining=falseでもraw保有のためlease_held=true。cancel/TTL/failureでrawを消し、全実jobが終了した時だけ解放する。never callbackはbounded statusだけ返りdrainingのまま閉じる。HTTP切断を実job終了とみなさない。

### 3.6 原bytes・metadata・回収

原NSDataを再encodeせずimmutable Dataとして一度固定しSHA256を一度計算する。ImageIOはJPEG/count1/各軸1..4096/8Mpx以下/EXIF非bool整数1..8又はmissing=nullのmetadata検査だけ。full raster decode/resize/回転/修復なし。

原bytesは一枚8MiB以下、manifest64KiB以下、chunk raw最大64KiB/wire256KiB以下。limitは最大返却数で非bool整数1..65536。offsetは非bool非負整数で実長未満、offset+limitのoverflow/hashを検査し、end=min(checked offset+limit,byte_length)として最終chunkは短縮できる。同immutable Dataの範囲だけ返し、8MiBなら最大128chunk。readyから固定300秒後は新export不可。全bytes/length/SHA検証後clientが明示cancelする。検証済fragmentをGit外へ保存し、不一致を新startへ変換しない。

manifest固定fieldsは `schema,service_mode,runtime_id,probe_id,generation,clock_id,source_api,requested_uti,requested_quality,format,byte_length,sha256,source_width,source_height,exif_orientation,accepted_ns,deadline_ns,request_start_ns,callback_body_handoff_ns,callback_return_verified,ready_expiry_ns,input_authorized,input_geometry_verified,normalization_applied,device_capture_ns,freshness_verified,scope`。source_api=XCTScreenshotRequest、UTI=public.jpeg、quality=0.6は要求値、format=jpeg、scope=screen、callback_return_verified/authority/geometry/normalize/freshness各false、device_capture_ns=nullを固定する。chunkはschema/runtime/probe/generation/mode/sha256/offset/byte_length/chunk_bytes/data_base64だけ。余剰key拒否。

request/callbackはnative host-side intervalでcompositor生成/鮮度の証明ではない。全画面captureでforeground/game identityを未観測のまま認証済みにしない。原画をnative入力sourceへ昇格させない。failureは未発生null又は固定code `not_available,old_evidence_blocked,trusted_local_unavailable,runtime_mismatch,invalid_request,owner_inactive,unavailable,consumed_id,limit_reached,busy_probe,deadline,prepare_unavailable,api_unavailable,request_unavailable,request_exception,reply_exception,capture_failed,bytes_invalid,jpeg_invalid,metadata_invalid,producer_violation,cancelled,expired` の閉enumにする。pair endpointの固定codeは§3.3で別定義し、承認pending stateは作らない。raw例外/daemon文字列をwire/logへ出さない。私有manifestだけにexpected device/install・transport・build/cap・runtime/probe/hashを結合する。JPEG/full metadata/log/端末ID/IP/team/pairing/鍵はGit外、公開summaryは許可fieldの合否だけ。

## 4. テスト影響範囲

対象はcompile opt-in/immutable mode/起動除外/RPC認証、新8 bridge/coordinator、原JPEG metadata/分割回収。通常build/11 false pathのmetadata/dispatch/source/保護資産不変と既G1/旧native ABI/capture/parserを関連回帰に選ぶ。旧legacy callback/stream/VTへ観測を広げず、未変更Perception/Beat/Controller/world/Ringを形式的に全再実行しない。client変更時は実Python3.9を確認する。

## 5. 新規テストケース

実装前のassertion Red→最小Green。compile/環境失敗はRedにせず、既assert/skip/閾値を緩めない。公開生成JPEGは境界試験だけでゲーム成功にしない。

| ケース | 必須assert |
| --- | --- |
| compile opt-in/実iPhone10,1/expected install一致 | 専用mode/cap、新capture1、全bytes/SHA同一、input/native/Scene/resize/encode/通知0 |
| 通常build/11/別model/unknown/sysctl失敗/App-test flag不一致 | 専用capture0、normal metadata/API/cap順序/旧capture/counter/座標同値。不一致はbootstrap前拒否 |
| persisted autoStart/autoConnect/broadcast true、通常Start/再Start/URL/in-process/HTTP別route | legacy producer init/register/start0、ScreenStream/preview/VT/cycle/ActionHandler/NG2Runtime0。禁止methodにauth ownerを注入しても迂回0 |
| 既token更新継承/失効/POSTpair/Allow/RecentAllow | 継承/identity不明は導入・起動停止。POSTpairは常時unsupported、承認UI/notification/approval job/auto-approval0、normalへの自動fallback0 |
| remoteとtrusted localのconfig/admin、偽origin/loopback/relay | remote更新拒否、caller keyでlocal昇格0。既in-process readはsessions/visibility/LAN/pairing shapeを保持。local revoke/pauseで同runner ownerが実失効し新request/commit/export0、未終了jobはdrain保持 |
| 全5 server constructor＋AppState37、Stop/再Start/port/LAN切替 | 同mode/NG8 instance/runtime/seen/history/generation/元期限/TTLを保持。Stop cancel後も実drain前解放0、旧ID再capture0、停止中もlocal revoke/pause可、normal producer0 |
| fresh process/parked旧process/更新build identity/旧runtime要求 | 新process・mode成立を区別。旧runtime start capture0。server Stop/Startをfresh受入としない |
| 旧spool存在/非empty/不正type/symlink/読取失敗 | old_evidence_blocked、capture0、旧bytes/名前/receipt不変、削除/回復/新start0。ENOENT/空だけclean |
| 128件上限/64履歴退役/同ID/別owner/cancel・TTL後ID | 129件目/退役ID/旧IDはcapture0、別owner payload0、metadata有限 |
| double start/cancel/late/旧generation/pause/revoke | 一勝者、偽owner/actor無効、各commit/export gate、最初terminal reason不変 |
| block保持後throw/保持不明throw/synthetic error後late daemon | 実callback finally＋send return前lease保持、callbackなしはdraining、再送0 |
| 同期callback/send未return、send return/callback getter・consumer fence中、duplicate | 両方完了までready/解放0、duplicate再getter/consumer0、underflow0 |
| main待機2秒超過/prepare中cancel/HTTP切断/never callback | 新prepare/request/commit0、実main/worker/send終了とcallback owned work handoff前lease保持、status有限、強制解放0 |
| final handoff通知のreceiverをfenceで保持 | data/getter/primary consumer終了済み、通知以後のmutable work0。literal callback return未証明をfalseで表示。実adapterはenqueueだけ、受け側job実終了まで別ticket保持 |
| API不在/例外/空/oversize/非JPEG/count/寸法/EXIF不正 | 固定failure、fallback/修復/公開0。EXIF1..8/欠落と896×414以外の合法JPEGは原bytes/metadata正確、normalize0 |
| range/hash/overflow/bool/余剰key/TTL後cursor/fragment再開 | payload範囲内のみ、同artifactだけ、length/SHA不一致を成功/新startにしない |
| 私有sentinel混入 | 公開summary/logにraw/Base64/秘密/端末識別子0。実fresh process/JPEG/drain未実施を成功にしない |

## 6. 実装順

1. このscope変更をRound 3限定独立レビューへ出し、最新commit/diff・専用build名/compile opt-inを固定する。計画改訂だけではnative実装/CI/端末操作を開始しない。
2. 独立overlayのpreimage/final sealを固定し、Kit mode/server metadata/認証allowlistと必要なApp/runner入口だけをRed→Greenにする。App/MacからUITest ObjC参照0、旧normal source bytesと通常build/11 false-path同値を確認する。
3. old-evidence読取gate、runtime ID/128・64/closed parserとcoordinatorを実装。fresh processの構造assertと実機確認項目を分ける。
4. 新NG8 bridge資産だけにsend/callback finally drainを実装し、実ObjC fake daemonのthrow/sync/late/fenceを検証。文字列error注入だけでこの境界を合格にしない。
5. 一worker/main prepare/request/metadata/hash/artifact/chunkを接続し、関連結合と独立差分レビュー。producer開始0や完全drainを証明できなければ残P1とし配布へ進めない。
6. 独立専用workflowの標準macos-26で専用IPAを実buildし、旧baseline seal＋overlay最終seal/実compiler/来歴/保護資産/完全sourceを照合する。正の8専用build番号namespace・独立prerelease/tag/asset名を固定し、匿名download後の全hashも確認する。旧publish tag guard・TEST107配布・既定launcher・通常workflowを変更せず11無導入。
7. 選択した8だけで旧native未開始/未回収なし・旧process終了・新build/process/modeを確認して一回取得。私有全bytes/hash/metadata/transport/cancel/実drainを確認し、geometry計画へ渡す。

## 7. コミット前テスト

本書の改訂・公開source比較の担当作業は文書だけで、native変更・試験・CI・端末操作を行っていない。親担当による別scopeの8端末校正とは区別する。将来は変更した起動/認証/取得/回収境界の関連結合、normal metadata/API/ABI/G1/旧capture回帰、client時の実3.9を選ぶ。範囲外フルRuntime/worldを既定にせず選択理由/再利用根拠/未実施を記録する。旧私有資料欠落をskip+passにしない。通常11原資料未移送/物理未確認を明記し、将来11へ反映する別incrementの回帰/受入を省略しない。

## 8. スコープ外・残るgate・レビュー対応

START-03の自動停止→NotRunning確認→launch→タイトルStart→home→All Zones階段→通常1-1は後続の必須要件。今回入口/UI座標を実装せず、旧Pause開始/同run回復を保持する。8の画像取得を入力資格/START-03/商品到達/11受入へ昇格しない。

scope外は通常serverとのcapture共存・legacy/VTへのdrain hook、8/11座標/raster/aspect guard/G1画像処理/認識/beat/world/goods/閾値変更、ゲームautomation/native start、予算リセット、UNKNOWN再送、旧資料削除、raw公開、有料サービス/大型runner。未確認はRound 3、新modeの全起動入口でproducer0、実fresh process/native未開始/旧資料なし、実iOS16 JPEG/drain/回収、旧11資料移送。source-onlyの成立性を実機受入にしない。

| 既レビュー指摘 | 現scopeでの対応・次の証明 |
| --- | --- |
| qualification/target可視性 | compile opt-in＋Kit純Swift raw model＋immutable server mode、認証configの既deviceID。App/Mac compile/通常11同値 |
| ID上限/restart/prepare期限 | runtime ID、128/64、受付2秒、raw300秒、実jobまでlease。境界assert |
| send throw/pending0/callback終了 | 新8 entryのsend＋callback全body finallyだけで観測。実ObjC fixtureで証明 |
| 旧回収の中断/cycle prepare副作用/legacy app worker/VT | 旧producerをprocess中開始0、fresh process・8 native未開始を前提とする専用modeへscope変更。旧資料検出busy、通常回収は変更しない。producer0が崩れれば残P1 |
| Round 3認証P1（config更新拒否とApp Allow/revoke/Stopの衝突） | 既token-only/POSTpair常時拒否、typed trusted local auth-adminと従来read shape、process所有coordinatorと全constructorのmode伝播へ限定補正。remote更新拒否/偽出典拒否/local revoke・pause/再Startをassertし、差分の独立確認へ渡す |

旧共存案の自己修正を合格扱いせず、このscope変更と起動入口だけを独立再レビューする。実装/試験/実機結果は別途記録する。
