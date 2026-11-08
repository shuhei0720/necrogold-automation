# TEST055: 未送信予約を最新判断から作り直す8項目プラン

状態: 計画レビュー完了（設計/網羅第1周・安全第2周、残P0/P1/P2なし）。2026-11-09（日本時間）。挙動不変の [コンテキスト整理](context-refactor.md) はcommit `2866be66c8396ccc87b056ae7bd6f3d9bcd13862` で完了し、公開ZIP全429files/CRC/bytesを照合した。本書はその後の別の挙動変更である。

## 1. 概要・目的

確認済み歩行中、未送信の予約を作った後に分類情報が増え、最新plannerが別の操作を必要とした場合、旧予約を取り消して最新Sceneから同じ拍へ再計画する。元の入力窓・全期限・入力数/再予約予算と安全条件を保持する。過去のUP予約をそのまま許可する変更ではない。

併せて開発用の実記録評価器を追加し、実機の失敗を模擬結合の成功から独立に表示する。現在の資料だけで可能な実Cの部分評価と、完全Controller/実ゲーム再生ができない範囲を明示する。Macの本物ゲームは正規本体/実行環境/GUI adapter未導入であり、この工程の合格とはしない。

## 2. 背景・受領根拠

TEST054の1,978,173bytes/SHA `15ae61c465bdabb99a34dabb2979abd43debfe586c323ecbf5337c7d48778a15` を受領。1方向/1MOVED後、command4/source69の次UPはbegin0でSCREEN17/validation8停止。69→70は原寸0px、C/Pillow strict BLOCKED、全protected不変。DIRTがGOLD/DOORに分類され、Decisionは `(UP,8,-4,0,FLOOR)` から `(LEFT,6,-4,0,DIRT)` へ変わる。observe終了時でも元deadlineまで94.834709ms残る。

11PNGは全参照9枚を含み、C/Pillow/O0/strictO2が一致する。暗い領域の明るさ変化は確認できるが、その描画原因は未確定。今回の分類更新を知った後にも、旧UP予約を入力権限として維持する根拠はない。

既存continuous再予約はsafe-floorの同じ操作だけを扱う。`continuous_ticket.direction`をreserveで再コピーするため、単にそのvalidatorを緩めると新方向/x/yを旧予約へ戻す危険もある。安全な旧SAME経路と、最新判断へ切り替える新FRESH経路を分離する。

## 3. 詳細設計

### 3.1 共通の権限・凍結境界

対象はlead確認済み/moves>0/WALK、reserved state1かつbegin未実行のMOVEだけ。初歩・retune・別pending・begin/ACK待ち・UNKNOWN・finish/terminalは対象外。stable/current completed-prefix/inflight0の最新Sceneを、既存owner/generation/cancelのcommit gateで受理する。

SAME/FRESHでchain2・run8を共有し、元target/notBefore/deadline/ordinal/period/motion horizonを変えない。元source/phaseの3秒、walk45秒/session180秒、現在modelの鮮度/有効性と同じ物理拍のcorrected、input16等の既存上限をobserve/tick/reserve/beginで維持する。新sourceやrefitで元horizonを回復しない。次拍探索はしない。

同じ位置/visits/entrance/prefixで、beforeの通常`ng2_choose`の5field全部がcached command_choiceに一致する証明と、latestの完全Decisionを、1回のvalidationの結果として保存する。before証明を2回目のchoose成功で救済しない。before→latestの既存motionが厳密BLOCKED(dx=dy=0)であることも必須。既知MOVED/TWEEN/UNKNOWN/開通結果から再計画しない。

### 3.2 SAMEとFRESH

SAMEの既存safe_floor・全gold/全protected・source全5field/最新same-action・strict BLOCKEDを維持する。reason8のremote target座標差だけの許可を変えず、新FRESHの追加拒否条件をSAMEへ持ち込まない。

FRESHは両SceneがFLOOR/GOODS_UNKNOWN/GOLD_CANDIDATE、origin FLOOR、全protected完全一致で、少なくとも1セルに下表の変更がある場合だけ。全230セルを検査し、座標・件数・TEST番号で特例化しない。

| before | 許すafter |
| --- | --- |
| UNKNOWN | 同値、FLOOR、DIRT、STONE、GOLD、DOOR |
| FLOOR | 同値、DIRT、STONE、GOLD、DOOR |
| DIRT | 同値、STONE、GOLD、DOOR |
| GOLD / STONE / DOOR / ITEM | 同値だけ |

ITEMを含む変更、既知blockerの消失、既知床/土からUNKNOWNへの逆戻り、protected変更を拒否する。新たなDOORはlatestのgold bracketを必須とする。これは分類知識を増やす/より制限する関係であり、実世界の地形変更原因の推定ではない。

