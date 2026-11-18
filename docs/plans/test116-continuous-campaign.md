# TEST116: 端末内保存で連続する有限campaign

2026-11-18（日本時間）。状態: 設計レビュー前。TEST115の成功した商品判定・実リスタートを維持し、次フロアでの回収待ちを周回から外す。実機改善・性能の合格宣言ではない。

## 1. 概要と実機根拠

2周目のe0b897は正常な完全陰性（分類45.157ms）、checkpoint保存、RESTART16の実ACK、新FLOOR159/160まで成功した。その後のPAUSE17/161はFR-112-CUMULATIVE-LIMITで追加した正常予算区切りであり、不明入力や利用者の操作ではない。terminalから次134eの受理まで、同じ端末時計で84.306183209秒。別のiSH時計では終端statusから次startまで83.636694秒。画像回収31.130秒、記録回収7.492秒、複数回の検証・ZIP・コピー・先行証明が同期に並ぶ。工程は重なりがあるため単純に合算しない。

利用者の新指示「次の周回に入ったらそのまま周回」を新しい専用opt-inで実装する。旧yield flagを単に外して累積16入力停止を再発させず、上限を隠れて増やしたり同一runでcounterを消したりしない。

## 2. 範囲、変更する契約、変更しない契約

新cap `necrogold_native_continuous_campaign_v1`、start任意key `continuous_campaign:true`（irregular profile専用、trueのみ、旧`yield_after_restart`との同時指定を拒否）を追加する。既methodの閉mode `campaign_status`を追加し、新methodや任意pathを許可しない。旧flag省略/旧yield/旧profile/旧回復は全画像照合・公開ACK前の新start禁止を維持する。

新rootは同じiPhone・同ownerのnative管理campaignである。通常の1-1ポーズから開始し、以後は各childが独立したUUID/clock/世代・C core・予算を持つ。正常な陰性後の実RS、新FLOOR、outcomeの耐久保存、候補veto、実callback drain、端末内全原本の耐久sealが揃った境界だけ、UI PAUSE/RESUMEとhost回収を挟まず新childへ進む。旧runの画像・陰性・経路・位相・prefix・送信状態を新childの入力権限へ移さない。

各childの方向16/restart12/walk45秒/session180秒、DATAのsource150ms/worker100ms（MOVEのsource/位相3秒は維持）、元MOVE/visual/同期期限、event64/motion-reference16/pin24/selected24/raw44/64MiB/metadata2MiB/PNG88MiB/export temporary2MiBは不変。seen128・Spool namespace128・history64・read-only recovery同時16も増やさない。rootの絶対期限は最初の受理時刻+16×180秒=2880秒（既同時回復数×既session上限）に固定し、child交換/保存/再接続で延長しない。新childの全期限もroot絶対期限で短縮する。新childは新UUIDで新しいlive FLOOR（又は既旧handoffの場合はfresh PAUSE）から読み直し、新fitを行う。新floorの商品を対象なしと報告しない。

## 3. Native/Cの資格と原子境界

既restart-yieldの正常basis、最初のFLOOR/PARTIAL/FULLのimmutable保持、positive hint、元親期限、実drainを流用する。新C API案は次の3つであり、既POD/旧関数の意味は変更しない。

- `ng2_controller_enable_continuous(NG2Controller *, int32_t successor_floor, uint64_t root_deadline_ns)`。作成直後だけ1回。irregular/cycle専用。rootは0で既fresh PAUSE-only、childは1でfresh FLOOR-only gate。別UI/DEATH/UNKNOWNや古い画像から入力を始めない。root期限をCの全新規許可と凍結期限の短縮へ結合する。
- `ng2_controller_continuous_finish(NG2Controller *, capture, start, prefix, now)`。既yieldのready/permitted、同じlatest source、入力0/現在command0、旧完全陰性→実RS/new floor/outcome、候補なし、元親期限の全積だけを受理する。方向/PAUSE/RESUME/RESTARTを発行せず終端にする。既旧handoff getterへallowedを偽装しない。
- `ng2_controller_continuous_status(const NG2Controller *, NG2ControllerContinuousStatus *)`。別固定PODにenabled/successor/qualifiedと旧job・実restart・新floor・latest source/start/prefix・qualified/parent期限を保存する。Runtimeはcore破棄前のsnapshotを保持し、この資格だけを入力として端末sealと結合する。終端後に通常操作へ復帰させない。

