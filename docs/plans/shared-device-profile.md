# 同一IPAでの11/8実機検証

2026-11-16（日本時間）。[FRAME-03](../requirements/necrogold.md)の最新指示を正本とする。完成版は同一IPA・同じ探索/判断/商品確認/Controller/Navigation。実端末から固定したgeometry/input profileだけを切替える。8専用capture-onlyは原画観測の一時補助で、製品の実機成功に数えない。

今回の最小実装は未統合のpure config。[型](../../patches/loopctrl/device_geometry/NG2DeviceGeometryProfile.h)と定数、[試験](../../tests/test_native_device_geometry_profile.py)だけを追加する。旧native資産/manifest/通常workflowを変更しない。旧applierの厳密inventoryを保つため、候補を旧ngg2 assets外に置く。

- 11はlegacy decode/dispatchをそのまま通し、414×896と全7操作座標を保存。新しい型番必須条件を足さない。
- 8は実観測iPhone10,1＋375×667だけを選ぶ。既知8＋11寸法は混在として拒否。選択元はtrusted local情報で、RPC paramsから切替えない。
- 8候補は同Cへ渡す896×414への写像、実FOV/HUD/UI guard、実CGPointを別々に保持する。C Command ABI/int32座標を変えず、8の半pointはdispatch前のDoubleへ解決する。
- profileの選択やmeasured point lookupは入力権限ではない。RAW/四方向native変位/UI guard/motion/menuのgapと旧owner/prefix/世代/期限/取消/UNKNOWN無再送を全て維持する。

unknown375を誤って8へ選ぶassert Red→strict selector、既知8の混在拒否、11全値、半pointと未解消gap、新HubのUP/RIGHT・旧4回QRからのmeasured候補をfocused fixtureで確認した。新5件＋既G1/raster25件成功、旧22source/asset/manifest hash不変。独立レビューの型番条件の解釈を明示し残P0/P1なし。実Runtime/通常IPAへの統合は未実施、8のnative入力資格はない。

追加の候補dataはDungeon PauseのContinue実点（Hubの別位置とは区別）と、footer字形を維持したbody/実端guardの別写像。guardは観測した実画素をコピーし、黒色を仮定して塗らない。実resamplerの非zero tapが全て観測範囲内かを検査する。固定G1 3枚は同じ公開CでFLOOR/beatを確認したが、原JPEG・未知精度・入力資格ではない。gap31と11 legacyを維持する。

次は実RAWの向き/寸法/位相/全UI guardを確認し、Runtimeのrunへimmutable deviceGeometryを束縛→11は既decoder/実command点のpass-through→8の別normalizer→同C/判断へ接続する。未観測FOVを床/商品陰性/移動証明にしない。画像はGit外に保持し、既知校正を未知評価へ流用しない。

各独立ゲーム実機試験は必ずゲーム終了・独立NotRunningから。起動後は間隔つき複数タップでホームへ進めてよく、到達後は連打を止め、階段との相対位置を確認して左1歩・下2歩へ。商店到達・全商品確認・次周回を主指標とし、途中の起動/リスタート回数を完成に置換しない。11への導入・物理受入と旧資料移送は未実施/未解決。

## 通常Runtime統合と100周自走へのincrement

1. **概要。** 計測補助を終え、両端末を含む通常IPAで同じ既native判定・制御・対象評価・周回を動かす。8専用の別リセマラ実装やCloudごとの手操作を完成形にしない。
2. **背景。** 8の実FOV・UI位置・半point入力と11のgeometryが異なる。旧canonicalへ単純伸縮するとUI/未観測セルを誤る。原画像の出典/向きと実tap支持を先に固定し、既11経路へ影響を広げない。
3. **設計。** trusted local model/native panelから選んだimmutable deviceGeometryをrunに束縛。11は旧decode/実command点をそのまま使用。8は別normalizerで同canonicalへ写像し、FOV/HUD/遮蔽/必要支持が欠けるセルをUNKNOWNにする。C ABI/探索/対象判定/期限は共通。入力点はbegin前に解決し、資格不足はbegin前に拒否。begin後の1送信・ACK/UNKNOWN・owner/世代/取消を維持する。新規開始driverは旧run保存/回収を壊さず、停止確認からホーム・LDD・1-1へ進む。
4. **影響範囲。** 新profile/normalizer/startup module、通常Runtimeの限定結線、専用overlay/build同一性、既周回入口と関連試験。原capture-onlyと通常producerを同時稼働させない。旧保護assetは旧sealのまま再適用し、新差分を別sealで固定する。
5. **新規試験。** 型番/寸法混在・半point・legacy任意command不変・8資格不足でbegin/synth0。実画素guard/端支持/遮蔽・未知セル・商品coverage/motionの誤資格を拒否。startupのNotRunning未確認/未知画面/結果不明では進めない。候補を再開/リスタートで捨てず、旧回復/回収を保持する。機能ごとに意味assertion Redを先行する。
6. **実装順。** 原JPEG確認と並行してpre-begin/profile・normalizer・startup・buildを分担。関連host/実Mac compile→検証済み通常IPA→8実機の短いrun→原因限定修正を反復し、既campaignへ接続する。校正runを未知評価に混ぜない。
7. **コミット前と実機検証。** 変更部/関連回帰と独立差分レビュー、実compiler/IPA/全sourceの照合。100周以上ではnative run数と実floor数、開幕見送り・商店到達・全商品確認・対象/候補・未判定・障害を分けて記録する。最終候補で未知実機評価を行い、候補誤廃棄0、未知を陰性へ変換しない。速度/耐久の既要件は別途保持し、実機商品到達を主指標とする。
8. **範囲外/未確認。** 11の既geometry/閾値変更、旧私有資料の移送、世界全探索、自動購入、資格を根拠なく開く変更。8の100周実績だけで11物理受入を宣言しない。100周自走品質へ達した後、利用者に最後の実機確認を依頼する。

最新の実機最優先指示により、次の版は明示した8専用の実験許可で有限native runを先行する。trusted localの既知8と実測7点だけを許可し、qualification gap31・本番未受入を保持する。共通Controllerのowner/前面/lock/予約/prefix/UNKNOWN/元予算/購入禁止は変更しない。11は実験許可0で旧経路を通す。8の実world画素とUI判定画素を分離し、HUD・未観測範囲を商品陰性やmotion支持に使わない。まず通常版へ復帰してG1実入力を校正し、実験版で1有限run→実結果に絞った修正を反復する。実験許可を最終品質・100周受入の代用にしない。
