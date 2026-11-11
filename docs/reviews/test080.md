# TEST080: TEST079受領と狭い閉金扉・閉じた通路候補

2026-11-11（日本時間）。baseline `88705eac9c64ace365a1bc8e60bbc3f50399ec10`、TEST079/build128。[計画](../plans/test080-sparse-gate-closed-mouth.md)。raw/Scene/原画の数値はGit外received079/test080-*。通常局所修正、独立レビュー1名。

## 実受領

3ZIP/58選択原PNG（20/18/20）を全SHA/ZIP・PNG chunk CRC/PIL verify-load/896×414/manifest全offset・hash・cursor/prefix/strict API16 schema/_load/実publicationへ照合。選択画像のnative行欠損0、全PAUSE/resolved/terminal/drained・完収。capture/dispatch failure/timeout0、host error/cancel0/status43回最大1.358秒。画像bytesは3,524,743/4,188,124/3,703,747で全4MiB以内。省略原画を補完しない。

| 実順/run | ZIP bytes / SHA256 | restart | MOVED/方向入力 | 開扉 | 終了 |
| --- | --- | --- | --- | --- | --- |
| 1/1f2b84fa | 3,832,377 / `e303479cf520061eb62e33e6a8f07a3ea21da7778404c0f3d711f1fa26fc1bc2` | 5 | 7/8 | 0 | movement |
| 2/93a2ca80 | 4,505,724 / `0a840aadb3d1ee2fab0b4e6d79a721f2f1591f9f4d5a043579a91e53051e8418` | 6 | 6/8 | 1 | goods |
| 3/d6cbad28 | 3,934,497 / `9fc3a051925770d9d7c3abe25c5ed6342b966be2fc2077e2296b9a8ab049b351` | 3 | 3/3 | 0 | no_path |

started_nsの実順で、添付順とは違う。rootが2の原368で3商品と価格100/150/50を視認、到達1/3。対象アイテムの有無までは認定しない。最終入力は商品優先でUNKNOWNのまま、商品可視だけでMOVEDへ数えない。

1の入力間隔は.512〜.526秒と1.045秒の空き1区間、2は.512〜.533秒と1.041秒の空き1区間、3は.518/.530秒。送信間隔をゲーム受付時刻/恒久毎拍/人超え合格にしない。server.buildの文字列『2026-11-11 10:48』はbundle build128とは別の値。

## 1: 狭い画面の実1歩がUNKNOWN

cmd19 UP/source328→353は元窓内begin（NB+1.077ms/D−8.923ms）・ACK後8UNKNOWNでMOVEMENT停止、最後もvisualD残約1.602秒。reference=authority328で別frameの救済はない。後刻schedule失効を各中間評価の資格へ補完しない。原328/353で実UP1歩、閉DOOR2ahead→adjacent・GOLD2exact/同法線/unique9をroot確認。

元phaseの中央除外maskは全73がINF、median支持148/bad0。078固定3featureは316/bad1だがcamera52帯68/248で元各100を満たさず、旧078証明は使えない。固定x112分割も313/5で不成立。最初のexpanded phase＋3feature固定65帯案はphase395/.05545648/有限2位.94774235だが、符号281/196・85で不採用。任意帯/閾値を探索して通さない。

採用する別結合は、旧全Nav後UNKNOWNかつ元73phase正INFのみ。両FLOOR/CANDIDATE/GOODS_UNKNOWN・全ITEM/保護0・旧origin/実next/最新origin床、閉DOOR2ahead→adjacent/GOLDexact2/unique9/同法線・保持旧STONE2点と門中心の非共線をANDする。新phaseは固定openingmaskの全3×3実依存が両frame既知同材質・非DOOR/ITEM/保護の点だけを元normalized intensity算術で採点。全73/unit/score≤.45/gap≥.08/支持300/mean6/contrast2.5/gain.65..1.55を維持し、新phaseの固定65独立帯各100（両frame64/65除外）を要する。さらに旧078固定H→V3feature/camera52の総300/95%/元15pp全73を併用する。

