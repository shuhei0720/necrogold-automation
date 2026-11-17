# TEST110: TEST109の4停止と再試行経路

2026-11-17（日本時間）。基準c2f7624。[通常計画](../plans/test110-device-failures.md)・[再試行設計](../plans/test110-irregular-retry.md)・[修正表](../fix-records.md)。実機改善は未確認。

## 受領・原因

8添付は4固有run/98 PNG/108記録/214論理ファイル。全CRC/安全path/内包ZIP一致・manifest/hashchain・896×414 RGBA SHAを確認した。原本・Scene・作者の実行証跡はGit外。単調時刻順8d78→9bf5→fe54→80c6は利用者4周に整合する。

| run | 停止と実証 |
| --- | --- |
| 8d78 | known-ACK LEFT後189のgold UNKNOWNを変位比較前に拒否、SCREEN17/attempt0。189commitは元visualD内約2.418秒。generic stopのDは入力窓で、ACK後visualDではない。原Motionは半端なcamera移動でUNKNOWNを保持 |
| 9bf5 | FULL210の正常UNKNOWN後、元Sceneの遠方2セルが戻るのを待ちLATE。原250は未変更Ringで完全陰性/C検査1、同prefixで元Dまで795ms。後続251〜264はUNKNOWNなので判定開始済250を捨てない |
| fe54 | 開扉後244→245は通常strict零・同完全LEFT判断。遠方DIRT→FLOORと対角bracketed DOOR→GOLDだけで入店を拒否。進行先は観測FLOOR。右の敵は左入力の妨害/死亡の実証ではない |
| 80c6 | safe PARTIAL317→321でSHOP表示が重なるpause iconが旧最良IoU.7835となりScene UNKNOWN/SCREEN17。新3×9openingは.8135/.8122で既0.8全参照を満たし、通常SceneはFLOOR/PARTIALに戻る |

## 通常4修正の作者確認

最終normal C `6e8be76ed115ba39ba52d1ca75693c0416bfec00b706da4b49442e28699d0865`、Perception `43682044cf954eda380f16b161c17b0309b649768f3085ff56c8cb88de9bc1bb`。

- ACK: 変更前の実assertion Red後、新10＋直接旧37の47件成功。元8評価/visualDとUNKNOWN無再送を保持し、変位後も金壁不明なら元anchorで新入力を止める。原178→189の限定ACK境界seedではbaselineのSCREEN/attempt0から、UNKNOWN/reason0/input3/attempt1へ。未保存の次画像/実MOVEDを作っていない。
- FULL data: 変更前Red後、新10/直接旧16の26件、追加open/edge14を含む40件成功。分類sourceと移動anchorを分離し、元D/一用/最初の適格1枠FIFO・候補優先・不正観測後のnegative拒否を維持。公開C/producerの保存→RESTART、40ms撮影と44/80/100ms workerの競合を確認。限定原210→250→251では250を新jobへ採用し、80ms worker中も250を保持して正常陰性/C採用・次PAUSE票まで確認。実PAUSE/RESTARTは未実行。
- 対角閉鎖: 変更前1method/8方向側方assert失敗から新7＋直接旧20の27件成功。最終normal Cでも新7成功。通常observe→旧票撤回→同拍新票→begin/ACK→unit MOVEDを手続き画素で確認。原244→245は同判断/strict零/新opened relation1、before0。原記録に完全beat履歴がないためRuntime再演とは呼ばない。
- pause icon: 変更前1method/1assert失敗から新7/旧066・084の11件成功。3×9zero-padding openingは観測maskの部分集合。旧raw/縦opening、全36×36/0.8、footer/zone/floor/死亡拒否を維持。全98原のO0/strictO2で321だけUNKNOWN→FLOOR/PARTIAL、他97のScene全bytes不変・profile間も全一致。新321はCの既存partial比較/通常strict零も通る。

独立担当review110_irregular_designはnormal C/Perceptionと新4moduleを読取り、P0/P1/P2新規指摘なし。レビューの実行0。Runtimeのqueued RGBA保持・実callbackは別境界であり、このnormal成功だけで完了と扱わない。

## Runtimeの実Red準備

job切替時に旧cycle.framesを消し、移送元をincoming/initial/found/recent4/pinnedだけから探す既Runtimeでは、Cが保持したqueued sourceのRGBAがrecent4外で失われ得る。必要IDを保った移送と、実Swift Runtimeの分類workerへ届くことを検査する。Runtimeはまだ `42f2f88634357083e82be64e56e6ba0806f26454e278b74782caee763c5bb3e8` のまま。

新driver/check_runtime110と実Swift/C fixtureは、元Runtimeに対する指定2assert（新profile prepare/queued frame worker）だけをRedとして資格化し、compile/環境失敗を拒否する。公開RESUMEを横断する非適格FULL sentinelでfoundを占め、適格PARTIAL→最初のFULL250→8つの実accepted framesを経てrecent4外に出る条件を作る。各caseは別process。実RGBAのhash/kernel後に分類結果だけを制御する。画像/時刻は手続きfixtureで、原runの全Runtime再現とはしない。

独立読取review110_red_fixtureはP0/P1なし、P2のcapture IDだけの排出条件を指摘。公開accepted_frames増加8＋prefix維持を追加し、単なるID飛びを前提にしない。現時点ではSwift未実行であり、標準Macのbefore-source実Redを先行する。normal2件だけを封印した36source/他34保持の中間manifestを使用し、IPAや無関係な全Runtime試験は作らない。

## イレギュラー再試行

設計/網羅/安全の3独立読取で、敵の正の証拠、最初のBLOCKEDの処理順、保存容量予約、pending候補/中断回復・schema交差の不足を検出した。正のhealthbar/body、288Bの新companion、旧profile分離、元8/D、continueとrestart各intent/outcome、有限容量予約の[契約](../contracts/irregular-retry.md)へ閉じる。まだ実装承認/試験成功とはしていない。今回の98原に死亡/被害の証拠はなく、死亡後の実menuも未受領。通常4停止を敵としてリセットしない。
