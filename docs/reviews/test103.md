# TEST103: TEST102受領と修正検証

2026-11-15（日本時間）。基準4df0a63、実機製品CODE0efbbf31/build194。[計画](../plans/test103-observation-coverage.md)・[修正表](../fix-records.md)。修正後の実機改善は未確認。

## 原本と実機結果

6ZIPは3campaign/runの重複ペア。実順は2a54→5efd→5676。全171原本/88record/77PNG、厳密JSON97件をCRC・安全path・重複・SHA・記録連鎖・session/clock/generation・stable prefix・RGBAまで照合した。元JSONの数値表現/bytesを保存し、再canonical化で原本identityを置換しない。raw資料と診断cacheはGit外、調整ランとして扱い未知評価へ使わない。全原本があり追加回収不要。

| 実機順 | 記録と結論 |
| --- | --- |
| 1 左2歩 | 2a54、商品job0、未送信UP10を144で退役し、149で静止再確認を拒否。SCREEN17。元回復期限は未失効で、期限切れ原因としない |
| 2 商品表示 | 5efd、UP16はDOOR_OPENED、UP17は実ACK済み。280が一時UNKNOWNとなり判定開始前のjob2をkernel/screen停止。Ringの誤陰性/分類時間超過ではない |
| 3 1店舗目 | 5676/cycle1、source260/prefix15をpolicy4でNEGATIVE/COMPLETE、35.223584ms・2410checks・flags0。PAUSE16/source270、耐久checkpoint→intent→RESTART17実ACK→新floor288/prefix17を連鎖で確認。実機で対象なし後の次周回まで成功した |
| 3 2店舗目 | 同UUID/cycle2、source494/prefix30をUNKNOWN/INCOMPLETE、14.397834ms・2042checks・flags258として正常採用後にPAUSE31/source502。候補ではないが完全陰性未成立。商品3個は目視可視。FR102-NEGATIVE-JOINの回帰と断定しない |

## 限定診断

旧Perception/Coreと既libraryの不変hashを確認し、原141/149、270/272/280、494の6枚を各一回だけ解析してScene/RGBAを固定。この6枚は再解析しない。281はまず状態テンプレ画素だけを検査し、原因確定後に実後続の通常確認を検証するため別scopeでfull Perceptionを1回追加して固定した（合計7原本、各1回）。未来像の捏造ではない。

1の141→149は旧normal motionを一度だけ評価してUNKNOWN(0,0)、149自己比較はstrict BLOCKED(0,0)。原141は旧STONE2個で、旧CLEAR補助のexactly1個条件外。scopeを固定した診断で追加の正の静止証明が成立するか確認する。UNKNOWNをMOVEDへ書き換えず、元anchor/world/prefix/期限を持った確実未送信の待機だけを対象にする。

2のpure pixel診断は1回。270/272のpause iconは13px/55で376/400=.94。280は全8候補が不成立で最大353/447=.789709<.8、他footer/zone/floor/非deathは成立。36.896291ms後の281は既9px/55で311/388=.801546となりfloor条件へ復帰。両frameはgeneration1/stable prefix17/非inflight。商人が固定icon ROIへ重なった一時遮蔽であり、FR066/084の旧文字断片と同根因の通算再発は断定しない。認識閾値を変えず、元visualD内の無入力待機で後続の通常FLOORを確認する。

3の494は通常分類1回・同一呼出のcanonical observation snapshot1回・私的compile1回で元certificate/checks/全slot数値の一致を確認。追加の分類/観測はしない。商品と同列の側面入口は左solid5GOLD＋反対側の上下2GOLDで、旧policy4の入口offset=-1に一致しない。実canonical SIGNは左full1枚だけ。旧policy6の2face/共通底辺も成立しない。一方raw両cap/3価格/3商品・既merchant score.996285960/coverage1.0は成立した。旧glyphのIoU.904761905/coverage.913461538は旧閾値不足のまま保持する。別policyの有限正証明を追加し、見えない看板の補完や未観測の陰性化はしない。

