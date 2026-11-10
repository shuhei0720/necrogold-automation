# TEST069: 回収完了と未送信開扉の再観測

2026-11-10（日本時間）。[計画](../plans/test069-collection-gate.md)。ユーザーの最新指示は「また画像全部保存し終わってない。これやめろ」。通常一回で全画像と返却ZIPを保存し、未完了を終了と呼ばない。

## 受領と原因

TEST068 ZIP 3,263,584bytes/SHA `ac50e2c7c4ba25ec1848a096bbf3a30e8e8eb1563ea68deb687a983bf2e32ce5d`。run cf5147ae1c8d428a8ad9e84eee1fffdc、report SHA `ab0968c245d9c1ce3b5714a1f0aa7b17f99ff3fd1e8b3635d8887ce782228f58`。ZIP path/重複/CRC・全12PNGのSHA/bytes/896×414/全chunk CRC・manifest/時刻prefix・active/report一致を確認。missing078/080/091/093、093part262,144bytes。残877,583bytes。追加回収は依頼しない。

4実MOVED、開扉/商品0。id9は未送信、source130/latest133は同LEFT/reason5/target(-1,0)/DOOR、gold2/局所/全保護不変。遠方(7,0)FLOOR→UNKNOWN、(9,1)DIRT→STONE。motionはUNKNOWN、zero score .508988/差 .32555、強構造支持も95%未達。Dの14.751ms前にquiet拒否→safe_floorでないDOOR→SCREENとなった。開扉失敗/時間切れではない。未収録画像は補完しない。

回収manifest→最終chunk87.728秒、RPC65回(結果59)/エラー0、RPC23.596秒に対し呼出間64.132秒。109 atomic/14,443,914bytes、受領3,250,611bytesの4.44倍。各fsyncの個別寄与は未計測だが保存区間の待ちが支配的。前068の再開時重複write省略は初回負荷を改善しなかった。

## 設計と検証の境界

iSH local spoolに従来のdurable journal/part/PNGを保持し、全画像検証後に現在runだけのZIP_STOREDを作る。共有側partへ一括copy、SHA→rename→再SHA→local receipt。公開未完了は新startより先に処理し、receiptだけでなく実共有ZIPを確認。未開始の接続失敗は回収未完了runと区別する。前run/設定/秘密値をZIPへ累積しない。

未取消・安全terminal/drained/入力確定のpaged回収だけ独立300秒。元game180/walk45/sync12・unsafe/legacy/既取消cleanup不変、回収中はread-only。同一未送信開扉の新観測は1run1回、旧UNKNOWNのcredit/再送なし、独立strict BLOCKEDとfreshfit/別ID・元予算必須。Nav/Perception閾値とRuntime/Swift/wireは変更しない。

新単体の意味的Red→Green、関係回帰と保存/公開境界を確認し、無変更の全world/Runtimeを既定で再実行しない。独立レビューではclock_idとrun_idの別識別、resolved≠全画像完了、未開始失敗の再接続、取消済の長時間回収、native取消のwrapper伝播を重点確認する。最終件数・レビュー修正・seal・ビルド/配布実体は完了後に記録する。現時点で069実機の商品/速度/保存合格は未確認。


## TDD・独立レビューの修正

新gateは元実装で4方向ともSCREEN停止の意味的Redから実装し、最終8件+関連30件Green。raw130→133はUNKNOWNを保持し、実Sceneのfixed gate geometry条件は成立、133selfはtexture eligibilityのみ。独立pair以後の未来画像/実fresh modelは未収録なので、公開procedural fixtureと実機続行を区別する。追加の実sealed回帰4件（通常cadence2/closedgold1/実C ABI1）Green、22source前後一致。

client新11件は旧90秒/残game期限・unsafe manifest・取消済予算・外部取消handoffで意味的Red→Green。最初のloopback拒否は環境errorとしてRedに数えず、実暗号HTTPが通る環境で正式実行した。保存/公開新15件はresolved直後/receipt前・copy/rename中断、完成画像/offset/SHA/PNG不一致、currentrun限定、旧run保持、journal/画像snapshot変化、distinct clock、CLI結果hook/取消境界を確認する。

