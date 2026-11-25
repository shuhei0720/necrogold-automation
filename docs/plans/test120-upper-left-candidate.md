# TEST120: 左上の壁capに沿う通路候補

2026-11-25（日本時間）。基準はTEST119/build266、CODE `617fc248`、保存HEAD `1d9a0a4`。TEST119結果のうち、利用者が最終訂正と赤丸で指定した4周目rootのcapture62左上だけを扱う。[要件SHOP-03](../requirements/necrogold.md)・[通路契約](../contracts/passage-approach.md)を維持する。右下の案は採用しない。

## 原画と原因

run `aa8eb6a0c0f24a9492bcbb9b6bc9b222`、PNG SHA256 `4f414180249cb09d0fe5a75d78c6230b7a9e2e43587640902555f656fb75b282`。原寸896×414の原画像を目視し、frame metadataのstable/current-prefix1・inflightなしとRGBA SHAを照合した。実event2のPAUSEはsource62、event3はRESTARTで、この配置へのMOVEは未発行。赤丸は位置説明だけに使い、縮小画像や注釈を入力特徴にしない。

旧build263と119のexact Perception/Navを同compilerで通常実行すると、全23,864 Scene bytesが一致する。FLOOR、GOLD_CLEAR、peak55、GOODS_UNKNOWN、GOLD/ITEM/保護0、候補mask0。Nav sourceも同一bytesであり、この原画は119変更による分類回帰ではない。FR116のFLOOR口とFR117の外側床Lを照合したが、今回の外capはDIRTで外床は未観測のため既形状に入らない。

外cap `(-4,-3)` は正DIRT、屋根 `x=-3..2,y=-3` と左境界 `x=-3,y=-3..3` は全て観測壁。`(-3,-2)` の普通木扉はSceneのDIRTを維持する。外側 `(-4,-2)` はfull sampleの445/625pxが黒、下帯325pxも全黒であり、上帯の床色断片からFLOORへ昇格しない。内床 `(-2,-2)/(-2,-1)/(-1,-2)` と中央2×2は正FLOOR。金壁の存在や未収録の先を正例にしない。詳細のhash・通常producer・raw sample・原時刻はGit外の解析証跡へ保持する。

## 限定変更

製品変更は `NG2Navigation.c` の独立した新witnessに限る。既 `ng2_passage_candidates` の全旧判定をそのまま計算し、結果がnonzeroならそのmaskをそのまま返す。旧結果0の場合だけ新fallbackを評価し、成立時は既bit5（実mouth `(-3,-2)`）の32を返す。旧成功候補集合へ新bitを足したり、既bitを別座標のaliasにしたりしない。

新helperは次の全条件をANDする。roof/leftの集計は新helper内で独立して行い、既top-dark分岐内のカウンタへ依存しない。

- 既passage Scene資格に加えてGOLD_CLEAR、全ITEM/保護0を要求する。
- 外cap `(-4,-3)`、屋根 `x=-3..2,y=-3`、左境界 `x=-3,y=-3..3` は全てDIRTまたはSTONE。
- 外側 `(-4,-2)/(-4,-1)` はUNKNOWNのまま。
- `(-2,-2)/(-2,-1)/(-1,-2)` と中央2×2 `x=-1..0,y=-1..0` は全てFLOOR。
- 既FLOOR pathの `(-2,-1)` は到達可能な3歩、内側 `(-2,-2)` は到達可能な4歩であることを要求する。

普通木扉単体でなく、外cap・独立した屋根/側壁・正内床が近接再観測を支える。Scene材質、色/texture/金閾値、ABI/API、計10bit、既chooser、Controller、入力・待機・総予算は変更しない。既chooserは原Sceneからnext LEFT/reason10/FLOOR、target `(-2,-2)`、経路長4を返す。各歩の新しい観測と通常入力資格は引き続き必要であり、この原画像だけで連続4入力を許可しない。壁・木扉・UNKNOWNには進まず、金が見えた後だけ従来の商店処理へ移る。

## 期待値と検証範囲

正式な公開testは私的画像/Scene dumpを含めず、上記の観測支持を表す疎な手続き地図を使う。意味あるassertion Redを旧Navで実測してから最小実装を行う。

| 検査 | 期待値 |
| --- | --- |
| 疎な正形状、DIRT/STONEのcap・壁 | 旧mask0→新32。Scene全bytes不変 |
| 原capture62の通常producer cut | 同じ原画/SHA/prefixで旧0→新32、Scene全bytes不変。既知校正であり未知精度ではない |
| 固定mouthに対する既chooser | 既知FLOORだけ最大4歩で内側へ。実nextは毎回FLOOR、壁/UNKNOWN/木扉向けの追加入力0 |
| 各cap/屋根/側壁/内床/外側UNKNOWN支持の欠落、別位置のcap、保護/ITEM/GOLD、UI/goods/不正Scene | 新witness不成立。旧候補も0のfixtureだけ全mask0を期待する |
| capをFLOOR等へ変更して既opaque候補が成立する場合 | 旧maskを保持。新witnessの陰性を全候補0へ誤変換しない |
| 新witnessと旧lower-fringe等が同時成立する地図、既成功の公開地図群 | 旧nonzero maskを全て同値保持。旧512を544へ増やさない |

O0/strict O2で変更単体と直接関係する既097/100/116/117等を選んで実行する。既assertを削除/skipしない。新witnessの支持欠落で別の旧候補が成立した場合は、旧Navとの同値を期待し、その反例を0へ潰さない。原画cutは私的証跡として公開testと分ける。手続き地図での既chooser反復は経路の安全性検査であり、未収録の実画面やiPhone到達の再現とは呼ばない。

## 実施順と未確認

この短い計画を先に保存し、独立した設計レビュー1回→着手GO→新testの旧assertion Red→Nav最小Green→直接関連回帰→独立差分確認へ進む。現時点では製品・test sourceは未編集。Controllerへの変更が必要になった場合はこのscopeで進めず、原因と設計を先に見直す。

今回のNavだけでは、未観測の金露出、通常Motion、実機の通路接近、入店/商品確認、毎拍/実効速度は未確認。native配布には実IPAビルド・seal/実compiler/完全sourceの同一性確認を別途行い、通常1-1ポーズから初回RS→候補探索→商店→全商品確認の実機試験と全run ZIPで受け入れる。関連しない全Runtime/通信故障集合や大型worldは、今回の境界を変更しないため既定の検証に加えない。
