# TEST079: TEST078追加受領と金壁露出・掘削予約

2026-11-11（日本時間）。baseline `5e9a9bbdb0e16157c995d04e42066006b20c8313`、製品はTEST078/build126。前batchの[受領記録](test078-received.md)と混ぜず、今回の3ZIPだけをGit外received078b/test079b-*へ保存。[計画](../plans/test079-gold-reveal-dirt.md)。通常局所修正、独立レビュー1名。

## 実受領

3ZIP/56選択PNG（20/16/20）を全SHA/ZIP・PNG chunk CRC/PIL verify-load/896×414/manifest全offset・hash・cursor/prefix/strict API16 schema/_load/実publicationへ照合。選択PNGのnative capture行欠損0、全PAUSE/resolved/terminal/drained・回収完了。capture failure/timeout0、host error/cancel0/status40回最大1.300秒。全画像bytesは3,665,700/4,004,551/3,821,038で元4MiB以内。省略原画を補完しない。

| 実順/run | ZIP bytes / SHA256 | restart | MOVED/方向入力 | 開扉 | 終了 |
| --- | --- | --- | --- | --- | --- |
| 1/17a58a71 | 3,893,930 / `e1ac7b45709a72d4ecbf4b64cb03b2dd54170d453c138d01dbc38372abf00495` | 3 | 5/6 | 0 | movement |
| 2/b73d5d78 | 4,269,557 / `485d9231ecd11b37c6001e043e8690004adaaaee876d0ac489e8819ea332526f` | 3 | 5/7 | 1 | goods |
| 3/388f19c6 | 4,096,912 / `005479b01c7ae9a1be72d965b09689a0c21e7204ff7322527093ce6a778e58be` | 4 | 6/6 | 0 | screen |

started_nsによる実順で、添付順と異なる。rootが2の原245で3商品と価格8/13/50を視認、全商品到達1/3。対象アイテムの有無までは認定しない。2の別cmd10はgateがD+2.538msでtoo_late、次拍で回復し商品へ到達した。今回の最終失敗2件とは別。

入力間隔は1が.506〜.527秒、2は1.040/1.046秒の空き2区間と.515〜.525秒、3は1.036秒の空き1区間と.513〜.521秒。送信間隔を実ゲーム受付や恒久毎拍/人超え合格にしない。

## 1回目: 露出した閉扉で実1歩がUNKNOWN

cmd13 LEFT/source176→196は元窓内begin（NB+1.918ms/D−8.082ms）・ACK後に8UNKNOWNでMOVEMENT。最後のC終了時もvisualD残約1.868秒。原画は実LEFT1歩で、元singleton GOLD(-2,-2)→最新(-1,-2)、新DOOR(0,-2)/反対GOLD(1,-2)が揃う。新2セルの旧projectionはUNKNOWN。referenceとauthorityは同176で別frame救済はない。後刻schedule失効から過去の各評価資格を補完しない。

raw最良(+9,0)/.41303681335/gap .33343805475、median259/bad1で元支持300未達。旧STONE5点のうち3点は対応するが、遠方2点はDIRTへ変わり旧partial_matchの全旧STONE保持を満たさない。078の閉扉補助は旧GOLDexact2/閉扉2ahead/high-intensity専用で対象外。固定3依存面自体は405/bad5・帯118/287・元strong全73条件成立。72競合は支持300未満であり、十分支持競合に実15pp差を測ったとは書かない。

新証明は旧処理後UNKNOWNだけ。旧GOLD1→最新GOLD2/唯一閉扉bracket・旧金対応・新門/反対金の旧UNKNOWN projection、保持された旧STONE2点と旧金の非共線、zero/±1/±2全9translationで異なるanchor組も含め唯一、原raw同方向unit/通常score≤.45/gap≥.08を併用する。両FLOOR/CANDIDATE/GOODS_UNKNOWN・全保護/ITEM0・旧origin/実next/最新origin床を要し、078固定3依存面の全mask/UI/既知同材質/符号/contrast6/camera52/両frame51,52除外/1pixel1支持/300/95%/帯100/元15ppを変更せず使う。旧partial全STONE条件や旧関数本文は不変。

元078公開ng2_motionに原画LEFT1ラベルのMOVEDを期待するassertion RedをGit外で実測した。新分類で保持ACK比較27pair中、旧known23/旧UNKNOWN3は全不変、この176→196だけUNKNOWN→LEFT1MOVEDへ改善。純分類の比較でありControllerのprivate全状態・未保持future・実機到達を再現したとはしない。新MOVEDは過去のunitだけ、開通/入口creditを作らず最新の次Navへ返す。

## 3回目: 経路外の差で未送信DIRT票を撤回

未送信cmd17 RIGHT/source272→273はbegin0・SCREEN。前後のfull5はRIGHT/reason6/target(1,0)/DIRTで一致、origin/実next・両3×3/全GOLD/保護集合と材質/ITEMは同じ。変化は遠方(-1,2)DIRT→FLOORだけ、strict BLOCKED(0,0)も成立。既quietはreason8/FLOORでDIRTを対象外とし、generic safe-floorがvalidation7で止めていた。

quietへlead確認済みcontinuous・moves>0・未入店・確実未送信state1のreason6/DIRT/実nextだけを追加。両Sceneの2*direction閉DOOR/入力軸に垂直な両GOLD、全GOLD・保護集合と材質/ITEM・両3×3・full5不変・strict BLOCKEDを要する。許可する差は保護外/両近傍外のUNKNOWN/FLOOR/DIRT/STONEだけ。旧quiet他scopeの意味は不変。同ID/票全bytes/元before/時刻/epoch/prefix/owner/取消/元期限を保持し、再予約や未送信credit、UNKNOWN入力再送を増やさない。

