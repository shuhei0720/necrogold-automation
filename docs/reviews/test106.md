# TEST106: TEST105実機失敗の確認

2026-11-15（日本時間）。6 ZIPは3実行と重複対。73 PNG・81記録・160 rawファイルを、CRC/安全パス/manifest/hashchain/decoded RGBA/時刻・世代・安定prefixで全照合済み。生資料はGit外。

| 実行順 | 元run / source | 停止箇所 | 確認した原因 |
| --- | --- | --- | --- |
| 1 | 4370… / 235→236 | 商品判定前のSCREEN17、未送信LEFT撤回 | 商品UNKNOWN、同Decision・厳密零の開扉後に遠方の新GOLDが既関係の範囲外 |
| 2 | 8c7… / 253 | FULLの正常UNKNOWN・policy7 PRICEを採用、RESTART intentなし | 閉容器の低い価格を全3品共通9px条件が拒否。既id11も背景由来のIoUで失格 |
| 3 | ff281… / 310/312→313 | PARTIAL正常UNKNOWN後、未送信UPのcycle_credit ROUTE10 | 既最上段投影の上にITEM/保護が追加され、材質だけのdata refreshが拒否 |

実2の候補見逃し62、実3の72は、それぞれ安定prefix3/5のPAUSE判断source。既Navは両方mask0。原62はLEFT/LEFT/UP、原72はLEFT/LEFT/DOWNで、元画像内の既観測床だけを使うvantageを確認した。未来の歩行成功ではない。

原8画像のPerceptionは同じd72/Core/Templatesの固定ライブラリで各1回、コンパイル0。停止pairの通常Motion/同選択は元のC8167ライブラリで確認し、原Sceneは不変。原253の既feature診断はRGB .998978644/foreground1に対し、gold IoU .904522613/coverage .952380952、dark IoU .931734317/coverage1。全ROIの背景と色境界による失格を、別の対象物だったと解釈しない。

前回の適用範囲は不十分だった。policy10だけの閉容器対策は、先行するpolicy7の価格拒否へ適用されていなかった。今回の対策/確認は[計画](../plans/test106-real-failures.md)へ分離し、過去の単体成功を実機改善完了として扱わない。

## 配布前の接続境界確認

新しいC接続5件＋直接旧11件の試験で、policy10/灰色閉容器の3配置がKERNELになるproducer不整合を確認した。旧価格観測は本体の白い模様を含む17×18pxのboxでも3群/余剰0と扱い、後から得た版2の閉容器証明へ価格を再観測せず渡していた。版2の数値検査はこの不整合を正しく拒否している。期待値・validatorを緩めず、新しい正の識別後も共通価格観測へ再結合する。これは配布前の開発試験で見つかった条件で、実機再発数へ加えない。失敗した16件の凍結実行記録も保持する。

原253の最初の最終校正では、通常分類が48.818msでUNKNOWN/PRICEのまま、Cも次周回へ採用しなかった。この失敗も保存した。実価格は8px高く、閉容器価格帯の末端で最下行が切れていたためで、処理期限超過ではない。通常商品と旧版の範囲は維持し、新版の正に識別した閉容器だけ、既に対象探索済みの帯下端まで価格全体を観測するよう修正した。

修正後の同じ原253は通常分類1回・certificate1回・公開C採用1回で完全陰性（policy7/layout2、flags0）となった。実価格boxは10×7/15×7/10×8pxで、50.040403msは元の残worker予算98.32825ms以内。原Scene/RGBA/分類Resultは不変。Cへの接続では新しいprefix/epochへResult時刻だけを換算しており、実Runtime再演・実機速度・実機リスタートの証明ではない。

最終製品はC `d2471675` / Ring `c39f67f3` / Nav `498760ef`。C継続33件の作者成功は中間Cの履歴で、最終sourceのCIで再結合する。Ringの関連19件は18成功と、新しいfixture期待を修正した1件の再実行成功を合成した記録であり、19件一括成功とは書かない。新価格C16件とNav26件は最終sourceで成功。旧104灰色閉容器の1期待値のみ、新たな正の版2証明の成功と、同値の旧版1拒否を検査する形へ更新し、他の旧assert/メソッドは保持した。

独立担当がbaseline4d084b55からC/Ring/Nav・5新試験・旧104の正当な1期待更新・選択CI156件/24scope・配布境界をsource-onlyで確認し、未解決P0/P1なし。FRESH/旧親期限一用、版2の正の閉容器識別と実価格、対象優先、候補の既知床3歩を確認した。Perception/Runtime/Wire/公開ABI・全既featureはbaselineと同一bytes。レビュー自身によるnative/compile/classify/Perception/input実行は0。選択CI・IPA/compiler/配布物の確認はこの後のrelease gateで行う。実機改善/未知精度/人超え速度は未受入。
