# TEST106: 開扉後、商品判定前と部分判定後の再観測

2026-11-15（日本時間）。TEST105実1の235→236は商品UNKNOWNのまま開いたLEFT入口の未送信票をFLOOR7で撤回。既FLOOR/UNKNOWN材質変化は遠方で、入口と同じ選択/保護/近傍/旧金は維持されるが、UNKNOWN→GOLDを旧opened-entry関係が拒否した。通常Motionは厳密零。実3の310/312→313も同UP選択・通常厳密零で、保持された7ITEM行−4の上に7ITEM行−5と説明可能な2保護端が加わった。旧top-aliasは消失だけ、旧新ITEM再判定は未送信credit中を扱えない。

FR100の開いた入口/新ITEM、FR104のdata refresh、FR105の保護付き新GOLDを照合した。今回も実機改善を確認できず、旧対策を改善完了として原因から外さない。商品判定前の正の壁増加と、判定後の投影増加を別の境界で直す。

- 既cycleの実同方向開扉ACK後だけ、固定MOVE両3×3外のUNKNOWN/DIRT→GOLDが既観測GOLDへ隣接する正の壁延長をopened-entry関係へ加える。旧金/全保護/近傍/既材質・同完全Decision/厳密零、元FRESH入力窓・再予約数・期限/予算を維持する。legacyへ広げない。
- 最新部分判定で安全なUNKNOWNを採用した後、保持された行−4に直接支えられる行−5の投影増加だけ、一度限りの新商品再判定へ渡す。旧ITEM/旧金/旧保護を保持し、増えた保護はその新ITEMの十字投影だけ。確実未送信のcredit/票を撤回して新しい通常jobへ渡し、最新結果と別の独立静止確認が揃うまで新しいUP入力なし。元親期限/候補保持/UNKNOWN無再送は維持する。

実装前の公開C assertion Redで確認し、実行時のfixtureとnative sourceを保存する。正常な元入力窓保持・ACK/MOVED・新worker受渡し、候補/対象保持、近傍・保護・旧金消失・不正投影・非零/UNKNOWN変位・prefix/期限/取消を選び、直接の旧entry/partial回帰を追加する。Perception/Ring精度・未収録の後続画面をこの手続き的試験で証明しない。Controllerの継続部だけの局所変更で、ABI/Runtime/入力予算・期限は変更しない。
