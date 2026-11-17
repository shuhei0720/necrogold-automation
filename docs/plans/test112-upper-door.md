# TEST112: 上側入口から下の商品までの有限観測

2026-11-17（日本時間）。独立設計レビュー済み、公開Cの新規13試験は合格。実装差分レビュー・選択Runtime結合・実機改善の確認は別に行う。[要件](../requirements/necrogold.md)のSHOP-02/GOODS-01/02、[制御契約](../contracts/native-control.md)、[対象判定](../contracts/target-assessment.md)に従う。FR-097-CLIPPED-PARTIAL、FR-104-PARTIAL-REFRESH、FR-105-PROTECTED-WALL、FR-107、FR-108/109のframing、FR-111を照合する。旧単体合格をこの配置の改善完了と扱わない。

## 1. 事象と原因

TEST111の時刻順4実行の最後は、開扉後に商品が下へ隠れたまま停止した。原147はFLOOR/PARTIAL、下側同一行の連続7ITEM投影と正確な十字保護、観測金壁9点。正常Ringは約7.56msでUNKNOWN/INCOMPLETE、row/partialとも0、partial_safe_no_positive=0。直前LEFT11はDOOR_OPENEDで、入店MOVEDではない。Navは既にLEFTの観測済み入口床を選べる。

旧空framingはUP/上端専用。旧lower観測は実MOVED入店、非空slot、現在のDOWN床を必要とし、今回は全て条件外。そのため正常な空判定後、即HELD→PAUSEになった。空を安全・対象なしへ変えず、別の有限入店観測を設ける。

## 2. 新しい限定権限

通常の同source workerがOK/UNKNOWN/INCOMPLETEで、対象/候補/強い手掛かりがなく、PARTIALかつ未FULL・row/partial0・選択-1・partial_safe_no_positive=0であること。同prefixの直前ACKが同方向の横開扉であり、lead確認/実移動履歴あり、現在Navの完全判断が同方向の入口FLOORであること。入力中、旧worker未終了、既観測episode、再開/PAUSE/storage/terminalは拒否する。

局所形は横方向d=±1について、入口(d,0)の上下GOLD、反対側(7d,-2..1)のGOLD柱、(4d..7d,-2)のGOLD屋根、下側row3・d..7dの連続7ITEM投影と正確な十字保護を要求する。原点/次床は正の非保護FLOOR。一般Nav、旧UP/lower、任意の金壁・空結果へ広げない。左右鏡像は各々の実HUD条件で検査し、一律に中央域へ収まるとは仮定しない。

## 3. 固定する世界と上限

元level、開扉event/source/prefix/world位置、最初の7ITEM投影集合、元GOLD支持、親期限、hold開始、同期期限、入力予算を固定する。実MOVEDだけで累積offsetを更新し、各SceneのITEMと保護を元worldへ写す。現在ITEMは元7セルの部分集合、正確な現在十字保護は元投影域の部分集合でなければ移動資格を失う。元GOLD支持の固定world位置を維持する。

横の入店は最大2入力、その後のDOWNは最大2入力、合計最大4の「開始した入力」。失敗/UNKNOWNを成功扱いして回数を戻さない。次手は各画像で確認し、H,H,D,Dを一括予約しない。元16入力・walk45秒・session180秒・未送信回復回数・元親期限は増やさない。全商品が早く正常判定できればそこで終了する。

## 4. 各一手と商品行の結合

原147で正に確認できる次手は入口へのLEFTだけ。原点のDOWNはDIRT、入口直下はGOLD、2歩先LEFTもその時点ではDIRTであり、許可を作らない。ACK後の通常strict MOVEDを確認し、新しい不変sourceで通常Ringを実行する。内側への次床が新しく非保護FLOORとして見えるまで入力しない。内側へ入った後、金壁の内側に沿ってDOWNを一手ずつ確認する。次の床/保護・元開扉world位置・元GOLDを毎回検査する。

通常rowの3連続中心、単独partialの中心は、実MOVED offsetを戻したとき元の同一7投影行へ一意に対応する必要がある。half-cell tieや別の行/店へ替えない。完全5セル探索の外側partialは、同じcoherent rowのleft−36/left+108に限る。後の完全陰性も既存C証明に加えて元の物理商品行との対応が必要。別の正常な3商品陰性でこの観測を終了・再開してはならない。領域外の新sourceでも実対象/候補は保持し、移動資格だけを不可逆に失効させる。

## 5. 観測範囲と陽性優先

最初から、隠れた7投影の全潜在ROIがHUD外にあることは要求しない。原147の既helper域[118,229,490,376]は旧中央315px域外で、最初のLEFTにより一部が心臓HUDへ重なり得る。旧「全潜在画素保存」の証明を流用しない。

元のworld投影から有限なanchor/ROI域を求め、各通常row/slotが同じ範囲にあることを検査する。LEFT例で3連続中心の先頭は196..340。量子化の±18pxを含め、rowの名前union left−112..left+184とslotのcx±60を覆う有限x域は66..542。yは元ITEM箱とsy=267±18のslot sy−32..sy+115を合わせ217..400。これは行の同一性を制限する域で、全画素を観測済みとする証明ではない。

途中のnormal row/slotが非空になっても、その全潜在unionをHUD外に要求しない。2横移動後にもslot sy+115は382付近に達し、ここで拒否すると必要なDOWNを再び禁止してしまう。各poseで通常結果が実際に観測した非空icon/name等のboxには`cycle_box`と同じ7HUD/画面境界を適用するが、未観測の潜在域は固定worldへ結合したUNKNOWNのまま原画を保存する。最終陰性は通常producer/C証明自身の全商品帯・価格・端・探索被覆と非HUD条件を必要とする。左右を旧x143..663条件だけで一括評価せず、潜在域全体が最終中央域へ収まった計算だけでも完了にしない。

