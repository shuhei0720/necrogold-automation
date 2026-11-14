# 最新状態

更新: 2026-11-15（日本時間）。TEST099を開発中。[計画](plans/test099-continuous-trial.md)・[修正表](fix-records.md)。ユーザーの最新指示は「通常に試験できる版」「のろいのゆびわまで本番に近く連続運転し、障害はログから特定して修正」。原停止を推測で直さず、正常な区切りだけを連結する。

098run97afbの回収ZIPは18PNG/20record、全CRC/SHA/manifest/連鎖/画像metadata/登録集合を照合済み。この1runのHTTP修正後の全回収は確認できた。complete=false/interrupted=trueは回復exportでも立ち、画像欠損とは扱わない。元実行は1restart/3歩後NO_PATH、商品判定は未実施。

保存Scene5枚は各1回だけ校正し、当初はbit5の候補、最後にもUP/FLOOR経路。通路待機の2beat期限との時刻対応はあるが、待機kind/anchor/途中画像が未保持で内側の失敗条件は未確定。097実1も継続許可後の再検査が原因箇所で、098の待機/診断は手前だけだった。両方を修正完了と呼ばない。

099は別getterによる最初の停止/通路待機のsnapshotと画像保持を追加する。元Status/Event/Scene ABI・入力条件/期限・UNKNOWN無再送は保つ。連続試運転は、完全陰性か確認済み開幕見送りの正常上限分岐でCが凍結するhandoff証明と、同runの全回収/ZIP/公開ACKが揃った時だけ新UUIDの通常startへ進む。候補/実判定UNKNOWN/障害/他のLIMITは停止。各run16入力/12restart/45秒/180秒/4商店・Runtime128ID上限は解除しない。区切りごとの回収時間があり、最終PERF受入とはしない。

campaignは原子的な索引と各run全ZIPを保持し、終了時に索引＋最後のrunを返却ZIPへまとめる。published journalも先に回収専用で照合し、crash/曖昧なstartで旧runを飛ばさない。--recoveryは新startなし、099spoolは098と分ける。

設計の独立レビューGO。C/実3.9の意味Red→Green、該当RuntimeだけMacの旧source意味Redを先に確認し、新Runtime→選択CI/新IPAへ進む。現行配布は[IPA175](https://github.com/shuhei0720/necrogold-automation/releases/download/test098-build175/LoopCtrl.ipa)・[098回収修正版](https://github.com/shuhei0720/necrogold-automation/releases/download/test098-http-recovery/source.zip)。099は未配布。

実機到達率/毎拍・人超え速度/未知対象精度/長期耐久は未受入。購入/宝箱開封/全商品登録は追加しない。Ring/Bank/判定資産/G1/R12全40は不変。遅延positive通知P1・native旧ledger整理なしP2は旧記録を維持。[索引](context.md)。
