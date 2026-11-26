# TEST122: 側方商店露出時の既知ACK後unitを証明する

2026-11-26（日本時間）。基準HEAD `d78159a`、出荷TEST121/build270・CODE `457478627d91136c3ff482f08b9a65314671b41e`、Nav `ebba4541`。[要件](../requirements/necrogold.md)・[native契約](../contracts/native-control.md)・[開発フロー](../development-flow.md)・[修正表](../fix-records.md)に従う。**短計画の作成だけを承認済み。独立設計レビューとroot GOまでは製品・正式試験・Git操作・CIを変更しない。**

## 原本の原因と期限

実順1の`fbbd2b1b`は初回RS後6実MOVED、次のUP11/source134が実begin・既知ACKとなった後、140/141/143/145/146/148/151/153の通常Motionが全てUNKNOWNで8評価を消費し、movement10で停止した。閉扉の未開始票を撤回した前回121とは別状態である。原134を固定し、画像間の零の連鎖や未保存のprivate状態は使わない。

原153はraw winner=(0,+9)・score `.487162370484`、runner=(0,+11)・score `.914186540960`で、全73候補が有限・既domain2である。FR096の唯一singleton/側方入口幾何は成立するが、既`revealed_singleton_motion`はworld blur支持194<300・上帯81<100で拒否する。既`revealed_domain2_dependency_motion`は全旧STONE保持の`unique_visible_terrain_translation`を拒否する。旧STONE(7,3)は投影先(7,4)でDIRT、旧(7,4)は画面外UNKNOWNとなる一方、他の旧STONE4個と非共線DIRT9以上は投影を支持する。

旧119/120/出荷121は同じ96原画像のScene全bytes、当該8pairの通常Motionが同一。motion sectionの全bytesも同一（SHA `d4e47a313ceb1bbe6cb7ecceb0ffcada6e6a338bedbbf69b3f0633462af698be`）。FR079/081/096/108/113の側方露出変位系列に残る、地形と画素支持の組合せであり、121の対策削除による回帰の証拠はない。

| 原時刻・境界 | ns | 判定 |
| --- | ---: | --- |
| UP11既知ACK / earliest | 23716134230666 | target+80msより後で、earliestはACK |
| 原153 capture start / end | 23716687392291 / 23716697831166 | ACK後・元visual期限内 |
| 原153 analysis end | 23716720009583 | 元visualまで2044.080167ms |
| 後続cleanup PAUSE12/source153のactual tick | 23716730984791 | 元visualまで2033.104959ms |
| 元input D / schedule D | 23715867928320 / 23716387167534 | 両方既過去。旧送信や次拍を復活させない |
| 元motion visual W/P | 23718764089750 | source134開始+3秒から凍結 |

153の実`observeStart`自体は未保存である。正常Runtimeのanalysis→同frame observe→後続tickと、UI `not_before=reserve(now)`のsource153同一性から、実commitはanalysis end以上・cleanup tick以下と因果的に挟める。`stop_detail.at_ns`はcapture endで、実commitに読み替えない。元実行はattempts8/observed153まで採用しており、最後の比較枠自体は期限切れで拒否されていない。153開始は初回140開始から548.448166ms、直前151開始から77.384500ms。凍結command periodは未シリアライズで、最終modelの518.812009msを代入して完全再生とはしない。

したがって新しい数値証拠を原8枠目の元visual内で採用できる根拠がある。ただしschedule Dは既過去なので、unit信用後の通常recovery・新fit・将来slotが必要であり、次歩・開扉・商品到達の成功は未収録である。

私的根拠はGit外`/workspace/analysis-evidence/test122-movement/motion-probe/`の`cause-receipt.json`（SHA `9ed00ce20f1f5a3a92f5638f60262cb1e12ea489532bb35faa98965cdc2ba901`）、`numeric.json`（SHA `1a28c201b4ebdde1792e6953c62f5ca3b46623a99f09020fe080666783d5e1a2`）、`trace.json`（SHA `f69bfc60c48b7d9f2e47f4c6cc814c54ec0256a589ad3ce53b94fd6e92bf2663`）、`timing-receipt.json`（SHA `23e122801897605eb2e869794b5abf8c0f68aee9c0917c7885e334a36ad06650`）へ結ぶ。原PNG/Scene/logは公開しない。

