# TEST124: 未発行の一回観測をcurrent DATAへ移す

2026-11-27（日本時間）。[native契約](../contracts/native-control.md)・GOODS-01/02。TEST123/root5の原188は正常OK/UNKNOWN/incompleteを元D前67.564167msで完了・67.383333ms前に採用した。右cap461/625画素が黒くupper/full FLOOR不成立なので、この原画像をNEGにする期待は置かない。

原ACK16のbefore180はgoods0、observed187が初FULLだが通常MotionはUNKNOWN。180→188もUNKNOWN、187→188は通常strict BLOCKED/dxdy0。商品後に実観測MOVEはないが、`full_spent`はMOVE送信前のarmで1になるため未使用flag0とは言えない。原job1 packet・full/current private flags・DATA履歴は未出力であり、下記A/Bのどちらを実際に通ったかは未確定とする。

## 原因と二つの限定入口

既`cycle_full_admit`は同じ水平一回観測をspent1/framing1としてarmする。新しいcurrent DATAに置換すると、`current_data_start`はframing/sourceを消しspent1を保持し、新mode2 UNKNOWNは常にHELDとなる。Aだけでなく、正常old resultのcallbackが返る前に新画像が来る場合は、`cycle_assess`が`full_admit`より先に`current_data_start(result)`を呼ぶため、元権利がまだarmされないBもある。

Aは、変更しない`cycle_current_data_start`の全guardを通り、既`cycle_current_data_unissued==1`であった水平LEFT/RIGHT一回観測だけを移す。NULL-result callerはAだけとする。spent1はそのまま保持し、予約/開始/NOT_SENT/UNKNOWNまで進んだ権利は移さない。

Bは同じ全DATA guard後、bind前の元contextでnonNULLの正常OK/UNKNOWN/incomplete・safe resultに対し、既`cycle_full_admit==1`かつLEFT/RIGHT/reason5/unit/FLOORである場合だけ、**その同じ既権利を初めてspent1として消費してから**移す。UP・generic mode2・単なる最新画像からは作らない。spent/framing0、actual input_state0、pause_attempted0、current_used/active0を必要とし、prepared PAUSEを取り消してBを作らない。`retry_only/retry_data/retry_waiting`、full_data_active、entry/lower/upper/current、initial/restart-yield veto等、通常callbackで旧full_admit前に早期returnする状態を除外する。Bが不成立でも既DATA-only分類は阻害しない。

原187のScene/通常packetと実events15/16を使い、「未arm/非pending/非pause等」の宣言した条件付きconst診断では、既full_history/local/full_admitが各1、choiceはLEFT/reason5/FLOORとなった。これは未出力private flagsの再現でも実B使用証明でもない。特に原187→188のstrict零＋遠方材質変化は既retry relationも成立し、その二画像だけではresult-DATAのhard-blocked bitを満たさない。公開Bはold→new signatureの通常UNKNOWNを実際にearnedし、既DATA pairとhard-blocked guardを保って確認する別componentであり、原Bの再現とはしない。

## 私的な所有記録と一回だけの消費

`NG2Controller.c`だけにprivate `NG2TransferredView124`を追加する。public POD/ABI・Ring/helper/negative validator・Runtime・wire/checkpoint・予算定数は変えない。記録はNONE/DATA_PENDING/READY/RESERVED_CONSUMEDの有限stage、owner started_ns/level、old job/capture/start/prefix、水平choice全5field、old ordinal・元P/hold/sync、元inputs/moves/restarts等と、新current job/capture/start/end/prefixを保持する。wireから復元しない。

元contextでA/Bを一度だけ確認しlocal recordへ保存してから、変更しない`cycle_current_bind`で新DATAをbindする。同bindのcurrent_used1・共有retry_used加算1/上限2を維持し、元hold/P/sync/session/walk上限をminで保持する。Aのspent1は維持、Bは初回0→1だけで、spentを0へ戻さない。

通常candidate/target・late positiveを先行保持し記録を失効させる。新currentのnormal OK/UNKNOWN/incompleteで、同source/job/owner/level/prefix・元D/P・finite safe result・zero positive/word hintを確認し、現sourceのfull local、origin/nextの無保護FLOOR、exact ITEM/halo、全row/slot/ITEM potential ROIの一歩後保存が成立した場合だけREADYへ移す。これで旧モデル・旧ticketを復活させず、旧sampleだけ保持してclear_slots/clear_modelし、releaseを実採用時刻へ置く。正常NEGは既独立C・耐久保存・PAUSE/RSへ進め、この記録で陰性にしない。

READY専用で二つの新しいstable/non-inflight画像A/Bを要求する。双方とも新immutable current sourceから直接、元方向の通常ng2_motionでBLOCKED/dxdy0を証明し、全tiles/protected・FULL/gold・全ITEM/halo・歩行床を保持する。A→Bだけの零は不可。id/start/end順・新prefix/owner/level・release以後・元P/freshnessを守り、不支持材質/Motion/UNKNOWN/TWEENで永久失効する。

