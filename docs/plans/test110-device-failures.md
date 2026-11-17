# TEST110: TEST109の4停止とイレギュラー再試行

2026-11-17（日本時間）。基準 `c2f7624`。ユーザー実機の停止を主に、原因を確認した局所修正を行う。実機の未達を単体合格で改善完了にせず、何をどう修正したかを次のテスト依頼へ明記する。

## 1. 概要・受領

8添付は4固有run。全ZIP CRC/安全path/重複bytes、manifest/108記録のhashchain、98 PNGの896×414 RGBA hashを照合し、214論理ファイルと原本をGit外へ保存。単調時刻順は8d78→9bf5→fe54→80c6で利用者の4周に整合する。原記録はIPA/build来歴を証明しない。

## 2. 背景・確認した原因

- 8d78: 最初のLEFTは実ACK既知だが、最初の適格189でgold_state UNKNOWNを新規入力の拒否条件へ先に渡し、ACK後の変位比較0回でSCREEN17。189は元visualD内に約2.418秒あり、generic stopのdeadlineは入力窓でvisualDとは別。原178→189は半端なcamera変位で通常Motion UNKNOWN、unitに書き換えない。
- 9bf5: 開扉後FULL210は正常UNKNOWN。元画像への完全材質一致を待ち続け、遠方2セルのUNKNOWN→FLOOR/DIRTが戻らず元Dで終了。原250は現行Ringだけで正常完全陰性/C検査1、同prefixの適格な撮影で元Dまで約795msある。後の251〜264はまたUNKNOWNのため、250の判定jobを最新版追従で破棄してはいけない。
- fe54: 開扉後244→245は通常strict BLOCKED零・同じ完全LEFT判断。遠方DIRT→FLOORと、次床の対角にあるbracketed DOOR→GOLDだけで未送信入店票を拒否。実進行先は観測FLOORのまま。隣の敵は後方で、停止時点の攻撃/死亡は確認されない。
- 80c6: 正常safe PARTIAL317からの入店credit中、321のSHOP/商人表示に重なるpause iconだけが既matcher不成立になりScene UNKNOWN→ROUTE10/SCREEN17。footer/zone/floor/death検査の別原因とは分ける。

FR108/109のFULL待機・PARTIAL材質・端ROI・価格証明を先に照合。今回はRing閾値を変更しない。敵/死亡が確認されない4停止をイレギュラーとして一括リセットしない。

## 3. 設計・担当境界

1. CのACK確認と新規入力資格を分離する。input3/同known-ACK MOVE/current-prefix/元visualD/元8評価だけは、gold UNKNOWNを変位比較より先に致命停止させない。変位確定後もUNKNOWNなら新入力を撤回して有界の無入力待機へ。後の独立した正常Scene/静止/経路資格を満たすまでMOVE/RESTART0。旧clear判断をリスタート資格へ流用しない。
2. CのFULL/UNKNOWNは元D内のDATA-only再分類を追加。pendingでない正常UNKNOWN・新しいstable/current-prefix/fresh FULLと同じ商品/金壁/保護、元anchorへの直接strict零を要求する。古いslot/model/proofを撤回し、新jobを通常producerへ。移動証明の元Scene/IDは別に固定し、分類sourceだけ更新する。開始したjob250はpaletteだけの後続251で破棄せず、元Source250の結果を通常の独立検査・保存/PAUSE/intent/RESTARTへ渡す。pending中は最初の適格な次frameを有限1枠で保持し、後着paletteで上書きしない。元一用/D/選択を保持し、正常UNKNOWNでも旧移動anchorへの独立証明からの観測一歩を失わない。Runtimeのjob切替時もneeded IDの既cycle.framesを移送元に含め、recent4より古いqueued sourceが失われないよう有界で保持する。現在Runtimeの選択callbackで画素の受渡しを確認する。候補・失格・元期限/予算は保持し、未観測を陰性化しない。
3. Cの確実未送信入店のDOOR→GOLDは、対角の正の閉鎖だけを別証明する。現在/次FLOOR・crossの実移動足場・old/new金壁bracket・全保護/商品・同完全判断・直接strict零を保持する。通れる床を追加せず、方向/目標変更や既知でない入力に広げない。
4. Perceptionのpause iconは旧raw/13・11・9px縦openingの後だけ、3×9矩形openingの正の証明を追加する。同じ55/85+既neutral mask、zero-padding erosion/dilation、full36×36 reference/0.8 IoUを保持。原321は314/386=.81347、307/378=.81217で成立する。出力は観測maskの部分集合で、crop/埋戻し/閾値緩和をしない。7px縦openingと厳しい無彩色案は不成立として採用しない。旧matcher/全footer/zone/floor/death拒否、UI不正/非opaque/別画面拒否を保持し、通常Perception→Cの次guardまで確認する。
5. 敵による進行不能/死亡のリスタートは最新要件へ追記。[別の8項目設計](test110-irregular-retry.md)で正の根拠と各UI資格、入力/保存/診断を確定する。R12の正の死亡promptはあるが、保存された死亡後タップ画面は現在未確認。古い画面へ既知座標を無条件送信しない。新入力境界/API/Runtime変更の独立重点レビューを先に閉じる。

## 4. 影響範囲

現時点の修正所有はCの3局所処理、Perceptionの正のicon認識、Runtimeの必要queued画素の保持。Ring/Nav/既feature/ELF/G1/R12は保持。public Scene/Status/Event ABI、API/cap、Runtime/取消/owner・prefix、元期限/予算はイレギュラー設計が確定するまで変更しない。raw資料は公開しない。

## 5. 新規試験・期待値

各機能で変更前の実assertion Red→最小Green。ACK中の非unit/期限/回数・送信UNKNOWN拒否、変位後の無入力待機と新しい正常資格、FULL250の通常producer/採用/耐久保存/RESTART連鎖と251の非失効、閉鎖対角/未知足場/近傍保護の拒否、pause iconの実画素/異常画面を確認する。期待値は原画像/時刻/要件と対応させ、未保存の未来画像・実応答を実機再現へ数えない。

## 6. 実装順

確認済みCの3原因、原321の正のPerception証明、イレギュラー設計/独立レビュー、各Red→Green、最終差分レビュー、選択CI/同source IPA/完全source・実compiler/配布物の照合、固定Release、次の実機の順。独立原因は同じ版へまとめる。根拠のない全体試験を既定にしない。

## 7. コミット前・配布検証

変更部と直接関連回帰を選び、境界を変更した場合だけ該当結合を追加。旧assert/拒否条件を削除/skipしない。標準macos-26/ubuntu-latest、source seal/実compiler/IPA同一性を維持する。新規Runtime入力境界は静的レビューだけでなく実callbackの選択結合で確認する。

## 8. 範囲外・返却

未知精度・毎拍/人超え速度・耐久の受入、未保存の未来Sceneや敵の種類の推測、購入/宝箱開封、遠隔/iPhone8開発は範囲外。実機の商品到達率を主指標にする。配布時は何をどう直したかとIPA/完全source、更新/再起動/Start Server・通常1-1ポーズからのiSHコマンドを返し、全照合後のcampaign ZIPと全run原本保持を依頼する。
