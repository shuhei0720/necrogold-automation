# TEST095: 受領と限定修正の確認

2026-11-13（日本時間）。実装中・未配布。実機改善は未確認。[計画](../plans/test095-device-stops.md)・[修正記録](../fix-records.md)。

## 094の受領

4 ZIP/82原PNG、ZIP計18,607,082B。全CRC/SHA、native専用manifest、record chain、全PNGとframe metadata、登録集合、archive inventoryを照合。全complete/terminal/drained、全入力state0、回収不足0。archive-journalは出版前snapshotでありpublished=falseを未回収の証拠と誤読しない。実時刻順はedad→656a→4835→c1dで、添付順とは異なる。

| 実順 | run | 観測された結果 | 制御と判定 |
| --- | --- | --- | --- |
| 1 | edad62b4 | restart上限、候補146見逃し | 0歩/0方向入力/12restart、limit。146原画を保持 |
| 2 | 656a4103 | 上側入口を開扉後、下の商品未確認で停止 | 8歩/9方向入力/2restart。214 PARTIAL正常判定を採用、216で新MOVE予約後217で拒否、screen保持 |
| 3 | 4835aea4 | LEFT2歩で停止 | 2歩/2方向入力/2restart。次UP8はbegin0/not_sent、MOTION拒否後の静止待ち2拍でbeat終了。送信UNKNOWNではない |
| 4 | c1d193c8 | 3商品sprite可視だが上の名前/SHOPがHUD切れ | 4歩/5方向入力/0restart。142 PARTIAL正常判定を採用、144で継続拒否、screen保持。完全陰性は未実施 |

実機の完全な商品判定→陰性次周回は0/4。目視のsprite可視を完全陰性証明へ読み替えない。実2/4の直接原因は正常採用後の継続条件であり、classifier kernel計算の故障ではない。対象外の全商品登録を前提にする設計も撤回し、同版で対象だけの判定へ変更する。

## 根拠と変更

原146は不変Perceptionを一度校正しFLOOR/CLEAR/peak61/goods0/protected0/mask0。094の長壁形とは違う分断された屋根と暗い曲がり口。新仮説でbit0だけ追加し、元Scene/UNKNOWN bytesと既chooser LEFT/path3を保った。

実2の214→217は遠方(-5,1),(-4,1)のDIRT→FLOOR、実4の142→144は(8,1)のDIRT→UNKNOWNだけ。全保護・完全判断・strict BLOCKED zeroは同じ。固定元画像を捨てず、origin/次床3×3外のこの二材質変化だけ別FRESHとして確認する。原画像の再分類は行わない。

実3の原129は旧STONE一つ。旧090は残STONE2の移動証明、091も2STONEのunit、092は2GOLDの静止証明であり今回に無条件流用できない。退役した確実未送信の通路待機だけに、旧STONE1＋非共線DIRT9＋一意9配置＋独立raw/blur/world95/axis75の全条件でzeroを確認する追加を検討・設計確認した。旧ng2_motionのUNKNOWNとMOVEDの判定は不変、後の132を元anchorへ差し替えず、元2拍を延長しない。

## 検証の範囲

Nav候補は新6＋関連25をO0/strictO2、PARTIAL継続は新5＋旧cycle29を確認。作者の局所Greenは最終同一source CIの代用ではない。新静止・対象だけの判定・client095の結果、独立差分レビュー、実IPA/完全source/固定Release照合は完成後に追記する。不変Runtime/API/FSなどの094証跡を再利用する場合は旧C calleeとの過去callback結果として区別し、新しい実C結合やiPhone到達を保証したとは書かない。

## 作者確認と独立レビュー

新Nav候補6＋旧25をO0/strictO2、新zero8＋旧motion13を確認。old085のController専用wrapperは新Ring headerを持たない旧harnessであり現在の統合成功とせず、新095のController6で現在の資格を確認する。旧091はassertを変えず、同じ現source8ファイルを切り出すNav-only構成で4件Green。

Controller新11（PARTIAL5/静止6）、実Python3.9のclient新3＋旧34がGreen。各意味Redの元source/test/ログを保持し、fixtureの構文/設定失敗はRedに数えない。作者の局所結果と最終sealに結合したCIを区別する。

独立担当は新zeroの積条件、共通update/publish/begin資格、既知Motion/actualGold経路の保持、遠方DIRTだけのPARTIAL確認、bit0仮説、旧094回収互換を確認しP0/P1なし。最終CI一覧・native差分集合と新policy2は別途確認する。

## 全商品登録案の撤回

named11/12・ignored13の実装とその局所試験は、ユーザーの最新指示により撤回し元のbank1〜10へ戻した。過去の局所Greenを現在の仕様・配布成功には数えない。旧081原275と094原142を一度使用した校正履歴はGit外へ保持し、未知評価へ再利用しない。

現在は[対象だけの判定](../plans/test095-target-only.md)を実装中。通常1-1金商店の有限B内の主画像全探索と、完全観測の強い対象名による陰性拒否を採用する。商品種別の辞書を増やさず、商品帯が欠けた状態は保持する。新しい判定・証明・Controller・Runtime/Wireの結果は凍結後に追記する。

## 対象だけ判定の凍結前確認

mode2は新13＋旧target14/bank20の47件がGreen。文字vetoの二つの不備とその組合せは、修正前のassertion Redと元sourceを保持して修正した。有限Bの全整数主画像配置、完全観測文字の閾値優先、元row/partial信号の保持、generic policy2証明とController/Runtime/Wireの接続を独立レビューし、残るP0/P1なし。旧商品bank/coverage feature/生成器/canonical15 source/ELFは不変。

現094の保持Scene214/142はgoods=PARTIALのまま各1回だけ判定し、host4.22/7.95msでOK/UNKNOWN/INCOMPLETE。Perception再実行0で、実画像の完全陰性や未知精度とは数えない。完全なprocedural画像は不変100ms期限で39.85ms、NEGATIVE/COMPLETE。iPhoneの速度・到達率は未確認。

Controllerのpolicy2新5＋旧cycle29も同一sourceでGreen。新しいSwiftの実行結果・最終同一source CI・実物照合はこの後に追記する。
