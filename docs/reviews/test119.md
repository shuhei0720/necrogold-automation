# TEST119: TEST118の実機停止への修正

2026-11-25（日本時間）。[計画](../plans/test119-device-failures.md)・[修正表](../fix-records.md)。基準はTEST118/build263（CODEdca8ca3、保存64f7b4f）。実機資料から原因別に修正し、CI266の実IPAと6項目の照合を完了。固定公開後の匿名取得確認は別記し、iPhone受入は未完了。

## 実機で分かったこと

9ZIP/4campaign/5run・132PNG/154記録のCRC/SHA/全PNG decode・RGBA hash/metadata/prefix/記録鎖・escrow/campaign/内包lastZIP同bytesを照合した。資料不足はない。原本はGit外、未保存の画像やprivate状態は補完しない。

| 実順 | 確認した停止/成功 |
| --- | --- |
| 5fd | LEFT1実MOVEDの後、未開始DOWNの比較元109→110更新は通常FRESH。110→111の通常strict零と新床露出で次判断がLEFTへ変わると、refreshed-source guardが既ROUTE待機前にSCREEN。109→111は通常UNKNOWNのまま |
| a1 | 全商品は上端で欠けPARTIAL。233→235の同choice/保護/ITEM/次床/strict零は成立、遠方DIRT→STONE1セルだけで既quietが拒否し観測へ進めない |
| 893 | 3商品は可視。中央100価格と同xの上方白1pxを結合し旧boxが不成立、独立に中央が7px下の価格配置も旧証明外。正常Ring完走でもUNKNOWN、最終は元source150msを1,875ns超過 |
| 3f | source199/job4/policy17、全3商品/3価格を完全陰性として元D前64.756959msで採用。durable→RS18の既知ACK→新floor221→qualified/seal→同Runtimeのef child開始が実機で成功 |
| ef | 早期FULL174/175は元LEFT166に対しUNKNOWN、176/177は同元166から通常LEFT unit。旧entered-refreshのprotected露出条件/次床判定に入らず停止。13GOLD/右cap黒を完全陰性にしない |

3fの末尾assessmentnull/adoptedfalseは新floor後のresetであり、checkpointの完全陰性adoptedtrueを否定しない。child重複初回RSはない。回収開始の実時刻は記録に無いため「回収ゼロ秒」とは主張せず、元Runtimeの耐久seal/drain→advance/childにhost exportの前提が無いことと実lineageを照合した。成功した周回継承を、他の失敗の解消とはしない。

## 検証の範囲

各修正で原画像/実時刻と拒否guardを結ぶcutを置き、正式試験の旧assertion Red→最小Green、直接関連を確認する。未保存live model/元private stateを適合する宣言値で補った公開cutは完全実機再生と区別する。新しい未来画像を使う独立公開modelは未知端末の成功ではない。

TEST119 client/capは実Python3.9で新17件の意味的Red→同testsのGreen、旧116/117/118関連81件もGreen。119専用capとnamespaceを追加し、旧118のcap/metadatafield、初回rootRSと同root回収/連続周回を保持。旧117/118の未許可サンプル119は、正式119追加に伴い120へ移しただけで拒否assertは残す。cap/client独立差分レビューP0/P1なし。最終CIは最新53clientを選び、116の無関係34件を新規実施へ数えない。

通路6・価格8・PARTIAL2・松明床5・late entered7の新28件は原因に結ぶ旧assertion Red→修正後Greenを確認し、直接関連も確認した。製品差分の独立レビューはP0/P1なし。全132画像の旧/新Perception比較で、efの4画像/5セルの床回復以外はScene全bytes一致。3fの成功判定packetも全bytesを保持する。これらは未知iPhone画像や実速度の受入ではない。

最終製品sealは37nativeのうちController/Perception/Ring/RPCの4ファイルだけがTEST118から変化し、残33・Runtime本体・API/native_v15/ABI/profile3を保持する。新しいsource所有が既Runtimeの画像lease/worker返却境界を跨ぐため、TEST119限定Mac1case/normalとcandidateの2subrunを別途確認する。全旧Runtime worldや故障集合を今回再実行したとは数えない。source150ms/worker100ms/元親期限は変更しない。

