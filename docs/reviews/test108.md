# TEST108: TEST107実機失敗の受領・修正・検証

2026-11-17（日本時間）。[計画](../plans/test108-real-failures.md)・[修正表](../fix-records.md)。基準 `c83056f` はTEST107配布時点と全tree一致。iPhone8/遠隔試験の実装は再導入していない。

## 受領と停止点

7添付を4固有runと3campaign最終runの重複へ照合。全ZIP CRC/安全path、内包ZIP全bytes、manifest/107記録のhashchain、97 PNGの復号RGBA/hashを確認した。原本・実行証跡・SceneはGit外。原記録はIPA build/native source hashを証明しておらず、未導入などの推測を原因にしない。

| run | 確認した停止 |
| --- | --- |
| 7186… | 開扉後の原157は正常Ring UNKNOWN/INCOMPLETE・policy10/ITEM128。3商品3価格でも通常品直下が暗く、閉容器専用の証明へ進んで失格。既FULL一歩観測は開扉後さらにMOVEした履歴を要求し、入口手前を扱わない |
| 7c69… | 原256→279は実画像でLEFT一歩。旧GOLD/全STONE/非共線DIRTの一意投影は成立するが、旧pixel面の支持不足でMotion UNKNOWN、ACK後reason10。単なる未送信ではない |
| be6e… | 原236の正常UNKNOWN後、FULL追加観測の全Scene不変/厳密零検査が原238で失格しSCREEN17。原237には一時的なPARTIAL/余分ITEM投影もある。原238の近傍材質方向は記録とホスト校正で逆だが、他4差と不変不成立は一致。権限の根拠に使わない |
| f2bf… | 原198→199は通常厳密零だが、観測床vantageがRIGHTからUPへ変わり、旧RIGHTの未送信票がROUTE10/SCREEN17。利用者の3周との対応は未確定の追加runとして独立解析 |

be6e原70は通常mask0の後にPAUSE/RESTARTの実ACKがあり、候補見逃しを確認。旧095/097の条件とは異なる上左split roofで、旧対策の削除回帰とは確認されていない。

## 実装

- 正の同方向開扉ACK/変位0・次FLOOR/入口金壁・正確ITEM保護・全potential ROI/no-positiveを要求し、入口手前のFULL/UNKNOWNも既一度限りの入店観測へ接続。旧UNKNOWN履歴と新入口形状の直積は拒否する。
- FULLのMOVE未予約stage1/2だけ、元GOLD/ITEM/保護を保つ描画材質の揺れを元D内の無入力待機へ。固定anchorへ直接のUNKNOWN/BLOCKED零のみ待ち、既知移動/TWEEN等は永久拒否。旧model/slots/preparation/proofを撤回し、既検証HUDデータだけ保持。後の同anchor全材質/保護・直接厳密零のfresh画像から通常fitした新modelで将来票を作る。`cycle_full_static` 本体・予約後/ACK後の拒否は不変。
- 単一完全29行face/相対14金壁/offset入口と既footprintを要する正のpolicy11を追加。既閉容器v2/実価格証明と全B対象探索、3価格/caps、Ring/C独立検査を維持。原236/238は右cap黒465/625、464/625で**新11でも正常UNKNOWN**。約39.05/41.29msのホスト校正は元100ms予算内だが、陰性や実機速度達成ではない。もう一歩入った後の実観測が必要。
- 旧Motionを上書きせず、既world領域の全依存閉包・全73比較の実支持300以上/有限値・unit勝者/.45/.08と、一意の旧地形投影・texture300票/95%/両領域100票を要する別証明を追加。通常rawの+INF/texture競合支持不足を差の証明にしない。固定maskは一度だけ生成する。
- 上左split roofの独立壁/屋根支持から既床3歩のvantageを選ぶ。暗い口や外側をFLOORへ補完しない。
- 確実未送信の観測床進路変更だけ、旧完全Decision照合後の新しい正規Decisionへ別refresh modeで撤回。新しい一歩近傍/観測target、単一remote STONE消失/正の床露出、固定新anchorの独立零/全tile一致を要求し、元期限/1進捗1回/run8を維持。既mode1/2は不変。

## 作者確認と原画像校正

assertion Redは期待値の前提を満たす試行だけを保存。初期fixtureの不成立・compile/環境・過大な保全検査の失敗を原因Redや実機再発へ数えていない。並行変更前の作者sourceと最終統合sourceを区別する。

