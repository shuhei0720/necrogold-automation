# TEST086受領とTEST087

2026-11-12（日本時間）。[計画](../plans/test087-target-pause.md)・[独立レビュー](test087-independent.md)。基準 `6a937163ac87dde049887eaf56a65f9dda757911`、TEST086/build146。raw/ZIP/ログ/Scene/cropはGit外 `received086` / `test087-*`。

## 受領と実機結果

開始時刻順は添付表示順と異なる。

| 実順 | run先頭 | 終了 | inputs/moves/restarts | 保存原画の確認 |
| --- | --- | --- | --- | --- |
| 1 | 76e862cd | GOODS1 | 9/7/0 | 全3商品可視・別ring「ゆうきのゆびわ」 |
| 2 | f7fae670 | GOODS1 | 9/7/5 | 全3商品可視、host回収deadline/cancelを伴う |
| 3 | 1b3efc43 | GOODS1 | 7/5/6 | 全3商品可視・中央「のろいのゆびわ」250 |
| 4 | c9bca989 | BEAT8 | 4/4/10 | 通路接近後、未送信票の取消と再同期後に停止 |

4ZIP/80原PNG・19,260,301画像Bを現API16閉schema/client_load/ZIP/PNG chunk CRC/SHA/PIL/896×414/全exportoffset・prefix・cursor/test069実publication gateへ全照合。全paused/terminal/drained/回収完了・見送り判断source21/21保持。省略799/省略参照96で全取得保存ではない。実4原16だけnative bounded capture行がなく、export原PNG/metadata正常・他79行は一致。欠落や私的状態を再構成しない。

実2はhost result_json rpc_deadline3（status/cancel/status）、host_deadline/cancel2試行/native_cancel_requestedを伴うがnative GOODS/PAUSEで最終回収完了。host/native時計を直接比較しない。実1途中dispatch too_late1は後続GOODS成功と分ける。追加回収/086再実行不要。監査receipt7231B/SHA `06cb7b20d1192a5aa990e2689697de0d4af03b22326dfc84a9ac4b98d9fe3cb5`。

root/監査/独立担当が原225/270/309の商品3点を視認、native goods3/4と一致した。実3中央は茶灰の指輪と「のろいのゆびわ」、左トーチ8/右プレートアーマー125。前版のgeneric GOODS成功はこの対象を自動識別したという意味ではない。共通SceneはTEST086 final lib `b53f3dffff7dfa9d35e357692c97a1168bd0875efe046ff0c7be3904642bfdad` と現source8の全一致を確認して再利用、80原画を各1回export・再compile0。

## 対象指輪の識別

新ユーザー指示で今回実装する。前版activeはScene.goods=UNKNOWN/PARTIAL/VISIBLEだけで、3価格/明るい3商品枠から可視性を判定し、Controllerがgeneric GOODSでポーズする。対象名/種類の判定・対象発見通知は実装していなかった。

R12/ring.png（public既存・全legacy bytesは不変）と実3原309の対象文字をderived featureの出典にする。原寸3scaleの校正でtarget icon .953305/同run308 .956985、別ring .313027/他negative最大.476866。原309の文字bbox(368,54,452,65)・84×11/239ink maskはIoU1.0、308 .643110/別ring近傍最大.393229。新原寸icon≥.80をcandidate、同一認証PNG・同一商品slotでicon≥.88かつword IoU≥.82/coverage≥.90の全ANDだけtargetに凍結する。価格250・run/frame番号・商品固定位置は条件にしない。旧597 score .76/.64とは別の閾値である。

原308はprefix20/inflightなのでpixel校正でだけcandidate例に使い、本番の認証入力にはしない。最終ACK PAUSE22のauthority309=prefix21 stable/noninflightを第一に、必要な場合だけ同prefix/非inflight/取得非交差/authority以下の保持PNG1枚を追加する。最大2枚、原寸/有限slot/scale/search/cancel検査で処理量を制限する。結果target/candidate/unknownを同run immutable sidecarとして初archive前に保存。closed active/report・既native入力・旧entryのhook既定Noneを維持する。

同じ独立担当がB計画へGOし、word/iconを別slotで混ぜないこと、破損/回収不足を対象なしにしないことを追記した。対象らしさ/不明を保持し、対象なし自動循環・OSバックグラウンド通知は今回追加しない。原3runは校正であり未知評価とは数えない。作者意味Red/単体/出版結合と最終結果は後続へ記録する。

## 実4の停止を分離する

