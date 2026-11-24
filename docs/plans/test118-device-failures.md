# TEST118: TEST117実機4失敗の修正

2026-11-24（日本時間）。基準は公開TEST117/build253、CODE c5bf0f8、保存419b558。前版の補助検証を実機改善完了と扱わず、今回4周を不合格として原因から確認する。

## 受領と現在の事実

8ZIP/4campaign/4run、96PNG/110記録を全bytes/SHA/CRC・PNG raw・recordchainまで照合。同梱ZIPと別添も一致。各runのclock_idは固有であり、別clockの差を同一runの期限評価へ使わない。受付/uptime順が一致する。全てchild0停止、collection completeは回収状態でありゲーム成功ではない。原本はGit外。

| 順 | run先頭 | 利用者の観察 | 元記録で確認した停止 |
| --- | --- | --- | --- |
| 1 | 4c651e | 3歩で停止 | cmd8 UP/ACK後、元106→127の8評価がUNKNOWN、MOVEMENT10。native moves2、未知の実変位を0歩と断定しない |
| 2 | 006989 | 金壁候補途中の通路で停止 | cmd8 LEFT/ACK後、元135→155がUNKNOWN、MOVEMENT10。native moves4 |
| 3 | 1fd786 | 商品可視後RSせず停止 | UP開扉後のFULL、Ring17はUNKNOWN/incomplete、SCREEN17。元worker結果と採用前拒否を分けて調べる |
| 4 | bf7b21 | 上部横扉を開けて停止 | 開扉147/同prefix149、PARTIAL UNKNOWN採用後のcycle_observeがROUTE10。元親期限前に停止。新V2は内側をLEFT/LEFT/DOWN/DOWN/DOWNして全商品と3下床を見る必要がある |

## 修正と検証の選び方

1. 修正表の同症状/元対策を確認し、実source/時刻/prefix/通常producer/拒否guardへ原因を結ぶ。似た停止名だけで117の未送信静止問題と同根因にしない。
2. 対象の実画像と元入力/ACK/期限を使う旧Redを先に固定し、同条件の新しい正しい資格を確認する。未収録の未来は独立モデルへ分ける。実機完全再生とは呼ばない。
3. 原因が確定した範囲だけ実装し、変更部の単体・直接関連回帰、独立差分レビュー1回を基本とする。入力/画面/判定受渡しの境界を変えた場合だけ、その境界の結合を追加する。
4. native変更時は新IPA、37source封印・実compiler・配布物/完全sourceの同一性、固定Release/匿名全取得を確認する。旧117の検証は再利用根拠と過去結果のlabelを付け、無関係な全故障集合やreader修理を既定にしない。
5. 配布時に修正点・検証・未確認と具体的な実機手順を短く返す。主指標は商品3つの観測→判定→必要時の実RS→次周回。初回rootRSと停止後全回収を維持する。

## 維持する条件

対象/候補の保持、正の画像と同商品の価格補助、全正探索領域、未観測陰性禁止、自動購入なし、UNKNOWN送信の無再送、元期限/予算/owner/prefix/取消、毎拍歩行・人より速い実効処理。全商品名登録、固定価格への置換、数値閾値/期限の拡大を安易な解決にしない。R12/G1/保護特徴資産、不要なAPI/ABI/Runtime/Spool変更、PC遠隔運用を混ぜない。

## 確認した原因と限定設計

- 歩行2件は、元authority画像では通常MotionがUNKNOWNだが、確実preinputの新画像から同じ実後続を比較すると通常unitが成立する。raw単独閾値やHUDで見えない旧扉を補完しない。既continuous SAME再発行で元target/ordinal/窓/親期限/period/準備epochを保ち、P/10以上離れた独立新画像を一度だけauthorityへ移す案を検証する。既chain2/global8、確実未送信・同prefix/choice/保護/通常strict零を保持。新referenceを旧閉schemaへ混ぜない。原HUD/modelの未保存部分とRuntime queue費用を明示し、ACK/credit/次拍は別に確認する。
- 商品3周は、price_witnessの既18ink断片除外がpolicy17だけ未継承。限定差分で最初の保存FULL106が通常完全陰性/Ring数値証明になる。107/108は右端floorの既色比証明が別に不成立で、閾値を上げない。またactual job3/source107が未完了の間の108の遠方材質変化でsticky拒否する機構を確認。通常DATA-only証明はこのpairで成立し、MOVE/UP信用を与えず判定受渡しへ限定する。未保存job1/2のsourceと返却順を捏造しない。
- 上部4周は、同固定147→149で遠方DOOR→GOLDとGOLDに遮られた対角DIRT→FLOORが同時に起き、既quiet/current DATAの適用が合成されない。新refreshは元anchor/prefix/全GOLD・ITEM・保護・同choice/通常零・一回/共有DATA2を保持してDATAへ進める。既7幅/y3のV1を残し、実5幅/y4・屋根y−1・外壁/門支持のV2を別に実装した。
- 原149から親Dまでは約2.537秒。新DATA後のreleaseを約2ms跨ぐ次captureを捨てると1拍失い、実処理を含む4歩が不足し得た。凍結source-end以降・同prefix/非inflight・実commit時oldworker return済みの独立画像を最初の一回だけ使い、元phase/予算の4歩clock/実費接続を確認した。source-endはjob/capture/prefixと固定し、後の画像から取り違えない。

独立futureのrow2では下床1セルがHUDでUNKNOWNになる追加問題を検出した。3商品が見えても足場証明を補完せず、[V2の5歩と初回予算配分](test118-upper-five-step.md)を別計画/レビューで実装。V1のHHDD4/元親期限は維持し、V2だけHHDDD5に必要な1periodをadmit前に一度割り当てる。route上限は固定し、各job continuationは既source/model期限でその上限以下へ短縮できる。凍結cycle_sync_deadline・walk45秒・session180秒/campaign rootに加え、active前の現在のsync_deadlineによる独立parentも尊重する。

新5歩componentは元記録のphase/cadence/ACK/responseと通常再fitを使い、初期constructor/admit832,790nsを含む全C実wall費用を課金して、最終100ms worker slot（callback/境界込み）のOK/UNKNOWN採用後に417.972ms残った。元parentによる4歩証明とは別で、正常Ring陰性/RSの結合証明へ流用しない。host別試行のbegin15.387ms/10ms超過不合格も保存し、iPhoneでの速度・成功は未確認とする。

5歩後の全3下床を使う片面policy18は、完全1SHOP/3ITEM/halo/両cap/3価格/全正探索を維持し、屋根・側壁・商品4row上の入口を挟む14個以上の観測GOLD支持をRingとCが別々に確認する。未知の下壁や床を補完せず、旧policyの範囲は変えない。

実Mac257でpreinput境界は合格。上部の実send期限超過は[begin重複計算の限定削減](test118-upper-begin-cost.md)、DATAの観測先着を作れていない試験順序は元100ms内の一件fenceで追加検証する。各不合格原本を保持し、新しいMac結合・IPA同一性・実機受入へ進む。私的cutや単体の合格を全過去state再現・実機成功と書かない。
