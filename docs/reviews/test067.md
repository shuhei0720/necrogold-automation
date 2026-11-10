# TEST067: 移動確認と入口の既知未移動

2026-11-10（日本時間）。[計画](../plans/test067-motion-confirmation.md)。TEST066は商品確認0/2。両native movement10/terminal/drained/PAUSE、1回目6送信/5MOVED+BLOCKED、2回目4送信/3MOVED+UNKNOWN。全30収録PNGのSHA/bytes/寸法/CRC/manifest/時刻・prefix一致。1回目125はexport省略、2回目は回収未完了で選択5枚不在。停止評価69/75/77/83は収録済み。未収録の画像やゲーム応答を補わない。

## 実機根拠と局所修正

1回目の約1.04秒間隔・2回目1.562/1.048/.515秒、初動約2.5秒。第1評価UNKNOWN後の第2評価に元周期1/4待ちがあり、約60ms取得間隔と重なり次拍窓を失う。第2だけ元周期1/10へ短縮し、第3は元1周期、最大3評価/元visualD/ACK・prefix/UNKNOWN無再送を維持。未収録の中間画像で早期MOVEDになるとは断定しない。

2回目69→83の説明文字等の表示変化を含む比較は、原score .52855/gap .3031・正方向9/closed+unique幾何が成立するがtexture823支持/63badで95%補助が不成立。原11関数・3画像面・全73scoreは変えず、UNKNOWN/highscore/同方向exact9/両FLOOR・UNKNOWNgoods・候補/両origin・next床/全保護なし/closed+uniqueに限り、contrast6以上の地形detailを追加証拠にする。300支持/95%/全他72候補に15pp差/2領域各100を保持。原画83は518支持/21bad/top226/right291、75/77はUNKNOWN維持。白文字のみが唯一原因とは断定しない。

1回目の最終125原画は不在、物理的な未移動原因は未特定。観測済み金bracketの同FLOOR入口・全5field/全tiles/全保護不変・ACK-known BLOCKEDだけ、1run最大1回のfresh HUD fit/将来拍/新IDを許す。旧BLOCKED event/歩数/開扉/lead/latest_verifiedを保持し、旧IDを再利用しない。UNKNOWN、非入口、DIRT/DOOR、2回目BLOCKEDは対象外。元verified12秒/45秒/180秒・16入力と取消等を維持する。

## TDD・原画比較・差分レビュー

新cadence6+元cadence8は066固定Cで13semantic failures/errors0/2.539秒、修正後14Green2.668秒。旧method8件のassertを維持し、第2の境界と対応する名前だけ新policyへ更新。不安定prefix後の同capture start再利用というfixture不備を1ns後の新画像へ直し、修正版でRed/Green両方を再確認した。

新blocked6は066固定Cで18semantic failures/errors0/2.195秒、4方向/元event全bytes/credit/lead/旧callback/元期限・予算/1回上限/freshfit/UNKNOWN・商品・取消・権限等を検証。独立レビューP1はモデル消去前snapshot欠損。追加assertを旧実装で4方向の意味的Redにし、observe内でreason6/ACTUAL_COMMIT・元model/rawを記録してから消去する。親visualDの最初tick検査は保持しprivate pendingで二重記録を防止。最終6Green2.284秒、レビュー担当の独立6Greenでもsnapshot/原点/全record bytes不変を確認。

新motion6は旧Navのpositive4方向×O0/strictO2で8semantic failures/errors0/.686秒。修正後6Green3.492秒、独立6Green3.199秒。静止/逆/2tile/8px途中/金増減/開いたgate/両状態・goods・金資格/床/局所・遠方保護/弱・flat・repeatを含む。97既知原画の元3plane bytes、114収録比較の元全73score bytes一致。判定差は066第二69→83だけ（同pairを2分類で重複記録）、他全部同じ。欠損7pairを明示し、未知評価やController全時系列再生とは呼ばない。

独立レビューの追加P1は、freshfit後に新ticketの判断が別の行先/障害物へ変わり得る限定不足。既存negative内でfitting/publication前の14変化をRedにし、元Scene/full5/全tiles・金・保護/strictBLOCKEDを再証明する。issued後DIRT→FRESHとsignature-only→tickなしbeginも2semantic Redで確認し、REFIT/ISSUEDのprivate許可をactualbeginまで保持、accepted画像ごとに再証明し、不成立は未送信撤回。beginは重いMotionを再実行せず、直列Cが証明した最新capture IDだけを定数時間で検査する。finish時は許可を撤回し、PAUSEへ制限を流用しない。6method/CI39の件数は維持。同じ独立レビューの中で修正確認し、最終6Green3.373秒。issued負例はPAUSE発行/begin/ACK/実PAUSE画像による停止まで確認し、進捗credit不変。最終Native/runner/docsに残P0/P1/P2なし。新18+旧関連21のdevice39件を予定し、公開原fixtureのCOREと新自前COREを実patched sourceへ束縛する。無変更Perception/Runtime/world/クライアント・private原画をCIへ累積しない。YAML/publisherは不変。

## 封印・配布待ち

Controller SHA `da6f3a2ddda72ccbd78430146a5eb3127db744a6ad43b9021366ce39dfa3da5d`、Navigation SHA `9f54c4dafe402c1176286b55283cfe5e63c7838db4ea42b4f6d02d487de82984`、manifest SHA `1864e63ca4346ad14f0cf9f138b7eda5c2241740a5d3f4df3b2ed9a146da278b`。baseline0aからこの2assetだけ変更し、他20/API15/cap13/ABI/client/R12原40/G1を維持する。固定upstream6e25へG1+G2を適用済み。Mac/実compiler/実IPA/全Mach-O/全sourceは完了後追記する。TEST067の実機成功は未確認。[配布と実機依頼](../status.md)に従う。


## 最終Mac104・実配布物

code `9335d0040290d592355df0860e32e45c6fea6f42`、[Mac104](https://github.com/shuhei0720/necrogold-automation/actions/runs/42785580107) device成功。新IPA/build104（0.3.4/top.ebato.loopctrl）SHA `db02df8fb6f900a755442478a8c0557401bcc7ae53f5ae5ac2f9f2c15048aeac`、外ZIP SHA `eece1e457a64fea8bcc1a72749adcbedc133b55a00484a27235f83e84655ff51`。

host39の全実行ID/生ログ/command/0fail/error/skip/xfailと選択/省略理由、ABI実query、22seal前後が実IPA sourceと一致。baseline0aからController/Navigationだけ変更、他20/R12原40/G1不変。実4C/5Swift/6RSP/PBX/raw compiler引数を照合、Perception/Nav strictO2・Controller/BeatO0・SwiftOnone/HOST macroなし。全9Mach-Oで従来103+067の計104marker非混入。通常device laneの単体/関連回帰のみで無変更のRuntime/world全体は実施していない。

build-source全504tracked bytes/path/CRC一致、7,366,797bytes/SHA `d756d45fd14f95f03fda056f62ffae31cf9661c3c67ef22d0a5c92a49091e2a6`。最終sourceとの差分を文書3件に限定して検査し、固定Releaseのsource.zip/SHA256SUMSへ保存。固定公開後は匿名GETとSHAで両assetを確認する。raw/画像/ログ/receiptはGit外。商品到達・歩行間隔は新しいTEST067の実機で評価し、未収録応答や合成試験から成功を断定しない。[実機依頼](../status.md)の新IPA更新/再起動/Start Serverから開始し、終了後runtime/test-067全ZIPを依頼する。
