# TEST094: native内の商品判定と陰性周回

2026-11-13（日本時間）。実装中・実機未検証。基準 `3e79c460840bf05fef0f49f5a10f39e09f2815cd`。[要件](../requirements/necrogold.md)、[商品coverage](rebuild.md)、[native契約](../contracts/native-control.md)、[対象判定契約](../contracts/target-assessment.md)を正本とする。同じ094へ組み込む上左通路のNav限定変更は[別計画](test094-shadow-passage.md)で根拠と試験を管理し、本計画の商品陰性・継続権限へ流用しない。

## 1. 概要

最新指示「本番の早さを想定して判定を実装」に従い、画像取得済みの同じiPhone内nativeで商品を判定する。商品確認後の各回をiSHへ戻して全20枚を回収・判定する循環にはしない。新しいcycle profileで、対象・候補はポーズ保持、証明済みの対象なしだけ直ちにPAUSE→RESTART→新ラン観測へ進む。unknown・判定故障も保持し、購入しない。

TEST094の最小受入は、一つのnative session内で複数の商店を判定し、少なくとも一つの陰性から次ランへ自動復帰する実測である。単なる見送りrestart、商品可視停止、ZIP完成をこの受入へ代用しない。

## 2. 背景

現在のCは `goods=VISIBLE` でfinishをラッチし、ポーズ後にterminalとなる。個別判定はその後のiSHでtarget/candidate/unknownを返し、無一致は `unknown/no_target_evidence` である。TEST089のC化・先行取得はこの後処理を短縮しただけで、陰性権限と周回への接続はない。FR-088-CPU/089-KERNEL/089-EARLY/090-RING-COST/090-UNKNOWN-TEXTを照合し、同じ後処理経路の小変更を本番速度の完成としない。

既Cの `tools/ring_native/{observe,icon,word}.c` は利用できる。canonical 15 source/feature/toolchain/licenseと固定i386 ELFは全bytesを維持する。i386 ELFやstdin/PNG wrapperをiOSへ持ち込まず、固定featureと画素関数を同じsourceからarm64へ組み込む。新しい処理は `NG2Ring.h/.c` と独立featureへ置く。新言語・外部判定サービス・ユーザー所有Macは要しない。

## 3. 詳細設計

### nativeの流れと非同期境界

global API `1.98.16-ngg2` / 旧cap15・revision v1〜16/profile1・2・閉schemaは維持する。新しい独立capability `necrogold_native_cycle_v1`、profile `normal-1-1-cycle-v1`、query schema `ngg2-cycle-v1`、専用client revision `native-cycle-v1` を追加する。新clientは専用閉parserで確認してから開始し、capなしを旧runへ無断fallbackしない。旧preflightへ新fieldや新profileを混ぜず、旧runの開始・回復・exportを維持する。

新profileだけ `WALK → GOODS_HOLD → ASSESS → {HELD, OBSERVE_MORE → WALK, NEGATIVE_PAUSE → NEGATIVE_RESTART → SEARCH}` を追加する。旧profileのgoods latch/finish/terminalを解除して流用しない。公開Status/Event/Sceneの既存layoutは維持し、companion stateは `search/hold/assess/observe_more/negative_pause/negative_persist/negative_restart/held/done` の閉enumとする。queryはrun/owner/generation/level/cycle/source・状態・判定・固定reason・worker/保存/入力の実時刻を返し、旧statusのgoodsを対象種類へ読み替えない。

商品frameをcommitした時点で未送信MOVE/preparationを撤回し、新規移動をholdする。送信済み入力があればその一件の実終了・安定prefixを先に確認し、UNKNOWN synthなら既凍結を維持する。分類対象は現在のowner/run/generation、同completed prefix、両端非inflight/stable、正常rasterのimmutable RGBAである。対象frameは入力権限とは別の証拠としてpinする。

専用の一つの分類workerへ最大一job、保持証拠は最大二frameを渡す。取得/controlQueue/main/run lock上で画素探索・hash・保存を実行しない。取得のキューは最新優先を保ち、job結果を `(owner, run, generation, level/cycle, job, capture, prefix, raster SHA, feature/classifier version)` に結合する。workerは入力権限を持たず、結果commitと入力発行はcontrolQueueの同取消gateへ戻す。stale/旧level/旧jobは状態を変えず破棄する。停止はworker終了を待たず新規入力を禁止し、lease解放は分類・保存・取得・mainの実終了までdrainする。