最後のcmd25 DOWNは346→354で公開MOVED。cmd26 LEFTはsource354/ordinal5でbegin0・outcome3/SCREEN17、入力未送信。event.end178007235869958はcapture355.endと完全一致し、Cobserve355中に失効した範囲へ絞れる。355はstable prefix25/no inflight、commit時にも元NBまで29.227ms・Dまで39.227msありsource/phaseもFRESH内。hostcancel/dispatch failureはない。

355PNG/Scene・詳細change記録は保存されず、recovery seq2/3もdrop2。最初に落ちたroute/pixel/validationの具体guardは未確定であり、後画像371の2床成長を355の中身に代入しない。

354/371は同じ画面位置で、371では床の可視範囲と明るさ/文字が変わる。公開chooserは固定world口(-3,+2)へLEFT/reason10/観測FLOOR/path2を両方で保持。354→371の旧stationary085はlocal近傍UNKNOWN→FLOOR1点・axis74.092%<75・9競合の元15pp不足でUNKNOWN。raw73zero/gap.131481・左右phaseの有限最良/競合gap・closure blurzero .323840<.45・world95%以上は成立しても、失格した旧axisを成功へ読み替えない。

cmd26元period522020193ns、355commit+2period=178008316049802、cleanupPAUSEreserve178008319267916は3.218ms後で旧2拍静止待ち終了と整合する。ただし私的なfinish分岐を証明したとはしない。PAUSE予約時も元Pは1.785秒残る。直前の再同期準備50ms不足3.575msと最初のSCREEN取消を分離する。必要な限定診断compile1回だけ、製品/旧単体は変更・再実行0。追加STONE planeも原画勾配72.945%/候補分離不足、現signature支持87/帯42・45で不足し、追加proofは製品化しない。歩行停止未解決を明記し、Aは非zero実差分があるUNKNOWN静止待ちの入口診断を既journalへ保存する変更に限定する。mask0契約/Runtime/入力挙動は維持し、次の不具合解析の証跡を改善する。

## 作者単体・最終sourceと評価

A新3は公開UNKNOWN/selfBLOCKED・元票/信用/W/Pを先assertし、期待入口trace1対旧0の有効Red。初回2Green/1shop重複trace失敗を元2callerの責務へ戻すpassage_active限定で直し、失敗methodだけGreen。編集した旧0822methodはentry＋後続rejectの順序/metadataを強め、最終Controllerでsource8を照合して2Green。未変更旧単体local再実行0、C seam/新関数0。Controllerは既prototype移動＋3locals＋通路の実mask算出/元record_change callだけで、既helper本文/他全bytesとevent観測欄・旧0mask拒否を保持する。

B新6は原309のSHA/header/feature前提後のtarget対stubunknown Red→初回6Green。続くsidecar型/別slotROI/必要source数4境界、PNG2境界、強icon2枠の第二slot対象名1境界をそれぞれRed→編集methodだけGreen。独立予備レビューで明示prefixと直前ACK/source_start結合不足、rootでpost-link後part残留の回復不足を発見。source8境界Red＋part残留Red→影響prepare/identity2method Greenで修正。native/C/compile0、私的PNGやenvにCI依存0。

子の出版/evaluator新6は正しいsidecar受理を期待する有効Redから最小Green。初回4Green/2fixture errorは現certificateのui_frozen=False必須fieldを欠いたseedの誤りで、製品ガードを緩めず補い影響3methodだけGreen。旧local意味再実行/native compile0。初archive前hook、旧None、既archive後にprepare0、同run回復start0/同ZIP・sidecar bytes、strict extra拒否と旧ZIPを確認した。

finalController `9492a632f02c4d053f4f7aca1e923ccbb83c50318edad34e915c61331b353c4d`、他7C/Hは元086同一。root C4を一度compileしlib `f3ee2dedea3b16044d707919de83ba6ff048dfde5294b55f2a3b04cc74bd74cb` へ固定。fresh pinned Git/G1→seal/applyは22=9既存+13追加中Controller1変更/21不変、manifest `a4cec8352ed908b9e45da48a7daea7677c7d005746cea84fa9cebc25d7b4deaa`。Runtime/Beat/Nav/Perceptionとcore client3(native_walk/validation/protocol)は同bytes、test069は対象判定hookのため変更したので4不変とはしない。原画/数学pixel回帰はNav/Perception同bytesの根拠で旧417照合と今回80Scene exportを再利用し、新全画像走査は0。

