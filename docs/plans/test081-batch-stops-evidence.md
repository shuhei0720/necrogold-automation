# TEST081: 六実機の停止3原因と各マップの見送り判断画像

2026-11-11（日本時間）。baseline `acf684bd0eb7b73ac5239e02f0879f9474470b35`、TEST080/build130。六runを比較して独立原因をまとめるincrement。Nav/Controller/Runtimeとcap追加のRPCMethodの4source。Perception/header/JSONの形/API `1.98.16-ngg2`・G1/R12原40・入力閾値/期限/歩行/リスタート予算/UNKNOWN無再送を維持する。保存容量だけは下記の明示opt-in profileで変更する。独立レビュー1名、各因果単体＋必要な保存/互換境界だけ、全Runtime/worldは追加しない。

## 1. 根拠と期待

080実順14377425→8b1a3039→fda712c9→13ac5415→57b548c3→12a2ed31。6ZIP/106原PNGを全SHA/ZIP・PNG CRC/PIL verify-load/896×414/manifest全offset/hash/cursor/prefix/strict schema/_load/実publicationへ照合、全PAUSE/terminal/drained/完収。取得failure/timeout0、host error/cancel0/status80max1.274秒。6のcmd9 too_late1件は回復後goods到達で他停止と別。root原216/212/140で3商品をそれぞれ視認（50/75/200、13/75/38、125/100/50）、全商品到達3/6。対象認識の成否までは認定しない。raw/SceneはGit外received080/test081-*。

3はreason7/FLOOR/target(0,-2)・閉DOOR(0,-3)/金2のUP接近。遠方FLOOR/DIRT差で同拍未送信再予約2を消費し、その後正式observation refreshへ移った記録と整合する。元143→145/146/153は既95%等が不成立で、元beforeを交換したり隣接frameの0を推移させたりしない。正式anchor146→保持153はstrict BLOCKEDで、遠方(6,1)STONE→DIRT/(2,4)FLOOR→UNKNOWNが現refreshのU/F/D限定に抵触する。147..152原画は省略、最初の拒否画像/私的経路を確定とは書かない。

4はcmd19 UP/source243→260を元窓内begin（NB+.795ms/D−9.205ms）・ACK後8UNKNOWN。capture終了時visualD残約1.971秒、実Creturn時刻は未export。原画はUP1歩。旧singleton金(-2,-2)→最新(-2,-1)、新門(-2,0)/反対金(-2,1)の旧projectionはDIRT/UNKNOWN。門は入力軸と直交したLEFT2に現れる。legacy高intensityunit .50300961325/gap .44563391730、0783面421/bad6/帯187・234、080phase652/帯497・155/score .38436529254/gap .35510996693。旧079は旧門UNKNOWN/通常scoreのscope外。新固定AND案はread-onlyでUP1MOVED、旧関数は変更しない。

5は開扉ACK後の未送信UP床進入票source152→154がSCREEN。両PARTIAL・full5/入口/両近傍不変・strict BLOCKEDだが、上端y=-5のsource protected領域内でITEM/保護7セル差、新金1点。latest protected17はimmutable source19の部分集合。原画は2商品だけで3つ目/店上部が切れている。商品全体が見える位置へ進むべき段階である。

4/5の最初の候補見逃しは判断原画がなく正誤未確認。source24/15前後を含め初期ゲーム判断原画は六run全て0枚（source実順14/17/19/24/15/14）。capture1は4がapp切替/5がiSHで地形根拠でない。4はRESUME最初FLOOR→skip source619.766ms/11独立prefix画像、5は335.380ms/6画像で元200ms資格に明白な不足なし。source自体がmissingで、encode上限だけの省略ではない。条件を推測変更せず保存問題を修正する。

## 2. A: 横向き金扉へ整列するunitの追加証拠

全旧Nav後UNKNOWNだけ。両FLOOR/CANDIDATE/GOODS_UNKNOWN・全保護/ITEM0・旧origin/実nextと最新origin床、旧金1→最新金2/唯一closedDOORのbracket、旧singleton対応・新門の旧projectionはDIRT又はUNKNOWN/反対金は旧UNKNOWNを要求。最新の門は入力軸と直交した2セル先で同法線、旧STONE由来の保持2点と旧金が非共線、異なるanchor組も含め全9translationで一意を要する。新STONEや変わったSTONEを証拠にしない。

legacy有限high-intensity最良（>.45）・gap≥.08・同方向厳密9px unit、078固定H→V3依存/全UI既知材質/52独立帯各100/総300・95%・全73元15ppと、080の全3×3依存known同材質normalized phase（元算術/全73/同unit/score≤.45/gap≥.08/支持300/65帯各100）を全てANDする。080の旧sparse all正INF条件は変更せず、新wrapperだけが別scopeで新phaseを使う。NaN/負INF/非unit/保護商品は拒否。