Runtimeのnormal境界ではcapture要求を止め、latest消費済み、capturePipelineIDs/daemon/control tokens/分類drain tokensが空、capture worker/producer/callback/persistence/mainの実returnを確認する。論理pending解除だけをdrainにしない。known candidate/target、late positive、保存失敗、owner/世代/lock/取消、入力UNKNOWNで継続資格を失効する。失格後の別画像で復活しない。

rootの入力leaseはchild交換の間も維持し、旧child.lease=falseだけでlegacy/UI権限を開放しない。交換はcontrolQueueで直列化し、root owner/cancel generation/heartbeat/root絶対期限、旧childの終端・全実drain・sealed原本、次UUID/namespace/容量予約、未消費のlinkを同時に再検査する。同じroot gateを取消と交換の線形化点とし、停止/取消が先ならchildは作らない。次childが先なら同root取消はそのchildにも届く。旧callbackはowner/root generation/child UUIDを全て照合し、交換後のchildへの観測・分類・保存状態や入力を変更しない。

最初のchild UUIDはroot UUIDと同一にし、index0/predecessor=nullを固定する。後続のfresh FLOOR gateは公開startのパラメータから選べず、この交換関数が作る未消費linkでのみ選べる。次childのslot/UUID/namespaceの予約tokenだけを、正常陰性PAUSE・checkpoint後からRS intent前に同root gateで確保し、未消費next UUIDを耐久recordへ結合する。既知のquota不足はこの時点で止める。次Spoolは旧finish・全原本seal後だけ作成するため、未起動Spoolの先行作成は行わない。旧finish後のSpool作成/追加write/電源断/取消などの不可避な失敗では、新childの入力を0として原本/diagnosticを保持し、自動的に旧Cを再開したり古い画像で保持PAUSEを発行したりしない。この場合ゲームがポーズ済みとは報告しない。停止成立は追加自動入力の禁止であり、fresh authorityのないPAUSEを捏造しない。

新child開始前に初回frameを通常Perception/irregularと独立に検査する。fresh安定FLOORかつcurrent-prefix0/noinflight・owner/lock/前面一致が必須。successor bootstrapはLaunchServices/openBundleIDを0回とし、旧childと同じgame PIDが現在前面にあることをlive確認してからcaptureを準備する。別アプリを再activationで上書きしない。root初回だけ既activationを保持する。商品は通常DATAへ先に渡し、旧陰性を根拠にRSしない。fresh gate不成立は新しいUIを送らず保持する。旧入力のUNKNOWNや送信不明を新UUIDで再送しない。

## 4. 端末内escrow、容量と失敗

各childのsession provenanceの`continuous_campaign`へschema=`ngg2-continuous-child-v1`/root_id/index/predecessor_id/root_started_ns/root_deadline_nsを記録する。全判定原画、既critical/選択原画、PNG生成に必要なmetadata、checkpoint/intent/outcome/terminalのhash chainを既Spoolへcommitし、元file/dir fsync後の`continuation_seal` recordへ結合する。sealはowner hash、root/child/clock、終端snapshot、全frame refs/chain head、C継続snapshot、次UUIDのintentを含む。rootの耐久索引はsession/link recordsの連鎖であり、再起動後の全namespace scanから再構成できる。個別sealを新しい公開ACKと呼ばない。PNG変換・暗号転送・ZIP作成は停止後でよいが、必要なRGBA原本をRAMだけに残したまま次childへ進まない。

上限は同時未公開child16（既read-only同時回復16から導く）、root child16（同時未公開slot16以内で固定。process全体のseen上限128は別に維持）。1 slotの上限は64+2+88+2=156MiB、16 slotの明示した総escrow上限は2496MiB。root索引/link metadataは既2MiB/childの内数に収める。raw/metadata/PNG/tempの実使用と残予約を重複なく数える。新slotはその156MiBと、他の未公開slotのPNG/finalization/metadata/temp残予約を端末の空き容量内で確保できる時だけ予約する。各writeにも他slotの残予約を反映し、既checkSpaceのcurrentだけの判断で将来export容量を食い潰さない。保持中の旧RGBA Dataはseal成功・全callback return後だけ解放する。

