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

計画の限定単体/関係回帰と独立差分レビュー1回、新IPA/22seal/実compiler/全Mach-O/全sourceの同一性を確認する。全Runtime/worldは追加しない。具体的なRed/Green・新証拠面・最終配布は確定後に追記する。実機の商品到達、毎拍/人超えは未確認。


## 最終実装・局所検証

Controller SHA `daadf667ec9bf114bae82be4a87aecc5b6e38c7f83557733a7fbb68a79cc22cc`、Nav SHA `1dbde4b4635bb25eaee372e039c5dfc38d210c2853f9ec2dff8e837557745627`。新view9メソッドは固定073 Cへ当時の9試験を結び直しcompile成功の意味的Red9/errors0→Green9/1.607秒。初版Controller34d4で旧UI10とController fullflow/restart12/unchangedrestart/clock/ABI5の関連15はGreen4.137秒。旧UIは意味的Red15/errors0後にfirst FLOOR start+200msの時刻だけ移行、旧ControllerはRed2/errors0後にfullflowとrestartloopへ独立200ms後FLOORを1つ追加し、全assertを維持した。

新motion11メソッドはO0/strictO2でGreen8.587秒。固定073 Navで2機能の意味的Red24subassert/errors0/1.046秒を確認。移動creditへ未来next床を要求してしまう条件も別の意味的Red17subassert/errors0/1.101秒で除いた。旧motion067の6・door072の7はGreen。元分類/score/threshold3は古いbare importの環境error（機能Redでない）を直し、その3だけ再実行してGreen3.264秒。元assert/閾値を削除して通していない。

3の原127→144はprimary UNKNOWNのまま、別のzero-only勾配開扉証明でDOOR_OPENED。中心半差contrast6・両画像の強軸一致・中心と左右上下5点が既知同材質・元opening面/HUD除外を固定。上下差分の標本が重複する帯境界y64/65を両画像で除いた最終結果は349支持/逆8=97.7077%、上119/下230。全73競合は全て支持300未満で、旧texture_lead同義の非競合扱いとなる。架空の競合比や15pp実測値を報告しない。支持十分な競合があれば元15pp条件を要求する。

6の原119→135は、旧STONE2点全てを保つ唯一(+1,0)translationと非共線DIRT・元expanded detail407支持/逆9=97.79%・独立2領域120/151でMOVED(-1,0)。早い119→126/127はUNKNOWNを維持。旧STONE2+は全保持、新STONEは根拠に使わず追加可だが旧集合を二重一致させれば拒否。旧入力先→最新originが実到達点であり、最新のさらに先のUNKNOWN/壁/扉はこの過去creditとは分離する。次入力は既存Nav/safe_stepで検査、未知の再送許可ではない。

19個の実送信に対する保持46原画像の送信方向比較を原C/新Cで行い、変化は3/6の上記2pairだけ、既存nonUNKNOWN21比較は同一。最終観測とsourceの両方が保持された18pair（既知MOVED15/UNKNOWN3）は全て含まれる。独立担当が元catalogue/原hash/新Nav hashを読取照合し、重複C実行なしで一致を確認した。46入力や完全Controller再生とは呼ばず、不正方向は手続的単体の証明範囲と区別する。未保持の未来画像/移動応答を補完せず、現在資料は調整・局所回帰であって未知評価や実機の次の歩行成功ではない。初期200msの端末での十分性、全経路/全商品到達、毎拍/人超えは未受入。

正規pristine+G1からseal/applyし、Controller/Nav2変更・他20/全22source一致。manifest SHA `52a7b13dd6dfab59f3d6a460bc6e83e6595652bbee8daba84855d2371efce3fb`。API16/cap14/v15/Scene/ABI/wire/Runtime/取得/Perception/全元閾値・予算/R12原40/G1不変。独立差分レビューと最終CI/IPA照合結果は確定後に追記する。


最終確認で、最初のCLEAR/候補から描画途中のGOLD_UNKNOWNまたはtile不整合CANDIDATEへ変わると旧guardが直ちに停止する境界も補った。修正前Controller34d4を固定し、新1メソッドの16条件で意味的Red16/errors0を確認。初期pending/候補待機・同原点level0・確実未送信・商品/保護なしの正常FLOORだけ、旧未送信票/slot/旧初期proofを撤回して元期限内で待つ。実goldは旧handoff、CLEARは新2独立観測へ進む。新state/延長/再送を追加せず、invalid画像・商品保護・送信後・移動後は旧guardを保つ。

最終C daadf667の新view10メソッド（SHA `513db55a06f22717ad7baa30777e58095da1c64dda448909c054439b075fc8a9`）と旧不確実/directfloor・商品保護・unknownsent・cancel/owner4の14件はGreen4.336秒。初期待機の4秒/同期12秒・session/旧callbackを検査した。初版の関連15はその版の過去結果として区別し、最終差分へ関係する4件を選び直している。Nav/testの凍結SHAは上記と同じ。独立担当は正式freezeのC/Nav/新21試験と旧fixtureを静的に確認し、native差分の未解決P0/P1/P2なし、重複試験なし。runner/配布物の確認は次の確定結果へ記録する。


選択runner SHA `1f6b752f89ff0c3645952516a905dd4de1e11039957ce99df778c672c3d24af4`を凍結。新view10/motion11の全21、関連9（UI begin1、Controller restart12/unchanged/goods/unknown-cancel/sync-walk5、Nav全73score1、motion067原分類1、ABI1）、selector3の33件。新21にnewlevel/fullflow/候補保持を含み、旧072bulkは追加しない。TDDのNECRO_TEST074_BASELINE_環境overrideは空値でもpresence拒否し、canonical/bare COREを正規sourceへ束縛、3clientのHEAD/path/blob/委譲・前後source同一性を検査する。独立担当は同hashの全scope/guard/thin入口まで確認し、追加P0/P1/P2なし。host33の実実行とMac/実物検証は後続のCIへ記録する。
