# TEST076: TEST075受領と停止改善

2026-11-11（日本時間）。baseline `6408286ec380a29541e385836e1c209d445f1fe1`、[計画](../plans/test076-stationary-recovery.md)。raw/Scene/proofはGit外received075/test076-*、元資料を公開しない。

## 受領と実画像

全4ZIP/69選択PNG（20/17/17/15）を全hash/ZIP・PNG chunk CRC/896×414/manifest全offset・hash・cursor/prefix/active-reportと実validator/publicationで照合。全PAUSE/resolved/terminal/drained、2はretained20/export17/4,179,563B（4MiB内）。未保持・省略を未来画像で補わず、回収済み075の追加回収や再実行は不要。

| 実順/run | ZIP bytes / SHA256 | restart | MOVED/方向入力 | 停止 |
| --- | --- | --- | --- | --- |
| 1/1828c816 | 3,553,598 / `56f4b04d16c5680a71dadf6768bd72960b3788dbbf256ca7da38f71a0b694a2d` | 8 | 2/2 | screen |
| 2/05379963 | 4,403,157 / `9811395fd637b195ce81164001bd9652cd355f34053dc304bc9bbe7e1bb7a4a6` | 2 | 5/6 | goods |
| 3/6b407804 | 3,675,893 / `f29f66a41535aab238da9dd66e3339026035a4a4b11e56f080ed0e209737d429` | 0 | 3/3 | capture |
| 4/c43fa118 | 2,719,580 / `8c00c5a0734e3b89821b6f7586daffc3d173398b3b054659e7c2b045bf4aacd6` | 1 | 2/2 | screen |

2回目はrootが原capture198を閲覧し、3商品と価格50/50/100が画面内にあることを確認。対象アイテムの有無までは認定しない。全商品到達は1/4。全capture failure=null/timeout=false、dispatch_failureは3回目のみ初歩cmd3 too_lateを保持し他3回null。iSH status46回はエラー/取消0、最大total1.324秒。075 parser変更の恒久的性能合格ではないが、今回2秒cancelは再発なし。

intake担当の中間送信文にdispatch全nullという誤記があった。元reportとindex/summaryには3回目の正しいobjectがあり、capture欄だけの確認をdispatchにも一般化した報告誤り。rootの原object照合で訂正しGit外audit-narrative-correction.jsonへ残した。CRC/schema/publicationの成功範囲には影響しない。

## 正確な停止箇所

1は金singleton(-4,4)発見済み、実2LEFTの後、未送信DOWN/source275→277。通常choiceは同フル5 DOWN/reason8/target(-1,2)/FLOOR。全金/保護/局所不変、遠方(5,2)/(3,4)DIRT→STONEと(5,4)FLOOR→UNKNOWNのみ。quiet/continuousのstrict静止がUNKNOWNとなりvalidation11/SCREEN。C17.856083ms、終了はNB+3.912444ms/D−6.087556msで、期限超過を直接原因にしない。

4は固定通路candidate bit5・world mouth(-3,-2)、pose(-2,0)。未送信UP/source97→99、全230tile/金0/保護0・両CLEARとフル5 UP/reason10/target(-1,-2)/FLOOR不変。passageはmask0でも静止確認を要求し、quietとfallbackのUNKNOWNでSCREEN。C9.033583ms、終了NB−11.244689ms/D−21.244689ms。capture98はmetadataのみで画像非保持、補完しない。

3はpose(-2,-1)で4歩目UP/source161が未送信、元D10ms窓。初期原画の候補mask32からbit5/口(-3,-2)を固定パラメータとした純幾何ではUP/reason10/target(-1,-1)/FLOOR。private live候補自体の復元とは区別する。source161のcapture16.567/decode29.086/analysis6.357/observe4.375msを経てC終了D−1.324819ms、begin0のcomplete0はD+11.064681ms。actual gateの現cmd7詳細は非保持でprepare/main-hopのどのチェックが棄却したかexact断定しない。元GOLD_CANDIDATE専用回復がCLEAR探索を除外するためCAPTUREで終了。別の初歩cmd3はgate D+0.597924msのtoo_lateで初歩回復済み。直前3入力の開始間隔532.821/523.251msは予定520.175ms付近、実game受理時刻とは区別する。

