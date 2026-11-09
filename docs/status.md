# 最新状態

更新: 2026-11-10（日本時間）。TEST060を2回受領。1回目は初歩MOVE予約前にBEAT停止、2回目は左1入力後の移動確認UNKNOWN→LATE停止。商品確認0/2。両runは回収完了/PAUSE/drain済み。詳しいBEAT失効内訳はログ不足で未確定。[受領結果](device-tests/README.md#test060-received)。修正版はまだ作成していない。

[最新開発方針](development-flow.md#最新の運用方針2026-11-10-日本時間)を保存済み。品質を維持し変更に応じて単体/関連回帰/関連結合/フルCIを選ぶ。固定時間の目標は置かない。現在はログ解析だけで、CI/新IPA/回収済みrun再実行は行わない。短いCI経路の実装は未整備。

## 直前TEST060の変更（実機は未達）

TEST059の3歩後の画像比較停止を受けた修正。[受領事実](device-tests/README.md#test059受領結果2026-11-09-日本時間)と原画の解析は保持する。

TEST060は未予約の連続新ordinalだけ、同じ元拍のnotBefore100ms前以降、画像取得開始200ms前以降から初回予約する。移動直後の古い確認画像へ早期に固定せず、最新Sceneと通常plannerを使う。更新前の元Dをactualtickまで保ち、HUD補正による期限後の復活を拒否。予約後期限/再予約/UNKNOWN無再送/商品優先・親motion期限は維持する。[計画](plans/test060-continuous-admission.md)・[長経路期待](tests/test060-world-cases.md)。

200msは画像処理85ms/取得間隔90ms/準備20ms＋余裕5msの合成成功域から導出した値であり、実機性能の保証ではない。原1pxの揺れを再現したworldや、原059の未収録第4入力を再生したと主張しない。

## 直前TEST060の配布物（受領済み）

| 項目 | 保存先・同一性 |
| --- | --- |
| code / Mac CI | `04b213f27364bc9e5cf3c68f9caf031f842fba97` / [Mac91](https://github.com/shuhei0720/necrogold-automation/actions/runs/42632308407) 全体成功 |
| IPA ZIP | [CI配布ページ](https://github.com/shuhei0720/necrogold-automation/actions/runs/42632308407) → Artifacts → `loopctrl-ngg2-unsigned`（13683333087）。17,823,847bytes / SHA `d131787aa5a823a2e9a8fc42da52e73e7cd6ab3c96e7f4a08cda52288d275a11` |
| 内部IPA | `upstream/release/LoopCtrl.ipa` / build91 / SHA `6587ef9794a2efc93295eef66ea558d2e528fdbda27497e66b3eea222dd6dacc` |
| 診断ZIP | artifact13683973589 / 650,690bytes / SHA `6cff2ed87ffa51c868da6285ee9ba40ca368c33132df450e1f869620d4407fb3` |
| native-host | artifact13682046081 / 778,200bytes / SHA `cb49d2b92056a41fbe29c49e29ed8b2db62d3e22dd7bdcec8da710d89816b659` |
| 完全source | [TEST060配布時の固定ZIP](https://codeload.github.com/shuhei0720/necrogold-automation/zip/42e625b0311c79c6d3e6acf19a150b9316fcc2a4)。全462tracked bytes/CRC/path一致、codeとの差分は文書だけ |

codeのbuild-source ZIPは7,204,755bytes / SHA `53d7cb93165ded23883443fc5975a42c35fefdb183af0b6af8a458b3676df19e`、全462ファイル一致。

22seal中Controller.cだけ変更、他21はTEST059baseline5ef0ec3と同一。C `3a16d0b675061dd60b632f419437094e9fea82e90e9027efe01c61910f73f7cb` / seal `3b768e55930227ee0345447d24022717382d776125fcc652a905c232ac8b93e5`、API1.98.14-ngg2/cap12/client v13維持。R12原40/G1不変。これは直前TEST060/build91の配布記録で、当時native修正のためIPA更新を依頼した。現在のルール更新・受領解析では追加更新を依頼しない。過去IPAの保存先はMac CIページのArtifacts。公開releaseは作らない。

## 検証

local Controller184/他native102/world3の計289method、203既知paths、315独立位相、world160到達＋停止2、client197/package228が成功。旧165method/956assert callを保持し、setupのみ新予約時刻へ合わせた。公開258/private31を厳密照合。新C3故障は既存Runtime59/058別2/旧059 C別1から分ける。

Mac91は公開native258/31厳密除外、Runtime既存59＋058別2故障、新060 C3＋旧059 C1故障、独立Swift world16・追加C world160＋停止2、Raster3・C全Scene/Decision parity-field/旧色式Red・暗号RPC・LoopCtrlKitが成功。client197は同一client/launcher/workflowのclient20成功へbindingした。

実PBX/実compilerログ/4C/5Swift/6RSP、22seal、IPA全9Mach-O/82HOST marker非混入を実物照合。実Runtime producer5件→暗号client/両journal、およびworld16→strict v13の診断3配列も一致。合成world・fixture通信の結果であり、Mac実ゲームやiPhone受入ではない。

Mac88/90のHOST時計同期失敗とMac89の診断出力形式失敗は、全体成功には数えない。第3周の補足でHOSTだけを修正し、375require/checker・元D/10msを維持。既存legacy047の未使用helperも古い固定fakeへ型互換を維持するが、旧modeの新しい実Swift試験は未実施。[検証の詳細](reviews/test060.md#test060-final-mac)。

## 今回確認した停止箇所

1回目はinputs/moves=0、reason8/BEAT。同期targetは選ばれていたが初歩予約は出ておらず、準備上限より約118ms前にPAUSEへ移った。capture30はFLOOR/金壁候補/HUD有効。途中25枚と各更新model/sampleが未保持で、track/補正のどの条件で失効したかは断定できない。

2回目はLEFT1、C計上moves=0、reason9/LATE。27→28の初歩再予約後、28→32の実C motionがUNKNOWN。画像上は地形が右へ約34〜35pxずれるが、既存の1歩完了条件を満たさない。確認画像は1枚だけで、motion元Dの2.603ms後に停止。原参照27へ戻してもUNKNOWNで、古い画像への単純な差し戻しでは解決しない。両runともlead_confirmed=0で、TEST060の連続歩行初回予約gateには未到達。

受領済みTEST060は再実行しない。現在は初歩の拍失効内訳と、移動確認画像のタイミングが調査対象。期限/認識閾値を緩めたり、未収録画像で成功を補わない。新しい実装版を作成・確認してから具体的実機テストを依頼する。

## コンテキストと未受入

初読3文書は16KiB以内。旧資料・要件・履歴を維持した[索引](context.md)。生ZIP/PNG/report/解析はGit外。原059の14画像を未知評価へ数えない。

ユーザーはMacを持たずCIでの実ゲームを想定。自己窓CIは画面取得/キー/原PNGの変化だけを実測し、正規ゲーム導入/認証/起動は未成立。Mac実ゲームは未実施で、通常利用をiPhoneだけで完結する要件を維持する。TEST060の実機商品到達、毎拍/人より速い処理、対象指輪の未知評価・通知・自動周回・耐久は未受入。

<a id="test-011結果と今回の変更"></a>

TEST011は[整理前statusの固定版](https://github.com/shuhei0720/necrogold-automation/blob/420c7ce3fb2e1fbe9f9ab7086891dd7e1118ba2e/docs/status.md#test-011結果と今回の変更)に保存した。
