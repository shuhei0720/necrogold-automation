# TEST094: 上左の影通路へ観測床から接近

2026-11-13（日本時間）。基準 `3e79c460840bf05fef0f49f5a10f39e09f2815cd`。ユーザーがTEST093実3の原156へ上向きの経路を示した。これは通路候補の指定であり、金壁・店の存在証明ではない。native商品周回とは独立したNav限定差分とする。

## 原因と限定追加

実3 `70cd5e6c` は0入力/0歩/restart12でLIMIT。RESTART cmd11の確認152から原156の取得開始まで216.194msで、既200ms待機後の最初の観測。152–155の原画は未保持で、過去画素・最初の分類を補完しない。原156はFLOOR/CLEAR/peak60/GOLD0/商品UNKNOWN/保護0、旧候補mask0。固定上左口(-2,-3)、外(-2,-4)、内(-2,-2)、その横(-1,-2)はUNKNOWNである。通常分岐は内側床経路、086補助は口/外の観測FLOOR条件に落ちる。084の下半の明るい床証拠も不成立。FR-084-MOUTH/FR-086-CORNERを照合したが、その適用条件とは異なる。

新しいpure Nav helperを既候補loopに追加し、次の全条件だけで固定bit0を保持する。旧helper・chooser・Perception/RGB・enum/layoutは変更しない。

- 元passage_sceneに加えFLOOR/CLEAR/商品UNKNOWN/GOLD0、全ITEM/保護0。新しい092の正の未局在金の資格は広げない。
- 口(-2,-3)、外(-2,-4)、内(-2,-2)、横(-1,-2)の4セルはUNKNOWNのまま。未知を床や金へ置き換えない。
- x=-3、y=-4..1の6セルが連続した観測DIRT、口の反対側(-1,-3)も観測DIRT。黒だけの一般的な隙間や、他の角/中央/右/下へ拡張しない。
- x=-2..0、y=-1..0の6セルが観測FLOOR。元の非保護FLOOR BFSで(-2,-1)へ最短3歩で到達可能であること。

旧chooserは固定world口から外側goalへ近づく観測FLOORだけを返す。原156ではLEFT/reason10/target(-2,-1)/FLOOR/path3。一歩ごとに既Controllerが実変位と新観測を確認し、保持原画のままなら3歩後にUNKNOWN手前で止まる。未収録の先を床・開通・商品到達へ合成しない。旧world原点、有限wait/NO_PATH、予算、取消、UNKNOWN無再送は既制御のまま。

## assertion Redと検証範囲

公開Sceneの手続きfixtureで観測材質・4UNKNOWN・旧chooserの安全な3歩を先にassertし、候補bit0の期待で実装前Redを測る。新6methodは次を固定する。

1. 指定された影形状だけがbit0を追加し、Scene全bytesとUNKNOWNを維持する。
2. 連続DIRT列6セルと反対側DIRTの欠損・別材質を拒否する。
3. 4UNKNOWN、6観測床、最短3歩・到達不能/迂回の境界を確認する。
4. 固定world口へ一歩ずつ実nextFLOORだけを選び、未観測の内側直前で停止する。
5. 黒だけ、別side/corner、商品/金/全保護/invalid Sceneを拒否する。
6. 旧10口、084片壁、086観測cornerの既maskを維持する。

新classと関連する旧084/086/072のNav試験を同sourceで選ぶ。Controller/Runtime/Perceptionは不変のため新しい全world/全Runtime再実行を増やさない。原156は一度だけ分類済みのGit外Sceneを再利用して旧0→新bit0と旧chooser判断・不変Sceneを校正する。他の未観測mapを正解negativeへ数えず、校正を未知実機の到達率にしない。native変更のbuild/seal/実compiler/配布物確認と、新しい通常1-1からの一連実機確認は094全体の配布工程に従う。

## 実施記録

公開fixtureの4UNKNOWN/7DIRT/6FLOORと旧chooser path3が通った後、候補1対旧0でO0/strict O2の意味Redを確認した。追加17行のhelper/呼出後、新6＋旧084の5＋086の6＋072の8＝25methodが両profileでGreen。初回の新負例で列の一部をFLOORへ変えた2条件は旧左口の正当なbit64/128を満たしたため、期待0をその既bit保持へ訂正した。元の意味Redと初回出力を残し、旧assertや製品条件は弱めていない。

原156は前回分類済みSceneだけを新Navへ渡してmask0→bit0を確認した。Scene全bytesと旧chooser判断は不変。新helper/1呼出の逆除去で基準Navの全bytesが一致する。現Nav SHA `072fa967028b67fe8d5f031b5ff50b876c029af386d3acbb0b199de7310d2b0e`。新IPA・実機での上向き通路接近と商品到達は未確認。

独立担当が計画・差分・新期待を静的に確認しP0/P1/P2なし。追加試験・再分類は行っていない。094の配布selectorは新6methodと旧関連集合を実patched sourceへ結合し、新Nav全file hash/新helperをseal・実物検査へ含める。Controller限定の093selectorをそのまま再利用しない。
