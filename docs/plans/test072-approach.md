# TEST072: 商品までの停止修正と、不可視金壁の通路接近

2026-11-10（日本時間）。baseline `605f2e5c526cf2da515235550a471133750dd05d`。ユーザーが既存3停止を先に改善し、続いて開始時に金壁が見えない通路パターンへの接近を実装するよう指定。時間上限なし、品質/実機主軸を維持する。

## 1. 概要

既存の開扉→入店→全商品可視を妨げる3停止を直す。その後、新しい上/左通路パターンでは観測床だけで通路へ接近し、移動で見えた地形を再評価する。金壁が現れれば通常の商店処理、局所接近後も見えなければ既存のポーズ/リスタートへ。店全体の不在とは断定しない。部分商品/候補は保持し自動購入しない。

## 2. 背景と出典

TEST071は実行順88384bb8→2e398828→318e3f42。全48PNG/全ZIPのCRC/SHA/bytes/896×414/manifest/prefix/cursor/report一致、全回収resolved。方向入力間隔約.505〜.526秒でほぼ毎拍。

883の156→158は同LEFT/reason5/nextFLOOR/full5/金/全保護・strictBLOCKED。(-3,-1)UNKNOWN→DIRTは既存近傍外であり、本因はnext隣(-1,1)のprotected1が両SceneでGOLDだったこと。2eの94→95は同UP/reason8/FLOOR/full5/金/全保護/strictBLOCKEDだが遠方2palette変化とchain2で停止。双方元D内。

318のsource113→122/124/126/134は実DOOR→FLOOR、新金と商品が露出。位置zeroの原intensity .241〜.320/他候補INFINITYだがnormal支持167<300、旧expanded332/bad18で95%を満たさない。既知調整資料として専用detail領域を試し、下端85・上下band65で支持320〜325/bad8〜12、各band131〜135/187〜192と元95%/全73候補15ppを確認。旧2領域の合格へ読み替えない。

ユーザーの赤丸画像12枚は初期約5×5部屋の上/左境界の通路。上左/上右/左下などを含み、赤線/普通木扉/黒い未観測だけを金壁正例にしない。画像は視覚ラベルでありローカルrawファイル未提供、寸法/px入力座標や実C認識の検証に代用しない。後続画面を合成して実機成功にはしない。

## 3. 詳細設計

### A. 既存停止

保護mask全体の同一性は保持し、origin/実nextの保護は必ず拒否。近傍の保護が両画像で同じ不通行GOLDにだけ重なる場合は、商品の歩行床保護と区別する。Navのorigin近傍とControllerの入口quietを整合させ、入店後の追加床歩行も可能にする。FLOOR/DIRT/DOOR/ITEM/UNKNOWNの保護は拒否。

未入店・lead/実MOVED確認済みのreason8/FLOOR・両GOODS_UNKNOWNでは、同full5/全金/全保護/strictBLOCKED/元ID・全clockと既存3×3局所不変が揃う遠方palette揺れだけ、quietで同IDを保持する。実2eはこの条件で予約を更新せず次拍へつなぎ、ルート不変なのに確認待ちを挿入しない。その他の同票SAMEのchain2/run8は変えない。確実未送信state1/begin0/outcome0・lead/実MOVED済み・同full5/金/全保護・同goods UNKNOWN又PARTIAL・origin/nextFLOOR・旧→最新strictBLOCKEDで、UNKNOWN/FLOOR/DIRTの見え直しに限り（protectedセルの材質変化も拒否）、旧票を永久not_sentへ。最新anchorと後続の独立非交差current-prefix静止pairを同full5等で証明してから、別ID/将来拍prep50ms/最新model sample≥proofへ判断し直す。前verifiedごと1回/session8回、元verified+12秒/旧sync/walk45/session180/16入力を固定。新modeを旧closed/terrain各一回から分離し、送信UNKNOWN/旧ID/epoch/creditを復活させない。

開扉補助はprimaryUNKNOWNだけ。原zero最良候補・score≤.45/gap≥.08/全73候補・唯一gold bracket・同方向DOOR→FLOOR・両originFLOORと歩行先保護なし・元金bracket保持を要求する。専用maskは既存expandedの下端79を85へ延ばし、既存detail>=6、支持300/95%/全候補15ppとdisjoint上下band(y<65/≥65)各100を要求する。既存normal/expanded/MOVED/閾値は不変、開扉creditだけで歩数は増やさない。新露出商品PARTIALは全商品完了にしない。

### B. 通路接近（A完了後）

Perception/Scene enumを変えずGOLD_CLEARのまま、初期座標の上境界(k,-3)/左境界(-3,k)、k=-2..2をpure Navで検出する。両脇に観測壁があるFLOORの口は外側UNKNOWNでも候補とし、口自体UNKNOWNなら外側FLOORと壁列の支持を要求する。黒だけの隙間は候補にしない。普通の右/下出口へ無差別探索しない。金壁が見える既存経路を最優先。赤線/minimap/未来情報/疑似GOLDを使わない。

