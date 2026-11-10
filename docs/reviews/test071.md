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

固定upstreamへG1を適用し、レビュー済み22sourceをseal/適用済み。新IPA/実compiler/全Mach-O/完全sourceは下記で照合済み。固定Releaseへ保存し具体的なTEST071実機試験を依頼する。商品可視到達と既知通路の毎拍について新071の実機合格は未宣言。


## 最終Mac112と配布物

code `6cab2f625b17bedb3cc8540ca4d8f717a3dc68d5`、[Mac112](https://github.com/shuhei0720/necrogold-automation/actions/runs/42832680834)成功。実IPA0.3.4/build112/top.ebato.loopctrl/min16.0、17,589,531bytes/SHA `88c2ed0987dddf6514dad10a2d953f0418b04876b9192feaf2c83507b64a8144`。unsigned artifact13773221174は17,856,970bytes/SHA `8ddc9a7f1c6e5baf9006ff90274f6f26dc76006b3ed5455d960a68ca7846af39`、validation13773490850は1,194,333bytes/SHA `283de21559d481f27889646a73d36b6a3340eab8aad502f5e69a545233f886e2`、host13772052519は7,698bytes/SHA `f581ccba9a0b7fc6d01085ee502ad8ad08384b55319d8bb73c207dc06a2423e6`。run/head/branch・全outer bytes/SHA/CRCを照合。

新11+関係9+selector3の実host23/8区分、全実行ID・生ログ・fail/error/skip/xfailなし、ABI/22source前後/3production client moduleのHEAD Git blob/path/SHA/delegate同一を確認。追加の正規sealed Cでdig/open2+ABI1もGreen4.176秒、selector3Green.013秒。nativeはController1変更・他21/R12原40/G1不変、API16/cap14/v15/ABI維持。manifest SHA `6cb240a5f77925c402cf6b452039aee66ad9277f7131f483274598dbf80a0ffc`。

既存の限定Mac Runtime境界を新Controller objectsへ結び付け、実証跡のTEST070名称/pathsを維持した。固定6180旧Runtimeの意味的Red1→production新070/旧prefix・cancel・controller・deadline_equal4境界/identityの6呼出Green。新床の実機後続画像を合成して到達成功へ置き換えない。

実compiler4C/5Swift/6RSPのraw log/PBX/引数とstrict-O2-v2 profile一致、Perception/Nav strictO2・Controller/BeatO0・SwiftOnone、HOST macroなし。全9Mach-O/118禁止marker非混入、app/runner API16/cap14/arm64を確認。build-source全532tracked bytes/path/CRC、7,469,542bytes/SHA `59cacbec72185a53c8cb046491d88a436e8439da28ade0b49bdd642a880e228d`。5種の実照合は各1回で成功、Git外receiptへ保存。

最終sourceはstatus/本review/台帳3文書だけを閉じ、全製品bytesをビルド時と一致させる。固定Release `test071-build112`へ検証済みIPA/完全source/SHA256SUMSを置き、匿名GET/全SHAを確認する。新通常1-1の金壁可視ポーズからまず2回、全商品の可視/停止位置/既知通路の毎拍と新地形の待ちを実機で確認し、自動`runtime/test-071-<run_id>.zip`全回分を必ず依頼する。[手順](../status.md)。実ゲームCI/新071実機の成功は未宣言。
