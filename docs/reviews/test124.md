# TEST124: TEST123原本・停止原因の検証記録

2026-11-27（日本時間）。[計画](../plans/test124-device-failures.md)。出荷CODE578a9ef/実IPA274/SHA30a48a1d、保存HEADfd5901dを基準にする。正常producerと実採用、イベント時刻とactualcommit、元入力と実unitを区別する。

原本10ZIP/278member・5run/5campaign・120stable PNG/138記録を全照合。不足0、全5campaign内包lastZIPは提出run原本と同bytes。実順d7a4/b48e/aa0d/ea66/6fa4。初回RS要求＋knownACK5/5・実unitのあるroot5/5・開扉4/5。native FULL1/5と人の3商品icon可視2/5は別指標。対象実在1(root3)に対する正常候補検出0、対象外で全商品可視のroot5は実RS0。商品後の新floor/child0。

## root3の対象見逃し

aa0d/source196の原PNGには左商品に指輪spriteと「のろいのゆびわ」表示がある。原正常job1は開始60440547773708→完了60440551523750、元D60440639936833、採用60440551958833。完了時88.413083ms/採用時87.978ms余裕がある。status okでもoutcome UNKNOWN/coverage incomplete、row_count=partial_count=0、candidate_latched=false。判定前停止・期限切れ・CによるNEG拒否ではなく、通常抽出段階の対象見逃しである。

出荷Runtimeの対象通知はPAUSE成立/cancelReason0/targetまたはcandidateを条件にするため、このUNKNOWNは対象通知条件に入らない。原exportにOS通知request/配信receiptはなく、汎用停止通知が別branchで出た可能性は残す。「通知が一切なかった」とは断言しない。

## 原停止の境界（解析中）

root1はguard BUDGET5とcontinuous更新8回の原記録があり、商品job0。root4は初回LEFT実unit後、未送信次票のFRESH/SAME更新後のSCREEN17。root2/3/5の保存された正常packetは全てUNKNOWN/incompleteかつ採用済みで、後のstatus上書きと区別する。root2/5の過去job1結果は未出力で、保存されたjob2から捏造しない。

修正箇所・機能別短計画・正式Red→Green・直接関連・独立差分・新IPA/全source/固定配布は原因を確認してから追記する。


受領最終receiptは `test124-intake/receipt.json` SHA8acb4d42、原全10ZIPは60,430,262B。初回RSの全before/after PNGは未保持で、新floor画像の完全証明を補わない。商品後RS intent/outcome/新floor/qualified/childはいずれも0である。

## 原画像・既版との比較

ringの保存stable商品12枚は出荷123と旧122で全Scene/全6112B packetが同値（cause-calibration SHAfc82baa1）。root3は観測sign0でkernel未到達。実右看板の最大成分228px/29x13と次106px/29x7は既高さ16未満、左はpause HUD内にある。通常Scene由来cx448/base_sy15を元kernelへ直接渡した診断ではscore.832406544/実pose429,45,33,28で候補閾値.80を超え、実pose自体はHUD下端45と交差しない。この強制slot診断を正常producerの成功と呼ばない。

新positive-only計画は全canonical spriteの安全な探索unionを先に証明し、normal mode2/UNKNOWN/不完全/row0/partial0/sign0・観測ITEM・中央top-HUDの有限1候補だけを扱う。既kernelで正の画像候補を得た時だけCANDIDATEへ追加し、no-hitのrows/partial/safe/cert/権限を保持する。checks/finishedは実作業を反映し、非OKを伝播する。TARGET/NEG/購入/移動資格を追加しない（plan bf6011d6/独立review ebcc800e）。

root5のUNKNOWNは、右cap398,117,25,25にblack461/625=73.76%の未観測があるため正しい。原188をNEGへ変える期待やfloor閾値緩和は採用しない。187→188は通常直接BLOCKED零だが、原ACK16の180→187/188は通常UNKNOWNのまま。180goods0→187初FULLで、その後の実view入力0とprivate full_spent未使用を同一視しない。旧full_admitはMOVE発行前にspent1/framing1をarmでき、未発行DATAでframing/sourceを消す一方spentを残すため、原unexported job1からmodeを捏造せず、所有された未送信oneviewの追加観測資格を別計画で検討する（独立cause critique SHA8565cdbc）。

## client/cap124の限定準備

正式意味Red17件/28assertion failure/errors0→Green17、実CPython3.9.25直接関連220Green。旧entry/shell・metadata bodies/既API/profileを保持し、新124のnamespace/capと旧future-invalid番号だけを限定変更。独立差分P0/P1/P2=0（clientreceipt3b3a9338、reviewce90278f）。source-only selector/host/Py39配線はflags=falseの準備とし、機能authorのmethod/CORE閉包/封印前に実行しない。


## 閉じた限定修正

