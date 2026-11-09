# 最新状態

更新: 2026-11-09（日本時間）。TEST059受領: UP3後に第4入力前の画像比較で停止、商品未達。**TEST060はMac再検証待ち、新IPAは未配布**。[Mac89](https://github.com/shuhei0720/necrogold-automation/actions/runs/42625173334)のnative258・長経路160＋停止2・新C3故障と主Runtime positiveは通過したが、追加HOST診断が先頭PASSの形式検査で失敗。Mac88の時計同期に続くHOST出力順の補足修正中で、59故障/IPAは未完了。production Cは固定、client20は成功。[今回の計画](plans/test060-continuous-admission.md)・[長経路期待](tests/test060-world-cases.md)。回収済みTEST059は再実行しない。

## 今回の修正と受領結果

TEST059はUP3/MOVED3・商品0。第4MOVEをsource54で予約後、55との比較がUNKNOWNとなりSCREEN停止。2遠方FLOOR→DIRT、次UP/床/金壁/保護は同じ。原画は背景1pxの位相差を示し、motion閾値を緩めて静止と扱わない。残期限67msでlateではない。TEST060は未予約の連続次slotだけ、notBefore100ms前以降・source取得開始200ms前以降から初回予約する。元拍/予約後期限/再予約/UNKNOWN無再送を維持する。200msはL85/cadence90/prep20+5余裕の合成成功域で検証し、実性能保証とはしない。14完成画像と別0入力run/未完了exportを区別。[受領事実](device-tests/README.md#test059受領結果2026-11-09-日本時間)。

TEST058はLEFT2/MOVED2後にlate停止。12PNG/journalsは完全回収・整合pass、商品到達fail。cap54で次DOWN/FLOORを認識できたが、未予約の次notBeforeが親由来deadlineより3.280ms後となり、第3MOVEを作る前に停止した。停止tickは元期限より約113.7ms早く、capture/dispatch failureはない。[受領事実](device-tests/README.md#test058受領結果2026-11-09-日本時間)。

TEST059は親motionの元期限内で移動を確認し、未予約candidateのtarget/10ms窓を同じ補正拍から対更新する。追加observeも元nominal/periodをアンカーとし、初回reserveで一体凍結する。予約済み/SAME/FRESHの期限、8%補正境界、source/model/phase/session/walk予算、取消・UNKNOWN無再送・商品保護を維持する。原058の未収録DOWN応答は作らず、既知12画像と合成Cの証明範囲を分ける。

localはController184/他native102/world3の計289method、203既知paths、315位相、160到達＋停止2、client197/package228が成功。公開CI258/private31を厳密照合し、新C1変更/他21維持、実装第2周3担当clear。build-source ZIP462全tracked bytes/CRC/path一致。Mac全故障・実compiler/新IPAは未完了。[検証](reviews/test060.md)。

## 直前TEST059の配布物（受領済み）

| 項目 | 同一性 |
| --- | --- |
| code / Mac CI | `96c0596a4b7fcad401eb41ceae928af13752ead8` / [Mac87](https://github.com/shuhei0720/necrogold-automation/actions/runs/42603972916) |
| 新IPA ZIP | [build87](https://github.com/shuhei0720/necrogold-automation/actions/runs/42603972916/artifacts/13669198824) / SHA `ebab41e26d65059eda35030180d78a9e04c041f0ee90c68a7fa0ac5e57c26103` |
| IPA内部 | `upstream/release/LoopCtrl.ipa` / build87 / SHA `32554737f90cb60ce2f5d6f0e3cbc1232253d7e13550ae9c0df4a153f1460463` |
| 検証ZIP | [Mac87診断](https://github.com/shuhei0720/necrogold-automation/actions/runs/42603972916/artifacts/13668698927) / SHA `d1adf66cbabc95cff53c45a711f939911aa6e8807c14e2cd71cbdad18deb9eaa` |
| 公開C検証 | [Mac87 native-host](https://github.com/shuhei0720/necrogold-automation/actions/runs/42603972916/artifacts/13666713002) / SHA `4f219c3a1c5751b86a2c4d1d0e3bf9968b2e24d7cdbd5b1c713a6ae05104c0c0` |
| 完全source | [資料込み保存branch ZIP](https://github.com/shuhei0720/necrogold-automation/archive/refs/heads/work/p1-capture-probe.zip)。返却時は最終commitへ固定し、全455 tracked bytes/CRC/pathとcodeとの差分が文書だけであることを照合する |

22seal中Controller.cのみ変更、他21はTEST058と同一。seal `fd95ed27d135c58ebd8872c6c9611a2c41913db3b4e4808bc4b7c9e197543190`、R12原40/G1維持。client v13 / API1.98.14-ngg2 / cap12は不変。**native修正のため新IPA更新が必要**。リンクはSafariで開き、IPAはGitHubログイン後に取得する。

## 検証範囲

旧Cの指定assertion Red→最小Green→旧式rollback Redを確認。Controller165、他native/evaluator99、計264件・189既知paths/skip0、package228、client197が成功。公開native CI236/private28除外と、固定旧/current/rollback各1件の実ログ・hashを照合した。

Mac87は既存Runtime59故障＋TEST058の2故障を全検出し、新C rollback1は別集計。準備callback15・pure16・chain4・pressure3、独立shop world16、Raster3、C全Scene/Decision parity-field・旧色式Red、暗号RPC・LoopCtrlKitが成功。Mac85のHOST時刻assert失敗は成功扱いせず、fixture同期後のMac86重点回帰とMac87全体成功を区別する。

rawPBX/実compilerログ・4C/5Swift/6RSP、22seal、IPA9Mach-Oの81 HOST marker非混入、455file build-source ZIPを実物照合。実producer5件→暗号client/journalと、world16→strict v13の診断3配列も一致。これらは合成world/fixture通信であり、Mac実ゲームE2EやiPhone商品到達の合格ではない。

## 直前の実機手順（TEST059・受領済み）

LoopCtrlをStop Server→完全終了→SideStoreで新IPAへ更新→再起動/Start Server。いつものVPN/ディスクイメージ接続を確認し、完全sourceを展開する。新しい通常オールゾーン1-1で開幕の金壁が見える回を、左側が下・画面端0でポーズする。iSHのフォルダ選択では `test_059.sh` があるフォルダを選ぶ。

```sh
mkdir -p /mnt/necro_test059
mount -t ios . /mnt/necro_test059
cd /mnt/necro_test059 && sh test_059.sh
```

歩行中はゲーム前面を保つ。自動ポーズ後5秒ほど待てばiSHへ戻ってよい。**「TEST-059: 終了」表示後に `runtime/test-059` 全体をZIPで返す。** 壁付近から曲がって進めるか、扉を開けて通れるか、商品が見えたか、連続歩行を確認する。[詳細手順](device-tests/README.md#test-059実行手順)。回収済みTEST058は再実行しない。

## コンテキストと未受入

初読は16KiB以内へ整理し、旧資料・要件・履歴を保持。[索引](context.md)。生ZIP/PNG/reportはGit外。原058の12画像は既知回帰であり、未知評価の合格へ数えない。

ユーザーはMacを持たずCIでの実ゲームを想定。[自己窓CI](https://github.com/shuhei0720/necrogold-automation/actions/runs/42545599822)は画面取得/キー/原PNGの赤→青を実測したが、正規ゲーム導入/認証/起動は未成立。Mac実ゲームは未実施で、iPhone単体要件を維持する。

TEST059のiPhone受入、全経路毎拍・人より速い性能・商品/指輪の未知評価と通知・自動周回・耐久は未受入。

<a id="test-011結果と今回の変更"></a>

TEST011は[整理前statusの固定版](https://github.com/shuhei0720/necrogold-automation/blob/420c7ce3fb2e1fbe9f9ab7086891dd7e1118ba2e/docs/status.md#test-011結果と今回の変更)に保存した。
