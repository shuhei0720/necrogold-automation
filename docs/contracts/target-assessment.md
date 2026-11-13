# 対象指輪のローカル判定

[要件GOODS-01/02](../requirements/necrogold.md)・[TEST087計画](../plans/test087-target-pause.md)。対象は「のろいのゆびわ」。native `goods` は商品可視性であり個別種類ではない。

## TEST094専用の端末内判定・周回

`necrogold_native_cycle_v1` / `normal-1-1-cycle-v1` だけ、同じiPhoneのnative workerで直接RGBAを分類する。[限定契約と閾値・保存・回復・通知](../plans/test094-native-goods-cycle.md)を適用する。全3商品/余剰なし/独立layout・各品identityの証明が揃ったnegativeだけ、耐久checkpoint/intent・新しいPAUSE資格・実ACK/変化したfloorを経て次周回へ進む。宝箱は中身を判定せず、正に識別した閉容器だけ対象外。対象/候補/不明/故障は保持し購入しない。PARTIALの限定OBSERVE_MOREとUNKNOWN無再送、元期限/累積予算を守る。

iSHは終了後の全画像/記録/ZIP照合を担当し、判定を再実行しない。通知のrequestedはOSへの受付で、実配信の証明ではない。iPhone速度/未知精度は未受入。以下は既存profileの後処理契約で、新profileへ無断fallbackしない。

## 既存profileのデータと判定

既nativeの全商品可視/ポーズ・入力drain後、同iPhoneのiSH内で判定する。外部へ画像を送らず、新しいゲーム入力を出さない。入力は同runの最終ACK PAUSE authorityを先に、必要時だけ同prefix/stable/非inflight/非交差の保持proof1枚を使う。画像上限2、896×414の原寸と有限3slot/scale/探索範囲・取消を維持し、正式sidecarは全画像certificate後に確定する。

看板・3価格/商品列を観測から求め、同画像・同じ商品slotのiconと表示名を空間的に結合する。価格の数値やrun/capture番号、特定runの固定座標を識別条件にしない。対象文字は「のろいのゆびわ」のderived glyph、iconはpublic既存R12 assetからのderived feature。raw/cropをGitへ保存せず、featureの出典hash/ROI・版/校正用途を記録しlegacy40filesを変えない。

| 結果 | 意味 |
| --- | --- |
| target | 同一slotでiconと対象名の独立条件を全て満たす |
| candidate | 対象らしいicon等はあるが対象名を含む全条件は未成立。保持する |
| unknown | 可視/資料/一致/判読が不十分。対象なしとはしない |

実3原309を正例、原225の別ringと他商品を校正に使った。新原寸featureの固定閾値はicon候補≥.80、targetはicon≥.88 AND word IoU≥.82/coverage≥.90。raw原308は飛行中なのでpixel校正でだけcandidate例にし、本番sourceへ入れない。隣接画像・変形を別run未知評価へ数えない。対象なし/自動リスタートを新たに判断しない。

## iSH内の画素処理と早期表示（TEST089）

Pythonは元のchunk/CRC/寸法/有限inflateを担当し、同梱static i386 helperがunfilter0..4/全画素alpha=255/観測・icon・名前探索を実行する。最大4行×3slotのraw doubleを親で元min/round9/判定順に集約する。3.9–3.11の逐次sumと3.12の補償sumを区別し、未検証Python版は明示失敗。raw iconは数学上界の丸め余裕0..1.000001だけ受理する。C内でdecimal丸めやtarget判定をしない。名前の探索範囲が幾何的に空の左右端でのみword:nullを許し、絵が見えればcandidateを保持する。

固定ELF/全source/feature/toolchain SHAをmanifestへ結合し、homeの専用0700cacheへ検証して配置する。shell/任意engine path/遅いPythonへのfallbackなし。固定長入力・相関SHA・閉schema・有限stdout/stderr・30秒期限と取消を検証し、故障は子を回収して固定reason/pendingとする。SHA相関echoをC内の独立hash計算と呼ばない。故障/時間切れをunknownや陰性に変換しない。

TEST089だけはread-only/drainedのterminal manifest下でauthority画像を優先取得し、個別SHA/寸法/durable保存後に暫定先行結果を表示できる。元metadata/offset/prefix/保存画像順を変更せず、取得indexだけ優先する。authorityがtargetならproof分類を省く。memory cacheはrun/export/source SHA/feature/classifier/protocolへ結合し、最終certificate後のbefore_prepareと分類時に資格・再読込画像を照合する。全画像照合前のsidecar/完了/次startは0。observer失敗は診断回収を続行し、最終prepareで必ず失敗する。既定Noneの旧client動作を維持する。

商品到達、暫定判定、全画像/ZIP完了の各時間を別に測る。早期表示で診断回収自体が速くなるとはしない。開発機/QEMUの倍率はiSHの人間速度達成の証拠ではない。固定実8runは陰性4/不明4、未知陽性0。校正正例/合成明度・位置・欠けの検証を未知陽性評価へ数えず、稀な対象を出す実機周回をユーザーへ要求しない。

## 保存と回復

`active.json` / native `report.json` の閉schema/bytesを変えない。初回archive前に `target-assessment.json` をatomic保存し、元inventory/ZIP/SHA/receiptに結合する。sidecarは版・run/report/asset/source hash・固定reasonとbounded evidenceを持つ厳密schema。現時刻/任意path/例外自由文を入れずdeterministicにする。

入力入替・symlink・foreignrun・未知field・余計なファイルを拒否する。既sidecar/ZIP/receiptは勝手に上書きせず、未完なら同runを先に再開し新ゲームstart0。旧entryのhook既定None・旧ZIP互換を保つ。evaluatorがsidecarを受理する場合も、この1名と閉schema/参照画像hashを検証する。

iSHへの結果表示はOSバックグラウンド通知ではない。今回、対象通知/対象なし循環・未知runの識別精度・iPhone後処理速度を達成済みとはしない。target/candidateでも既ゲームのポーズを保持し、自動購入しない。

## 診断用の原画像回収（TEST088）

対象判定の長時間化で通常ZIPが未完成の場合、既publication lock/certificate下で登録済み全PNGと元active/reportだけを別の証拠ZIPへ出せる。ファイル名はtest-088-evidence-<uuid>.zip、別storage/別schema receiptを使い、通常archive/receiptやsidecarは変更しない。未完成part/未登録資料を混入させず、全CRC/SHA/元bytesの照合を行う。これは診断回収だけで、対象判定/通常出版完了や次run開始の許可ではない。通常の判定はpendingとして保持し、unknownや陰性を捏造しない。
