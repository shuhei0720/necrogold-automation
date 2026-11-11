# TEST081: 六実機の停止原因と各マップの判断画像

2026-11-11（日本時間）。製品baseline `acf684bd0eb7b73ac5239e02f0879f9474470b35`、TEST080/build130。[計画](../plans/test081-batch-stops-evidence.md)。六runをまとめて比較し、実変位・正式refresh・部分商品の進入・判断画像の保存を分ける。raw/原PNG/Scene/全ログはGit外received080/test081-*。候補見逃しの判定自体を修正済みとはしない。

## 実受領と確認できた結果

6ZIP/106選択原PNG（実順19/16/18/20/18/15）を全SHA/ZIP・PNG chunk CRC/PIL verify-load/896×414/manifest全offset・hash・cursor/prefix/strict API16 schema/実`_load`/publicationへ照合。選択PNGのnative capture行欠損0、全PAUSE/resolved/terminal/drained・完収。capture failure/timeout0、host error/cancel0/status80回最大1.274033秒。選択画像の回収完了と、保存されなかった全撮影画像の復元を混同しない。

| 実順/run | ZIP bytes / SHA256 | restart | MOVED/方向入力 | 開扉 | 終了 |
| --- | --- | --- | --- | --- | --- |
| 1/14377425 | 4,354,060 / `69e04e9afc4219cdd29e0d78340e1191ac30e88297c05f1f8b3beab13ebd3d97` | 4 | 5/6 | 1 | goods |
| 2/8b1a3039 | 4,278,352 / `e4301d8bb43d3a2de4b9bf99be08cd9749403b6c3fc893ffc0090add81c5d81c` | 1 | 5/6 | 1 | goods |
| 3/fda712c9 | 4,333,108 / `119f900f7aec94abe39222259f1f564795afab5e932fd4ede9c0f3221f3f63ee` | 2 | 3/3 | 0 | screen |
| 4/13ac5415 | 4,028,266 / `d09bddc7e7c16349dcb4562689fa24e5170b5f60c1b484752628aa6322c1fe5a` | 5 | 6/7 | 0 | movement |
| 5/57b548c3 | 4,396,351 / `0d5bb61df34ee82170d69e4c6150edaff1f64156c50463bf78a6c473b5e17557` | 2 | 5/6 | 1 | screen |
| 6/12a2ed31 | 4,319,287 / `55db9235cd4d8aefbeda061cb0e783bd569b10903eac7e99dd5f29f18042d0e6` | 1 | 5/7 | 1 | goods |

started_nsによる実順で、添付順とは異なる。rootが原216/212/140で、それぞれ3商品と価格50/75/200、13/75/38、125/100/50を視認し、全商品到達3/6を確定した。対象アイテムの有無や認識完了までは認定しない。画像合計は4,103,924/4,028,484/4,112,396/3,755,244/4,184,675/4,109,411Bで、全て旧4MiB以内。

6のcmd9はtoo_late1件（gateは元D+11.508ms）を記録したが、その後goodsへ到達している。3/4/5の最終停止と混同しない。1/6の入力間隔に約1.04〜1.05秒、2に約2.613秒の空きがあり、他は概ね.509〜.533秒。送信間隔を実ゲーム受付時刻・恒久毎拍/人超え合格にしない。全runのserver.build literal『2026-11-11 12:18』もbundle build130とは別の文字列型の値である。

## 停止3件の原因と限定変更

### 4回目・A: 横向きの閉金扉が見えた実1歩

cmd19 UP/source243→260は元窓内begin（NB+.795ms/D−9.205ms）・ACK後8UNKNOWN。取得終了時visualD残約1.971秒、実C return時刻は未exportなので補完しない。原画は実UP1歩。旧singleton金(-2,-2)→最新(-2,-1)、新門(-2,0)/反対金(-2,1)の旧projectionはDIRT/UNKNOWN。門は進行軸と直交するLEFT2に見えるため、旧079/080のscopeでは救えない。

legacy最良unitはscore .50300961325/gap .44563391730。078固定3依存面は421/bad6/52帯187・234、080 known phaseは支持652/65帯497・155/score .38436529254/gap .35510996693。新Aは全旧判定後UNKNOWNにだけ、旧金1→新金2の唯一closed bracket、旧金対応、新門の旧DIRT又はUNKNOWN/反対金旧UNKNOWN、直交2セル先の同法線門、旧STONE由来保持2点と旧金の非共線・全9translation一意を要求する。新STONE/変化したSTONEを証拠にしない。