最終target module `b2b52ffe41826ea7031f24ca26ab6a77a1283efc7d18a134470f7c8dcea37575`、feature `202322326d86f600b300713ca8572b592f3beb59ceff6e6f6e58ef9cb3b728b4`。凍結pixel classifierで原309target、225/270unknownとなった。name/3slot/座標を自動検出し、309の中央icon .953305062＋word IoU/coverage1.0を同slotで結合。所要2.03〜3.83秒程度は開発機の原画処理で、iSH性能や未知陽性精度とはしない。source/part修正後もdecoder/row/icon/word等9関数の本文hash完全不変を確認し、結果を再走査せず再結合した。実4GOODS0は対象authorityを選ばずunknownの対象で、原308inflightは本番sourceにしない。

別run8画像を内容閲覧前に選び独立担当が人label、4は明示陰性・4は文字/箱の中身等が不明。原画SHA/ACK PAUSE source/prefix/報告SHAを先固定し、閾値調整に使わず凍結後各1回だけ評価。結果は8ともunknown、明示陰性4のtarget誤検出0。不明4を陰性成功へ数えず、陽性holdout0・未知陽性/実機精度は未受入。label SHA `0d8b070dd14e3c98a43229e937da86fe83a5a7ebeb45b5acd97086a67068af19`、最終数学source再結合はGit外final-evaluation-binding.json。

限定selector/同code CI/実compiler・IPA/5実物verifierと固定公開GETは後続の記録へ結合する。Aの歩行停止未解決、signature-onlymask0の保存不足、OS背景通知/対象なし循環の未実装・未受入を隠さない。

## 限定CIの選択

33methods/10scopeを選択。native9=新入口3＋正当更新0822＋未変更旧4（082zero-mask/076期限等2/ABI1）、client21=target6＋出版6＋関連旧9（results1/出版4/evaluator4）、self3。旧Capture3は新decoderを通らず未変更なので省略。CORE12を選択前にsealed upstreamへ結合し、21override prefixは空値も拒否、main自己試験tupleの087をASTで固定。evaluatorの既NativeCoreはrepo側8sourceをsealed8と前後照合するので、upstreamへ差し替えたとは称しない。旧086entry互換も同bytesへ結合する。

self3作者1回PASS。新C fixture宣言0、Python4module/classの8markerを旧260 exactprefixへ追加し計268・重複0。target/feature/classifier/schema/sidecar・evaluator/entryは同code metadataへ結合する。同じ独立担当が全静的差分/author証跡/selector/source/sealを確認しP0/P1/P2なしでGO。5実物verifierはcode/count/実物到着後の明示GOまで全guardFalse、実行0を維持。

## 同code実物と公開

code `8553efb7a487b71e9be333a054465f76f4017111`、run43184318092/build148。host33methods/10scope全Green（native9=新3/編集旧2/未変更旧4、target/出版新12/関連旧client9、self3）、fail/error/skip/expectedfail0。Mac070旧Red1/現6Green・081保存6Green、同bytesRuntimeの固定保存Red133は別証拠再利用。

5実物verifier各1回PASS、失敗/再実行/追加意味0。全664tracked blob/CRC/path、22seal Controller1変更/21不変、R12原40/G1・core client3/API16/cap15/client16/旧v1を照合。実4C（Nav/Perception strictO2、Beat/Controller O0）・Swift5 Onone/RSP6・HOST不在、全9MachOで旧260 exactprefixを保つ268marker不在。新C fixture宣言0。target module/feature/classifier/schema/sidecar/evaluator/entryの同code identityを結合。

receipt 13140B/SHA `c398bbe5e3b8de26ae1692bc83548216be75d49727775794e97977c5542bfddd`。5 result/verifier SHA・3artifact API digest/bytes/head/run・root独立in-memory IPAを同code/IPA/sealへ照合。同じ独立担当が実物読取確認しP0/P1なしGO、追加意味再試験/独立doc編集0。IPA0.3.4/build148/min16、17629270B/SHA `f4c9e9f1c02e76fb0921f31f5613f9a7986d825d2528e848aabbd82b00b33a76`。

[固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test087-build148)・[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test087-build148/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test087-build148/source.zip)。closingはstatus/本レビュー/device台帳3件のみ。全664closing blobを照合したsourceと検証済みIPAを固定assetへ保存、公開後3assetを匿名全GET/digest/SHA/CRC照合して返す。新1-1ポーズから一連5回/対象表示/全保存完了後ZIP全回分を依頼。歩行停止/signature-onlymask0/未知陽性精度/OS背景通知/対象なし循環の未解決を維持する。