16 slot/seen128/namespace128/空き容量のいずれかが次childを妨げるなら、可能な限り正常陰性PAUSE後・実RS前に保持して`escrow_quota`/`run_limit`/`storage`で停止する。既newFLOORを得た後の競合/失敗からblindな旧cancelやPAUSEを送らない。継続資格と保存失敗の順序を試験し、入力不明のままcleanupしない。対象/不明/故障/予算停止と対象なしを別集計する。有限上限を到達率の成功にしない。

全sealとroot indexは耐久的で、プロセス再起動後は読取専用証拠である。自動継続権限を回復しない。壊れた原本/未commit/未完linkは保持して診断回収し、新startを許可しない。公開済み回復objectは読み取り終了後に解放して、16同時上限を128累積への誤上限にしない。旧Spool directoryを削除してnamespace128を潜り抜けない。

## 5. 閉wireとclientへの引継ぎ

startは`run_id=root_id, profile=normal-1-1-irregular-v1, continuous_campaign:true`。同UUIDでflag/profile/rootを変更不可。通常startの閉replyへ`continuous_campaign:true`だけ追加し、内部helperのyield有効化を旧wireの`yield_after_restart`として同時出力しない。実child identityは新queryで取得する。未知startは同rootのstatusで照合し、新rootを再送しない。

queryは既`necro_native_irregular`の`mode:campaign_status, run_id:root_id, keepalive:bool`。既envelopeのpayload内に別schema `ngg2-continuous-campaign-v1`を使う。payloadはschema/root_id/state/active_run_id/terminal/workers_drained/input_state/native_inflight/ui_frozen/stop_reason/child_limit/deadline_ns/children。childrenはindex/run_id/predecessor_id/state/escrow_sealed/terminal_reasonの閉配列（最大16、一意順序）とする。root stateはaccepted/running/draining/stopped、active_run_idは最後の子を含めUUID、stop_reasonはnone/target/candidate/unknown/cancelled/owner/locked/storage/escrow_quota/run_limit/native_limit/session。childrenに詳細陰性を自己申告させず、後の全証拠で照合する。API1.98.16/cap15、既Status/Event/Scene/Cycle PODと旧envelopeは不変。新cap/閉mode/schema/C companionの版1で機能を識別し、cap不在のIPAへ新clientを開始しない。

keepaliveは同root/ownerのactivechildへ、既NG2TicketGuardの条件だけで更新する。root失格/停止後のheartbeatや古いchild statusで別childのleaseを延命しない。`necro_native_cancel`のroot_idはrootを取消し、既activechildへ同取消を届ける。返却はrootのstartと同じ閉reply（run_id=root、continuous_campaign=true）とし、childの詳細はcampaign_statusから取得する。個別childの取消/照会をrootへの新規入力許可にしない。

新clientはroot start intentとroot_id、statusのchildren索引を原子的に保存し、live中はstatus/keepalive/取消だけ行う。正常境界ごとにhost manifest/chunk/batch/record/published/ZIPを実行しない。terminal+全root/childの実drain後だけ、全childrenを既irregular queryのread-only回収・hashchain/PNG/ZIP/公開ACKで順次照合する。root索引＋全child識別子＋最後run ZIPをcampaign ZIPへ収め、各run ZIPは原本として残す。各archiveのroot/index/predecessor/sealを索引と照合し、取りこぼしをcompleteにしない。

serverも同ownerの新rootがlive/drainingでleaseを持つ間、manifest/chunk/batch/record/published/native_resultsによる生成・公開を入口で拒否する。未active/回復cloneを経由しても迂回させない。root/child status・取消・prepare読取りは旧権限のまま許す。停止・全実drain後とプロセス再起動後の読取専用回復だけ既exportを許可する。旧modeのexport契約は変更しない。

host再起動/ネットワーク不明は保存rootでstatusを照会し、ゲーム継続を推測しない。nativeプロセスが残っていれば同rootへのkeepalive/取消、消えていればprepareが返す全未公開IDを同じroot索引と照合して回復だけ行う。rootの元索引を失った場合も未公開全IDを回収し、新startを自動発行しない。

## 6. TDDと関連試験

旧実装で正常RS後PAUSEが出る意味Redを取り、新modeでPAUSE/RESUME0、host画像RPC0の間に次childのfresh FLOOR/新fit/選択へ進むことをGreenにする。旧modeのPAUSE/公開ACK資格、累積16/12/45/180・raw44等は従来assertを保持する。Cは同source/parent/入力0/未処理goods/positive/未知/取消/期限・初回root PAUSE/child FLOORの反例を含める。

