# TEST074: TEST073受領と限定修正

2026-11-11（日本時間）。[計画](../plans/test074-visible-evidence.md)。baseline `7901c5fd0f1f4d030923aaab1027b8cc38730e0c`。原ZIP/画像/report/Scene/派生proofはGit外received073/test074-scenes/test074-motionへ保持する。

## 受領と停止理由

添付順ではなくnative started_nsで実行順を照合した。全6ZIP/114選択PNG（20/16/20/20/20/18）のbytes/SHA/全ZIP・PNG chunk CRC/896×414/manifest全offset/hash/cursor/時刻prefix/stable・inflight/active-report/strict API16 schemaが一致。全run terminal/drained/resolved、capture/dispatch failureはnull、取得timeoutなし。保持上限による非収録画像があり、6回目はnative missing7・export omitted9（source68/76追加）、export18/retained20。選択画像の回収は完了しており、追加回収目的の再実行を依頼しない。

| 実行 / run | 元ZIP bytes / SHA256 |
| --- | --- |
| 1 / 4bc9e087 | 3,401,113 / `402579ce7b27ce40c60573f260f51fc22337929c591b253461269cc09ffa7919` |
| 2 / 7414d4ee | 2,877,979 / `b0435f986b4b07fcb398da27beb25281449913dbcb51cbb32489084694e9683d` |
| 3 / 0c7d26c2 | 4,086,262 / `43693332540fd0920c882503d35337d0bf696ab7ca35a2cec045e7b774e45375` |
| 4 / 2e5edcd9 | 4,102,127 / `0ea9a9d12adc2522ed1bbdf5c94ccfe515ed577de476398e88717dec3d0b7f98` |
| 5 / c73a3854 | 3,686,168 / `8495dfc2745454ec7aa29be3d143093f6adbd3ae93eddd83e93e38e206d6f9c8` |
| 6 / 5772e818 | 4,349,585 / `e8d5ea9aa86a56dabc0396c31032b7984c49096b4e15e007ddf72ed7d3dea288` |

| 実行 | MOVED/方向入力 | restart | 停止と画像 |
| --- | --- | --- | --- |
| 1 | 3/3 | 5 | NO_PATH12。初期誤候補の到達不能。途中の31で左金壁を見送り |
| 2 | 2/2 | 1 | SCREEN17。未送信UPの84→86で静止UNKNOWN、元Dまで51.322ms残 |
| 3 | 4/5 | 2 | MOVEMENT10。開扉後のUP ACKをUNKNOWN8評価、2商品だけ見える |
| 4 | 2/3 | 2 | MOVEMENT10。DOWN ACK後UNKNOWN8評価 |
| 5 | 2/2 | 3 | NO_PATH12。初期誤候補の到達不能 |
| 6 | 4/5 | 0 | MOVEMENT10。最後LEFTが原画で1tile変位するがUNKNOWN8評価 |

全商品確認0/6、全6回の最終PAUSE成立。1〜5は計13回のRESTART ACK/新level視覚確認が成立し、最初PAUSEはRESUME ACK後275〜378ms。前回の71/90msでのPAUSE未成立を今回の原因にしない。入力送信と実MOVEDを混同しない。

全114原画を配布073の実C（Controller/Beat O0、Perception/Nav strictO2）で解析。1最終levelの122mask256→166mask0、2の35mask1→69mask0、4の53mask512→88mask0、5の67mask128→103mask0。初期口はFLOORだったが歩行前にSTONE/DIRTへ戻っている。固定world口は移動後に原点を取り直さないための設計だが、初歩前でも誤った旧候補を維持するguard不足があった。1/5はMOVED後約1.05秒で2拍待ちを使い切りNO_PATHへ。

1の31はゲーム時刻0:00.01、左金壁ROI625pxで色比一致435/433px中r>52も満たすのは76/81px、280条件未達で金tile0/peak58/CLEAR。medianRGB42/36/10、HUD除外外。暗い初期1枚を陰性へ確定した問題であり、元閾値を一律に緩めない。6のsource68は非収録。利用可能119はpose(-2,-2)、固定mouth(-3,-2)へのLEFTと観測次床が整合し、goal到達前にmotionで止まっている。今回からgoal延長が必要とは断定しない。

## 変更と検証の境界

描画確認・初歩前候補再検査と、実画像の動作確認を原因別に扱う。旧成功072の初期候補/初歩前画像は非収録で、今回のguardをその実画面で不変と証明したとは呼ばない。合成Scene/時計の制御単体、実画像の局所回帰、実ゲーム/実機受入は区別する。原画から先の未収録移動応答を合成して成功としない。

