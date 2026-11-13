# TEST095: 候補見逃しと商品観測の継続

2026-11-13（日本時間）。基準2af68f63ee14a4523374bf563ae0b15afefdfdb2。CI/配布物照合済みの実機主導修正。[要件](../requirements/necrogold.md)・[制御契約](../contracts/native-control.md)・[修正表](../fix-records.md)を維持する。実機改善は未確認。

## 受領と原因

094の4 ZIP/82 PNGは全CRC/SHA・専用manifest/記録chain・画像metadata・登録集合・archive inventoryを照合済み。実時刻順はedad→656a→4835→c1d（添付順と異なる）。実1はrestart12/0歩、実2は8歩/開扉後PARTIAL、実3は2歩で未送信拒否後BEAT、実4は4歩/商品が画面上端でPARTIAL。後二つの判定実行は対象なし確定ではない。

実1の原146は保持済み。094とは別の上左の分断された屋根と暗い曲がり口で、既存候補mask0。実2/4はclassifier正常・制御採用後、観測継続の地形比較で停止。実2は遠方DIRT二セル→FLOOR、実4は遠方DIRT一セル→UNKNOWNだけが変わり、最新判断・全保護・strict静止0は同じ。実3はUP入力を一度も送らずMOTION拒否し、静止再観測2拍期限で終了。最初のMOTION不成立は診断中。

## 限定修正

- Nav: 原146に対応する上左bit0の有限仮説だけ追加。六UNKNOWN・両屋根側/左壁の観測支持・既観測FLOOR経路3歩を要求する。UNKNOWNを床にせず、金壁や店の存在証明へしない。他候補bitと旧判定を保存する。
- Controller: PARTIAL観測継続に限り、同じ完全判断・全保護・strict静止0・原点/次床周辺の不変を保った、非保護の遠方DIRT→FLOOR/UNKNOWNを別FRESHとして検証する。GOLD/STONE/DOOR/ITEM・その他の変化は拒否。元ticketを復活させず、新しい将来拍・元deadline/累積予算で歩く。上側入口から商品のある下側へ、観測済み床の判断を逐次更新する。記録外の未来画像や店内到達を捏造しない。
- 実3は厳密な原画/時刻診断後に必要な対策を追記する。送信済UNKNOWNを再送する変更や時間延長はしない。

## 確認と返却

各修正は実装前assertion Red→変更部Green→関連回帰。Navの094/084/086/072、ControllerのPARTIAL/FRESH・保護・未送信/UNKNOWN・開扉後の該当ケースを選ぶ。画像は各原寸を一度だけ校正し、調整runを未知評価へ数えない。通常の独立差分レビュー1回。通信/並行境界を変更した場合だけ該当結合を追加し、同一bytesの旧Runtime/API/FS等の証跡は過去結果と区別して再利用する。無関係な全world/故障集合を増やさない。

native変更後は実IPA・36seal/実compiler/9Mach-O・完全sourceを照合し固定Releaseへ保存する。新試験番号の起動/ZIPラベルは旧回収を壊さず追加する。通常1-1ポーズから候補探索→商店→全商品確認・判定→確定対象外なら次周回を依頼し、全保存終了後の表示ZIP全体を返却してもらう。

## 実3の限定静止証明

原129→132/155を不変Perceptionで一度校正。旧STONEは一個だけで、既2個条件と092の2GOLD条件は対象外。rawのzeroが最良でrunner差は.08以上だが旧.45閾値を超え、独立blur-zeroは.45以下・他72比較より小さい。world95/axis75/全72への15pt leadも成立する。旧ng2_motionのUNKNOWNを変えず、確実未送信で退役した通路入力のstationary_waitだけに別のzero専用証明を追加する。

新証明は両FLOOR/CLEAR/商品UNKNOWN、両原点と次床FLOOR・両3×3完全一致、全保護/GOLD/DOOR/ITEMなし。旧STONEを一個とし、その観測位置を保持してHUD外に置く。HUD外の共通DIRT9以上、STONEとDIRT支持が2次元であり、元の9配置（zero/四軸±1/±2）で旧STONEとDIRT9/2D支持を満たす配置がzero一つだけであることを要求する。全支持の元位置・投影位置で既HUD除外を全sample ROIへ適用する。後から見えたSTONEを旧anchorの代用にしない。

数値は既定を再利用: 全73 raw有限/最良zeroが.45より大きい既fallback domain/runner差.08以上、blur-zero有限/.45以下/他72すべてより小、world support300以上/各region100以上/20×bad≤support、signed-axis support300以上/各region100以上/4×bad≤support、signed-axisの他72に既15pt lead（worldは既95%のsupport条件）。既存のMOVED/静止/092GOLD等の関数本体・閾値・期待を変更しない。

private Nav helperをControllerのupdate/publish/beginの同じstationary資格で呼ぶ。旧motion呼出が成功してMOTION_UNKNOWNであり、CLEARのstationary_wait_sceneを通った場合だけ補助する。MOVED/TWEEN/UNEXPECTED・decode失敗・actual GOLDの既経路を上書きしない。確実未送信・旧ID無効・同prefix/元world/最新完全判断・取消/UNKNOWN禁止・元2拍/parent/各期限を全て保持し、zeroをMOVEDや実入力ACKへ読み替えない。新配置の偽陽性リスクは実装前の独立設計確認と、raw/blur/各競合・8DIRT/共線/複数配置・STONE喪失/新STONE代用・near/HUD/保護・期限等の拒否単体で確認する。実機改善・未知精度は未確認のまま次の一連へ渡す。

実装前の独立設計確認では、この全ての積条件とzero専用/確実未送信の限定を条件にP0/P1なし。追加拒否ケースは既知Motionの上書き禁止、blur同率/優越・非有限競合、HUD全ROIと元/投影DIRT同一性を含める。コード差分は凍結後に同じ独立担当が確認する。

## 対象だけの判定への変更

全商品を登録する案はユーザーの最新指示で撤回した。新商品ID11〜13・feature追加は配布しない。[対象だけの判定計画](test095-target-only.md)に従い、主画像の有限商品帯を全探索するmode2を追加する。Runtime/Wireも変わるため、同一bytesだった旧callback結果だけでは済ませず、変更境界の新しいMac試験を行う。
