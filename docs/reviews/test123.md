# TEST123: 実機受領・原因・差分検証

2026-11-26（日本時間）。[計画](../plans/test123-device-failures.md)・[修正表](../fix-records.md)。基準は出荷TEST122/build272/CODEf5143e3、保存HEADc7e0944。新IPA/実機改善はまだ確認中で、過去CI/合成合格を新実機成功へ置き換えない。

## 原本と実成功

9ZIP/281member・5run/4campaign・120PNG/143記録を全照合。CRC/SHA、安全unique path、全896×414 decode/RGBA、metadata/記録鎖/hash seal/escrow/strict ledger・checkpoint、内包lastZIP提出原本同bytes、回収completed/drainedを確認し不足0。stable117/inflight3は原状態のまま保持する。全run同Runtime/時刻非重複で、実順はf5a3→66c8→child b6cb→636e→4a98。生原本・PNG・Scene・reportはGit外。

| 原実機の主指標 | 件数 |
| --- | --- |
| 初回RS | root4/4 |
| 実unit/開扉 | 5/5・5/5 |
| 全商品可視 | root3/4＋child1/1＝4/5 |
| 商品後実RS | root1/3＋child0/1＝1/4 |
| 新floor/次child | 1・1 |

66c8/source148は正常policy15/layout1の完全NEGをC採用、durable→実RS15 knownACK→画像168/169でタイマー0:06.39→0:00.01と新floor→b6cb/index1開始まで確認した。終末packet nil/adopted falseはcommit後resetであり成功を否定しない。新21の成功hitではない。他のnamed新資格はprivate途中hit未出力で通しの適用/不使用を断言しない。

独立受領/成功監査は `test123-intake/receipt.json` SHAc727205a と `test123-success/receipt.json` SHA59bce319、出荷来歴の別88項目はidentity SHA4347fab1。ZIP単独のinstalled binary識別と出荷artifact/sourceの一致は別の証明範囲である。

## 原因と計画レビュー

商品31Scene/全6112B packetは旧121/出荷122で同input同値。full停止3件はD内の正常UNKNOWN採用→PAUSE ACK→durable→GOODS。未実行・時間超過・CによるNEG拒否として修正しない。f5a3の実face非HUD/探索ROIだけの1px重複＋縦alias、b6cbのcap上半材質と固定vertical全被覆、4a98の1px横aliasを分けた。直前/後の既完全NEGを今回sourceへ流用しない。周3は正常safe PARTIAL採用後のtop投影＋rail穴でROUTE停止し、後のkernel上書きとproducer status okを区別する。

control短計画は独立P0/P1/P2なし（plan-review SHA69a0c73e）。商品計画のP1 G123-ALIAS-SETは、rowごとの自己整合だけではalias+両外一式を落とせる不足だった。2boardの実bbox中心から期待全seedを復元し、決定的master順/全rowset/両外prefixをexact比較する補正で閉鎖した（goods-plan-review SHAe1e81161）。追加merchant fieldの転用は不要。旧threshold/HUD規則を緩めず、新22/5・marker3に数値意味を限定する。両計画とも通常反復の限定レビューで、全worldや無関係故障集合を増やさない。

## clientと制御TDD

client/cap123は実CPython3.9.25で正式Red17method/28assertion failure/errors0→Green17、直接関連203合格。旧116〜122entry/shell/default、118〜122metadata helper body、旧API/profileを保持し、future-invalid123→124各2literalだけを変更。独立client差分P0/P1/P2=0（review SHA1dcc64bb、author SHA25d9caf5）。selector/host/Py39/wiringの追加は別source/freezeへ分離する。

control新11methodはexact出荷122の最終同fixtureで19意味assertion failure/errors0、修正後11Green/直接旧25Green/skip0。初版Green中にprofile前提（enable_irregular→enable_yield）漏れを発見し、公開資格をearnedするfixtureへ直して旧122の再Redを保存した。初版Redを完全earned実装前Redとせず、compile/環境失敗や誤oracleも意味Redへ数えない。旧ACKの普通goods-first latchは保持する。

