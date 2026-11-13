# TEST091受領・TEST092検証

2026-11-13（日本時間）。基準5ddb6c6a38ccab8dc49bcfe518560ceadb99144f。[計画](../plans/test092-startup-stationary-status.md)・[修正記録](../fix-records.md)。実機改善は未確認。

## 受領と判定

初回d503は10,289B/3JSON/PNG0。CRC/安全path/strict load/certificate/canonical sidecar/登録集合が整合。新規startから約426ms、最初のcapture1がmetadata/aspect（828×1792、orientation1）で停止した。正常画像/解析/入力0、JPEG自体未保持で画面の中身は未確定。後の「ZIP保存再開」はこの未公開resolved結果を先に保存する正規処理であり、元のgeometry原因とは別。再実行で起動できた報告も保存する。

追加4ZIPは16,498,098B、77PNG/15,431,058画像Bを全CRC/size/SHA/strict load/certificate/canonical sidecar/登録集合へ照合し全回収完了。添付順ではなく実時刻順を使う。

| 実順/run | 結果 | 方向入力/移動/restart | 公開PNG | 対象判定 |
| --- | --- | --- | --- | --- |
| 1/7702ec73 | goods/paused | 8/6/5 | 20 | authority326・row/3slotあり、個別engine実行済み、unknown/no_target_evidence |
| 2/7a8d5740 | beat/paused | 2/2/1 | 17 | no_authority、個別判定未実施 |
| 3/56df9290 | goods/paused | 9/7/4 | 20 | authority327・row/3slotあり、個別engine実行済み、unknown/no_target_evidence |
| 4/6d609f31 | screen/paused | 0/0/6 | 20 | no_authority、個別判定未実施 |

17枚は保持/公開とも17枚で回収不足ではない。全4回capture_failure=null。nativeの商品完了2/4と、全配置の到達改善・人超え/毎拍の受入を分ける。export対象77枚が揃ったことを全取得frameの恒久保存とは呼ばない。

原326はシャベル/ロングソード/コンパス、原327も対象名/絵を独立目視で確認できない。対象なしの確定や陰性精度の合格とはしない。native engineは各slotで絵/文字を処理する。sidecar word=nullは集約で採用する一致がない意味で、文字engine未呼出の根拠にしない。原画のclassifier再実行/feature調整/ELF再buildは0。

## 原因と変更範囲

7a8d source125→127/152は遠方DIRT→STONEだけ、次UP/reason8/同目標/FLOOR。旧19motion段はUNKNOWN、127→152は静止BLOCKED。原gold2/旧STONE5/非共線DIRT20保存・unique9zero、rawzero .46762/gap .29038、world95%/axis75%の別証拠が成立する。旧static gradientは94.35%で95%条件に不足し、誤った未送信静止拒否から再同期へ入り元期限内に回復しなかった。旧proofを変更せずGOLD専用zero証明を追加する。

6d60原280は正常FLOOR/CANDIDATE/peak158/GOLD tile0で、上端に金壁の切れ端が見える。通常chooseはNO_PATH、旧passageはCLEAR専用でmask0。同じ原地形をCLEARと仮定した調査コピーでmask1/上左口/LEFT経路が成立するが、製品SceneをCLEARへ書き換えない。原280は最終PAUSE sourceで、欠けた最初の拒否279や全過程を代用しない。陽性だが地図内位置を確定できない候補として同じ観測通路だけへ近づく限定modeを追加する。

Runtime起動は既3秒内の新取得・既2秒reply/drain・64回/50msに限定して縦反転aspectだけを再観測する。Raster/EXIF/他failure・正常後の失敗は変更しない。UIは正式sources/早期classifier cacheの有無で実施状態だけを分離し、unknownを対象なしへ変換しない。

## 調光と未確認

現nativeはSpringBoardのlockstateを監視し、ロックはreason4/前面失効は3。今回4回はその停止ではない。LoopCtrl/patchにidleTimer/輝度制御はなく、背景LoopCtrlへ設定して前面ゲームに効く保証もないため調光抑制は混ぜない。取得画像は正常で、間接的な性能影響まで否定する測定はしていない。

## 作者段階の表示試験

