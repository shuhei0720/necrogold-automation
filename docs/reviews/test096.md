# TEST096: 095の受領と残存停止

2026-11-13（日本時間）。CI/配布物照合済み、実機改善未確認。[計画](../plans/test096-walk-cycle-repair.md)・[修正表](../fix-records.md)。

3 ZIP/61 PNG、ZIP計14,247,136B。全CRC/SHA・専用manifest/record chain・全画像metadata・登録集合・archive inventoryを照合。全complete/terminal/drained、回収不足0。

| 実順 | run | 実際の停止 | 判定 |
| --- | --- | --- | --- |
| 1（添付3） | 2d81089d | UP4歩後LEFTを実送信、1セル動いたが8比較UNKNOWNでmovement停止 | 商品未到達・分類未実施 |
| 2（添付1） | 4e7d6242 | LEFT4歩後DOWNを実送信、1セル動いたが8比較UNKNOWNでmovement停止 | 商品未到達・分類未実施 |
| 3（添付2） | 81a50184 | 商品可視、分類20.619msで終了。同期PAUSE275.218msの後に採用され元期限を187.704ms超過 | 新policy2だがUNKNOWN/INCOMPLETE。SHOP認証失敗flags260も残り、対象なしは未確認 |

前二つはFR079/081と同系列の金壁/入口の新露出時の判定不足。旧source条件を消した回帰の証拠はないが、存続STONE2個への依存が1個の配置を扱えず残存している。095の修正が別branchにあることを、根本原因が別だという説明には使わない。

実3の左SHOPは目視で完整だが固定24×11画素例とのIoU.672/coverage.75で拒否。右には商品名が重なる。左の参照ink欠け28個に白文字は0であり、単純な白遮蔽ではない。merchant/商品帯の探索は未実行だった。商品登録を増やす問題ではない。

## 修正と校正の確認

Navは旧stageを上書きせず、最後がUNKNOWNのときだけ、旧金1→2/旧STONE1以上/非共線DIRT9/一意投影と既独立画素面の積条件を追加。新11＋旧079/081/095の24、O0/strictO2で成功。追加部分を除くと旧Nav全bytesに戻る。保持Scene2組を各1回だけ新ng2_motionで確認し、LEFT1/DOWN1を認識。Scene不変、再Perception0。未来の到達成功とは数えない。

Controllerはpolicy3だけに元Sceneからの金構造・3ITEM/端床の独立検証を追加。新7＋旧39が成功。追加を除くと旧Controller全bytesに戻る。旧修正を削除したという回帰の証拠はないが、実機の条件漏れは修正表へ残す。

Ringは固定のSHOP/商人画素認証を増やさず、別証明3で観測金構造を認証。raw余剰物は対象なしの条件にせず診断値を保存し、全商品登録/文字maskは追加しない。新12と旧47を確認（旧47はpolicy3の余剰48px看板ガード訂正前、旧経路は不変）。幅37〜48の余剰SIGNを落とす実装誤りは作者がRedで検出し、全canonical余剰SIGNを数えるよう修正、独立確認した。

凍結後、原288の同一RGBA/保持Sceneで全C判定を1回だけ実行。100msの実host期限で40.552ms、OK/NEGATIVE/COMPLETE、certificate3、raw余剰1を保持、3商品/3価格/余剰看板0。全5セルを探索しpure validatorも成功。再Perception0、UNKNOWN評価への再利用なし。これは元画像の校正であり、iPhone採用の時刻や次周回までの実操作を再現した成功とは呼ばない。

Runtimeは旧sourceへの戻しを全bytesで確認できる有限のticket発行前待機だけを追加。新4＋旧関連8の12callbackをMacで選ぶ。旧094のPAUSE観測まで分類をparkするfixtureは新しい正しい順序では成立しないため、元bytesを保存して未実行と明示し、同じ権限/回復条件を保つ独立intent取消へ置き換える。ローカルSwift実行は未実施。

独立担当は4製品差分と選択CIを確認し、修正済み余剰看板指摘以外に未解決のP0/P1なし。Macro faultの全組合せではなく、選択境界の証明と実機未確認を分ける。最終CI/IPA照合はこの後に記録する。

CI170は選択host134/API/spool/Exportが成功。Runtimeの旧sourceは指定assertで意味Red、現sourceの275ms PAUSE候補は成功した。次の陰性ケースは陰性採用→1回RESTART→次候補採用まで成功したが、試験時計がRESTART後34msしか進まず、既存200ms UI待機のため最終PAUSEへ進めなかった。元ログを保存し、独立レビュー後、095 helperと同じ次候補採用後220msの一度だけの進行を追加。製品・期限・assertは不変で、試験側の不整合として記録する。修正後の全12callbackとIPAは次CIで確認する。

## 最終CIと配布物

code `c12e66667de54ea69180c0b6629cf11e7498a1af`、run43427316593/build171。現sourceのhost129＋selector5=134件/13scopeが成功。Macの認証API・実FS spool・Exportと元sourceの意味Red、現Runtime新4＋関連8の12callbackが成功。次候補のUI待機時計を直したCI170の失敗は履歴に残す。旧094 Runtime14を実行済みとは扱わず、新096の置換caseと選択範囲を明示した。別の実C producer5入力は既policy2であり、証明3全体のMac実callbackやiPhone判定精度を証明しない。

root実物5種類を照合、計5試行/5種類。36seal/4変更、実C8/Swift5/profile3のRSP/FileList・9Mach-Oと禁止748marker・旧canonical15source/56,088B ELF・bank/生成器・G1/R12全40、build source811ファイルの全bytes/CRCが一致。IPA 18,012,560B、SHA `b185b36a7a3b6efce5bba2b3e5a0e6b5aff32608607a1cac489c00e6e840d3a2`。作者Redの一部は元source/test保存の記録で、完全な元compiler束とは呼ばない。原288の保持Scene/判定bytes/時刻を変えない制御側の限定校正でも対象なしを採用したが、実PAUSE未観測のため耐久完了とはしない。

closingは文書だけを変更し製品/試験/sealは不変。[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test096-build171/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test096-build171/source.zip)を固定Releaseへ保存する。公開後の匿名全GET/SHA/実tag/closing全source照合は私有配布記録へ残す。次の実機は通常1-1ポーズから候補探索→商店→対象だけ判定→対象なしなら次周回まで。停止通知後、全画像/記録/ZIP照合の終了を待って表示ZIP全体を返却してもらう。到達率・毎拍・人超え速度・未知精度の実機受入は未確認。
