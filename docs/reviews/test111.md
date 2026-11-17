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

CODE797448203a61150fe7961b1dbe8c8b4e08239d4b、[CI219/run44069884103](https://github.com/shuhei0720/necrogold-automation/actions/runs/44069884103)は成功。選択host240＋selector7、実CPython3.9の21、実Macのnegative/retention/candidate/fresh_deadline全4ケースを現sourceで確認した。旧110の29Runtime/Spool工程は明示skip。

manifest SHA256 `7be3fcee7d698683231934a7954905d0b88b1a20ffac58425804e174115cf033`。36資産の実apply/hash一致、変更はController/Ring.c/Ring.h/RPCMethodの4つ。IPAは18,191,326 bytes、SHA256 `e43f46a5534b24c0e68dff9a94ad9644c782b08a915e3a49b5d6600772fe61f3`。実compiler/profile、全9 Mach-Oのhost hook不在、保持資産、完全CODE source1016files/CRC/全bytes、同じCODE/run/buildとの5実物gateを照合した。

5gateは6attempt。canonical build scriptの実bytesが不変でも保持リスト所属だけで拒否した配布検査の不備を修正し、全15sourceをmanifest/local/CODE/baselineの4者SHAで検証。独立差分レビュー後、合格済みpackage/hostを再実行せずretainedだけ再開した。semantic/compiler/classifierの追加実行は0。

完全sourceは09b853fa123f52bdb47c2cdb5b0beaca00fd0ddeの全1016files/CRC/全bytesを再照合。CODEとの差分はdocs3のみ。source ZIPは9,621,562 bytes、SHA256 `83d3078436789e14e0a5d7183dc931fe8e8c1913824eda01ac26eb6a28c3d26c`。

[固定test111-build219](https://github.com/shuhei0720/necrogold-automation/releases/tag/test111-build219)をpublisher220/run44073360888で公開した。release448529580/tag/closing commitと、IPA/source/hash表の匿名GET200・全bytes/SHA・Release digest一致を確認。期限付きartifact URLは配布先にしない。

実機の改善・速度・未知精度は未確認。次の実機テストは全商品の可視位置への到達、正しい対象判定、対象外の保存→リスタート、次周回の継続を確認する。
