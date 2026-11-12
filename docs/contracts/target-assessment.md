# 対象指輪のローカル判定

[要件GOODS-01/02](../requirements/necrogold.md)・[TEST087計画](../plans/test087-target-pause.md)。対象は「のろいのゆびわ」。native `goods` は商品可視性であり個別種類ではない。

## データと判定

既nativeの全商品可視/ポーズ・入力drainと全画像の保存照合後、同iPhoneのiSH内で判定する。外部へ画像を送らず、新しいゲーム入力を出さない。入力は元certificate済み同runの最終ACK PAUSE authorityを先に、必要時だけ同prefix/stable/非inflight/非交差の保持proof1枚を使う。画像上限2、896×414の原寸と有限3slot/scale/探索範囲・取消を維持する。

看板・3価格/商品列を観測から求め、同画像・同じ商品slotのiconと表示名を空間的に結合する。価格の数値やrun/capture番号、特定runの固定座標を識別条件にしない。対象文字は「のろいのゆびわ」のderived glyph、iconはpublic既存R12 assetからのderived feature。raw/cropをGitへ保存せず、featureの出典hash/ROI・版/校正用途を記録しlegacy40filesを変えない。

| 結果 | 意味 |
| --- | --- |
| target | 同一slotでiconと対象名の独立条件を全て満たす |
| candidate | 対象らしいicon等はあるが対象名を含む全条件は未成立。保持する |
| unknown | 可視/資料/一致/判読が不十分。対象なしとはしない |

実3原309を正例、原225の別ringと他商品を校正に使った。新原寸featureの固定閾値はicon候補≥.80、targetはicon≥.88 AND word IoU≥.82/coverage≥.90。raw原308は飛行中なのでpixel校正でだけcandidate例にし、本番sourceへ入れない。隣接画像・変形を別run未知評価へ数えない。対象なし/自動リスタートを新たに判断しない。

## 保存と回復

`active.json` / native `report.json` の閉schema/bytesを変えない。初回archive前に `target-assessment.json` をatomic保存し、元inventory/ZIP/SHA/receiptに結合する。sidecarは版・run/report/asset/source hash・固定reasonとbounded evidenceを持つ厳密schema。現時刻/任意path/例外自由文を入れずdeterministicにする。

入力入替・symlink・foreignrun・未知field・余計なファイルを拒否する。既sidecar/ZIP/receiptは勝手に上書きせず、未完なら同runを先に再開し新ゲームstart0。旧entryのhook既定None・旧ZIP互換を保つ。evaluatorがsidecarを受理する場合も、この1名と閉schema/参照画像hashを検証する。

iSHへの結果表示はOSバックグラウンド通知ではない。今回、対象通知/対象なし循環・未知runの識別精度・iPhone後処理速度を達成済みとはしない。target/candidateでも既ゲームのポーズを保持し、自動購入しない。
