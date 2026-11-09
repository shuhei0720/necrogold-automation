# TEST058 レビュー・検証

2026-11-09（日本時間）。[計画](../plans/test058-shop-dispatch.md)と[合成world期待16例](../tests/test058-world-cases.md)。実機の商品到達は未受入。

## 計画レビュー

fresh安全第1周clear。設計第1周P1「証跡snapshot/pinとJSON延期が未分離」、P2「world拍受付が未定義」を具体化し第2周clear。網羅第1周P1「旧FRESHの別AX期待との矛盾」「16例の初期条件/期待一覧不足」を、限定したAX共有期待への置換とworld表で解消し第2周clear。実Cで判明したsouth最小2goldのHUD隠れを正面5セル幅へ、迂回DSのfloor-vantageループを2床後に掘削する地形へ、world Red前に訂正。入力4/7予算と商品/開通/進入の期待を維持し、設計/網羅は第3周の最終地形までclear。第4周は行わない。

## ControllerのTDD

新query未対応の互換stub（常時0）でcompile成功→semantic assertion Redを観測し、private preparation epoch/getterの最小実装後、全153件（既存145＋新8）成功。初歩/retune/旧ID/ACK/UNKNOWN/取消/非MOVEは0、SAME/FRESHと2chainの同epoch、別logical MOVEの別epoch、元deadlineとsource/phase/walk/session horizonの等号/+1nsを検査した。旧symbolそのままのbaselineではないことを記録し、Red時sourcehash未採取を最終hashで代用しない。証拠はGit外 `test058-controller-tdd.json`。

## Runtime・world・実物

固定旧Runtime `e72e4d1` / SHA `35a23af11c4d1c4419d3f59b55a6f7498c434934e4a275584063060ee76cf667` と固定fixture `d936ab9` を使う[Mac76](https://github.com/shuhei0720/necrogold-automation/actions/runs/42562321793)でcompile成功、指定 `FAIL MISSING_prepared_continuous_reissue_sends_within_original_frozen_deadline` / exit1 / stderr空を確認した。受領値の残余5,017,107nsと置換AX11,311,875nsを与えた合成公開fixtureで、完全実機再生ではない。

最小実装 `e714d80` の[Mac77](https://github.com/shuhei0720/necrogold-automation/actions/runs/42563596823)で実callback14例のreplacement AX0とworld全16例が成功。worldは通常8例4入力/3変位、迂回4例7/5、PF4/3、PA0/0・PARTIAL、CA0/0・取消、UN1/1・UNKNOWNで固定期待に一致。実producer16reportはclient v13のstrict parserと3診断配列も一致。実ゲーム・iPhone受入ではない。

local native/evaluator249件/全177path/skip0、client197件、package224件が成功。原057の7完成PNGはO0/strictO2/Pillowで全Scene・73scoresを照合し、実RIGHTと未実行UP判断までを評価した。未完了ZIPのstrict評価を追加し、integrity invalid/goal unknownを合格へ変えない。CI private除外25はlocal全件と別集計。

fresh実装レビュー第1周で設計/安全は静的P0/P1/P2なし。網羅P1(a)連続2再予約の実経路、P1(b)due直実行・診断先行・snapshot圧迫を追加。freeze `03302de` は実callback15例、productionの11key/epoch/IDに接続したpure16例、SAME2/FRESH→SAME×callback両順4例、pin20＋6実commit/旧encode保持/原PNG bytes・SHA・metadataの取消・失効・商品終端3例を持つ。期限/owner/lock等は同期main hook内で注入しtimer先行失効との競合を防ぐ。3担当が同周で静的追加指摘なし、P1(a)(b)はMac原ログの確認待ち。

[Mac78](https://github.com/shuhei0720/necrogold-automation/actions/runs/42565588321)で追加境界・reuse無効/診断先行の別2故障・world16・全旧Runtime Greenが成功。3担当が原artifactとRuntime SHAを独立照合し、第1周のP1(a)(b)を解消した。既存59故障は別集計で維持する。22seal中の変更はController.c/.h/Runtime.swiftだけで他19source同一、R12全40/G1不変を独立照合。

## 試験の同期修正と最終検証

full79は固定旧Redで新event公開直後・callback登録前にreleaseが空振りし、callback返却待ちで失敗した。期待MISSING Redへ到達した成功とは数えない。元d936 fixture SHA `1d17bcf7a5c4c3b0eca981de7cb6f161827fcfbbcbb71be180cfdf952f5f2c10`を検査後、HOST待機だけ挿入した実行fixture SHAは `c41647ccf903b0a209b5cec3ec464041faf010f822b44164eac67fb3a0c36304`。挿入除去で元bytesを完全復元でき、旧Runtime/C・時計・assertは不変。current側も実hold登録を待ち、direct_dueの実return待ちは維持した。

full81は旧59の3番目のmutationで、対象guardへ到達する前に通常owner producerのassertが失敗。100ms watchdogが先に取消し、入力0・reason5・drain済み・dispatch_failure=nullで停止した合法な競合だった。対象の旧analysis-owner・旧producer-owner・新058ownerだけ、実fault直前に健康なwatchdog checkをID限定でparkし、解析drain/実callback返却とowner復元後に解放するHOST fenceを追加。lockを保持して待たず、他のwatchdog試験・native値・元assert・全故障の期待は不変。3担当が静的補足を確認し、package226件成功。

新共通classはhook未導入の固定047では未使用なので条件付きで除外した。full83へ一時追加した旧047全体の確認は、既存のRaster期待が現版に対して古く失敗した。今回の必須laneから撤回し、旧047全体の再現は未受入・別scopeとする。成功結果へ数えない。full80/82は途中候補として取消した。

[最終Mac84](https://github.com/shuhei0720/necrogold-automation/actions/runs/42586379842)、code `5a190d3285d8f32cc0aa381d35d4566e8e27766f`で必須の固定058/056 Red・旧色Red・全旧59＋新2・world16・実compiler/IPAを確認中。client18は197件成功し、client/launcherは最終codeまで不変。完全build-source ZIPは450tracked files全bytes/CRC/path一致、SHA `6ba1353cb11381eca36404eaed0bca75b76b905dda9ee54999b5f241e7e040f0`。実compiler/IPA/最終配布sourceの照合は未了。compile失敗をRed、合成worldを実ゲームE2E、既知7PNGを未知受入と扱わない。
