# 最新状態

更新: 2026-11-13（日本時間）。TEST096 build171のCI/配布物照合済み。**実機改善・受入は未確認**。[今回計画](plans/test096-walk-cycle-repair.md)・[受領/検証](reviews/test096.md)・[修正表](fix-records.md)。過去の対策や単体合格を改善完了と扱わない。

## 変更

095実1/2は各4歩後、曲がる1歩を移動済みなのにUNKNOWN8回で停止。金壁/入口が新たに見える旧FR079/081系列で、存続STONE2個への依存が残っていた。旧stageを変えず、旧金/STONE1以上/非共線DIRTと強い独立画素面を必要とする限定証明を追加した。元UNKNOWN無再送・全期限・累積16入力/12restart/45秒walk/180秒sessionは維持。

実3の分類は20.6msで終わるが同期PAUSE275msに採用を塞がれた。元期限内だけticket発行前の順序を調整。SHOP/商人固定画素で拒否される通常3商品の配置には、元Sceneの金壁/看板/価格/完全な商品帯をRingとController双方で検証する証明3を追加。全商品登録・文字maskは追加せず、のろいのゆびわだけを全探索する。対象なしだけ次周回、対象/候補/未観測/故障は保持。購入/宝箱開封0。

## 検証と配布

code `c12e66667de54ea69180c0b6629cf11e7498a1af`、run43427316593/build171。選択host129＋selector5=134件/13scope、Macの現API/実FS spool/Export、Runtime新4＋関連8の12callbackが成功。旧Runtimeの意味Redも確認。CI170の試験時計不足を製品変更なしで訂正した。校正と模擬時計/画素/判定注入の接続試験であり、実ゲーム/iPhone精度や速度の合格ではない。

実物5種類を照合。36seal/4変更、実compiler・9Mach-O・旧判定資産/G1/R12と完全source811ファイルを確認した。

[新IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test096-build171/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test096-build171/source.zip)。固定Release asset、hashは同ReleaseのSHA256SUMS.txt。native変更のためIPA更新が必要。

## 次の実機

IPA更新→LoopCtrl完全終了/起動→Start Server/通知許可/通常VPN。sourceを展開しtest_096.shのあるフォルダをiSHへ選ぶ。通常1-1ポーズから候補までrestart→通路/商店→商品確認→のろいのゆびわ判定→対象なしなら次周回、最大4商店。途中の陰性PAUSEでは切り替えず、停止通知後にiSHへ戻り全画像/記録/ZIP照合の終了を待つ。表示runtime/test-096-<UUID>.zip全体を返却。入力UNKNOWN表示時は次回前にLoopCtrl完全再起動。

iPhone到達率/毎拍・人超え速度/未知対象精度/長期耐久は未受入。証明3は有限の通常3商品構造/鏡像だけ、対応外は保持。遅延positive通知P1・ledger自動整理なしP2は旧記録を維持。[索引](context.md)。
