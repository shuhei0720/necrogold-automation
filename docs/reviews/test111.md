# TEST111の検証範囲

2026-11-17（日本時間）。基準d169d5b/TEST110 build217。[計画](../plans/test111-device-failures.md)、[修正表](../fix-records.md)。実機改善・未知画像の精度・iPhoneでの実効速度は未確認。

## 受領資料と成功の比較

13添付を重複照合して9固有ZIP/4campaign/5run。既存client、hashchain、全115 PNG/131記録のRGBA hashを照合した。a4af原309/310は旧Ring/Cの完全陰性証明、PAUSE、durable保存、RESTART22、新床337まで成立。成功処理を比較基準とし、campaignのcancelledだけで全停止を手動取消と解釈しない。

e5bbは同じ行の独立coverageと分類sourceの保持、ef21/17afは上側入口の固定観測形状、a0f6は未送信時の隣接床露出＋遠方制限変化、a4af次床は期限切れ票の回復時だけの遠方材質拒否を分けた。未来画像のない回復を実機成功へ数えない。

## 差分と試験

- Ring: 同一source/行の独立した完全証明へのfallback、上側入口policy15、名称を必須としない画像＋自身の価格表示policy16。曖昧な画像/価格欠落は候補。価格数値OCRや特定金額への固定はしない。
- Controller: 確実未送信の専用観測回復、既存quiet画像資格の共有、移動確認後の保持画像DATA-only採用、元親期限内の有界DATA-only再分類。公開ABI/入力期限/回復予算を増やさない。
- Client: 111だけ新capを開始前の既存schema取得で検査。同APIの旧IPAを拒否し、旧099/110既定動作を維持。
- 旧12試験ファイル・13メソッドは最新の名称任意要件に対応する期待だけ変更。価格欠落/曖昧画像/文字だけの候補保護とmode0/1を保持し、その他メソッドbytesを照合する。

各挙動修正の実装前assertion Redと最小Greenを私有証跡へ保存。実原画の校正は未知評価から除外する。既知のろい画像1枚は画像score約.953で名称なしTARGET、今回115枚はTARGET/CANDIDATE追加なし。これは観測済み資料の結果であり未知精度を示さない。

独立差分レビューは未送信回復、Ring/policy15/16、分類callback、client/配布scopeに限定し、残P0/P1なし。分類のlate callback候補保持漏れは追加Red後に修正し再確認した。保持/再取得の新14件と最終関連82件Green。e5bbの実274と17afの受領DEADLINE→実14を通常Ring/公開Cへ渡す校正も成功し、元期限/credit0を確認した。

新Runtime結合fixtureも独立レビュー済み。旧negative/retention/candidateの有効assertをそのまま再利用し、fresh_deadlineを追加した閉じた4ケース。実Macは実行結果が得られるまで未確認。

## 不変資産と残工程

G1/R12全40files、Runtime110の製品bytes、Wire/Spool/Export、Perception、canonical Ring kernel/features/ELFを保持する。旧build217の29 Runtime故障集合・Spool証跡は不変資産に対する過去結果であり、111で実行した結果とは表記しない。

最終source freeze/seal、選択hostと実Python3.9、実Macの4callback、IPA/実compiler/全source/固定Release照合は未完了。実機テストは全商品の可視位置への到達、正しい対象判定、対象外の保存→リスタート、次周回の継続を確認する。