## 検査と配布の範囲

新Nav8は旧078公開正例のO0/strictO2で8semantic subfail/error0のRed。新版初回は7Green、rawgapのPython前提だけが丸めで1failとなり、実隣接doubleのlow<.08/high≥.08へfixtureを補正して当該methodだけGreen。GOLD2の非bracket negativeを加えたpair methodもGreen。他6は初回Greenを継承し、製品epsilonや期待値を緩めない。DIRT6は旧078Controllerだけを強制した公開1method/4方向×3材質の12semantic subfail/error0のRed（他CORE依存のRed時hash未保持のため全旧coreとは呼ばない）→新版6Green。非zero epochの前提assertを補強した2methodsだけ再Green、元票全bytes→元NB begin/ACK→TERRAIN_OPENED→別入力でFLOOR実移動→次Nav DOORまで、掘削と実変位/開扉を分離して確認した。関連17は旧Nav3/078閉扉2/071shop5/071terrain2/Controller2/072passage2/ABI1。限定device CIは新14＋関連17＋selector3の34件。runner/import/callable/空baseline環境拒否、freshG1/22seal（Nav・Controller2変更/他20）、実compiler/全9MachO/完全source/IPAを照合する。未変更Runtimeは070既定限定確認だけを維持し、全故障/worldを積み増さない。

製品freezeはNav SHA `8f0c97156610ff5ad0e70a0ce1059664cd913c081286c50865dacbb7e018f0f5`、Controller `741f53f775da4c88a8573a6dcc174c55c7e0a2d827034a31fcb3b0fcfbad1201`。新Nav test `567be868ca2a918c457a2e819f8a63f0c67a093612a759cee25251fc1846750e`、DIRT test `c46873365b1459e1bb92eef4685ca9494c538f32c3eb925089a2fbc2c8d1716c`。freshG1→seal/apply完了、22中Nav/Controller2だけ変更。他20不変。独立1名が計画/最終製品・新単体・runner/契約と既実行ログを確認し、残P0/P1/P2なしでGO。レビュワーによる試験の重複実行はなし。実CI/IPAの照合結果は以下に記録し、固定assetの匿名GETを返却前に確認する。API16/cap14v15/ABI/全header/Perception/Runtime/JSON/G1/R12原40、旧判定/閾値/全期限・予算を維持。全対応配置/見逃し率/恒久毎拍/人超え・対象認識/通知/対象なし自動周回は未受入。前batchで判明した初期見送り原画の保持不足は別課題で今回へ混ぜない。


## 実CI・IPA照合（build128）

code `6b54170593bdbdf7ae42cdb4f2ee9f7a410f721a`、[run43005185350](https://github.com/shuhei0720/necrogold-automation/actions/runs/43005185350)の標準public Ubuntu/Mac device lane成功。新14/関連17/selector3の実34件がfailure/error/skip0。実sealed COREのcanonical/bareと5client HEAD/4callable・旧4client同bytesを照合、063/071/072/074/075/076/077/078/079 baseline envとBASELINE_NAVは空値も拒否する。実compiler4C/5Swift/6RSPをsource/PBX/raw args/hashへ結び、Nav/Perception strictO2・他C O0/Swift Onone・hostmacro混入なしを確認。未変更Runtimeは070意味的Red1/現6callに限定し、全故障/worldは追加しない。

Git外5verifierを各1回実行し全exit0。全5reportのcode/manifest/IPA hash、host・compile・MachO全22source mapとRuntime4C mapが一致。22seal Nav/Controller2・他20、R12原40/G1/header/ABI/API16cap14v15、全9MachOに旧141+新3=144 marker/新C宣言7（export6/static1）の混入なしを照合。rootも取得APIのrun/head/branch/digest/size・全ZIP CRC/安全path/重複0とinnerIPA全bytes/SHA/plistを独立照合。追加の製品試験は行わない。

IPA0.3.4/build128/min16.0/top.ebato.loopctrl、17,609,364B/SHA `d2b206f4c5f58ffeed8aa15af74ee2ce5282f42934796d4f9b9ceaac8aa0759b`。unsigned artifact13848922086は17,890,223B/`b20f9878a321cb27fb38cf671f9bf72dad8f069220e8e6891098abf0332576dd`、validation13848937103は1,261,327B/`e8ff0a53230e9b4bd52f4b634b545f19a5dee4bb7880f54ed1b9b5f7b9896fd3`、host13847976940は10,184B/`104e38bd1e30892aed21bf0793de387870f92eff8d6696451994664501f427f5`。

code sourceは583 tracked files/7,676,292B/`8ae3093958cae4d9d830193428554b728c055ad72163c31423af739438b5e01b`の全bytes一致。最終sourceはstatus/本記録/device台帳の3文書だけclosingで全製品bytesを維持する。固定[Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test079-build128)へ検証済みIPA/完全source/SHA256SUMSを保存し、返却前の匿名全GET・SHA/CRC・タグ/asset来歴をGit外receiptへ記録する。IPA再ビルドなし。

新実機は未実施。新IPAをSideStoreで更新→LoopCtrl完全終了/起動→Start Server/通常VPN。毎回新しい通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認をまず2回、展開sourceのtest_079.shで実行。短いrestartポーズはゲーム前面、5秒以上ならiSHへ戻り全画像/ZIP保存照合完了を待つ。runtime/test-079-<run_id>.zip全回分と全商品/停止位置/拍間隔を依頼する。078の追加回収/再実行は不要。
