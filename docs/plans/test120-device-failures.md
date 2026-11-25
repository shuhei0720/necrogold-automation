# TEST120: TEST119の実機停止と成功を同じ条件で確認する

2026-11-25（日本時間）。基準はTEST119/build266、製品CODE617fc248、保存HEAD1d9a0a4。ユーザーの「修正で成功動作を潰さない」「実機失敗を直す」を受け、成功・停止の全原本を比較してから変更する。過去の合成/CI合格を実機改善完了へ読み替えない。公開GitHub・Actions・固定IPA/完全sourceの既承認は継続し、保存目的の再確認をしない。

## 原本と比較基準

11ZIP/7run/4campaign・170PNG/203記録を全照合、欠損なし。原本/PNG/Scene/報告はGit外。実順は723root、1a358root→ca2child、6423root→c41child、aa8root→2d1child。ZIP添付順を実行順としない。旧TEST118/build263のexact Git source（C535a9f0e/Perception446c9b/Ringf62e/Nav e6893c8a）と119（Cef0fffaf/Perception19ff/Ring7ef61f/Nav同一）を固定し、同じ原RGBA・通常producer・時刻・拒否guardで比較する。未保存private状態を宣言contextで補ったcutは完全実機再生と区別する。

| 事象 | 現時点の原本からの原因 | 次に確認する範囲 |
| --- | --- | --- |
| 723 root・3歩後SCREEN | 既stationary wait中、323→329のみ直接零、323→330はUNKNOWNだが329→330は零。同じDOWNでもvantage target変更をsame_choiceが拒否。元P/W内 | 旧anchorをUNKNOWNのまま信用せず、独立した現在零と有限な待機条件の扱いを設計。119 live票専用修正の待機側適用漏れかを確認 |
| ca2 child・1歩後SCREEN | 元67→69の通常零、旧UP→新LEFTのGOLD vantage再判断。旧経路FLOOR→DIRT・遠方STONE→DIRT等が既開口条件外でROUTE10。exact旧新の公開C cutも同一停止 | 旧UPを撤回し現在の正床/同GOLD/保護・通常零から有限route観測へ。後続独立proof/fit/未来新IDだけ許可 |
| c41 child・通路SCREEN | source122→123は通常strict零。新DOOR2セル先＋bracket GOLD露出・遠方DIRT→FLOORが旧単調関係の適用外でGOLD8。旧新producer同値 | 元GOLD/保護/現在の正FLOOR/同方向/確実未開始と固定期限を保持した限定関係。既door3セル先の条件との適用表を確認 |
| 2d1 child・開扉後CAPTURE | 原画像は2商品のPARTIALで正しいUNKNOWN。LEFT22をCが予約/承認したが、Runtime実送信直前で元Dを50,136ns超過 | 同じC-owned pairの通常Motion再計算を削減する案。begin記録→sendNowの7.466542msはC/Runtime guard全区間で、実機の個別費用は未記録。D/10msを延ばさない |
| aa8 root・capture62左上候補見逃し | ユーザー赤丸は左上。CLEAR/peak55/mask0、旧新全Scene bytes同一。既左上fringeは外capのFLOORを要求するが原画capはDIRT、外床はUNKNOWN | [別plan](test120-upper-left-candidate.md)の観測cap/全屋根/全左壁/正内床を独立witnessへ。旧nonzero mask保持、0時だけ既bit5。普通木扉はDIRT/外床UNKNOWNを維持し4正床以内の再観測だけ |

## 成功を壊さない基準

1a358/source173のpolicy9、6423/source335のpolicy7、aa8/source235のpolicy4/layout3は、正常完全陰性→C採用→耐久保存→実RS→新floor→同Runtime child開始を実記録で確認。policy7のunmatched_items=2は正式に許容された成功で、一律0条件を追加しない。aa8は119の同列白点/独立低価格対策が実機で効いた例。旧263では同原画UNKNOWN/PRICE64、119では完全陰性/cert1。前2成功は旧新正常判定packet全bytes同一。旧TEST118/3f policy17の成功も維持対象にする。

末尾rootのassessment nullやadopted falseはnewfloor後のresetであり成功checkpointを否定しない。rootとchildのclock/ownerは別なので、clock_id一致やchild初手PAUSEを一律の不変条件にしない。sealのnext_id/root期限/predecessor/index/同runtimeの接続・重複bootstrap RSなしを原証拠へ結ぶ。

## 実装・試験の進め方

原因別の最小案と適用表（観測/待機/READY/begin）を作り、入力資格・固定期限/予算・候補保持・未観測陰性禁止を維持して独立レビューする。大きな候補方位/証明契約変更は別8項目計画で先に確認する。正式assertion Red→最小Greenと直接関連を選び、環境不足を製品Redに数えない。

同じControllerファイルは担当関数を分割して並行編集し、勝手な全体置換や旧guard削除をしない。成功3rootの通常packet/採用条件と旧119の直接関連を保持。変更した入力/queue境界だけMac結合を選び、無関係な全world/故障集合を増やさない。手続き画像/clockと実iPhoneの限界を記録し、未保持の未来画像を補完しない。

native変更後はcap120/clientの識別、選択host/実Python3.9、必要なMac境界、実IPA/profile/source/seal同一性を確認する。IPA/完全source/SHAを固定Releaseへ置き、匿名全取得/実tagまで照合する。配布時は具体的な修正点と維持した成功を短く報告し、通常1-1ポーズから初回RS・`--until-target`と全run ZIP返却を依頼する。実機の改善/毎拍/人超え速度/未知精度の受入は新結果まで未確認。

[route観測計画](test120-route-observation.md)・[PARTIAL同一証明再利用](test120-partial-proof-cache.md)・[左上候補](test120-upper-left-candidate.md)を独立設計レビューしてから製品へ適用する。右下という途中解釈は最新ユーザー訂正で撤回し、右方位や新bit/APIの拡張は行わない。
