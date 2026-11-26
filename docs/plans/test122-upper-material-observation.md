# TEST122: V2上部入口の静止観測と歩行外の材質差

2026-11-26（日本時間）。基準HEAD `d78159a`、製品CODE `4574786`、C `554b6ae4`/Nav `ebba4541`。[要件](../requirements/necrogold.md)・[native契約](../contracts/native-control.md)・[修正表](../fix-records.md)・[開発フロー](../development-flow.md)に従う。rootは原因解析後の本短計画作成だけを承認した。**製品・正式試験・CIの変更/実行は別のroot GOまで0。**

## 原因と証明範囲

実順3の `ca23ef00` はLEFT28/source332が既知ACKし、原339の通常 `DOOR_OPENED` で開扉1・移動5を確認した。開扉後のMOVEは0。原340/job2は正常OK/UNKNOWN/incomplete・partial-safe1（partial1/row0）として期限内採用済みであり、商品が未観測なのは正しい。結果採用時刻に結ぶrelease `24057935189875` はworker100msのD `24058029004083` より93.814208ms前である。末尾のstatus deadlineはその後のcycle failureによる書換えで、producerの未採用を意味しない。

原339/340と保存402〜407は通常Perceptionで5ITEM@row4、V2の形を満たす。原339→340、原340→402〜407の通常Motionは直接strict BLOCKED零。後者の4材質差は `(8,-2)` UNKNOWN→FLOOR、`(-4,1)/(-3,1)` FLOOR→DIRT、`(-2,1)` DIRT→FLOORで、ITEM/保護mask/全GOLD/現在のoriginと次LEFT床は不変である。宣言した最小V2 contextのconst cutでは `upper_world/upper_floor/upper_identity=1` のまま、`upper_static_footprint` の全230tiles一致だけが0となりvalidation9を返す。旧119/120/121はScene全bytes・対象7helper body・同input結果が同じで、FR118 V2/slot/cacheの削除回帰ではなく静止材質の適用範囲外である。普通PARTIALのFR119 paletteとTEST120 begin cacheはupper専用経路を扱わない。

実stopのP `24061010251921` はreport continuation `24060489991812`＋実period `520260109` にexact一致する。`live_stop_detail` の実sourceはupper.active時にupper.parentを選び、記録stageはcycle_observe（upper stage2〜4ではない）、最後まで開扉後MOVE0である。保存407のcapture endはPより27.380296ms前、analysis endは0.639838ms前だが、実commitはP+135079nsであり、最終の実時計拒否は正しい。待機を期限内に進められなかった原因と最後の打切りを分け、Pを延ばさない。

Git外根拠: `test122-movement/upper-guard/result.json` SHA `0acb0d7ebf1e678870890d9bd07d3622faf8dc52d01ea827af508a2636d60f7b`、`ca23-timing-cause.json` SHA `3d390ddc8ffb466bc1952d9997d075c747fd0635cb3ee5dfdc9bae1d4fcc6064`、全受領は `test122-intake/RECEIPT.md`。job1 packet・341〜401・private rebound/stage/modelの履歴は未出力で、339→340の全callerを再現したとは扱わない。

## 最小変更案

既完全一致を先に保持し、V2の同じimmutable分類anchorから現在Sceneへの**静止観測用の材質関係だけ**を別helperで追加する。新DATA/bind/worker/route/slotを作らず、rebound枠・元job/anchor/upper.world・parent/allocated parent/period・counterを変えない。旧V1、既FULL bridge、実unit後の通常bind・postunit slot、通常UNKNOWNの待機は保持する。

資格は初回H1前（upper.inputs/horizontal/downが全0）のV2に限り、既upper identity/world/floorと同goods、正確な同ITEM座標/同保護mask・保護上の全tile・旧GOLD/DOOR/ITEMを保つV2だけ。差は歩行外のUNKNOWN/FLOOR/DIRT/STONE相互だけとし、新GOLD/DOOR/ITEMや保護の増減は許可しない。origin/現在のnextは両Sceneで非保護の正FLOOR、双方の実stepping cross（中心と4近傍）は全tile不変とする。後のDOWN候補が新FLOORになっても、将来の移動資格には使わず、その段階の独立current/通常world/floorを再度要求する。原 `(-2,1)` は最初LEFTのnextの対角で、現在の実stepping crossには含まれない。

この形を満たしても、固定anchor→独立currentの通常strict BLOCKED零を既 `upper_normal_zero` で実行し、UNKNOWN/非zeroは通さない。静止factは既cacheの全Scene/metadata/job/owner一致へ通常どおり保存し、beginのcheap guard・元票・新currentでの撤回を維持する。素材ラベルだけでMotionを合成せず、入力/開扉/移動creditを増やさない。

## 正式Redと関連確認の案

予定は新 `tests/test_native_upper_material122.py`。公開C lifecycleで正常fit→実unit→同方向開扉ACK→V2 PARTIALの正常safe UNKNOWN採用をearnedし、独立currentで今回の具体的4材質差を与える。私的upper field/slot/modelを注入せず、callerの資格は公開status/event/commandに結ぶ。旧121で次の正資格（静止proof→通常fit→未来H1票）へ進めないassertion Redを先に保存し、元P/全counter/job/sourceを保持したGreenを要求する。手続き画像/時刻は宣言したcomponentモデルであり、未出力339→340履歴の再生ではない。

左右で初回H1前の材質差が同jobの静止資格となった後、H/H/D/D/Dの各新sourceを従来の完全一致で確認し、通常unit以外は加算しない。H1後の材質差は新資格へ渡さず、旧bridge/snapshot経路を保持する。step cross/次床/ITEM/保護/旧GOLD/DOORの変化、別goods/variant1、direct UNKNOWN/非zero、prefix/owner/job/anchorの変化、元Pの前/等号/後、capture/analysis<Pかつactualcommit>Pを拒否側に置く。既snapshotのbridge rearm拒否、beginのexact fact/fallback、V1、postunit/last-slot、PARTIAL beginの直接関連methodを選ぶ。全world/無関係なRuntime故障群は既定にしない。

Controllerの所有はupper静止predicate近傍だけ。goods担当のC陰性witness/currentData担当hunkを上書きしない。root GO→正式Red→最小Green/関連→独立差分レビュー後、nativeの実IPA/compiler/seal/完全source確認はroot工程。次のiPhoneでは通常1-1ポーズから初回RS→候補→開扉→上部入口の壁沿い観測→全商品判定→実RS/次周回を確認する。未収録の後続商品画像・実機到達/毎拍/速度は未確認である。

正式Green後の直接関連で、初案が既postunit snapshotの独立DATA bridgeを静止扱いにする退行を検出した。初報ではSTONE→DIRTと説明したが、このfixtureはH1実unit後なので元STONEは隣へ投影され、実際の変更点はUNKNOWN→DIRTだった。STONE不変だけでは解決せず、根拠のない材質制限は採らない。今回実ca23の開扉後MOVE0に合わせ、新資格をupper.inputs/horizontal/down全0の初回H1前へ限定する。旧postunit/snapshot/rebound assertは全て維持する。upper.inputsは全元guardを通った真beginでだけ増加し（ACKやMOVEDのcreditではない）、horizontal/downは同routeの通常実unitをupper_observeが確認したときだけ増加するというsourceと原イベントの開扉後MOVE0へ結ぶ。これらのprivate counterがdumpされたと扱わない。元失敗log・説明訂正・phase限定後の結果をreceiptに保持する。
