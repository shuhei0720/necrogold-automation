# TEST098: iSH回収のHTTP上限と同run維持

2026-11-14（日本時間）。[計画](../plans/test098-http-recovery.md)・[修正表](../fix-records.md)。ユーザー画面は前run回収0/18枚でhttp_body_limit終了。待機ではなく中断であり、旧版を再実行して待ち続けても上限は変わらない。実機の超過応答mode/生データは未受領。

## 確認した不整合と変更

CycleClientは暗号化HTTPのbatch/manifestを512KiBへ制限していた。実サーバーの64KiB×4データはbase64化され、JSONEncoderがスラッシュをescapeし、SecureEnvelopeの暗号文もbase64化される。正常な有限応答でも超過できる。batch/manifestだけ1MiBへ変更し、single256KiB/他512KiBと、認証/MAC/ID/schema/画像CRC/hash/manifest/保存prefix/元UUID/期限は維持する。

明示した--recoveryは元の~/.necroprobe/runtime/test-098を使う。既device lock内で開始済みjournalがなければRPC/新UUIDより前に拒否。未回収は元UUIDをkeepalive=falseで回収し、公開済みは既receipt/元ZIPを検証して同ZIPを新しい展開フォルダへ再保存するだけ。通常試験は既動作を維持する。

## 実施した検証

実Python3.9で、正しいPNGの4chunk応答が933,627Bとなり、旧版でhttp_body_limitを再現した。HTTPConnectionだけメモリ応答へ置換し、実HttpTransportのヘッダ/読込上限・認証・復号・回収・PNG CRC・全ファイル/manifest/hash検証を通している。実機ネットワークや原runの応答を再現したとは呼ばない。上限拡大後も、不正MACとbulk1MiB/single256KiB/他512KiBの超過を拒否した。

HTTP新3の意味assert Red2/エラー0→Green、入口1の意味assert Red1→Green、回収専用新5の意味assert Red3/エラー0→Green。関連は旧094の34件＋095の3件を重複実行せず選び、合計46件（新9＋旧37）成功。表示文追記後に入口1だけ再確認し、shell構文/実3.9の--check --recoveryも成功。環境/compile失敗をRedに数えず、既assertを削除/skipしない。

独立差分レビューはGO、残P0/P1なし。ゲーム側native/公開API/指輪判定資産/G1/R12/IPA175はbyte不変。clientだけの変更なのでMacビルド/新IPA/全world/全Runtime試験は追加しない。ソースは全追跡ファイルと固定公開URLの全ダウンロードを照合して配布する。

## 実機確認

IPA交換・LoopCtrl再起動・元フォルダ/記録削除をせず、回収修正版sourceを別フォルダへ展開し、test_098.sh --recoveryを実行。通常の試験番号/永続spool/run IDは098のまま。全画像・記録・ZIP照合の終了後、表示runtime/test-098-UUID.zip全体を返却してもらう。これは元run回収の実機確認で、新ゲームを開始しない。歩行の1回目の停止原因は別件で未解決。
