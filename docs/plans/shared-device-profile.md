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