既mode2 relationはDATA pairだけ、既full_staticのcurrent branchはUP専用なので、そこを汎用変更しない。新provenanceだけのstrict relation/static分岐を設け、既current observerの二枚proof、new add_sample/fit、model_capture>=B、未来拍・publication・通常reserve/begin guardへ結ぶ。成功reserveで一つの新command ID/ordinalを記録してCONSUMEDとし、同じIDのbegin再検査用の所有は保持する。失敗・NOT_SENT・UNKNOWN後にREADYへ戻したり二つ目のIDを作ったりしない。旧ACK16はUNKNOWN・変位0のまま、同入力を再送せず、新unitだけを通常Motionで信用する。

level/reset・取消/terminal・候補・storage/pause/restart・identity/P違反・別sourceへのlatchで記録を消す。pending workerはcandidate優先で必ず返す。一回失効したrecordはcurrent_used/spentのsticky制約で作り直せない。

## Red、検証、所有範囲

製品GO前にexact出荷123でAの公開earned入口1testを正式実行し、全前提が成立してnormal UNKNOWN後のOBSERVE_MORE3期待だけHELD7となる意味Red1/errors0/skip0を保存した。private flag注入はなく、既halo122 helperはread-only suffixでarm/counterを読むだけである。Bもold worker未完了→新DATA画像→old normal callback前の既full_admit正資格をpublic earnedし、Aと分けてRedに結ぶ。

新2direct proof/new fit/first future ID→実public ACKと通常unit→新画像のnormal producer完全NEG→独立C→durable/PAUSE/RSをcomponentとして確認する。時計・Scene/未来画像は宣言したモデルであり、元実機の未来再現・iPhone速度とはしない。原188はUNKNOWN保持、原187と188のpacketを流用・同一化しない。

無provenance mode2、NULL-B、予約済/開始済/UNKNOWN/NOT_SENT、候補/強word/latepositive、owner/job/source/prefix/level、P前/等号/後・取消、retry上限2/current_used、直接source→A/BのMotion、ITEM/halo/local/ROI、reserve/begin後の二つ目入力、旧ACKのbytes/変位0、generic UP/旧full成功を必要境界として選ぶ。旧halo122の「UNKNOWNはHELD」methodはAが意図変更対象なので、setupだけを非provenance mode2へ移し、従来HELD/noMOVE/noDATA remint/counter assertを維持する。assert削除・skipで通さない。

root2所有のupper_*とroot1/refined-data helperは変えない。新private type/field/resetの一行とcurrent DATA/start/assess/relation、full_static、reserve/beginの必要な専用dispatchだけを局所編集し、C全fileを旧snapshotで上書きしない。root3 Ring/testの凍結b42c/1813を保持する。通常修正の独立差分レビュー1回・変更部/直接関連を選び、無関係全world/全Runtimeを再走しない。nativeの実IPA/全source同一性と次iPhone受入はroot工程とする。

## 実施・限定検証

Aはexact出荷123のpublic earned入口で意味Red1/errors0、Bも別に同出荷sourceで意味Red1/errors0を保存した。Bの初期remote材質だけの準備はretry relationが成立してhard bit1をearnedできず、Redへ数えていない。二ACK historyと独立の新signatureで通常old-comparison UNKNOWN/hard bit1を実際にearnedし、既DATA guardを通した正式B Red後にB captureを追加した。A/shared実装を先にGreen1、B追加後に入口Green2とし、後から追加したguard確認を事前Red済みとは呼ばない。

最終公開9methodはfailure/error/skip0。A/Bそれぞれnormal UNKNOWN→新anchorから直接二枚零→新fit→最初の未来LEFT新ID/ordinal→通常ACK/MOVED1→移動後source自身の通常完全NEG→独立C採用→PAUSE/durable/intent RS→次levelを確認した。移動後の商品座標はA left304/sy159、B left340/sy87で、各sourceの3ITEMから求めた。未来画像とclockは宣言したcomponentであり、原188や実iPhone未来へ代用していない。候補/word優先、prepared-PAUSEの非provenance mode2 HELD、相互零だけの拒否、ITEM/halo/local・P/取消・一用/開始前再検査も同9で確認した。

旧halo122 affected methodはprepared PAUSE→DATAの非provenance fixtureと、そのSceneに対応するnormal producerへsetupだけを変更し、出荷時の全5assert ASTを保持・単独Greenとした。直接関連の既negative/positive・予約/開始済み・DATA-only UNKNOWN/NEG・旧UP通し・旧未送信一用の7methodもGreen。無関係な全world/全Runtimeを追加実行していない。root1/root4とroot2所有helperのbytes、閉鎖済root3 Ring/helper/test、POD/ABI・kernel・negative判定は保持する。実iPhoneでのcap追加観測・候補保持/通知・実周回と速度は次の実機まで未確認。