MOVED unitだけで開扉/入口creditは作らず、次は通常Navへ返す。旧079/080/全旧関数・閾値/元source/visualD8評価を維持。実3の新zero証明は追加しない。

## 3. B: 正式refreshの閉金扉接近に遠方STONEを許可

旧観測refreshの、lead/実MOVED確認済み・未入店・reason7/FLOOR/target=2*direction/閉DOOR=3*direction/法線に合う両金・GOLDexact2・両GOODS_UNKNOWNだけの分岐を追加する。元anchorと現在のfull5/両3×3/金/全保護集合と材質/origin・実next床を不変とし、保護外かつ両近傍外のU/F/D/S差だけを許す。GOLD/DOOR/ITEMや近傍差、保護差は許さない。

新STONE分岐は既previous→latestの外側検査に加え、immutable正式anchor→latestのstrict BLOCKEDを直接ANDする。元before143同票quietを追加せず、既not_sent→anchor146→独立proof→元予算内の新futureticket/最新HUD/50ms準備の権限を保持。anchor/source/epochを替えて0を作らず、既reason8等のrefreshは旧範囲のまま。chain/run回数、同期horizon/歩行45秒/session180秒/各等号・UNKNOWN送信禁止を維持する。

## 4. C: 開扉後の上端部分商品を隔離して床進入

未入店・last_completedに同方向DOOR_OPENED ACKがある最初の未送信UP/reason5/unitFLOOR票だけ。両PARTIAL/CANDIDATE、lead/実MOVED/continuous有効、full5/入口bracket/両3×3・origin/実next床は不変。通常quietと同じ元clock/ID/epoch/取消/owner/prefix/strict BLOCKEDを要する。

許すITEM/GOLD/U/F/Dの揺れと保護消失は、immutable sourceがprotectedとした固定上端y=-5のセル内だけ。現在の保護は元source集合の部分集合、境界外は旧金/ITEM/保護と材質を保持する。新保護点は境界内でも拒否。before/元票/元保護supersetを書き換えず、Sceneや画素を偽の保護状態へ変換しない。新金ラベルもこの隔離域では確定した壁/商品陰性へ使わない。sourceと直前acceptedの境界外gold消失を拒否し、mask0でsourceへ戻る場合も同じ限定資格を検査する。

quiet結果をそのobserve内で一度検証し、旧gold-retainedの例外と同票保持で共有して時刻/strict0検査を省略しない。VISIBLE/near保護/別ID/既入店/普通扉/UNKNOWN送信/未開扉/期限超過に例外なし。自動購入や候補廃棄・安全床校正/reference/FRESH権限を増やさない。

## 5. D: 各マップの最後の正常見送り判断元を保存

ユーザーの「初回に見逃すってことはどこで見逃すかわからん」を受け、最初の1枚のみの案を撤回する。新profileでは各マップの『正常見送りPAUSEの判断元』を保持する。keyは既snapshot.status.restartsの0…11。候補の再評価で同じマップ内のPAUSE予約が増えることがあるため、予約ごとに追加せず同indexの最新の有効sourceへ置換する。これで実際のrestart直前の最終判断を残す。以前取り消された判断のevent/referenceは元のまま、画像のmissing/omittedは正直に記録する。

current unstartedPAUSE（同ID/state1/begin0/outcome0/reason0/goods0/terminal0）、元frameのFLOOR/GOLD_CLEAR/GOODS_UNKNOWN・owner/generation/安定current-prefix/非inflightを既cache gate内で確認。cache(retainEvidence false/true)双方でpinDispatchSourceLockedより前から同じhelperを使い、evict前に確保する。source欠落/無効を別frameで捏造しない。既pinnedに追加のID集合を持ち、別RGBA複製を増やさない。旧bootstrap initialの余分なstrong参照は解放し、initial参照は保持済み判断元の一つを指す。run.lock内からRuntime.lockを取得せず既ロック順を守る。追加C/AX照会、同期PNG生成や入力権限を加えない。

判断画像最大12と既terminal/found/最新比較の優先枠最大7を重複除去すると19≤20。置換時も20枠内で更新し、既criticalのpriorityは保つ。従来4MiBでは合法な各512KiB画像19枚を保証できないため、新profile `normal-1-1-evidence-v2` だけ最大20PNG/各512KiB/合計10MiBを許可する。encode失敗はexport failure、1枚上限超過はomitted、取得元欠落はmissingとして正直に記録し、任意画像の無条件保存とは呼ばない。歩行・restart回数や同期期限を伸ばす変更ではない。