既C kernelの有限探索・float演算順・mode0/1・first tieを共用する。Pythonに残るmin/round9、word選択、行選択、target/candidateの集約は新wrapper内の小さいC aggregationへ同値移設する。全slotのraw wordを計算する現仕様を維持し、名前探索が幾何的に空ならnullとする。canonical kernelは変更せず、wrapperが各有限observe/icon/word呼出しの前後と新しいslot/aggregation loopで取消・実時計・期限を確認する。旧関数の画素/行/slot上限を維持し、途中でOS強制停止できるとは扱わない。controlQueueはworkerを待たず入力を止め、遅延結果を破棄し、leaseは関数の実returnまで保持する。NaN/丸め境界・arm64/libm差を境界試験で固定し、fast-math/FMAを使わない。

target/candidateを認めた時点で追加入力を禁止し、既安全条件でポーズを確認して通知を一回だけ発行する。現 `ring_observe` は三価格の行だけを返すため、新profile専用に観測sign/価格/ITEMの対応から単品slotを得る有限adapterを追加する。PARTIALでもそのslotの共通icon/word関数で候補を保持し、三列抽出できないことを陽性証拠を捨てる理由にしない。旧CLIの観測/出力は変えない。

観測継続は専用結果 `OBSERVE_MORE` に限定する。判定が正常かつ採用期限内、同frameのScene.goodsがPARTIAL、coverage=incomplete、同levelで一度でも対象候補を見たsticky latchが0、送信不明0が必要である。さらに最新の独立stable/current-prefix Sceneでsafe next FLOOR・全保護・完全Decision・新しい将来拍/準備・元期限/累積予算を再証明した時だけWALKへ戻す。hold時に退役した旧ticket/preparation/phaseを復活させず、別ID/新資格を作る。full-visibleのunknown、slot未登録による最終unknown、failure/timeout、候補latchありは全てHELDで、unknown一般からの移動再開分岐を作らない。OBSERVE_MOREにrestart権限はない。

### coverageと陰性証明

可視性・対象一致・対象以外の確認を分ける。新判定は `coverage=complete/incomplete/unknown`、slotごとの `target/candidate/non_target/ignored_container/unknown`、全体の `target/candidate/negative/unknown` と固定reasonを持つ。故障/時間切れは有効unknownへ丸めずpending/failureで保持する。

coverageの対象はユーザー指定の通常ケイデンス日本版1-1金店に限定し、layout契約 `cadence-jp-1-1-gold-strip-v1` を追加する。これは「全商品3つ」を確認する対象の有限layout classであり、一般の店/部屋/世界全体を三品と仮定しない。[rebuildのcomplete要件](rebuild.md)を、このlayout認証と実観測集合の一致で満たす。屋根や店全体は不要だが、商品三品の全footprintと隣接する空床endcapを同じ一枚で直接確認する。別layout、余剰商品、切れ、未対応componentはunknownで保持する。最新ユーザー指示「宝箱はいらん。のろいのゆびわだけ」に従い、陳列されている対象だけを探す。宝箱の中身は識別せず、閉じた宝箱を正に確認した場合だけ独立結果 ignored_container として対象外にする。

row anchorを `(L,S)`、各中心を `c=L+36k (k=0,1,2)` とする。Sceneは同RGBA由来のFLOOR/既goods VISIBLE、実GOLD cell一個以上が必須。二つのsign board幾何、少なくとも片側の完全なSHOP全文glyph、独立merchant spriteで金店layoutを認証する。boardは既raw component条件（画素数150以上、幅18..48・高16..40）に加え、中心差 `72±2px`・縦差2px以下、両方の観測SIGN component全bboxがscreen/HUD外にあることを要求する。このmode1は観測componentの幾何を証明し、物理板の黒い外周や店全体の完全観測を主張しない。SHOP全文のIoU≥.94/coverage≥.95を片側以上で要求する。merchantは中心 `(L+36,S)` 周囲の固定derived saturated-foreground featureをNCC≥.94/foreground coverage≥.95で照合する。source SHA/ROI/feature SHAと有限phase variantを固定する。黄色componentだけをidentityにせず、merchantや唯一の完全SHOPが欠ける場合はunknownにする。

