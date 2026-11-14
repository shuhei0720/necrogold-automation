# TEST100: 実測した入店停止・商品証明・候補見逃し

2026-11-15（日本時間）。基準39851a4、修正版nativeはbuild187/code4ba361d。[要件](../requirements/necrogold.md)・[契約](../contracts/native-control.md)・[修正表](../fix-records.md)。通常反復を維持し、今回の新しい部分商品bind/証明だけ8観点で確認する。実機成功を保証しない。実施結果は[検証](../reviews/test100.md)へ記録した。

## 1. 背景と受領

6添付は3runと各同一内容campaign。全73PNG/81record/160原本、CRC/SHA/manifest/連鎖/画像登録/896×414/RGBA hashを照合。実時刻順は13e3→3444→9c66。campaign cancelledやmanifest completeは実機成功/利用者取消の証明ではない。

実1は開扉ACK後、未送信LEFTの232→233でSCREEN。唯一の材質差は遠方(-3,+1)DOOR→GOLD、両3×3とprotectedは不変、同LEFT/reason5/FLOOR・独立strict BLOCKED。元期限の122.8ms前で、既opened-entry関係だけが拒否。実2は456に3商品が見え、19.070msで結果を採用したがUNKNOWN/incomplete。列267/189は正しい。従来glyph証明と別形のpolicy3がどちらも適合せず、flags260。実3は223→225の新ITEM/保護増加でcycle_partial_distant_dirtが拒否し、旧partial結果の継続権限を失う。2.8秒以上の元horizonが残る。実2の見逃し59は、左下口(-3,+2)のDIRTと、その外側の見えるFLOORを旧候補が扱わない。

6枚だけ現Perceptionを各1回校正し、不変Sceneを私的cacheへ保存。以後再解析しない。初期判断に未来画像を使わず、保持Sceneの関係成立と未収録先の実機成功を区別する。

## 2. 設計と変更範囲

A: cycle profileの既opened-entry関係だけに、同方向の実開扉ACK/同完全Decision/独立strict零/元prefix・期限の下で、遠方DOOR→GOLDの限定関係を追加する。変更セルは両3×3外・非保護、変化前後で両側を観測GOLDに挟まれる。旧GOLD/ITEM/保護を失わせず、普通扉・未開扉・対象セル・UNKNOWNへの権限にしない。旧profileの挙動は変えない。

B: 新しく見えたITEMを旧partialの不在証明で処理しない。OBSERVE_MORE・pending/input/credit/candidateなし、同prefix/固定world位置/完全safe-floor Decision・同方向開扉ACK・独立strict零の下だけ、単調なremote ITEM/protected増加を最新partialの新jobへbindする。旧ITEM/旧protectedは保持、差は遠方FLOOR/GOLD→ITEMと新ITEMのself/cardinal保護だけ、両3×3は不変。旧job/result/credit/票を失効し、最新画像を通常classifierで判定してから次入力へ進む。新候補/不明は通常保持する。旧拒否診断は権限0で残す。continuationは旧horizonとのminで絶対に延長しない。stationary episodeにつき1回、再許可は実MOVEDまたは通常の実restart後の新levelだけとし、bind/時刻/未送信再予約では復活させない。

C: 左下bit9だけの外側fringe候補を別helperにする。WALL={(-3,1),(-3,2),(-3,3),(-4,3),(-2,3)}、FLOOR={(-4,2),(-2,2),(-1,0),(0,0),(-1,1),(0,1)}、短い観測床vantage(-2,1)≤3歩・inboard(-2,2)≤4歩、外側FLOORは現床graphで未接続。CLEAR/商品UNKNOWN/ITEM・protectedなしが必須。元の口/他helper/chooserは不変。DIRTはDIRTのままで、既chooserの観測床接近・独立確認・見送りだけを使い、掘削/未知進入を追加しない。

D: 商品証明は新policy4/board_mode4として従来policy1〜3を保持する。固定の下側商品・側面入口形を正の根拠にする。rowを(ax,ay)へ写し、3ITEM(ax..ax+2,ay)・両FLOOR cap、solid側5GOLD(ay-3..ay+1)、反対側2GOLD(ay-2/ay)・入口FLOOR/DOOR(ay-1)、正しい2face/全stripを要求する。左右mirrorは同じ観測条件。Controllerが同immutable Sceneで独立再計算し、数値gold countだけを信用しない。新ABI fieldは増やさない。

新形だけ、価格の共通9px baselineと3cell各18白画素以上を要求する。全既価格band内の4番目の十分な価格群は拒否し、実456の1pixel剣先を価格にしない。小片は原画像と私的geometry診断に残し、unmatched_pricesは十分な余剰価格群の数として0必須を保つ。別の既存countへ小片を加算しない。既strong-word・全位置icon上界/完全探索・余剰列/board/price・endcap・商品3個/全範囲・候補優先を保持する。glyph閾値の一律緩和、全商品名称登録、UNKNOWNのNEGATIVE変換は禁止。Bank/Coverage/canonical15/56,088B ELFは不変。元100ms classifier予算は延長せず、19msの旧早期拒否を新完全探索の性能と混同しない。

