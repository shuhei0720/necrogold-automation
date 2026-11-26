# TEST122: FULL商品の保護halo露出から現在DATAを再判定する

2026-11-26（日本時間）。基準HEAD `d78159a`、CODE `4574786`、C `554b6ae4`。[native契約](../contracts/native-control.md)・[要件](../requirements/necrogold.md)・[修正表](../fix-records.md)・[開発フロー](../development-flow.md)に従う。rootが承認したのは本短計画作成まで。**製品・正式試験・CIは別のroot GOまで0。**

## 原因と現在の正の証拠

実順4の `7a9def6a` はLEFT19が既知ACK/通常DOOR_OPENED、原234/job1は正常OK/UNKNOWN/incompleteを元D内に採用した。原234の左cap黒67/625（可視89.28%）が元90%を満たさず、234を陰性にしてはならない。商品が見えている原235/236は出荷121と旧120の正常Ringで完全NEG/policy7/layout1、Ring数値証明とown-anchorの独立Cwitnessが各1、packet全6112bytes同一である。今回Ring閾値の変更は不要。

原234→236は通常direct strict BLOCKED零で、同3ITEM/同保護mask/全旧GOLD/現在の正床を保持する。しかしprotected `(-3,-1)` のUNKNOWN→DIRT、遠方 `(-6,-2)` UNKNOWN→FLOORと `(6,4)` FLOOR→DIRTで旧framingのvalidation9となり、`cycle_observe` は元Pより約2.55秒前の `24215017947333` にSCREEN停止した。原235はprotected差と後者遠方差の2セルだけで同じ通常零。旧 `cycle_current_data_scene` は234/235/236すべて1だが、`cycle_current_data_pair` は保護tile変更の一律拒否により0となる。これは商品/haloを失った意味ではなく、同じ潜在保護に現れた非歩行DIRTを旧証明が扱わないことを示す。

234 capture start `24214885409791`、job1 worker `24214944503750`、正常UNKNOWN結果end `24214980655791`、採用release `24214981273166`、元D `24215035409791`。235はrelease前に取得/解析済みで、236はrelease後start `24214985807000`、end `24214997108833`、analysis end `24215017909250`、stable prefix19・非inflight。元Pは `24217572899791`。新DATAはその時点の独立current236を第一の受入例とし、235の正常NEGは別の取得済み証拠として保持する。235を実際に新workerで採用したという履歴は補わない。

Git外根拠はgoods担当の `test122-goods/normal-results.json` と各正常packet、C側 `test122-movement/full-halo/result.json`（const data geometry/direct Motion、private mode/counterの完全再生ではない）。元job1のnormal UNKNOWN採用と、後のcycle failureによるstatus kernel書換えを混同しない。

## 限定したDATA-only admission

旧 `cycle_current_data_pair` の拒否は保持する。そこが保護tileで拒否した場合だけ、現在FULL専用の別qualificationを `cycle_current_data_start` の入口へ追加する案とする。両Sceneの `cycle_current_data_scene=1`、同3ITEM座標・正確な同保護mask・全旧GOLD/DOOR/ITEM・origin/歩行十字を保持し、今回と同じ**ITEMの直接cardinal haloで現在の歩行十字外にある1セルだけのUNKNOWN→DIRT**を許す。新FLOOR、ITEM消失/追加、保護増減、任意の保護材質変更へ広げない。他の非保護差は既data pairの有限material domainに限定し、固定旧anchor→現在の正常direct strict零も要求する。新helperはold MOVE/framingの正資格やNEGを救わず、immutableな新mode2 DATAだけへ渡す。

callerは既drain対応 `restart_yield.enabled` を必要とする。元job/level/prefix・owner・現Scene/seenの完全metadata一致、新ID/start、元P/source150ms、正常UNKNOWN/incomplete採用済・full_seen1/partial0・pending0・候補なしを保つ。新currentData未使用/非実行・共有DATA counter<2、一度だけのcurrent置換、pause ACK/durable/intentなし、finish/terminal/storage/restart不明/別upper-entry-lower routeなしが必要。入力は0、または旧jobが所有するexact未begin/未complete/未outcomeのPAUSE1件だけを撤回できる。begin/ACK/UNKNOWNの入力は再解釈しない。

旧framing未発行のsource/history（`cycle_full_spent`/framing1/full_source ID/start/prefix/Scene/parent）または既retry状態の同level/prefix/元parentを、既 `cycle_current_data_unissued` 等で確認する。未知のprivate flagを実記録へ補わず、正式caller試験でこの公開earned経路を作る。原19はDOOR_OPENEDであり、実unit後entered tokenを捏造して資格に使わない。

bindは既 `cycle_current_bind(...,2)` を使う。旧票/framingを退役し、source236に新jobを発行して共有DATA counterを1消費、current一回を消費し、元hold/parent/sync/ordinalを引き継ぎ、旧slot/model/入力資格を消す。元234の結果を再ラベルしない。Runtimeの旧worker callback/drain token実return後だけ新workerをdispatchし、新job固有のsource150/worker100/Dを通常計算する。235/236で得られた正常NEGも、その新jobでproducerを実行して独立Cwitness・durable・通常PAUSE/実ACKを経るまでRS資格にしない。新結果UNKNOWNはHELD、候補は保持し、MOVE/UP/再送は0。

## 正式Red・関連確認・所有

予定は新 `tests/test_native_full_halo_data122.py`。公開C lifecycleで実MOVED→開扉既知ACK→FULL3ITEMの正常safe UNKNOWN→未発行framing→今回のhalo露出を観測する。旧121で新DATA未発行/SCREENになる意味Redを保存し、新mode2 immutable source/job・DATA2一回・元P/hold/位置/counterを確認する。current source236の通常producer→独立C正常NEG→保存→通常RS/次floorまでを宣言した公開モデルで確認し、原未知未来の実機再生とは扱わない。Ringの既cap拒否/原234 UNKNOWNを保持する。

複数保護差、DIRT→UNKNOWN/STONE等の逆/別材質、別halo/ITEM/保護/旧GOLD喪失、歩行近傍、direct UNKNOWN/非zero、currentData二度目/DATA枯渇、pending/候補、prefix/owner/level/source不一致、PAUSE開始済/ACK/UNKNOWN、P/150/100の前・等号・後とcommitだけ越境を拒否する。新jobUNKNOWNの保持、候補先、旧worker実return fenceとUI前drainは既契約を維持する。

Controllerの変更候補はcurrentData admissionの専用helperと局所call-siteだけ。upper担当も同じ所有者、de9の陰性witnessを担当するgoods担当とは関数hunkで協調しwholefile overwriteしない。旧currentFull/mode2、entered、framing、PARTIALの直接関連methodを選び、境界の実変更に応じた最小Runtime callback確認をrootが選ぶ。全world/無関係故障群を増やさない。正式Red→最小Green/関連→独立差分レビューの後、nativeビルド/封印/完全source/配布とiPhoneの全商品判定→実RS→次周回を確認する。実機改善/毎拍/速度は未確認である。
