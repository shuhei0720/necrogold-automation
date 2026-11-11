# TEST078: 閉じた金扉へ到達する1歩の確認

2026-11-11（日本時間）。baseline `63ca426770349bab73953241982a171d76ca35e6`（TEST077/build124）。実機主軸の通常局所修正。NavのUNKNOWN限定MOVED補助と新単体、限定CI・独立レビュー1名・新IPA/固定配布を対象にする。Controller/Runtime/Perception/JSON/全header/API16cap14v15/ABI/G1/R12/元閾値・全期限・予算は維持する。

## 実機根拠

077受領2ZIP/38原PNG（18/20）を全hash/CRC/デコード/manifest/prefix/cursor/厳密schema/実publicationで照合。全PAUSE/完収、取得failure/timeout0、hostエラー/取消0・status33回最大1.407秒。2の初期PNG1のcapture行は256行ringから消えており、その行は補完しない。保持省略や未来画像を再構成しない。raw/Scene/数値はGit外received077/test078-*。

実順92742894→587d35cc。1は7restart/5MOVED/7方向入力/1開扉、rootが原372で3商品と価格75/125/65を確認し到達成功。最終入力は商品優先UNKNOWNのままで移動を捏造しない。2は7restart/6MOVED/7方向入力/開扉0、最後のUP cmd24/source395→419が実1歩なのに8評価UNKNOWNでMOVEMENT停止。原395の閉扉(0,-2)・金(-1,-2)/(1,-2)が419の(0,-1)・(-1,-1)/(1,-1)へ厳密に相対移動し、閉扉直下へ到達している。最新NavはUP/reason5/DOOR、開扉と進入は未実施。

cmd24の実beginはNB+5.355ms/D−4.645ms、ACK後575.226msの419もvisualD残約1.953秒、期限超過や未送信SCREENを直接原因にしない。直前cmd23は未送信SCREENから別ID24へ同拍再予約済み。別cmd21 too_lateも区別する。最後のreference不適格は元scheduleD超過と整合し、非保持の中間評価時の資格は断定しない。

## 旧判定を緩めない理由と新証拠

実395→419のraw最良は同方向厳密unit(0,+9)、score .5670244288、gap .3825624042。closed_translation/unique_gate_translationは1。旧medianは支持506/bad13・領域[4,0,502]、detailは318/bad1・[4,0,314]で、独立2領域各100を満たさない。またgate_detailは最新さらに次のFLOORを要求し今回のDOORを拒否する。条件を外すだけでは解決せず、不採用。

既074の5依存中央gradientは319/bad5だが開扉用y65帯[254,65]、既world blurは137で不足。camera中央52の単一案は中心だけのmask検査では310/bad4・137/173だったが、5依存すべてのUI/maskを除くと250/bad4・115/135となる。必須支持300未達で不採用、UI跨ぎ38やROI境界22を証拠に戻さない。旧面/支持条件は維持する。

代わりに新unit専用の別feature面を設ける。各frameで水平→垂直の固定順に、中心とその軸±1の実使用3依存がすべてmask内・観測known・非DOOR/ITEM/protectであり、中央差分の絶対値が2*6以上の最初の軸を一度だけ選ぶ。featureはaxis/その3材質pattern/signで、両frameの同axis/同patternだけを全73shiftで比較する。未使用軸の画素は読まず、各candidate/画像pairに都合のよい軸へ選び直さない。1画素1支持、既max-axis5依存面の条件緩和とは呼ばない。

maskは既opening_maskのまま、使用する全3点で両画像のmask/UIを確認する。帯は075と同じ固定camera中央52（raw207/4）。両画像中心51/52を除外し、最大半径1の実依存が上下で重複しないようにする。支持300/95%/上下各100/全73への元texture_leadを維持する。featuresはframeごとに前計算し、全shiftで同じ表を使う。

この単一の固定仕様だけをread-onlyで監査し、395→419は支持322/bad5（98.4472%）・upper150/lower172、394→419は320/bad5・150/170、O0/strictO2同値。72競合はすべて支持300未満で、元規則の候補外である。十分支持競合に対する実15pp優位を測れたとは一般化せず、手続negativeでその境界も確認する。位置/閾値/優先軸を結果に合わせて探索・変更しない。

## 限定する入力証拠

新補助は全旧分類後もUNKNOWNの場合だけ。両FLOOR/CANDIDATE/GOODS_UNKNOWN、全protected/ITEMなし、旧origin・旧実nextと最新originの観測FLOORを要求する。旧2*directionのDOOR＋法線が入力方向に一致する金bracketが、最新directionの同DOOR＋同法線bracketへ対応するケースだけに閉じる。全旧GOLDの厳密translated保持と個数同一、zero/±1/±2全9の幾何候補で対応が唯一であることを要求し、DOOR→FLOORはこの補助では扱わない。

元raw全73候補の最良が同方向unit・finite・score>.45・gap≥.08であることを要求する。元のhigh-intensity閉金扉rescueと同じ枝に限定し、既primaryや他補助の既知分類を変更しない。新52面も支持300/一致95%/上下各100、全73への元15pp規則を維持する。新3依存featureの前計算/比較は独立追加し、旧65関数/既5依存features/cache比較の意味と既知出力は変更しない。

成立時だけMOVED(dx,dy)=入力方向のunitを返す。最新さらに次がDOORでも、過去の実到達を証明できることと次の入力権限を分ける。次は通常Navの開扉へ戻し、閉扉への到達でentrance/DOOR_OPENED/商品creditを作らない。新reserve/期限延長/再送/静止をMOVEDへ変える権限は追加しない。商品VISIBLEや不明inputの優先停止は既Controllerのまま。

## 単体・独立確認・配布

手続Sceneの公開ng2_motion単体を旧077 compile成功の意味的Red→最小Greenへ。O0/strictO2を確認し、4方向のunitと閉金扉到達→次Nav DOOR/未入店、非FLOOR・商品/保護/ITEM・旧金削除/法線/開扉/幾何複数解、raw zero/逆/2tile/8/8.5px・gap境界・known出力保持を検査する。新面は両側の使用依存UNKNOWN/異材質/UI/mask/protect・H優先/片側H対片側V・不適格HからVへの固定選択/未使用Hを読まないpositive・差12等号/11/反符号を検査する。単帯・51/52境界依存・支持/95%/全73の十分支持競合と15pp境界、全73のfeature表とraw実3点直接loopの同値も確認する。受領PNGはGitへ埋め込まない。

関連回帰は旧gate_detail/開扉gradient/金なしunit・075 static/cache/原primaryとControllerの開通・商品/UNKNOWN無再送から選び、正確なmethod一覧を凍結する。既assert削除・skipや全Runtime/world積み増しをしない。原2runの保持されたACK比較でknown判定不変/今回UNKNOWNのunitだけが変わる範囲を確認し、欠落futureやlive全状態の再現とは区別する。

通常1名が計画/最終差分を独立レビュー。fresh G1→sealでNav1/他21不変、実compiler/全MachO/IPA/全tracked sourceを照合し、固定Release assetを匿名全GET確認後に返す。新IPA更新/LoopCtrl再起動/Start Server/VPN、通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認をまず2回、保存照合後runtime/test-078-<run_id>.zip全回分と全商品/停止位置/拍間隔を依頼する。