計画の限定単体/関係回帰と独立差分レビュー1回、新IPA/22seal/実compiler/全Mach-O/全sourceの同一性を確認する。全Runtime/worldは追加しない。具体的なRed/Green・新証拠面・最終配布は以下へ記録した。実機の商品到達、毎拍/人超えは未確認。


## 最終実装・局所検証

Controller SHA `daadf667ec9bf114bae82be4a87aecc5b6e38c7f83557733a7fbb68a79cc22cc`、Nav SHA `1dbde4b4635bb25eaee372e039c5dfc38d210c2853f9ec2dff8e837557745627`。新view9メソッドは固定073 Cへ当時の9試験を結び直しcompile成功の意味的Red9/errors0→Green9/1.607秒。初版Controller34d4で旧UI10とController fullflow/restart12/unchangedrestart/clock/ABI5の関連15はGreen4.137秒。旧UIは意味的Red15/errors0後にfirst FLOOR start+200msの時刻だけ移行、旧ControllerはRed2/errors0後にfullflowとrestartloopへ独立200ms後FLOORを1つ追加し、全assertを維持した。

新motion11メソッドはO0/strictO2でGreen8.587秒。固定073 Navで2機能の意味的Red24subassert/errors0/1.046秒を確認。移動creditへ未来next床を要求してしまう条件も別の意味的Red17subassert/errors0/1.101秒で除いた。旧motion067の6・door072の7はGreen。元分類/score/threshold3は古いbare importの環境error（機能Redでない）を直し、その3だけ再実行してGreen3.264秒。元assert/閾値を削除して通していない。

3の原127→144はprimary UNKNOWNのまま、別のzero-only勾配開扉証明でDOOR_OPENED。中心半差contrast6・両画像の強軸一致・中心と左右上下5点が既知同材質・元opening面/HUD除外を固定。上下差分の標本が重複する帯境界y64/65を両画像で除いた最終結果は349支持/逆8=97.7077%、上119/下230。全73競合は全て支持300未満で、旧texture_lead同義の非競合扱いとなる。架空の競合比や15pp実測値を報告しない。支持十分な競合があれば元15pp条件を要求する。

6の原119→135は、旧STONE2点全てを保つ唯一(+1,0)translationと非共線DIRT・元expanded detail407支持/逆9=97.79%・独立2領域120/151でMOVED(-1,0)。早い119→126/127はUNKNOWNを維持。旧STONE2+は全保持、新STONEは根拠に使わず追加可だが旧集合を二重一致させれば拒否。旧入力先→最新originが実到達点であり、最新のさらに先のUNKNOWN/壁/扉はこの過去creditとは分離する。次入力は既存Nav/safe_stepで検査、未知の再送許可ではない。

19個の実送信に対する保持46原画像の送信方向比較を原C/新Cで行い、変化は3/6の上記2pairだけ、既存nonUNKNOWN21比較は同一。最終観測とsourceの両方が保持された18pair（既知MOVED15/UNKNOWN3）は全て含まれる。独立担当が元catalogue/原hash/新Nav hashを読取照合し、重複C実行なしで一致を確認した。46入力や完全Controller再生とは呼ばず、不正方向は手続的単体の証明範囲と区別する。未保持の未来画像/移動応答を補完せず、現在資料は調整・局所回帰であって未知評価や実機の次の歩行成功ではない。初期200msの端末での十分性、全経路/全商品到達、毎拍/人超えは未受入。

正規pristine+G1からseal/applyし、Controller/Nav2変更・他20/全22source一致。manifest SHA `52a7b13dd6dfab59f3d6a460bc6e83e6595652bbee8daba84855d2371efce3fb`。API16/cap14/v15/Scene/ABI/wire/Runtime/取得/Perception/全元閾値・予算/R12原40/G1不変。独立差分レビューと最終CI/IPA照合結果は下記。


最終確認で、最初のCLEAR/候補から描画途中のGOLD_UNKNOWNまたはtile不整合CANDIDATEへ変わると旧guardが直ちに停止する境界も補った。修正前Controller34d4を固定し、新1メソッドの16条件で意味的Red16/errors0を確認。初期pending/候補待機・同原点level0・確実未送信・商品/保護なしの正常FLOORだけ、旧未送信票/slot/旧初期proofを撤回して元期限内で待つ。実goldは旧handoff、CLEARは新2独立観測へ進む。新state/延長/再送を追加せず、invalid画像・商品保護・送信後・移動後は旧guardを保つ。