FRESHで入力権限になるのは最新Sceneの通常plannerが新しく選ぶ有効なdirection1..4のMOVE。FLOORだけでなく、通常plannerが既存の経路/保護/入口条件を満たして許可するDIRT/DOORも扱う。独自の掘削/扉ルールを追加せず、最新plannerが移動不能なら許可しない。旧GOLD/STONE/DOORを新FLOOR/DIRTへ誤って戻した入力は上表で拒否する。

### 3.3 pending・再予約・移動確認

private pendingはNONE/SAME/FRESH、追加データはFRESHの完全pending Decision。旧予約をnot_sent/SCREENでoutcome3・begin0にして、別ID・最新sourceの予約を作る。入力数・位置/visits・最終ACK/ordinalは取消では進めない。

tickは最新Sceneから再chooseし、FRESHではpendingの5field全一致を要求する。reason8でもtarget差を省略しない。予約前に別FRESHを重ねない。SAMEの既存検査はそのまま。新commandのdirectionとx/yを同じlatest choiceから作り、元continuous_ticketのdirectionへ戻さない。FRESH→SAMEの2回目も現在の新directionを維持する。新しい有効horizonが元の凍結値より短い場合は既存同様拒否し、延長して成立させない。

FRESH以後のその拍ではoptional original referenceを永久失格にし、再作成・SAMEでの復活を禁止する。存在する旧metadataは失格と明示したまま残せるが、fallback_attempted=false。primaryは最新authority Sceneを使う。次ordinalの通常予約は従来へ戻る。ACK後の取得start>=max(ACK,target+80ms)、3attempt/元deadline、商品優先/未知無再送、開通と進入の分離を変更しない。

### 3.4 Runtime・診断・client

RuntimeのcontrolQueue/owner/generation/AX pipeline lease/drain方式は変更しない。旧callbackは旧IDで失効し、新commandは別の前面sampleを準備する。旧callbackの実return前にもlease/coreを破棄せず、最終callbackへAX IPCを戻さない。旧callbackは新commandのcomplete/取消/故障記録に副作用を持たない。

既存SceneDetailのvalidationへ `12=FRESH_ALLOWED` を追加し、2=SAMEと区別する。replan_allowed/counter両方を今回込みで正しく保存。既存ABI/key/件数上限とfirst/latest/cell省略方針は不変。旧/最新sourceは既存event/scene_changes経由でpin/exportされることを実producerで確認する。新queryは増やさない。

client v13/capability `necrogold_native_v12`、`test_055.sh`/`runtime/test-055`。API1.98.14-ngg2と旧cap広告を維持。validationは0..12のみ、13/bool/float/不整合を拒否。v12 literalのstarted回復を残し、v12/v13双方でmotion_references必須、旧v11以下の条件も維持する。全export/通信/回復上限は不変。ここで旧v12互換とは、新v13 clientが旧v12 literal journalを読む回復を指す。旧v12 client実行ファイルによる新規起動は保証せず、TEST055は新v13 sourceとtest_055.shを必須にする。旧cap広告を旧clientのfresh動作保証とは扱わない。

### 3.5 実記録の評価器

developer専用CLIを `tools/evaluate_device_recording.py` に置き、iSH起動経路へimportしない。raw ZIPはGit外。path/重複/symlink/件数/解凍量/JSON/PNG上限・CRC/SHAを検査し、既存strict journal/report/画像検査を再利用する。ZIP内コード/設定を実行しない。Cを使う場合は信頼したrepoのproduction sourceだけをcompileする。

出力は①資料整合性 ②記録された実機目標 ③原画像のC部分評価 ④欠落/未収録の範囲を分ける。評価対象は全要件ではなく `goods_visible_and_paused` という記録上の到達milestoneに限定する。terminal/drained・input未知なし、nativeの商品flag/ポーズ成立と、対応する保存PNGを実Cで再確認できればpass。記録された終端が商品未到達ならfail、資料不足/矛盾や未終了ならunknown。不可視商品の不存在や指輪判定はこのmilestoneに含めない。resolved/drainedを商品到達成功としない。passはexit0、既知failはexit1、不正資料/評価不能はexit2とする。

元PNG/HUD・capture/decode/analysis/observe/ACK時刻・prefixを変更しない。完全に対応できるscene/motion/plannerだけを評価し、visits/entrance等の再構成が不足ならその項目を未評価にする。今回65 capture行にPNG11枚/不足54枚、8sample model等はないのでfull_controller_replay=false。60→68 UNKNOWN、60→69 MOVED DOWN1、69→70 BLOCKED/Decision変更を部分的に検証する。LEFTへ分岐した後の実画面は未収録とし、77/78/79のポーズ画像を代用しない。公開CIの手続き生成ZIPは明示的なfixtureとして区別する。

## 4. 影響範囲

