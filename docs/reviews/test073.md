# TEST073: 再開直後のPAUSE確認失敗

2026-11-11（日本時間）。[計画](../plans/test073-restart-pause.md)。baseline `c99f3850b315c82ef2330d50460415b6527e34b3`。TEST072の実機で成立した商品経路を保ち、候補なし時のUI遷移だけを修正する。

## 受領と実画面

添付順と実行順は異なる。device started_nsの昇順で2dd614cc→bd252a30→bd74dabe→f1bafe8dが1〜4回目。全4ZIP/45PNG（16/7/7/15）のCRC/SHA/bytes/896×414/全PNG chunk CRC/manifest/export全offset・hash/cursor/時刻prefix/stable・inflight/active-report一致。全run resolved/terminal/drained、原本と証跡はGit外received072/test073-scenes。

| 実行 | ZIP bytes / SHA256 | 実画像・実Cの結果 |
| --- | --- | --- |
| 1 / 2dd614cc | 4,375,121 / `251e3bfdcde4d6c6fd64b2a756802bd1a5a27d77a88466644ad4fb2c1928b52f` | 5MOVED+開扉1+商品優先UNKNOWN1、3商品100/125/30、GOODS/PAUSE |
| 2 / bd252a30 | 1,558,975 / `3c2e01a61ad841cd3613d6e82584ecf8d2bebb62b4fa4525188304d40c4082c0` | 0方向入力、PAUSE未確認、CAPTURE終了 |
| 3 / bd74dabe | 1,574,248 / `8523fae040f944e4cda0176d320286a2164fac66a7f5b315b460b4f1e905f491` | 0方向入力、PAUSE未確認、CAPTURE終了 |
| 4 / f1bafe8d | 4,425,229 / `0ffe8c675991f4209d461ff6c9bd318a5bb8b505fa66ebf5173e1a136f82b4ed` | 6MOVED+開扉1+商品優先UNKNOWN1、3商品100/50/100、GOODS/PAUSE |

商品全体可視2/4を確認。1の原画164・4の208に3品と価格、173/217にPAUSE/restart_label1が見え、実Cも一致。4の未送信too_late履歴（id10、query開始D+2.444ms/mainEntryD+9.757ms）は保持し、その後の回復成功と区別する。方向間隔は1で約.515〜.525秒、4は1.570/1.035秒の空きがある。今回は速度変更を混ぜない。

2/3のsource21/23・final127〜130はFLOOR2/GOLD_CLEAR1/GOODS_UNKNOWN0/実gold0/全保護0/通路候補0。初期分類やCLEAR整合guardは正しい。RESUME1→PAUSE2ともACK、PAUSEのobserved_capture_id0/paused0。RESUME ACKからPAUSE beginまでは71.289375ms/90.355417msで、ゲーム時刻は1.61→5.90/1.57→5.82と進行しメニュー無し。ACK後4.003/4.004秒でCのUI遷移確認期限が切れCAPTURE6。最後まで画像は受理、取得/RPC/dispatchのfailureはない。全4runのrestartsは0で、この2回はRESTART/fingerprint判定前に止まっている。

## 対策の範囲と限界

既知ACKのRESUME/RESTARTから200ms以上、かつその時刻以降に開始した最新stable/current-prefix FLOORを得てからPAUSEを予約し、beginでも再確認する。既存のPAUSE→RESTART待ちと値を揃えるが、端末の物理的な最短受付時刻を測定できたわけではない。実画面で受付しなかった原因と200msの十分性は次の実機で確認する。

商品latch/以後MOVE・RESTART禁止は即時、既にUI遷移から時間が経った1/4の保持PAUSEには追加待ちを入れない。待機中に金・通路候補が明瞭になった場合は未送信skipを撤回して最新の候補へ移る。送信済PAUSEとACK済RESTARTの新level確認は別扱い、未知入力や実未成立PAUSEの自動再送はしない。Controller以外21source・Nav/Perception/Runtime/取得・全閾値/元予算/ABI/wire/API16cap14v15は変更しない方針。

## TDD・レビュー・配布確認

固定072 Cでcompile成功/errors0の意味的Redを先に確認。新UI時刻1methodは実ログ71/90msと200ms−1の3assertFAIL、最新通路候補1methodは待機/未送信PAUSE/ACK済PAUSEの3assertFAIL。合成UI応答を実端末の反映成功にしない。

新機能・関連回帰・独立した差分レビュー1回と、native1変更の新IPA/22seal/実compiler/全Mach-O/全source/固定Release匿名GETを確認する。無変更の全Runtime/worldや072全45試験を既定で累積しない。新073の実機成功は未確認。候補なし開始を含む一連テストをまず2回依頼し、全商品までの到達と実restart成立を確認する。回収済み072の追加回収は不要。


## 最終実装・選択検証

Controller `b359cca905ede11a6157d55e55b2f46a76ac3c8772fd5d78c5961c9cd663d3ca`、新UI試験 `a0e8ee1028142bb9659d2981e3dca88f7b4703b530af9148df531e35741038a6`を凍結。新10メソッドGreen1.642秒、関連旧12Green3.834秒。旧resume/restart fixture2箇所は新200ms契約へ衝突するassertion Red2/errors0を先に確認し、FLOOR観測時刻100ms→200ms+2nsだけ変更、全assertを維持した。

予約前/保持PAUSE/beginの3段へ共通helperを適用し、bounded eventの最新ACK済RESUME/RESTARTだけを根拠にする。elapsedと取得開始を差分比較し200ms境界/跨ぎ・古い画像・wrong prefix/unstable・clock/owner/cancel/UNKNOWNを検査。既にUIから時間が経ったPAUSEと直接FLOOR開始に追加待ちなし。待機中の通路候補は未送信票を撤回し優先、送信済PAUSEとACK済RESTARTの新level証明は区別する。

通常の独立差分レビュー1回でC/新試験/旧fixture/計画/契約/launcherを確認。暫定hostrunnerに旧072bulkが残る指摘は、完成runnerで新UI10/関係9/selector3へ差替え、CORE sealed source差替えと全source/HEAD bindingまで確認して閉じた。最終未解決P0/P1/P2なし、重複実行なし。

選択CI22メソッドを確定。正規sealed sourceはController1変更・他21、22seal前後同一、manifest SHA `7c9c29946607c4dbeec02d24c3744fa8d8087defb209ce76dab7fa894fc9de62`。既確認Nativeを重複実行せずselector3だけGreen.005秒。IPAの実ビルド/実compiler/全Mach-O/全sourceは下記へ確定後追記する。新073の実機は未確認。