反対側SHOPの全文は商品名の正常なoverlayで欠け得るため必須にしない。この側は観測SIGN componentのbboxと72px配置・認証merchant/片側SHOPとの同layout関係で検証する。原条件を満たさない場合だけ、別mode2の固定36×40内の既GOLD|SIGN mask・四隅/辺75%/説明できない外周0の追加証明を試みる。mode2の不成立を理由にmode1の有効な証明を取り消さない。商品名を任意maskして読めたことにせず、商品自体の名前/iconは独立に完全照合する。326右SHOPは四文字全てに商品名が重なるので、二つの完全なSHOP文字が残るという別の期待も置かない。これは低いSHOP scoreの受理ではなく、別の有限認証条件であり、他layout・余剰board・別merchant・片側SHOPも無い例をcounterexampleにする。

各品のbrightness-presence帯は `[c-18,c+18)×[S+24,S+66)`、価格帯は `[c-11,c+12)×[S+69,S+89)` とする。通常商品はicon/完全表示名の認定footprintと同baselineの価格componentを直接得て、一対一・非重複に対応させる。ユーザーが除外した閉じた宝箱だけは、名前を要さず、全sprite footprintと独立した閉じた蓋・帯・縁・足の形状を正に照合する。宝箱の実bboxと価格baselineは出典151/213から固定した有限variantを使い、実price componentとの唯一対応を要求する。任意に価格帯を広げず、中身をnon_targetと主張しない。価格は数値を識別せず、既white条件/18画素以上・有限9px baseline探索を用いる。full icon footprintはbrightness帯と区別する。幅/高さ36px以下、左上は既bank探索の `x=c-width/2±8`・`y=S+24..57` にあり、全bboxが認証strip/viewport/HUD外に収まり、他品の全bboxと重複しないことを要求する。名前は既有限探索内の実tight boxを使い、merchant/sign等との重なりで欠けた名前を完全としない。各footprintはscreen/HUD外に収まり、slot間の結合を替えない。

空床endcapは中心 `(L-36,S+48)` と `(L+108,S+48)` の各25×25pxである。両方の全域と上下12/13px半域に既 `ng2_material_floor` と同じmedian/variance式を適用し、可視画素90%以上（既floor証拠の90%境界を採用）、既item-presence条件のbright24画素未満を要求する。隣接価格帯も既white18画素未満とする。SceneをFLOORへ塗り替えたり、上方の金壁から空床を外挿したりしない。これらは商品列の観測終端であり、店の物理内壁の位置を主張しない。

独立component列挙の対象は認証strip `[L-54,L+126)×[S+24,S+89)` と、その中の価格帯である。価格群が実際に三つあり、上の三品へ唯一対応すること、認定name/icon/price footprint外に既item-presence以上の未対応componentがないことを確認する。既Scene ITEMやcanonical row三slotだけから個数を自己認証しない。複数の認証row/異なるbaseline/余剰価格・item/視野外延長/暗転・遮蔽はcomplete0。部分画像の継ぎ合わせで欠けた領域を補わない。

coverage witnessはlayout版、row/strip box、merchant/signのbox・score、観測item/価格数、未対応component数、各品のname/icon/価格box、両endcapのbox/median/variance/可視・bright・white数、Scene state/goods/実GOLD数を固定長で持つ。各数値の範囲と配列長を閉schemaへ固定し、run/generation/prefix/capture・RGBA SHA・feature版へ結合する。native pure APIは `NG2RingOptions` の `const NG2Scene *scene` がNULLならpositive/unknownだけを許し、negative0とする。

093原326（SHA `0fe7ff9a24dd18af72c31b53a97246eb497917c8539205bb5a41af6fb4c362d8`）の既rowは `(482,43)`。endcapは `(434,79,25,25)` / `(578,79,25,25)`、medianは25/15/14と28/17/16、blackは56/625と50/625、両者の全域/上下半域は既floor式を満たし、bright/whiteは0である。これは屋根や右内壁を外挿しない幾何校正で、既Sceneのラベルは変更していない。merchant/SHOP/全slot/余剰componentを含む新detectorで全条件が成立した場合だけ326をnegative正例にする。別条件を緩めて期待へ合わせない。

