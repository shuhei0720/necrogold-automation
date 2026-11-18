# TEST117: 実機4失敗を基準に判定と歩行の検証を改める

2026-11-18（日本時間）。基準はTEST116/build249（CODE98e2d2d、保存ad32e35）。利用者は4周の失敗を報告し、開発プロセスの見直しを指示した。補助試験の合格を実機改善完了にしない。

## 1. 受領、事象、成功範囲

8ZIP/4campaign/4固有run・96PNG/110記録を全照合。同梱4ZIPも別添と全bytes一致。欠落はない。索引のcompleteは回収状態でありゲーム成功ではない。開始時計順は962c→8efc→098f→3b28。全てchild0で停止した。

| 実機 | 実sourceと失敗条件 | 今回の閉鎖対象 |
| --- | --- | --- |
| 1:962c | 188/189はFULL3品、Ring OK/UNKNOWN・BOARD\|ROWS258。左看板は完全だが右は名称文字/HUDで分断。元行は生成済みでも独立coverage不成立 | 見えている3商品の完全な証明と、隠れた商品を不在にしない条件を分離する |
| 2:8efc | 245はPARTIAL・5連ITEM、UNKNOWN/SCENE1。PARTIAL入店で保護haloをさらに5cross拡張し安全な実destを拒否。中央閉宝箱の価格baselineも違いrow0。247は通常BLOCKED/同maskだがchoice自体が無効でROUTE10 | 実origin/destの正確な保護境界で入店。別baseline価格のrow生成/独立証明と新壁のDATA再取得も分ける |
| 3:098f | 実LEFT2/lead確認後、67→70遠方DIRT/STONE変化で未送信DOWNを撤回。GOLD1/旧STONE0を既静止証明が扱えず元WでBEAT | 同じ元anchor・期限の配置限定zero-only証明。移動creditやグローバルMotionを緩めない |
| 4:3b28 | 実RS6/LEFT2後、215→219零→READY→220/221BLOCKED→222零消失。既回復helperがCLEARを扱わず元W/P内でSCREEN | READYの入力資格を取り下げ再観測する適用漏れ |
| 4:候補128 | DIRT境界の外側に床L/石capがあるが候補mask0。実GOLD0 | 観測済み内床の3歩vantageだけを候補化。壁/未知床へ入らない |

原188右の紫ringは、既086原225の『ゆうきのゆびわ』と局所sprite一致を独立確認した。本物086309/113236とは異なる。価格数字や現UNKNOWNだけを非対象ラベルにしない。245中央の閉宝箱は既正例の形態と一致し、内容を調べず対象外。全画面の機械的陰性証明とは区別する。

## 2. 変更する検証工程

前回normal_chainは単一の非mirror配置と、fit後に都合のよい位相へ動かす時計・分類中の1µs進行を使った。境界単体としての用途と、実機の配置/遅延/表示揺れを検証する用途を区別する。原本600画像のbyte一致は認識・到達の合格ではない。

各失敗を次の鎖で閉じる。①原画像/SHA/source/prefix/原時刻・拒否guardを固定、②修正前の意味ある拒否を再現、③修正後の同cutで次の正しい資格を検査、④未収録の未来は独立したモデルで追加移動/判定/RSを検査。完全な過去Controller状態の復元や実ゲーム再現とは称さない。既成功・対象/類似ring・数値不適格・開始済み・期限外の反例を保持する。

変更helperは必要な状態適用表（CANDIDATE/CLEAR/actualGOLDとOBSERVE/READY/未begin/開始済み）を確認する。全直積の大量CI、無関係な旧フル故障集合は追加しない。今回の独立レビューでは『当該実失敗条件を試験が含むか』を先に確認する。

## 3. 具体設計と不変条件

Ringは通常producerの実画素/ITEM/価格/看板関係を先に確定し、完全な1看板と実3offerからの独立coverageを検討する。断片看板を対象なしの根拠にせず、対象/文字/画像の正の探索領域を狭めない。既coverage policyへ収まらない場合はproducerと独立certificate validatorの契約を先に明記する。全商品名称の登録、価格の固定値化はしない。

PARTIAL入店はFULLで既に使う実origin/destのexact protectionとの適用差を解消する。2重haloを縮めても実destが保護/ITEM/未知なら拒否する。価格は各slotの独立した3群（各18ink/高さ9px以内）、2群の旧baselineと1群の有限lower位置を共有した純画素幾何で発見する案を別variantとして設計確認する。閉容器templateをPerceptionへ複製せず、Ringとのweak依存も作らない。row.sy全体を下げず、本物の上端・旧行/partialの正探索unionを保持する。完全可視の幾何と対象不在の全canonical探索/独立数値certificateは別に証明する。

current PARTIALは通常零・元の潜在商品・未消費観測・新fit・直接2零・元DATA枠/親期限の範囲で再取得する。ROUTE10をPROTECTED9と誤記しない。