このMac前奏の公開C校正で、実Runtimeと同じ`restart_yield`有効時は旧current-DATA開始がlate-enteredより先になり、元unit反映前にDATAを先取りする追加原因を確認した。既7件のyield falseでのclosureは保持するが、この実modeを閉じたとは扱わない。true-modeの重点2件は元unit未反映のassertion Red→7行の限定順序修正でGreen、最終新7＋直接旧13の20件もGreen。増分独立レビューもP0/P1なし。中間sealを保存し、修正後Cを新しいG1試験コピーから再seal/applyした。37中4変更/33保持の実配置も一致する。

変更部の単体/関連回帰と必要な実IPA/実compiler/全source・seal照合を行う。RuntimeやSpoolが不変なら新規全故障/大規模Macworldは実行せず、過去結果を過去として区別する。次の端末試験で商品到達→正常判定→実RS→次周回を評価し、毎拍/人超え速度や実機精度を補助検証だけで合格にしない。

専用Runtime結合のsource freezeは公開RGBAの前奏→同じ公開C状態→通常Runtime latest/cycle/画像lease→通常Ring→producer/commit両return・drainへ結合した。Scene/分類結果の注入は使わず、元Runtime本体は不変。normal/candidateの短い2subrunの最終source独立レビューもP0/P1なし。Linuxの公開C前奏校正をMac実行や実機成功とは扱わず、実Macのcompile/callback結果はCI原本で別途確認する。

CI265は旧known-floor選択がGit外のTEST043全画像を要求して停止した。元ログ/ZIP・digestを保持し、旧assert/試験sourceは変更しない。CI普通床1件を既公開`test_floor_quantization_integer_band_boundaries`へ選択変更し、22RGB境界＋flat/HUD/gold優先を欠けたprivate根でGreen確認。旧known-floorは同じ製品sourceのローカル130件でPASS、CIで新規成功と数えない。native37/4変更・seal・他129件は保持し、新CODEでCIを実行する。

## 実ビルドと配布前照合

製品CODE `617fc2483d4fbaae6f79764b5c06edca7a2fdf9e`、CI266/run45534392534。標準ubuntuのhost130（native103/cap6/package8/selector13）と実CPython3.9.25の53、標準macos-26の`entered_current_queue`1case/normal・candidateの2subrun、IPA build266が成功。普通床のCI選択1件以外に、CODE02dから製品sourceは変えていない。

Mac原証跡ではnormalの3workerがsource34→35→36を通常UNKNOWNとして採用し、candidateの2workerはsource35の対象候補をqueued36より先に保持。late-unit一回、元P/hold・source150ms/worker100ms、immutable RGBA/sourceと両return後のdrain/leaseを確認。全5commitは元期限内。公開RGBA/通常Perception・Ringと実Runtimeを使うcomponent試験で、実hardware ACK/撮影backend/未来MOVE・RS/実ゲーム/iPhone速度は未確認。

原3artifactのGH digest/size/CRC/安全で一意なpath、CODE全1181blobのflat ZIPを照合。読取6項目（元CI、source/package、host/Py39、current Runtime、実iOS compiler、全9MachO）も合格。37nativeの正確な4変更/33保持、R12全40/G1/canonical15、API/native_v15/ABI/profile3、実8C/5Swiftとsource/object/argv/RSPを保持。IPA SHA256は`2fa20bf29c5219d76796c92d6f9810b203718fb0cf1f35e1b7c2f698968a80c0`。

最初の読取attemptはworkflowのteeログ1本を一覧へ登録しておらずruntime段階で停止。原source/入力/失敗ledgerを保持し、必須26本と同CODEのtee/pipefail・checkerのexact78B PASSへ結合する限定修正を独立レビュー。原8入力/製品/CI/IPAを変えず、新しいattemptで6項目を一回確認した。分類/コンパイル/過去Runtime・Spool故障集合を読取時に再実行していない。

固定配布は[TEST119/build266](https://github.com/shuhei0720/necrogold-automation/releases/tag/test119-build266)。公開sourceはこの製品CODEから文書だけを変更し、公式ZIPの全Git bytesと同nativeを別途照合する。新版iPhoneの改善確認はこれからであり、元実機の再発数を検証件数で置き換えない。
