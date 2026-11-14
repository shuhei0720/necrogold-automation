# TEST100: 入店停止・商品判定・左下候補

2026-11-15（日本時間）。[計画](../plans/test100-observed-shop-stops.md)・[修正表](../fix-records.md)。開発中、実機改善未確認。

## 受領と原因

6添付は3個別runと同じ内容のcampaign wrapper。13e3/3444/9c66の時刻順で24/24/25PNG、26/27/28record、合計160原本。全ZIPのpath/重複/symlink/CRC、manifestと原record SHA/連鎖、画像登録/896×414/RGBA SHAが成功。native浮動小数の17桁表記をPython再serializeへ置換せず、原bytesを正本にした。全campaign cancelledはcleanup結果で、利用者取消やゲーム成功とは断定しない。

実1の初回stopは232→233、実開扉17の後の未送信LEFT18、FLOOR7。唯一の材質差は遠方(-3,+1)DOOR→GOLD、両Sceneの同LEFT/reason5/床判断・strict BLOCKED。opened_entry_floor/実ACKは成立し、opened_entry_relationだけ不成立。元deadlineの122.8ms前で時刻超過ではない。

実2はsource456で3商品可視、判定19.070ms/採用1.584ms後で元100ms期限内。列267/189は正しい。旧glyph証明と12金の下側構造が適合しないためUNKNOWN/incomplete、flags260=GLYPH|ROWS。3商品・価格の実pixel/Sceneは7金の側面入口下形に対応。旧価格群には剣先1pixelも余剰として入る。対象なしへ丸めず、別構造証明を用意する。

実3はsource223→225の部分商品再検証ROUTE10。新ITEM2セル、保護6セル増加、同LEFT/reason5/床、strict BLOCKED。cycle_partial_choiceは同一で、cycle_partial_distant_dirtが保護検査前に拒否。新商品は旧partial結果の対象外なので、最新画像の別jobで再分類する。元horizonは2.8秒以上残る。

見逃し59は左下口(-3,+2)DIRT、外側(-4,+2)FLOOR・両flank壁・4歩の内床。旧mouthはDIRTを候補にしないためmask0。新bit9もDIRTを通行可能へ変換しない。

現Perceptionは必要6枚を各1回だけ校正し、不変Sceneを私的cacheへ保存。以後0回。rawScene/元画像/原logはGit外、保持画像の関係成立を未来到達や未知精度へ流用しない。

## 設計レビューと進行

独立計画レビューはP0なし。新PARTIAL jobの最新immutable画像がRuntimeの通常workerへ渡る限定Mac callback一件が不足というP1を計画へ反映し、実装GO。C単体と旧Runtime bytes一致だけで新しい連携を合格にしない。全Runtime故障/worldは再実行しない。

Nav/商品Ring/clientラベルの分割差分レビューは残P0/P1なし。Navは新6/関連45、Ringは新9/関連25と同製品の旧bank20、clientは実3.9の新4が成功。各意味Redを実装前に保存した。Navの接続外床fixtureは既存bit7が正しく立つため期待0を128へ訂正し、新6だけ再確認、旧45は同sourceの結果を保持した。

Ring原456は旧/新で各1回だけ分類し、新policy4/board4で完全陰性。全探索host40.900ms、元100ms/cancelは保持し、iPhone性能受入にはしない。Bank/Coverage/canonical15/56,088B ELFは変更しない。

新Ring9と新Controller5が同じ未追跡test名を選んだ衝突をCI/sourceレビューで検出。Controllerを別path/classへ移し、Ring元9は凍結SHA074403c45ec237e5b2f0e847dfdb037dc0c20a955f5b4bce4360f44828c54298へ全bytes復元した。保持copyと復元証跡を保存、製品変更/通過済み試験の再実行なし。旧assertの削除で成功扱いしていない。

Cの最終同source単体/関連、限定Mac callback、実IPA/配布物・全source照合は後記する。実機の停止解消/商品到達率/毎拍・人超え速度/未知対象精度は未確認。

Controller最終C ac437fdb9c4c200bf34e4848173c971c3e443c51ed87db8d9db6d0eeb36cbdc1で新18＋関連8が全合格。保持Sceneの実1はopened-entry関係が成立し、実3の旧partial関係はROUTE10を維持しながら、新helperでjob2/source225/pending1へ移り、旧horizon4503739067166を厳密に保持した。これは復元した限定preconditionでのhelper校正で、完全な実機replayではない。独立C差分レビューGO、元Runtime/headerは不変。

最初の限定Mac run43622545811/build185/code62a2ffcはC/Swift compile成功後、対象case前のactual_runtime_startで拒否された。artifact14125110516、50,487B/SHA13e88e102c529e0ffd421af537ed7ea17f74f37d5bf971511e59ce8fae07d68a、CRC照合済み。起動error本体が未出力なのでrawcodeは未確認。fixtureが通常のcycle prepare/ready待ちを省いており、source上の通知準備前拒否条件を満たすため、fixtureだけに通常prepareと起動error診断を追加した。元start/job2 assertionと製品guardは保持する。この失敗は意味Redに数えず、限定caseだけ再実行する。全fixtureの再実行は行わない。
