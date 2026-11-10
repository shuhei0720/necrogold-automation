# TEST063: 確実な未送信の連続歩行を新しい拍へ戻す

2026-11-10（日本時間）。TEST062はユーザーの商品可視1/2、プログラムの完全商品判定0/2。成功経路/全認識閾値を保ち、2回目の3歩目未送信期限切れだけを修正する。

## 根拠と変更

受領ZIP SHA `4d1a4849e947a84e69cfd21a4c0256838c6b5a0aa49b7a8c73a0785efa2e2c91`。2回目は実C moves2、取得障害なし。frame98の実C処理と再予約が入力窓まで及び、AX前面query開始はD+1.315ms、最終gateはD+7.996ms。TicketGuardでCbeginを呼ばず、complete0がCAPTURE6として終了。古い入力は実際に送られていない。

state1の生きたMOVE・begin0/outcome0・lead確認済/moves>0・同stable ACK prefix・origin床のFLOOR world/gold候補/商品UNKNOWN・全tile/保護不変・full5判断一致・strict BLOCKED・新鮮Sceneだけを対象とする。未送信の開扉/掘削も、既存plannerが許可した同じworldであれば対象。取消/商品/終了・権限喪失・state2/3/4・不明入力・期限内complete0は対象外。実時計はmax(now,last_now)、元Dを超えた時だけ旧IDをLATE/not_sentで撤回し、新将来拍を既存post_move回復で選ぶ。同ID/元Dの延長、入力再送、移動の推測は行わない。

最後に確認したMOVED/開扉/掘削の実commit時刻をprivateに保持し、新回復の12秒をそこから数える。回復後の未送信ticketが再失効しても元episode/12秒を継承し、真の新proofだけが新予算を開始する。walk45/session180が優先。前面準備50ms、最新HUD採用、元イベント、全再予約/入力予算は維持。valid modelは新しい将来拍へ利用、失効時だけ既存fitで再取得する。

## 検証と返却

旧Cで意味のあるassertion Red→新単体/関連回帰、独立差分レビュー1回、device CIの実IPA/コンパイラ/seal/source照合。全Runtime/world/clientの再実行は既定にしない。C以外のnative/API15/cap13/client v14/ABI、成功した店への経路、完全商品/画面認識閾値は不変。TEST063の新IPA/全コードを自動失効しない固定リンクで配布し、実機の商品可視までとruntime/test-063全ZIPを依頼する。

1回目は開扉後に商品・価格が見えるがPARTIAL判定、その後pause-icon検出が一時不成立でSCREEN停止。完全商品判定の安定化は残課題として記録し、今回の期限修正へ混ぜない。
