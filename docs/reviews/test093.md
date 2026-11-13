# TEST092受領・TEST093検証

2026-11-13（日本時間）。[計画](../plans/test093-opened-entry.md)・[修正記録](../fix-records.md)。新実機改善は未確認。検証の最終結果は末尾に記す。

4ZIPは20,117,970B、原80PNG/19,071,938Bを全CRC/SHA/strict load/certificate/canonical sidecar/登録集合へ照合した。全paused/resolved/drained、画像回収不足なし。実時刻順を採用する。

| 実順/run | 結果 | 方向入力/歩数/restart | 個別判定 |
| --- | --- | --- | --- |
| 1/4062fe25 | screen、開扉後の未送信入店票を拒否 | 6/5/1 | no_authority、未実施 |
| 2/a6b6d0cd | screen、同配置の再試行も開扉後に拒否 | 6/5/0 | no_authority、未実施 |
| 3/e3a639a5 | goods、3商品可視 | 8/6/4 | authority313で実施済み、一致未確認 |
| 4/ebf576e5 | screen、開扉後の未送信入店票を拒否 | 7/6/1 | no_authority、未実施 |

商品確認1/4を新版の到達率合格とはしない。原246/130にはのろいの名前・絵とロングソードの2商品が見える。3つ目不可視で個別判定/通知は未呼出、matcherの偽陰性とは区別する。実3は原303から3商品可視、313で正式判定。実4原215はへいわのゆびわ/いばらのかんむりの2商品。新原画の指輪engine再分類・feature変更・buildは0。

全失敗で直前のDOOR_OPENEDは成功。現Cと同8coreの保存libraryを使い、critical7PNGを各1回解析し4pairのstrict BLOCKED0・同じ完全Decision5/実visits・次FLOORを確認、追加compile0。原211/244/245など未保持画像を生成して補わない。新対策はC予約更新の適用範囲であり、090薄鉄型補正/091開通証明を削除した回帰とはしない。詳細な原因・限定条件は計画に記す。

## TDD・配布前レビュー

基準732aの8coreを保存し、新6methodはcompile成功/errors0・assertion failures13のRed。原fixtureは5454be36の版で、予定した境界subcaseを追加した最終a41e28ccとは同一bytesではない。原py自体は保持されずidentity/hashとtracebackを保持、中心のrevalidate失敗assertは最終版にもverbatimで残る。新fixtureの最終Greenは配布コードのCIへ結合する。

A/B入店の段階Green後、期限切れのtick/begin/complete0で元停止を確認する別の意味Red3件を保存した。有限PARTIAL回復を追加して当該1methodがGreen、追加境界を含む6methodもController477e73d4/fixturea41e28ccでGreenだった。入力/位置/移動creditは手続き単体の範囲であり、未来の商品到達を証明しない。

独立レビューで、mask0の旧quiet成功を新FRESHより優先できないP1を検出。旧081のsource-mask-return試験を変更せず1method実行しfail1/errors0を確認した。quiet成功ならmask0でも新refreshを撤回する1行を修正し、最終Cはab3fe447。旧helper/assert/新fixtureは不変、同担当の静的再確認でP1解消/P0なし。最終18method/6scope（新6＋旧8＋selector4）は同codeのCIで実行する。旧38件・全Runtime/world/UIは対象外、Runtime092の9＋旧1は不変bytesと過去証跡へ結合する。

原7PNGを再分類せず保存Sceneを使い、477のwrapperを1回compileして4pairの限定校正を行った。対象helperの全bytesが最終ab3と同じことを別途確認。4062/a6/ebf後pairは新relation1/validation12、ebf前pairは既存generic FRESH12。実位置/visits/完全Decision5・strict0を確認したが、p.sceneは既知source、modelは正規化した部分文脈である。欠けた4062の244/245、a6の129、ebfの211/214は補完せず、全Controllerの実時刻再生とは呼ばない。

sealは1c6ce5bed0f871d136a3e65911fc0ef8b07261ef3d952553ed58466de94b33cc、22中Controller1変更/21不変。新2つのprivate uint64は親horizonと実退役時刻だけで、ABI/wire/enumは不変。この時点では最終試験/IPA実物照合は未実施だった。結果は末尾に記し、新実機改善は未確認のまま保持する。

## 最終CIと実物確認

code `7e6b9ba70711512145dfbc7a275287d56234aa97`、run43362104103/build159。標準Ubuntuの同sourceで、新6＋旧081の3/071の2/077の2/065の1＋selector4＝18methods/6scopeが全Green。最終a41fixtureとC ab3を結合し、P1の旧mask0 assertも変更せず合格した。Runtime/Nav/Perception/UI/engine/API16/cap15/ABIは不変。旧Runtime092の新9＋旧1を不変bytesと過去receiptへ結合し、今回の実行へ読み替えない。

IPA0.3.4/build159/min16は17,645,407B/SHA `e52219b40d2d075a87d3354dd8ecd2e7f38c170adf5edd1c9f0ba7096aa6f128`。実物5gate各1回PASS、追加compile/意味試験/分類0。22sealのC1変更21不変、実C4/Swift5/RSP6、全9Mach-O/旧388＋新10＝398禁止marker、R12全40と完全source750件のCRC/全bytesを同CODE/run/IPAへ結合した。独立担当はreceiptだけを読み、実物gateを再実行していない。

closingはstatus/本review/実機台帳/修正表の4文書だけ。IPA・製品・試験はbuild codeのまま固定Releaseへ保存し、匿名全GET/実tagを照合して返す。実機改善・到達率/毎拍/人超え/未知陽性精度は未確認のまま、通常1-1ポーズから一連4回・完了表示後の全run ZIPを依頼する。
