# TEST078: TEST077受領と閉金扉前の移動確認

2026-11-11（日本時間）。baseline `63ca426770349bab73953241982a171d76ca35e6`、[計画](../plans/test078-closed-gate-motion.md)。raw/Scene/解析はGit外received077/test078-*。通常局所修正、独立レビュー1名。

## 実受領の確認

2ZIP/38選択PNG（18/20）を全SHA/ZIP・PNG chunk CRC/PIL verify-load/896×414/manifest全offset・hash・cursor/prefix/strict API16 schema/_load/実test069 certificate・inventory・archiveへ照合。両PAUSE/resolved/terminal/drained、取得failure/timeout0、全host RPCエラー・取消0/status33回最大1.407秒。保持・省略を補わない。

| 実順/run | ZIP bytes / SHA256 | restart | MOVED/入力 | 開扉 | 終了 |
| --- | --- | --- | --- | --- | --- |
| 1/92742894 | 4,386,853 / `82805b14fe2a563ad472a80ad421dff3cd85f7b93ef5dce9ee6d2b92aa5514ac` | 7 | 5/7 | 1 | goods |
| 2/587d35cc | 4,193,956 / `554714887dfcf316f7cbdf9495115b1401327d6f35f2a5c5cdde1bb4e9744620` | 7 | 6/7 | 0 | movement |

両retained20、export18/20・画像計4,076,945/3,874,696Bで4MiB以内。2のreport capturesはring256行/49..428で選択初期PNG1の対応行だけ非保持。image manifest自己metadata/hash/cursorと実publicationは有効、行との照合は未確認として補完しない。server.buildは文字列時刻2026-11-11 08:09でbundle build124とは型の異なる値。

rootが1の原372で3商品と価格75/125/65を視認。全商品到達1/2、対象アイテムの有無までは認定しない。最後の送信MOVEは商品優先でUNKNOWNのまま保持しており、ACK/商品をMOVEDへ数えない。7入力間隔は.510456〜.532193秒で通常拍付近、ゲーム側受付時刻や恒久的毎拍を証明するものではない。

## 失敗の正確な位置

2の最後cmd24はsource395/UP・begin/ACK済み。元source394の未送信cmd23をSCREENへ確定し、同拍別ID24/ordinal7へ再予約済み。NB95681394919335/D95681404919335、実beginはNB+5.355ms/D−4.645ms。405..419はstable/current-prefix24の15capture、8回の間隔付きUNKNOWN評価と整合する。最終419はACK後575.226ms、C終了時visualD残約1.953秒、期限切れではない。

原395のDOOR(0,-2)/GOLD(-1,-2),(1,-2)が419のDOOR(0,-1)/GOLD(-1,-1),(1,-1)へ対応し、実UP1歩で扉直下へ到達。実扉は閉じたまま、次NavはUP/reason5/DOOR。元sourceの次手はUP/reason7/FLOOR。raw最良は(0,+9)/.5670244288/gap .3825624042、closed/unique_gate_translation1なのに全旧補助はUNKNOWN。

別cmd21 too_lateのgateはD+6.348304msで、最後のMOVEMENTとは異なる。最後のreference不適格は元scheduleDを358.696ms超えた419で必然。中間405/407/409時点の資格・fallback評価は上書きにより断定せず、送信前から失格していたと推定しない。未保持未来応答やprivate全状態の再構成は行わない。

## 設計確認

旧gate_detailのfuture-next FLOOR条件だけを外す案は不十分。median506/bad13/領域[4,0,502]、detail318/bad1/[4,0,314]で独立2領域100未達。旧5依存gradient319/bad5/65帯[254,65]、worldblur137も不足。旧支持条件を削らず不採用とした。

camera中央52の5依存案は、全依存UI/mask除外後に250/bad4・帯115/135となる。初期の310にはUI跨ぎ38・ROI境界22が含まれており、必要300未達として不採用。全5依存を安全に保つ案の成立とは記さない。

新案は各frameで固定H→Vの最初の有効軸を選ぶ3依存feature面。中心と使用軸±1だけを読み、全実依存のmask/UI/known/nonDOOR/nonITEM/protect/contrast6を確認する。選択はframeごと一度、candidateやpairごとに変更せず、同axis/3材質pattern/signを1pixel1支持で全73に比較する。旧max-axis5依存面/65loop/既knownは不変。camera52/両frame51,52除外/原支持300・95%・帯100・元15pp規則を保持する。

この固定単一仕様の395→419は322/bad5/帯150・172、394→419は320/bad5/150・170、O0/strictO2同値。72競合はすべて支持300未満で候補外、十分支持競合に対する15pp境界は手続negativeで確認する。値・mask・帯・優先順を結果へ合わせて探索しない。

独立担当は改訂計画/製品静的差分にP0/P1なしでGO。旧077実public ng2_motionの手続unitを4方向/O0・strictO2でMOVED期待→全UNKNOWNとするunittest 1method/8 subfail/error0を実測した。先行単profileの4失敗/exit1と区別して重複算入しない。新helper欠如やstub0の失敗はこのRedへ数えない。新8methods初回は7Green、rawgap境界の実double入力だけで2subfail。製品epsilonを変えず、隣接c1の実差low<.08/high>=.08をassertするfixtureへ補正し、軸のpixel比較追加と合わせ変更2methodsだけGreen再確認。他6methods初回Greenを継承し、CIで8全methodを1回実行する。最終差分・限定CI/実IPAは完成後に追記する。新unitはUNKNOWN-only・両CANDIDATE/GOODS_UNKNOWN・全protect/ITEM0・旧実next/latestorigin床・閉扉2ahead→adjacent/同法線・全旧金exact/unique9・raw73/unit/highintensity/gapと新面の全支持規則を保持する。新MOVEDは閉扉への到達だけで開通/入口creditを作らず、次Navの開扉へ進める。

実保持ACK比較18pair（同じcommandの複数画像を含む）を同source/profileの公開ng2_motionで前後照合。旧known15は全不変、旧UNKNOWN2も不変、今回395→419の1pairだけUNKNOWN→UPのunit MOVEDとなった。新strictO2の分類比較であり、欠落future proofやControllerのprivate全状態/live admission・実機到達の代用ではない。

## ローカルfreeze

製品Nav SHA `0da8483d7663ee4ae144ad6da35602e06b82b15ab49ca3eea5d16c2d791bec61`、新単体 SHA `ba46b496ec474441526ddf59c09d4771544478ccc171db8974ee509aaa822e50`。新helperと末尾1callを除くと旧Nav全文bytesへ完全一致。fresh G1→seal/applyで22中Nav1/他21不変、全header/Controller/Runtime/Perception/JSON/API16cap14v15/ABI/元閾値/予算/G1/R12原40を維持。

限定CIは新8＋関連14（原Nav4/074補助3/075static2/075cache・known1/Controller3/ABI1）とselector3で25件。元primary/開扉・金なしunit・静止/全73cache parity・商品/不明入力無再送を変更範囲から選ぶ。実sealed COREのcanonical/bare依存/5client HEAD・4実callable、無変更旧4clientをbaseline同bytesへ固定。063/071/072/074/075/076/077/078 baseline envとBASELINE_NAVは空値も拒否。意味単体を重複ローカル実行せず、全Runtime/worldを積み増さない。

独立1名が改訂計画/製品/新単体の最終差分と既実行ログ、runner/契約を確認し残P0/P1/P2なし。レビュワーによる試験再実行はなし。全sealed CI、新IPA/公開assetの実物確認、端末での次の開扉・全商品到達/速度は未実施として分離する。
