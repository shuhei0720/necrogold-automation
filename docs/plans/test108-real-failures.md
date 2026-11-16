# TEST108: TEST107の実機停止と候補見逃し

2026-11-17（日本時間）。基準は `c83056f`（TEST107配布時点と全tree一致）。実機ログを主に、原因に絞る修正・変更部の単体/直接関連回帰・独立レビュー・同sourceのIPA照合・次の実機の順で進める。iPhone 8/遠隔試験の開発は再開しない。

## 受領と原因

7添付は4固有runと3campaign最終runの重複。全CRC/安全path、campaign内ZIPの全bytes、manifest/record hashchain、97原PNGの復号RGBAを照合した。107記録と原本はGit外。利用者の3周と対応が未確定の追加runも解析対象に含め、数を水増ししない。

- `7186…` は開扉ACK後に入店MOVEなし。通常Ringは実記録と同じ正常UNKNOWN/INCOMPLETE・policy10/ITEM128。通常品の下側が暗闇となり、閉容器専用のUNKNOWN床許容へ入るが、正の容器identityはない。全商品が見えるという人の観察を全被覆の機械証明へ置換しない。既FULL一歩観測は「開扉後さらに横MOVEしたACK」と現在位置の上下金壁を要求し、入口手前を扱わない。
- `7c69…` は最後のLEFTが実ACK済み。原256→279で地形は一歩分移り、旧GOLD/全旧STONE/非共線DIRTの一意unit投影とraw planeは成立するが、独立textureの票数/phase条件が不足してMotion UNKNOWN、reason10となる。ACKや単なるscoreだけをMOVEDへ変換しない。
- `be6e…` は正常UNKNOWN分類後のFULL追加観測で、原236/238の地形不変/厳密零が不成立となりPROTECTED9/SCREEN17。107のPARTIAL合成とは別経路。両画像の全3ITEM/正確保護/直下3床/両端床は既offer footprintを満たすが、policy9の2看板条件に当たらず、単一看板用の旧policy7も入口が商品列より下の形に当たらない。原比較の近傍材質と記録の向きには未解明点があり、旧MOVE権限を回復する根拠にはしない。
- 追加 `f2bf…` は198→199で厳密零だが、次の観測床vantageがRIGHTからUPへ変わる。旧RIGHT票は未送信のままROUTE10/SCREEN17となる。送信済みUNKNOWNの回復とは分ける。
- `be6e…` 原70は実際の見送り判断source。通常候補mask0の後にPAUSE/RESTARTの実ACKがある。上左のsplit roofは旧095/097の別条件に当たらず、暗い口へ入らずに既床3歩で観測できる形を見送っている。旧対策の削除回帰とは確認されていない。

FR101/104/105/106/107のFULL/PARTIAL・価格床・候補・静止対策を照合し、過去単体合格を実機改善完了と扱わない。

## 変更方針と担当境界

