# 最新状態

更新: 2026-11-10（日本時間）。TEST070を開発中。最新指示は「移動で明かりの範囲が広がりルートを読み直す必要がある場合は1〜2拍許容。それ以外は毎拍歩行」。[要件](requirements/necrogold.md#2026-11-10-明かりによる新可視地形と歩行間隔)・[計画](plans/test070-cadence-lighting.md)。新地形でも判断が次拍までに終われば待ちを挿入せず、未観測/UNKNOWN/商品/保護/元期限の安全条件は維持する。

## 実機の根拠

[069受領解析](reviews/test069-received.md)。test-068内fc37とtest-069の1357/b404の3run/全50PNGをSHA/bytes/896×414/CRC/manifest/cursor/prefix/active-reportで照合。3本とも3商品が可視、画像20/20・16/16・14/14保存完了。自動GOODSは1/3で、他2本は商品が見えてもSCREEN。可視到達と自動判定完了を分ける。

周期約.52秒に対し1.04/1.57秒の入力間隔。fc37のUP→UPでは新露出0でも約1.05秒待つ。1357 DOWN→LEFTは新露出5cell/方向変更があり約1.04秒。新照明によるルート判断と、既知通路の単なる確認遅れを区別する。未収録途中画像は補わず、ゲーム受信時刻なしで入力取りこぼしゼロと断定しない。

現Controllerは未確定時の3回目を元1周期後まで待つ。加えてC再検証12.556msで10ms送信窓を超過、別箇所は準備済み票のSAME再予約前後で診断作業が時間を使いCepoch再利用の期限を失った可能性がある。元10ms窓は延長しない。

## TEST070の変更範囲

同一ACK-known MOVEの画像評価を最大8回へ。2〜7回目は直前評価開始から元period/10以上、8回目は初回+元1周期以降も要求し、旧最終機会を残す。strict proofが早く得られれば元次拍へ進む。UNKNOWNを実移動扱いせず入力の再送は増やさない。元before/prefix/source/phase/visualD・12/45/180秒/16入力・GOODS/取消を保持する。

Runtimeはcoherent C snapshot/現在source pinを先に保持し、重い画像参照収集/整列/退避を前面証拠の再利用/入力後へ移す最小変更を実装中。新しい未検証画像を飛ばして旧ticketを送る処理はしない。正式なactual Runtime Red→Greenは同Macジョブで固定旧実装/新実装を順に検査する。local Swift環境がなく、模擬時計と実機成立を区別する。

新native-walk-v15/API1.98.16-ngg2/cap14でattempts≤8を識別。旧v14はAPI.15/≤3、v1〜13はAPI.14/≤3、同UUID/clock/export/cursor回復を保持。ABI/layout不変。Perception/Navの商品/地形閾値は変更しない。商品認識の看板/HUD問題は別課題として保持。

TEST069のiSH永続保存・全画像検証後のZIP一括公開を再利用し、TEST070のlocal namespace/ZIP名/launcherを分ける。旧069原本は保持。未公開runの次start/完了前の終了表示は禁止、独立read-only300秒と取消境界は維持する。今回の単体/関係回帰・独立レビューと必要な新IPA/同一性照合後に固定Releaseへ公開し、必ず具体的な実機試験を依頼する。

## 現在の配布済み版

[TEST069/build108固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test069-build108)。code `6180eacf3bec8c9ecb0e65c889339f9483ef383d`、[Mac108](https://github.com/shuhei0720/necrogold-automation/actions/runs/42804504968) device50件成功。[検証](reviews/test069.md)。IPA SHA `47ae26f5d512abd8bf0fefc8fa85707fc50d9e0713a754a07a55680694f77dda`。最終sourceはcodeから文書3件だけ異なり実装同一。受領069の可視到達3/3・画像全回収と、自動GOODS/毎拍歩行の未達を両方記録する。TEST070の実機/実ゲームCIは未実施、速度合格は未宣言。

## 運用

[開発フロー](development-flow.md#最新の運用方針2026-11-10-日本時間): 実機ログ→局所修正→単体/関係回帰→必要なIPA/同一性確認→実機。固定時間なし/品質安全条件不変、通常差分レビュー1回。無変更Runtime/world全体を毎回累積しない。既承認branchへ保存、生ZIP/原画/report/log/秘密値はGit外。同じiPhoneだけ、ユーザーはMacを持たず実機担当。初読3文書≤16KiB、[索引](context.md)から必要資料だけ読む。
