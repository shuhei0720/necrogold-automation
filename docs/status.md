# 最新状態

更新: 2026-11-11（日本時間）。TEST071の3run/48原画を受領し、全商品可視0/3。既存停止を先に直し、次に金壁不可視でも上/左通路へ近づいて再観測するTEST072を開発中。[計画](plans/test072-approach.md)・[追加契約](contracts/passage-approach.md)・[要件](requirements/necrogold.md#2026-11-10-金壁不可視の側方通路へ接近)。新IPA/実機はまだ未実施。次回から「候補までリスタート→候補接近→商店→全商品」を一連の実機テストとする。

## 受領と修正対象

実行順は88384bb8→2e398828→318e3f42（添付順と異なる）。全ZIP/48PNGのCRC/SHA/bytes/896×414/manifest/cursor/時刻prefix/active-report一致、全回収resolved/terminal/drained、dispatch_failureなし。raw/receiptはGit外received071。方向入力間隔約.505〜.526秒でほぼ毎拍だが完全同期を断定しない。

1は5MOVED+1開扉、2商品/PARTIALで停止。156→158の同LEFT/reason5/nextFLOOR/full5/金/全保護・strictBLOCKED。商品保護boxが隣のGOLDにも重なり、quietが危険床と同じ扱いで拒否。2は2MOVED後、94→95の同UP/reason8/full5/金/保護/strictBLOCKED、遠方DIRT/FLOOR揺れとSAMEchain2で停止。双方期限内。3は5MOVED+1送信UNKNOWN評価、113→122/124/126/134は実DOOR→FLOOR/新金と商品露出だが狭い地形の旧texture支持不足で8評価UNKNOWN、MOVEMENT停止。ACKや目視をそのまま開扉creditにしない。

A: 不通行GOLD上の保護重複と歩行先の保護を区別。旧SAME上限は維持し、ルート不変・未入店reason8の遠方揺れは元ID/全clockのquietで毎拍を維持。quiet不適格な未送信新観測は旧票撤回→独立静止pair→別ID/将来拍へ。開扉UNKNOWNだけ専用detail領域/2bandで元300支持/95%/15ppを証明、元MOVED/閾値は不変。

B: 提供12画像は上/左の通路形を視覚ラベル化。観測FLOORだけで固定mouthへ近づき、金出現で通常shopへ。外側実到達後の独立CLEARだけ局所見送り、未到達/不明は不在にしない。歩行後restartは最終vantageのfingerprintを基準に新levelを証明し、座標等をresetするが総inputs/moves/IDs/session/最初のwalk45秒期限は保持する。

## 開発・保存

A/B実装を凍結。新45メソッドGreen、独立設計レビューが最終hashの新4module+旧入店50件Green、安全レビューも未解決なし。レビューのP1（初回未開始時計/不明金の見送り/実金tileとCLEARの不整合）は新Red→最小修正で解消。網羅も最終hashの修正差分を確認し、3観点とも未解決P0/P1/P2なし。選択CI58と22sealを確定し、Macビルド/実物照合を残す。API16/cap14/v15/wire/ABI/Runtime/Perception/取得は不変の方針。単体/関係回帰と必要境界だけ検査し、全Runtime/worldは累積しない。標準public Mac/Ubuntu、新IPA/22seal/実compiler/全Mach-O/全source照合後に固定Releaseと具体的な実機依頼を返す。

現行配布は[TEST071/build112](https://github.com/shuhei0720/necrogold-automation/releases/tag/test071-build112)、code6cab2f625b17bedb3cc8540ca4d8f717a3dc68d5/[検証](reviews/test071.md)。IPA SHA88c2ed0987dddf6514dad10a2d953f0418b04876b9192feaf2c83507b64a8144。匿名GET/全SHA照合済み。受領済み071の再実行/追加回収は不要。

ユーザーは同じiPhoneだけで使用し、Macを持たず実機担当。最新指示は新機能に必要なら数時間可、品質維持。新照明で経路判断が必要な1〜2拍だけ許容、それ以外は毎拍。固定時間なし・実機ログを主に局所改善、候補保持/UNKNOWN無再送/全画像照合前の終了・次start禁止を維持。初読3文書≤16KiB、[索引](context.md)から必要資料だけ読む。