最終C daadf667の新view10メソッド（SHA `513db55a06f22717ad7baa30777e58095da1c64dda448909c054439b075fc8a9`）と旧不確実/directfloor・商品保護・unknownsent・cancel/owner4の14件はGreen4.336秒。初期待機の4秒/同期12秒・session/旧callbackを検査した。初版の関連15はその版の過去結果として区別し、最終差分へ関係する4件を選び直している。Nav/testの凍結SHAは上記と同じ。独立担当は正式freezeのC/Nav/新21試験と旧fixtureを静的に確認し、native差分の未解決P0/P1/P2なし、重複試験なし。runner/配布物の確認は次の確定結果へ記録する。


選択runner SHA `1f6b752f89ff0c3645952516a905dd4de1e11039957ce99df778c672c3d24af4`を凍結。新view10/motion11の全21、関連9（UI begin1、Controller restart12/unchanged/goods/unknown-cancel/sync-walk5、Nav全73score1、motion067原分類1、ABI1）、selector3の33件。新21にnewlevel/fullflow/候補保持を含み、旧072bulkは追加しない。TDDのNECRO_TEST074_BASELINE_環境overrideは空値でもpresence拒否し、canonical/bare COREを正規sourceへ束縛、3clientのHEAD/path/blob/委譲・前後source同一性を検査する。独立担当は同hashの全scope/guard/thin入口まで確認し、追加P0/P1/P2なし。host33の実実行とMac/実物検証は下記。


## 最終Mac・配布照合

code `5eff462fa0b53c01c3246c840b606ac8a8a9e02f` / [Mac118](https://github.com/shuhei0720/necrogold-automation/actions/runs/42934281012) device全体成功。新view10/motion11/関係9/selector3の33件・8scopeを実行ID/全log/3client Git blobまで照合し、failure/error/skip/expected-failure0。localではNativeを再実行せず33実import/CORE11参照・override5条件拒否/selector3 Green.013秒を確認し、HEAD後の3client実path/blob/delegateも一致。独立差分レビューは同commit/最終C/Nav/runner/manifest/新旧fixture/契約/入口/source束縛へ未解決P0/P1/P2なし。静的レビューの結論とCI/実機の成功は区別する。

限定Mac Runtimeは既存実070のbaseline意味的Red1→Green6呼出を今回の実4C object/sourceへ結び付けた。元mask/score/ABI/全予算を維持し、無変更Runtime/world全体を追加していない。実compiler4C/5Swift/6RSPとraw log/PBXを照合し、Perception/Nav strict-O2-v2/他C-O0/Swift-Onone、HOST宏非混入。全9Mach-Oを検査し128種のHOST/test marker非混入、主要2binaryはarm64/API16cap14一致。build-source全552ファイルのpath/全bytes/全CRCがGitと一致する。

| 成果物 | ID / bytes | SHA256 |
| --- | --- | --- |
| unsigned outer ZIP | 13817378683 / 17,873,306 | `bfb8f2a929b40360b58414f15e7b576b7bd69586f11b64cbfa99171a5d100135` |
| validation outer ZIP | 13817044096 / 1,223,904 | `76a16cc3e00bcd38734cb4633fb4d388045c025e49903d687aaa209bb398ade4` |
| host outer ZIP | 13816584491 / 8,732 | `77c352a9bde2a991536196178cfb596132668a68b3ab60f66d814646b7562c3f` |
| build-source ZIP | 552 files / 7,556,212 | `aa223b4afe4bce6fb2bfc483bc3603ed328e77df80bedaae68c85be8826c12ac` |
| 内IPA | 17,598,661 | `24032b923fd1201e3b282ce815031791dfc9490f9fa1b3dc7b4526f6274cc5d3` |

内IPAの全CRC・top.ebato.loopctrl/0.3.4/build118/iPhoneOS/min16.0を確認した。delivery/compiler/host/runtime/MachOの実物検証5種は各初回PASS。source22seal/Controller/Nav2変更・他20/R12原40/G1/取得/API/wire/ABI不変を照合。raw/receiptはGit外。

最終sourceはstatus/本検証/実機台帳の3文書だけ閉じ、全製品bytes同一を確認して[固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test074-build118)へ配置する。公開後IPA/source/SHA256SUMSの匿名HTTP200・全bytes/SHA/CRCとAPI digestを照合する。公開後receiptをGitへ足すための配布source再変更はしない。実ゲームCI、074の実機全商品到達、毎拍/人超えは未受入。

次の実機は新しい通常1-1ポーズから候補までrestart→金壁/通路候補へ接近→入店→全商品確認を一連としてまず2回。自動`runtime/test-074-<run_id>.zip`全回分と実restart/候補/開扉/入店/全商品/停止位置/拍間隔を依頼する。回収済み073の追加回収・再実行は不要。
