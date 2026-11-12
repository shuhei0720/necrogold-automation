# TEST084受領とTEST085

2026-11-12（クライアント日本時間）。[計画](../plans/test085-verified-scheduling.md)・[独立レビュー](test085-independent.md)。基準 `0443bc9abc5c814ed620d09afdd487af203eb681`、TEST084/build142。raw/JSON/Scene/解析はGit外 `received084` / `test085-*`。

## 実機結果

started_ns順に照合した。

| 実順 | run先頭 | 終了/PAUSE | inputs/moves/restarts | 結果 |
| --- | --- | --- | --- | --- |
| 1 | 3a5b22f5 | goods1/1 | 8/6/1 | 全3商品可視 |
| 2 | 1babdecf | late9/1 | 4/4/2 | 扉前で停止 |
| 3 | 26857403 | beat8/1 | 2/2/2 | 左2歩後停止 |
| 4 | a41de5bb | goods1/1 | 6/4/2 | 扉前待機後、全3商品可視 |

4ZIP/80原PNG・17,923,256画像BのZIP/PNG chunk CRC・SHA/PIL verify-load/896×414/現API16閉schema/client_load/export全offset・prefix・cursor/test069実publication gateを照合。全paused/terminal/drained/回収完了、host/cancel/capture failure/timeout0。途中dispatch too_late1は後続実歩があり最後の停止と区別する。正常見送りsource7/7保持・選択native行欠損0。omitted423/参照省略19で全取得画像保存ではない。追加回収や084再実行は不要。

rootと監査担当が原140（実1）の50/75/100と原207（実4）の25/50/150の全商品を視認し、native GOODS2/4とも一致する。対象識別/通知受入ではない。見逃しなしはユーザー報告と保持判断sourceの観測範囲を分ける。

共通Sceneは元TEST084最終C4 lib `e45b509633a0af80401146c4c8235600dd8abed840b91d545c06cc08f74b619f` と現source8hashの全一致を確認して再利用し、80原画を一度だけexport。再compile0。監査receipt SHA `8d30057d9a3ed0b30f1ebfba54a5cc19dde3336b07142746c65673eb75828c72`。

## 実2: 遅い歩行proofと次拍sourceの資格

cmd13のauthority134→141 primaryはUNKNOWN0。元MotionReferenceの同ticket reference133/prefix11がeligibleで、公開133→141 fallback MOVED1が採用され、最後のLEFT実1歩は確定している。ACKだけの歩数やprimary成功へ読み替えない。

原141start160784727479833からcommit160784898595958まで171.116125ms、observe終了160784912349833。次NB160784936632770/元D160784946632770・100ms公開窓開始160784836632770。source141はNB−200msより9.152937ms古い。確定proofが届いた時点で、次拍へ新予約する取得開始200ms条件を満たせない。first actualtickは記録がないので一点へ再構成せず、observe終了以降・元D内のproof消費だったという区間論証を残す。

既proof_deadline tickでこの同ACK/採用MOVED・未発行next/最新proof・元P・100ms窓・200ms源不足を全ANDしたときだけ、既post_move_recoverへ渡す。失効した旧nextを予約せず、新鮮HUD/元episode・command_sync・walk/sessionの上限/新50ms準備を再検査する。一般のcandidate expiryやUNKNOWNを救済せず、元early-proof expiry assertを保つ。

## 実3: 静止確認と元2拍期限

最後のLEFT実歩は公開MOVEDで成立。次UPcmd8はbegin0/確実未送信reasonSCREEN17。start_stationary_waitのOBSERVEから独立BLOCKEDが成立せず、W=min(P,triggerCommit+2*元period)へ達した。scheduleDから元period524,203,584nsを導き、W160891228651793を照合した。cleanup PAUSE予約はW+2.800248msだが、この時刻を未exportのfinish呼出時刻と同一視しない。原122→142の元14stageは全UNKNOWNで、元W前の原142commitにも通常proofは成立しなかった。

保存モデルは全publicvalid・同samplefit成功。原142を元間引きでtrackするとperiod522486997で最終reportと一致。最新recovery reason4はPREPARATIONで、50ms準備窓を4.402253ms越した付随候補失効。初期の作者のTRACKという命名は誤りで撤回した。Beat品質不成立やモデル故障とはしない。W/P/2beatの延長を修正へ使わない。

新zero-only proofは無金/商品未知/金扉item保護なし・近傍不変・旧STONE保持/非共線DIRT9とuniquezero幾何、raw全73有限のzero最良gap.08、mask0全3×3依存内blur全73有限のzero最良/score.45、worldblur95%/300/2帯100、fixedaxis75%/300/2帯100/全73走査・support≥300競合への元15pp差のAND。強度と曖昧性排除を別証拠へ分けた新proofであり、元14proofと同じものではない。元rawscoreやblur gapの失格を成功へ書き換えない。Git外prototypeは原122→142だけ追加zero、関連原negative11とinvalid4拒否。設計校正であり、新単体/製品/実機成功と区別する。

## 実4と退行の確認範囲

扉前145→147は次cellがDOORのためsafe_floor不成立、遠方DIRT→UNKNOWNも元monotone条件外となりvalidation7=FLOORで先に拒否。別quiet gateもstrictBLOCKED不成立でmaskを消せず、既gate refresh/refitで約2.625秒待機した。その後は開扉・商品可視へ成功した。初期作者のvalidation7=MOTIONという命名は誤りで、MOTIONは11。原145には開幕文字が残り147で消えるが、『文字だけ除けば通る』とはせず、各元pixel witnessの支持/帯/score不足を記録した。

Bの追加proofは金/扉等でこの実4を拒否し、待機短縮を達成済みとはしない。原の壁only/rawblur等の未成立試算を閾値低下で通さない。

