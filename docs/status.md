# 最新状態

更新: 2026-11-13（日本時間）。TEST094 build165はCI/配布物の検証済み版。**実機改善・受入は未確認**。[計画](plans/test094-native-goods-cycle.md)・[検証と未受入](reviews/test094.md)・[修正表](fix-records.md)。過去の対策や単体合格を実機改善完了と扱わない。

## 変更

093の3ZIP/60PNGは全回収照合済み。商品可視2回、restart上限1回。旧個別判定は実施済みだが対象なし確定経路はなかった。見逃し156は観測床3歩の上左通路仮説を追加し、UNKNOWNを床へ変えない。

094の専用cap/profileは同じiPhoneのRGBAから直接指輪を判定する。全商品を確認した証明済み対象外だけ、PAUSE→耐久intent→RESTART→新floor確認へ進む。画像回収/iSH判定を周回間に挟まない。宝箱は開けず対象外。対象/候補/未判定/故障は保持、自動購入0。16方向入力/12restart/45秒walk/180秒sessionは累積、4商店までの有限試験。

## 検証と配布

code `60284ae188d3e5bec4981256c1baa6110609ea4b`、run43390253276/build165。変更部と関連host144件/16scope、Macの実API・FS spool・Export6・Runtime新11＋旧3が成功。模擬時計/地形/判定を使うcallback試験で、実ゲームや実機到達率ではない。IPA実物5検査・実C8/Swift5のcompiler設定・9Mach-O・旧canonical15source/56,088B ELF・G1/R12・全source bytesを照合した。過程のCI失敗原因は検証記録に保存。

[新IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test094-build165/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test094-build165/source.zip)。固定Release assetへ配布し、hashは同ReleaseのSHA256SUMS.txt。新API/判定経路のためIPA更新が必要。

## 次の実機

IPA更新→LoopCtrl完全終了/起動→Start Server/通常VPN。sourceを展開しtest_094.shのあるフォルダをiSHへ選ぶ。通常1-1ポーズから一回開始し、候補までrestart→金壁/通路候補→商店→全商品判定→確定対象外なら次周回を確認する。途中の陰性PAUSEでアプリを切り替えず、停止通知後にiSHへ戻り全画像/記録/ZIP照合の終了を待つ。表示されたruntime/test-094-<UUID>.zip全体を返却。入力UNKNOWN表示時は次回前にLoopCtrlを完全再起動する。

iPhone到達率/毎拍・人超え速度/未知対象精度/長期耐久は未受入。bank外やlayout不足は未確定保持。遅延positiveの専用通知P1、session/回復ledgerの保持上限と自動整理なしP2を残す。[索引](context.md)。
