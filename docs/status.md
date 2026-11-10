# 最新状態

更新: 2026-11-11（日本時間）。TEST072の4run/45原画を受領し、商品全体可視2/4を実画像・実Cで確認。第1・4回はGOODS/PAUSE成立、第2・3回は候補なし判定後のPAUSEが画面に反映されず停止。TEST073で再開直後のUI準備待ちを修正中。[計画](plans/test073-restart-pause.md)。新UI10/関連旧12Green、独立差分レビュー未解決なし。CI22/22sealを確定し、新IPAを作成する。073実機は未実施。

## TEST072受領

実行順2dd614cc→bd252a30→bd74dabe→f1bafe8d（添付順とは異なる）。全4ZIP/45PNG（16/7/7/15）のhash/CRC/bytes/896×414/manifest/prefix/cursor/report一致、全回収resolved/terminal/drained。raw/派生証跡はGit外received072/test073-scenes。

1は5MOVED+開扉1+商品優先UNKNOWN1で3商品100/125/30、4は6MOVED+開扉1+商品優先UNKNOWN1で100/50/100。実GOODS/PAUSEとも成立。方向送信を全歩数にしない。4には未送信too_late履歴と1.57/1.035秒の空きがあるが、その後回復して到達。初故障履歴を成功で消さず、今回速度/認識の変更を混ぜない。

2・3は正常FLOOR/CLEAR/金tile0/商品0/保護0/通路候補0。RESUME ACKから71.289ms/90.355msでPAUSEを送りACKも得たが、メニューが出ずゲーム時刻が約4秒進行。画像は終端直前まで正常受理、PAUSE observed_capture_id0/paused0のまま約4秒後CAPTURE6で終了。RESTARTは未発行、全4runともrestarts0。取得/RPC/dispatchのfailureは2・3にない。通路判定・CLEAR整合guard・restart fingerprintより前のUI反映待ちの失敗。

## TEST073の範囲

最後の既知ACK RESUME/RESTART後200ms以上、かつその時刻以降に開始した最新stable/current-prefix FLOORを得てからPAUSEを予約する。200msは既存PAUSE→RESTARTの待ちと揃えた対策値で、端末の受付最短時間を測定できたという意味ではない。時間だけ進めて古い画像から入力せず、beginでも再確認。商品latchは即時、既にUI遷移から時間が経った成功回のPAUSE/歩行は遅くしない。PAUSE失敗/UNKNOWNの再送は追加しない。

待機中に通路候補が現れた場合も未送信skipを撤回して最新候補へ移る。送信済PAUSE/ACK済RESTARTの境界と新level証明を混同しない。Controller1件だけ変更予定、他21/Runtime/Nav/Core/Perception/API16cap14v15/wireABI/各予算・元閾値は維持する。

## 配布・運用

現行は[TEST072/build114](https://github.com/shuhei0720/necrogold-automation/releases/tag/test072-build114)、code8a54beb6e5b046b7ec801afbe4e7339c2eb4e702/[検証](reviews/test072.md)。新073は機能Red→Green/関係回帰/独立差分レビュー1回→必要な新IPA/22seal/実compiler/全Mach-O/全source照合後に固定Releaseで返す。無変更Runtime/world全体は累積しない。

次の実機も「候補までリスタート→金壁/通路候補→商店→全商品」を一連でまず2回。候補なしの開始を含めて実restart成立を確認し、短いrestartポーズ中はゲーム前面、ポーズが5秒以上続いてからiSHへ戻り保存完了を待つ。自動run別全ZIPを返してもらう。回収済み072の追加回収・再実行は不要。

同じiPhoneのみ、ユーザーはMacを持たず実機担当。品質/安全条件不変・固定時間なし、実機ログを主に局所修正。既知通路は毎拍、新地形で実route判断が必要な1〜2拍だけ許容。商品候補保持/UNKNOWN無再送/全画像照合前の終了・次start禁止、raw/秘密値はGit外、既承認branchへ保存。初読3文書≤16KiB、[索引](context.md)から必要資料だけ読む。