独立設計レビューとfresh安全レビューで、clock_id≠run_id、resolved≠全画像証明、no-start再接続、未検証snapshot差替え、signalhandoff、取消済300秒付与、receipt保存中取消を修正。取消履歴を物理drain証明へ混ぜると完成済み取消runが永久未公開となるP1も検出し、300秒許可だけを別条件へ分離した。現在の取消は停止/未完了、過去の取消runで全画像が揃っていれば次回publish-only可能とする。最終差分のP0/P1なし。wrapper15件は最終0.562秒Green、collection変更3件Green、native38件/追加sealed4件Greenを照合。実ゲームの成功は未確認。

## 封印と選択

nativeはControllerのみ変更、SHA `822af1b1e509cb72ef556223b3828e217d35eaac5564f8e7ed8b3c723f71c5af`、他21/R12原40/G1不変。manifest SHA `0b17836112d250fcae3b9dbca6e13494fefa3a78cc3b2b58edcd880bcf6188a2`。API1.98.15-ngg2/cap13/clientv14・ABI1/Scene23864/Status192/Event128/MotionWait48/RecoveryStatus456、Runtime/Swift/wire不変。

device CIは50件を選択（native16/client31/selector3、新34+関連13+selector3）。全過去suiteを累積せず、今回の入力再観測と回収/出版境界だけ検査する。native_walk/test069の実driver import・HEAD Git blob/SHAを前後照合し、未変更Runtime/world/全RPCは実施しない。実IPA/実compiler/全Mach-O/完全sourceの証拠はビルド後に記録する。


## 最終Mac108と実配布物

code `6180eacf3bec8c9ecb0e65c889339f9483ef383d`、[Mac108](https://github.com/shuhei0720/necrogold-automation/actions/runs/42804504968)成功。実IPA/build108、version0.3.4/top.ebato.loopctrl、17,588,938bytes/SHA `47ae26f5d512abd8bf0fefc8fa85707fc50d9e0713a754a07a55680694f77dda`。unsigned artifact13758128059、17,852,780bytes/SHA `a02a0b4a32c8380bd23b2046d8b9652d2b3b0581fd37ac235de2171003de71c4`。validation13758611692、158,393bytes/SHA `17ddc400881c11b71fc03dbf5e5b90be9af3843e0ccb9bd3f57f6bdedc098b83`。host13757926283、11,552bytes/SHA `3e0bfdbb2ec1beb6d261bbe0c3b24746e5ac9e775dbc8b5b789deb35cd3b67f7`。GitHub run/head/branch・全outer SHA/bytes/ZIP CRCを確認。

host50/12区分の全実行ID/生ログ/command/0fail/error/skip/xfail、ABI実query、22seal前後を実IPA sourceへ結びつけた。native_walk SHA `16479a856007a237d898f6d88ea5fba6bc3011c80c38302e56eb369a3611a0a7`、wrapper SHA `b1ebfb676c08aaada11f1cde9b52639b381c62fbe6ec486db0484c0954482e1d` は実driver import/HEAD Git blob/SHA前後一致。API15/cap13/v14、fixture module一致。独立設計・fresh安全の最終P0/P1なし。

実4C/5Swift/6RSP、PBX/生compiler引数/log/profileを照合。Perception/NavはstrictO2、Controller/BeatO0、SwiftOnone、HOST macroなし。全9Mach-Oの109禁止marker非混入、app/runner API15/cap13/arm64一致。nativeController1変更/他21、R12原40/G1不変。無変更Runtime/worldの全体再実行は行わず、実ゲームCI/iPhone受入の成功を推定しない。

build-source全517tracked bytes/path/CRC一致、7,421,202bytes/SHA `7080e29e181d7349801d1ab88dac4ed8291c2b662e607653473cf05bd35fd72f`。最終sourceはこのcodeからstatus/本review/台帳の文書3件だけ異なり、全実装/launcher/testsは同一。固定Release test069-build108のIPA/source.zip/SHA256SUMSへ公開し、匿名GET/SHAで確認する。生受領資料/証跡はGit外。069の扉突破/商品全体/保存完了は実機未確認で、[status手順](../status.md)の新IPA更新/再起動・Start Serverから新1-1をまず2回依頼し、自動ZIP全run分を返してもらう。
