# 最新状態

更新: 2026-11-09（日本時間）。TEST059は上3歩後に第4入力前の画像比較で停止し、商品未達。TEST060では連続歩行の初回予約を新しい画像から作るよう修正。Mac91全体成功・新IPA/ソース/実compilerを照合済み。TEST060の実機試験待ち。実機の商品到達・全経路毎拍・人より速い実効処理は未受入。回収済みTEST059は再実行しない。

## 今回の変更

TEST059の4th MOVEはsource54→55のmotion UNKNOWNで停止。原画は共通1rawpxの地形ずれがあり、motion閾値を緩めて静止とは扱わない。notBeforeへ57ms/Dへ67ms残り、lateではない。14完成PNGと別0入力run・未完了exportを区別する。[受領事実](device-tests/README.md#test059受領結果2026-11-09-日本時間)。

TEST060は未予約の連続新ordinalだけ、同じ元拍のnotBefore100ms前以降、画像取得開始200ms前以降から初回予約する。移動直後の古い確認画像へ早期に固定せず、最新Sceneと通常plannerを使う。更新前の元Dをactualtickまで保ち、HUD補正による期限後の復活を拒否。予約後期限/再予約/UNKNOWN無再送/商品優先・親motion期限は維持する。[計画](plans/test060-continuous-admission.md)・[長経路期待](tests/test060-world-cases.md)。

200msは画像処理85ms/取得間隔90ms/準備20ms＋余裕5msの合成成功域から導出した値であり、実機性能の保証ではない。原1pxの揺れを再現したworldや、原059の未収録第4入力を再生したと主張しない。

## 配布物

| 項目 | 保存先・同一性 |
| --- | --- |
| code / Mac CI | `04b213f27364bc9e5cf3c68f9caf031f842fba97` / [Mac91](https://github.com/shuhei0720/necrogold-automation/actions/runs/42632308407) 全体成功 |
| IPA ZIP | [CI配布ページ](https://github.com/shuhei0720/necrogold-automation/actions/runs/42632308407) → Artifacts → `loopctrl-ngg2-unsigned`（13683333087）。17,823,847bytes / SHA `d131787aa5a823a2e9a8fc42da52e73e7cd6ab3c96e7f4a08cda52288d275a11` |
| 内部IPA | `upstream/release/LoopCtrl.ipa` / build91 / SHA `6587ef9794a2efc93295eef66ea558d2e528fdbda27497e66b3eea222dd6dacc` |
| 診断ZIP | artifact13683973589 / 650,690bytes / SHA `6cff2ed87ffa51c868da6285ee9ba40ca368c33132df450e1f869620d4407fb3` |
| native-host | artifact13682046081 / 778,200bytes / SHA `cb49d2b92056a41fbe29c49e29ed8b2db62d3e22dd7bdcec8da710d89816b659` |
| 完全source | [資料込みbranch ZIP](https://github.com/shuhei0720/necrogold-automation/archive/refs/heads/work/p1-capture-probe.zip)。最終返却は文書保存commitへ固定し、全462tracked bytes/CRC/pathとcodeとの差分が文書だけであることを照合する |

codeのbuild-source ZIPは7,204,755bytes / SHA `53d7cb93165ded23883443fc5975a42c35fefdb183af0b6af8a458b3676df19e`、全462ファイル一致。

22seal中Controller.cだけ変更、他21はTEST059baseline5ef0ec3と同一。C `3a16d0b675061dd60b632f419437094e9fea82e90e9027efe01c61910f73f7cb` / seal `3b768e55930227ee0345447d24022717382d776125fcc652a905c232ac8b93e5`、API1.98.14-ngg2/cap12/client v13維持。R12原40/G1不変。native修正のため新IPA更新が必要。IPAの保存先はMac CIページ。SafariでGitHubログイン後、Artifactsの loopctrl-ngg2-unsigned を選ぶ。公開releaseは作らない。最終返却では実取得を確認した期限付き直接リンクも渡す。

## 検証

local Controller184/他native102/world3の計289method、203既知paths、315独立位相、world160到達＋停止2、client197/package228が成功。旧165method/956assert callを保持し、setupのみ新予約時刻へ合わせた。公開258/private31を厳密照合。新C3故障は既存Runtime59/058別2/旧059 C別1から分ける。

Mac91は公開native258/31厳密除外、Runtime既存59＋058別2故障、新060 C3＋旧059 C1故障、独立Swift world16・追加C world160＋停止2、Raster3・C全Scene/Decision parity-field/旧色式Red・暗号RPC・LoopCtrlKitが成功。client197は同一client/launcher/workflowのclient20成功へbindingした。

実PBX/実compilerログ/4C/5Swift/6RSP、22seal、IPA全9Mach-O/82HOST marker非混入を実物照合。実Runtime producer5件→暗号client/両journal、およびworld16→strict v13の診断3配列も一致。合成world・fixture通信の結果であり、Mac実ゲームやiPhone受入ではない。

Mac88/90のHOST時計同期失敗とMac89の診断出力形式失敗は、全体成功には数えない。第3周の補足でHOSTだけを修正し、375require/checker・元D/10msを維持。既存legacy047の未使用helperも古い固定fakeへ型互換を維持するが、旧modeの新しい実Swift試験は未実施。[検証の詳細](reviews/test060.md#test060-final-mac)。

## 実機手順（TEST060）

LoopCtrlをStop Server→完全終了→SideStoreで新IPAへ更新→再起動/Start Server。通常のVPN/ディスクイメージ接続を確認。完全sourceを展開し、新しい通常オールゾーン1-1で開幕の金壁が見える回を、左側が下・画面端0でポーズする。フォルダ選択では test_060.sh があるフォルダを選ぶ。

```sh
mkdir -p /mnt/necro_test060
mount -t ios . /mnt/necro_test060
cd /mnt/necro_test060 && sh test_060.sh
```

歩行中はゲーム前面。自動ポーズ後5秒ほど待ったらiSHへ戻ってよい。「TEST-060: 終了」後に runtime/test-060 全体をZIPで返す。連続歩行、開扉、入店、商品が見えるかを確認する。[詳細手順](device-tests/README.md#test-060実行手順)。

## コンテキストと未受入

初読3文書は16KiB以内。旧資料・要件・履歴を維持した[索引](context.md)。生ZIP/PNG/report/解析はGit外。原059の14画像を未知評価へ数えない。

ユーザーはMacを持たずCIでの実ゲームを想定。自己窓CIは画面取得/キー/原PNGの変化だけを実測し、正規ゲーム導入/認証/起動は未成立。Mac実ゲームは未実施で、通常利用をiPhoneだけで完結する要件を維持する。TEST060の実機商品到達、毎拍/人より速い処理、対象指輪の未知評価・通知・自動周回・耐久は未受入。

<a id="test-011結果と今回の変更"></a>

TEST011は[整理前statusの固定版](https://github.com/shuhei0720/necrogold-automation/blob/420c7ce3fb2e1fbe9f9ab7086891dd7e1118ba2e/docs/status.md#test-011結果と今回の変更)に保存した。