legacy有限high-intensityの同方向厳密unit/元gapと、078全実依存・独立52帯・300/95%/元15pp全73、080全3×3依存known同材質phaseの同unit/.45/.08/300/独立65帯100を全てANDする。旧079/080/全旧関数・閾値は変更せず、MOVED unit以外の開通/入口creditを作らない。純分類59比較では旧known42/旧UNKNOWN16が不変、243→260の1比較だけUNKNOWN→UP1MOVED。欠落future、Controllerの私的状態・各時刻資格の再構成や実機到達の代用とはしない。

### 3回目・B: 正式refreshに現れた遠方STONE差

reason7/FLOOR/target(0,-2)で、閉DOOR(0,-3)/金2へのUP接近中。未送信の同拍再予約がchain2を消費し、その後に正式observation refreshへ移った記録と整合する。元before143→後続145/146/153の強0は成立せず、143を交換したり、隣接画像の0を推移させたりしない。正式anchor146→保持153はstrict BLOCKEDだが、遠方(6,1)STONE→DIRT/(2,4)FLOOR→UNKNOWNが旧refreshのU/F/D限定を満たさない。147..152の原画は省略され、最初の後続拒否frameや私的経路を断定しない。

新Bは、lead/実MOVED確認済み・未入店・reason7/FLOOR/target=2*direction、閉DOOR=3*direction/同法線金2、両商品UNKNOWNの正式refreshだけへ遠方U/F/D/S差を許す。元anchor/latestのfull5・両3×3・金・全保護集合/材質・origin/実next床を維持し、immutable正式anchor→latestのstrict BLOCKEDを直接要求する。元beforeのquiet同票救済ではない。not_sent→独立proof→元horizon内の新future票・最新HUD/50ms準備、旧chain/run回数・全期限・UNKNOWN送信禁止を保持する。

### 5回目・C: 上端で切れた商品領域による進入票の撤回

開扉ACK後の未送信UP床進入票source152→154がSCREEN。両PARTIAL・full5/入口bracket/両近傍は不変、strict BLOCKED。上端y=-5のimmutable source protected領域内でITEM/保護7セル差と新金1点があり、latest保護17はsource保護19の部分集合。原画は2商品だけで店上部と3つ目が切れており、全商品を確認した段階ではない。

新Cは未入店・同方向DOOR_OPENED ACK済み・最初の未送信UP/reason5/unitFLOOR票だけ。immutable sourceがprotectedとした固定上端y=-5内だけのITEM/GOLD/U/F/D揺れと保護消失を隔離し、新保護は域内でも拒否する。境界外の金/ITEM/保護・材質、full5/両近傍/origin/実next床を保持し、元source/保護superset/票全bytes/ID/epoch/clockを書き換えない。例外は同票保持だけで、安全床校正/reference/FRESH・自動購入や候補廃棄へ広げない。

一度検証したquiet結果を当該observeのgold-retainedと同票保持で共有し、mask0でsourceへ戻る場合にも元時刻/strict0を省略しない。独立レビューで非GOLD変化後のmask0復帰がquiet=falseを消費しないP1を確認したため、追加の意味Red2を実測して最小guardを補った（下記）。商品VISIBLE/near保護/別ID/既入店/未開扉/普通扉/送信UNKNOWN/期限超過の優先は維持する。

## 候補見逃しは未確定、各マップの判断元を保存

4/5の初回候補見逃しは、判断用ゲーム原画が残っていないため正誤未確認。六runの初回見送りsource14/17/19/24/15/14は全てPNG非保持で、原capture1も4はapp切替・5はiSHで地形の根拠にならない。4は最初FLOOR→skip source619.766ms/11独立prefix画像、5は335.380ms/6画像で、元200ms資格に明白な不足はない。metadata上の資格を候補陰性の正解とは呼ばない。source自体の保持不足を、encode上限だけの省略や回収失敗と混同しない。省略過去画像の追加回収・実行し直しは求めない。

Dは最初の1枚だけを保持する案から、各マップの最後の正常見送りPAUSE判断元を残す仕様へ変更した。restart index0…11をkeyとし、同map内の再評価では最新の有効sourceへ置換する。state1/同ID/begin0/outcome0/reason0/goods0/terminal0、元frameのFLOOR/GOLD_CLEAR/GOODS_UNKNOWN・owner/generation/安定current-prefix/非inflightを既cache gate内で検査する。cacheのretainEvidence false/true双方でpinDispatchSourceLockedより前から共通helperを使い、evict前に確保する。欠落sourceを別frameで埋めず、追加C/AX照会・同期PNG生成・入力権限を加えない。

