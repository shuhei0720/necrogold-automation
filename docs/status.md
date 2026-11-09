# 最新状態

更新: 2026-11-09（日本時間）。TEST058を受領し、次ordinalの拍補正と古い期限による空窓停止を確認。TEST059を開発中、新IPAは未配布。[計画](plans/test059-next-slot.md)。

## 今回の修正と受領結果

TEST058はLEFT2/MOVED2後にlate停止。12PNGとjournalsは完全回収・整合pass、商品到達fail。次DOWNは認識できるが、未予約の次notBeforeが親由来deadlineより3.280ms後となり、第3MOVEを作る前に停止した。TEST059は親motion期限を維持し、未予約candidateのtarget/窓だけ対更新して初回reserveで凍結する。旧Cのassertion Red→最小Greenとrollback Redを確認し、回帰中。[受領事実](device-tests/README.md#test058受領結果2026-11-09-日本時間)。

TEST057はRIGHT1/MOVED1後、次UPの送信が期限に間に合わず停止。経路外のDIRT→FLOORでSAME再予約し、observe後の残余5.017msに対しAX照会11.312ms。capture失敗ではない。次UPへの床は認識できるが、入店/商品確認は未達。[受領事実](device-tests/README.md#test057受領結果2026-11-09-日本時間)。

TEST058はC epochで同logical MOVEの資格を証明し、元のfresh前面確認/leaseを共有。重い診断JSONを入力直前から外し、準備済みで期限到来した入力を直実行する。全期限・予算・商品保護・取消/UNKNOWN無再送を維持する。独立worldへ実gestureをつなぎ、木/鉄扉・四方向・迂回掘削の開通→進入→商品→PAUSEを検査した。[計画](plans/test058-shop-dispatch.md)・[16例](tests/test058-world-cases.md)・[検証](reviews/test058.md)。

TEST057 ZIPは完成7PNGの途中checkpointで、strict評価はintegrity invalid/到達unknown。直接原因の証拠は保持され、追加回収の再実行は依頼しない。

## 直前の配布物（受領済み）

| 項目 | 同一性 |
| --- | --- |
| code / Mac CI | `5a190d3285d8f32cc0aa381d35d4566e8e27766f` / [Mac84](https://github.com/shuhei0720/necrogold-automation/actions/runs/42586379842) |
| 新IPA ZIP | [build84](https://github.com/shuhei0720/necrogold-automation/actions/runs/42586379842/artifacts/13660334564) / SHA `33e13bfe060610f1c96a562bbebdc8505d275c718a8416b515d15efd4af5db79` |
| IPA内部 | `upstream/release/LoopCtrl.ipa` / build84 / SHA `0ed81f68c50986d60848293b9c0a5c9fc54664c4a23626d6c9d0dd0487491f20` |
| 検証ZIP | [Mac84診断](https://github.com/shuhei0720/necrogold-automation/actions/runs/42586379842/artifacts/13661456112) / SHA `3d12b0720bc4d4a4f6ab204d1d9a3a3dd9b8770efe547b47d8d3081834b7e7f8` |
| 完全source | [保存branch ZIP](https://github.com/shuhei0720/necrogold-automation/archive/refs/heads/work/p1-capture-probe.zip)。配布時は資料込みcommitへ固定して全tracked bytes/CRC/pathを照合する |

native22sourceの変更はController.c/.h/Runtime.swiftの3、他19はTEST057と同一。seal `0cf5028c40ed5cf7daebb2d9013fa446adc1dcce99849841570e4ed5d311040e`。client v13 / API1.98.14-ngg2 / cap12、R12全40/G1原bytesを維持。**native修正のため新IPAへの更新が必要**。Stop Server→完全終了→SideStoreで更新→再起動/Start Server。新1-1開幕金壁可視・左側が下・画面端0のポーズから `sh test_058.sh`。

## 検証範囲

Controller153件、local native/evaluator249件・177既知paths/skip0、client197、package226成功。公開native CI224/private25除外、client CI18の197件も成功。固定旧RuntimeのMac assertion Red→新Runtime Greenを確認。実callback15・pure16・連続再予約4・診断圧迫3を通し、旧59＋新2故障を別集計で全検出した。

Mac84はworld16/Raster3/C全Scene・Decision parity-field/旧色式Red/実RPC/実compiler/IPAすべて成功。rawPBX/4C・5Swift・6RSPを実ログへ結合し、22seal・IPA9Mach-OのHOST非混入・450fileのbuild-source ZIPを照合。実producer5件→暗号client/journal、world16→strict v13/診断3配列も一致。合成world・fixture HTTPは実ゲームE2Eではない。[独立レビュー・途中失敗の記録](reviews/test058.md)。

歩行中はゲーム前面を保つ。自動ポーズ後5秒ほど待てばiSHへ戻ってよいが、**「TEST-058: 終了」表示後に `runtime/test-058` 全体をZIPで返す**。回収済みTEST057は再実行しない。

## コンテキストと未受入

初読は16KiB以内へ整理し、旧4資料・要件・履歴を保持。[索引](context.md)。生ZIP/PNG/reportはGit外。AIの原画像目視は暫定で、未知評価の合格へ数えない。

ユーザーはMacを持たずCIでの実ゲームを想定。[自己窓CI](https://github.com/shuhei0720/necrogold-automation/actions/runs/42545599822)は画面取得/キー/原PNGの赤→青を実測したが、正規ゲーム導入/認証/起動は未成立。Mac実ゲームは未実施で、iPhone単体要件を維持する。

TEST059のiPhone受入、全経路毎拍・人より速い性能・商品/指輪の未知評価と通知・自動周回・耐久は未受入。

<a id="test-011結果と今回の変更"></a>

TEST011は[整理前statusの固定版](https://github.com/shuhei0720/necrogold-automation/blob/420c7ce3fb2e1fbe9f9ab7086891dd7e1118ba2e/docs/status.md#test-011結果と今回の変更)に保存した。
