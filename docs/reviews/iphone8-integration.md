# iPhone 8の同C診断・capture-only結線

2026-11-16（日本時間）。本番iPhone 11の既source/座標/閾値は変更しない。8だけの新規診断と独立overlayを確認した。実機資料・端末識別子・鍵・詳細ログはGit外。

新規`tools/iphone8_geometry.py`はG1画像専用の校正診断で、既Cの公開`ng2_analyze_rgba`だけを呼ぶ。実FOV・HUD・明示遮蔽に重なるセルをUNKNOWNへ落とし、公開CのUNKNOWNを部品呼出しで迂回しない。部分観測2セルのassert Redから実装し、新10件＋旧raster15件が成功。独立レビューでprovenanceからの資格上書きとUI遮蔽coverageの不足を修正し、再確認で残指摘なし。既22資産のhashは不変。

同じ校正資料でFLOOR/beat・PAUSEが成立した一方、footer負guard36画素、Restart表示、direct原JPEG/CoreGraphics位相、実motionの資格は未確定。全出力の`input_authorized`・`automation_ready`・`profile_qualified`はfalse。校正画像を未知評価へ流用しない。

capture-only overlayの8許可pathは、固定6e25＋旧G1/G2の実preimageとの差分だけを独立レビューした。HTTP pair403と閉route、暗号open後のtyped token出典、同process限定管理出典、初期化前の通常producer回避、全constructorの同mode/coordinator、App/test identity、所有listenerだけの異常停止処理を確認。配線7件＋listener1件は意味Red→8件Green。新applier31件、完全source packager4件も成功し、残P0/P1なし。

この時点のServiceは最小stubで、`service_status_runtime`の実Mac assertion Redを先に確認する。新Service実装のレビュー、全結線の実Swift/iOS compile、actual compiler argv/target/source/IPA/完全source二重封印、8のfresh-process原JPEG取得は未実施。Info値一致だけでcompiled flagを証明しない。通常workflow・TEST107配布・既定launcher・R12は変更しない。8の成功は11実機受入の代用ではなく、旧資料移送も未解決。