実Macでcapture/decode/control、producer enqueue後return前、persistence callback return前、main callbackを各parkし、child0/入力0/root lease保持を確認する。seal途中のwrite/fsync/rename/terminal/link失敗、owner/lock/cancelとの線形化、前面失効（successor activation0）、late positive、RS前quota/namespace不足、ROOT keepaliveで最新childだけ更新、root取消が交換前後の両方で届くことを選ぶ。rootDがchildの元Dより早い場合は、C begin後に時計をrootDの直前/等号/直後へ進めて最終mainのsynth0/1を検査する。watchdog100msだけで代用せず、凍結ticketDと実synth直前時計の両方でrootDを検査する。後のchildを動かした後も全旧raw/chain bytesが同じで、全childの通常export/PNG/hash/公開が成立することを確認する。

実Python3.9で閉start/status/cap、同root不明start、重複/順序/不足child、旧flag互換、live中export0、停止後全child順次回収、途中回収再開、失われたroot/復旧、容量停止の別理由、全未完時complete禁止を試験する。単体/合成結合と実iPhoneの到達/速度を区別する。

## 7. 実装順・レビュー・配布

この計画を経緯を共有しない独立担当が設計/網羅/安全で点検し、P0を閉じてから製品を変える。C/headerはshop担当の編集完了後に直列で追加。Runtime/Spool/root wireとclientを仕様固定後に分担する。機能ごとの意味Red→最小Green、直接関連回帰と独立差分レビューを行う。並行/保存/入力権限の変更があるため、この境界の実Mac結合を選ぶが、旧全故障集合を機械的に追加しない。

新cap/manifest/seal、実compiler/Mach-O/IPA、完全sourceと固定Release assetを照合する。配布時に通常1-1ポーズ、IPA更新/完全再起動/Start Server、test116コマンド、停止後全child ZIP/索引の返却を具体的に依頼する。実機は「商品全可視/正常判定/実RS/次フロアから待たず探索」を測り、ソフトGreenで改善完了と書かない。

## 8. 対象外と残る限界

商店開扉後の移動とcapture25の候補見逃しは別の実画像原因へ限定して修正する。回収を停止後へ移すことを、回収自体の70〜89秒の高速化と呼ばない。無制限ディスク/無制限自動再試行、未知入力の再送、旧陰性で新floorを捨てること、対象/価格/候補閾値緩和、R12/G1やiPhone8/遠隔開発を含めない。root有限停止/容量停止のあとまで無停止の本番性能や30分500restartを達成したとは主張しない。

### Spoolの追加具体化: seal後の正常exportと再起動回収

制御原本は`contentSealed`で凍結する。成功したseal後は新RGBA/frame metadata/checkpointなどの制御record追記を拒否し、正常PNG/manifest/publishedだけを既同一Spoolへ追記できる。旧readOnly/IO故障を解除せず、再起動後のSpoolは常にreadOnlyで、入力・新child予約token・自動startを復元しない。sealの閉payloadは上記root/run/index/predecessor/next/terminal/frames/controllerに`clock_id`と`session_sha256`を加えた11keyとし、session内owner/clock/provenanceも実hashへ結合する。

プロセス再起動後は同rootの既namespaceから容量会計だけを再構成し、全未公開slotの残RGBA/metadata/PNG/temp予約を回収writerへ引き継ぐ。これは保存領域の会計であり継続資格ではない。原Spoolに検証済みPNGが既にある場合、新modeのsibling回収ledgerはその固定root/child内のPNGをreadOnly参照し、再複製しない。元metadataのraw参照・全PNG bytes/hashを確認し、任意pathを受理しない。原本・recovery追加分のmetadata/PNG/tempを同じ156MiB枠へ合計し、同じPNGの物理重複を容量削減と偽装しない。破損元PNG/metadataや未commit一時fileを隠さず診断へ残す。

追加試験は「正常seal→一部PNG export→プロセス参照消失→readOnly再回収→全元bytes一致」「別childの残予約を食い潰す低空き容量」「元PNG/meta改変」「orphan一時file」「seal途中のwrite/fsync/rename/dirsync失敗」とする。元slot/record/frame上限を増やさず、制御原本と既故障のreadonly状態を維持する。
