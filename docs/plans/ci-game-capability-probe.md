# CI画面取得・入力の独立診断（8項目）

2026-11-09。ユーザーはMacを持たず、実ゲーム試験をCIだけで行えるなら、という意図。TEST056のnative source/入力/配布を変更しない別branch `work/ci-game-probe-056` の測定。

## 1. 目的

標準macos-26の実runnerで、GUI・Metal device列挙・外部の画面取得/入力を測る。device列挙をMetal command実行や実描画の証明にはしない。ゲーム本体・正規導入・認証・実ゲームE2Eは未成立のまま分ける。

## 2. 背景

公式runnerはM1/arm64 VM。日本版1085123767にはM1互換欄とmacOS未検証の表示がある。App Store購入はApple Accountに結び付き、当該ゲームのCI起動は未確認。VMだからGPU/Metal不能とは断定しない。

## 3. 設計

自前のAppKit窓だけを起動し、space入力前後の赤→青描画を外部screencaptureで観測する。別の小さなCGEvent senderから入力する。内部イベント関数の直接呼出しで成功化しない。arm64/OS/Metal device数・GUI/権限・App Storeアプリ有無と入力到達/画素変化をJSONへ保存する。検査は各段階timeoutを持ち、GUI不可/権限拒否/compile失敗は測定結果として区別する。秘密環境変数・account名/host UUID/デバイス識別子は採取しない。

起動した子process PID・自己窓ID/owner・run nonceを照合し、生存/所有を取得と送信の直前にも確認する。送信はそのPIDへのpostToPidだけとし、前面不一致/所有不明なら中止する。画面はそのownerの窓ID指定だけで取得し、失敗時の全画面取得・取得後の切抜きfallbackを禁止する。screen preflightは呼出processの事前判定として別記し、実screencaptureの成否と混同しない。権限request APIや認可設定変更は行わず、拒否/未実施はunknown/blockedとする。

job全体 `timeout-minutes: 8`、helper全体300秒、compile180秒・app準備20秒・capability/owner照合/sender/capture各10秒を上限とし、残helper期限との短い方を使う。SIGTERM/通常失敗/段階timeoutでもpartial JSONをatomic保存し、起動したPIDだけを終了/回収する。keydown後は同じPID/所有へkeyupを必ず対にする。期限後は新keydownを禁止し、所有確認できる自processへの残keyupと終了処理だけを許す。

Python/Swiftのuptime時計を往復の取得区間で相互検証して絶対期限を渡し、不一致時は送信しない。privateなpending記録から所有確認付きkeyup-only cleanupを行い、cleanup中のsignalはflag化して最大10秒の回収を巻き戻さない。測定完了はcleanup成功後だけ。compile診断は自己sourceの固定相対path/行/列/種別とsanitized messageだけを許可し、全stderrやsource echoを保存しない。

## 4. 範囲

このbranchの診断workflow・Swift/Python測定helper・結果だけ。phone client/native/G1/R12には変更しない。標準public macos-26のみ。購入・ログイン・第三者連絡・ゲームDL/ゲームbinary公開・有料runner・権限設定の迂回/自動承認は行わない。

## 5. 期待と限界

外部PNGで赤→青、アプリ側の実keyDown受信、外部CGEvent発行を個別記録し、GUI基盤の能力だけを判定する。入力が届かない/画像がない/描画未変化ならpassにしない。probeを実ゲーム到達やiPhone入力経路の成功とは呼ばない。環境測定なので、未知環境の失敗を機能実装前Redとして数えない。

測定完了とcapability passを分ける。passは同じowner/nonce、外部入力、keyDown増分、draw増分、対応した正常PNG2枚の赤→青の全条件が揃った時だけ。compile/環境取得失敗、GUIなし、権限拒否、timeout、未実施/unknown、欠損/壊れた/古いPNG、owner不一致はpassにならない。正常取得できたのに入力未到達/描画不変/内部状態と外部PNG不一致なら観測されたpipeline failとする。この期待に対する判定器のassertionケースを実装し、環境測定結果とは別に実行する。

## 6. 順序

freshな設計・網羅・安全の計画/実装確認（修正含最大3周）→標準CIの測定→生JSON/自己窓PNGを照合→実施/未実施をユーザーへ説明。nativeのMac74 buildは別に継続。

## 7. 返却

actual run/attempt・checkout commit（git HEADとGITHUB_SHA一致）・許可されたsource file hashes・前後PNG hashes/寸法・summary JSON hashをmanifestへ保存してGit外へ回収し照合する。画像は新規private temp内の自己窓だけ。JSONは許可項目から構築し、環境dump/window全一覧/account/未加工例外はartifactに含めない。mainの最終資料へ狭い結論だけを記録し、実ゲーム試験未実施を明示する。Macをユーザーに用意してもらう前提にしない。

## 8. 対象外

日本版ゲームの導入/Apple Account/receipt、ゲーム画面oracle、Steam/GOG購入・代替版で同一iPhone版を検証したとの主張、phoneの停止修正・速度・商品/周回受入。実ゲーム導入が成立するまでprobe結果はその代用にしない。
