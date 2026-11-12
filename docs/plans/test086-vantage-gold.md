# TEST086: 通路の観測地点と単金維持の実歩確認

2026-11-12（クライアント日本時間）。基準 `843d401ecaff22607063bd4fad744aefc8ec51f5`、TEST085/build144。実機主軸・品質維持・時間上限なし。同じ独立担当1名が計画/差分/実物を確認し、原因に関係する単体/旧回帰とIPA同一性へ絞る。

## 受領と原因

実順10554662 LIMIT14/restart12・歩行0、c4817849 GOODS、6a0429bf GOODS、153e6565 MOVEMENT10・2歩/入力3。4ZIP/80PNG・18,473,950画像Bを現schema/client_load/CRC/SHA/PIL/prefix/cursor/実publication gateへ全照合、全paused/terminal/drained/回収完了・選択native行欠損0。見送り判断source16/16保持だが、093の既知誤陰性を含み、16件を意味的な正常negativeとしない。再回収/085再実行不要。

原093の左口(-3,-2)と外(-4,-2)はFLOOR、両脇DIRT。内側(-2,-2)はUNKNOWNで元inboard到達条件に落ちる。初FLOOR88から200.947ms後、元200ms待機は経過済み。full中央値2/0/1・黒450/625、lower325の非黒175/325・中央値6/4/4でR16/floor色を満たす明るいwitnessはない。床に再分類したり、上の黒口を根拠にしない。

実4cmd6 UPは元10ms窓でbegin/ACK成功後、適格100–106/110の8原画で旧15段すべてUNKNOWN。最後commit時に元visualPは約1.903秒残る。原画像では地形が画面下36px移り、実UP1歩と整合する。singleton GOLD1→1、旧STONE全3保持、旧DIRT19中16保持・非共線10・9translation一意camera(0,+1)。101は元phase/blur/axisの支持・帯・競合差を満たす。085Aの確定MOVED再同期は未確定なので、085Bの静止proofは金候補なので資格外。8回/P/閾値を広げて通す問題ではない。

## A: UNKNOWNは保持して既知床vantageへ近づく

新helperと既candidate loop内の限定分岐だけを追加し、旧判定/口10bit・旧分岐を維持する。Perception/choose_passage/Controllerは変更しない。

- 初期worldの上/左10口のうちk=±2の4cornerだけ。両Scene等の未来条件を作らず、その時点の元passage_scene(FLOOR/CLEAR/GOODS_UNKNOWN)を使う。
- mouth/outsideとも観測FLOOR、両flankは観測DIRT/STONE、同初期壁列DIRT/STONE支持3以上、元passage_sceneの金なし・元crossのprotected除外・口/外/endpointのFLOORと経路材質によるITEM踏込み禁止を全AND。inboardはUNKNOWNのままで元FLOORpathなし。
- inboardからroom内側へ1cellだけ接線方向に寄った一意endpoint（原093なら-2,-1）が観測FLOOR/crossclearで、originから旧BFSの最短path length3で到達可能。midmouth/右下の出口・長い迂回を新規探索しない。
- 元choose_passageは同じworld mouth/外側goalに近づく既知FLOORだけを返す。原093ではLEFT/reason10/goal(-2,-1)/FLOOR/path3、UNKNOWN inboardは変えない。新gold後は元shop移行、未到達/未観測は旧未判定/NO_PATH・元有限予算のまま。推測掘削/扉/UNKNOWN入力・世界全体の店なし認定を増やさない。

Git外160Scene校正は093だけmask0→bit5=32、他159/既bitは維持。未知実機の成功率ではない。公開Sceneの元UNKNOWN/口/外/両壁/観測routeを先assertした意味Red→最小Green。4corner/old10bit、endpoint route3と迂回5・到達不能/不在/保護、inboard/material/口外/壁列境界、GOLD/商品/invalid、旧branch不変・source不変・公開Navの各step実nextFLOOR/UNKNOWN手前停止を新6件で確認する。元bit受理から有限接近・期限・UNKNOWN無再送を担う公開Controllerは同bytesなので、関連する旧072のgold_clear_passage/shadowed_outer_goal/acknowledged_unknown_visual_motionと期限のexact CIを選ぶ。新A Controller結合は増やさない。C seam0を優先し、既単体の形式再実行をしない。