旧closed_gate_axis_strongの帯100も全旧関数も変更しない。新結合の独立性はphase側に置く。readonly実pairはphase347/帯192・155/score .04768658424、72競合支持max285で全INF。符号は316/bad1で十分支持競合0。有限競合との実.08差や十分支持競合との実15pp差を測ったとは呼ばず、境界は手続単体で確認する。MOVED unitだけを返し、開通/入口creditを作らず次の通常Navへ渡す。

## 3: 接近後に壁と確認された候補

cmd11 DOWN/source152→160はMOVED、pose(-2,1)で固定bit8 mouth(-3,1)/goal(-4,1)の内側隣接へ到達。次の方向票は出ていない。保持152/177で口はDIRT/両脇壁・GOLD/ITEM/保護0、choose_passageは経路なし。外側goalはDIRT→FLOORに揺れるため陰性根拠にしない。160原PNGは省略済みで、実wait anchor/私的kind/成立時刻を復元しない。旧2拍BLOCKED待機→未判定NO_PATHとコード上整合する。

追加はこの閉口だけの局所見送り。最後ACK実MOVEDで固定内側隣接へ到達・input0・BLOCKED待機、旧anchor/独立stable current-prefixのstrict BLOCKED zero・origin床/口同DIRT又は同STONE/両脇壁・全金/商品/ITEM/保護なし・両観測に床経路なしを元2拍/horizon内で要求する。private closedへだけ退役し、外側実到達inspected・未判定unresolvedと分ける。他候補があれば通常選択、未判定があれば従来NO_PATH、残り全てが確認済みなら既restartへ戻る。gold/商品/保護/owner/取消/prefix・UNKNOWN入力・元全予算は維持し、世界全体の店なしや金根拠なし掘削へ広げない。

## 単体・レビュー・配布の範囲

Bの新公開6methodsは旧079Controllerと他C/Hの全sourcehashを固定した正例1method/上左×DIRTSTONE4semantic subfail/error0/skip0/compilecleanのRedを先に実測。新B6の初回は5Green、session理由のfixture期待だけ14と誤記した1subfail（既headerは15）。製品を変えず期待を正本15へ訂正し、他未判定候補→NO_PATH/実restart後同口再候補/0MOVE・未送信拒否/元horizon等号を補強した4methodsだけGreen。さらに後続anchor許可の正例1methodだけGreen。他2は初回Greenを継承、全suiteを重複実行しない。B freezeはController SHA `b468b045708ecf587e0f2bfe78b20a7d033ebd27ba6a0033cdbd80d8030fb1e9`、新単体 `aab0dddb7e7518834a08acfc8c0ae8f67e5f344bf54c3ee51a3f9e753c690974`。

独立計画レビューはP0/P1/P2なしで実装GO。Navの公開旧079正例はO0/strictO2×4方向の8semantic subfail/error0のRedを製品apply前に実測（Red時全corehashを別採取していないため全旧core凍結とは呼ばない）。新版8は初回6Green、C bridgeのctypes引数数2errorsとdense静止fixtureのdefault overlay誤用1failをfixtureだけ補正。BLOCKED期待は維持してoverlay=Falseとし、影響2methodsだけGreen。8.5px blended negative追加の1methodもGreen。他5は初回結果を継承、製品/epsilonは変更しない。新Nav test SHA `b106f7061d49fbff3de30618a9f8952e09351fb1fb102adba61433625d5139bd`、C11宣言（export8/static3）、Controller C seam0。新phase全73は製品mask/View/round/intensityhelper非依存scalarと同値、全9実依存/65帯非重複・.45/.08/300/100/mean6/contrast2.5/gainclamp・95%/15pp/元all正INF/旧known/未入店を確認した。

独立1名が最終製品/全新14単体・既ログ/契約/runnerの差分を確認し、残P0/P1/P2なしでGO。レビュワーの試験再実行はなし。実限定CI/IPAの照合は以下に記録し、固定assetの匿名全GETを返却前に確認する。

新Nav8/Controller6・関連17（旧Nav2/078閉扉2/079露出2/Controller2/072通路6/074初期1/076待機1/ABI1）とselector3を選び、全Runtime/worldを追加しない。API16cap14v15/全ABI/Runtime/Perception/JSON/全旧閾値・期限・予算/G1/R12原40は維持する。新実機の到達率/見逃し率/恒久毎拍/人超え・対象認識/通知/対象なし自動周回は未受入。初期見送り原画の保持不足は別課題のまま。


