# TEST058: 連続入力の送信準備と商店到達結合の8項目計画

状態: 実装・Mac84実ビルド検証完了、iPhone受入待ち。fresh計画レビューは設計/網羅第3周の地形訂正までclear、安全第1周clear。2026-11-09（日本時間）。[要件](../requirements/necrogold.md)のSHOP-02/GOODS-01/BEAT/STOPを維持し、1歩だけで止まる原因と商店までの結合不足を扱う。

## 1. 概要

資格付き未送信再予約へ有効な前面確認を引き継ぎ、期限直前の診断JSON生成を入力より先に走らせない。実操作で状態が変わる独立な合成商店worldを、認識→経路→開扉/掘削→進入→商品可視→ポーズまで公開Runtimeへ接続する。実機での商品到達の合格は次の未知TEST058で確認する。

## 2. 背景

受領057 ZIP SHA `f49e35e4ae1a3491c1af7e0fe4e0e0acbbc990b60ff0e3cc262cd904f3f197c1` はRIGHT1/MOVED1後停止。source45→46は経路外DIRT→FLOOR、最新UP判断は不変でSAME許可。observe記録終了時の残余5.017107ms、AX照会開始まで5.176042ms、AX11.311875ms、gateはdeadlineの11.613976ms後。新画像の取得失敗ではなく、未送信outcome0がreason6へ写像された。窓は元の凍結期限により5.250148ms。延長して救済しない。

完成7PNGとcapture6の途中fragmentがある未完了checkpointで、resolved=false。直接原因に必要な37/38/45/46/53は保持され、追加回収の再実行は依頼しない。次UPへの4床は観測できるが、上端の扉はHUDで未認識・商品UNKNOWN。旧056式でも今回のNavは同じなので、前回校正による到達改善を今回から主張しない。

## 3. 詳細設計

Controllerのprivateなpreparation epochを、新しいlead確認済みlogical MOVEごとに発行する。同一元ticketから許可されたSAME/FRESHだけで保持し、現在の未送信command IDに対する専用read-only queryでRuntimeへ返す。初歩/retune/別ordinal/ACK後/terminal/取消/UNKNOWNは再利用資格を持たない。既存Status/Event/Scene/MotionWait ABI、全再予約/移動条件と凍結horizonは維持する。

Runtimeは元main.syncから実returnまで同一の強参照preparation leaseを保持し、run実体/clock/owner/generation/expectedPID/ACK prefix/epoch/ordinal/target/notBefore/deadlineを照合する。sourceとcommand IDは更新可能だが、最新IDの所有権とC beginは常に再検査する。sampleのstart/endを更新せずquery-startから1秒を守る。FRESHでは最新direction/x/yを送り、旧方向や失格したmotion referenceを復活させない。失格時は新規prepareか安全停止とし、古いcallbackは新ticket/leaseを変更できない。取消後のsample資格は即失効、実callbackのdrainは待つ。旧FRESH公開試験の「旧/新IDに別AX各1回、新query時刻が後」という旧期待だけは本変更と矛盾するため、資格付き共有ではAX計1回・sample start/end不変、失格時は別sample/停止へ置き換える。最新方向/座標・旧callback隔離・元期限・drain/exportのassertは維持し、削除/skipで通さない。

observeで最新画像の商品/保護/経路を先に検証した後、期限が迫ったMOVEではobserve後・tick後の完全JSON cacheを先行させない。現cacheを、毎commitのboundedなC snapshot/累積参照/最新比較priority pin/UNKNOWN UI freezeと、完全JSON生成・公開に分離する。recent4枚から落ちる前にpin20内で保持する。期限到来済みの準備済みticketは同controlQueueで直接executeし、将来ticketは重いJSONをその前へ再投入しない。延期は当該ticketのcallback完了/失効/取消までにflushし、終端・回収前は必ず最新snapshotを公開する。元callbackの実return・C直列化・status/cancelを維持し、JSON作成中に送信gateのrun lockを長時間占有しない。許可窓/予算/鮮度の数値は変更しない。

