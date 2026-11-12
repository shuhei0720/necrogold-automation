# TEST085: 確認済み歩行後の予約と独立静止確認

2026-11-12（クライアント日本時間）。基準 `0443bc9abc5c814ed620d09afdd487af203eb681`、TEST084/build142。実機主軸・品質維持・固定時間上限なし。同じ独立担当1名が計画/差分/実物を確認する。

## 受領と範囲

4ZIP/80原PNG・17,923,256画像Bを現schema/client_load/実publicationgate/CRC/SHA/PIL/prefix/cursorへ全照合。実順3a5b22f5（goods）、1babdecf（late）、26857403（beat）、a41de5bb（goods）。全paused/terminal/drained/回収完了、正常見送りsource7/7保持・選択native行欠損0。商品可視/自動完了は2/4、見逃しなしはユーザー報告と保持画像の範囲を分ける。raw/JSON/SceneはGit外 `received084` / `test085-*`。

実2はcmd13のauthority134→141 primary UNKNOWN、同ticketの有効reference133→141 fallback MOVED/selected133でLEFT実1歩が確定。実3も最後のLEFT実歩は成立し、次UPはbegin0/確実未送信。前版の画面認識落ちと混同しない。Beat.cは旧083/084同bytesで、保存モデルは全publicvalid/同samplefit成功、実3原142のtrackも最終periodと一致する。Beat閾値/モデルを変更する根拠なし。

実3はstationary OBSERVEのW=min(P,triggerCommit+2*元period)まで独立strictBLOCKEDが成立せず停止。最新recovery reason4はPREPARATIONでありTRACKではない。実4validation7もFLOORでMOTION11とは異なる。作者の初期enum名の誤記は撤回済みで、番号/時刻は元headerへ照合する。実3の準備窓4.402ms超過は付随失効であり最終停止の直接原因へ繰り上げない。

## A: 遅い確定proofを次の未発行拍へ流用しない

実2のproof141はsource開始160784727479833、commit160784898595958、observe終了160784912349833。次NB160784936632770/元D160784946632770、元100ms公開窓開始160784836632770。proofsourceはNB−200msより9.152937ms古く、次拍へ新予約する200ms資格を満たせない。最初actualtick自体は未収録だが、observe終了以降・元D内のproof処理であったことを後続理由/追加recovery記録0から区間として区別する。

元proof_deadlineを消費するtickで、下記全ANDのときだけ既post_move_recover(VISUAL_SCHEDULE)へ戻す。期限切れの全nextを救済しない。

- 同ACK MOVEの既採用MOVED1（元qualified fallbackも含む）・確定実歩、input0/current0・未発行next/pendingなし。proof ID/current画像ID/event observed IDが一致し、元command/last_completed/eventの正統性を保つ。
- goods/finish/cancelなし、元visualP内・model有効。最初actualproof tickが元次拍100ms公開窓内かつ元next/scheduleD内、現在proofsourceがそのNB−200msより古いこと。
- 元proof/ticket/event/ordinal/入力・移動creditを変えず、未発行candidateだけ撤回。新ticketの許可ではなく、既有限post-move同期に戻る。元episodeD/command_sync・walk/sessionを延長しない。
- 新しい通常予約は元prepare_recovery_slotのsampleID≥proof・新鮮source/位相・将来50ms準備・100ms公開/200mssource・10ms入力窓を全て再検査。UNKNOWN/未確定/発行中入力を再送しない。GOODS優先と旧初歩/retune/gate/passage条件を保つ。

公開Controllerの元C4だけでassertion Red→最小Green。元早いproof後のcandidate expiry assertは維持し、新条件外は旧停止を保つ。publication両端/source200ms等号/元D/P等号と＋1ns、primary/fallback採用proof、issued/pending/未知/不一致prefix/source/event、商品/取消/元予算、後続freshslotと旧event不変を選ぶ。私的C seam/新API/Scene copy/flagは追加しない。通常の旧単体をローカルで形式重複せず、作者新試験と影響する旧exact名だけを同code CIへ選ぶ。

## B: 無金通路のzero-only静止proof