新PARTIAL DATAで旧model/slotを撤回する際、sample_countも0にすると、worker100ms＋原currentage31.381ms＋新規2秒fitで元次拍の準備を455,227ns逃し、次拍visualはPを391,967,824ns越すことを確認した。新callerだけ既immutable HUD samples/countを保持し、model/slot/creditは撤回して新正常結果・別current/add_sampleで通常新fitを行う。一般clear_model/clear_slots/add_sample/current_bind/reset_levelとRuntime/Core/Controller.h/Beatは旧同bytes。独立局所deltaレビューP0/P1/P2なし（SHAa8391b96）。

原phase/period/lead/ACK費用を公開earned clockへ平行移動したモデルで、worker100ms・旧currentageと通常UP unitが元P内に成立し1.575秒残る。earned Pはmapped原Pより59.880ms厳しい。最早worker1ns例は2.095秒残。未来HUD/ACKは宣言したcomponent入力で、実機未来再現/速度合格ではない。原120はstart<releaseのためcaller正例に使わず121のみを使う。原constで旧static10/新DATA geometry1を確認し、未出力private状態を原dumpと呼ばない。

DATA枯渇のcounter==2だけを独立にearnedした専用dynamic caseは未実施。新経路0→1消費/再armなし、既>=2 guard/sourceと直接関連の範囲を明記し、未実施を合格に数えない。control最終receipt `test123-control/implementation/final-receipt.json` SHAacb8898b、owned geometry38896e65/caller61f57a91/testb96bfd15。商品/combined最終差分・封印/実CI/IPA/全source/固定配布の結果は実施後に追加する。

## 商品と最終差分

原235/106/169はexact出荷122で3意味Red、新正常22/5の完全NEGとなり、Ring証明とown-anchor Cの両方が受理した。公開新8のexact旧122は11assertion failure/errors0、最終新8Green＋直接旧11件のGreenを確認し、66c8/source148、旧5成功＋19/20/21の全8packet、636e/source119のPARTIALは全6112Bを保持した。新marker3/価格0を含む3packetのJSON・原本保存・ZIP復元は実CPython3.9.25で全値/型/bytes同一（最終transport receipt SHA68b04c9b）。これは通信・保存の範囲であり、Swift実行や実機受入の証明ではない。

combined差分レビューのP1は、新numeric validatorでrow0座標を検査する前にsy+48等を計算し、INT32上下端でsigned overflowを起こせる不足だった。正常board/tagのままrow0/certificateを同時改変する反例を追加し、「診断なしの明示拒否」の意味Red3/errors0→最小前置guardでGreenを確認した。別の新geometryだけfresh word_slotを-1へ揃え、prior reuse/noReuseのmetadata差も閉じる。旧validator/既成功枝は変更しない。性能は元source/worker差を保った実clockで別測定し、固定時計の正常結果を期限達成へ読み替えない。

性能校正ではb6cbの新alias探索が約21.6msを占め、cache確保は約5µsで主因ではなかった。新22だけ30probeの同じinclusive条件をx/y maskへ分け、昇順の同じprobeを選ぶ最適化を採用する。原3packet、10alias対象・1word・取消/期限6cutの全6112Bと全pose/visit順/checkpointが同値。旧helperは全bytes保持し、対象kernelや探索範囲・閾値を変えない。独立局所差分P0/P1/P2なし（membership review SHA f03e8141）。

非同機Linuxへ原sourceageを平行移動した交互3対で、b6cbは元D内C完了が最適化2/3・基準1/3、中央値65.916ms対68.078ms、f5a3/4a98は各3/3。最適化でも1回期限切れが残りall_within=false（receipt SHA7b9ce233）。元68.0325msの残時間や100/150msを延ばさず、3/3になるまでの反復選別・旧枝へのcache介入はしない。全期限の安定達成やiPhone実効速度は未証明で、新実機受入と分けて残す。

