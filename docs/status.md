# 最新状態

更新: 2026-11-10（日本時間）。TEST070/build110を検証。最新指示は「明かりで新地形が見えルートを読み直す必要がある場合は1〜2拍許容、それ以外は毎拍歩行」。[要件](requirements/necrogold.md#2026-11-10-明かりによる新可視地形と歩行間隔)・[計画](plans/test070-cadence-lighting.md)・[検証](reviews/test070.md)。新地形でも次拍までに判断できれば待ちを挿入せず、未観測/UNKNOWN/商品/保護/元期限の安全条件を保つ。

## 実機根拠と変更

[069受領](reviews/test069-received.md)の3runで商品可視到達3/3・50PNG全回収、自動GOODS1/3。fc37 UP→UPでは新露出0でも約1.05秒待つ。1357 DOWN→LEFTは新露出5cell/方向変更があり約1.04秒。新照明による経路判断と、既知通路の確認/準備遅れを分ける。途中の欠落画像やゲーム受付時刻を補完しない。

Controllerは同一ACK-known MOVEの画像評価を最大8回へ。2〜7回は直前start+元period/10、8回は初回+元1周期も必須とし旧最終機会を維持。strict proofが早く得られれば元次拍へ進む。before/prefix/source/phase/visualD・元12/45/180秒/16入力・UNKNOWN synth無再送/商品優先を維持。

Runtimeはcoherent C snapshot/現在source pinを先に保持し、重い画像整理をCepochによる準備済み前面証拠の再利用/期限内dispatch後へ移す。pin上限20・取消/世代/owner/前面/最新Scene final begin・poison/drainは保持。snapshot identityでACK後の新状態を古いretentionへ戻さない。未検証latest画像を飛ばさず、10ms送信窓を延長しない。

新v15/API1.98.16-ngg2/cap14でattempts≤8を識別。旧v14=API.15/≤3、v1〜13=API.14/≤3、同UUID/clock/export/cursor回復は不変。ABI/layout/Perception/Nav不変。商品可視でも自動GOODSにならない看板/HUD問題は別課題で残す。

TEST069のlocal永続保存/全画像検証後の一括ZIP公開を再利用し、070のnamespace/root/filenameを分けた。旧原本保持・未公開runの次start/完了前の終了表示は禁止。独立read-only300秒・取消境界を維持。

## 検証と配布

code `f9bcc3bc7ec97ac4fa692bf388ffd64d79148e03`、[Mac110](https://github.com/shuhei0720/necrogold-automation/actions/runs/42818545816)成功。変更/関連39件、固定旧Runtimeの対象assert Red→新Runtime/関連4境界/identityの6呼出Green。全host実行ID・3client HEAD blob・22seal・実4C/5Swift/6RSP/strictO2・全9Mach-O115禁止marker非混入・全526build-source bytes/path/CRCを照合。native4変更/他18・R12原40/G1不変。全Runtime/world/実ゲームCIは未実施。

実IPA0.3.4/build110、17,588,671bytes/SHA `a5100f749b9f21b755292a8d5c2732743cc059fde1ac4a246c10ccca23ad1402`。独立レビューP0/P1なし。最終sourceとの差分は文書3件と旧schema試験1件の2行だけで、製品/driver/native/launcherは同一。実機での毎拍/到達/GOODS改善は未宣言。

[新IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test070-build110/LoopCtrl.ipa)・[完全source ZIP](https://github.com/shuhei0720/necrogold-automation/releases/download/test070-build110/source.zip)・[SHA256SUMS](https://github.com/shuhei0720/necrogold-automation/releases/download/test070-build110/SHA256SUMS.txt)。固定Releaseへ公開、匿名GET/全SHAまで確認する。

## 実機依頼

SideStoreで新IPA更新→LoopCtrl完全終了/起動→Start Server、いつものVPN/ディスク設定。source展開後、test_070.shのあるフォルダを選択。新通常All Zones 1-1の金壁可視ポーズから実行する。

```sh
mkdir -p /mnt/necro_test070
mount -t ios . /mnt/necro_test070
cd /mnt/necro_test070 && sh test_070.sh
```

歩行中ゲーム前面、自動ポーズ後約5秒でiSHへ戻り前面のまま`TEST-070: 終了。画像とZIPの保存・照合が完了しました。`を待つ。まず新しい1-1を2回、既知通路の毎拍・新地形での必要待ち・商品全体の可視/停止位置・保存完了を確認し、自動`runtime/test-070-<run_id>.zip`全回分をそのまま返してもらう。回収済み069の再実行は不要。

## 運用

[開発フロー](development-flow.md#最新の運用方針2026-11-10-日本時間): 実機ログ→局所修正→単体/関連回帰→必要なIPA/同一性確認→実機。固定時間なし/品質安全条件不変、通常差分レビュー1回。無変更Runtime/world全体を毎回累積しない。既承認branchへ保存、生ZIP/原画/report/log/秘密値はGit外。同じiPhoneだけ、ユーザーはMacを持たず実機担当。初読3文書≤16KiB、[索引](context.md)から必要資料だけ読む。