[run43852121420](https://github.com/shuhei0720/necrogold-automation/actions/runs/43852121420)、job133247044108、source`1fcbe87`でServiceの実Mac compile成功→指定`service_status_runtime`だけFAIL/exit1/空stderrを確認した。4source hash一致、Bridge26/Core32/Mode8・applier31/packager4も成功。これは意味RedでありService実装成功ではない。sealed manifestなしのためIPA build jobは意図したskip。

次候補ではServiceに実GCD queue/単調時計/独立watchdog、metadata-only ImageIO、原bytesのhash/chunk、旧spoolの読み取りgate、owner/Stop fenceを結線した。独立レビューのsandbox祖先P1を、OS提供homeをFD anchorとして下だけnofollow走査する形で補正。既status assertionを維持し、公開合成JPEGで原bytes/EXIF/chunkと破損・取消・旧資料の結合fixtureを追加した。Core/Bridge/modeは不変で、Serviceの実Mac Greenは次CIで確認する。

新二重封印/package verifierは、compiled productsへの結合がsectionだけではload commandやsection外symbol変更を見逃すP1を実反例で確認し修正した。署名差分だけを限定正規化し、header/全non-signature load commandと非署名payload全体を照合する。独立した2反例の拒否を再実行し残P0/P1なし。新16件、applier31・packager4の計51件が成功。固定upstreamから旧seal→新overlayを実replayし45 sourceの最終hash一致を確認した。実compiler/IPA/完全source/原画像は次の専用buildと実機で確認し、未確認を成功扱いしない。

[run43854686087](https://github.com/shuhei0720/necrogold-automation/actions/runs/43854686087)、source`2c40053`はService実Mac compile/結合fixture・既Bridge26/Core32/Mode8・Python51に成功。actual iOS build800006はSwift importerのlabelが`reply:drained:`であるのに`withReply:drained:`を渡して停止した。独立errorはこの1件で、IPA/package/公開は未到達。compile失敗はbehavior Redではない。

次候補は同じproduction bindingを小さいUITest専用assetへ移し、実ObjC headerによるSwift typecheckをhost段階へ追加した。呼出しlabel以外の挙動・Service/Core/Bridge/mode/元fixtureは不変、独立差分確認P0/P1なし。6追加sourceを含む最終sealを再作成し、実Mac/IPAを再確認する。最新指示どおり完成版は11/8同一IPA・共通gameplay＋端末別profile。capture-onlyは原画取得の一時補助に限定し、8の本番商店到達/商品確認は未受入のまま記録する。

[run43857208861](https://github.com/shuhei0720/necrogold-automation/actions/runs/43857208861)、source`713ac0c`は実ObjC importerを通すbinding typecheckと既host/51件に成功。IPA build800007・ad-hoc codesign/package・既strict v3 actual compiler照合も成功したが、新verifierの`probe_plist_identity`で停止し完全source/公開は未到達。どのfieldかは旧logから未判定で、投入済みbuild settingを最終plistの証明へ代用しない。

次候補ではApp既Info2件に必須3keyを明示し、それ以外のdictionary不変を独立確認。UITestにも固定Infoをsourceとして明示する。applierは既Info2pathと固定名plist1件だけを追加許可し、任意plistは拒否。新assert Red→33件Green、package4＋verifierの閉診断17件と合わせ54件成功。診断は6fieldsのpresence/type/matchだけでraw値を出さず、拒否条件を維持する。実Xcodeによる展開・完全source・原画は次CI/実機で確認する。

[run43863102211](https://github.com/shuhei0720/necrogold-automation/actions/runs/43863102211)、source`b66680d`でhost/binding/54件・実IPA build800008・compiler/二重seal・全source1430files再照合・[固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/iphone8-capture-probe-build800008)公開が全成功した。Rootも通常の匿名downloadでIPA/source/manifestの全hashと完全source mapを別照合した。unsigned IPA SHA256は`0dad9b2ab63c82eceb1a47600487d18d534eb36f9e3a74bfb29676b0931a0638`。Windows RAM内で新署名stagingのcode/resource/profileを再検査し、旧204停止・旧spool不在・writer停止の後、正規Upgrade1回がOS Complete、導入後build800008一致まで成功。署名IPA/p12/pairingのCloud転送なし。fresh process/原JPEGの受入は別途記録する。

footer診断の負guard欠損は、字形を保つbodyと観測済み実端guardの2写像へ分けた。黒色補完を使わず、色付きprobeで全guard画素が実sourceから来ることを確認。補間の実nonzero tapで支持を検査し、旧cropの欠損36画素と明示遮蔽はunknownのまま保つ。Python2件とCのUIMap countのassertion Red→Green、Floor Resume実点の別assertを含むgeometry/profile/raster33件が成功。独立レビューでP0/P1なし。固定G1の3枚は同一公開CでFLOOR/beatだが、校正資料であり未知精度・direct原JPEG・入力資格へ一般化しない。11のlegacy値/保護native/R12は不変、gap31を維持。

[通常Runtime/100周increment](../plans/shared-device-profile.md)の8項目を独立して設計/網羅/運用レビューし、具体的P0/P1なし。11 passthrough・8 UNKNOWN・begin前拒否・begin後既契約と負例を対応させた。実装/実機受入はこれからであり、Windows依存の校正driverをPHONE-01達成と呼ばず、run/floor/商品完了の分母を分ける。

通常shared overlayの最初のhost段階は、Rootが作成担当と独立して限定レビューした。固定旧seal/preimage・限定path/asset inventory・実Runtimeからのbinding抽出・11任意command点維持・8 gap31でbegin前拒否・host flagの本番不使用を確認し、P0/P1なし。関連57件成功。専用workflowは標準Macで実Swift/C bindingを検査するが、unsigned build stageは存在せずIPAを作らない。通常raster/startup/実UIKit枝とunsigned packageの実受入は後続であり、最初のhost成功を実機周回へ代用しない。
