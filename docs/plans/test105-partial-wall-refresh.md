# TEST105: 開扉後、商品保護と重なる遠方金壁の再観測

2026-11-15（日本時間）。TEST104実3の178→180は開扉ACK後、正常なPARTIAL UNKNOWN採用12.47ms後にROUTE拒否。元親期限は約2.52秒残っている。両Sceneの通常Motionは厳密零、完全5field選択は同じUP。ITEM集合・全保護・既GOLD・両MOVE 3×3は保持され、差は遠方のUNKNOWN/DOOR→GOLD（保護あり）とSTONE→DIRT（保護なし）だけだった。

修正前にFR-100-OPENED-GOLDとFR-104-PARTIAL-REFRESHを照合した。前者は非保護金壁だけ、後者も変更セルの既保護を拒否するため、今回のITEM十字投影と重なる壁を対象にしていない。旧対策削除の回帰とは断定しない。

Controllerの既fresh data rebindで、固定MOVE近傍外の保護セルが新しくGOLDとして確認された場合だけ最新immutable通常判定へ渡す。旧ITEM/全保護/既GOLD・同選択・厳密零・元prefix/親期限を維持する。歩ける保護セルやITEMへの変更は許可せず、旧credit/票は撤回する。最新判定と別の独立した静止確認が揃うまでMOVEしない。Ring/Navigation/Perception/Runtime/旧ABI・予算は変更しない。

実装前の公開C assertion Red→最小Green。開扉UP・保護付き新GOLDの正常再判定/新しい静止確認、陰性化しない候補保持、近傍/ITEM/保護/既金消失/静止不足・prefix/期限拒否を確認する。直接の旧partial refresh/entry回帰と独立差分レビューを選ぶ。原pair校正と手続き的な公開C試験は実ゲーム到達の証明ではなく、下側を含む3商品確認と対象なし次周回は次の実機で確認する。