製品変更はNG2Controller.c、NG2Navigation.c、NG2Ring.cとTEST100の最小入口/必要なラベル選択だけ。Runtime/旧ABI/旧入力・時刻・取消・UNKNOWN無再送/HTTP/回収/全画像照合/正常handoff資格は不変。

## 3. 期待値と単体

Aは実cycle constructorから実ACKした開扉と未送信の独立画像で意味Red→Green。同方向/異方向・旧profile・非bracket・近傍/保護/旧GOLD消失・期限/prefix/取消の拒否を保持。Bは新job ID/最新source・旧result拒否・新classificationまで入力0・候補保持・旧horizon・一度限り・MOVED前の再許可0を検証し、静止せず動いた/保護消失/旧ITEM消失/近傍差/未開扉は拒否。旧partial/FULL bindを関連回帰へ選ぶ。

Cはpublic mask0→512の意味Red後に実装し、各壁/床/short route/外側未接続/ITEM・protected・gold・goods・ABI・固定座標の反例、旧候補のmask/既chooserを検証。Dは正しい新形でUNKNOWN→完全陰性、新shape/価格証明の偽装・欠落・4価格/余剰board/部分表示・旧policy1〜3・強い語/対象icon・全域候補の保持を検証する。Controllerは偽のpolicy4結果を独立拒否する。

raw原本はGit外、公開fixtureは手続き的な形/画素/時刻とし、実画像dumpを混ぜない。現source456は旧/新をそれぞれ1回だけ分類して結果と所要時間を私的に校正する。未知精度/人超え/未来到達へ流用しない。

## 4. 実装順

独立した計画確認→各担当のassertion Red保存→最小変更→変更単位のGreen/関連回帰。C担当がControllerのA/Bとpolicy4独立検証を一元所有、Ring担当はRing.c、Nav担当はNavだけ。入口は099 engine/schemaを共有し、test100.py/shellから番号100を渡してspool/返却ZIP/索引をtest-100へ分離する。旧099番号/既定動作と回復を保ち、他labelの索引を受理しない。既publication/native/protocolへ変更せず、実3.9でラベル・同UUID回復・旧099既定を関連確認する。作者の全Green後に狭い独立差分レビュー1回、実際の指摘だけ訂正する。

## 5. 回帰・CI・性能

現在source/方法一覧を固定し、変更部/関連C・Nav・Ringと新入口だけ。Runtime製品bytesは不変とし、今回のC挙動をpublic単体で確認する。独立計画レビューのP1を反映し、新PARTIAL bind→新job/最新immutable画像の通常worker分類→旧job結果の不採用→candidate又はtimeoutのinput0保持を確認する限定Mac callback一件を必須とする。必要なら同じsource/job tupleの既fixtureを再利用する。手続き的producer/resultによる補助と実機を区別し、旧Cの意味Red/新CのGreenを該当caseだけで先に確認する。今回変更しない全Runtime故障/world/API/spool/export/全Ring原画像は形式的に再実行せず、旧sourceの証跡と不変bytesは過去結果と明記する。全新C単体と限定Macが通ってからIPAを作る。

classifierの新完全経路は本番C flagsで局所計測し、元deadline/cancelを保つ。実機速度の受入にはしない。

## 6. レビューと残る問題

入力権限・候補保持・証明の各境界を独立して設計/期待値/安全の観点で確認する。policy4を単なるgold閾値変更にせず、旧policyの意味を保持する。新partialは再分類へだけ移り、旧証明で新商品を捨てない。UNKNOWNを解けない配置は保持し、その理由を報告する。今回の3事象に根拠のない動作変更を混ぜない。

## 7. 保存・配布

修正表に修正日/事象/原因/対策/改善確認方法/再発数を記録し、097/098/099など同系列を照合する。単体合格や過去の実機1例を改善完了としない。native封印、実compiler/9Mach-O・保持資産、全tracked source bytes/CRC/来歴を確認し、固定ReleaseのIPA/全コード/SHAを公開、匿名全GET/hash/tagも確認する。raw/設定は公開しない。

## 8. 実機

新IPA更新・LoopCtrl完全再起動・Start Server/通知/通常VPN。通常1-1ポーズからTEST100 --until-targetで探索/入店/全商品確認/対象なしの次周回を試してもらう。対象/候補/不明/障害/上限で停止し、iSHの全保存・ZIP照合完了後のcampaign ZIPを返してもらう。索引＋最後のrun全ZIP、全run原本は保持。新規到達率/毎拍・実効速度/未知対象精度は実機で確認する。