## 不採用のNav案

元sourceのraw静止最良/gapは1=.501462/.290947、4=.483634/.277461。075 zeroは絶対score条件と強95%の不足により対象外、4はさらに金なし。固定標準Sobel1案（full9既知依存/原opening mask/camera52/contrast48）も95%・二帯支持は満たしたが、全73への15pp差が1で2候補、4で1候補不足。値・候補を削らず不採用、別kernel探索はしない。Nav/全旧proof/数値を変えない。Controllerで確実未送信票の権限を捨て、固定anchorへの後続strict証明を必要とする案へ進む。

## 設計・単体と独立確認

Nav/Runtime/Perception/JSON/全publicヘッダ/ABIは不変。Controllerだけに限定追加する。shopは既存mask変更拒否経路、passageは既存quietが要求されるmask0も対象と明記し、通常mask0 shopへ余分なmotion評価や拒否を加えない。元reference失格だけでprimary確認を追加拒否しない075契約も維持する。

新passage6methodは凍結075のcompile成功後14 assertion failures/error0、新stationary8methodは19 assertion failures/error0。合計14method/33 subtest failuresの意味的Redで、環境・compile失敗は数えない。製品b31d33d1e363055c6fbbe39fefaa5a500a6a12291c0e08fa0bc3115eca3544e0で新14method Green7.024秒、旧assert/期待値の削除・変更なし。元anchorへ直接strict BLOCKEDが取れるまで新入力なし、隣接画像だけの静止で元worldを更新しない。P/Wと元event/ID/epoch/入力creditを分離し、新future票にも元Pを継承する。後続画像は明示的な手続unit fixtureであり、実機の未保持未来画像ではない。

独立レビューは製品差分/拒否条件/旧mode不変/runnerの実sealed CORE・client bindingを静的確認。計画のshop mask条件の曖昧さは上記へ明確化、製品P0/P1なし。無変更の共通時計巻戻しguardは静的確認と分けて記録し、新mode全境界を単体で実行したと一般化しない。P等号/超過・strict新gold成功の追加subtest等の結果、限定CI/新IPAは確定後に追記する。未保持の後続フレームを合成して実機到達と呼ばず、次の端末試験で全商品まで評価する。

## 最終ローカルfreeze

Controller `b31d33d1e363055c6fbbe39fefaa5a500a6a12291c0e08fa0bc3115eca3544e0`、stationary test `ec5c60da1cc157cde171f9130354f40cc3ab700a39c141361676cb617483e737`、passage test `b2ffba9f083d0c8f59a8cfc603908b7e4220d71742682437a975e8cd80c9f636`。8+6のmethod数は維持し、P等号/+1・READY/ISSUEDでW通過後のP維持・strict新gold成功handoffを既存2methodへ追加してGreen3.272秒、late observe4方向/旧safe・最新unsafeを別2methodへ追加してGreen2.663秒。gold handoff後にfuture_ticket/newID/schedule/visual≤Pまで強化した1methodもGreen1.787秒。追加observepositiveは凍結075 compile成功後の意味的Red1/error0を別確認。製品は全て同じb31dで、旧assertを削除せず必要な変更methodだけ再検査し、最初の14Greenと補足検証を区別する。

実PNG由来の275→277・97→99は新待機の純幾何/full5/safe-stepに適合し、元motion UNKNOWN・trigger自己BLOCKED・anchor strictProof0のままであることを確認。161は初期mask32の固定候補bit5をパラメータとしてCLEAR/同材質/同フル5/strict自己BLOCKEDのlate幾何へ適合する。既知pose/visits以外のprivate clock/model/owner/prefix/live ticketはscaffoldとし、実Controller全状態の復元・未保持future proof・実機到達を主張しない。