root1は正の単一remote金露出の同ID保持と、直前採用済みGOLD消失を旧quiet/mask0経路でも拒否するcaller fenceを追加。公開APIでrun8をearnedした旧123の同2case/2意味Red/errors0→新8Green。直接関連13Green。旧072の2methodは7assertionが旧123でも同じ失敗で、未合格/今回非選択と明記し、15全合格とはしない。source/fixture/旧12helper/peer-ownedを独立確認しP0/P1/P2残0（root1 final review fd5e1f32、ownedCfb25842e）。

root3は旧123原196の意味Red1と公開9methodの6意味Red/errors0→新9Green、旧関連5Green。新正常候補.832406544/実pose429,45,33,28を得て、他24packet全6112Bを保持した。新fallbackが適用されるno-hitは意味fields不変だが、実checks/finishedは必ず更新する。公開Cモデルで候補→PAUSE/ACK→耐久保存、MOVE/RS0。OS通知の受理/配信は未観測。原ns差を保った非同機実clock1対で旧UNKNOWN3.37ms/新候補6.55ms、新D余裕85.608msは校正でありiPhone速度合格ではない。Ringb42c1695・test18131cd4、独立最終review120931c3。

root4は公開earned初動→FRESH/SAME→元anchor通常UNKNOWN/current直接零の旧123意味Redを確認し、新DATAで退役後の独立A/B、新fit/将来新ID、元P/W/scheduleを保持した。既承認rawHUD履歴だけを保持し、各履歴はその取得時点の安定prefix、退役後A/Bは現prefixに固定する。C-return後の退役barrierは最初のguard済actualtickで一度だけarmし、その前に開始した並行captureをproofへ使わない。

独立レビューは、新actualGOLDを単に待ち続けるP1を検出した。追加意味Red後、clear権限撤回→別GOLD anchor/新actualtick/独立GOLD A/B/normal fullDecision/newfitを経て、元境界内でFLOOR/DOOR/DIRTの新ID一回へ渡す。実MOVEDだけ+1、実DOOR_OPENED/TERRAIN_OPENEDは0歩で既通常処理へ戻す。公開14＋直接関連16Green、P1閉鎖/残P0/P1/P2=0（review94f017ac、closedreceipt1c72b410）。旧13helperとroot1所有部分を保持。初期関連25では旧076の1method/2assertionが旧123でも同じ失敗で、未合格記録を残した。全部の旧集合が新Greenとは書かない。

## root2の因果の訂正

原sealed checkpointはjob2adopt直後ではなくPAUSE25のACK後であり、HELD/completed1だけからprivate upperを確定しない（source-order bdc8eca2）。一方、hold_started60292561272458がactualH1 begin60292806000041より前のまま保存される。出荷CODEの全9hold代入/queued-bindを独立監査し、generic新PARTIALは実unit後nowへ更新、FULL-only/current-UP/entry/lower等の他復元は原LEFT/PARTIAL/row+4に不適であり、oldholdを明示復元するupper_bindへコード論理的に絞れる（hold ancestry5c6dfa92）。これはコード/データ同一を前提とした帰納で、未出力private値の直接観測ではない。

raw2SHOP投影は正しい新potentialであり、HUD誤検出という初期推測は撤回した。旧5＋新2をScene/保護から消すのではなく、有限possible-regionとして保持して各足場を再検査する計画を採用する。D3原UNKNOWN/protected1は未来currentで解決するまで進ませない。


## root2の限定実装・差分確認

V2の実H1が通常MOVEDした後だけ、旧5＋新2potentialの所有をprivate tokenへ固定し、全7ITEM/全保護・元hold/P/sync/5stepsを保持する。現正常safe job・独立current・既firstsnapshot boundsを通して残LEFT1→DOWN3を進め、原D3の未観測/保護が残る場合は進めない。別GOLD/ITEM/保護変化はsticky invalid、対象候補が先行する。checkpointのHELDからprivate値を補う実装にはしない。

exact123の同公開earned H1で意味Red1/errors0→新12Green、直接upper関連15Green。firstsnapshotの元worker/source/end/adopt境界もpositive＋4negativeを確認した。別の通常画素componentはD2でPerception FULL3/通常UNKNOWN、D3で通常完全NEG9の有効証明を得た。D2 rawTARGETは実callbackでcandidate保持へ進む。宣言したcontrol全HHDDD経路と画素componentは別証明であり、sparse→raw Motion UNKNOWNをunit/静止へ置換せずtoken invalid/追加入力0を保つ。

独立最終review c43e96e7、author receipt5cbdf28c/closed2863b991でP0/P1/P2残0。root1新helper/latecaller、root4全追加spanとpeer root5 helperを保持した。元iPhoneの未来画像・全商品到達/速度の改善は未確認。


## root5の一回観測移送

暗い原188をNEGへ書き換えず、元の横一回観測を新current DATAへ所有移送する。Aは既にarmした未発行、Bは全既DATA guard後の未arm/正常old resultが既full_admitを満たす時だけ初回spent1として消費する。NULL callerはAだけで、generic mode2/prepared PAUSEはHELDを保持する。元P/hold/sync/current_used/共有DATA2を延長・返却せず、現normal UNKNOWN後の新source直接二零/newfitから一つの新IDだけをreserve/beginで再検査する。

