# TEST107: TEST106実機4実行の受領と修正

2026-11-16（日本時間）。8添付は4campaignとその最終runの重複対。CRC/安全path/全manifest/原記録hashchain/PNG復号RGBA/時刻・世代・安定prefixを全照合し、4実行・104 PNG・118記録・230 rawファイルをGit外へ保持した。評価に使った画像を未知評価へ流用しない。

| 実行順 | 元run/source | 実機結果と停止点 | 確認した原因 |
| --- | --- | --- | --- |
| 1 | 57b9… / 182→184 | UP開扉後、商品帯が上端で切れたままSCREEN17 / cycle_observe・ROUTE10 | 下段ITEMに支持されたtop投影追加と、遠方DIRT→UNKNOWNが同時に出現。旧成長述語は他セル不変を要求 |
| 2 | 4750… / 210→212→214 | 210→212はdata再判定、212の正常PARTIAL採用後にSCREEN17 / ROUTE10 | 既許可のtop alias縮退と、金壁で遮蔽された対角FLOOR→DIRTの同時変化を拒否 |
| 3 | f691… / 40→107 | MOVE 0、PASSAGE_WAIT_GOLDの元DでNO_PATH12 | 再起動直後の暗い原40を基準へ固定。通常Motionは40→107だけUNKNOWN、元D内の最新87→88は厳密零 |
| 4後半 | 1c88… / 438→440 | 正常PARTIAL採用後にSCREEN17 / ROUTE10 | 不変の下段ITEMが支持する、保護されたtopセル1つのUNKNOWN→FLOORだけで拒否 |

3つのSCREEN停止は正常なRingのUNKNOWN/INCOMPLETE/partial-safeを採用した**後**のC静止・進路検査失敗。cycle.statusのKERNEL表示は後の `cycle_failure` による上書きで、元の正常分類結果と区別する。元分類は約17.087/7.741/7.793ms、SCENE flag1。価格flagによる停止ではない。原182/212/438は商品帯・名前等が画面上端で切れ、絵が3つ見える場合も完全被覆ではない。陰性判定を緩めず、UPへさらに入る処理を修正する。

4実行目の前半だけは原197で正常policy9・完全陰性・3商品/3価格・flags0。C採用→保存→RESTART intent15→実ACK15→新floor225まで原記録で成立した。5番目の独立native runではなく、4実行目内の次levelで後半停止した。rawにIPA build/native source hashの証明はなく、未導入などを推測して失敗原因にしない。

## 原画像と設計の点検

不変のPerception/Core/Templatesへ結合した既ライブラリで原9画像、その後に追加87/88を各1回だけ校正。原PNG/RGBA/Sceneの不変を確認した。コンパイル・分類・入力・制御状態操作は0。現C/Navへ結合した保持ライブラリの通常Motionを6組各1回確認し、182→184/210→212/212→214/438→440/87→88は全てBLOCKED・dx=dy=0、40→107だけUNKNOWNだった。87/88は全230tile/保護が一致し、同prefix3・独立取得で元Dの約877ms前に解析完了している。

全Scene述語をORしていた旧関係は、個別の許可変化の合成に閉じていなかった。投影のセル役割と残セルの既静的関係へ分離する。[計画](../plans/test107-partial-composition.md)に、下段支持/正確mask/他下段ITEM併存の拒否・元期限/一用・最新対象判定優先を記録した。既entry episodeの拡張は4境界の変更が必要なので採用しない。Ring/Nav/Perception/Runtime/Wire等の変更は不要。

## 実装前の確認

現C d247と実行時の全依存sourceを凍結。PARTIAL新5method＋承認した旧101の1methodは、6 tests / assertion failure7 / error0 / skip0。初歩前再取得は確定した元2拍Dを持つfixtureへ資格化した最終新7methodで、旧Cに対しfailure3 / error0 / skip0。初期fixtureには未確定Dの代わりにhorizon表示を読んだもの等があり、未到達・状態不一致の試行は原因のRedから除外して保持した。環境・コンパイル失敗もRedには数えていない。旧101のoutside subcaseだけを、新しい正の合成証明で適格になる期待へ更新し、他method外bytes/他faultの拒否を保持した。

独立差分点検では、episode開始前の既知MOVEDを記憶せず、その後のUNKNOWNでdata基準を置換し得る不足を検出した。元D確定・MOVED/UNKNOWNを通常関数で事前確認したRed1 / error0を凍結し、初期GOLD待機の既知MOVED/非零をepisode前からstickyに拒否する限定修正を加えた。これは配布前の新確認で、実機再発数へ加えない。

## 最終sourceの作者検証と原画像校正

Controller `fdbc142cb7366c686e16296168a668eb80e432467526817c7d8ce92395e78822` でPARTIAL新7＋直接旧17の24件が成功。初歩前は新7成功と直接旧15成功の別receiptであり、単一22件実行と書かない。選択CIはこの46件/11scopeにselector6を加えた52件/12scope、新14件/2scope。selector自身6件だけは最終sourceで成功済み、CIはこの後に実行する。

関連連鎖は、複合投影変化→新jobの手続き的な安全PARTIAL→独立零→UPの実ACKと別の実MOVED→新しいFULL sourceを通した。同じ移動済みScene/手続き的RGBAから通常Ring producerがpolicy9の完全陰性を作り、C採用→保存→intent→実RESTART ACK→次floorまで成功した。UP前のResultはC単体の手続き的データで、全段を実画像認識や実ゲーム再現と呼ばない。

最終C・保持作者lib・元Scene/recordをhashで結び、test-only wrapperをO0で1回compile/linkして原3pairの純粋な役割証明だけを各1回確認した。実1は新ITEM=2、実2はalias=1、実4後半はdata=4で全て成立、元230cell/Scene不変。UP開扉ACK/正常safe PARTIAL等の記録済みcontextだけを正規化し、入力権限や実Runtimeの継続を作っていない。

再bind後に使う原184/440へ、不変のRing c39fの正規APIを各1回実行し、いずれもOK/UNKNOWN/INCOMPLETE・safe partialを確認した。約11.118/8.756ms。元capture→新job trigger想定時刻の差から残worker予算100msを用いた校正で、未知のqueue遅延を補完していない。全商品の対象なしではなく、最新の未観測を保持する結果である。原11 Scene/RGBA・旧校正receiptは不変、追加のPerception/制御状態操作/入力/明示certificate検査は0。

独立source-onlyレビューは最終C/他35native保持・作者証跡125参照・原校正・旧101限定変更・CI52件/12scopeの選定・6配布helperと4pending fenceを確認し、未解決P0/P1なし。episode前MOVEDの不足は資格Redとsticky修正で閉じた。初期GOLD waitのactive0未dispatchという仮説は、既分岐がactive1を設定していることを確認し否定した。レビュー自身のnative/試験/compile/classify/Perception/入力/CI/公開実行は0。選択CI・新IPA/配布物照合は次工程とする。

原Scene/Motion校正は条件を特定するための補助で、未知精度・実Runtime再演・実機改善・人より速い処理の証明ではない。