各sourceの実rawと正常worker結果を保持する。対象/候補、icon exact/upper-bound≥.80、既存の強い名称vetoは入力を止め、遅いcallbackでも捨てない。空結果から全rawの対象不在を主張せず、partial_safe_no_positiveやcoverageを偽造しない。最後の単一sourceの全3商品・価格・端の被覆と既存の独立C証明だけが陰性/保存/リスタートを認める。複数partialを合成して陰性にしない。

## 6. 拍モデルと元期限内の可能性

`cycle_latch`/`cycle_bind`は`clear_slots`で古い票を撤回するが、BeatModel/raw sample列を消さない。新経路も毎手`clear_model`して2秒fitを始めない。独立したcurrent-prefix strict零画像を受け、通常`add_sample`/track（失格時は通常fit）だけで最新HUDを採用し、model_capture_id≥proof IDと通常50ms準備を必要とする。各MOVED後も同様に最新画像でtrackする。失効したモデルを有効扱いしたり、失効前の票を復活させない。

原147の判定採用時から親期限まで約2.5767秒。保存された12枚/約2.2127秒のHUDを通常native fitへ渡した校正は周期約522.412msとなり、最初の将来targetから4個目までを置いた場合でも親期限まで約701ms残る。これは保存sampleの計算で、未保存の実controller modelや未来4移動の実機成功ではない。

予約前ごとに実際の最新model/将来targetと残り段数を使う。`target+(必要な残入力−1)*currentPeriod`に既存の最短視覚確認80ms＋source150msの余地もない場合は、新入力しない。この検査は必要な時間の見積もりであり、将来FLOORやACK遅延の保証ではない。位相、準備、床、独立零、予算の不足は元期限内で待機し、回復できなければ保持/PAUSEへ。元親期限を更新して通さない。

親期限は観測MOVE権限を制限する。データworker自身のsource150ms/worker100msは従来どおり別に検査し、親が切れても正常な対象/候補を失わない。入力再開は0。新sourceを作るためだけにworker期限を延長しない。元の親期限後に独立した完全陰性が成立する場合も、単一sourceの正常証明と通常のdurable/UI手順が必要。

## 7. 原画・診断・境界

公開ABI/クライアントschemaを変えず、private episodeで元world/親期限を保存する。既Cycleのcurrent/queued source leaseを使う。最初の商品原画、各worker source、入力source/実MOVED画像、最終画像を既pin24の圧力下でも保持できることを選択Runtime結合で検査する。実sourceを失う場合だけ有界なlease補正を別途行い、保持できると読取だけで断定しない。

実source/current比較、最初の停止理由、段階、親期限を診断へ残す。初回比較失格・非零・別prefix・古結果・取消・前面/lock/owner失格・送信済UNKNOWNは移動権限を戻さない。世界対応を失った新sourceのDATA-only正常判定は候補を保存できるが、別商品行の陰性を再開根拠にしない。

## 8. Red/Greenと実機確認

公開Cで「実開扉→空の下側PARTIAL→別のstrict零→観測入口一歩」のassertion Redを先に固定する。次に、後続を手続き的な画像/Sceneとして正常worker/実MOVEDを各手へつなぎ、全商品可視/同じ物理行の完全陰性→durable PAUSE/intent→RESTART→次床を確認する。原147以後の床は未収録なので、後続合成を実機再現と呼ばない。

新試験は以下を分ける。公開Cでは新規13試験が合格し、最後の選択Runtime結合は別途確認する。

- 空PARTIALから入口へ進む正経路と鏡像。次床がDIRT/UNKNOWN/保護なら入力0。
- 各sourceの新worker、独立零、fresh HUD、通常モデル追跡。毎手2秒fitを始めない。
- 元7投影の縮退と正確な保護。領域外ITEM/slot、別の正常陰性行、元GOLD消失を拒否。
- 元親/hold/sync・150/100ms・4開始入力の固定。予算不足、位相失効、遅延commit、5手目を拒否。
- 初回/途中/遅い対象候補の保持、正常worker異常、旧job/prefix/取消を拒否。
- 送信済UNKNOWNを加点/再送しない。最終UNKNOWNで一般Navへ落として戻らない。
- 最後の正常単一source完全陰性だけが保存・実リスタートへ進む。
- 新しい複数手の実C/Swift callback、元raw hash/PNG/manifest、pin24圧力と取消を選択結合で確認。

旧UP空framing、FULL観測、lower104、対象優先/期限/UNKNOWN無再送を直接回帰として維持する。旧Runtime29故障集合を自動で再実行しない。独立設計/差分レビュー、現在sourceのcompiler/seal/IPA/完全source照合後、通常1-1ポーズから次の実機で全3商品への到達・判定・対象外の再開/次周回を確認する。

直接回帰62試験は61合格、1件はTEST111原本Cでも失敗する旧TEST102の期限後TARGET破棄assertだった。TEST111で既に認めた「期限後の陽性をCANDIDATEとしてだけ保持」に合わせ、当該1メソッドのexpired_worker分岐だけ更新し、そのメソッドの全4分岐を再確認した。TARGET採用は認めず、outcome/candidate以外のCycle全byte、入力/移動/再開回数、入力状態は不変を要求する。制御本体はこのために変更しない。

追加の第14試験では、正常Perceptionの合成原画に合わせ、横2歩後もPARTIALの7投影を維持し、下1歩目でFULLの3商品へ縮退する経路を固定Cで確認した。下2歩目の単一source正常完全陰性まで合格。未来の実機画像や実Runtime callbackの証明には数えない。
