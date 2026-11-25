# TEST119: 松明に照らされた現在の床を正の画素で確認する

2026-11-25（日本時間）。[TEST119計画](test119-device-failures.md)。元Perception色閾値の引上げやControllerでのDIRT→FLOOR代入を行わず、別の現在画素証明を追加する。

1. **背景/目的**: efの次LEFT(-1,0)は原174でFLOOR、175〜177でDIRT。176/177の全25×25中央値は(40,24,19)で既bright-floor条件外だが、UL/LRの異なる領域と上帯は既`ng2_material_floor`の色/textureを満たす。下の観測GOLD壁の松明が左下へ重なる。旧UR/LL条件や083の外側下帯はこの領域を証明しない。
2. **確定predicate**: 旧DIRTだけ、原点以外、全25×25が画面/HUD外、full spread、39<=R<=52・45R<=100G<=68R・25R<100B<55R。現在の下3セルが全てGOLD。固定upper(-12,-12,25,12)、UL(-12,-12,12,12)、LR(0,0,13,13)の各sampleがR>=16と旧floor色/textureを満たす。UL/LRは非重複、upperはULと重なるので3独立領域とは呼ばない。
3. **明点の閉条件**: 原25×25中のwarm点はR>104、G<R、100B<55R。全warm点が4近傍で一つの成分をなし、実画素数>=36、bbox幅/高さが各6〜13、bboxは元ROI内、相対top>=0/bottom==12、2×実画素数>=bbox面積。単なる6×6bboxと36点を混同せず、別の孤立warm点は拒否。下壁の向きとUL/LRだけで、回転/別対角へ一般化しない。
4. **不変条件/範囲**: UNKNOWN/STONE/DOOR/GOLDを床へ変えない。元36px tile/896×414/alpha/stride/HUD/画像向き処理は不変。全依存GOLDと画素を現在の同画像から得る。既material/gate処理後、商品/ITEM保護投影前の別helperとし、最終ITEM/保護優先を残す。全旧色比・RingのGOLD14/黒cap・価格/候補/陰性条件は維持する。
5. **Red/反例**: 公開Perceptionと独立に生成したfloor+torch/下GOLD支持で旧DIRTの意味Red→新FLOOR。現在正のsample欠落/無texture/異色、同GOLD railのDIRT/STONE+torch、rail欠落、warm孤立/分断/浮上/極小/疎、境界/HUD/投影優先を確認する。私的14校正ケースを未知精度へ数えず、正式試験へ出典と期待を固定する。
6. **実装順/レビュー**: 私的候補と閉spec e3395c975cを固定し、独立設計/安全レビューP0/P1なし・曖昧specのP1解消を確認した。正式test先行Red→同helperの最小実装→Green/083・084等直接関連→原175/176/177の通常public PerceptionとC境界→独立差分レビューの順。
7. **影響検査**: 受領132PNGを旧/新public Perceptionで比較し、全変化セル/型を列挙。許可するのは新predicateで証明されたDIRT→FLOORのみ、ITEM/保護/別出力の不意差を調べる。成功3f/source199の通常Ring最終packetを保持する。これは今回画像の校正であり未知評価ではない。実IPAのprofile3/全source/37sealを再照合する。
8. **限界/次工程**: 現在の床証明だけで未収録178〜180や新入力/RS成功を仮定しない。既ACK166→176/177の通常unit、inclusive元visualD、一回性、元P/DATA2を保つ既entered/current DATAの限定継続は別計画で確認する。大きいDIRT待機modeや画像のみ陰性への変更は採用しない。iPhone到達率/毎拍・人超え速度は新版の実機で受け入れる。