検出した複数mouthをworld座標で保持し、既知FLOOR最短経路で一つずつ接近する。目標は壁境界の一つ外側、途中UNKNOWNは歩かず、見えている内側vantageで新画像を待つ。形/route/protected/同prefixを各入力前に再確認。新しい金候補/既存edgeが現れたら予約の新旧権限を分けて通常plannerへ移る。FLOOR以外の掘削/開扉は金根拠なしでは禁止。

local private modeとmode-aware chooser/safe_stepで初歩校正/連続予約へ接続し、旧shop safe_floor/referenceの意味を偽装しない。探索開始/初歩校正/未送信予約/ACK待ち/最終CLEAR、続くPAUSE/RESTARTの予約・ACK待ちで商品PARTIAL・VISIBLE/ITEM/保護、新金候補、取消/前面/owner失効、UNKNOWN送信を検査する。PARTIALで金根拠がなければ保持停止、VISIBLEは商品保持、適格MOVEDのみ最大1credit、保持後の方向/RESTARTは0。移動は従来ng2_motionでunitMOVEDを証明。外側目標へ実到達し、独立したstable GOLD_CLEARがあり商品UNKNOWNなら候補を局所見送り、他候補があれば継続、全候補がこの条件で終了したときだけPAUSE→RESTART。途中UNKNOWNは内側の観測床vantageへ接近して新露出を待ち、元期限内の最大2拍でなお到達不能なら未判定へ分ける。未判定候補は不在/完了へ数えず、他候補の後も未判定が残ればNO_PATH保持停止。GOLD_UNKNOWN/商品のPARTIAL・VISIBLE/保護・未知送信・期限切れを不在にしない。

restart比較基準はPAUSE直前の最新安定current-prefix FLOORで凍結し、初期画像を流用しない。RESTART ACK後の独立画像でも同じ終点worldなら新levelとしない。歩行後restartでは、この基準からの確認済みfingerprint変更後だけper-levelの座標/visits/入口/lead/model/slot/reference/探索候補を撤回する。session時計/総入力・移動/events/ID/取消を巻き戻さず、level開始時の総数をbaseとして初歩条件と区別する。旧callbackは新levelに無作用。walk_started_nsは最初の歩行episodeから保持し、level用の初期同期起点と区別する。元16入力/12restart/45walk/180sessionは延長しない。

## 4. テスト影響範囲

AはController/Nav、BはNav純粋関数/Core宣言とController private state。Runtime/Ticket/Perception/取得/HTTP/closed wire/ABI/API1.98.16/cap14/clientv15は変更しない方針。初歩/retune/予約/取消/restartの影響を調べ、必要な限定Mac境界を選ぶ。native変更の新IPAと22seal/実compiler/全Mach-O/完全source照合を行う。

## 5. 新規ケース

保護GOLDと保護歩行床の区別/4方向・入店後追加床、chain上限で旧票失効→独立pair→別ID、元期限/一回上限/旧callback/商品/owner/phase拒否。開扉は4方向/新露出商品と金/支持・band・差・非zero・bracket不成立・UIだけの拒否。受領全48原画は既知資料として差分を確認。

探索は同native sessionのrestart→次level通路候補→新金→開扉/入店→商品保持の一連proceduralケース、上左/上右/左下/影の口/複数口、黒だけ/普通扉/保護/非床/到達不能の拒否、world target保持、金出現の通常shop移行、独立CLEARからrestart、歩行後restartのlevel resetと総予算/旧callback、restart前後の元walk+45秒等号での停止。procedural未来画像を実機の正例にしない。

## 6. 実装順

正本要件・[限定契約](../contracts/passage-approach.md)更新→重点プランレビュー→Aの機能別semantic Red→最小Green→A凍結→BのNav Red/Controller Red→最小Green→責務整理。所有fileを分け、Controller/Navの引渡しを明示して同時編集しない。計画外の大きい変更は正本へ反映する。

## 7. コミット前・返却

変更単体/名前を選んだ関連回帰、独立設計・網羅・安全レビューを最大3周で閉じ、P0解消/残P1/P2明示。無関係な全Runtime/worldは累積しない。標準public Mac/Ubuntuで必要な新IPA、実物5種証明と全sourceを照合し、固定Releaseを匿名取得確認。新IPA更新/完全終了・起動/Start Server、2026-11-11の最新指示に合わせ、新通常1-1から「候補までリスタート→金壁/通路候補→商店→全商品」の一連TEST072をまず2回依頼する。手動で金可視/不可視の開始群を用意する依頼を既定にしない。自動run別全ZIP返却、未完了の終了表示/次start禁止を維持。

## 8. スコープ外と未確認

全マップ探索、金根拠なしの掘削/普通扉開け、購入、認識閾値の一括緩和、予算延長、実測なしの到達保証。12画像には探索済み負例がなく店の有無を保証できない。新パターン精度・実機到達率/毎拍は次の端末試験で確認する。
