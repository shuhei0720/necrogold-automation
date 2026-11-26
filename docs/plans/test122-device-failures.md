# TEST122: TEST121実機4件の停止を原因ごとに修正する

2026-11-26（日本時間）。基準は出荷TEST121/build270、CODE `457478627d91136c3ff482f08b9a65314671b41e`、保存HEAD `d78159a`。実機を主にし、既成功・固定期限・入力権限を保持して原因に絞る。[修正表](../fix-records.md)・[開発フロー](../development-flow.md)・[native契約](../contracts/native-control.md)。GitHubへの保存、標準Actions、新IPA/完全sourceの固定Release配布の既承認は継続する。

## 原本と今回の実機結果

8ZIP/4root/4campaign・96PNG/111記録/223memberを全照合した。CRC/SHA、安全な一意path、全896×414 PNG decode/RGBA hash、metadata/prefix/記録鎖/escrow/実順、内包lastZIPの全bytes、terminal/drain/input0/回収completedを確認し、提出不足はない。7a9/source233だけは原記録どおりinflight/stable=falseで、安定画像へ変更しない。原本/PNG/report/Scene/個人情報はGit外。未出力job1 packet・private mode/counter/historyは補わない。

実順は開始時刻と同Runtime uptimeの非重複から fbbd→de9f→ca23→7a9d。添付順ではない。全root/index0/initial_restart=true。実初回RS4/4、実歩行4/4（6/5/5/7歩）、開扉3/4、全商品可視2/4。その2件の商品後RSは0/2で、次childも0。途中の正常UNKNOWN採用3件とPAUSE ACK/耐久保存を確認し、後のcycle_failureによるstatus上書きを未採用と混同しない。

| 実順 | 原本で確認した原因 | 変更する境界 |
| --- | --- | --- |
| 1/fbbd | UP11が実begin/既知ACK後、固定134→保存140..153の通常Motionが8回UNKNOWN。153は唯一singleton/側方露出と強いdependency画素支持があるが、旧world支持数と全旧STONE保持条件が適用外 | [限定したunit証明](test122-singleton-dependency-motion.md)。元visual内の強い独立証拠だけを追加し、既過去scheduleを復活させない |
| 2/de9f | source124/job2は正常UNKNOWN/PRICE64を元Dの56.067ms前に採用。3商品/全halo/下3床/merchant/両capは正だが、中央の低い価格をsingle policy7が認めない | [価格に依存しない完全可視証明](test122-price-independent-goods.md)。全商品を正に観測した限定条件で独立Ring/C検査。全商品登録や名前OCRを追加しない |
| 3/ca23 | 開扉後PARTIALは正しくUNKNOWN。V2/同商品/床/直接静止零でも、歩行外4材質差を全230tile一致guardが拒否し下行を開始しない | [V2静止観測の材質関係](test122-upper-material-observation.md)。現在の歩行cross/商品/保護/金壁を保持し、旧完全一致を先に残す |
| 4/7a9d | 原234はcap可視89.28%でUNKNOWNが正しい。235/236は既出荷121/旧120とも正常完全NEG/Ring/C証明1だが、halo1セルUNKNOWN→DIRTで新DATAを受け入れない | [FULL haloのDATA-only資格](test122-full-halo-data.md)。旧MOVE票を救わず、新しいimmutable sourceの通常再判定へ渡す |

全96原画像の通常Perception Scene bytesと、各原因の旧119/120/121の関連結果は同じ。既121対策の削除回帰を示す証拠はないが、同じ症状の継続であり旧合格を実機改善扱いしない。同原因の通算再発数は未集計のまま残す。返却spoolはCODE/IPA/build/capの識別子を出しておらず、ZIP単独でインストールbinaryの同一性を証明できない。

## 実装・検証・配布

各短計画で原画像/通常producer/元時刻/拒否guardを固定し、出荷121の完全sourceコピーに対する意味あるassertion Red→最小Green→直接関連を行う。未出力private状態や未来の実機応答は、公開C lifecycleの宣言した手続きモデルと区別する。Cのupper/currentDATAと陰性witnessは関数hunkで分担し、whole-file上書きをしない。

旧実RS成功5packet、TEST121のpolicy19/20別形7case、今回235/236の既完全陰性と234のUNKNOWNを保持する。候補は常に優先し、未観測/商品欠け/不明をNEGにしない。一般閾値・P/W/D・source150ms/worker100ms・input10ms・owner/prefix/取消・UNKNOWN無再送・共有DATA2・drainを維持する。新資格を実際に使う境界だけ関連結合を選び、無関係な全Runtime故障/合成worldを配布条件に増やさない。

TEST122 clientは121を継承し、識別/capability/namespaceだけを追加する。旧116default、初回RSと子の重複bootstrapなし、同root回収/連続周回を保持。独立差分レビュー後、新IPAを実ビルドしseal/来歴/実compiler/全9MachO/完全sourceを照合する。固定3assetの匿名全取得まで確認する。

配布時は今回の4修正、確認済み範囲と未確認を具体的に説明する。通常1-1ポーズから初回RS→候補/通路→開扉→上部入口は内壁沿いに下行→全商品確認→対象なしの通常判定/保存/実RS→次周回を依頼し、全run/campaign ZIPで確認する。host合格を実機の商品到達・毎拍/速度・未知配置精度の受入へ置き換えない。
