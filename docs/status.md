# 最新状態

更新: 2026-11-13（日本時間）。TEST097 build173のCI/配布物照合済み。**実機改善・受入は未確認**。[今回計画](plans/test097-arrival-continuation.md)・[受領/検証](reviews/test097.md)・[修正表](fix-records.md)。過去の対策や単体/CI合格を到達成功へ数えない。

## 実機根拠と変更

096の4ZIP/85PNGを全照合。実1は通路接近の実UPをUNKNOWN8回、実2は上端で切れた商品slot0を保持、実3/4は部分判定後の材質関係を拒否。実4も対象なし未確定。候補028/052/130/254は実判断sourceで見送り。前回のPAUSE採用遅延は今回の3判定で再観測していない。

Navは旧段を保持し、2種類の有限通路仮説とGOLD1を保持する接近の独立した移動証明を追加。Controllerは既071のshielded対角と遠方STONE→DIRTをcycleへ限定接続。空の部分結果には、実UP開扉・正の上端ITEM/保護・既可視部の新規遮蔽なし・独立静止を必要とする別の1入力framingを追加。新FULL/FLOORが先に来たら旧票を撤回し通常の新分類へ渡す。

空結果のUNKNOWN/INCOMPLETE/安全flag0は不変。対象なし・完成店舗数・restart権限をframingから作らない。Ring/Runtime/Wire/公開ABI・旧陰性証明・全商品登録なし・購入/宝箱開封0を維持。UNKNOWN無再送、元期限/累積予算は不変。

## 確認と配布

code `eb48c1479d3662bda10812af8c604f5f619228c9`、run43439504944/build173。選択host132/16scope＋selector5/1scope＝137/17scope、現Mac API/spool/Export・既Runtime096の12callback/旧Runtime意味Redが成功。画像校正・模擬時計/画素の接続試験であり、実ゲーム/iPhone速度・未知精度の合格ではない。

実物5種類を照合。36seal/2変更、実compiler・9Mach-O・旧判定資産/G1/R12・完全source821ファイルを確認。[新IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test097-build173/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test097-build173/source.zip)。固定Release asset、hashは同ReleaseのSHA256SUMS.txt。native変更のためIPA更新が必要。

## 次の実機

IPA更新→LoopCtrl完全終了/起動→Start Server/通知許可/通常VPN。sourceを展開しtest_097.shのあるフォルダをiSHへ選ぶ。通常1-1ポーズから候補までrestart→接近/入店→3商品が見える位置→のろいのゆびわ判定→対象なしなら次周回、最大4商店。途中の陰性PAUSEでは切り替えず、停止通知後にiSHへ戻り全画像/記録/ZIP照合の終了を待つ。表示runtime/test-097-<UUID>.zip全体を返却。入力UNKNOWN時は次回前にLoopCtrl完全再起動。

iPhone到達率/毎拍・人超え速度/未知対象精度/長期耐久は未受入。対応外layoutや対象候補は保持。遅延positive通知P1・ledger自動整理なしP2は旧記録を維持。[索引](context.md)。