新5＋旧表示1を実Python3.9でGreen、有効assertion Redは実施状態が出ない旧表示で先行確認。旧mockの不足reason/sourcesだけを実sidecar形へ補い、対象なし未確定の旧assertを維持した。補助progress088はhostでi386直execがerrno8となり失敗し、意味Red/Greenには数えない。pixel packet書込/実kernel起動は0、旧「判定中」進捗literalを保持し、新表示単体と切り分ける。新helper/import/call/初期noticeを逆変換すると旧2Python本文に一致、schema/feature/native15source/ELF56,088Bは不変。

新C/Runtimeの意味試験・限定CI・独立差分レビュー・配布物照合は結果が揃い次第追記する。未収録の未来画像/実ゲーム応答を生成して成功にせず、実機改善は未確認とする。

## 新Cの作者確認と独立レビュー

GOLD静止の新4methodはO0/strict O2で有効assertion Red→Green。新block/callとpositive通路predicateだけを逆除去すると基準Nav全文に一致し、旧19motion段/順序は不変。後のpositive-only全ITEM/保護guard追加はGOLD証明本文を変更せず、最終mode単体/原Scene校正へ結合した。

新modeは6method＋元GOLD ticketの1methodを別実行でGreen、旧関連7も同じ最終8source/coreでGreen。元Gold票は静止証明後も同ID/source/ordinal/時刻を保持し、100ms/44msの窓前に追加入力/移動credit/回復を作らず、元notBeforeでbeginできることを確認した。runtimeが保持済みの票をtickで再発行する必要はない。作図のpx/grid単位、UNKNOWN表記、不要な再発行を期待したfixtureは目的/既時刻assertを保って訂正し、初回失敗も残した。これらを製品の意味Redに数えない。

最終coreはC f5dc9713/Nav8c8809ecと不変Perception等の8sourceに結合。原Sceneをcacheから再利用し、125→127/152・127→152はBLOCKED/0歩、原280はCANDIDATE158/GOLD0を保ったままmask1/上左口/LEFT-FLOORになる。追加compile/原PNG再分析/Controller呼出0の校正で、未収録279や未来の店内画像は作っていない。別の旧Controllerによる手続きfixture設計調査は最終現Cの試験とは分ける。

同一独立担当が計画とUI/Nav/C/Runtimeを静的に1回レビューしP0/P1なし。GOLDexact2・positive-only全保護/ITEMguard・旧CLEAR不整合拒否のP2を解消。初期2枚/固定mouth、後CLEAR/goal/再取得でのnegative-veto、actualGold/finish/levelでの撤回、元期限/UNKNOWN無再送を確認した。Runtimeはd18e7441、新fixture/checkerを製品編集前に凍結し、Swift不在による事前意味Redの時系列制限はそのまま明示する。限定Macの旧Runtime Red1/現新9＋旧091pin1はまだ未実行。独立したcompile/意味/分類の再実行は0。

最終CIは新Nav4＋新C7＋関連Nav2/C7＋UI6＋selector4の30件を選び、旧38件/全Runtime/worldは再実行しない。公開分の新IPA/実source/実compiler/全Mach-O/source照合はこれから行い、実機改善を未確認のまま保持する。

## 初回CI154と試験ハーネスの訂正

code7f3fdc1/run43349912952/build154のhostは、GOLD4後の新mode7でctypes RecoveryStatusの型エラー8件となり停止した。GOLD窓methodが共有CDLLのargtypesをfixture側の型へ設定し、後続の借用helperが別classの同layout型を渡したため。作者がmode6と窓1を別に実行した順序依存の見落としであり、実機の新停止や製品の意味Redではない。Mac/IPA jobは未開始。

新試験のrecovery aliasだけを署名設定と同型確保を行う既fixture helperへ統一し、typed pointer検査/全8拒否assert/旧ファイルを維持した。実production runnerのimport順で新class7を同processへ並べ、errors8の再現後にGreen7/errors0/skips0。製品/C8source/native manifestと各作者校正は不変、新fixtureだけcccee0427f49bf057d6128da3939169bd258e7154e72693e3b2f6deebeaabebeへ更新した。同じ独立担当が差分・receiptを静的確認しP0/P1なし、再試験0でtest-only commit GO。新CODEの限定CIを開始して全30件を同じ配布sourceへ結合する。

補助selectorの旧参照とexecutorの旧basenameは実物検査前に訂正し、ASTで092参照/固定hashを確認。最初のdraft/失敗出力を保持、これらを実物5gate成功や製品動作確認に数えない。
