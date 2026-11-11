# 最新状態

更新: 2026-11-11（日本時間）。TEST074の3run/54原画を受領、全商品可視0/3。1は金発見後の次未送信LEFTで静止UNKNOWN、2は正しいUP後UNKNOWN8評価、3はiSHのstatus JSON処理2秒超過による取消。[TEST075計画](plans/test075-motion-rpc.md)・[根拠/検証](reviews/test075.md)。075修正・限定単体/独立レビュー完了、IPAビルド準備中・実機未実施。

## 根拠

実順46efced0→0372e82b→1834cdeb。全3ZIP/54PNGのhash/CRC/manifest/prefix/cursor/report/strict schema一致、全選択画像回収resolved/terminal/drained。保持省略を補完せずrawはGit外。1/2最終PAUSE成立、3はcancel確認/paused0、capture/dispatch failureは全null。

1は4UP後・金への切替成功、次LEFT/reason8/FLOORでfull5/金/保護/局所不変でも通常texture283<300によりUNKNOWN。rawzero score.311/差.484は合格、独立勾配538/逆1/上下293/245は強度を満たす。D残は実C終了2.259ms（画像終了44.552msと区別）。2は3入力目UPが元窓内で送信され、実unit移動だが8評価全UNKNOWN、最後もvisualD1.927秒残。STONE0で既存石アンカー補助は対象外、旧の強い面も不足。原点52のfull21既知blur/完全旧L/左右phaseを満たす83/85/86だけ新MOVED、他はUNKNOWN。

3は6restart後の金可視で、初歩公開窓の123ms前にhost取消。HTTP/復号は短いがstatus JSONの段階が333→1520msへ増え次で2秒超過。最終金の認識/経路は有効、native初歩の失敗ではない。失敗平文がなくexact再現/OS停止は断定しない。

## TEST075の範囲

parserはvalidation.pyだけの局所高速化を凍結。逐字scanと全tree再walkを削減し、深さ16/nodes10000/size/UTF8/duplicate/nonfinite/error優先/RPC2秒を維持。新5/関連5Green、10,222差分で返値・error一致、status形のPython行work64.8%減/Linux1.85倍（実iSHは未確認）。Navはprimary/旧proofの閾値を維持し、UNKNOWN時だけ根拠の成立した静止/厳密unit補助を追加。新静止5/移動10、先行の関連26、最終cache同値1,898比較/15Green、独立レビューP0/P1解消。限定CI43・新IPA/実物照合後に返す。API16cap14v15/ABI/元予算/UNKNOWN無再送/商品優先を維持する方針。

## 配布と次の実機

現行は[TEST074/build118](https://github.com/shuhei0720/necrogold-automation/releases/tag/test074-build118)、code5eff462/[検証](reviews/test074.md)。075は未配布。検証済みIPA/完全sourceを期限のない固定Releaseへ置き、匿名全取得/bytes/SHA/CRCまで照合する。

次の実機は新しい通常1-1ポーズから、候補までrestart→金壁/通路候補→接近/入店→全商品確認を一連としてまず2回。短いrestartポーズ中はゲーム前面、ポーズが5秒以上続いたらiSHへ戻り全画像/ZIP保存照合完了を待つ。自動runtime/test-075-<run_id>.zip全回分と停止位置/全商品/拍間隔を依頼。回収済み074の追加回収・再実行は不要。

同じiPhoneのみ、ユーザーはMacを持たず実機担当。実機主軸・品質不変/固定時間なし、無関係な全Runtime/world累積なし。既知通路は毎拍、新地形の判断が必要な1〜2拍のみ許容。raw/秘密値はGit外、初読3文書≤16KiB、[索引](context.md)から必要な資料を選ぶ。