独立担当が製品差分、補足test差分とGreen記録、固定anchor/PW/元gate・terrain・observation不変、shop mask限定を確認し残P0/P1/P2なし。無変更の時計巻戻し共通guardは静的確認と明記。新goldは旧anchorへのstrict0成立時だけ通常handoffし、UNKNOWNなら商品/候補を保持して停止。確実未送信lateはtick/begin/complete0に加え、observe先着も最新Sceneを使って検査し、古いsafe Sceneで最新unsafeを飛び越えない。

runner `b93a61746b052d6cb1a9e94a8b4a3b0dc3d93e98df45d8bef42459a8bc88eb71`。新14+関連13（gate2/terrain2/観測refresh2/passage3/旧gold unsent3/ABI1）+selector3=30を実methodへexact列挙。selector3はローカルGreen。CORE canonical/既存bareを実sealed upstreamへ結び、063/071/072/074/075/076 baseline env・BASELINE_NAVを空値でも拒否。5client HEAD blob/4実callable、無変更のnative_walk/test069/validation/protocolをbaseline同bytesに固定。075のNav/JSON試験は同bytesの過去結果として今回の実行数へ足さず、全Runtime/worldを積まない。

fresh G1→seal/applyで22source中Controller1のみ変更・他21不変を確認。API16cap14v15/全public header/ABI/G1/R12原40・全数値閾値を維持し、限定CI30と実compiler/IPA/全sourceの照合へ進む。新実機は未実施。

## 実CI・IPA照合（build122）

code `8bda0a7a4ffca107472117311c3ca0491182a5e4`、[run42958472307](https://github.com/shuhei0720/necrogold-automation/actions/runs/42958472307)、標準public Ubuntu/Mac device lane成功。新14/関連13/selector3=30件はfailure/error/skip0、実sealed CORE・5client blob/4実callableとpublic ABIを照合。4C/5Swift/6RSPをactual compiler/PBX/raw args/hashへ結び、Nav/Perception strictO2・他C O0/Swift Onone・hostmacro無混入を確認。未変更Runtimeは既存TEST070意味的Red1と現6callだけを検査、全Runtime故障/worldは選ばない。

22sealのController1変更/他21不変、全public header/ABI/API16cap14v15/G1/R12原40維持。全9MachOで旧133+076 namespace/module3=136 fixture marker不在。実5verifier各1回exit0で統合receipt SHA `94f9eb5f463b82f7e6c059007b57e4bf6a2530fb7eedca3dddd8f96c6503c7d0`、verifier5本/依存3本は前後hash不変。追加の製品試験やrepo編集は行っていない。rootもinner IPAの全bytes/SHA/CRC/paths/plistを独立照合。

IPA0.3.4/build122/minOS16.0/top.ebato.loopctrl、17,607,458B/SHA `4a4bec1ceaa0f33ad25ace737b6b24eeeb5c1ce048aa324a87e94d9c04572f18`。unsigned artifact13828776317は17,884,747B/`1e91c42343ad8f2567082a966a9558a0d999573e581ca237ac6686433bcacc97`、validation13828731580は1,247,032B/`7d390a69a4c03a7ed8b1d5a282de04286cf63b115cb5abf66ce2ff5c5a10ccf9`、host13827358684は9,247B/`b953cf372fa48a72f9cbbb03455f6fded665b1c950a6f058de2fcbb3720c10be`。API run/head/branch/digest・取得全bytes/CRC/安全path/重複なしを一致。code全sourceは565 tracked files/7,606,882B/`a6e71f1960e2c7e3b7bb1c932ee51a5949bb211246ba9ffcc311fb0bdeff74b6`で全bytes一致。

[固定Release](https://github.com/shuhei0720/necrogold-automation/releases/tag/test076-build122)へ検証済みIPAと最終全sourceを保存する。最終sourceはstatus/本記録/実機台帳の3文書だけを閉じ、全製品bytesはcodeと同一。公開後の匿名全GET/SHA/CRC/API digest一致を確認してから返却する。実機で固定anchorへのstrict再確認が戻るかと全商品到達/拍間隔は未受入、075の回収済みrunを再実行させず新しい通常1-1の一連試験をまず2回依頼する。
