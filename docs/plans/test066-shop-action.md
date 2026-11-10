# TEST066: 開扉前・店内の予約維持とポーズアイコンの断片

2026-11-10（日本時間）。TEST065の4run/67PNGを受領。1回目は全商品可視保持とPAUSE、2回目は入店後も下方商品の3枠が不完全、3回目は3商品可視だが画面認識失敗、4回目は開扉前に停止。送信23操作は実移動20/開扉3、BLOCKED/UNKNOWN/逆方向の観測0。ただしモデルのVISUAL_PHASE失効や未送信期限切れによる再同期/空拍があり、拍ずれなしとは保証しない。ユーザーは現程度の速度を暫定許容し得ると述べており、まず停止と商品確認を優先する。毎拍/人超えの達成へ読み替えない。

## 原因と局所変更

4回目141→142は同FLOOR/GOODS_UNKNOWN、全5field LEFT/reason5/target(-1,0)/DOOR、金/保護/局所不変、strict BLOCKED。遠方2cell STONE→DIRTで旧quietはnextFLOOR限定のため停止した。開扉前のDOOR不変・同じgate1操作へ既存quietを適用する。開扉を移動creditにせず、次の進入1歩と分ける。STONE/未観測/茶壁やlead校正/再予約/referenceの権限は拡げない。

2回目166→167は入店済み・同PARTIAL・reason8の観測床1歩で、遠方STONE→DIRTだけが変化。入口reason5限定から漏れて停止した。実入口通過済み・両PARTIAL・reason8/FLOORだけを、同じ全5field・origin/next床・全金/保護/局所近傍・strict BLOCKED・元時刻/予算を再検査して同IDで維持する。商品を踏まず、未観測を対象なしにしない。

3回目143は取得画像のポーズアイコン付近に商品名が重なり、バーの連続支持が11/12pxへ分断され、既存縦opening13後IoUが0.8未満。圧縮と描画の寄与を個別に特定したとはしない。既存13を優先し、失敗時だけ11も検査する。輝度55/85・IoU0.8・continue/死亡否定・footer/zone/floor一致は維持し、gap fillや参照clipを加えない。公開入口で原画143のFLOORを確認し、片バー/バー消失/白領域/短い類似文字等を拒否する。修正後sceneの他の停止条件も原画で確認し、未収録の先を成功としない。

## 期待・確認・返却

ControllerとPerceptionのみnative変更。旧C/旧Perceptionの意味的Red→局所Green、開扉と入店後の全方向/元ID/期限保持、金/保護/局所/商品/署名/判断/権限/送信済みの拒否、アイコン既知画像/公開入口の必要十分な回帰を選ぶ。既存assert/拒否条件を隠さず、通常差分レビュー1回。Runtime/Nav/Beat/API15/cap13/ABI/client v14、元12/45/180秒、50ms準備、入力不明の禁止は不変。

device CIと実IPA/22seal/実compiler/Mach-O/完全sourceを照合し、固定ReleaseのTEST066と具体的iSH手順で新実機を依頼する。全Runtime/world/不変clientを毎回の前提にしない。旧065は回収済みとして再実行しない。速度は間隔/未送信の空拍/位相失効/実変位を分け、ゲーム受信時刻がない限界を説明する。
