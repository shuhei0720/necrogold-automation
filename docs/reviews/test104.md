# TEST104: TEST103実機結果と修正確認

2026-11-15（日本時間）。実機の失敗を起点にする。補助試験の成功を実機改善完了とはしない。

## 受領

8 ZIPは4実行分のrun/campaign重複。全218ファイル・111記録・99 PNG、厳密JSON123件、CRC/path/SHA/chain/同世代・安定prefix・RGBA・wrapperを照合済み。元数値表現を保持し、原本はGit外。再回収は不要。

添付順ではなくaccepted_startで対応した。

| 実行 | runの先頭 | 実機報告 | 記録 |
| --- | --- | --- | --- |
| 1 | fedfc307 | 鉄扉・上部入口、開扉後停止 | screen/17、cycle_observe、250→252、ROUTE/10。通常PARTIAL判定は約4.91msで正常採用 |
| 2 | 0797f4df | 普通扉・上部入口、一歩入店後停止 | screen/17、cycle_observe、214→216、ROUTE/10。通常PARTIAL判定は約12.78msで正常採用 |
| 3 | 339df93e | 商品可視だが次周回へ進まない | goods/1、原205の通常FULL判定は約16.35msで正常採用、UNKNOWN/incomplete。GLYPH/ROWSで完全陰性不成立 |
| 4 | fcf6fb67 | 普通扉・上部入口で停止、候補116を見逃し | screen/17、cycle_credit、332→344、ROUTE/10。通常PARTIAL判定は約14.89msで正常採用。次MOVE21は確実未送信 |

3つの上部入口は、入力方向ではLEFT。TEST102のUP専用episodeに入らない。全実行で再開intent/命令IDは0。分類未実施・分類時間切れ・restart送信失敗とは区別する。

## 調査範囲

FR-095/097/098/100/101/102/103の部分商品・材質差・開扉・観測継続・完全判定、FR-084/086/094/095/097/098の候補を照合した。

不変Perceptionをstrict O2で原9画像へ各一度適用し、Sceneを固定した。Controller/Navigation/Ringの診断と製品試験は別に記録する。未記録のprivate状態や未来応答を実履歴の再現と呼ばない。

候補116はFLOOR/CLEAR。既occluded-upperのmouth UNKNOWN条件だけが不成立で、実画像ではFLOORだった。両flank壁が観測されている点で旧097の負例と分け、同じ観測床の接近経路だけを使う。

## 修正と確認

上部入口の3pairは通常Motionでstrict BLOCKED、dx/dy=0。元ITEM/保護と次の選択は不変だった。新しい遠方GOLD/材質変化では旧creditと確実未送信票を撤回し、最新immutable画像を通常判定へ渡す。親期限は短い方を保持し、新結果と別の静的確認なしに入力しない。OBSERVE_MOREとCREDITの両方を修正し、旧ITEM露出の一度限り資格を消費/復元しない。

原205は全商品帯の独立証明を追加した。実2full SIGN、実GOLD、正確な3ITEM/保護11、直下の価格床3、両rawcap・共通価格・全商品帯の対象探索と強語vetoを要求する。部屋外側の壁形状を商品可視性の代わりに使わず、未観測の床や余剰ITEM/保護を拒否する。新policy9の全商品帯は非HUD中央域に限定し、旧1..8/閾値/探索範囲は不変。

原116には両flank壁と元の壁支持、外側UNKNOWN、既床3歩を必要とする別候補guardを追加した。未知セルや普通扉への進入許可は追加しない。

| 選択確認 | 結果 | 範囲 |
| --- | --- | --- |
| Controller | 新14＋直接回帰18＝32成功 | 各拒否/親期限・prefix・取消・候補/繰り返し再判定、LEFT開扉→LEFT移動→DOWN、通常producer→保存→intent→実RESTART ACK→次floor。手続き的な観測で実機再現ではない |
| Ring | 新8＋旧関連53＝61成功 | 価格床/保護/非HUD/余剰/対象・候補・強語・数値変造・旧形状拒否。最終58入力不変 |
| Navigation | 新7＋旧関連16＝23成功 | O0/strict O2。旧branch/旧assert保持、3歩とも既観測床だけ |

