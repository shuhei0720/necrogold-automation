# 最新状態

更新: 2026-11-13（日本時間）。TEST096の実機4回は受入未達、TEST097を実装・検証中。[今回計画](plans/test097-arrival-continuation.md)・[受領](reviews/test097.md)・[修正表](fix-records.md)。**実機改善・受入は未確認**。単体/CI合格や過去の対策を到達成功へ数えない。

## 今回の実機

4 ZIP/85 PNGを全照合。実順は添付3→4→2→1。実1はUP3歩後の実UPをUNKNOWN8回、実2は開扉後の上端で切れた商品slot0件を保持、実3/4は正常な部分判定後の観測継続を拒否。実4もUNKNOWN/INCOMPLETEで、対象なしは未確定。候補028/052/130/254は実判断sourceで見送りを確認した。前回のPAUSE採用遅延は今回の3判定で再観測していない。

## 修正方針と未確認

既観測床だけの2種類の有限通路仮説、GOLD1を保持する実移動の証明、開扉後の部分観測継続を調査する。空partialを対象なしへ変えず、商品が見える位置へ進む根拠を明示する。旧条件を削除せず、UNKNOWN無再送・候補保持・元期限/累積予算を維持。全商品登録・購入・宝箱開封は追加しない。

各原画像は一度だけPerceptionし、不変Scene/元RGBA/hash/実compilerをGit外に保存。修正部の意味Red→Greenと旧関連、必要な境界試験を選ぶ。全Runtime/worldを通常の前提へ戻さない。将来の到達を合成成功で埋めない。

## 配布済み

[TEST096 IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test096-build171/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test096-build171/source.zip)。build171/code c12e666・closing0f6953f。[配布時の検証](reviews/test096.md)はhost134/現Mac Runtime12/API/spool/Export・実物5種類。これらは今回の実機失敗を否定しない。TEST097は未配布。

新版では通常1-1ポーズから、候補までrestart→接近/入店→3商品が見える位置→のろいのゆびわ判定→対象なしなら次周回までを依頼する。停止通知後iSHで全画像/記録/ZIP照合を待ち、表示run ZIP全体を返却してもらう。回収済みrunの追加回収目的の再実行は依頼しない。

iPhone到達率/毎拍・人超え速度/未知対象精度/長期耐久は未受入。遅延positive通知P1・ledger自動整理なしP2は旧記録を維持。[索引](context.md)。
