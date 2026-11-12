# 最新状態

更新: 2026-11-13（日本時間）。TEST091・LoopCtrl build152。実機改善未確認。[計画](plans/test091-device-stops.md)・[受領/検証](reviews/test091.md)・[修正記録](fix-records.md)。修正前に過去の同じ事象/原因を照合し、実機未確認を改善完了と扱わない。

## 実090の結果

実順c4109c61/3c04c7df/ec411d6f、3ZIP/60原PNGを全CRC/SHA/strict load/certificate/canonical sidecarへ照合、全回収完了。全商品確認0/3。

実1は未送信初歩の0歩SCREEN拒否。原175未保持で最終predicate未確定。実2は旧STONEを保つ実UP1、実3は正しく認識した木扉の開通0変位を確認できず8UNKNOWN。090のHUD喪失/薄鉄型とは別条件。原184にのろいのゆびわが見えるが全3商品不可視・正式個別判定未呼出。調整前一回診断はno_complete_rowで、精度合格ではない。

## 今回の限定対策

初歩はlevel入力/移動/lead0の未送信票だけを撤回し、既replan2回/元12秒/全予算内で独立2枚から再取得。元候補口UNKNOWNを陰性にしない。拒否raw1枚はv2の余剰pinへ追加し、既critical7/map12を維持する。Runtime診断は原点の未送信拒否を保持するだけで、level入力0/回復資格はCが確認する。

通路は全旧STONEを保持する別unit証明、開扉はblur絶対品質と既raw/detail/unique bracketの別zero証明を追加。旧17段/閾値/UNKNOWN無再送/入力窓/期限を維持。classifier/56,088B ELF/feature/authorityは不変。通路/開通問題の未対応条件が継続し、旧対策削除による回帰とは未確定。

## 検証・配布

code f355a1dd2c37ecdb04fafa0aa853b0e26f71c0ac、run43265221701/build152。CI38件/11scope、限定Macの旧Runtime Red1/現新5＋旧081関連6が成功。5実物検査は各1回PASS、22seal3変更/19不変、実compiler/9Mach-O/全731source/IPAを照合。全Runtime故障/worldは未実行。単体/校正/CIは実機到達成功ではない。

[新IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test091-build152/LoopCtrl.ipa)・[完全ZIP](https://github.com/shuhei0720/necrogold-automation/releases/download/test091-build152/source.zip)。固定Releaseへ保存し、公開後の匿名全GET/actualtagも照合して返す。

IPA更新→LoopCtrl完全終了/起動→Start Server/通常VPN。ZIP展開後test_091.shのあるフォルダをiSHへ選ぶ。

```sh
mkdir -p /mnt/necro_test091
mount -t ios . /mnt/necro_test091
cd /mnt/necro_test091 && sh test_091.sh
```

通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認を一連に4回依頼。ポーズ後iSHへ戻り、全画像/ZIP照合完了を待って表示されたruntime/test-091-<run_id>.zipを全回分返却。090追加回収/同088再実行/稀な対象待ち周回は不要。

## 未受入

実機到達率・毎拍/人超え・未知陽性精度・OS背景通知/対象なし循環は未受入。候補保持/自動購入0/全画像保存・API16/cap15/ABI/G1/R12を維持。[索引](context.md)。
