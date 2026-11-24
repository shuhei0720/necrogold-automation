# TEST118: 上部V2を全商品・下床の観測位置まで進める

2026-11-24（日本時間）。[118本体](test118-device-failures.md)の追加限定計画。実bf7の147/149後の画像は未収録であり、以下のfutureは独立モデルと明記する。

## 1. 背景と目的

原147/149は潜在商品域row4の新V2。旧V1はrow3でHHDD4歩後row1へ到達する。V2も4歩とした初案ではrow2となり、通常RGBAでは3商品と価格が見えても、下床1セルが中央HUDとの接触でUNKNOWN。raw cap/価格の成立を全3下床成立とした中間解釈は訂正した。UNKNOWN床を補完するRing変更や看板の追加で解決しない。必要な第3DOWNを含むHHDDD5を新V2に限って扱う。

## 2. 設計と親期限

旧V1の4歩と期限は不変。新V2の正の5幅/row4・屋根/外壁/門・最初の横床・候補なし・既model有効のadmit前だけ、5歩に必要な枠を一度割り当てる。directional inputs+5<=16を確認する。元base continuation parentと、その時点のmodel periodを別に凍結し、新allocated parentはbase+1periodを既sync/session/walk/root上限でclampする。足りなければ進めない。

clampの具体値は凍結`cycle_sync_deadline`、`walk_started_ns+45*SECOND`、`session_bound(p)`と、`upper.active`を立てる前に取得する現在の`sync_deadline(p)`。session_boundは`started_ns+180*SECOND`と有効campaignの`root_deadline_ns`の最小。sync_deadlineで現在有効な開扉・静止待機等の独立parentも尊重する。元base continuation自体は新V2初回配分の基準であり上限に再clampしない。after-activeの自己parentを再計算して枠を増やさず、overflow/期限切れ/入力枠不足ではallocationしない。

増える1periodは、row4から従来の観測位置row1へ進む1実歩のため。worker100ms/source150ms、1input窓10ms、SYNC/全走行予算は増やさない。初回allocated parentはrouteの固定上限であり、各bindのjob continuationは既source/model/FRESH等とのminによりその上限以下へ短縮できる。admit後の遅れ・材質差・再判定でroute上限を増やさず、失効した旧jobを復元しない。原4歩の親Dを途中で変更して成功扱いしない。

## 3. 状態と安全条件

newV2だけ最大horizontal2/down3/started5、V1は2/2/4。各歩の新しい実観測FLOOR・非保護・通常MOVED/ACKを要求し、未知床へ計画だけで入らない。全potential保護、V2有限halo投影、候補veto、共有DATA2/合成refresh一回、immutable first source-end/worker-return fenceとearly150例外は維持する。新Pのbase/period/level/opening/source/prefixを固定し、別epochへ持ち越さない。

## 4. 試験への影響

入場前の予算配分と新5歩のためupperの単体・元clock/cost・Mac正常RGBA経路を更新する。旧V1の原P・4歩・positive vetoの回帰を保持。Ringは5歩後の実モデル画像を通常producerへ渡し、既証明が不足なら不足guardを別に調べる。row上限だけを緩めない。全Runtime故障集合は追加しない。

同じ単面worldを5歩へ進めたnormal画像は3商品/3下床/両cap床/価格が成立するが、旧one-faceの下入口/下rail条件と、旧upper-sideの『入口が商品2row上』に合わない。今回は入口が4row上。追加した片面policy18はrow1・完全1SHOP・exact3ITEM/halo/3下床/両cap/価格/full-positive sweepを維持し、row−5の7roofとsolid sideのrow−5..row+1、およびopposite opening row−4を挟む観測GOLDで14個以上の独立壁支持を証明する。左右は同じ相対式。未知の下壁を足さず、RingとC採用が別のgeometry validatorで確認する。旧11/15/17の範囲は変更しない。新18にも既18ink価格支持とdual3%床momentを明示継承し、前回17の継承漏れを繰り返さない。

## 5. Redと期待値

旧4歩V2は、5歩目を発行できずrow2の不足下床を解消できないことを意味Redへする。newV2は元物理phase・記録cadence/ACK/response・逐C実費で5MOVEDし、row1の3ITEM/3下床/価格/capsを観測する。full3の通常Ring結果→独立C証明→耐久保存→RS→次childまで、各範囲を分けて検査する。

新片面geometryは各必須GOLD/門/3下床/両cap/余剰ITEM/保護/価格/ROIを一つずつ欠落させる反例、左右・数pxずれ・target/candidate優先・真の第四価格・小白断片・床momentを確認する。typed policy番号だけを18へ変えた他shapeはCが拒否する。

元parentのままの4歩clock/実費接続と、新V2の初回配分を使う5歩component検証は別証跡にした。5歩は記録phase/cadence/ACK/responseと保存12HUDからの通常再fitを使い、初期constructor/admitの832,790nsを含む全57 C境界の実wall費用を課金。5 ACK/通常unit後、callbackと境界費用を含む最終100ms worker slotのOK/UNKNOWN採用まで進み、固定route上限に417.972ms残った。最終slotは分類だけに100msを追加する意味ではない。未保存の元rolling modelや未来の画像・ACKを完全復元した検証ではなく、正常Ring陰性/RSの結合検証とも分ける。

同componentの別host試行ではbegin実費15.387msで元10ms窓を超えて不合格となり、その結果も保存した。成功測定をiPhoneの10ms保証・毎拍歩行・実効速度の受入にしない。実機は未確認。

## 6. 実装順と所有

限定設計レビュー→旧Red→upper担当のopaque variant/初回予算配分/5歩差分→単体/元clock5歩→process担当の通常RGBA/Mac→root統合。C他機能、Runtime、Spool、API/ABIを変更しない。新Ring条件が必要なら別設計・レビューを先に行う。

## 7. 保存・配布前の確認

旧base/frozen period/new allocated parentを検証記録へ残し、route上限が全callbackで不変、各job continuationがそれ以下であることを確認。最終source/seal/実compiler/IPA/完全source/固定Releaseを照合。初回RSを維持して実機試験を依頼する。単体/モデルの成功をiPhone到達率や速度の受入へ流用しない。

## 8. 対象外

旧V1や他runの期限拡大、動作開始後のrolling延長、6歩以上、未知床/商品を陰性にする補完、撮影のHUD消去、未来画像の実機再現扱い、追加の全体CI。policy18の限定設計を、単面/row制限を一般に外す変更へ広げない。