## 4. 影響範囲

NG2Controller.c/.hのprivate epoch/query、NG2Runtime.swiftのlease/入力優先とHOST hooks、対応単体/公開結合、独立SmallShopWorldとHOST renderer、check helper/新launcher/CI/manifest/必要な契約記述/資料。Perception/Nav/Beat/Ticket・R12/G1・RPC schema/client v13/cap12は不変。診断JSONから権限を推測せず、optional reference条件を入力資格と混同しない。raw057の7完成画像を新manifestで必須hash化する。

## 5. 新規テスト

実装前に旧Runtimeへ実測残余5.017ms・AX11.312msを与える公開fixtureでassertion Redを確認し、compile/環境失敗はRedに数えない。旧Cへの新query互換stubを使う場合は常時0の未対応値と明記し、既存処理を改変したRedにしない。新機能は旧コード→Red→最小Greenで進める。

同epochのSAME/FRESH/方向変更/FRESH→SAME/2回更新、旧→新と新→旧callback順、全key不一致、query1秒の等号/+1ns/逆時刻、取消/owner/gen/PID/lock/ACK/UNKNOWN、期限等号/+1ns、最新C拒否、cache延期中の5枚以上commit/pin20飽和/取消/terminal各出口の原画像保持・flush/回収を検査する。HOT用時計は未採取の処理内訳を捏造せず、独立に付加した遅延と受領値の出典を記録。原057画像は実RIGHTと次UP判断の部分再生までで、分岐後の未来画像を応答に流用しない。

SmallShopWorldはreport/Decision/Controller歩数/期待操作列を読まず、gesture方向と自身の地形だけで衝突/開扉/掘削/進入を更新し、world位置・遮蔽から原寸RGBA/商品を描画する。[16例の地形・入力予算・終端期待](../tests/test058-world-cases.md)をRed前に固定する。world独自の520ms周期/epoch・150ms先行/±10ms受付と同拍重複拒否を持たせ、HUDも同じ独立時計から描く。拍外を拒否する境界例も検査するが、この合成受付幅を実ゲームの窓と称さない。probeは開通だけ、次入力でunit進入、商品後の方向入力0と1PAUSE/実PAUSE画像を独立worldログと照合。隣接PARTIALでは既存安全停止が正解で、無理に商品へ進ませない。UNKNOWNは別processの最後で実行し、UI freezeを解除して次例へ流用しない。これは合成結合で実ゲームE2Eではない。

## 6. 順序

freshな設計・網羅・安全の計画レビュー（最大3周）→旧コードassertion Red→epoch/Runtime最小実装・world結合→関連回帰・fresh3実装レビュー（最大3周）→標準Mac実build/故障検出/実compiler/IPA→全source照合→具体的な実機依頼。新worldが露出した本体の不足は計画に追記してRedから直し、期待緩和/skipで通さない。

## 7. 配布前

local全必須画像/新7枚・native/evaluator/client/package、既存Runtime59/Raster3/C parity-field/実RPCを維持。新reuse無効/診断先行の故障を別に検出し、world全matrixと新旧Callback/取消/元期限を実Macで確認する。22seal・変更3native以外19source/R12/G1不変、rawPBX/実compiler/6RSP/IPA9Mach-O HOST非混入、全tracked source ZIPのbytes/CRC/pathを結合する。新IPA更新→LoopCtrl完全終了/起動/Start Server、新1-1開幕金壁可視/左下edge0ポーズから `sh test_058.sh`。自動ポーズ後iSHへ戻り「TEST-058: 終了」まで待ち、`runtime/test-058` 全ZIPを必ず依頼する。

## 8. 対象外・未確認

入力窓・run8/chain2/input16・source/phase3秒・query1秒等の緩和、UNKNOWN再送、未観測商品を陰性にする変更、認識色の再校正、自動購入、指輪/周回完成。Macの正規ゲーム導入/起動は未成立で、今回も本物のゲーム試験とは称さない。既知記録・合成worldのGreenを未知iPhoneの到達・毎拍・人より速い性能へ置き換えない。
