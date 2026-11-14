# 最新状態

更新: 2026-11-15（日本時間）。TEST100開発中。[今回計画](plans/test100-observed-shop-stops.md)・[前版検証](reviews/test099.md)・[修正表](fix-records.md)。099実機3回の停止と候補59の見逃しを、確認した別原因ごとに修正中。

[IPA183](https://github.com/shuhei0720/necrogold-automation/releases/download/test099-build183/LoopCtrl.ipa)・[全コード](https://github.com/shuhei0720/necrogold-automation/releases/download/test099-build183/source.zip)。通常1-1ポーズから`sh test_099.sh --until-target`。IPA更新後LoopCtrlを完全終了/起動・Start Server/通知/通常VPN。終了時はiSHの全保存・ZIP照合完了を待ち、表示されたcampaign返却ZIP（索引＋最後のrun全ZIP）を返す。全run原本は端末に保持する。通常単発はオプションなし、未回収だけ`--recovery`、099spoolは098と別。

098run97afbは18PNG/20recordの全CRC/SHA/manifest/連鎖/登録画像を照合し回収完了。この1runのHTTP修正後の回収は確認できた。元実行は1restart/3歩後NO_PATH・商品判定0。保存Scene5枚だけでは待機kind/anchor/途中画像が足りず、内側の失敗条件は未確定。097実1も継続許可後の再検査で停止し、原不具合は未解決。

099は別getterで最初の停止/通路待機と有限画像を残す。旧ABI・入力条件/期限・UNKNOWN無再送は維持。完全陰性か確認済み開幕見送りの正常上限分岐でCが凍結した資格と、全回収/ZIP/公開ACKが揃う場合だけ新UUIDの通常startへ進む。対象/候補/実判定UNKNOWN/障害/他LIMITは停止。各run16入力/12restart/45秒/180秒/4商店とprocess128IDは維持する。過去実行で128へ達した曖昧な拒否も同UUID回収のみ、自動再送/再起動なし。区切りごとに回収時間が入り、最終PERF受入ではない。

設計/C/Runtime/client独立レビューGO。build183/run43614403456、code ade7d047のhost85、現Mac API/spool/export・Runtime096の12・099の新6＋関連1、実物5検査を確認。新Runtimeの旧source意味Redは別run177。途中のfixture誤りを実Mac診断で訂正し、製品不具合/実機成功と混同しない。

固定Releaseは公開済み。IPA/全コード/SHAの匿名全GET・hash・tag一致を確認した。

実機到達率/毎拍・人超え速度/未知対象精度/長期耐久は未受入。購入/宝箱開封/全商品登録は追加しない。Ring/Bank/判定資産/G1/R12全40は不変。遅延positive通知P1・native旧ledger整理なしP2は継続。[索引](context.md)。
