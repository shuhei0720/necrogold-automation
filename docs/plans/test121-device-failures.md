# TEST121: TEST120の実機停止と成功を比較して修正する

2026-11-25（日本時間）。基準はTEST120/build268、製品CODE723c1c6/Ccf471e36/Nav6b4faeb6、保存HEAD55a762f。実機を主にし、成功を保持して今回の拒否guardへ修正を絞る。[修正表](../fix-records.md)・[前回検証](../reviews/test120.md)。公開GitHub/標準Actions/固定IPAと完全sourceの既承認は継続し、保存の再確認は行わない。

## 原本と実順

7ZIP/4run/3campaign・99PNG/117記録を全照合。CRC/SHA・安全な一意path・全PNG decode/896×414 RGBA hash・metadata/stable prefix/記録鎖・escrow/親子・内包lastZIP同bytes・回収completed/drainedを確認し、提出不足はない。原本・PNG・Scene/reportはGit外。未収録の過去job packetは補わず、ZIP欠損と区別する。baselineは全1201Git blobの完全な試験コピーを保存し、相対kernel/headerも同bytesへ結ぶ。

| 実順 | 利用者の観察 | 原記録で確認した境界 |
| --- | --- | --- |
| 1/root3a4a | 商店扉前で停止 | 6実MOVED/開扉0。LEFT11/source125→126は未begin・確実NOT_SENT、validationFLOOR7。126は元Dより約127ms前、解析終了も約104ms前。原125→126は通常直接零・同LEFT閉DOOR。behind対角DIRT→STONEを旧quietが、遠方DIRT→FLOORを旧monotoneが拒否する合成適用外。同input旧119/120は同じ拒否 |
| 2/root5572 | 扉前危ういがRS成功 | source283/job5、policy17/layout1の正常完全陰性をC採用。durable→実RS24/既知ACK→新floor306→同Runtime child。末尾LIMIT/nullはresetで、失敗ではない |
| 2/child a084 | 商品可視だがRSせず、capture1候補見逃し | FULL3ITEMのsource215/job2で通常UNKNOWN/incomplete・policy6/EXTRA_BOARD1024をD前約53msに採用。PAUSE実ACK→durable→GOODS1。原画の同じ右看板が文字で2成分となり、余分な看板として拒否される。同成分だけをgroupするcutでも左capのupper floorが拒否。full/lowerは正Floor、既補対UL/LRは正Floorで、元閾値を保持する別証明を調査する |
| 3/root18c0 | 商品可視だがRSせず | FULL3ITEMのsource125/job2で通常UNKNOWN/incomplete・policy2/BOARD2+ROWS256をD前約82msに採用。PAUSE実ACK→durable→GOODS1。正の看板1枚/accepted_rows0。single-sign Scene/face・両cap・dense sweepは成立し、既merchant score/coverage .919/.892、SHOP .913/.913が元.94/.95に届かない描画差を確認 |

a084 capture1は旧119/出荷120でScene全bytes同一・CLEAR/GOLD0/mask0。正FLOOR口(-3,-2)、UNKNOWN inboard(-2,-2)、屋根3セルの黒gapがあり、前回の全屋根capとは別形状。通常C startup cutも実記録どおりPAUSE予約へ進む。既bit5と観測済み3床のinside viewだけで再観測する案を別計画へ置き、未知床/隠れた金を補完しない。位置・phase・skipを前回capture62と混同しない。

## 成功と再発の扱い

5572の正常packet・全3商品/3価格・正常陰性・採用・保存・実RS・別floor/封印・child開始を原記録/画像で確認する。child clock一致/初手PAUSEを強制せず、bootstrap flagの重複がないことを検査する。120の個々の新route/cacheがこの成功を生んだ因果はprivate mode/hitが未記録なので先取りしない。過去の3f/policy17、119のpolicy9/7/4実成功と対象候補保持も維持する。

商品停止2件は通常producerの期限内返却・C採用があるため、単に時間切れや未実行として修正しない。FULLのUNKNOWNと普通PARTIAL creditを混ぜず、C側の追加DATA/観測条件はgeometry/history/未消費予算に結ぶ。先に全被覆の正常証明を確認し、未観測やUNKNOWNを陰性へ変えない。

## 修正と検証の範囲

原RGBA・通常producer・元時刻/prefix・拒否guardを同じcutで固定し、原因確定後に短い計画と正式assertion Red→最小Green、直接関連を選ぶ。全opaque状態の再生や未収録未来は主張しない。別shape・既対策の適用漏れ・退行を同inputの旧/新と保存bytesで区別する。

同Controller/Ring等の編集は関数所有を分け、全体コピーで他担当のhunkを消さない。新しい看板証明は真正な余剰看板/商品/価格・target探索・独立C認証の拒否を保持する。商品名OCRや全商品の登録を拡張しない。Navは既nonzero候補と観測床経路を保持し、bit/方向/APIを増やさない。

元P/W/D・入力10ms・source/worker期限・UNKNOWN無再送・owner/prefix/取消・対象候補優先・初回RS/連続周回を維持し、独立差分レビューを行う。境界を変更した場合だけ該当Mac結合を追加し、無関係な全world/faultを増やさない。native変更後は新IPA・seal/来歴/実compiler/全9MachO/完全sourceを照合し、固定Releaseと匿名全取得まで進める。

配布時に具体的な修正点、維持した成功、実施範囲と未確認を示す。通常1-1ポーズから初回RS→候補/通路→商店→全商品確認→対象なしの通常判定/保存/実RS→次周回を依頼し、全run/campaign ZIPで実機の商品到達・継続を評価する。実機の改善・毎拍/人超え速度・未知配置精度は新結果まで未確認。

独立Controller適用表では、両停止はFULLでordinary PARTIAL creditの対象ではない。既FULL MOVEはACK observed214/124とjob source215/125のidentityが異なるため通常admission外で、未保持DATA枠/modeを推測しない。対象13関数は旧119と同bytes。producerの正のcoverageを成立させ、C独立証明を維持する修正を優先する。
