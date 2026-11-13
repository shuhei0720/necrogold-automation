# 最新状態

更新: 2026-11-13（日本時間）。TEST092/build157を配布。実機改善未確認。[計画](plans/test092-startup-stationary-status.md)・[受領/検証](reviews/test092.md)・[修正記録](fix-records.md)。修正前に過去対策を照合し、単体合格を実機改善完了と扱わない。

## 受領と対策

初回d503は最初の縦828×1792/EXIF1を約426msでaspect拒否、解析/入力0。後のZIP保存再開は正規回収で、再実行では起動できた。追加4ZIP/77PNGを全CRC/SHA/strict load/certificate/sidecarへ照合。実時刻順7702 goods6歩→7a8d beat2歩→56df goods7歩→6d60 screen0歩、商品到達2/4。17枚runも全回収済み。

実1・3は絵/文字判定実行済みで一致未確認、実2・4は商品authorityなしで未実施。対象なし確定ではない。今回のログにロック理由4はなく、調光が直接原因という根拠はない。間接影響は未確定、idleTimer/輝度変更0。

092は初期portraitを元3秒内の新取得だけで再観測、同GOLD2/旧STONE保存の別静止zero証明、陽性だが未局在の金候補から既観測通路への接近、指輪判定の実施済み/未実施表示を追加。最初拒否279未保持を原280で代用せず、未来の到達も合成しない。旧証明/期限/予算/取消/UNKNOWN無再送・全画像公開照合・候補保持/自動購入0・API16/cap15/ABI/G1/R12を維持する。

## 検証と配布

code `78faae482fe4c44ca9329c6514e32a0267308f9d`、run43353378401/build157。限定host30/10scope、Macの基準Red1・現新9＋旧保存1が成功。実物5gate各1回PASS、22seal3変更19不変・実compiler・全9Mach-O/388禁止marker・R12全40・完全source743件を照合。旧38件全体/全Runtime/worldは再実行していない。

154のctypes型衝突、155の正常後入力禁止、156のHOST待機不足は試験側を訂正し、製品sealは不変。最終fixture017d064aは訂正後で、事前凍結の初版4c75035dとは区別する。

[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test092-build157/LoopCtrl.ipa)・[完全ZIP](https://github.com/shuhei0720/necrogold-automation/releases/download/test092-build157/source.zip)。IPA 17,643,859B/SHA `f5d213ff6d702e945d5436eef2c06971a9b7f822b3fb8b51502189813124349f`。公開後の匿名全GET/実tagも照合して返す。

## 次の実機

IPA更新→LoopCtrl完全終了/起動→Start Server/通常VPN。ZIPを展開しtest_092.shのあるフォルダをiSHへ選択、`mkdir -p /mnt/necro_test092`、`mount -t ios . /mnt/necro_test092`、`cd /mnt/necro_test092 && sh test_092.sh`。通常1-1ポーズからrestart→金壁/通路候補→商店→商品3つ確認を一連で4回。自動ポーズ後5秒でiSHへ戻り、全画像/ZIP照合完了後の表示ZIPを全回分返却。回収済み091の再回収/088再実行/稀な対象待ち周回は不要。

到達率・毎拍/人超え・未知陽性精度・OS背景通知/調光の間接影響は未受入。[作業索引](context.md)。
