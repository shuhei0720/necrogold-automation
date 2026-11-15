# TEST101: 観測の継続と移動確認

2026-11-15（日本時間）。基準b731edfa（製品はTEST100/build187）。[要件](../requirements/necrogold.md)・[native契約](../contracts/native-control.md)・[修正表](../fix-records.md)。実装前の計画。実機改善未確認。

## 1. 受領と原因

6添付は3run＋同じ全runを含むcampaign。73PNG/81record/160原本のCRC/SHA/連鎖/登録画像/RGBAを照合。実順144d→70d5→06f9。取消表示や回収完了をゲーム成功としない。必要5枚だけ現Perceptionを各1回校正し、Sceneを私的cacheへ凍結。再解析しない。

実1は3歩後、ACK29の528→553をUNKNOWN8回で停止。dispatchは10ms窓内、visual期限も約2秒残る。0金→1金が初めて見える単位移動で、旧first-goldのraw次点が片phase帯で135画素しかなく300未満、finite guardで拒否。他の一意terrain/全73raw/両phase/world証明は成立。途中の2〜3拍間隔は未送信SCREEN22/24/26/27と再同期に対応するが、source436/462/488/502が欠け、個別のquiet拒否predicateは未確定。この移動確認修正で全空拍が直るとは書かない。

実2は部分判定6.536msを正常採用し、継続credit後の546→549でROUTE拒否。上端y=-5の代替ITEM投影7セルが縮退し、下段y=-4のITEMと両3×3は不変。同UP/reason5/FLOOR・実開扉ACK・strict BLOCKEDが成立。旧未送信入口には上端投影の対策があるがcycle credit側へ未接続。新商品露出用の100再bindとは別条件。

実3は判定14.576ms/約0.963ms後採用、flags258=BOARD|ROWSのUNKNOWN。3商品は見えるが右capは467/625画素が黒い実遮蔽。旧policy3/4と違う、商品列より2セル下の側面開口。capをFLOORに変えず追加接近する。直前ACK17はvisual UNKNOWNのままFULLで閉じた。旧17の移動creditを復活させない。

3事象で100の過去成功を破壊した証拠は未確認。ただし回帰なしの保証ではない。継続許可の後の画像再検査まで試験する不足を埋める。

## 2. 設計と所有範囲

A（Controller）: 上端の重複投影の縮退だけを別関係にする。UP・実開扉後、連続した上端ITEMに対応する保護済み下段ITEMを全保存。変更は上端ITEM→UNKNOWN/FLOOR/DIRT/ITEMと、下段の投影で説明できる外端保護だけ。下段の実商品/保護・旧GOLD・両3×3・完全Decisionを保持し、独立strict零・元prefix/絶対期限を要求。一般ITEM消失や097空framingへ広げない。OBSERVE_MORE→credit→後続画像→将来票まで公開Cで確認する。

B（Navigation）: 旧motion全段は維持し、未解決のfirst-goldに別supported-phase証明を追加。安全床・商品/保護なし・元金0→1/元UNKNOWN・旧全STONE＋非共線DIRTの一意単位移動、全73raw有限/元margin、world95%/support300/両region100/全73の元競合差を維持。両phaseのwinnerとzeroは有限、有限競合すべてに元.08差、4単位方向は各々少なくとも片帯で有限。少なくとも片帯でraw次点が未支持の場合だけ。INFを正の差に数えず、閾値・入力時刻を緩めない。

C（Controller）: FULL UNKNOWNでも安全な追加観測を一度だけ許す別private mode。元immutable FULL/partial=false/outcomeUNKNOWN、正常な同jobの結果で全観測slotの保守上界<.8・強い対象語なし・候補なしが前提。直前の同軸実開扉と既知ACK/FULL visual-closeを区別し、旧ACK17をMOVEDへ変えない。新しい独立static画像・同prefix・原点の上下GOLD bracket・店内側の観測FLOOR/保護なしを確認して、別ID/将来ordinalの局所観測MOVEを1回だけ発行する。一般経路の絶対位置/visitsの復元には使わない。

元の全potential商品領域（row/partialのicon/name検索とITEM量子化包絡）が、移動後もviewport/HUD外に残ることを要求。217の包絡は[169,485)×[49,196)、LEFT後[205,521)×[49,196)。旧結果の陰性creditを使わず、ACKだけで再分類しない。独立strict MOVEDで新しい最新画像を通常workerの新jobへ。新sourceがPARTIALなら事実どおり分類するが、未局在の絶対位置を使う旧経路移動へ移さず保持する。候補/不明/UNKNOWN入力は保持、視覚UNKNOWN/TWEENは既有限待ち後に停止し再送しない。同level内の新job/時刻/MOVEDで一度限りを復活させない。途中UNKNOWNを商店完了へ数えず最終結果で1回だけ数える。元horizon/入力16/walk45/session180/取消は保持。

