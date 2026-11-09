# TEST058 合成商店worldの期待一覧

状態: 実装前の期待。2026-11-09（日本時間）。[計画](../plans/test058-shop-dispatch.md)。既存のゲーム応答を手順どおり返すfixtureとは別に、gestureを独立な地形が消費する。未知実ゲーム/人間確認済みの地形ラベルとは扱わない。

## 地形と時計

基準north: player=(0,0)、入口G=(0,-3)、金壁=(-2,-3),(-1,-3),(1,-3),(2,-3)、入口前の床=(0,-1),(0,-2)、商品3枠=(-1,-5),(0,-5),(1,-5)。その他の通行域はshop内部だけで、外周はSTONE/UNKNOWN。east/south/westは入口/通路を90/180/270度回転。商品棚の中心はGから店内方向へ2セル、3枠はそこからworld X方向に-1/0/+1とし、入口方向によらず価格3列は横並びとする。商品位置と遮蔽で表示し、閉扉中/外側では価格未観測、入口Gへ進入後はVISIBLEとする。家具の画素配置はこのworld座標から投影し、reportや期待したgesture列で商品を出さない。

detour基準north: (0,-1)=STONE、唯一の外側経路を(-1,0)=FLOOR,(-1,-1)=FLOOR,(-1,-2)=DIRT,(0,-2)=FLOORにする。初期DIRTは1回掘削でFLOOR、扉は1回probeで開き、どちらもその操作ではplayerは動かない。以後の同方向入力で初めて移動する。他方向も同じ回転。最短経路は正常4入力/遠回り掘削7入力で、入力16予算内。

入口を挟む2セルに加え、外側±2も金壁にした5セル幅の正面壁を使う。south原点では中央のbracketがHUDでUNKNOWNになるが、外側の金壁が実際に観測できることをCで確認し、normalの最初の1歩で中央の入口がHUDから外れる配置とする。detourは先に2床を歩き、その後の角セルをDIRTとするので、southでも掘削前に入口を観測できる。最初の2セルだけの最小壁では開幕可視条件のNav用tile証拠が0になることが判明したため、Red前に地形定義を訂正した。扉/床のclassifierを緩めて隠さない。木扉はwood、鉄扉はstone系spriteを金壁2セルのbracketに置き、認識経路を通す。原寸896×414、既存HUD/textureを再利用する。world独自のepoch/520ms周期からHUDと受付を描き、入力は150ms先行±10ms・同拍1回まで。時計/受付は合成条件で、実ゲームの許容幅を示さない。入力受付前後の等号/+1ns/重複拒否はworld単独でも確認する。

## 16ケース

全caseは通常1-1のPAUSEから公開startする。方向入力数はresume/PAUSEを含めない。正例では商品観測後の追加方向入力0・PAUSE1・最終PAUSE画素を要求する。正常の最終位置は回転後のG、world変位数3・開扉1・掘削0、遠回りはworld変位数5・開扉1・掘削1。

| ID | 入口/扉 | 追加条件 | 方向入力 | world終端/商品 | PAUSE/理由 |
| --- | --- | --- | --- | --- | --- |
| N-W | north/木 | 基準 | 4 | G / VISIBLE | 1 / GOODS |
| N-I | north/鉄 | 基準 | 4 | G / VISIBLE | 1 / GOODS |
| E-W | east/木 | 基準回転 | 4 | G / VISIBLE | 1 / GOODS |
| E-I | east/鉄 | 基準回転 | 4 | G / VISIBLE | 1 / GOODS |
| S-W | south/木 | 基準回転 | 4 | G / VISIBLE | 1 / GOODS |
| S-I | south/鉄 | 基準回転 | 4 | G / VISIBLE | 1 / GOODS |
| W-W | west/木 | 基準回転 | 4 | G / VISIBLE | 1 / GOODS |
| W-I | west/鉄 | 基準回転 | 4 | G / VISIBLE | 1 / GOODS |
| DN | north/木 | 遠回り+DIRT | 7 | G / VISIBLE | 1 / GOODS |
| DE | east/鉄 | 遠回り+DIRT回転 | 7 | G / VISIBLE | 1 / GOODS |
| DS | south/木 | 遠回り+DIRT回転 | 7 | G / VISIBLE | 1 / GOODS |
| DW | west/鉄 | 遠回り+DIRT回転 | 7 | G / VISIBLE | 1 / GOODS |
| PF | north/木 | 開扉後外側ではPARTIAL、GでVISIBLE | 4 | G / VISIBLE | 1 / GOODS |
| PA | north/木 | 初期PARTIAL枠を(0,-2)へ置き、(0,-1)を保護 | 0 | 原点 / PARTIAL保持 | 1 / PARTIAL_GOODS |
| CA | north/木 | 最初の未送信MOVEで公開cancel | 0 | 原点 / UNKNOWN | 0 / CANCELLED |
| UN | north/木 | 最初の方向をworldが消費しsynth結果UNKNOWN | 1 | (0,-1) / UNKNOWN | 0 / UNKNOWN_INPUT |

開通直後はworld位置/変位数が変わらず、reportのdoor_changes/terrain_changesだけが対応する。次入力でのunit変位をworldログと実C Motionで照合する。商品優先で最後のACK MOVEが未評価の既存許可は保つ。正例のreport.movesはnormalで2または3、detourで4または5だけを許し、1少ない場合は最後の成功ACKのgoods latchと未評価traceを必須とする。それ以外のworld/report差は失敗。最後の入力までMOVED確定済みの場合だけreport位置とGの一致を要求し、未評価を移動成功と捏造しない。

PFの部分商品は入口から2セル以上離れ、入口への1歩を保護しない。PAは隣接保護に触れず保持停止が正解。CAは取消後のworld方向入力0・旧callback無効果、UNは再送/自動cleanup/次run操作0とUI freezeを要求する。正常の1PAUSE期待をCA/UNへ適用しない。
