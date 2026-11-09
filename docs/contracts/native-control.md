# Native制御の不変条件

入口は [context索引](../context.md)、現行版・結果・次工程は [status](../status.md)。数値境界や相互関係の変更は、要件・変更単位の計画・Redから検証する。

## 1. 要件と作業権限

[要件正本](../requirements/necrogold.md) と [AGENTSの要件](../../AGENTS.md#守ること) を参照する。起点/向き・設定、開幕gold/入口、未知/候補保持、毎拍/人より速い性能、iPhone単体を維持する。

保存権限は継続する。現scopeはstatusから辿る計画に置き、過去の命令を現在の指示にしない。

## 2. 保存資料と秘密値

`legacy/r12/` 全40ファイルを [元manifest](../r12-source-manifest.json) とbyte一致で保存する。NG-G1と保護されたnative資産は変更単位の対象外なら維持する。元資料・raw ZIP/PNG/report/log、端末設定、pairing token、秘密値はGit外に置く。

## 3. 入力owner・prefix・取消

時計は端末のmonotonic ns。取得開始/終了の両境界で同じcompleted prefix、inflightなしを確認した安定画像だけを入力権限にする。交差・古い世代・取消済み画像は使わない。C呼出しはcontrolQueueで直列化し、mainでのbegin中はそのcallerを同期停止する。純粋な画像解析はcapture worker、公開Sceneはimmutableなheap所有とし、observeと証跡をowner/generation/cancelの同じgateでcommitする。capture・解析・main callbackの実終了までdrainする。画像の最新優先・上限、EXIF1〜8、px/pt変換、alpha/sRGB/比率/stride/範囲/overlapの検査を維持する。

main.syncでrun lock外のAX前面照会を行い、最終callbackの実returnまで同じleaseを保持する。最終callbackにAX IPCを置かず、query-start≤end≤now・開始から1秒以内をIPC/待機込みで検査。C epochが証明する同logical MOVEのSAME/FRESHだけ、同run/clock/owner/世代/PID/prefix・元拍/期限のfresh sampleを共有可。初歩/retune/ACK後は共有不可。最新ID/方向/座標・実時刻・前面/ロック・owner/世代/取消・元C ticketをsynth直前に検査して1回だけ送る。旧IDは新状態を変更しない。未確認inputは1件、UNKNOWN再送/自動cleanupは禁止。停止後/別アプリへ旧画像で入力しない。

## 4. 初期slot

初歩だけ、lead+50msの準備余裕を持つ拍を一度選ぶ。予約公開はnotBeforeの100〜50ms前に最新の通常判断から行い、それ以前にticket/event/replanを作らない。元の拍を次の拍へ取り直さない。待機・公開・beginで同じ拍と凍結境界を再検証し、失効modelは直後のrefitでも救済しない。retuneと確認済み連続歩行へこの初歩専用規則を持ち込まない。

## 5. 未送信の再予約

初歩は最大2回。確認済み連続MOVEは1chain最大2回・run最大8回。両者とも確実な未送信、両Sceneのsafe_floor・同gold・strict BLOCKEDを再検証する。初歩は同directionとorigin/next近傍の保護を検査する。continuousは全protected一致、元/保存の完全5field Decisionと最新actionも検査する。元target/notBefore/deadline/period/ordinalとmotion horizonを保持する。continuousのreason8/FLOORでは許可済みの遠いtarget座標だけの変化を扱えるが、direction/reason/obstacleと最新判断を再検査する。未知inputや期限切れを次拍予約に置き換えない。

FRESH（validation12）はlead確認済み連続MOVEで、SAME不成立時に最新判断へ切り替える別経路。両FLOOR/GOODS_UNKNOWN/GOLD_CANDIDATE・origin FLOOR・全protected不変・source5fieldの単一証明・strict BLOCKEDを要求する。全230セルでUNKNOWN→FLOOR/DIRT/STONE/GOLD/DOOR、FLOOR→DIRT/STONE/GOLD/DOOR、DIRT→STONE/GOLD/DOORだけを許し、GOLD/STONE/DOOR/ITEMは不変。新DOORはgold bracket必須。

最新の通常plannerが許可する1MOVEを別ID/latest sourceへ予約し、pending全5fieldと最新direction/x/yを再検査する。FRESH→SAMEでも元方向へ戻さない。SAMEとchain2/run8・同じ拍/ordinal/全凍結期限を共有する。未予約のFRESHを重ねず、元source/phaseのhorizonをsource更新で延ばさない。


## 6. 全期限・予算

| 項目 | 維持する上限・境界 |
| --- | --- |
| 方向入力 / restart | 16回 / 12回 |
| walk / session | 45秒 / 180秒 |
| source画像 / 位相 / 前面query-start | 3秒 / 3秒 / 1秒 |
| MOVE入力窓 | 元notBeforeから10ms以内 |
| 状態遷移 / heartbeat | 4秒 / 5秒、watchdogは100ms周期 |

model、source、phase、walk、session、dispatch、motionの元境界は短縮だけを許し、refitやsource更新で延ばさない。全期限・取消は待機と保存の後にも検査する。主処理と停止・結果回収の期限は各専用契約を守る。

## 7. 拍とleadの有限試行

ライブHUDから通常1-1のprofile（周期0.515〜0.530秒）を確認する。動画の約0.52秒や命令送信時刻を固定epoch・実受付幅にしない。初期leadは未確認。150/75/225/300/375/450/25msを各1回まで、安全な床でACK後のstrict BLOCKEDと同じgold/経路を確認した場合だけ試せる。UNKNOWN・partial・商品変化・gate/dirt/保護対象ではretuneしない。同方向の実1歩MOVEDでleadを選択し、全試行を元の入力・walk予算に含める。

## 8. ACKと移動確認

ACKはゲーム移動の証拠ではない。ACK既知state3のMOVEだけ、同じcommand/before画像で、安定したACK prefixのafterを確認する。取得開始はmax(ACK完了,target+80ms)以降。UNKNOWN/TWEENの適格評価は最大3回、元の次拍およびsource/phase/walk/sessionのmotion期限内とする。現在のbefore画像を別画像へ置き換えて確認回数や期限を回復しない。cleanupには最新ACK prefixの新鮮なFLOORが必要。

motionの全73候補、強度.45・差.08、通常texture支持300/75%、構造補助95%・全候補15pp差・2領域各100等の既存条件を保つ。MOVEDは符号付き同方向unit変位、partial/逆方向/未知は成功にしない。開扉・茶壁破壊は進入と分離し、開通だけで歩数を増やさない。観測済みgold/保護セル/入口の規則を維持し、入力回数から移動を推定しない。

## 9. 元画像による限定fallback

入力権限は常に最新Scene。別のimmutableな元Sceneとcapture/start/prefix・元ticket・period/期限・完全Decision・位置/visits/entranceを、lead確認済み/moves>0のcontinuous safe-floor logical MOVEだけに保持する。単に元画像を保存しただけでは適格にならず、資格付き未送信更新が必要。

元画像から送信前の**全ての**安定current-prefix画像へ直接strict BLOCKED(dx=dy=0)を確認する。mask0、HUD/signatureのみの観測、pending→reserveも含む。両FLOOR・GOODS_UNKNOWN・GOLD_CANDIDATE・safe_floor、全gold/全保護、元/保存/最新の5field Decision、位置/visits/入口・prefix・全凍結境界を検査する。最初の不成立でlogical MOVE中の資格を永久失効し、取り直さない。

FRESH後はその拍で旧referenceを永久失格とし、再作成・SAMEでの復活を禁止する。primary UNKNOWNの時だけ、資格ある元画像で既存ng2_motionを補助実行し、同方向unit MOVEDのみ採用する。TWEEN/BLOCKED/既知結果/開扉等を上書きしない。初歩・retune・次ordinalへ持ち越さない。任意referenceの失格は、既存reason8の再予約や最新primaryによる確認の追加拒否条件ではない。

## 10. 商品優先

商品latchは追加入力より先。適格な同一商品frameで既存移動確認を1回行ってcreditできるが、UNKNOWN/TWEENでも商品を保持して閉じ、再観測待ちで入力を続けない。earliest前/期限後の商品frameは移動を捏造せず、最後に実際に評価した診断を残す。不可視を対象なしとせず、候補保持・購入禁止・通知の要件を落とさない。

## 11. ABIと診断

既存Status192B/Event128B/Scene23864BとMotionWait layoutの意味を保つ。SceneDetail.validationは2=SAME、12=FRESH_ALLOWED。別queryのMotionReferenceは80B、成功ACK MOVEごと最大16行。閉じた12keyは command_id / authority_capture_id / reference_capture_id / reference_start_ns / reference_prefix / observed_capture_id / reference_eligible / primary_motion / fallback_attempted / fallback_motion / selected_capture_id / selected_motion。

観測前はobserved=0、全motion=0、attempted=false、selected=authority。reference_prefixは直前の未送信eventではなく同logical MOVE前の最終ACK。未適格fallbackを評価済みと表示しない。通常はeventとtraceのobservedを一致させる。goods=1の最終ACK MOVEに限り、traceの未評価/最後のUNKNOWN・TWEENを保ち、後の商品event observedとの差を認める。初回応答の空配列は応答コピーへ補い、保存reportのaccepted lifecycleを変えない。その他の診断も閉schema/型/件数上限・最初の故障記録の意味を維持する。

## 12. 新規起動と旧client回復

新規起動はstatusの対応capabilityを要求する。保存revisionのliteralに従い、native-walk-v12/v13はmotion_references必須、旧版では不在を許すが存在すれば厳密検査する。v10/v11/v12/v13は4chunk batch、v9は1chunk、v1〜v8はlegacy回復。started journalは元UUIDでGET0/start0、unknown startを再送しない。fresh preflightだけ許可済みtransientエラーを最大4試行/計8秒/各2秒で再確認する。

## 13. Exportと保存

PNG上限は20枚・各512KiB・計4MiB。初期/商品/停止と最新比較を優先。chunk64KiB、manifest wire512KiB/chunk wire256KiB。batchは最大4chunk/256KiBでも、各chunkの検証・取消・期限を省かない。検証済みprefixだけをhash/cursorへ反映し、atomic fragmentをjournalsより先に保存する。再中断でも物理的な未検証suffix全体を保持する。active journalが回復の権限を持つ。

ordinary RPC2秒、結果専用8秒、export1試行90秒を残session180秒以内に収める。所有するterminal/drained runだけが結果を公開し、古い返信で新しいcacheを消さない。回収成功を未知inputの解決にしない。取消・lock・同時実行・世代/ownerの既存guardを維持する。

## 14. Compileと封印

profilev2はPerception/Navigationだけstrict O2（-fno-fast-math、-ffp-contract=off）、Beat/ControllerはO0、SwiftはOnone。native_v6/profilev1との旧互換を保つ。22封印source・実PBX・raw compiler引数/response・profile・build manifest・IPAを同じcodeへ結び、app/runnerのAPI/capabilityと全Mach-OのHOST/fixture/spy非混入を照合する。配布source ZIPも全tracked bytes/CRC/pathを確認する。公開CIは標準macos-26/ubuntu-latestを使う。

## 15. Fixtureと実機の証明範囲

[testing](../testing.md)に区分と実行入口を置く。必須実画像の不足/hash不一致はlocal失敗とし、CIの明示除外と区別する。合成・録画再生・通信結合・compiler/IPA検証は実ゲーム到達やiPhone性能の合格ではない。未測定・欠落・失敗を0費用や成功に置き換えず、未知評価はラン単位で分離する。

## 16. 開発工程

工程・fresh3観点/最大3周・TDD・人間レビューは [開発フロー](../development-flow.md) を正本とする。

## 17. 配布と実機依頼

[AGENTSの保存と返却](../../AGENTS.md#保存と返却) に従い、日本語/JST・完全source・具体的実機手順・終了後runtime全ZIPを提示する。native/cap変更時は新IPA、SideStore更新→LoopCtrl完全終了/起動→Start Server。新通常1-1ポーズから、同時テストなし。回収済みrunを追加回収目的で再実行せず、終了した未回収だけ同じprocess/source/runtimeで回復する。
