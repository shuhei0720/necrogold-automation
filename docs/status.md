# 最新状態

更新: 2026-11-15（日本時間）。TEST100配布版、実機改善未確認。[計画](plans/test100-observed-shop-stops.md)・[受領/検証](reviews/test100.md)・[修正表](fix-records.md)。099の6添付は3runと同一内容のcampaign。全73PNG/81record/160原本を照合した。

修正は開扉後の遠方DOOR→GOLDによる拒否、新ITEM出現時の最新画像への再分類、側面入口下の3商品を確認する別policy4、左下口DIRTの候補bit9。旧partial結果で新商品を陰性にしない。対象はのろいのゆびわだけ、全商品登録/購入/宝箱開封は追加しない。

build187/run43623716812、code4ba361d3ca3ec12d4e068294c245546a4b4c1c6d。変更部＋関連host121件/21scope、別Mac186の単一callbackで旧Cのnamed assertion Red/現C Green、IPA実物5検査が各1回成功。実物検査で試験/compile/分類の追加実行0。製品native36中の変更はController/Navigation/Ringの3ファイルだけ。Runtime/header/旧ABI/Bank/Coverage/canonical15と56,088B ELF/G1/R12全40/通信・回収は保持。旧Mac183の広い試験は不変sourceの履歴扱いで、今回の実行にしない。

[IPA187](https://github.com/shuhei0720/necrogold-automation/releases/download/test100-build187/LoopCtrl.ipa)・[全コード](https://github.com/shuhei0720/necrogold-automation/releases/download/test100-build187/source.zip)。固定Release公開済み。publisher188/run43625480323、Release445493721。IPA/全コード/SHAの匿名全GET200・全bytes/hash・tag一致を確認。公開sourceはdocsだけ更新したclosing e74f8ebで、全非docsはbuild CODEと同一。

IPA更新後LoopCtrlを完全終了/起動、Start Server・通知・通常VPN。通常1-1ポーズから`sh test_100.sh --until-target`。候補探索/restart→商店→全商品確認→対象なしと確定した場合だけ次周回。対象/候補/実判定UNKNOWN/障害/資格のない上限では停止。区切りごとに画像回収が入る有限試運転で、最終PERF受入ではない。既入力/時間/restart上限とUNKNOWN無再送は維持する。

iSHの全画像保存・ZIP照合完了を待ち、表示されたcampaign返却ZIP（索引＋最後のrun全ZIP）を返す。全run原本は端末に保持。test-100は旧099と別spool。通常単発はオプションなし、明示された未回収だけ`--recovery`。

097実1/098の未確定停止を今回の別原因修正で解決済みにしない。実機到達率/毎拍・人超え速度/未知対象精度/長期耐久は未受入。遅延positive通知P1・native旧ledger整理なしP2は継続。[索引](context.md)。
