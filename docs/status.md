# 最新状態

更新: 2026-11-10（日本時間）。TEST066の2run/30収録PNGを受領し、全SHA/bytes/896×414/CRC/manifest/取得時刻・prefix一致。両native terminal/drained/input0/PAUSE。1回目は5歩後BLOCKED、2回目は3歩後UNKNOWNでmovement停止。商品確認0/2。入店したというユーザーの印象と、入口cross/商品を確認できない記録を区別する。[受領台帳](device-tests/README.md#test066-received)。

## TEST067: 移動確認と入口の既知未移動

[計画](plans/test067-motion-confirmation.md)。Controller/Navigationだけの修正。Perception/Runtime/Raster/Beat/API15/cap13/ABI/client v14は維持する。

- 空拍: 1回目の6入力は約1.04秒間隔、2回目は1.562/1.048/.515秒。初動約2.5秒。最初の確認画像がUNKNOWNで、第2評価の周期1/4待ちが約60msの取得間隔と重なり次拍へ遅れる。第2だけ元周期1/10へ早め、第3は元1周期・3評価・元visualD・同ID・UNKNOWN無再送を維持する。未収録の中間画像で早期確認できるとは断定しない。
- 2回目69→83: 背景が正方向1tile動くが説明文字の消失を含み、元texture補助が不成立。原判定経路を保持し、UNKNOWNに対して高contrast6以上の追加証拠だけを使う。両FLOOR/UNKNOWNgoods/候補/保護なし・床・正方向exact9・closed/unique両幾何・73候補・gap.08・300支持/95%/15pp差/2領域各100を必須とする。75/77はUNKNOWNのまま、83だけ追加証明する。
- 1回目の最後は同金bracketの観測床入口reason5でstrict BLOCKED。実判定125原画はexport省略で、拍外し/暗い扉等の物理原因は未特定。同床/両UNKNOWN/全tiles・金・保護・判断全5field不変の入口に限り、ACK-known BLOCKED後1run1回だけfresh HUD fit/将来拍/新IDを許す。旧event/歩数/開扉/lead/latest_verifiedは不変、元verified12秒/45/180秒・16入力・商品取消等を維持する。UNKNOWN/非入口/DIRT/DOOR/再度BLOCKEDは対象外。

送信10操作は8MOVED/1BLOCKED/1UNKNOWN。全beginは元10ms窓内（NB+.445〜7.245ms）、確認済み逆移動0。残存回復snapshotはVISUAL_SCHEDULEであり、拍推定失敗と断定しない。ゲーム受信時刻/動画はなく位相ずれゼロは未証明。065の速度暫定許容を066の合格へ流用しない。

## 検証と次の実機

新cadence6＋既存cadence8は066固定Cで13semantic failures/errors0→修正後14Green。新blocked6は066固定Cで18semantic failures/errors0→修正後6Green。新motion6も旧Navで意味的Red→Green。97原画/114比較の元3plane/全73score bytes一致、066第二69→83だけ追加MOVED。独立レビューP1の消去前model/raw snapshotを直し、新assertのRed→Greenを確認。新ticket発行後も同入口限定をactualbeginまで保持し、追加P1の負例Red→修正を独立6Greenで確認。レビュー最終P0/P1/P2なし、device39件とIPAへ進む。変更部/関連回帰と必要なIPA同一性確認を選び、未変更Runtime/world/クライアント全体をCIへ累積しない。実ゲームCIは未導入。

native変更のため新IPAを標準Macでビルドし、22seal/実compiler/全Mach-O/全sourceを照合して固定Releaseから返す。TEST067は未配布・実機未実施。SideStore更新/LoopCtrl完全終了・起動/Start Server、新通常All Zones1-1金壁可視ポーズからtest_067.sh、終了後runtime/test-067全ZIPと3商品可視/拍の安定性を必ず依頼する。

## 受領と回収の限界

1回目07a85…は6入力/5歩/開扉0/商品0、全17選択PNG受領。判定125等は4MiB選択から省略、未収録画像を補わない。2回目f432…は4入力/3歩/開扉0/商品0、18選択中13PNG、欠損3/6/35/82/88と35.partあり回収resolved=false。停止評価69/75/77/83は収録済みで原因解析可能。host_deadlineは回収側の期限でnative movement停止とは別件。report 3.jsonは同runの途中保存で3回目ではない。回収済部分を追加収集するためゲームを再実行しない。

[TEST066固定Release build102](https://github.com/shuhei0720/necrogold-automation/releases/tag/test066-build102)・[066検証](reviews/test066.md)。Mac102/device34・Mac103公開、実IPA/22seal/9Mach-O/全498source照合は過去結果。今回の実行記録で導入後の動作を確認した。旧配布assetは差し替えない。

## 運用

[開発フロー](development-flow.md#最新の運用方針2026-11-10-日本時間): 実機ログ→局所修正→単体/関連回帰→必要なIPA/同一性確認→実機。固定時間なし/品質安全条件不変、通常差分レビュー1回。承認済branchへコード/資料保存、raw/画像/report/log/秘密値はGit外。通常利用は同じiPhoneだけ、ユーザーはMacを持たず実機担当。初読3文書≤16KiB、追加資料は[索引](context.md)。