今回停止へ関係するController7関数とBeat.cは083→084で全bytes同一、原3の旧083/current084 motionも同じUNKNOWN。『同じ地形が以前通れた』だけで退行や新修正無関係を断定せず、取得/処理・画面変化と既条件の違いを根拠にする。A/Bの新単体・最終source/CI/IPA/実機受入はこの時点では未実施。

## 作者単体と最終固定source

A新6は公開C4の同ACK/MOVED・元earliest/P/旧期限などの前提を先に通し、immutable084でPOST_MOVE期待2対NORMAL0だけの有効Red→初回6Green。主Red前に不要な恒等assertを元deadline保持の実assertへ置換した編集methodだけ再Redを確認し、製品後のfixture訂正0。qualified fallbackの公開reissue/primaryUNKNOWN/referenceMOVED、100ms/200ms等号±1、元D/P・goods/cancel、既command_sync非0の同episode/後続新reserveと旧D等号begin拒否を確認。旧8C/Hの別anchor/flag/API・C seamは追加0。

BのRedはA固定Controller6ebf…＋旧Nav511437…のsnapshotで対象を分離し、公開Motionは旧NavだけをO0/strictO2でcompile。固定世界＋独立noise/gainの無変位ラベルから期待zeroを決め、元14stage/独立前提を先assertした8subcasesがBLOCKED2対UNKNOWN0だけで意味Red。新6Green。初回first5のinvalid-state12subcasesはfixture helperが成功1を前提にしたため失敗し、旧APIのreturn0/zerooutを該当methodへ明示して単独Green。第6の最初のW等号negativeもBEAT停止要求直後にterminal1を期待した誤りを、追加MOVE拒否/PAUSE予約・ACKだけterminal0→公開PAUSE観測でterminal/paused1へ訂正し、そのmethodだけ再Green。製品の閾値/処理は試験期待のために変えていない。追加した境界も編集methodだけ再確認し、失敗logを保存した。

第6C4は初めからCLEARの通路をpublic APIで2歩→次票確実未送信→UNKNOWN trigger/OBSERVE→元W前に新BLOCKED→元W等号をreason0で越える→新ID/future50ms準備/元P内を確認。私的READY getter・fakeGOLD・強制motionなし。旧票/event全bytes/入力・歩数不増/旧ID begin・complete拒否を保持する。B HOST guarded試験Cはexport3/static計測補助3の計6宣言、製品API/Controller private seam0、全実数をMachO marker検査へ渡す。旧意味試験のlocal重複はA/Bとも0。

最終Controller SHA `6ebf9456674f6faaf26ca13dfc96ac81473614c60460722b45f2e2bbef99748b`、Nav `27fa85aa00422ec6e791ee6e99fbc4d136904bf4966fda495f3414841630429e`。A test `e346db6356db86a63baea33a028b1606157710fae0a6a811e2501441c9179632`、B test `c75bd213473f65436d285645d12944b55256cde2d3f846dd9a944941cc70d785`。新helper/callだけを除くと旧Controller・Navの全bytesへ復元し、旧14stage/順序を保つ。

rootは同8C/Hを一度だけC99/Perception・Nav strictO2/他C O0でcompile、lib `08d2fc652fde7eefb03311284d25c7a1dc60d710c926e3733975ecf1b2fbc384`へ固定。原337枚のScene/候補maskは全bytes同一。保守的stable ACK-prefixの172pixel組は旧known116を全保持、motion差0。native終了/source+3秒を越す2組を除き、私的元visualDは再構成しない。別の未送信stationary原122→142はUNKNOWN→BLOCKED、金扉145→147はUNKNOWN保持。純pixel比較であり、新実機の未来frameや入力権限・到達を推定しない。

fresh pinned Git checkout→G1→seal/apply成功。22中Controller/Nav2変更・他20不変、manifest `c2526300a3caefa8fb408ef703974fa32c82d0fdefaf4bf05efc8472e414242c`。Runtime048a…/Beat/Perception/core4/API16/cap15/client16/v2/旧v1回収・G1/R12を維持。同じ独立担当が製品/新12/最終C4/原画/sealを結合してP0/P1/P2なしでGO。selectorと同code CI/実物はこの時点では未実施。

## 限定CIの選択

33methods/10scope（native29=新12+旧17、client publication1、selector self3）を選ぶ。Aの旧100ms/200ms/早期proof expiry/遅いHUDとcommit/既同期上限/GOODS、元ABI/query、Bの元W/P/READY-UNKNOWN/alias・partial/blur依存/正常motion結果とentry全画像公開gateへ絞る。CORE15とbare test_native_perceptionを選択前に結合し、PROOF/STATIONARY等baseline/evidence overrideは空も拒否する。旧Controller fixture a332…・旧084入口4file/core4/Runtimeは全baselinebytes同一。

self3の作者初回Green0.018秒後、独立reviewがmainのself選択tupleだけ旧084を指すP1を発見した。native/client選択のASTとself関数のGreenだけではmain経路の版を保証しないため、新085 module/classへの1tuple訂正を行い、main ASTに旧084定数がないことを確認。self3ソース/対象helper/他意味処理は不変で形式再実行を増やさず、同code CIで実際の新self3選択を必須にする。最終runner SHA `1ae9491ebf69538a8ae994b204f9be1a31a5a6b32e6f418eeb2ea77d9786aa2c`。workflowはdevice参照の1行だけ。

新markerはPython3module/classの6とB C6の12件を旧237 exactprefixへ加え計249、重複0・全C宣言coverage。HOST試験Cは製品sourceへ混ぜない。5実物verifierはこの時点では全guardFalse/未実行で、code/count/実物到着後に同一性を照合する。
