# 最新状態

更新: 2026-11-10（日本時間）。TEST068の1runを受領。4歩後に扉前で停止、開扉/商品確認なし。16選択PNG中12枚保存、残4枚のままhost_deadlineとなった。今回は追加回収を依頼せず、添付済みの証拠でTEST069を開発する。[受領台帳](device-tests/README.md#test068-received)。

## TEST069: 全画像保存と未送信開扉の再観測

[計画](plans/test069-collection-gate.md)・[検証記録](reviews/test069.md)。回収の完了前に「終了」と表示しないことを優先する。

TEST068のゲームは6.706秒で停止・drained/入力確定。回収manifestから最終chunkまで87.728秒、RPC23.596秒に対し呼出間64.132秒。共有iOS mountへ109 atomic/14,443,914 bytesの細かい同期保存を行い、90秒制限に達した。前版の修正は再開時の重複writeだけで初回保存に効かなかった。

TEST069は `~/.necroprobe/runtime/test-069` のiSH内永続保存に変更し、全画像のmanifest/cursor/SHA/PNG/active-report一致を確認してから、現在runだけのZIPを共有側へ一括copy・whole SHA照合・rename・再照合する。端末内原本は保持し、公開途中の中断は次ゲームより先に処理する。返却物は自動作成される `runtime/test-069-<run_id>.zip`。旧TEST068は削除/移行しない。

terminal/drained・input0/3・非inflight/非凍結・未取消を確認したpaged回収だけ独立300秒。ゲーム180/歩行45/再同期12秒・入力上限/UNKNOWN無再送は不変。回収中にstart/入力/keepalive/cancelを追加しない。unsafe/旧非paged/既取消のcleanupは従来どおり。未完了に終了表示や次startを許さない。接続前失敗などnative未開始は画像回収完了と区別し再接続可能にする。

扉前停止は入力id9の送信前判定。原画130→133は同LEFT/reason5/target(-1,0)/DOOR・gold/局所/保護不変だが遠方2セルが変わり、motion UNKNOWNで旧quietが拒否。score .50899で旧.45を超え、構造95%も未達なので閾値は緩めない。確実未送信の同closed doorだけ1run1回、旧IDを撤回し独立した新画像対のstrict BLOCKED、fresh HUD fit、新ID/将来拍prepを要求する再観測へ進む。元12/45/180秒を保持し、送信UNKNOWNを再送しない。

## 検証と配布

code `6180eacf3bec8c9ecb0e65c889339f9483ef383d`、[Mac108](https://github.com/shuhei0720/necrogold-automation/actions/runs/42804504968) device50件成功（native16/client31/selector3）。新34件は意味的Red→Green、独立設計/安全レビューの全P0/P1を修正。nativeはControllerだけ、他21/API15/cap13/ABI/clientv14・Runtime/Swift/wire layout不変。

実IPA/build108 SHA `47ae26f5d512abd8bf0fefc8fa85707fc50d9e0713a754a07a55680694f77dda`、17,588,938bytes。22seal・host全ID/生ログ/両client実driver/Git blob/SHA・実4C/5Swift/6RSP/strictO2・全9Mach-Oの109禁止marker非混入・build-source全517tracked bytes/path/CRCを照合。他21/R12原40/G1不変。最終sourceはcodeから文書3件だけ異なり実装同一。TEST069の実ゲーム/実機は未実施、商品到達/速度/保存完了の合格は未宣言。

[新IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test069-build108/LoopCtrl.ipa)・[完全source ZIP](https://github.com/shuhei0720/necrogold-automation/releases/download/test069-build108/source.zip)・[SHA256SUMS](https://github.com/shuhei0720/necrogold-automation/releases/download/test069-build108/SHA256SUMS.txt)。固定Releaseへ保存、公開後の匿名GET/SHA確認まで行う。[詳細](reviews/test069.md)。

SideStoreで新IPA更新→LoopCtrl完全終了/起動→Start Server、通常のVPN/ディスク設定。sourceを展開しtest_069.shのあるフォルダを選び、新しい通常All Zones 1-1・金壁可視ポーズから実行する。

```sh
mkdir -p /mnt/necro_test069
mount -t ios . /mnt/necro_test069
cd /mnt/necro_test069 && sh test_069.sh
```

歩行中ゲーム前面、自動ポーズ後約5秒でiSHへ戻り前面のまま`TEST-069: 終了。画像とZIPの保存・照合が完了しました。`まで待つ。自動作成された`runtime/test-069-<run_id>.zip`をそのまま返してもらう。まず新しい1-1で2回、商品全体の可視/停止位置/歩行間隔/全画像・ZIP保存完了を確認する。複数回なら全run分。TEST068の追加回収は不要。

前版は [TEST068/build106固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test068-build106)。受領068の商品確認未達・回収未完了を前版CI46件の成功で埋めない。

## 運用

[開発フロー](development-flow.md#最新の運用方針2026-11-10-日本時間): 実機ログ→局所修正→単体/関連回帰→必要なIPA/同一性確認→実機。固定時間なし/品質安全条件不変、通常差分レビュー1回。無変更Runtime/world全体をCIへ累積しない。承認済branchへ保存、raw/画像/report/log/秘密値はGit外。同じiPhoneだけ、ユーザーはMacを持たず実機担当。初読3文書≤16KiB、[索引](context.md)から必要資料だけ読む。