各slotのnon_targetは、対象以外の識別済み商品について独立した名前とiconの両証拠・空間結合・競合排除を持つ場合だけ成立させる。既実画像で人が識別できる非対象品から出典SHA/ROI/版を固定した有限feature bank（最大16品）を作り、icon≥.94・word IoU≥.94/coverage≥.95・唯一一致を要求し、対象/類似ringと交差検証する。価格・run/capture ID・特定配置を識別条件にしない。未登録品、名前未読、対象icon候補、判定競合はunknown/candidateで保持する。093原151の第三品はclosed chestで中身未観測である。最新指示により正に認定した closed chest は ignored_container として除外し、armour等や中身のnon_targetへ読み替えない。未認定容器はunknownのままにする。このbankの対応範囲を明記し、全商品を一般識別できたとはしない。実画像からこの証明を作れない品を低い対象scoreだけで陰性にしない。

negative certificateはcoverage witness、観測集合と全slotのnon_target又はignored_container witness、候補0、同run/level/prefix/画像hash、判定版を結合する。いずれか不足ならnegativeを発行しない。二frameを使う場合も異なる位置/slotを混ぜず、候補を一枚の陰性で上書きしない。

### 再開権限と有限予算

negativeなら直ちにPAUSEを新規予約する。証拠保存はPAUSEの実行・settleと並行できるが、RESTARTはPAUSE ACK/実画面・restart labelと証拠commitの双方が成立してから一回だけ発行する。全ての入力は最新の安定completed prefix、fresh Scene、実時計、前面、lock、owner/generation/cancelを再確認する。古い分類frameは現在の入力sourceへ昇格させず、新しいPAUSE UI観測から権限を作る。

RESTART送信成功だけではlevelを進めない。既fingerprint変化と有効FLOORを確認し、新しい初期描画/HUDで探索・beat同期をやり直す。旧ticket/epoch/位相を破棄し、UNKNOWN入力/不明startを新IDや新runで再送しない。起動時PAUSEからは直接RESUME、陰性後PAUSEからだけRESTARTへ進む。

094は単一native sessionを維持し、既16方向入力/12restart、最初のwalkから45秒、session180秒、元予約/再予約/visual予算を累積する。陰性・level切替で更新しない。新しい安全上限は判定済み商店最大四件、分類一job・二frame、証拠保存一writer・未commit一件。四件/既予算/保存上限でポーズ保持して終了する。長期500restartを満たすepisode継続は別の明示契約であり、094でsessionを勝手に作り直して実現した扱いにしない。

### 端末内証拠と回収

新profileは私的Application Support配下にsession UUIDで専用spoolを作る。任意pathをwireから受けず、通常file/権限/非symlinkを検証する。各cycleの証拠RGBA、取得両端/prefix/generation、C status/event snapshot、coverage/各slot/certificateをcanonical manifestで結合する。固定長RGBA8/896×414・全alpha/size・SHAを検証し、exclusive part書込→file同期→rename→directory同期でimmutable commitする。陰性RESTARTのintentを送信前に保存し、ACK・次ラン確認は別の連結recordへ追記する。既commitや既ZIPを上書きしない。

各cycleは判定authority/必要proof、PAUSE入力source/確認、RESTART source/確認を重複排除して最大六rasterとする。四cycle＋従来terminal診断最大20枚で計44枚、raw spool64MiB、metadataとexport temporaryは別途各2MiBを予約する。新profileの最終PNG上限は各2MiB/計88MiBとする。通常PNGを一度だけ作り、encoded bytes・長さ・SHAをimmutable sidecarへ耐久保存してからexport manifestを凍結する。通常PNGが失敗/oversizeの場合は固定geometryのRGBAからbounded stored-DEFLATE PNGを生成する（896×414 RGBA/filter0・23 stored block・単一IDATで1,484,368 bytes）。同manifestのretry/recoveryは保存済みの同encoded bytesだけを返し、別encoderで再生成しない。これによりrestart後の圧縮率が悪くても証拠を欠落扱いにして捨てない。旧profileの512KiB/10MiB上限は変更しない。事前に次checkpoint最大量を予約し、書込/同期/hash/空き容量/件数の故障ではRESTART0・保持停止。未commitを破棄して次cycleへ進まない。生画像と証拠はGit外に置く。