A/Bはexact123でそれぞれ公的earned意味Red1/errors0を先に確認。新9＋直接旧7＋affected旧1の17Green、failure/error/skip0。元UNKNOWN ACKは再送・unit信用へ変えず、新IDの通常MOVEDだけで+1、その新sourceのnormal完全NEG→独立C→耐久PAUSE/RS→次levelを宣言したScene/clock componentで確認した。原実機の未来画像/速度/全商品到達の受入とは別である。

旧122の対象methodは新Aが意図的に変える経路なので、setupだけを非provenance prepared PAUSEへ移し、元全5assert AST・他全defsを保持してHELD/noMOVE/noDATA remintを確認。元187→188の通常零/remote変化だけではresult-DATAのhard bitは立たず、Bの原実経路を証明しない。原job1/source/private modeの未出力を補完しない。

C2fde2c4c・newfixture34a70efa・oldfixture067ad33eを凍結し、author b82d932f/ownedpatchd61ebcd0。root1/2/4の凍結済み部分とroot3 Ring/fixtureを保持。独立最終review a3b88b8f/closed9bb20a25でP0/P1/P2残0。


## 機能差分の統合・封印

機能5件＋clientの独立差分を統合確認し、P0/P1/P2残0（functional combined1f662ad8）。全Controller定数/他ngg2全files・Runtime/headers/Perception/Nav/Beat/Wire/Spool/15kernel資材/R12全40は出荷123と同bytes。fresh G1からG2を封印・適用し、37nativeのRPC/C/Ring3変更・34保持/追加0、全installed SHA一致を確認した（manifest ed2cd012、patch e5e5b674）。新52＋直接旧57の実施記録を確認し、旧072/076の既知baseline失敗は未合格/今回非選択として保持する。最終scope/selector・CODE/実CI/IPA・新実機は後続工程。


## 最終source scope

host137=新52＋直接旧57＋metadata6＋package8＋selector14、native109、実AST CORE閉包66、実CPython3.9選択108を明示固定した。non-doc変更16/新11、fixture74/import18/Py39 paths50を実sourceに結び、旧file/directory aliasを正しく分離した。selector14は実3.9.25でexact旧123の意味11assertion Red/errors0→新14Green、metadata6prefix/旧assert/helpers/過去reader originsを保持。独立finalscope review07ad3777でP0/P1/P2残0。fullhost137/実Py39108のローカル再走は行わず、これから同一CODEの実CIで一度実行する。実IPA/全source照合・固定公開・実機受入は未実施。


## 実CI・配布前の同一性確認

CODE20778950f39d8bc9134932952328331ae1b99c5a、CI276/run45860793228はsource-ready/host/focused-buildの実3job成功・15skip。host137と実CPython3.9.25の108はfailure/error/skip0、元artifact GHdigest/全bytes/CRCを照合。元IPAは18,520,248B/SHA `35fcfe28f500c929f37a01216395ffb3f21e5368e59a9e8c33b6329880fef3ea`。

read-only五項目はattempt1で全合格（verification SHA `f7698b0b2a2c5779a897e6a70f1f1b7a3bdc0c71ead85cbd6e72c7feaca3ebe4`）。CODE全1261Git blob/全bytes・37nativeの3変更34保持/追加0、実compiler/profile3、全9MachO、過去markerの正しい出典と新fixtureマーカー排除等を確認した。reader c34c49a5、scope d5e4ce29。新Mac Runtime0・旧Runtime/world/spool再走0、local reader classifier/compiler0。未実施を現行合格へ置換しない。公式docs-only SOURCE/固定公開/匿名全取得・iPhone受入は後続工程。


## 固定公開の最終確認

公式SOURCE `fbbaf4c1141d01289563e54ee1a6ffa49b3f32d5` はCODEから文書4件だけ、全1261Git blob/全bytes/CRC/同nativeを照合。source.zipは10,881,837B/SHA `921d1c4a10ccb88f1c9720b352b8c245faa010c43e5fbaf10a081ae8f331361e`。公開277/run45863674713の唯一の実行job publish-downloadが成功し、元build276を再ビルドせずrelease459690227/test124-build276へ保存した。

固定3assetの匿名全GET200を実施し、IPA/完全source/SHA表の原本全bytes/SHA/GitHub digest/size、両ZIP CRC、実tag SOURCEを確認（public receipt SHA `7d9ecc3abf1aae424585be4efc9e12164d70b5b0e8d208ee64ca74c22df5b3e8`）。IPAは18,520,248B/SHA `35fcfe28f500c929f37a01216395ffb3f21e5368e59a9e8c33b6329880fef3ea`、SHA表156B/SHA `1e79793303d49efae5f7c5d2826812acf44cc88dce51bd9f3f817025946ef261`。公開後の更新は文書だけとし、固定asset/実tagを置換しない。実機改善/毎拍・速度/元再発数の受入はTEST124返却待ち。
