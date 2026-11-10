# 最新状態

更新: 2026-11-10（日本時間）。TEST070を3回受領しTEST071を開発中。[計画](plans/test071-observed-entry.md)。添付順と実行順が逆で、device started_ns/原画から4ae60e18→c94d9812→3c1a844dの順にユーザー説明と対応する。1回目は3商品可視/GOODS、2回目は開扉後2商品だけ、3回目は扉前停止。商品全体可視を1/3として扱い、2商品を成功や対象なしにしない。

## TEST070受領と原因

3run/全41PNG（14/14・14/14・13/13）のZIP/PNG CRC・SHA/bytes/896×414/manifest/cursor/時刻prefix/active-report一致を確認。全画像回収resolved=true。4aeは5MOVED+1開扉+商品優先UNKNOWN1、GOODS/PAUSE成立。方向入力間隔約.514〜.530秒でほぼ毎拍だがゲーム受信時刻なしで完全同期とは断定しない。

c94の原画124→125は同UP/reason5/target(0,-1)/FLOOR・同gold/全protected・strict BLOCKED。2商品/PARTIAL判定は正しい。唯一の変化は金bracket背後斜め(-1,-2)DIRT→FLOOR。旧quietの局所拒否→PARTIALを許さないgeneric safe_floor→FLOOR7/SCREEN停止。元Dの89.610ms前であり、送信失敗や時間切れではない。

3c1の原画120→121は未送信LEFT/reason6/DIRTの次セルが最新reason7/FLOORへ変化。actual CはTERRAIN_OPENED zero vector、strict BLOCKEDではない。gold/全protected不変・他は遠方FLOOR→DIRT。元Dの36.326ms前にFLOOR7で停止。商品はまだ不可視でUNKNOWNが正しい。Perception/Navの誤判定として閾値を緩めない。

## TEST071の限定修正

Controllerだけの変更を基本とする。開扉ACK直後の観測済入口FLOORへ1歩の同票では、full5/gold/全protected/origin/next床/strict BLOCKED/元IDと全期限を保持し、金壁の背後forward2/lateral±1セルだけのFLOOR↔DIRT揺れを許す。一般の3×3近傍を広げない。

未送信dig対象DIRT→FLOORは旧票を撤回し、新床full5をanchorに独立した後続strict BLOCKEDを確認してから新ID・将来拍prep50ms・model sample≥proofで判断する別回復へ。1run1回、元last_verified+12秒/旧sync/walk45/session180/16入力を保持し、未送信の開通/歩数creditは作らない。旧ID/epochの復活や送信UNKNOWNの再送は禁止。既存closed gate refreshは維持する。

新071入口/launcherは既存のlocal永続保存と全画像検証済ZIP公開を再利用。旧070原本保持・未公開runの次start/未完了の終了表示禁止・read-only300秒を維持する。API1.98.16/cap14/clientv15/全wire・ABI不変。Runtime/Ticket/Nav/Perception/各閾値は変更しない。

変更単体11件は固定070の意味的Red→Green、既存関連32件も成功。独立差分レビューP0/P1なし、22source seal/適用済み。[検証](reviews/test071.md)。新IPA/実compiler/全Mach-O/全source照合後に固定Releaseへ保存し、必ず具体的な実機試験を依頼する。未収録の入店後/新床後の画像を合成して実機成功にはしない。

## 現在の配布済み版

[TEST070/build110固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test070-build110)。code `f9bcc3bc7ec97ac4fa692bf388ffd64d79148e03`、[Mac110](https://github.com/shuhei0720/necrogold-automation/actions/runs/42818545816)変更/関連39件と限定Runtime Red→Green/6呼出を確認。[検証](reviews/test070.md)。IPA SHA `a5100f749b9f21b755292a8d5c2732743cc059fde1ac4a246c10ccca23ad1402`。実機結果は上記の1/3到達として更新、全体速度/商品認識の受入合格は未宣言。TEST071実機/実ゲームCIは未実施。

## 運用

[要件](requirements/necrogold.md#2026-11-10-明かりによる新可視地形と歩行間隔): 新照明でルート判断が必要な1〜2拍のみ許容、それ以外は毎拍。[開発フロー](development-flow.md#最新の運用方針2026-11-10-日本時間): 実機ログ→局所修正→単体/関係回帰→必要なIPA/同一性確認→実機。固定時間なし/品質安全条件不変、通常差分レビュー1回。無変更Runtime/world全体を毎回累積しない。既承認branchへ保存、生ZIP/原画/report/log/秘密値はGit外。同じiPhoneだけ、ユーザーはMacを持たず実機担当。初読3文書≤16KiB、[索引](context.md)から必要資料だけ読む。