rawが耐久commit済みなら次levelへ進める。PNG化・paged RPC・iSHの全画像検証/ZIP出版はsession終了後でよく、各cycleに全20枚RPCを挟まない。PNGは一枚ずつ生成・送出してmemoryを解放する。immutable PNG sidecarは出版ACKまでdiskへ保持し、別途88MiBのexport quotaを予約する（raw64MiB＋metadata2MiB＋temporary2MiB＋encoded88MiB）。新profile用の閉schema・全登録集合certificate・全cycleを含む一session ZIPを設ける。native manifestはexact UTF8文字列とSHAを返し、JSON数値の再直列化へhashを依存させない。header/耐久record/frame envelope/中断artifact目録は最大558 descriptorへ結合し、64KiBごとに専用record modeで回収する。返却ZIPは終了後のC zlibによるstream deflate level6を使い、全member bytesを再読込照合する。旧active/report/target sidecarと意味を混在させない。chunk64KiB/batch四chunk・暗号HTTPは維持する。cycle専用batchはraw256KiB以下・wire512KiB以下、単chunk応答256KiB以下とし、旧profileの応答上限は変えない。新しいnative sessionのstartは前sessionの全公開後だけとする。プロセス再起動やowner変更後はspoolをread-onlyで回収し、未確定の入力intentを自動再実行しない。開始前にsession headerとunpublished indexをfile/directory同期し、その完了前はRESUMEを含む入力0とする。起動時のscanは専用queueで行い、pending/故障/未出版cycleがある間は全profileの新startをdefinitive_not_startedで拒否する。空の旧環境の挙動は維持する。現在の認証済み同端末ownerは明示UUIDの旧runを回収・出版ACKできるが、旧owner/boot/時計出典を保持し、入力再開権限を得ない。

回復では元spoolを変更せず、別のrecovery/export/publication receipt ledgerへ記録する。header未commitなら検証済みUUID directoryをanchorとしoriginal owner未確認・authority0の診断とする。未確定intentはUNKNOWN、孤立したrawは診断だけ、partは未commitとして長さ/hash/件数上限内で列挙する。finalmanifest未作成ならcommitted registryから中断診断manifestを決定的に作り、raw由来PNGは版固定stored encodingで別recovery ledgerへ保存する。参照欠落/破損はincomplete diagnostic ZIPと明示し、通常の全画像証明や完了へ偽装しない。診断出版ACK後、旧workerの実drainを確認した次の明示startだけを許可する。同じ回復呼出し内で新ゲームを自動開始しない。保存/同期故障はdurable_ns0・RESTART永久0とし、可能なら実PAUSE後に不完全証拠として終える。

queryは専用RPC necro_native_cycleを使い、mode prepare/status/manifest/chunk/batch/published、envelopeはschema/run_id/profile/mode/payloadの閉形とする。prepareはゲーム開始前にLoopCtrl前面で通知許可を確認し、必要な場合だけOS自身のrequestAuthorizationを行う。許可操作を合成しない。拒否/利用不可なら新profileを開始せず具体表示する。target/candidateの安定PAUSE後はUNUserNotificationCenterへ一回だけasync投稿し、request受理と実配信を区別して記録する。iSHログをOS通知の代替とはしない。publishedはexport_id/manifest_sha256/archive_sha256を受け、全登録fileの同一性とmanifest一致を確認してclient出版のreceiptを耐久保存する。各chunkが実際にclientへ届いたことをnativeが証明したとは扱わない。nativeがclientのZIP全bytesを確認した証明とは呼ばない。

## 4. 試験影響範囲と性能基準