## 追加する限定証明

既通常段を全て先に維持し、その後のUNKNOWNにだけ別のunit証明を加える。一般Motion閾値・旧全STONE証明・Perception・Controller/Runtimeの入力権限は変えない。

- 両正常FLOOR/商品UNKNOWN/実GOLD_CANDIDATE、旧GOLD1→同じ旧GOLDを含む新GOLD2、現在の側方closed bracket、旧origin/nextと現在originの正FLOOR、全ITEM/保護なしを要する。既FR096の全9幾何候補中の唯一singleton投影を使い、新商品・新地形を過去変位のanchorにしない。
- rawは既domain2そのまま（全73有限、同方向unit、元`.45/.08`条件）。遠方の旧STONE→DIRT/UNKNOWNだけを既FR096のroute近傍除外で扱う追加qualifierに閉じ、保持STONE2個以上と旧GOLD/保持STONE/旧DIRT9以上の非共線性を要する。FLOOR/GOLD/DOOR/ITEMへの矛盾、origin/次床付近の損失、別投影、HUDだけのanchorは拒否する。旧`unique_visible_terrain_translation`を一般弱化しない。
- 固定dependency maskは既全依存閉包・分離した2帯のまま。勝者支持300/95%/各帯100に加え、全72代替の実支持300以上・既15pp差を全て要求する。別の既signed-axis面も支持300/95%/各帯100と既競合guardを要する。面を合算しない。

153のdependency面は1052支持/47不一致・両帯500/552、全代替の支持min326・最小差23.460247pp。独立axis面は473支持/18不一致・両帯245/228。axis代替は全72個とも支持300未満なので差の証拠には数えず、全代替排除はdependency面が担う。axisの不足競合を無限差にせず、絶対品質を独立に要求する。この診断ANDは140..151では不成立、153だけ成立する。

## 正式Red・関連確認と返却

GO後に新`tests/test_native_singleton_dependency122.py`を作る。公開113のdomain2/108の手続き画像モデルを参照し、遠方旧STONEのDIRT/UNKNOWN化・保持STONEと非共線DIRT・同方向unitを持つ独立signatureを生成する。既全段UNKNOWN、全73の正支持と上記ANDをfixture側で確認してから、公開`ng2_motion`のMOVED/unit期待で出荷121の意味的Redを実測する。実画像・source134/153はGit外校正に留め、模擬画像を実機の完全再生/未知評価にしない。

4方向、各遠方損失と両者合成を確認する。負例は原143等の早い支持不足、非unit/TWEEN/逆方向、raw不明/別winner/差不足、二重幾何・旧GOLD損失・bracket不足、保持STONE/非共線DIRT不足、近傍STONE変化、ITEM/保護、片帯<100・支持<300・95%不足、全73中一つのdependency競合支持不足/15pp不足、axis絶対品質不足を選ぶ。証拠面ごとのguardを満たすことを先に確認し、他のguardで偶然拒否するケースを専用境界成功と数えない。

公開Controllerの通常fit→実unit→同command begin/既知ACKでearned状態を作る直接関連cutも置く。固定beforeからの7回UNKNOWN→8回目unitで一度だけcreditし、元source/command/ordinal/visual期限/全counterを保持する。capture endと実commitの元visual前/等号/後を分け、期限後unitを拒否する。元schedule Dを過ぎたunitは既recoveryへ進むことを確認し、入力再送や未来の到達を成功条件に混ぜない。原relative間隔を根拠とする手続きモデルであり、未保存phase/model/private状態を復元したとは呼ばない。

変更予定はNavの別helper/callと上記正式試験だけ。関連096/108/113の公開MotionとACK/8枠・visual期限の既Controller methodsを選び、O0/実strict O2で検証する。独立差分レビュー1回、native変更後の実IPA/source/compiler/seal同一性はroot工程へ渡す。初回RS・連続周回・対象/候補保持・未観測陰性禁止、source150ms/worker100ms、元P/D・入力10ms、UNKNOWN入力無再送を保持する。次のiPhoneで通路の停止位置通過→商店開扉/入店→全商品確認を評価し、host合格を実機到達・毎拍/速度の受入へ置き換えない。