- 開扉FULL: 旧107に正本1method/2assert失敗。初期OR直積への対向Red1。新7/旧FULL9成功、さらに待機修正後の同Cでwait7/open7/旧9の23件が成功。
- FULL待機: 旧Cに正本1method/2assert失敗。stage2権限撤回、固定anchor非推移、fresh fitの新ID、既知変化/新商品/予約後拒否、撮影なし・不正prefix discardのみでも元D失効を確認。原236→238は待機述語に当たるが、次床DIRTの現在MOVE0を保持。未収録の未来frame/入店後を作っていない。
- Motion: 旧107で4方向unit期待が4assert失敗。raw全finiteの中間案は元pairで不成立として撤回し、別world planeの正本Redを保存。cache前は新10/直接旧33成功。cache後は新12成功、原/4方向/限定視野/全73位相の80ケースで全score bytes/支持数/texture/Motion不変。95%だけ/片bandだけを壊した私有変異は各1assert失敗/error0。製品へ変異を混ぜていない。
- 原256→279は最終通常MotionでMOVED(-1,0)。world最小支持404、勝者.385949/runner.847476、texture843/不一致39。mask23296B、host stack24624B、ホスト単回cache21.308ms。端末性能/毎拍の受入ではない。
- split roof: 旧Navの新7で5assert失敗。新7と旧直接26がO0/strictO2で成功。原70の通常候補mask0→1、既床3歩LEFTから(-2,-1)のvantageまで、原Scene不変。
- 未送信vantage: 最終新10を旧Cへ結合して24assert失敗/error0、新10/旧072・098の16が成功。原eventsのMOVED11件からworld/visitsを復元した純述語1回でも適格。非activeな私有mode等は校正用仮定で、Runtime成立や11MOVE再演とは呼ばない。
- policy11: 旧107で通常producerがUNKNOWNとなる正本Red1。新13と既閉容器/Controllerの直接13成功。手続き的な新sourceから通常producer→C採用→PAUSE/保存/intent→RESTART callback/新floorを確認した。原236/238の未観測capはUNKNOWNのままなので、この連鎖を原runの成功とはしない。

## 独立レビューと保全

最終C `8f07146971b35ff77f754c3821eeb50b77427a541a670e11ecef95dd3300ad41`、Ring `0a767a0d532fd95c51962f2f8d6efe703a33a1aaa8d19e72a656910f445611a8`、Nav `34f1fae64d4fd5c4f5617749fec4f9a4ebb59a772bf0c0faa214bece6b3348c9` を独立担当が静的確認し、未解決P0/P1/P2なし。待機stage2の権限撤回とMotion品質guardの独立検査を閉じた。価格/看板余剰0と全B内の部分候補領域数の区別も計画へ明記した。レビュー担当のcompile/native/入力/CI実行は0。

36 native sourceをseal/実適用し、基準との差がC/Ring/Navの3件だけで他33件が不変と確認。ABI/API/cap・Runtime/Raster/Perception/features/canonical15/ELF/G1/R12を維持した。旧Runtime42f2/Mac191は過去の証跡であり、新C実行の証明へ昇格しない。

runner/selector/workflowの補足静的レビューも未解決P0/P1/P2なし。明示method集合はproduct153件/21class scope、新56件/6module、selector6件の合計159件/22scopeへ固定し、空/重複/skip/expected failureを成功扱いしない。ホストのselector6件が成功した。これらは現在の選択CI159件が成功したという意味ではない。

## 最終CIと実物照合

CODE `e8c4bb884f079fe11a7b14483bc3095990964641` の[device CI206](https://github.com/shuhei0720/necrogold-automation/actions/runs/43935103938)は、同じ最終sourceの159件/22scopeがfailure/error/skip0で成功し、未署名IPAを作成した。Runtime callbackの再実行を加えず、旧42f2/Mac191はhistorical-onlyのまま。

同runの3artifactをGitHub metadataの全bytes/digest/CRC/pathへ結合し、同CODEの完全source967 filesをGitの全bytes/CRCへ照合した。実package/host/retained/Mach-O/compileの5gateを各1回で全成功。検証器による追加native/分類/compile実行は0。実compiler・36source・旧source/feature/ELF/R12・9 Mach-O・現在のmethod inventoryを照合し、作者の旧source確認を最終CIと区別した。

IPAは18,065,614 bytes、SHA256 `08e84bbf3777e706861bfe8ce993f4d78faa05225b928cd3bb258e2943d606f7`。CODE完全sourceは9,344,389 bytes、SHA256 `f13a24c98a552973cf85ac4df26f7254b214a8002d4e92f4b695d2597f30855e`。固定Release `test108-build206` への公開は次工程で、公開後の完全sourceは閉じ文書だけを加えたclosing commitを使う。

無関係な全Runtime故障/全合成world/実ゲームE2Eは実行していない。新TEST108の実機到達率・未知精度・毎拍/人超え速度・耐久は未受入。原236/238で未観測の端を陰性にせず、次の適格frameと移動後は実機で確認する。
