# TEST104: 実機の上部入口停止・商品判定・通路見逃し

2026-11-15（日本時間）。[要件](../requirements/necrogold.md)・[制御契約](../contracts/native-control.md)・[対象判定](../contracts/target-assessment.md)・[実機結果](../reviews/test104.md)を根拠にする。

## 原因と変更範囲

1. 開扉後の3停止はLEFTからの入店。正常な部分判定後、次画像のROUTE検査で停止する。既UP専用episodeへ無条件に入れず、旧分類sourceに依存する継続資格の扱いを実差分で確認して修正する。遠方の材質例外を根拠なく増やさない。
2. 商品可視の原205は正常なUNKNOWN判定。全商品被覆と店外壁形状の過剰な結合を分け、正の店認証・全対象探索・余剰商品/価格・両端の被覆を独立に確認する。全商品の名称登録は追加しない。対象/候補/未観測は保持する。
3. 原116の候補見逃しは、既上左口のUNKNOWN専用条件と実FLOORの不一致。旧branch/旧拒否assertを保持し、観測FLOOR mouth・両flank壁・元outer/roof/left壁支持・outside UNKNOWN・既観測上vantageまで3歩を必要とする別guardを追加する。未知外床や普通扉へ直接進まない。

Controller/Navigation/Ringの必要な局所だけを変える。Perception/Runtime/旧ABI/旧回収/累積予算・期限・UNKNOWN無再送を保持する。確定した述語と設計は実装前に本計画へ追記する。

## 確定した局所設計

3つの停止pairは全て通常Motionでstrict BLOCKED、dx/dy=0。ITEM/保護は不変で、既観測の開いた入口と次の選択は維持されている。原250→252の新GOLD/遠方材質、214→216の遠方FLOOR→DIRT、332→344の遠方FLOOR→DIRT等が旧静的材質許可の範囲外だった。

安全なPARTIAL UNKNOWNを採用した後、元prefix/期限・strict零変位・近傍footprint・既GOLD/ITEM/保護・同選択を確認した新観測は、古いcredit/確実未送信票を撤回して最新immutable sourceの通常判定へ渡す。OBSERVE_MOREとcredit発行後の両方へ接続する。古い結果でMOVEせず、新結果と別の独立した静的確認が必要。親期限/入力予算/取消/候補優先を更新しない。

原205では両full SIGN、両raw endcap、共通価格3/余剰0、商品presence3が成立した。旧3..8形状は全て不成立で、glyph/merchantの旧固定描画閾値も不成立。新policy9は入口の壁形状と商品帯被覆を分け、実2full SIGN・実GOLD・3ITEMと価格域の正のFLOOR被覆、両cap・共通価格・全B対象探索・強語veto・余剰検出を独立に要求する。旧1..8/旧閾値/商品帯サイズは変えず、Cでも証明を独立検査する。未観測の価格床を補完しない。

新policy9の商品帯は既非HUD中央域x=143..663、y=45..315へ全体が収まる必要がある。選択した3ITEM以外のITEM、3ITEMの十字近傍で説明できない保護、保護の欠落も拒否する。原205は3ITEM/保護11が正確に対応する。この追加証明を旧形状policyへ無断適用しない。

## 下側の商品を全て見るための追加確認

ユーザーの「下の商品が全部見えるまで歩く」再確認を受け、配布前に確認を追加した。既存の新連鎖は最初のDOWN後の候補保持で終わり、全商品可視までを証明していなかった。

1. **目的**: 入店・一歩DOWNで完了にせず、下側の商品/価格が全て確認できる位置まで、各画像を再判定して進む。
2. **原因**: 既NavはITEM row+2を画面内と扱うが、商品帯B下端は322で中央315を越える。公開C連鎖でも最初のDOWN後に次の票がUPになるassertion Redを確認した。原332はrow+4の7ITEM投影で、3ITEMだけの試験ではrow+3の過剰保護拒否も見落とす。
3. **局所設計**: 既Nav/UP episodeを変えず、入店が実移動で証明された通常商店にDOWN専用の有限観測を追加する。全ITEMの±18px投影/名前/価格域と、全coherent row/partialの探索域（最大slot sy−32..sy+115）を一つの保守的potentialへ含める。初回n=ceil((下端−315)/36)・元親期限・world基準potential/level/入口identityを固定。x全体143..663、n歩後の上端45以上が必要で、残入力予算を増やさない。
4. **保存証明**: このx域/y≥45の既HUDはheart下端321..414とfooter380..414の下向き閉集合。DOWNでworldが上へ36px投影されても既可視potentialを新たな下端HUDへ隠さない。上端条件でpauseへの侵入も防ぐ。未観測部分は毎回新しい画像/正常workerで確認し、幾何計算を対象なし証明に使わない。
5. **各一手**: 最新UNKNOWNの全上界/強語veto・正確なITEM/保護・観測非保護FLOORの実footprint、別のstrict零比較を必要とする。新票→既知ACK→通常の実MOVEDだけでworld offset/nを進め、新immutable jobへ渡す。次の床は次の観測で確認し、n枚を予約しない。遠方材質変化は元親期限のまま票撤回/最新再判定とする。
6. **優先/終了**: 対象・候補・独立した完全陰性を先に処理。pending workerの元期限/FIFOを保ち、観測親期限切れで候補結果を捨てない。potentialが収まった後も不明なら保持し、旧generic歩行へ落として入口側へ戻さない。実変位UNKNOWNは加点/再送しない。
7. **確認順**: coherent部分slotを使うassertion Red→最小修正→3ITEMと7ITEM row4→row3→真のFULL3 row2→row1の公開連鎖→通常policy9→保存/intent/実RESTART ACK/新floor。元の早期候補保持は別に保持する。取消/prefix/期限/保護/worker/非零/不適格ROIも確認し、変更Cの関連試験と独立差分レビューを追加する。
8. **範囲外**: 全Navの経路条件緩和、4方向の一般観測探索、未知床への操作、予算/期限延長、未観測商品の陰性化、購入。Runtime/公開ABIは不変。Ring/Navの同一bytesの結果は再利用し、実機での全商品到達は次の実機で確認する。

通常producerの強い看板/商人条件が成立するFULL row+2も確認する。レビューで挙がった「producerはHUD交差を許す」という前提は、既box_validが同じ7HUDを拒否するsource照合で誤りと確認した。既UNKNOWNの境界を通常producerで確認し、冗長なpostguardやCの無効陰性を不明へ変える処理は追加しない。Ring f80の変更部・旧1..9/閾値・元205校正を保持し、原画像を再分類しない。

## 確認と返却

実画像/元記録で原因を絞る→実装前assertion Red→最小修正→変更部の単体と直接回帰→独立差分レビュー1回→新IPAと完全sourceの同一性照合→固定GitHub Release→実機試験。原Sceneの校正は一度固定し、未来の画像や未記録private状態を実履歴として補わない。

必須拒否: 対象/候補、不可視商品、古い/別prefix、未確定入力、取消/前面/lock/owner、元期限失効、未知床/保護セル。商品完全陰性だけを既存の保存・intent・実RESTART ACK・新floorへ渡す。単体/校正/CI成功はiPhone改善の証明ではない。

通信・取得・queue・Runtime構造を変更しないため全Runtime模擬試験は追加しない。native変更に必要な選択検証・IPA作成・source/seal/compiler/実物照合を行い、通常1-1ポーズから候補探索→入店→商品判定→対象なし次周回を依頼する。
