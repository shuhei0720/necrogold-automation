# TEST061 設計・検証記録

2026-11-10（日本時間）。[計画](../plans/test061-verified-progress.md)。初歩同期、入力/観測期限、次行動再取得、商品到達までを一つの状態遷移として検討する。原060は受領台帳に記録済み。

## 独立設計レビュー

第1周は設計P1(期限短絡後complete0経路)/P2(診断保持寿命)、網羅P1×2(ACK中track失効、実producer→暗号client)/P2×2(確認後episode境界、独立world経路)、安全P1×2(全proofのactualcommit時計、保存revisionとAPIの回復)/P2(必須閉診断schema)。P0なし。

第2周は当該差分だけ再確認し全指摘解消、3担当とも残P0/P1/P2なし。初歩旧callback無効化、元12秒、actualobserve_atと全proof後tick、snapshot消去前のfirst/latest保持、旧API回復、v14診断必須を計画へ明示した。静的設計レビューであり、実装・実機成立の証明ではない。

## 選択する検証

Controller全methodは変更が広いため実行。変更した境界の新C Red/Greenと関連Swift公開結合、client互換/両journal、独立地形worldの必要経路を選ぶ。未変更のNav/Perception/Beat/Raster・入力座標はbytesと過去の実画像結果を結ぶ。world160/全Runtime59を毎回起動せず、focused CIで実ビルド/実compiler/22seal/全9Mach-O/source ZIP同一性は維持する。未実施を成功としない。


## 実装と既知停止の回帰

原060の初歩前BEATとACK後UNKNOWN/元次拍期限による停止を別経路として修正。Controllerに確実未送信の初歩再取得、凍結scheduleD/visualD、確認後の新位相取得、全proofのactualcommit/次actualtickを実装した。Runtimeは実時計と消去前snapshotを接続、client v14/.15/cap13と旧API回収、TEST061 launcherを追加。

旧Cの独立商店worldはLEFT1歩後にUNKNOWN/LATEで商品未確認となり、商品到達assertionでRed（compile/errorではない）。同じ合成条件で修正後は10ケース成功。四方向×木鉄8、LEFT→UP、画像処理遅延のみを含む。取得24/復号60/解析16ms・cadence105ms・ACK295ms、1拍まで地形35px→36pxを描く独立worldであり、原060の欠落画像を補った再生ではない。途中UNKNOWNと拍間隔の空きもassertする。

新C境界は初歩同期・旧callback・actualcommitと全proof・元12秒・診断保持の単体を追加。実装途中の追加Redで、期限前公開/期限後begin、retune再取得ticketの8%alignment、signed時計付近の診断D、SAME/FRESH再予約の元syncD継承も固定した。既存Controllerの全method/assertを保持し、旧「失効即終了」の期待だけ新契約の撤回/再取得へ対応させる。重いworld160/全Runtime59は今回のfocusedでは未実行。

## 実装の重点レビュー

第1周の設計/安全担当が、再予約で元syncDが消えるP1を実C限定probeで確認（元12秒を70ms超えたbeginが成功）。両SAME/FRESHへ元Dを継承し、preparation queryも同Dを守る修正・Red/Greenを追加した。安全担当のP2はsync診断Dのsigned範囲超過で、sync12/walk45/session180のminへ制限し境界試験を追加。P0なし。修正差分の第2周確認・網羅確認と、最終CI/配布物結果は次に記録する。

第2周の実装差分確認で設計/安全のP1/P2は解消。網羅担当のP2（Swift after-C tickが対象proof成立を固定していない）はreason9・選択ACKのmotion/observed ID/creditとBLOCKEDのlead75msをassertして解消。worldの歩数不足許容も最終GOODS ACKだけに限定した。3観点とも残P0/P1/P2なし。その後の初歩capture終了D前/actualcommit D後の6行補正は追加Red/Greenで、診断clock1を保ち元12秒の入口は実commitで拒否する。

local最終Cは`b1bbe02da9a17ef8618aae5f7e36f059ed5736fd7cce970c0249f8ddf620f894`。新Recovery29、補強後world3method/10case、package263が成功。client212と最大reportの追加1件も成功。patched upstreamで公開Controller179/Recovery28/Beat12/world3/package262を先行確認し、最後の境界補正後は関連Recovery29/world3/package263を再確認した。全Controller184の最終確認、Macの新公開結合/4故障/shop16・実IPA/compiler照合は配布前に結果を追記する。
