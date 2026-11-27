# TEST125: 実unit後の遠方paletteを元jobの静止証拠にする

2026-11-27（日本時間）。[観測結果計画](test125-observation-result.md) の追加前段。既存の製品増分 `NG2Controller.c d3b589d5…` と各担当のfixtureを固定してから追加する。予算・期限・通常Motion・kernel/ABI/Runtimeは変更しない。

## 根拠と不明点

原画像のH1後129から130/131への変化は、保護外の遠方3セルのDIRT→FLOOR、FLOOR→DIRT、DIRT→STONEだけであり、ITEM・保護・旧GOLD・goods・origin・次LEFTは同じ。通常Motionは直接BLOCKED(0,0)である。`upper_static_footprint` はtile差分を不合格にし、`upper_material_footprint122` は入力済みという条件だけでpostunitを除外するため、新しいDATA jobへrebindする。このrebindで、直前実unitと元sourceを要する既postunit slot資格も失われる。

旧workerの開始/採用・実C return・未出力の後続画像は不明であり、130で必ず入力できたとは断定しない。原periodによる同phase仮定では、130のanalysis終了は次H2のnot-beforeより約12.44ms前、131は約31.71ms後である。analysis終了をC returnとして扱わない。早い現在画像を元jobで検査できることと、将来の実機で全行程が期限内に完了することを分ける。

## 追加する静止関係

- 対象は既active/validのV2、元level/job/capture/prefix/P/holdを保持し、既reboundがない、実unit後のstage1/2/3に限る。UNKNOWN worker中・FULL・候補・取消・terminalへ資格を作らない。
- cycle.prefixを持つ完了event自身のknown ACKと通常MOVED、方向/実dxdy、observed captureと元job source、anchorの対応を必要とする。新しいMOVEの予約がlatest eventになっても、そのpending eventを実unitと解釈しない。元unit eventと元sourceを保持した同じ静止関係をbeginでも再検証する。
- 原ITEM・保護・GOLD・goodsと既upper world、origin/次FLOORを保持する。変化セルは両方のstepping cross外・保護外で、旧/新とも完全に観測済みのFLOOR/DIRT/STONEだけに限る。UNKNOWNを含む変更、商品/壁/保護の変更は従来DATAまたは拒否へ回す。
- この関係は `upper_static_footprint` の限定追加である。通常Motionによる直接zero、独立currentの時刻/prefix/owner、model、新ticket、begin、実unit確認は既存のまま必要とする。元source/resultを最新画像で置き換えず、新job・DATA refund・入力/歩数/期限の追加を行わない。
- 旧pre-H1 material関係、既存の橋渡し、弱probe計画のstrict-first結果資格は維持する。弱probe fixtureのUNKNOWN→STONEは新関係に含まれず、元の新jobを得る全assertを保持する。

## Red・Green・回帰

独立計画レビュー後、追加公開fixtureでpublic fit→開扉→V2→通常H1→7potential→通常safe workerを獲得する。現在画像は遠方の既知F/D/Sだけを変更し、元P/hold/world/入力counts・元unit/source/jobを先にassertして、元job保持と独立current資格の期待を固定版d3bでassertion Redにする。私的flagを注入しない。

rootの製品GO後だけ最小実装を行う。元job/source/workerを保持した現在画像から、同じ元P内のH2予約・begin再検証・ACKと通常実unitを確認する。UNKNOWN・近傍/cross・ITEM/GOLD/保護・prefix・所有・候補/強word・started/UNKNOWN input・期限・二度目の権限取得を拒否する。旧弱probe fixtureと既upper124/snapshot118/material122のassertは変更しない。

原PNG-derivedのnormal Scene/Motionを同じ静止predicateへ通す私的診断と、公開control lifecycleを分けて保持する。通常producerの固定diagnostic clock packet、歴史的Runtime時刻、公開fixture時計を混同しない。将来のperiod/model/latencyは作らず、条件付き予測や公開component成功を実機完了と呼ばない。