各機能の実装前assertion Redを保存。compile/setup失敗、旧許容DIRT→FLOORに新jobを期待した新fixture、半セルの新fixture座標誤算、早期Scene拒否の新fixture前提不成立は製品Redと区別した。合成container9の白装飾が価格群を越える例は元の余剰検出でUNKNOWN保持が正しく、新しい価格位置差の正例とは分けた。製品閾値や旧assertは緩めていない。

原205の修正後通常分類は1回だけ、完全陰性/policy9/flags0・証明有効。約40.97msで元のworker残り99.08ms内だった。これは開発機への時計写像による校正で、iPhone速度の証明ではない。その同じResultとSceneを公開C APIへ渡す校正でも完全陰性を採用した。prefix0/新規制御状態・時刻だけ正規化した条件であり、元prefix12の全履歴やRuntimeの再現ではない。追加compile/分類/Perceptionは0。

原116の新通常Nav校正は1回でmask0→1、Scene不変。Controller/Navigation/Ringだけを変更し、残33native・Core/公開ABI・Perception/Runtime・旧回収/canonical15/56088B ELF/G1/R12/共有099は保持。独立差分レビューは製品source GO、P0/P1なし。選択CI/IPA作成と実物照合は配布時に記録する。今回の各修正の実機改善・毎拍/人超え速度・未知対象精度は未確認。

## 下側の商品を全て見る追加修正

ユーザーの再確認を受け、配布を保留して、最初のDOWN後の候補保持で終わる試験とは別に全商品可視までの連鎖を追加した。coherent公開連鎖では元d886 Cが次の票をUPにし、row+2のB下端322を残した。原332の7ITEM/row+4投影では、row+3で重複した保護膨張が実際には非保護の次床も拒否し得る。これを実機の新たな再現数には数えない。

CへDOWN専用の有限観測を追加した。全ITEMとcoherentな全row/partialの保守的potential、必要DOWN数、元親期限/入口/levelを固定し、最新判定→別のstrict零→新票→実MOVED→最新jobを一手ずつ要求する。x中央域と投影上端を確認し、既7HUDの下端閉集合を上へ投影して旧可視potentialを保存する。歩数・ACKだけで進捗を作らず、正確な保護と各実足元の観測FLOORを確認する。全potentialが収まった後の不明は保持し、入口へ戻る旧経路へ落とさない。

レビューで、data-only FULL差替え時の旧sourceとの零変位bridgeが欠ける条件を検出した。direct/queued 1method・2assert失敗/error0を保存し、不明/非零bridgeでworld資格をsticky無効化した。新self零だけでMOVEへ復活できず、datajob/候補・対象/独立陰性は処理できる。UNKNOWN保持時だけ元bridge pairと期限を既StopDetailへ凍結し、別jobへ証拠を付け替えない。

追加9件の開発確認が成功。3ITEMと7ITEM→真のFULL3への絞り込み、商品・価格が全て入った最新画像での通常policy9、耐久保存/intent/実RESTART ACK/次floorまでを確認した。対象優先、実保護床拒否、旧位相/未送信/取消/owner/不明入力、元親期限とpending worker期限、far材質の再判定/FIFO、bridge反例も確認した。これらは手続き的画像/状態/時計による制御確認で、未収録のiPhone未来画像や実ゲーム到達の再現ではない。

RingのHUD拒否が不足するとのレビュー前提は誤りだった。既box_valid/partial_hudが同じ7HUDを検査する。凍結f80普通producerのstrong-auth合成row339,231はglyph/merchant1.0でも正常UNKNOWN/INCOMPLETE・BOUNDS512となり、追加guardは不要。私的driverのビット定数誤記は保存値の純検証で訂正し、製品Redとしない。Ring/Nav/元205Resultの再分類や無関係な全体試験は追加していない。

初期C32件はd886の証跡であり、追加観測を含む現Cの成功とは混同しない。追加C e336・新test d511は独立差分レビューGO/P0/P1なし。新9＋直接関連13＝22件は最終同sourceで成功（約38.99秒、全凍結入力不変）。旧C32も含む最終選択CI/IPA照合は配布時に追記する。
