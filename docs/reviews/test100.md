# TEST100: 入店停止・商品判定・左下候補

2026-11-15（日本時間）。[計画](../plans/test100-observed-shop-stops.md)・[修正表](../fix-records.md)。build187、実機改善未確認。

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

## 現CI・実物

最終CODE4ba361d3ca3ec12d4e068294c245546a4b4c1c6d。Mac186/run43623513420は同CODEで通常prepare後、旧Controller39851a4の`partial100_latest_item_exposure_binds_job2_before_new_worker`だけがassertion Red、現ControllerはGreen。artifact14125700027、55,549B/SHAd8f6628a2375348e7d41faa63874806732f1e9c7e697e9cf5382ad24325eea94。17:54:04Z完了はdevice187の17:55:25Z作成より前。source/通常worker/最新immutable B・旧job拒否・候補保持/追加方向入力0・元horizonを結合した。歴史的歩行/開扉だけHOST seed、Scene/RGBA/resultは手続き的で、実画像456のproducer→Controller完全校正や分類精度/実機E2Eの証明にはしない。

device187/run43623716812は変更37＋関連78＋selector6の121件/21scope、実IPA compile、compiler profile3/C8/Swift5、パッケージ来歴が成功。旧Mac API/spool/export/Runtime096/099の広い試験は今回は未実行、不変sourceに結合した183の履歴を保持した。

package/host/retained/Mach-O/compilerの実物5検査が初回の各1回で全PASS、追加試験/compile/分類0。独立helperレビューGOのreaderSHAf977f3986de25f916751933c9307e5b8bbda4461d33f4699f8e6f39fe4ec1109へ固定し、全9 Mach-Oから旧1372＋今回100のfixture/HOST markerを排除した。native36中の変更3、旧ABI6と別StopDetail120/Handoff64、Runtime/header、Bank/Coverage/canonical15/ELF/G1/R12を照合した。

作者6scopeのRedには私的凍結sourceがあるものと限定receiptのみのものがある。Nav/Ring/B/Dの実行時source未保持を後のfinal sourceで置換せず、最終同sourceのGreenは今回CIで別に結合した。テスト名衝突の復元とfixture訂正も保持し、compile/環境失敗を意味Redへ数えていない。

IPAは18,026,453B/SHAbf6828a19bdd4d65228c8416cb1bb1b1a19c9da9a97475b2cb80a8ba910c637c。unsigned artifact14125262813は18,446,821B/SHAafeedce56c02c3e8a8bffdeaf404f38eafb935a8e6f22a786b341bc27bc573f0。validation14125397202/host14125590825もAPI digest・CRC・安全path・全来歴を照合。build CODEのsourceは867 tracked files/8,922,326B/SHA66d97aac9b332b574c47e7693efb155f0da91da53ceb8843e9da2054dfe1ee29、全bytes一致。公開sourceはこの検証結果だけのdocs closing commitへ結合し、非docs差0/全source bytes/固定Releaseの匿名全GET/hash/tagを公開後に追記する。

実機は`sh test_100.sh --until-target`で探索→商店→全商品確認→完全陰性の次周回を依頼する。対象/候補/UNKNOWN/障害では保持、終了後は全画像保存・ZIP照合完了したcampaign返却ZIP。商品到達率・毎拍・未知対象精度・長期耐久は未受入。

## 固定配布

publisher188/run43625480323が成功し、Release445493721/tag `test100-build187`を公開。closing e74f8eb6e60a050032088c4c55ecbc0406f587f5の変更はdocs5pathだけ（renameを含めず差を列挙）、製品/試験/workflow等の全非docsはbuild CODEと同一。公開全sourceは867ファイル/8,923,843B/SHAce242ae6706e84e3ac927362e95a017c49b855c2bff978dd8ae173ca267f4db0、全tracked bytes/CRC一致。

[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test100-build187/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test100-build187/source.zip)・[SHA](https://github.com/shuhei0720/necrogold-automation/releases/download/test100-build187/SHA256SUMS.txt)を匿名で全GET200し、原本の全bytes・SHA・Release digest・tag commitを照合した。IPA SHAは上記のbf6828a1のまま。公開後のこの記録追記はdocsのみで、固定asset/tag/ビルド済み製品は変更しない。