C Controller/header・clientとlauncher・cap/封印/compile/package/RPC検査・native/trace試験・Mac fixture/helper・CI選択が対象。Perception/Navigation/Beat/Core/Raster/Ticket/CaptureBridge/Templates/G1/R12とアルゴリズム/入力座標は不変。Runtime本体は診断projectionの必要が実証された場合だけ対象へ追加し、queue/control変更を混ぜない。

TEST054の11画像を `tests/test055-fixtures.json` にhash/出典だけ追加し、既存141と合わせ全152必須pathの不足/hash不一致を失敗にする。O0-only参照対strictO2の全Scene/全73scores/Motion/Decision/Entranceを維持。private画像のCI除外はmethod名/件数を明示し、local全件と別記する。

## 5. 追加・更新する検証

- 主Red: 実画像69/70と実位置/visits/入口を使う実C Controllerで、旧UP不送信・別ID/最新source70・LEFT/DIRTの再予約を期待し旧codeのassertion failure/0errorsを先に観測する。モデル/lead-inを合成するunit部分は明示し、完全な原トレース再生とは呼ばない。
- 全方向・FLOOR/DIRT/DOOR・単調分類の許可/拒否、cached-source各5field故障、pending latest各5field故障、FRESH→SAME方向/x/y、同一拍/全凍結境界・chain2/run8/input16、別ordinal/初歩/retune拒否、started/UNKNOWN/owner/世代/取消/商品、早いafter/3attempt/開通≠進入/失格referenceを検査。
- 旧SAME成功/reason8例外・全既存安全試験を保持。旧「単調な更新でも必ずstop」のsubcaseは、旧予約不送信のassertを残し、新ID/latest Decision/validation12へ期待を根拠付きで更新する。source不整合・protected/非単調/motion/期限の失敗は成功化しない。case削除/skipでGreenにしない。
- Macのproduction C/PNG/Rasterを通すFRESH公開fixture、旧/新callbackの両終了順、実return/drain/export、元方向の残留禁止。旧55 named faultsを維持し、新しい実ControllerのFRESH無効/旧direction再利用の2故障を追加して計57。旧faultを新fixtureが先に落として隠さないようscopeを分離する。新2reportを実producer stdoutと同一bytesで保存し、実暗号HTTP→新client検査/両journalへ接続する。
- 新client revision/cap・validation12と旧v12回復を実暗号HTTPでRed→Green。評価器は読込可能stubのnot_evaluatedから有効な終端未到達資料へfail/exit1を期待するassertion Redで始める。評価器RedをControllerの実機不具合Redと混同しない。破損/成功/未判定/欠落/未収録/無変換のケースも確認する。
- 実TEST054に対する評価器の期待はintegrity pass、goal fail、fullController不可、未収録分岐を明示。既知不合格がexit1になることを検査証拠として保存する。

## 6. 実装順と独立レビュー

①fresh設計/網羅/安全の計画レビュー（最大3周） → ②実C主Red/client・評価器Red → ③C private policyと最新予約の最小Green → ④client/cap/評価器と境界回帰 → ⑤Mac57/Raster3/C同値/RPC/実compiler/IPA → ⑥fresh3観点の実装レビュー（最大3周、同じ周の実配布物補足まで） → ⑦完全source/新IPAと具体的TEST055実機依頼。

担当をController/header/tests、client/回復、記録評価器、Macfixture/helper、root統合/来歴/資料に分ける。要件・本計画・レビュー1文書を正本とし、進捗をAGENTSへ積み増さない。レビューは `docs/reviews/test055.md` に記録する。

## 7. コミット前・配布前の証拠

local全152画像を含むnative/評価器、client、package/compile、旧回帰を対象変更に応じて実施する。実Mac57、Raster3、両C同値/field故障、LoopCtrlKit/暗号RPC、実PBX/raw compiler/response profilev2、22seal/保護資産、IPA/Mach-O testhook非混入、全source ZIPのCRC/全byteをcodeへ結ぶ。実生成reportと実暗号clientの診断一致を同一最終artifactへ結ぶ。

docsはcompact状態を維持し、status/契約の該当節/試験入口/本計画/レビュー/実機台帳へ結果を保存する。反実仮想のLEFT後や実機到達・毎拍・速度はhostで合格にしない。新IPAの理由を説明し、SideStore更新→LoopCtrl完全終了/起動→Start Server、新しい通常1-1ポーズから `sh test_055.sh`、終了後 `runtime/test-055` 全ZIPと歩行/商品/ポーズを必ず依頼する。

## 8. スコープ外

gold/stone/door消失の許可、既知blockerから床/土への緩和、motion/認識閾値や時間窓/3attempt/予算の拡大、map融合、未来画像の流用、未知input再送、初歩slot/retune/入力座標変更、購入/指輪認識・通知/全周回の合格宣言。正規ゲーム本体・Mac実行環境・GUI adapterの提供なしに実ゲーム試験を実施済みとしない。