## B: 単金を維持した同方向1歩の別証明

元15段/順序・各閾値を変更せず、最後のUNKNOWNだけに新unit-only helperを追加する。GOLD0→1の083補助や無金zero-only085補助を拡大しない。

- both FLOOR/GOLD_CANDIDATE/GOODS_UNKNOWN、GOLDは正確に1→1で元translation先へ保持。DOOR/ITEM/保護なし、origin/次cellが観測FLOOR。旧STONEを全て保持し最低2、同translationで旧DIRT最低9と非共線支持、元9translation一意を要求する。
- 元raw73が全finite・最良が命令方向のcamera9px unit、rawscore>.45かつ元gap≥.08。元independent_phaseを全ANDする。rawscoreを.45以下へ書き換えたと扱わず、強度は次の独立structural witnessで証明する。
- 元worldblur≥95%/支持≥300/独立2帯各100と、fixed-axis52≥75%/支持≥300/2帯各100を全AND。両者で全73を走査し、支持300以上の競合へ元texture_lead15pp、低支持は元規則。geometry単独・ACK単独・回数だけでMOVEDにしない。
- 新出力は命令同方向のunit MOVEDだけ。BLOCKED/開通/入店creditや曖昧な入力再送を追加しない。旧票/reference資格・ACK prefix/earliest/元P・8評価/全予算/GOODS先行は元Controllerのまま。

101のraw .548093498・runner .831152607/gap .283059109、blur611/28bad・帯368/243、axis613/72bad・帯485/128と元位相/競合条件が成立する。100は強度/位相不足、102–106はblur競合差不足を維持し、110も全AND成立なら同様に受け入れる。frameIDを製品条件にしない。Git外prototypeで原8組と正解付き8px/TWEEN/純unit・逆・alias等の関連negativeを照合する。旧081実5金1→2/newDOORは証拠不足で新対象外、未解決を保持する。

公開C4の手続pixel/Sceneで、旧15段UNKNOWNと独立したraw/phase/blur/axis/geometry前提を先にassertして意味Red→最小Green。単金保持/材質/保護/商品/DOOR/0→1・1→2・複数金の拒否、phase/支持/帯/競合/9pxと8px・逆/静止、元known結果/invalidを選ぶ。公開Controllerの同ACK/適格画像/元Pで実1歩だけcreditされ次入力へ進む結合1件を選ぶ。必要なHOST guarded C SHIMは固定前提計測のみ、Controller private flag/forced motionなし。全新C宣言/export/static名をASTで固定し実MachO markerへ結合する。

## 所有と最終検証

Aはcandidate担当のNav上部/候補test、Bはmotion担当のNav下部/motion test。地域限定applyし全ファイル置換しない。作者Redと同独立担当の計画確認後に製品へ適用する。B RedでAを固定した場合、全8が旧baselineだったと誤記せず対象を分離する。新作者単体と関連旧exact名・小さなselector自己試験だけを同code CIへ選び、全Runtime/worldを既定にしない。

最終source8/C4と保持原画像・旧known回帰を一度照合、fresh pinned Git G1→seal/apply。同code限定CI/実IPA/5実物verifier・全sourceを照合し、固定Release公開後に匿名全GET/SHA/CRCを確認する。Runtime/core4/API16/cap15/client16/v2/旧v1回収・G1/R12を維持予定。無変更Runtimeは固定保存Red133と今回Mac Greenを分離再利用し新Redを増やさない。

同じiPhoneの新しい通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認/PAUSEを複数回依頼し、全run ZIPと候補見逃し/停止位置/全商品/PAUSE/拍間隔を返してもらう。新実機到達率・恒久毎拍/人超え・対象識別/通知/対象なし循環は未受入とする。
