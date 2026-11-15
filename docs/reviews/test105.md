# TEST105: TEST104実機3実行の再発確認

2026-11-15（日本時間）。受領6 ZIPは重複対を除く3実行、73 PNG・82記録。CRC・安全なパス・manifest/画像/記録のhash・decoded RGBA・安定prefix・時刻を照合済み。生資料はGit外に保持する。

| 実行順 | 元run末尾 / 判定source | 実測された停止 | 確定した原因 |
| --- | --- | --- | --- |
| 1 | c1d3… / 234 | FULLの正常UNKNOWN採用、28.735ms。RESTART intent/命令なし | 3ITEM・価格床3・両端・3価格は成立。名前の重なりで右SIGNが上側17pxだけの成分になり、左SIGNと上端は同じでも中心が6px異なる。旧全2面条件が拒否 |
| 2 | f255… / 270 | FULLの正常UNKNOWN採用、22.106ms。RESTART intent/命令なし | 両SIGN・両端・3価格・3ITEM/正確な保護は成立。3品目の価格直下の粗い地形セルがUNKNOWNで、価格床3セル条件が拒否 |
| 3 | ed7b… / 178→180 | PARTIALの正常UNKNOWN採用12.469ms後、ROUTE10で停止。元期限内 | 静止・同UP選択・ITEM/保護/旧GOLD・歩行近傍は不変。遠方の保護halo内のUNKNOWN/DOOR→GOLDを旧更新条件が拒否 |

過去FR-104-OFFER-COVERAGE/FR-104-PARTIAL-REFRESHは今回の実機で改善完了を確認できていない。今回の各拒否は前回の単体で扱った条件の外にあり、同じ症状の継続として記録する。旧コードが同じ条件で成功していたと証明する資料もなく、回帰と断定しない。

既存Perception/Core/Templatesと同一の凍結ライブラリで4原画像を1回ずつ校正。SIGN/価格/条件の診断は原2画像各1回。3実行目の通常Motionと記録されたvisitsの選択も各1回で確認した。未知評価・実ゲーム再現・修正後の実機成功ではない。受領sessionには実行IPAのbuild/hash attestationがないため、申告されたTEST104から実行版の完全同一性まで証明したとはしない。

## 修正と開発検証

Controllerの保護付き新GOLDはdata-only再判定へ渡す。看板は同じ上端と正常な隣の看板で行を固定する証明を追加。赤色の閉容器はnative限定の正の識別と別policy10へ分離し、識別された1品直下以外の未知床は受けない。対象全探索・強語veto・既閾値・旧assert・元Scene/入力権限/予算は維持する。[今回計画](../plans/test105-goods-and-continuation.md)。

Ring新7＋直接旧61＝68件成功。公開Cは新4＋直接旧15、MOVEDまで延長した新4、商品producer接続の新5＋旧6＝11件を作者証跡ごとのsourceで区別して保持する。19件/延長4の作者Cは途中source、商品11のCは最終8167、Ringは最終malformed-slot guardの前。最終CIで現在の同一sourceへ再結合する。selector6件成功、feature JSON→生成器→埋込Cの一致も確認。

各機能の実装前assertion Redを確認。CのRedは実行source/fixtureを保持。RingのRedは元nativeとlogを保持したが実行時fixture全体を未保存で、後続の陰性ケース追加もある。実行時の全sourceを凍結した証拠とは呼ばない。R2 Cの初回JSON不足、固定Ringライブラリ保存時のtransitive header不足は環境失敗として分離し、意味Redや成功へ数えていない。

最終Ring000961/C8167の固定ライブラリで、原234/270をそれぞれ通常分類1回・独立certificate1回・公開C採用1回で校正。両方が正常COMPLETE NEGATIVE、policy9/10、certificate有効・CのNEGATIVE_PAUSE(state4)になった。原Scene/Resultの画素証拠は不変。開発環境の分類は48.684/48.822msで、記録された残worker予算98.811/98.858ms以内。C接続はprefix0/新epoch・Result時刻だけを明示正規化し、実Runtime履歴の再現や入力送信をしていない。コンパイル/Perception追加は0。この2枚は校正資料で、iPhone速度・未知精度の証明ではない。

最終選択CIは98 product/14scope＋selector6＝104件/15scope、新16件/4scope。Core/fixture import閉包28、native36中Controller/Ringの2だけ変更する。Perception/Navigation/Runtime/Wire・公開/companion ABI・canonical15/ELF/G1/R12/旧104試験は保持。Wireの既数値policy/id・既slot kind/outcome内で表現できるため、Runtime構造や旧client回収は変更しない。全Runtime故障/合成worldは今回の既定にせず、未実施とする。

独立差分レビュー1回は合格、未解消P0/P1なし。数値証明で範囲確認前に加算する条件と、配布helperのselector104誤参照を配布前に修正した。Ring Redの実行時fixture未保存は監査範囲の制限として残す。最終C/Ring/manifest、生成feature一致、104件/15scopeと配布helperの結合を確認済み。

## ビルドと実物照合

[CI200](https://github.com/shuhei0720/necrogold-automation/actions/runs/43706249547)、CODE3a5042d22170fcc9d16dd784de55e07245f9b1b7で選択104件/15scope・unsigned IPA・実compiler/source/package検証が成功。標準Mac/Ubuntu、13jobの3success/10skip、必要Mac4工程と旧Runtime8skipを照合した。全Runtime再実行やMac実ゲームは行っていない。

元3artifactをAPI ID/サイズ/hash・CRC・安全パスと結合し、package/host/retained/macho/compileのread-only実物5gateが初回5attemptで全て成功。追加のnative/分類/コンパイル実行0。CODE sourceは933tracked全bytes/CRC一致、SHA97d0825d61f95efe70448367126f5441d6481e1fbe77b3e2d2f8cc9895b1ea5f。配布IPA200は18058712B、SHAf92b83165465bd581274618505bcbbeea57845f81a4447c726c93cbab316c730。

公開sourceはこの後のdocs-only閉鎖commitへ対応させ、全product/native bytesがCODEと同一の完全ZIPを検証する。固定Releaseと匿名全GET/hash/tagの結果は公開後に追記する。実機の商品確認/自動次周回・毎拍/人超え速度・稀な対象の未知精度は未受入。