1. 入口手前のFULL/UNKNOWNは、正の同方向開扉ACK・変位0・次の観測FLOORとその金壁bracket・正確ITEM保護・全potential ROI/no-positiveを証明し、既存の一度限りの一歩観測へ渡す。通常Ring/陰性証明の条件は変えない。Cのhistory/local/admitだけを先に修正する。
2. Motionは旧分岐/閾値を維持する。既`world_mask`の全依存を閉じた別planeで全73位相の実支持300以上/有限値・unit勝者/.45以下/.08以上の差を正に証明し、同領域のtexture300票/95%/上下100票と、既raw厳格domain・一意の旧GOLD/全STONE/非共線DIRT unit投影を同時に要求する。通常rawの支持不足による+INFと、旧textureの競合支持不足をmarginの根拠にしない。最初のraw全finite案は原で不成立だったので採用しない。支持が足りなければMOVEDとしない。
3. 上左split roofは、独立した観測壁/屋根と暗い口・内側既床を要求する候補witnessを追加する。既床だけでvantageへ進み、未知口へ入力しない。旧弱形拒否を保持する。
4. 単一看板/offset入口にも、全被覆した後の正の商品判定を用意する。新policy11は単一の完全29行faceに加え、商品列へ相対化した観測済み金壁境界とoffset入口FLOOR、既offer footprint/全B対象探索/3実価格/両endcap/余剰価格・看板0/第4Scene ITEMなしを要求する。全Bを走査する部分候補領域の数は既policy9と同じ扱いとし、画像上の未検査領域を作らない。右の閉容器の価格下端は既ordinary範囲を越えるため、既106の正の閉容器identity/実価格/v2の証明を使う。下側UNKNOWN床の許容は増やさない。Ring producer・Ringの証明検査・Cの独立Scene/数値検査を結合し、対象/候補/欠損は保持する。原画に既SHOP glyphの閾値が成立しない案は採用しない。旧paired9/closed10・旧単一blob拒否を保持する。原236/238は新11でも右endcapが黒465/625、464/625で正常UNKNOWNのまま。これを陰性化せず、もう一歩入って端を実観測する必要がある。
5. 追加runの未送信票は、新旧の完全Decisionを各1回正規chooserで照合し、同じactual GOLD・全商品/保護なし・両原点/新旧次床/新targetが既FLOOR・新しい一歩近傍不変・厳密零を要求する別refresh modeへ撤回する。旧STONE消失1セルと既DIRT/FLOOR/UNKNOWN関係を限定し、新方向の正の床露出を要求する。後続は新anchor全tile一致・独立零・完全同Decisionで、新しい将来拍だけを許可する。旧ticket/slot/phaseの権限を継承せず、既refreshの元sync/walk/session期限と1進捗1回/run8を更新しない。ACK/送信済みUNKNOWNや新方向の未知床へ広げない。
6. FULL追加観測は、MOVE未予約のstage1/2・input0だけ、元GOLD/ITEM集合/保護を保つ非保護材質の揺れと直接Motion UNKNOWN/BLOCKED零を元D内の無入力待機へ渡す。固定anchor/job/choice/prefix/一用/Dは不変。stage1へ落としmodel/slot/preparation/proofの権限を撤回し、同levelの既検証raw HUD samplesだけデータとして保持する。待機画像でsampleを足したりfitしたりしない。後の同anchor全材質/保護・直接厳密零・新fresh画像で通常fitが新model IDを作るまでMOVE0。中間pairのzeroで橋を埋めず、MOVED/TWEEN/開扉等の既知変化・非零は永久拒否。新ITEM/保護/金/候補・予約後stage3/ACKは旧拒否/保持を維持する。撮影がなくても既OBSERVE_MOREの親D検査で失効する。未収録の将来の適格frameや移動後の店内を実機成功として作らない。

共有ファイルの所有は、Cのfull history/local/admit、Cの後続state、NavのMotion、Navの候補へ関数単位で分ける。public ABI/API/cap、Runtime/Raster/Perception、既feature/canonical15/ELF/G1/R12、対象保持/購入禁止/UNKNOWN無再送、元prefix/期限/一用/累積予算を維持する。

## 検証と返却

各期待値を実装前sourceへ結びassertion Red→最小Green。意味単体・変更関数の直接関連回帰・必要なproducer/Controller受渡しだけ選び、旧assertの削除/skipや無関係な全体試験を加えない。原画像校正は既知runの条件確認であり未知精度や実機再演ではない。未収録の後続画像を作って到達成功としない。

最終sourceを一度sealし、承認したnative差分だけを確認。独立差分レビュー後、標準Mac device laneで選択単体と新IPAを作成し、実compiler/全source/IPAの実物を照合する。固定ReleaseでIPA/完全sourceを返し、通常1-1ポーズから `test_108.sh --until-target`、終了後の全照合済campaign ZIPと全run原本を依頼する。商品到達率・対象保持・次周回・毎拍/実効速度の受入は実機結果で判断する。