互換用profile `normal-1-1-v1` は全map保持を含めず旧initial/priority/合計4MiBのlegacy+pagedを完全維持する。新profileはpaged-onlyとし、default/明示legacy bulk resultsを拒否する。10MiBをbulk base64化すると既暗号plaintext8MiB/HTTP12MiBを超えるため、protocol/validationの共通上限を広げない。新cap `necrogold_native_v15` を追加してcap14も保持、client revision `native-walk-v16` の信頼mappingでAPI16/profile2/10MiBを指定する。wire key/type/APIは変更しない。runにprofile/予算をimmutableに保存しresponse.profileも一致させる。

旧revision1…15のjournalはそのrevのAPI/profile1/4MiBで回収する。startedは同UUIDのGET回収のみで新startしない・新capも要求しない。unstartedは同UUIDでrev16へ移行する。wireが自己申告するprofile/totalから予算を増やさず、信頼revision mappingで検証する。test069/protocol/validationは同一bytesを維持する。候補判定器を推測変更せず、次の見逃しを各マップの根拠で判断できるようにする。

## 6. テストと実装順

各因果の公開assertion Red→最小Green。A新Nav約8methodsは手続画像/4方向・新門DIRT/UNKNOWNと不正FLOOR/STONE・直交vantage・旧STONE/異なるpair unique9・全73/元phase閾値/全依存/両強条件・旧known/未入店を確認する。原画はGit外。

B/Cは公開Controller各6methodsを基本とし、原票全bytes/clock/source/epoch不変・元anchor独立0/前面owner取消・期限等号/chain/未来HUD、境界外/near保護や新保護/金消失/商品VISIBLE・mask0往復・未開扉/送信UNKNOWNを拒否する。既assertを削らない。

DはこのLinuxにswiftc/CoreGraphicsがないため、専用test-onlyを先にcommitし標準macos-26のretention Red-only laneで旧Runtime＋host seamの実cache→pin→exportを意味Red1として実測（IPA/全worldなし）。旧first-only Red run132はsuperseded診断であり新仕様の証明に使わない。改訂fixtureはmulti-mapの旧v1合法入力で実evictionを経たsource欠落をassertion Redにし、同fixtureの新v2入力で最大12map/同index置換/critical優先/両cache経路/owner・世代・無効source/旧v1の4MiB・legacy+paged境界を6casesで確認する。入力profile差はreportへ明記する。compile/環境エラーはRedにしない。新Red確認後だけD製品をapply。

新client/profileの8methodsとcap/package1methodは実HTTP startの旧profile及びcap15のprofile要求で意味Redを確認してから最小Green。旧revision/4MiB/historical API14・15・16/started回収/不正profile・bulk拒否を関連境界に選ぶ。旧fixtureのprofileが現行定数で暗黙上書きされないよう、履歴v1を明示する最小追従だけ行い既assertを削らない。

最終device laneでは新保存Green必要6casesと旧070 Red1/Green6だけを実sealed sourceで実行し、保存境界の実compiler/source来歴もIPAへ結ぶ。新multi-map Red-only artifactを別入力として固定hash/APIへ照合し、同じfixtureの最終Greenと対にする。Red-onlyと最終source照合の範囲/件数を別記する。

Nav/Controllerの意味単体は担当者だけが実行し、変更method以外の全体再実行を増やさない。related methodは各変更部の既拒否/候補保持/保存上限/APIABIから明記選択。独立1名が計画/最終差分と実ログを確認する。

## 7. 封印・返却

freshG1→sealでNav/Controller/Runtime/RPCMethodの4変更・他18不変。実compiler/profile/PBX/RSP/全MachOへのhost seam/marker混入なし、全tracked source/IPA/固定Release匿名全GETを照合する。完全source/新IPA・SideStore更新/完全再起動/Start Server/VPN/test_081.shを示し、通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認を依頼する。今回同様3〜6回を目安に、全run別ZIPと結果をまとめて比較する。080の追加回収/再実行は不要。

## 8. 限界・スコープ外

見逃しの正誤は初期原画欠落で今回未確定。実3中間/実4後の未来応答や私的stateを合成せず、pure分類・fake clock・実Runtime保存・iPhone受入を分ける。全配置の到達率/見逃し率/毎拍/人超え・対象認識/通知/対象なし自動周回は未受入。Perception全体の矩形安定化、一般unknownzero救済、候補形の推測変更、入力予算拡張/全Runtimeworldの積増しは混ぜない。保存容量だけの明示profile変更と互換境界は本計画5節の対象。