実3原122→142は通常rawのscore .491725905が.45を越し、元14stageは全UNKNOWN。一方zeroは元raw全73候補で唯一の最良、有限runner gap .309779657≥.08。固定mask0の3×3 blur依存を全てmask内へ閉じた別scoreはzero .332918858≤.45で唯一最良だがrunnerとの差.002050884は小さく、これをphase gap.08合格と呼ばない。

別zero-only helperを元14stageの後へ追加する。元raw/全旧helper・順序・閾値を変更せず、新しいANDとして強度と曖昧さ除外の証拠を役割分離する。元proofと同一のものへ言い換えない。

- 両Scene FLOOR/GOLD_CLEAR/GOODS_UNKNOWN、originと次cellは両方観測FLOOR。全GOLD/DOOR/ITEM/保護が両Sceneに存在しない。origin/次cellの各3×3近傍材質が不変。
- 旧STONEを全て同座標で保持し最低2、同座標DIRT最低9とSTONE基準に非共線な支持、元9translationのunique zero幾何を全AND。材質単独・未送信単独で静止と推定しない。
- 元raw73全candidate finite・zero唯一最良・元gap≥.08、元rawscore>.45に限定。新blur73も全finite・zeroが全72より厳密に良く、元score算術/contrast/gain・強度≤.45を要求。blurphaseのgapを曖昧さ排除に使わない。
- 元worldblurのzero一致≥95%/支持≥300/独立2帯各≥100と、元fixed-axis52のzero一致≥75%/支持≥300/2帯各≥100・全73を走査し、support≥300の競合へ元texture_lead15pp・低支持は元規則を全ANDする。原122→142はworld918/20bad・388/530、axis1190/98bad・729/461。強度はblur、曖昧さは元raw gapと独立axis全73へ分け、片方だけで成立させない。
- 返すのはBLOCKED/dx0/dy0だけ。MOVED/開通/入店や実歩credit、deadline/W/P/元2beat・再送の資格を増やさない。原142は元Wより前のcommitで静止proofを確認できる対象であり、未収録の中間画素を再構成しない。

実4原145→147は金/扉とwitness不足でこの追加対象外、UNKNOWNを保持する。今回実unit115→122/逆pair・実2primary UNKNOWNのunit134→141は拒否。旧記録の8px/TWEEN/unit等の正解付きnegativeをGit外prototypeで照合し、その結果と出典を独立レビューへ渡す。失敗したraw/壁only/blur-onlyの試算も残し、元閾値を下げて成功へしない。

公開Scene/signatureの独立した静止正例で元UNKNOWNのassertion Red→最小Green。raw強度とgap/blur強度と曖昧性の役割、scalar/帯/有限/geometry/保護・金/扉/商品・origin/次cell・8px/TWEEN/純unit/alias等の拒否を選ぶ。公開Controllerの関連結合1件で未送信OBSERVEの元W内proof→READYを結合し、元W後も延長せず元P・新freshslot準備で進むことを確認する。製品API/Controllerの私的seam・強制motion・実機の未来frameは使わない。固定前提の独立計測だけにHOST guardedな試験C SHIMのexport3・static計測補助3、計6宣言を許可し、実宣言/export/static builder数は作者freezeのASTで確定して全markerを実MachO検査へ結合する。Bはこの追記の同担当確認と有効意味Redの後だけ製品へ適用する。

## 検証・配布

native変更時はsource8/C4・保持原画の差と旧known回帰を一度照合し、fresh pinned GitのG1→seal/apply。同code限定CI・実IPA・5実物verifier/完全sourceを照合し、固定Releaseへ公開後匿名全GET/SHA/CRCを確認する。Runtime/core4/API16/cap15/client16/v2/旧v1回収・G1/R12は維持予定。無変更Runtimeの新Red/全故障worldは加えず、固定保存Red133と今回Mac Greenを分離再利用する。同じiPhoneの通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認/PAUSEの複数回と全run別ZIP返却を必ず依頼する。新実機の到達率・毎拍/人超え・対象識別/通知/対象なし循環を先取りしない。
