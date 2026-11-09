# TEST060 合成worldと時刻の固定期待

状態: 実装前の期待。2026-11-09（日本時間）。[計画](../plans/test060-continuous-admission.md)。原059の未来画像ではなく、独立の地形/時計/受付でproduction Cを検査する。既存Swift world16は変更しない。

## 地形と終端

north基準はplayer(0,0)、gate(0,-5)、床(0,-1)〜(0,-4)、金壁(-2,-5),(-1,-5),(1,-5),(2,-5)、追加の金壁(-2,-4),(2,-4),(-2,-3),(2,-3)。入口内側の部屋と商品棚3枠は既存SmallShopWorldの定義をgateへ平行移動する。east/south/westは全地形を90/180/270度回転し、価格3列はworld X方向へ横並びとする。±2列を2セル延ばすのはDOWNでも開幕金壁と移動のtextureがHUD外で観測できる地形定義であり、perception/UNKNOWNを緩める変更ではない。

Git外の実装前studyで、8地形×HUD7位相は原寸RGBAのFLOOR/gold候補/商品UNKNOWN、6操作のNav/Motion/商品をO0/strictO2で全確認。1行だけの金壁延長やDOWN直線距離5最小壁は不成立だったため、この固定地形へ限定する。

| case | 方向 | 扉 | world方向入力 | world移動 | 開扉 | 商品/終端 | PAUSE |
| --- | --- | --- | --- | --- | --- | --- | --- |
| N-W | UP | 木 | 6 | 5 | 1 | gate(0,-5)/VISIBLE | 1 |
| N-I | UP | 鉄 | 6 | 5 | 1 | gate(0,-5)/VISIBLE | 1 |
| E-W | RIGHT | 木 | 6 | 5 | 1 | gate(5,0)/VISIBLE | 1 |
| E-I | RIGHT | 鉄 | 6 | 5 | 1 | gate(5,0)/VISIBLE | 1 |
| S-W | DOWN | 木 | 6 | 5 | 1 | gate(0,5)/VISIBLE | 1 |
| S-I | DOWN | 鉄 | 6 | 5 | 1 | gate(0,5)/VISIBLE | 1 |
| W-W | LEFT | 木 | 6 | 5 | 1 | gate(-5,0)/VISIBLE | 1 |
| W-I | LEFT | 鉄 | 6 | 5 | 1 | gate(-5,0)/VISIBLE | 1 |

操作1〜4は各1歩、5は閉扉を開けるだけで変位0、6は入口へ1歩。商品遮蔽は閉扉/外側ではUNKNOWN、入口に進入すると3商品の価格までVISIBLEとする。商品後は追加方向入力/購入0、holding PAUSE1。最後のgoods latchで未評価ACKを許す場合は既存契約どおり、実world移動5に対してnative4だけを許し未評価traceを必須とする。それ以外の差は失敗。

## 正常な時間条件

world時計のperiod520ms、lead150ms、受付±10ms・同拍重複拒否は独立の合成条件。C target/Decisionからepoch/受付を更新しない。各操作のworld beat indexを保存し、最初をbとして厳密に[b,b+1,b+2,b+3,b+4,b+5]を要求する。異なる拍であっても[b,b+2,…]なら失敗。

取得〜判断Lは60/70/80/85ms、取得完了後次取得開始まで5ms、cadence C=L+5ms。準備（AX/queue合計）は20ms、synthACKは280ms。これらはテストの成功域であり実機保証ではない。pipelineはcapture開始/終了・decode/analysis/commitを別の時刻として扱い、capture中のinflight/prefix交差や制御queueがsynth中に停止する条件をモデル化する。未来の完了を先に返さない。

各Lについてcapture位相を、world epoch基準で0、1ns、floor(C/2)、C−1ns、(C−(200ms mod C)) mod C+1nsの5値へ固定する。8地形×4L×5位相=160終端実行で、全入力数/開扉/位置/商品/PAUSEと連続拍を要求する。コマンドsourceの情報は受付/移動oracleへ渡さない。通常fixtureのframe cadenceを都合よくcommandへ同期させない。

別の公開C admission試験では同じ4L/C/Pの全1ms位相を走査し、元の次拍・未予約待機・最新適格sourceからの予約・実beginが元10ms窓内であることを確認する。全1ms位相試験と160終端worldの件数を分ける。

## 明示した停止条件

worldの3歩目入力ACK後、nativeの3歩目MOVED確認から第4予約前にだけ次を注入する。第4以後を別拍で救済しない。

| case | 入力条件 | 期待 |
| --- | --- | --- |
| SLOW-CAPTURE | 最後の古い取得開始はB−200ms−1ns、L160msでB−40ms−1nsに判断。5ms後の次取得はB−35ms−1ns開始、判断はB+125ms−1ns | 第4方向入力0、world/native移動3・開扉0・商品0。元D=B+10msでlate停止、保持PAUSE1。GOODS/BEAT未達で正例に数えない |
| SLOW-PREPARE | 適格SceneがB−20msで判断、AX/queue60msでmain開始B+40ms | 第4方向入力0、world/native移動3・開扉0・商品0、元Dを越えて送信しない。late停止/保持PAUSE1。正例に数えない |

停止後の回収は新しい実captureでPAUSEを確認する。取消/UNKNOWN/隣接PARTIAL・木鉄/各方向/迂回掘削は既存world16でも全回帰する。この新worldがcameraの1rawpx揺れや実ゲームの受付を再現したとは扱わない。原54→55 UNKNOWNは別の原画像回帰で不変を検査する。
