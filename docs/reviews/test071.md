# TEST071: 開扉後の入店と新しく見えた床の再確認

2026-11-10（日本時間）。[計画](../plans/test071-observed-entry.md)。baseline `acfeb7a210d2a67a0ae509ec25417650dc3aa3c2`。実機を主にして、今回の2停止に絞ったController修正・単体/関係回帰・必要な新IPA作成を行う。

## 受領資料と対応

添付順は実行順ではない。device started_nsの昇順で4ae60e18→c94d9812→3c1a844dを1〜3回目に対応させ、原画とユーザー説明を照合した。ZIPは順に4,117,881/4,145,661/4,186,718bytes、SHAは`46e710f6c02202a0def5a71f6d5af549690b2986705f6a1984c382f90b8f9f99`/`dae209d547903a7461ce83196056cacbc9b3c584c2b9c09ae4944499a6c34c4d`/`b9099392a4d94b3316679ca68100c24b1e99d2df24ea27c0896c52ca537346e0`。3run/全41PNG（14/14・14/14・13/13）のZIP/PNG全chunk CRC・SHA/bytes/896×414/manifest/cursor/時刻prefix/active-reportを照合し、全回収resolved=true。raw/派生資料はGit外。

4aeは5MOVED+1DOOR_OPENED+商品優先UNKNOWN1評価、原画153に3商品が見えGOODS/PAUSE成立。方向入力間隔.514〜.530秒でほぼ毎拍だが、ゲーム受信時刻はなく完全同期とは断定しない。

c94は5MOVED+1DOOR_OPENED。原画125は2商品のみで3品目は未観測、PARTIAL判定が正しい。同UP/reason5/target(0,-1)/FLOOR・同gold/全protected・strict BLOCKEDなのに、金bracket背後斜め(-1,-2)DIRT→FLOORの1変化でquiet拒否、FLOOR7/SCREEN停止。observeはD−89.610msで送信失敗や期限超過ではない。

3c1は4MOVED/開扉0。原画120→121で未送信id12のLEFT/reason6/adjacent DIRTがLEFT/reason7/FLOORへ見え直し、actual CはTERRAIN_OPENED zero vector。他は遠方(10,1)FLOOR→DIRT、gold/全protected不変。D−36.326msのFLOOR7/SCREEN停止で商品は未可視。未送信なので開通creditを与えず、Perception/Nav閾値を緩めない。

## 変更と不変条件

開扉ACK直後・未入店・両PARTIAL・同reason5/FLOOR票だけ、forward2/lateral±1かつ直前が両SceneでGOLDのセルに限りFLOOR↔DIRT揺れを許す。full5/gold/全protected/origin/next床/strict BLOCKED/元IDと全期限は不変。一般近傍を広げず、2商品をGOODSへ昇格しない。

未送信reason6/DIRT→同unit方向/targetのreason7/FLOORは旧票をnot_sentへ永久撤回する。最新床をanchorに独立・非交差current-prefixのstrict BLOCKED/full5/gold/全protectedを確認し、新ID・将来拍prep50ms以上・model sample≥proofで発行する。既存private gate_refreshの状態を共有するがclosed gate predicateは保持し、terrainのactive/1run1回usedは別管理。latest_verified+12秒/旧sync/walk45/session180/16入力を保持し、旧epoch/ID・送信UNKNOWNは復活しない。実変位/開通/歩数creditは増やさない。有効なHUD modelを再利用し形式的な再fitを省く。

native変更はController1件だけ。Runtime/Ticket/Nav/Perception/各閾値、API1.98.16/cap14/clientv15/wire/ABIは不変。新071のmodule/launcherは既存publicationへ番号を渡すだけで、local永続原本・全画像/ZIP照合前の終了/次start禁止を維持する。

## 検証と限界

新shopは旧070の意味的assertion Red（compile成功/errors0）から5メソッドGreenへ。4方向×両側×両palette方向の16正例、開扉ACKなし/別方向・保護/次床/金/ITEM/元期限などの拒否を含む。新shop5と旧closed refresh8/gate0646/door0666/shop0664/cadence0708の関連37メソッドGreen19.294秒。新terrain6メソッドも固定070で4方向の意味的Red/errors0→全6Green4.626秒。20trigger境界、観測/発行後12種、商品/取消/owner等12subcase、独立proof・HUD/model/prep50・元budget・旧ID・実第二gateで1回上限を確認した。新11と既存関連32は同じ凍結Cで成功。

独立差分レビュー1回の最終結果はP0/P1なし。Controller `a2ee91abe382d0d6a242385aead9d3f45382b341d5941afe23238bac96ad9634`、shop `7bb5cd3aa2ef33d248624dafb72b1c177f3ee43f74ed8f5ee1a84193ea9f2a66`、terrain `8f2275fcb536991ab32eef2c051dda47227675515482ea626c16f6909ae551bd`を凍結し、独立proof/一回上限/元budget/旧callback境界と文書/host選択まで確認した。模擬Cの継続を未収録の実機画面や商品到達成功として扱わない。今回の入力権限変更に関係する既存Mac dispatch/取消境界だけを新Cと結び付け、全Runtime/worldを累積しない。

固定upstreamへG1を適用し、レビュー済み22sourceをseal/適用済み。新IPA/実compiler/全Mach-O/完全source照合後、固定Releaseへ保存し具体的なTEST071実機試験を依頼する。商品可視到達と既知通路の毎拍について新071の実機合格は未宣言。
