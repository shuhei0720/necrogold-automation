# TEST057: 暗い床の色境界を安定させる8項目計画

状態: fresh計画レビュー完了（設計/安全第1周、網羅第2周clear）。2026-11-09（日本時間）。要件は[正本](../requirements/necrogold.md)、受領事実は[TEST056](../device-tests/README.md#test056受領結果2026-11-09-日本時間)。

## 1. 概要

暗い床のRGB中央値が1〜2変わるだけでDIRTとなる誤判定を、既存の限定された明るい床band内のB下限だけで修正する。入力の期限・予約予算・安全判定を緩めず、往復と不要な再予約の原因を減らす。未知の配置での到達・毎拍性能は次のiPhone受入で確認する。

## 2. 背景

TEST056はLEFT→RIGHT→LEFTの3MOVED後late停止、商品0。world目標は固定だが、同位置91→93の直上がRGB(42,26,24)→(44,27,24)でFLOOR→DIRTとなりUPを取り消した。最終2比較も分類変動だけでSAME再予約し、observe終了が元deadlineの1.567ms後になった。全18原PNGを保持し、比較画像の保持修正自体は成立した。

旧152必須画像＋今回13ゲーム画像を実Cで比較すると、B下限+100は213セル、+155は269セル、+200は283セル、比率.50は290セルをDIRT→FLOORへ変更する。その他のScene fieldsは不変。+100では最新2比較の変動が残る。+155では103/104/105のtiles差分が0、91/93は経路外1セル差が残る。これらは既知画像の調整であり未知評価ではない。

## 3. 詳細設計

`38<r<=52` の既存bright_floor内だけ、`55*r<=100*b` を `55*r<=100*b+155` とする。R/B各1単位の整数変動なら線形式の変化は最大155となる。これは既知画像での校正値であり、撮影誤差の普遍的上限を保証しない。B上限、G上下限、G-B差、spread、暗いband、gold先行判定、STONE/DIRT/wood、gate、商品保護、HUD、座標、原画素を維持する。Cと独立Pillow経路へ同じ式を適用する。

Nav/Controller/Beat/Runtime/Ticket、連続run8/chain2/input16、10ms windowと凍結時刻、motion/UNKNOWN無再送、owner/取消/drain、画像保存上限、API/cap/client v13は不変。反復防止penaltyや経路記憶、時間延長を混ぜない。+155に含まれる全変更セルを原画像の目視ラベルへ結び、真壁・商品・保護セルがfloorになる未解決例があれば実装前に候補を見直す。今回の目視はAI担当による暫定判定であり、人間によるラベル確認・最終実機受入は次工程で未了と記録する。

## 4. テスト影響範囲

Perception/Python scan、C profile用HOST試験、必須実画像manifest/replay、seal、TEST057 launcher/CI、資料。認識変更によって古い実画像の分類・Decision期待が変わる箇所は画像根拠と旧/新の対応を記録し、旧assertをskip/削除して通さない。古いFRESH等のguardを担う例は明示した合成Sceneでも同じguard assertを残す。元reportの歴史的Decision/失敗結果は改変しない。

## 5. 新規試験

実装前に実056の目視確認floorを要求するassertion Redを、現C/Pythonで観測する。compile/環境失敗はRedに数えない。実MacのC profileにも色bandの直接期待を入れ、旧式へ戻す故障がassertionで失敗することを確認する。

Greenでは新下限の内/外/等号、r=38/39/52/53、G/B上限・差・spread、gold先行、DIRT/STONE/wood/UNKNOWN/HUD/商品保護を確認。下限内/外×横/縦金壁bracketから認識→Nav/Motionを通し、新bandのFLOORでも単発gate probe・safe_floor除外を維持する複合例を追加する。DOOR→FLOORの開通と同方向unit変位を別に検査し、beforeがFLOORの曖昧な開通は成功と捏造せずBLOCKED/UNKNOWNで止める。既存152＋新18の全170画像pathを必須hash照合し、C O0/strictO2/Pillowの全Scene同値、Nav/Motionの既存73候補・原変位・旧guardを確認する。新056は同位置比較と実3MOVEを部分再評価し、新たな入力後の画像や全Controller再生を捏造しない。公開CIは私有画像caseだけを厳密な名前集合で除外する。

## 6. 実装順

freshな設計・網羅・安全の独立計画レビュー（修正込み最大3周）→assertion Red→最小C/Python修正→関連回帰・不変bytes→fresh3観点実装レビュー（同周の実物補足、最大3周）→実Mac標準runner build→IPA/完全source照合→実機依頼。

## 7. 配布前検証

local native/evaluator全件・package/helper・client、Mac旧59故障/Raster3/C全Scene/Decision parity-field/RPC/実compilerを保つ。新しい旧色式故障を別に検査する。22source seal、変更Perception以外21source不変、G1/R12原bytes、実PBX/flags/RSP、IPA内9Mach-OのHOST非混入、全source ZIPのtracked bytes/CRC/pathを確認する。nativeの認識変更なので新IPA更新が必要。通常1-1開幕金壁可視/左下/edge0のポーズから `sh test_057.sh`、自動ポーズ確認後iSHへ戻り終了表示を待つ。`runtime/test-057` 全ZIPを必ず依頼する。

## 8. 対象外・未確認

歩行開始の高速化、予算/期限変更、新たな掘削許可、経路score変更、指輪/周回完成、Macの正規ゲーム導入/起動。今回の既知画像のGreenは実機成功を意味しない。次の未知ランで往復・停止位置・商品到達・入力間隔を評価する。ユーザーはMacを持たず、CIでの実ゲーム試験は未成立のまま。課金runnerやゲーム購入/認証を追加しない。
