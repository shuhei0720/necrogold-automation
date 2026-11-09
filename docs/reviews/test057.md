# TEST057 独立レビュー・検証

2026-11-09（日本時間）。[計画](../plans/test057-floor-quantization.md)に従い、暗い床のB下限だけを校正する。全経路毎拍・店到達の受入は未完了。

## 計画レビュー

fresh設計/安全第1周clear。網羅第1周P2「新下限×金壁bracketの認識→Nav/Motionの複合期待が曖昧」を、下限内/外×横/縦、単発probe/safe_floor除外、開通とunit変位の区別、曖昧な開通を成功にしない期待へ補足し、第2周clear。残P0/P1/P2なし。

実装前に既存152＋056ゲーム13の165画像を原画素の実Cで比較。+100は213セル、+155は269セル、+200は283セル、.50は290セルをDIRT→FLOORへ変更し、他のScene fieldsは不変。+155の全269セル（既存230/05639）はAI担当が原寸contextと境界例の原画像で床と暫定判定し、真壁/扉/商品/保護セルをfloorにする例を発見しなかった。候補union290の目視ラベルはGit外、SHA `560b1aa72de6d42e8c27f3f6f3250ee3e5bbfe25551814c1e20e40e5e959e8f7`。同資料のhumanというファイル名は人間の確認済みを意味しない。人間のラベル確認と未知実機受入は未了であり、未知配置への保証ではない。

+155はRGB整数各1単位の変動に対応する線形式の幅として選び、正確な中央値計算の丸めバグとは扱わない。+100は最新2比較の揺れが残り、.50は既存negative RGB(50,25,25)をfloorにするため採用しない。+155も91→93の経路外1セル、15→68等の変動は残る。既知の停止直前103/104/105だけはtilesが一致し、記録位置の判断は68以降RIGHTになる。新RIGHT経路の応答画像は未観測である。

旧実画像の分類修正により、TEST051 capture79の遠方target、TEST054記録69/70のDecisionと60初歩も変わる。当時のreport/manifestは保持し、当時DOWNの60→69を新LEFTの成功に流用しない。旧FRESH・latest source/五項目Decision/凍結時刻/取消等のcoverageは合成Sceneと明記して維持する。

## 実装・実物

旧C SHA `eda7134a56f3bc43baed5de75933de0a4d72f92da7497ea972787c4b979648c3` で、新synthetic floor期待・実056原画floor期待のassertion Redを観測した。Cprofileも全compile成功後 `FAIL profile_floor_quantization_known_tile` / exit1。最小修正後Perception17件/170path、Cprofile Scene132×23864bytes・orientation40・fingerprint129・新色境界40がGreen。GCCの結果であり実Macとは区別する。

local全238件の初回は237成功/1失敗（129.838秒）。失敗は記録評価器の旧69/70 Decisionと旧未観測分岐期待で、新分類のLEFTとcapture60/70双方の未観測を明示した。元report・DOWN実変位・goal fail/exit1・full replay=false・未来画像不使用は維持。対象module全22件を最終再実行し22/22成功（4.979秒）、他216件は不変で成功した。skip0。package/helper221件（1.661秒）、client197件（49.658秒）も成功。

新C SHA `b1af1db64671c5fc61b935e21c79abb3e21293f82ac21df3320cd96d8a0cb88c`、seal `cee2d62641fdbb29fc235158568afdcafe6a5aba30e7ae0eb0f70a022583c4e5`。全22source中Perceptionだけ変更、他21source・G1/R12原bytes不変。固定旧056 CのO0/O2両objectへ新semantic試験を実行し、同値だけで成功させず上記floor assertでRedとなるhelperもlocal成功した。

fresh設計・網羅・安全のsource実装レビュー第1周と補足で残P0/P1/P2なし。資料P2（testing導入の旧152件/目視ラベルSHA）を同期し、評価器の未更新分岐期待P1も訂正してGreenを独立確認した。旧FRESH3例のassert3/3/9件とreference guardを保持し、明示合成へ移したFRESH3例は公開CIへ戻す。私有画像22methodだけを厳密名集合で除外する。実Mac・IPA/全sourceの照合は同周の後続補足で未確認。

実TEST056の現C再評価もintegrity pass、商品到達fail/exit1、完全Controller再生=falseのまま。新たなLEFT/RIGHT入力の成功を録画から補完していない。
