# TEST125: upper の観測継続と弱い探索位置

2026-11-27（日本時間）。[要件](../requirements/necrogold.md) SHOP-02/GOODS-01/02と[native契約](../contracts/native-control.md)を維持する。独立レビュー済み短計画 `892081e6…` に対応する。対象はTEST124の `upper_result` によるUNKNOWN採用であり、対象検出・陰性証明・予算・入力権限の変更は含めない。

## 原因と保存する成功

上部扉からの実H1を通常Motionで確認した後、通常商品判定は期限内にUNKNOWNを返していた。商品2個と未観測域が残る画像の弱い探索最大位置がHUDの境界を跨ぎ、既存の `upper_slot` がその位置を不正な商品画像枠として拒否した。最大値は指輪そのものの検出位置ではない。元ITEM anchor、候補なし、word枠は合格しており、周辺画像の最大位置が変わった時に観測継続を失っていた。

既upper ownerはhold単独から断定しない。原Pが通常source+FRESHを超えることと、その増額がV2 admissionだけで可能な閉じた実装、実開扉・H1・prefixの整合を別々に確認した。未出力の旧worker結果・private token・後続画像の条件は再現したものとして扱わない。

同campaignの先行runは通常policy19の全商品NEG、独立C証明、checkpoint採用、ポーズ、durable、実RS、変化した新floor、次childまで確認できた。この成功と、見えていない商品をUNKNOWNのまま保持する経路を保存する。

## 最小変更

- 既存 `cycle_box`、`upper_slot`、NEG/C証明、Ring/kernel、header/POD/ABI、Runtime、定数、元P/holdと入力予算は変更しない。HUD座標の例外追加、枠のclipping、UNKNOWNのNEG化は行わない。
- 純粋な `cycle_observation_probe125` を追加する。対象/候補・強word・非有限・不整合・異なるkind・残存ID/証明field・画像外・元探索範囲外を拒否する。
- 追加資格はinexact flag0、有限 `icon_score == icon_upper_bound < .80` に限る。canonical iconは32x28/33x28/34x29、元probeと同じ `x=cx-width/2±8`、`y=sy+24..57` の画像内poseだけを許す。弱い最大位置はこの範囲内ならHUDを跨げる。wordは84x11、元探索範囲と既存non-HUD枠を維持し、wordなしは零fieldを必要とする。
- `upper_result` のpartialで旧strict判定を先に保持し、不合格時だけ限定adapterを使う。既に合格していたexact1等を新たに厳格化しない。
- adapterは既active/validのpostunit upper、同owner/level/job/capture/prefix、元P/hold、現在PARTIAL/full_seen0、通常OK/UNKNOWN/incomplete/safe、row0/partialあり・候補なしを必要とする。元anchorまたは既124の有限potential、全ITEM/保護/旧GOLD、origin/次FLOORの検査を保持する。これは新しいMOVE/NEG/RS権限を作らない。
- 採用後も独立current、通常zero、新ticket、begin再検証、ACK後の実変位、取消、期限、UNKNOWN入力無再送は既存処理のままとする。他のPARTIAL ownerへの適用は別の実根拠を要する。

## Redと検証範囲

公開fixture `tests/test_native_upper_observation125.py` はpublic fit→開扉→V2→通常Motion H1→7potential→safe worker→遠方palette変化による新jobを獲得する。Sceneとtyped workerは宣言したcontrol componentであり、private flagを注入しない。旧124で、元P/hold/world/prefix/実H1/入力countsを先にassertしたうえでOBSERVE_MORE期待に対するHELDのassertion Redを確認した。

追加の公開procedural RGBAから通常Ringが返す弱いHUD最大位置を、返却fieldを一切変更せず同じpublic C lifecycleへ渡す。こちらも旧124でassertion Red、新実装でGreenを確認した。実ゲームやPerception全体の再生とは区別する。

原PNGの通常producerを固定した宣言diagnostic clockで実行したpacketは、変更前後で全bytesを照合する。これは過去Runtimeのmemory packetや時刻そのもののdumpではない。原記録のslot/box/count/check/bound照合と、実worker/adopt/D/P、成功RSの履歴は別に保持する。原画像・Scene dump・全packet・生記録はGit外とする。

新試験では有限値/閾値、canonical形状/範囲、word、候補/対象、余計なsemantic field、complete/NEG、job/capture/prefix、cancel/late、同job再利用、旧strict exact1、独立current→H2→DOWNの通常unitを確認する。関連はupper124、snapshot118、material122を選び、既assertを維持する。成功policy19の通常全packetと独立C証明も保持する。

## 未確認と期限

原H1後の旧worker採用時刻、実C return、未出力の後続画像、将来のframe/model/latencyは不明のまま残る。元periodを用いた条件付き予測から、全商品到達が必ず元P内に収まるとは主張しない。実変位は元visual期限内に必要であり、期限内にbind済みのFULL workerだけが既存の独立Dで完了できる。元Pの延長や新しいdrain例外は本計画に含めない。次の実機で全商品到達・対象保持・実RSと次周回を評価する。