正常判断最大12と既critical最大7の重複除去で19≤20。合法な各512KiB画像19枚は旧4MiBに収まる保証がないため、明示opt-inの `normal-1-1-evidence-v2` だけ合計10MiBを許可する。最大20PNG/各512KiBと入力・restart・時間の予算は維持する。encode失敗/1枚超過はmissing/omittedとして記録し、全撮影画像の無条件保存とはしない。候補判定器は変更せず、次の見逃しを判断元で調べられるようにする保存変更である。

新cap `necrogold_native_v15` とclient `native-walk-v16` がAPI16/profile2/10MiBを選ぶ。既cap14とprofile `normal-1-1-v1` の旧initial/priority/4MiB・legacy+pagedを保持し、新profileはpaged-only。bulk base64で既暗号plaintext8MiB/HTTP12MiBを超えないよう、v2のdefault/明示legacy結果を拒否し、protocol/validationの共通上限を広げない。runのprofile/予算はimmutable、response.profileも一致させる。旧revision1…15のstarted journalは元UUID/API/profile1/4MiBでGET回収だけ、新startや新cap要求なし。unstartedだけ同UUIDでrev16へ移行する。wire自己申告から予算を増やさず、信頼revision mappingで検証する。test069/protocol/validationは既bytesを維持する。

## ローカル単体と実Runtime Red

| 対象 | 実行済みの範囲と結果 |
| --- | --- |
| A・Nav新8 | 旧Navの公開正例でO0/strictO2×4方向×門両側の16semantic subfail、compile error0のRed。新版8methods Green。後続Nav理由をreason7としたfixture前提だけを、旧080のfull5判断とも一致するreason8/実nextFLOORへ補正し、変更した公開正例1methodだけ再Green。実MOVED期待と原手続Sceneは不変 |
| B・Controller新6 | 旧080Controller強制の公開1method/4方向で意味Red4。新版は5Green、PARTIAL SAME-chainを成立前提にした不正なgeometry fixtureだけを訂正して当該1method Green。C/H hash不変 |
| C・Controller新6 | compile成功の公開意味Red5/error0。新版は4methods初回Green、actual commitをquery nowへ進める前提とbegin後creditのfixture誤用を直した2methodsだけGreen。strict0の追加negativeは当該methodだけGreen。さらにレビューの非GOLD/mask0復帰2subcaseで意味Red2/compileclean/error0→最小guard修正→当該1method Green。変わらない全methodsの再実行はしない |
| client新8 | 実HTTP fresh startが旧profileを送る意味Red1→profile/cap/revisionの最小修正後8methods Green。歴史revision/API14・15・16/旧4MiB/started回収等の関連20methods Green。その後、v2 legacy bulkを拒否しない意味Red1→guard修正→当該method Green、旧v1関連3methods Green。後者は新8内の変更methodで、新9件とは数えない |
| package2 | 新cap15にstrict compiler profile2を要求する意味Red1（旧required_native_profileがNone）→新cap15と既cap14の2methods Green。API16据置/既strict profile2を確認 |

Nav製品SHA `ff3aa8ae932a39df75d6bc495b26ad9ab5ebcfbb11f2a1f0eb1747bf7d7fe3ef`、新A単体 `b00a8ae66e8181f34c6ff22852349c8d9ec2fb50761f6c4a434524431faf4a47`。新B単体 `31f609544556d18951ed3aef0b3a0e469ef87ac3bc472f82419af6fab777884c`。CのP1補正後Controller SHA `393180c768d84a3f684a69748bc98651959fab2e2c2742bea425e6e9a18fc60f`、新C単体 `c7e526cad0a87ab912c0de1fa738a7797877f2d8d7b0c2c953be32849429ecb8`。Navは新補助と末尾呼出し以外の旧全文bytesが一致し、C/H・旧判定/閾値の範囲を保つ。Navのtest-only C宣言9、B/C/clientに新C seamなし。

client製品SHA `d3dc2493b4ca34ceffbeedbb8d429f13734aa24f2eea53af70f95c53efc520f9`、新client単体 `f67ee9ee308c4694ad17044bf043a779c5ac2fb8481d993dc51a2fa0f49d3e56`。これらは各作者の実inventory/既ログ・実ファイルhashへ照合したローカル結果であり、最終CIや実機の成功ではない。