最終Ring3270a76c/C0a50e4f8/H7e098d06・fixture490d56e9を固定。mask後の新8だけ再Green、旧11は固定v2Greenと旧helper全bytes保持で再利用し、無関係集合を増やさない。C旧425関数中423/Ring旧147中145の本体を保持し、残る差は限定dispatch/caller/fallback行だけ。Header全POD/API宣言、Runtime/Nav/Perception/Beat/Core/Wire/Spool/Controller.hは同bytes。fresh G1から封印・適用し、37native全実SHA一致、4変更33保持/add0、canonical15/R12原40を保持した（manifest SHA656b9cd3、patch6ee288ac）。

combined独立最終差分はP0/P1/P2残0、receipt SHA83f659a1。商品author最終SHA5bcb1c92、計画24cce8e8へ数字の文書訂正だけを反映し、native/fixtureの再変更はない。新selector14はexact旧122 subjectで11意味assertion failure/errors0→現14Green（実CPython3.9.25）。source-only ASTはhost83＝native55＋cap6＋package8＋selector14、CORE50、実Py39は旧86＋新11＝97、既存変更15/新8を固定した（wiring receipt SHAbaeae5b4、AST352ba86f）。localで全83/97や旧selectorを重複再実行せず、CODE固定の標準CIで検証する。

新read-only readerは旧source/package/compiler/全9MachOの原helperを同SHAで継承し、今回は五項目だけを選ぶ。helper9source/3data・旧actual272のmarker来歴を保持し、実artifactの必須name/typed ID/GHdigestを先に検査する。source/fixture/importの現bytesと83/97のASTを確認し、実CODE/run/buildと全CODE blobの確定前はactual GO/八final flagをfalseのまま保持する。source review SHA d73de7f8、reader e5c61351。旧Runtime/worldの再実行や旧CIの新結果への付け替えはしない。


## 実ビルドと配布前同一性（2026-11-26）

CODE `578a9ef94ecf581d8fdb363efff58b5ff4dd51f5`、[CI274/run45833855464](https://github.com/shuhei0720/necrogold-automation/actions/runs/45833855464)はhost83/実CPython3.9.25の97/実IPA生成が成功。skip/error/failure/expected-failure0を原host ZIPから確認。全18jobは必要3成功/選択外15skip、旧Runtime/worldは再実行していない。

元package19,076,787B/SHA cc367df727e00a24a8ab70e9cd54cbb7f121d98bbe691043303aa1d8c48b3b7f、validation163,940B/SHA201c1da8、host31,944B/SHAa3841efdはGitHubの必須name/typed ID/digest・全bytes/CRCを照合した。IPAはpackage内の元memberを無変換で取得し、18,508,986B/SHA `30a48a1d019f472d49d5450e84431d0d4bdc17e1c6a777ae241f1b29c83863f9`。

CODE flat10,562,039B/SHA80da3a75の全1243Git blob/全bytes/CRC/各SHAを照合。source-only最終fill/aee13805と独立最終差分を確認した後、原8roleとCI identityに結び、rootがactual GO/八flagを確定した。reader e5c61351・scope6b09c525・input3666325cを固定し、read-only五項目 ci/source_package/host_python39/ios_compile/macho がattempt1で全合格した（verification SHA `e4bac2b70778fa2794195c0d28794a56c449c54c6210d31d352fec2cccc1705a`）。37native/API/profile3・実compiler・全9MachOのfixture混入なしを確認。reader内classifier/compiler実行0、新Mac Runtime0。

新iPhoneでの商品到達・対象判定・商品後RS・連続周回/毎拍・速度は未受入。Linux期限校正の1件all_within=falseも据え置く。公式SOURCEと固定3assetの匿名全取得は別工程で検証し、公開後追記する。
