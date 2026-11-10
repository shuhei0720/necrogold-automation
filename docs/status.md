# 最新状態

更新: 2026-11-11（日本時間）。TEST072の4run/45原画で商品全体可視2/4。第1・4回の到達を確認し、第2・3回の再開直後PAUSE未成立をTEST073で修正。[計画](plans/test073-restart-pause.md)・[検証](reviews/test073.md)。200msの端末での十分性と一連の実restart→商品到達は次の実機で確認する。

## 受領と変更

実行順2dd614cc→bd252a30→bd74dabe→f1bafe8d。全4ZIP/45PNGのhash/CRC/manifest/prefix/cursor/report一致、全回収完了。1は5MOVED+開扉1+商品優先UNKNOWN1で3商品100/125/30、4は6MOVED+開扉1+商品優先UNKNOWN1で100/50/100、GOODS/PAUSEとも成立。4のtoo_late履歴と空拍は保持し、回復成功と区別する。

2・3は正常FLOOR/CLEAR/金0/保護0/通路候補0。RESUME ACKから71.289ms/90.355msでPAUSEを送ったが、ACK後もメニュー無しでゲームが約4秒進み、PAUSE確認期限でCAPTURE6。画像取得は正常でRESTARTは未発行、全4runのrestarts0。Nav/Perception/不明金guardを原因にしない。raw/派生証跡はGit外。

073は最新の既知ACK RESUME/RESTART後200msと、その後に取得を開始した最新stable/current-prefix FLOORを得てからPAUSEを予約し、beginでも再確認する。時間だけ経って古い画像から入力しない。商品latchは即時、既にUI遷移から時間が経った成功PAUSEへ追加待ちなし。待機中に通路候補が明瞭化したら未送信skipを撤回して候補へ進む。送信済PAUSE/ACK済RESTARTの新level確認、全予算、UNKNOWN無再送は維持。200msは対策値で最短受付時間の測定結果ではない。

## TEST073配布

code `7da8f9ccbe35de9ae67bae94d583f39e50f47878`/[Mac116](https://github.com/shuhei0720/necrogold-automation/actions/runs/42920344110)成功。新UI10の意味的Red→Green、関連旧12Green、独立差分レビュー未解決P0/P1/P2なし。実CI22/限定Runtime6呼出・22seal/実compiler4C・5Swift・6RSP/全9Mach-O/全546build-source照合済み。実ゲームCIは未実施。

Controller1変更、他21/Runtime/Nav/Core/Perception/取得/元閾値/API16cap14v15/wire/ABI/R12原40/G1不変。IPA0.3.4/build116、17,595,799bytes/SHA `30e069f7dc60dc105ee896c6f5e11fe5985330c3faa32e062d15fd6b41ac95a0`。

[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test073-build116/LoopCtrl.ipa)・[全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test073-build116/source.zip)・[SHA256SUMS](https://github.com/shuhei0720/necrogold-automation/releases/download/test073-build116/SHA256SUMS.txt)。最終sourceとの差分はstatus/検証/台帳3文書だけ、全製品bytes同一。固定assetの匿名GET/全SHAまで照合する。

## 必ず依頼する一連の実機テスト

候補なし開始を含め、リスタート→金壁/通路候補発見→接近/入店→全商品確認を一回としてまず2回。途中の歩数/開扉を完了にしない。毎回新しい通常1-1のポーズから開始する。SideStoreで新IPA更新→LoopCtrl完全終了/起動→Start Server、通常VPNを有効にする。

source.zipを展開し、フォルダ選択ではtest_073.shがあるフォルダを選ぶ。

```sh
mkdir -p /mnt/necro_test073
mount -t ios . /mnt/necro_test073
cd /mnt/necro_test073 && sh test_073.sh
```

短いrestartポーズ中はゲーム前面を保ち、ポーズのまま5秒以上変わらなくなったらiSHへ戻る。`TEST-073: 終了。画像とZIPの保存・照合が完了しました。`を待ち、2回目は同じフォルダで最後の行を再実行。自動`runtime/test-073-<run_id>.zip`全回分と、実restart/候補発見/入店/全商品/停止位置/拍間隔を返してもらう。回収済み072の追加回収・再実行は不要。

## 運用

同じiPhoneのみ、ユーザーはMacを持たず実機担当。実機ログ→局所修正→単体/関係回帰→必要なIPA/同一性→実機。品質/安全条件不変・固定時間なし、無関係な全Runtime/worldを累積しない。既知通路は毎拍、新地形で実route判断が必要な1〜2拍だけ許容。候補保持/UNKNOWN無再送/全画像照合前の終了・次start禁止。raw/秘密値はGit外、既承認branchへ保存。初読3文書≤16KiB、[索引](context.md)から必要資料だけ読む。