## 静止補助の設計確定

原141→149を追加Motionとして再実行せず、旧Navのpure内部snapshotをcompile1回/実行1回だけ取得した。旧STONE2個を保持、共通visible DIRT21/非共線21で9配置の物理zeroが唯一。raw zero .6367323/runner .7511813/gap .1144490/73全有限、world支持795/不一致37、axis1012/134、全72 axis leadは成立。blurのみ(+1,0)=.3019802がzero=.3042838より良く旧全phase最小条件を満たさない。

旧singleton/motionを変えず、別plural資格は物理zero/全旧raw/world/axis条件と、唯一cardinal1signature px競合・他71strict優位・競合axis支持≥300を全て要求する。実unit支持763で既15pp比較が実行される。signature1pxは画面4pxであり、画面完全不動/MOVEDの証明ではなく確実未送信の固定world待機だけの再資格。独立review102が静的GO、具体P0/P1なし。

原281は追加full Perception1回でFLOOR/FULLと確認しcache固定。旧不変Navで原270→281のnormal motionを1回だけ確認しUNKNOWNのままだった。商品優先により移動creditを与えず最新FULLを通常分類へ渡す必要があるため、その経路も変更部の試験へ含める。

## 原281に残る別のcoverage阻害

通常Ring96952をcompileせず再利用し、原281の分類を別scopeで1回のみ実行。15.908705ms/2322checks、policy2/board1/UNKNOWN/flags260。両fullSIGNはboxes[396,30,30,29]/[468,30,30,29]、count574/324で成立するがglyphの旧.94/.95に対し左.836538462/右.653846154。rawcap/価格/merchant/B探索前のreturnなので、それらの0欄は不合格ではなく未実行。

既cacheのpure条件で下入口10固定GOLD/center2FLOOR/両capFLOOR/3ITEM/入口と既2full面は成立。待機修正後にも既知の停止を残さず、計画に別policy8を追加した。旧glyph・policy1〜7・未観測保持を変えず、完全なraw証明は新通常分類と独立C検査で確認する。

## 最終修正と確認

Controllerは3258b2d8、Navigation36cf2f83、Core8ad308d7、Ring6f7ba78d。旧Motion/singleton/旧policy1〜6/旧assertは保持し、Coreは新helperのprototypeだけ追加して旧ABI構造を維持した。native36中の変更は4ファイルだけで、残32/Perception/Runtime/Bank/Coverage/canonical15/ELF/G1/R12/共有099は不変。

C新24＋直接関連16の40件を最終同sourceで一度実行し成功（69.263秒、errors0/skipped0/source不変）。Nav新8＋旧21はO0/strict O2で成功。Ringは59fc時点で新14＋関連39の53件成功後、最終レビューで重要P2を1件検出。policy7 numeric validatorがproducer/Cと同じ半セルmapping・支持範囲を検査していなかった。全x座標+55の証明変造を意味Redで確認し、numeric7だけ限定修正。関連3件成功、producer7/8と他全文bytes不変。旧53を最終6f7で実行したと書かず、選択CIで現sourceの全53を確認する。

独立review102はC/Nav/Core/Ringと最終controlsを確認し、P2限定修正もGO。今回scopeに残P0/P1・重要P2なし。将来fixtureの初期前提不足とloader名の誤記は失敗履歴として保存し、製品Red/実機再発や成功件数へ混ぜない。新pluralのC前提は観測kernelに対応した決定的rendererで成立させてから、旧Cが新futureticketへ進めない意味Redを測った。

元494は通常policy7で完全陰性、38.283581ms/2244checks/flags0で元残99,076,042ns以内。元281は通常policy8で完全陰性、37.829568ms/2452checks/flags0（元worker未実行なのでfresh100ms校正）。compile1/classify各1/hooks0/追加Perception0。numeric7修正後は既Resultのpure検証だけ各1回行い、両方成功/bytes不変、再分類しなかった。原141→149の新Nav補助も1回だけ校正して資格1、Scene不変。