保存境界の新仕様はLinuxの模擬保存だけでRedとせず、標準macos-26のRed-only run133で実旧Runtime＋host seamのcache→pin→paged PNG exportを実行した。[run43030728793](https://github.com/shuhei0720/necrogold-automation/actions/runs/43030728793)、test-only head `bcbfd0ae0b52b9e6211f2d1625cd2d74af3fd3cc`、artifact13859988734/969,883B/SHA `ff8ab00a6a5ec29f0662a475060525f0d2356476280f5005b25a06a5332d3290`、全ZIP CRC有効。旧Runtime SHA `bfb0f271ca4504b7c428661a597c0fc070db29d993904f70c9020abb76b549f7`を固定し、旧版が正当に受け付けるv1入力で12map分のsourceを実evictionへ通し、`FAIL test081_all_restart_decision_sources_survive_pressure`・returncode1・compiled=trueを確認した。checkerのpassはこの意味Redを検出できた意味であり、製品Greenではない。

共通fixture SHA `302c4875593c2bf9c33ab2d9f6d6b1b17198ba791a1203a62075db876bb3d205`、Redで実行したfixture SHA `839559a7fa832ddde52f35ffd74a6751e58393a35c6abaf00b74af6b455dc701`。Redはv1、最終Greenは明示v2と別v1互換caseを用い、旧Runtimeへ架空のprofile shimを足して失敗させていない。旧first-only run132はsuperseded診断としてのみ保存し、改訂multi-map仕様の証明には使わない。Red-onlyはIPAを生成せず、Cの入力判断やゲーム進行・iPhone受入も証明しない。

## 初回device CIの保存試験ラッパー訂正

code `4f42d14a4a93f9c4de688d692e0730721cd5bafa` のrun134/43032602439では選択69件/18scopeが全Green、旧070 Red1/Green6も通過した。新081の実Mac実行stdoutは6caseのPASSと専用footerの全7行だったが、共通runtime_contractが旧suiteの先頭markerを要求し `runtime_production_contract_missing` でCIを止めた。compile失敗や製品の6case失敗とは区別する。IPAは作成されていない。

専用checkerだけでgreen-only・同RTE・実行1回に限定してこの形式差を扱い、その後の検査をreturn0/stderr空/期待6case＋footerの全7行完全一致へ強める。134実stdoutを使う正常/欠落/順序/余剰/FAIL/stderr/nonzero等の12境界をoffline検査し全PASS。製品、共通checker、fixtureテンプレート/実行fixture bytesは変更せず、Red133との対応を維持する。新codeでdevice CIを再実行するのは、この訂正と同じcodeの実compiler/IPA/artifactを結ぶためで、無関係な全Runtime/worldは追加しない。

## 最終検証・配布は未実施

現AST選択inventoryはnative36（新20/関連16）・client28（新8/関連20）・package2・selector3の計69件を予定する。これは実行結果ではない。最終hash/inventory確定後のdevice CI、実sealed Runtime保存Green6cases、既070意味的Red1/Green6、実compiler/PBX/RSP/全MachO/IPA/全tracked source/固定Release匿名全GETは未実施。freshG1→seal/applyは生成済みで、旧manifestとの実比較は22中Nav/Controller/Runtime/RPCMethodの4変更・他18不変。manifest SHA `fb1cff76cb57b2477a731ea48973ae05086299f0e6fe5c12aa874bd01572db19`、API16/cap15。実compiler/IPAへの結び付きは未確認。最終source件数・host実CI件数・ビルド番号を未実施のまま成功として記入しない。

最終差分の独立レビューは残P0/P1/P2なしでGO。上記の未実施検証を完了後、rootがこの欄へ実結果を追記する。新IPAと完全sourceを固定Releaseへ保存・照合し、SideStore更新/LoopCtrl完全終了・起動/Start Server/通常VPN/test_081.shを示して、通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認を今回同様3〜6回依頼する。全run別ZIPと商品全体可視・停止位置・歩行間隔をまとめて比較する。080の追加回収/再実行は不要。

全対応配置の到達率・候補見逃し率、恒久毎拍/人超え、対象アイテム認識/通知/対象なし自動周回は未受入。今回の候補見逃しは判断原画不足で未確定のまま。各マップの判断画像を残す変更を、見逃し判定の改善や全商品到達の実機成功と呼ばない。
