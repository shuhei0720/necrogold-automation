# TEST092: 起動・通路前の停止と指輪表示

2026-11-13（日本時間）。基準5ddb6c6a38ccab8dc49bcfe518560ceadb99144f。[修正記録](../fix-records.md)を修正前に照合。小さな差分の単体/関連・同一担当の独立レビュー1回・必要なIPA作成に絞る。新しい実機改善は未確認。

## 受領と根拠

初回d503は新規start約426ms後、capture1のmetadata/aspect（828×1792、EXIF1）でgeometry停止。raw未保持で画像の中身は未確定。前面PIDの確認と描画向きの更新完了を分けていない。画面の「ZIP保存再開」は停止結果を先に公開する正規回復で、元の停止とは別。次の実行で起動できた事実も保存する。

後の4ZIP/77PNGは全CRC/SHA/strict load/certificate/canonical sidecar/登録集合に一致。実時刻順は7702 goods6歩→7a8d beat2歩→56df goods7歩→6d60 screen0歩。7a8dは公開対象17枚で回収不足ではない。goods2回は正式source/row/3slotがあり絵・文字の個別engineを実行済み、結果はunknown/no_target_evidence。原326はシャベル/ロングソード/コンパス、原327も対象名・絵を目視で確認できず、正しい陰性判定の合格とはしない。残2回はno_authorityで個別判定未実施。

## 1. 起動の縦画像だけを有限待機

Raster/EXIF/比率は変更しない。既存のactivationDeadline3秒を前面確認と起動portrait待機後の新request admissionに共有し、再延期しない。初正常decode前・未解析/未観測/未入力・prefix0/非inflight・同owner/世代・取消/lockなし・freshなexpected前面証拠下だけ、metadata/aspectかつ厳密な縦反転比率・EXIF1/欠落の失敗を解析せず再取得する。最大64試行/50ms無入力待機、次request admissionでも元期限を確認。元期限より前に発行済みのcaptureは既2秒のreply期限/実drain契約を維持し、期限後でも正常replyなら元の世代/owner/取消/prefix/freshness gate下で扱う。期限以後の新requestはなく、portrait失敗が続けば元metadataで終了。正常decode1回で永久終了。square/encoded/reply/timeout/analysis/EXIF不正・正常後のgeometryは旧failfast。

前面queryはmainの実終了までlease/mainOutstandingを保持し、前後の取消/owner/世代/lock/PID/freshnessを確認。再launch/再入力はしない。最終failureは既capture_failureへ元metadataを保持し、途中のportraitは正常画像や入力権限にしない。新wire/期限延長なし。新HOST fixture/hashを製品編集前に固定し、Swift不在の開発機で事前の意味Redを実行済みにせず、最終Mac同job内で固定基準Runtimeの有効Red→現Greenを各1回実行する。

## 2. GOLDを保つ静止の別証明

7a8d source125→127/152は旧19段UNKNOWN、far DIRT→STONEだけで次UP/reason8/目標(0,-4)/FLOORは同じ。旧GOLD2/全旧STONE5/旧DIRT20・unique9zeroが保存される。rawzero .46762/gap .29038、旧static gradient94.35%で95%条件に不足。world95%は826/不一致21、上下399/427。独立axis75%は1158/93、上下775/383、既競合比較を満たす。

旧19段/旧95%条件を変更せず、UNKNOWN専用zero証明を追加。両FLOOR/CANDIDATE/商品UNKNOWN・原点/次FLOOR/全保護0・完全同GOLD2/unique9zero・全旧STONE2以上保存/非共線旧DIRT9以上を要求。raw全73有限/zero最良/gap≥.08、world95%/二帯各100、axis75%/二帯各100・全73に既texture_leadをANDする。競合の支持300未満は優位の肯定証拠と呼ばない。MOVED/開通/未来の商品を与えず、既BLOCKED0歩へ返す。元ticket/時刻/UNKNOWN無再送/待機予算は維持する。

## 3. 地図外の金候補と観測通路