元2Result/Sceneを最終Cのfresh公開cycle/observe/worker/assessへ各1回渡し、両方NEGATIVE/COMPLETE/OKとして採用された。元数値本体は変えず結果時刻だけ宣言した模擬時計へ正規化、prefix0のfresh状態であり、実prefix17/30全履歴・Runtime・実ゲームUIの再現ではない。通常producer→公開C→PAUSE/耐久保存/intent/RESTART実ACK/新floorは手続き的結合試験で確認し、実機改善とは区別する。

証拠の限界: Nav Redの実行時Nav/Core/generated shimとbefore receiptは保存済みだが、編集前Python assertion moduleはhashのみで別copyを保存していなかった。完全なPython/compiler bundleと偽らず、named inputsの保持として記録する。旧Redの再測定やsource再構成は行わない。最終Python sourceとcompiler入力のhash/実行は別に結合する。

TEST103の薄entryは番号だけ変更、共有099 engine不変。実Python3.9と開発Pythonで--check、shell構文が成功。選択CIは一意product122件/22scope（新46/関連76）とselector6＝128件/23scope。CI定義169保護sourceはbaselineと全bytes一致、native/source/成果物の確認を行う。新しいRuntime/Mac部品試験や全合成worldは変更範囲外なので再実行せず、Mac191/C4101は歴史的証拠だけとする。IPA作成・実物照合・固定公開はこれから。修正後の実機到達率/速度/精度/耐久は未確認。

## DEVICE196と配布物の照合

DEVICE196/run43685183886、CODE `ec14bbb5f7128e266039603476a00c2301bdca25` は成功。最終同CODEで一意128件/23scope（product122/新46・関連76＋selector6）すべて実行成功、skip/error0。新しいRuntime/Mac部品試験は追加せず、IPA自体はmacos-26で実ビルドした。

未署名IPAはbuild196、18,045,643 bytes、SHA256 `55e554e191c5b728e3f4ed5a5b8a61e0d1e2ecd4b90af7cec3619e00ec858bf4`。原artifact IDはunsigned14150941276/validation14151025885/host14150675486。API digest・全ZIP bytes/CRC/path/重複/Info.plistを照合。CODE完全sourceは908ファイル/9,105,876 bytes、SHA256 `4151952d5a398f3b50dfe8c60c27e5a2f2314015998405715767ac1dcef4c503`、全Git bytes一致。公開sourceは終了資料だけを加えたcommitから作る。

package/host/retained/macho/compileの五つの読取照合が成功。native36/変更4、1691 marker（旧1620＋新71）、9 Mach-O、実C8/Swift5とcompiler response/filelist/profile・seal来歴を照合した。照合時の追加semantic/compiler/classifier実行0。最初のhostはroot記録の表示label不足、次は凍結した正規Zig-LICENSE/musl-COPYRIGHTのsuffix外で拒否。表示labelに既検証green_scopeを使い、2ライセンス名だけを許可する狭いreader差分を独立確認後、passed packageを再利用して未完了だけ再開した。失敗履歴を保存し、5種類/7attemptを区別する。spec/source/CI/権限/元bytes条件は変えていない。

| 照合 | receipt SHA256 |
| --- | --- |
| package | `7da6e61c28cd828b590f36f82cf62f4581c374608aa682f12a8f98fa4b77b6cc` |
| host | `e4886a981168cc0fea06ef9826663790f963a85916019ce8b6b7670b9673a8e0` |
| retained | `09518670b67a536d6b1bfda62e55618fa47d4eb6ce7782151345889a25cb7400` |
| macho | `ee22d8ea0b8b1b8cf8aa2ffaf53df9049518bea507731c900b93dc3bfb5d7249` |
| compile | `c08ad4af6581b71be0cc4cc7bfdc4b3a60b9ed141bf660580a9abf5a010b4311` |

修正後実機の到達率・次周回・毎拍/人超え速度・未知精度/耐久は未確認。固定Release `test103-build196` の匿名全GET/全bytes/hash/tagは公開後に追記する。