変更対象は新ring wrapper/aggregation/coverage feature、C Controllerの新profile状態、Swift Runtimeの分類/保存worker・drain・回収、独立cycle capability/profile/閉schema、094 iSH entry/出版/evaluator、build/seal/限定CIである。canonical ring15source/ELF、旧API/cap/profile/schema、Perception既認識閾値、UI座標、G1/R12は維持する。Nav追加は冒頭の別計画で扱う。境界変更が広いため設計・網羅・安全の独立重点レビューを適用し、無関係な全world再試験は追加しない。

提案予算は「商品frameのcapture開始→判定commit」p95≤150ms、分類worker単体p95≤100ms、candidate確認→ポーズ成立p95≤500ms、商品frame→陰性後の次ランHUD p95≤1.0秒とする。後者は同条件の人比較も行い、[既PERF-01](../requirements/necrogold.md)の20%以上短縮/有効商品確認数を置き換えない。暫定値は実装・実測前に固定し、未達を後から緩めない。

一jobの採用期限は `min(worker開始+100ms,capture開始+150ms)` とする。これは結果採用の資格であり、旧kernelを100msで強制終了する保証ではない。controlQueueはworkerと独立にこの期限を検査し、超過時は追加移動を出さず保持ポーズへ移る。時間切れをnegativeへせず、遅れたcallbackも資格を復活させない。実returnまでworkerをdrainする。保存は分類と別に計時し、RESTART待ちを含む全経過時間に算入する。開発CPU/i386/QEMUの倍率やCI上の時計をiPhone速度の証明にしない。

## 5. 新規ケース

- 識別: 実対象・類似ring・非対象bank・未登録品、PARTIAL単品adapterと旧CLI三列互換、部分二品、欠け/暗さ/重なり/端/HUD、名前とiconの別slot、不一致row、四品以上、名前探索null、閾値/round9/tie/mode0・1。正例校正と未知評価を分け、対象no-matchからnegativeが生じないassertを置く。
- coverage: 専用layout認証なし、二つの空床endcap欠け、観測三品でもfootprint切れはcomplete0。屋根切れだけならstripが完全な場合に限り受理。一品欠け/未対応、余剰ITEM/値札、遮蔽物、別画像のslot混合、古いlevel/prefix、二frameに候補が一つあればrestart0。326は上の全predicate、151のclosed chestは強い独立認定を満たす時だけignored_containerを期待する。
- 制御: 二つ以上の完成shopを連続処理、negativeだけPAUSE→RESTART→実新floor→再同期、target/candidate/full-visible unknown/failureは保持。OBSERVE_MOREの正常期限内PARTIALだけを新safe-floor/保護/prefix/将来拍から再開し、旧ticketを復活させない。初期PAUSEをrestart扱いしない。16/12/45/180予算の同run累積、旧票/phase/UNKNOWN無再送、四件上限を確認する。
- 並行: 分類/保存の各commit前後で取消・前面/lock/owner/世代変更、遅延/重複結果、送信中商品、worker期限、drain未完で次run禁止、statusやexportがinput holdを解除しないことを実callbackで確認する。
- 永続化: 全write/同期/rename/manifest境界の中断、短書込/容量/上限/hash/異物/symlink、restart intent後の不明結果、通常PNGの失敗/高entropy→stored PNG全画素同値・2MiB境界、旧ZIP不変・read-only回復、全44枚の登録集合/cycle参照/ZIP証明。最初のnegative後に全画像RPCなしで次levelへ入れることを計測する。

## 6. 実装順

1. 本計画・profile/API/陰性certificate/保存契約・性能予算を独立レビュー。実画像の非対象witness/完全coverage成立条件を先に確認し、成立しないものはunknownに固定する。
2. 有効assertion Redを先に作り、新C wrapper/aggregationと境界取消を実装する。canonical15source/ELF不変を確認し、旧Python oracle/i386 packet・新arm64の全field同値と新negative/coverageの別期待を確認する。
3. Controller新profileのHOLD/negative復帰と旧profile不変をRed→Greenにする。Runtimeへ分類一workerと世代付きcommitを接続する。
4. native durable spool/intent/outcomeとread-only回復をRed→Greenにし、durable確認のないRESTARTを拒否する。新profile export/094 ZIPを接続する。
5. 実callbackで複数shop・取消・保存故障の必要結合を確認し、独立した最終設計/網羅/安全レビューを行う。P0解消、残P1/P2と次工程を記録する。
6. 同codeの標準CIでIPA/完全sourceを作り、通常1-1ポーズから094を実機確認する。商品到達率、陰性→次ラン、判定/保存/入力の実秒を受領して次の局所修正へ進む。