6d60原280には上端で切れた金壁が見え、CANDIDATE/peak158だがgrid内GOLD0。通常chooseはNO_PATH、passageはCLEAR専用のためmask0。原280は最終PAUSE sourceであり、未保持の最初の拒否279や全194→279の状態を代用しない。診断と画像から分かる適用漏れを直し、最初のpredicate未確定は残す。

候補をCLEARへ変換せず、FLOOR/CANDIDATE/既gold閾値peak≥135・商品UNKNOWN/GOLD0/原点FLOOR/全ITEM・保護0だけを正の未局在候補とする。Navは既mouth/床/保護/経路の条件を維持してこの観測を追加適格とし、入力許可を持たない。grid外GOLD捏造・新enum/ABI・未観測床/掘削/普通扉の許可は追加しない。

Controllerにprivate passage_unlocalized_gold/initial_candidate_unlocalizedを設ける。初期の候補mask非zero、独立2枚の同positive分類/同mask/口脇30支持を要求し、mouth/world原点を固定する。CANDIDATE0のmask0はUNKNOWNで初期見送りへしない。移動にだけ使うpassage_floor(CLEARまたはpositive)と、旧clear_gold_floorの陰性条件を分離する。

適用点はsafe_step、初期uncertain/start_floor/remember/recheckと091の確実未送信初歩再取得、observeのactive passage guard、route/goal進捗・無入力待機、stationary/unsent passage guard。closed_passage_mouth・旧CLEAR-onlyのrestart判定は不変。private意図flagは陰性/restartを拒む方向だけに単調に保持し、移動は現在の適格Sceneと旧fixed mouth/完全Decision/静止証明が必要。既stationaryの物理snapshotは変更しない。2枚proof後もpositive意図を保持し、localgoalでactualGOLDが未確認ならNO_PATH/未局在未判定として保持する。後のCLEARだけでそのpositive意図を捨ててrestartしない。もともとのCLEAR通路候補での局所見送りrestartは維持する。初歩再取得中にmask0/口UNKNOWNとなっても陰性へ変換しない。

新flagはactualGOLD/商品handoff・finish/terminal・level切替時に撤回する。商品/保護・取消/旧prefix/ACK_UNKNOWN無再送を優先し、16入力/12restart/45秒walk/180秒session、同期12秒、旧2拍待機/再取得回数を維持する。新しい未来MOVED証明は追加せず、実移動は既motion verifierへ渡す。未収録の進入先を合成して実機到達としない。

## 4. 指輪判定の実施状態を表示

unknownを一律表示していたFR-090-UNKNOWN-TEXTの継続。正式sourcesあり/早期classifier結果cacheありは「実施済み・一致未確認（対象なしとは未確定）」、正式sourcesなしは「未実施（判定できる商品画像なし）」を共通formatterで表示する。target/candidate、source authority・sidecar/schema・feature/閾値/ELF15sourceは不変。新5＋旧表示1を実Python3.9で確認する。旧mockの不足metadataだけを実sidecar形へ補い、対象なし未確定の旧assertを維持する。

補助progress試験がhostのi386直exec非対応で失敗した場合は環境失敗と記録し、意味Red/Greenにしない。進捗literal/他本文の保持と変更表示の単体を分け、原画の再分類やkernel再buildは不要。

## 検証・配布・未確認

変更部の新単体と必要な関連のみ。起動/取消/前面/owner/世代/元期限、Cの候補保持/静止/未送信、表示を検査し、実機の未来応答を合成して到達率にしない。Macro/ABI/API16/cap15/G1/R12を維持。実22seal/実compiler/全Mach-O・旧342禁止marker/全source/IPAを同じCODE/runへ結合する。固定Releaseの正式checksum名は既publisherどおりSHA256SUMS.txt。公開後匿名全GET/actualtagを照合する。

画面調光そのものは現nativeの停止理由ではなく、今回4runにロック理由4はない。間接的影響まで否定せず、idleTimer/輝度変更は混ぜない。主指標は商品全体確認への到達率。新IPA更新後、通常1-1ポーズからrestart→候補→商店→全商品確認の一連4回と全run ZIPを依頼する。