FULLの元画像188/189・245/247の採用順cutでは、既DATAのhard rejectionも確認した。新current mode2はMOVE信用を作らず、両FULL/同3ITEM/正確halo/両cap/全下床・元GOLDを保持し、近傍/商品域外の有限な材質変化（newGOLDを含む）だけを許可して最新画像のDATAへ切り替える。MotionUNKNOWNをzeroへ変換しない。旧workerのTARGET/CANDIDATEを先に保持し実return後だけ、元parent/2DATA枠/current一回でfresh分類する。新UNKNOWNはHELD/MOVE0、mode0/1のUPへ落とさず、最新完全陰性と独立C証明/耐久保存/UIだけがRSを許可する。
新GOLDの受理は固定の店領域と歩行範囲を区別し、未知入力/新DOOR/近傍保護の変更を許可しない。

静止は元anchor/source/prefix/通常零/既数値条件を保持する。CLEAR READY後の一時不成立は未送信資格の撤回と再観測だけ。GOLD1+旧DIRTの証明は独立アンカーと既15pp等を保持したzero-only資格として別途設計確認する。67→88/90の数値合格と70/89/91/92の不合格を維持し、閾値低下やSceneの改ざんをしない。元2拍W/親Pを更新せず、期限後・入力開始済み・UNKNOWN送信を回復しない。098の元列でzeroが1/0/1/0と揺れるため、単体zeroの成立だけで同run継続を実証したとはしない。recovery理由4はPREPARATIONであり、先のtrackingモデル失効という解析は訂正した。保存model/原capture/tickの限定cutで次入力の合法性を追加確認する。

Navは128の床L・石cap・独立屋根壁に限定し、既chooserのLEFT/LEFT/UP→(-2,-1)の3歩だけ。壁や暗所は通行許可へ変換しない。金色閾値/既116のFLOOR口は変更しない。

## 4. 初回リスタート（利用者の最新指示）

2026-11-18の最新指示「修正は進めるとして初回もリスタートにして」を適用する。先の条件付き許可から変更となったため、初回RSを実装する。原因修正の代用にはしない。今回3/4は2歩の実MOVEDとlead確認済み、4は既RS6後であり、初回だけ変えても共通原因は閉じない。

TEST117はtrue-only `initial_restart` を専用cap下のirregular startへ指定する。PAUSEならRESUMEを送らず、現在のrestart表示から既UI資格/ACKでRSへ。FLOORなら対象/候補保持を優先し、初回専用PAUSE→RS→実新floorを確認して通常処理へ進む。初回RSは商品陰性/有限yield後終了へ流用せず、最初の通常走行へ続く。元予算/未知入力無再送/取消を維持する。連続rootだけ一度設定し、既にRS後のfreshfloorを引き継ぐ自動childへは継承しない。旧TEST116のflag省略動作を保持する。

C opaqueの専用enable APIとRuntimeのimmutable flag設定を分離し、RPC/startの同UUIDでflag変更を拒否する。PAUSE初期のRESUME0/RS1、FLOORのPAUSE→RS、有限yieldで開始直後終了しないこと、連続successorの重複RS0を変更境界の試験へ追加する。

## 5. TDD、実画像とモデルの範囲

原画像の通常Perception/Ring/Motion校正は必要なpairだけ、実行数/使用source/compilerを私的記録へ残す。画像と非公開資料はGit外。公開試験は必要十分な疎な地形/看板欠け/隣室/元時刻の反例へ変換し、原条件との対応を明記する。

意味Redは同じ元W/P・sourceを使い、compile/getter不備をRedに数えない。許可された固定anchor/数値合格後の一回入力と正常商品の陰性→耐久RS、新floorを直接関連範囲だけ確認する。位相を強制的に有利にする時計補助を実時刻反例の代用にしない。全実機トレース再生は未実装として残す。

## 6. 実装順と所有

受領/旧修正表照合→原因校正→限定設計/必要な独立設計確認→元実装Red→最小Green→直接関連回帰→差分独立レビュー→変更した境界のMac結合→IPA/全source/実compiler同一性→固定Release→実機。Ring/current-PARTIALとstationaryが同じControllerを変更する場合、担当を分けず直列統合する。新gold零証明のGreenは設計確認後。

## 7. 保存・配布・実機受入

修正表の修正日/事象/原因/対策/確認方法/再発数へ、同症状継続・適用漏れ・別原因を区別して記録する。G1/R12/特徴資産/Spool/連続化Runtimeは不必要に変更しない。API/ABIの不要な変更をしない。117 clientは新visible_goods_v1 capを要求し、116 IPAへの誤起動を開始前に拒否する。新共有headerを採用した場合はnative資材37件を封印し、実compilerのinclude依存にも一致させる。nativeを変えた場合の実IPA・実compiler・seal・完全source/固定リンク/匿名全取得は維持する。

配布時は修正点と具体的な通常1-1→連続周回の実機試験/iSHコマンド/全ZIP返却を短く示す。主指標は商品観測→判定→実RS→次周回の成立、歩行の実時刻と対象保持。件数・保存成功だけを改善完了にしない。

## 8. 対象外

無制限探索、全商品登録、未観測陰性、候補破棄、UNKNOWN再送、元期限/入力予算/数値閾値の拡張、初回RSだけで原因修正済みとする回避、PC/別iPhone遠隔運用、課金runner、実機速度の未実測保証。