D（Ring＋Controller独立再検証）: 別policy5/board5。3ITEM・両FLOOR capに加え、片側縦5GOLD(ay-1..ay+3)、下壁7GOLD(ax-2..ax+4,ay+3)、開口上GOLD(gate,ay+1)、開口FLOOR/DOOR(gate,ay+2)。重複を除いて12正位置、左右mirror。数だけで許可せず、全raw endcap・2看板・3価格・全商品帯の対象全探索/強語/余剰拒否を旧3と同じ条件で要求。旧1〜4と優先順・4専用価格条件は維持。元217はcap UNKNOWNなので必ずUNKNOWNのまま。

E（Runtime診断）: cycle限定で、既retainInitialRejectionLockedが全identityを確認済みの原sourceも1枚保持する。既observed1枚だけの旧profileは維持し、追加sourceも同じ現在のcoherent pairに追従する（最初の一件に固定はしない）。追加sourceは全旧priorityの後へ置き、既24pin/44spoolとschemaを維持。通常の非優先pinの退役順は維持し、後から旧critical/restart/dispatch sourceが来る満杯時に通常の退役対象がなければ、両pin経路で任意追加sourceだけをfallback退役できるようにする。priority順だけでは全pinが保護され新しい旧criticalを拒否するため、この競合も試験する。旧priorityは保護し、以前から退役可能な非優先pinへ新しい保存保証を付けない。容量が埋まる場合は既missing reference診断を保持し、常時保存の保証にしない。採証は入力/待機/回復の権限0。

製品担当をController、Navigation、Ring、Runtimeで分け、同じtest名を使わない。Header/旧ABI/Bank/Coverage/canonical15/ELF/G1/R12/通信・回収・入力予算は変更しない。

## 3. 期待値と拒否

Aは実開扉→部分判定→独立静止credit→上端縮退→将来入力の一連をRedにする。下段商品/保護喪失・別材質・非UP・近傍差・prefix/期限/取消・UNKNOWN移動は拒否。旧100の増加時再分類と旧097空framingを保持。

Bは手続き的格子/signatureで、実際に観測したLEFTの整合した公開motion正例を確認する。4方向のcomputed-plane境界と旧083の公開4方向は別に検証し、新しい公開4方向E2Eと呼ばない。zero/4単位の支持欠落、非有限raw、誤方向/非単位、新金元地点既知・複数金、anchor欠落、phase/world競合を拒否。

CはUNKNOWN→後続独立static→新票→ACKだけなら0credit→実MOVED→新source/job→候補保持を検証する。元17の再送/移動credit0、同店count1・一度限り・元期限・ROI/HUD/次床/保護・候補・旧job結果/旧票拒否を含む。手続き的未来画像を実機到達の証明にしない。

Dは新12正位置の全欠落/同金数偽装・cap遮蔽・ITEM・開口offset・全pixel/価格/看板・強語/対象優先・証明偽造を拒否。元217相当のUNKNOWN capは完全陰性不可。既3/4の正例を保持。

Eは実Macの有限保持/exportで元pairがrecent4退役後にも同hashで残ること、全旧priority・restartと24上限、不一致/世代/prefixで捏造しないことを確認する。

## 4. 実装順

独立した計画確認→担当ごとに実行時fixtureと元製品sourceを私的凍結→assertion Red→最小Green→関連回帰→独立差分レビュー。compile失敗をRedにしない。元assertは削除/skipしない。各担当が新しい固有pathを所有する。TEST101の入口は099 engineへ番号101を渡し、旧099/100入口・shared engineを保持する。

## 5. 検証範囲

新単体と直接の関連だけを最終同source CIへ固定。限定Macはfull-framingのC/Runtime受渡しとEの保持/exportだけ。旧Runtime＋現CでEのassertion Red、現Runtime＋旧100 CでCのassertion Red、現Runtime＋現Cで両Greenの計3実行に分ける。全Runtime故障/worldや旧API全体は再実行しない。不変/過去の証拠と今回の実行を分ける。原画像のRing再分類は必要時の1回だけ、未知評価にはしない。

## 6. レビューと未解明

新しい観測MOVEの権限と期限、候補保持、原商品のviewport保存、旧UNKNOWN無再送、各policy独立証明を重点レビューする。全空拍の原因は未解明で、画像不足の分を推測で緩めない。次の実機で最初の欠損pairと到達/次周回を優先確認する。

## 7. 保存と配布

修正前に旧083/093/095/097/098/099/100を照合し、修正表へ原因・対策・検査・再発を記録。実機未確認を完了にしない。標準public runnerだけで新IPA、seal/実compiler/9Mach-O/全tracked sourceを照合。固定ReleaseへIPA/完全source/SHAを公開し匿名全GET/hash/tagを確認する。

## 8. 実機

IPA更新・LoopCtrl完全終了/起動・Start Server/通知/通常VPN、通常1-1ポーズから`sh test_101.sh --until-target`。候補探索→商店→追加観測→全商品確認→完全陰性だけ次周回を依頼。対象/候補/不明/障害は保持。全画像保存とZIP照合完了後のcampaign返却ZIP（索引＋最後のrun全ZIP）、全run原本を保持。毎拍/人超え/未知精度・耐久は未受入。