Nav freezeはSHA `a81cb36bc3d06eb8b8186b83b33b75fbb3bc3e6d30360b451473cafd469747cf`。追加6helpers＋末尾1callを除くと旧Nav全文bytesへ一致する。保持ACK比較22pairを同source/profileのpublic純分類で照合し、旧known17全不変/旧UNKNOWN4不変、今回328→353だけUNKNOWN→UP1MOVEDへ改善。未保持futureやController private全状態/時刻資格の再構成、実機到達の代用とはしない。freshG1→seal/applyで22中Nav/Controller2変更/他20不変。


原353の自己比較は旧UNKNOWNだが、この同一PNGの照合は未来の独立観測や次ticketの実再検査を再現していない。今回の証明は過去unitの確認に限定し、次の開扉/進入/全商品到達は新実機で評価する。未収録futureのゼロ判定や入力権限を推測で追加しない。


## 実CI・IPA照合（build130）

code `15cdd72b0188e11970d6e547ee62b76ad5957e8e`、[run43017847436](https://github.com/shuhei0720/necrogold-automation/actions/runs/43017847436)の標準public Ubuntu/Mac device lane成功。新14/関連17/selector3の実34件はfailure/error/skip0。実sealed COREのcanonical18/bare17と5client HEAD/4callable・旧4client同bytesを照合。063/071/072/074/075/076/077/078/079/080 baseline envとBASELINE_NAVは空値も拒否。実compiler4C/5Swift/6RSPをsource/PBX/raw args/hashへ結び、Nav/Perception strictO2・他C O0/Swift Onone・hostmacro混入なしを確認。未変更Runtimeは070意味的Red1/現6callに限定し、全故障/worldは追加しない。

Git外5verifierを各1回実行し全exit0、統合receipt SHA `90044e0d48b3683087e9738af1b00175005636a8128b539e4d7f15cca60f14d0`。全5reportのcode/manifest/IPA hash、host・compile・MachO全22source mapとRuntime4C mapが一致。22seal Nav/Controller2・他20、R12原40/G1/header/ABI/API16cap14v15、全9MachOに旧144+新3=147 marker/新C宣言11（export8/static3、Controller0）の混入なしを確認。rootも取得APIのrun/head/branch/digest/size・全ZIP CRC/安全path/重複0とinnerIPA全bytes/SHA/plistを独立照合。追加製品試験なし。

IPA0.3.4/build130/min16.0/top.ebato.loopctrl、17,615,287B/SHA `cfdee552a92b02c8f4f992443438f651cbb6a57ac615efce5b8a1e9d71d4f885`。unsigned artifact13854556369は17,895,653B/`09f05f37dc9a40024deaedbb50afc23deea784493d4b54f85f3661899e845f36`、validation13854661335は1,270,793B/`9c1e00e0633afb99126700ba865ae0e8a98625f4e484b11589219ccd4de586d0`、host13853706413は10,487B/`06a9fada5e162dcc2db08a0486298eaac1089587f24e1ad794e8de9cbaa7c968`。

code sourceは589 tracked files/7,703,737B/`7cd57c39915c72c00fb4bfc120c0392b04988e51ddb4db8624482373fdbc4213`の全bytes一致。最終sourceはstatus/本記録/device台帳の3文書だけclosingで全製品bytesを維持する。固定[Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test080-build130)へ検証済みIPA/完全source/SHA256SUMSを保存し、返却前の匿名全GET・SHA/CRC・タグ/asset来歴をGit外receiptへ記録する。IPA再ビルドなし。

新実機は未実施。SideStoreで新IPA更新→LoopCtrl完全終了/起動→Start Server/通常VPN。毎回新しい通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認をまず2回、展開sourceのtest_080.shで実行。短いrestartポーズはゲーム前面、5秒以上ならiSHへ戻り全画像/ZIP保存照合完了を待つ。runtime/test-080-<run_id>.zip全回分と全商品/停止位置/拍間隔を依頼する。079の追加回収/再実行は不要。