## 7. コミット前の検査

変更部の単体、旧ring089/090・商品保持・restart/prefix/取消・旧profile/export/出版の関連回帰、新worker/spool/API受渡しの結合だけを根拠付きで選ぶ。実Python3.9で094回収/旧pending互換を検証する。浮動/丸め/arm64コンパイル自体の失敗はRedへ数えず、固定feature・未知field・偽negativeを拒否するassertでRedを作る。

native変更なので `macos-26` / `ubuntu-latest` の既標準runnerで新IPAを実buildし、実compiler/flags、更新seal、全Mach-O禁止marker、G1/R12全40不変、同code全source ZIPを照合する。既LoopCtrl Apache・musl/Zig MITの出典/通知を保持し、プロジェクト全体へ新しいlicenseを付与しない。固定ReleaseへIPA/sourceとhashを公開し、匿名全GET/実tagまで確認する。試験件数を増やすための無関係なフルCIは行わない。

## 8. 範囲外と実機返却

自動購入、未知を飛ばすモード、全マップ探索、旧UNKNOWN入力の解除/cleanup、途中ZIPの改変、ユーザー所有Mac/有料runner、未実測の即時性/一般識別/長期耐久保証は追加しない。bank対象外の品やcoverage不成立で保持する限界を表示する。未知陽性0と既校正を混同せず、稀な対象を出すための周回をユーザーへ要求しない。

配布時はIPA更新・LoopCtrl完全再起動・iSHの具体的コマンドと、新しい一連試験を示す。通常1-1ポーズから一度開始し、native内で候補探索→商店→個別確認→証明済み陰性なら自動restart→次の商店へ進むことを確認する。自然配置/有限上限により二店へ届かなければ未達として理由を記録し、手動で金可視配置へ合わせない。対象・候補・unknown・故障・利用者停止・予算で保持した後、session全cycleの表示ZIPを返却してもらう。過去093の回収済みrunを再回収しない。

## 設計レビューの処置

独立した設計・網羅・安全レビューで、coverageの具体predicate不足P0は上記layout/全観測集合/認定row結合で解消した。PARTIAL再開/API互換/通知・回復・PNG同一性の設計P1も上の独立経路で具体化した。未実施のP1（実データ交差検証、余剰component/候補veto、native期限、実callback・耐久故障）は実装検証工程へ残す。入力実装を新profile内で進めることと、陰性権限の配布合格を区別し、最終aggregate有効化・IPA配布前に該当assertと独立差分レビューを確認する。

実装時の独立レビューで、SEARCHの通常RESTARTと陰性RESTARTの分離、初期判断画像保持、次floorのPARTIAL/VISIBLE、full templateとbrightness帯の区別、UNKNOWN/frozenの診断回収、journal二重rename中断、回復ledgerの同一性、request-local不正rangeの非poison化を確認する。新clientのper-run journalを耐久正本としactiveは選択mirrorとして扱う。保存済みraw/全PNGの確認前に完了を表示しない。

094の未受入: iPhoneのp95/人比較・長期耐久・未知配置精度、有限bank外の品、原326/151のlayout不成立は未判定保持。採用期限後の有効positive証拠は捨てず保存し入力0で保持するが、timely判定とは別の遅延positive専用通知は未実装P1。保存済みsessionは128件/回復ledger128件の有限上限があり、自動削除は今回追加しないP2。

SEARCHの通常restart直後に最初のFLOORがPARTIAL/VISIBLEである場合も、元のACK/prefix/指紋/4秒を先に処理してから新しい商品jobを結合する。新指紋の証明がない場合はrestart/level creditを増やさず、保持ポーズと個別観測だけに限定し、OBSERVE_MOREと陰性restartを禁止する。未開始journal/認証済み-32095と不明な開始は区別し、後者は再送しない。保存不能-32096をpendingとして回し続けない。
