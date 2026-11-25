# TEST121: 分断屋根の左FLOOR口を内床から再観測する

2026-11-25（日本時間）。基準はTEST120/build268、CODE `723c1c6`。対象は2周目child `a0840959463642ad8f90f7eb8e2d9b4c` のcapture1。[要件SHOP-03](../requirements/necrogold.md)・[通路契約](../contracts/passage-approach.md)と元入力/期限/予算を維持する。通常の局所Nav修正として短い計画と独立レビューを行い、製品・正式testの着手はroot GO後とする。

## 原画・出荷source・拒否条件

原寸896×414の原画を確認し、PNG SHA `a291649247e2e16ab0d26ee60cb881f80e07984ac1e1fde3f6d24738bd502062`、RGBA SHA `47319c6562202f47df5a0157abff420e9fba300a2121292a644bc9c0852dbf7a` と原frameのstable/prefix0/非inflightを照合した。出荷sourceはNav SHA `6b4faeb6adbee72c60e0ad58f3e253dffd40254b6b17e9bfb24d92e6ae8c3d97`、Perception `19ff0492`、Controller `cf471e36`。通常producerはFLOOR/CLEAR/peak78/商品UNKNOWN、GOLD/ITEM/保護0、mask0、Scene SHA `61916c2c19df17de794d8dfeebdb3b90d29e86dc96fcd04c5cae2f4f529beb5d`。旧119Navでも全Scene bytes同一・mask0だった。

実eventはsource1のPAUSE1 ACK→RESTART2 ACKで、この配置へのMOVEはない。同じ原frame/時刻とpublic irregular＋continuous(successor1)設定によるC startup cutでもphase FLOOR1から同じPAUSE予約となり、source/start/not_before/Dが原eventに一致した。これは初期detectorの適用外であり、候補成立後の移動guard拒否ではない。原本・全guard・raw sample・cutはGit外 `analysis-evidence/test121-gold/` のreport、`a084-capture1-guards-and-samples.json`、`a084-capture1-public-phase-cut.json`へ保持する。完全Runtime再生や実機入力とは呼ばない。

左口 `(-3,-2)` は今回は正FLOOR、inboard `(-2,-2)` はUNKNOWN（625px中564px黒）。屋根の `(-2,-3)/(-1,-3)/(0,-3)` は各625px全黒で、床へ上げる根拠がない。旧120の[全屋根壁cap](test120-upper-left-candidate.md)は「全屋根壁・左口壁・4歩内床」が条件なので今回は成立しない。親5572のフェード中306/307にあった旧bit4=16も、child1で上右セルがSTONEに落ち着いて消失している。早期の別候補をそのまま継承しない。

## 新witnessの必要な支持

Navの独立helperだけを追加する。下記を全てANDし、DIRT/STONEの違いは既 `passage_wall` のままとする。色/床/金閾値・Perception・Controllerは変更しない。

| 観測支持 | 必須条件と役割 |
| --- | --- |
| 初期Scene | 既valid/passage Scene資格、FLOOR・GOLD_CLEAR・GOODS_UNKNOWN・origin FLOOR、全GOLD/ITEM/保護0。未局在CANDIDATEや商品保護へ適用しない |
| 固定左口 | 実mouth `(-3,-2)` がFLOOR。普通扉やDIRTだけを口の正例にしない |
| 未観測の曲がり | inboard `(-2,-2)`、外側 `(-4,-2)/(-4,-1)` はUNKNOWNのまま |
| 分断屋根 | `(-2,-3)/(-1,-3)/(0,-3)` がUNKNOWN。黒だけを候補にせず、次の独立した両端壁をANDする |
| 左屋根端/cap | `(-4,-3)/(-3,-3)` が観測壁 |
| 反対側の屋根端 | `(1,-3)/(2,-3)/(3,-3)` が観測壁。片側capだけで広い暗所を候補にしない |
| 口の下側境界 | `x=-3,y=-1..3` の5点が観測壁。口の両脇と独立した左壁の連続支持を保持する |
| 正の内床 | `x=-2..0,y=-1..0` の6床と `(-1,-2)` がFLOOR。中心からvantageまでの安全床と、暗いinboardの内側にある観測支持を要求する |
| 有限経路 | 既FLOOR pathでvantage `(-2,-1)` が到達可能な3歩。mouth/inboard/外側はまだ到達不能。未知セルや壁を経路へ足さない |

この支持は、正のFLOOR口・両roof端/cap・側壁・内床を一緒に確認するための新しい有限仮説であり、金壁/店の存在証明ではない。Scene全bytesとセル材質を保持する。

## 候補集合・到達・予算

出荷120の計算結果を、120 cap fallbackまで含めて先にそのまま求める。nonzeroなら同じmaskをそのまま返し、0のときだけ新witnessから既bit5=32を返す。正規mouth `(-3,-2)` の意味を変えず、bit/方向/ABI/APIの追加・aliasはしない。旧nonzeroと新witnessが同時成立しても新bitを足さない。

既chooserはこの原SceneからLEFT/reason10/FLOOR、target `(-2,-1)`、経路長3を返す。現在の観測だけなら内側3正床までで止まり、mouthと外側goalへの実到達とは扱わない。新画像でのみ進路を読み直し、新露出がなければ既2拍/親期限内の未到達待機と未判定停止を維持する。FLOOR口をDIRT/STONEの閉口資格へ変換せず、vantage到着だけで局所陰性/RSへ進めない。

既120 capの4歩内床仮説は独立して保持する。今回の3歩も既4歩も初期画像の正床経路の境界であり、未知の4歩目や一括方向入力の権限ではない。各歩の独立観測・通常Motion・商品優先・実next FLOOR、元総16入力/12RS・walk/session/同期期限は不変。未来の金露出や商品の位置を補完しない。

## 正式Red・反例・校正範囲

公開testは私的PNG/Scene dumpを含めず、上記の支持を表す疎な地図を使う。旧subjectはexact出荷120Nav `6b4faeb6...`へpinし、Navだけをcompileする。並行するController修正をRedへ混ぜない。

- 正形状は旧0→新32をassertion Red→Greenで確認し、候補関数/chooserのScene全bytes不変と、固定mouthに対する既chooserの3正床→停止を確認する。別の小さいfixtureで中心だけ・口だけ・capだけ・黒だけの候補0も要求する。
- 各必須壁/床/UNKNOWNを独立に欠落・別材質へ変え、保護全230セル・ITEM/GOLD・UI/商品/不正Scene・別座標のcapを拒否する。到達不能の内床、未知セルへの入力0、口未到達のまま停止することを確認する。
- 新witnessの拒否を全候補0と混同しない。例えばinboardをFLOORへすると既左口32、上右屋根セルをFLOORへすると既bit4=16になり得る。旧候補が成立する反例は旧mask同値を期待し、0期待で潰さない。
- 新witnessと既lower-fringeが同時成立する地図は旧512のまま、544にしない。通常10mouth/複数候補・097系分断口・116/117・120 cap等の直接関連を適切に選び、旧assertを保持する。
- 原capture1の同じ通常Perceptionから旧0→新32・Scene不変を私的cutで確認する。全今回99PNGと旧119結果170PNGは、同じ基準Perceptionから各版のfresh Sceneを独立に作り、Scene不変・旧nonzero集合の完全保持・新mask差分全件を記録する。前回capture62の120 mask32も保持する。旧zeroからの追加差分は観測支持へ照合し、利用者未指定の画像を勝手に金壁正例にしない。

検証件数は支持と反例から決め、必要な最小単体/直接関連を選ぶ。269原画は既知校正であり、未知精度・実到達・毎拍/速度の評価には使わない。

## 順序と未確認

短い計画→独立レビュー→root GO→旧Navの意味Red→Nav最小Green→直接関連/99＋170校正→独立差分確認とする。pure Nav以外の入力/queue契約を変えないため、旧full world・全fault・Mac境界の再走は不要。nativeの実IPA/source/seal照合と次のiPhone受入はrootの全体工程へ結ぶ。金壁露出、口への実到達、入店/全商品確認、今回の見逃しの実機改善は未確認である。

実施済み: rootの計画レビュー/GO後、新8methodsをexact旧120Navで10 assertion失敗/error0に固定し、同じ新8件を最小helperでGreenにした。新8＋直接旧9の計17件がO0/strict O2で合格。全99＋旧170の269原画はnormal Scene差/書換え0、旧nonzero5件を完全保持し、候補差は今回a084 capture1の0→32だけ。旧capture62の32も保持した。chooserと旧helperのsource bytesは保持し、製品変更はNavだけ。

補足の原時刻public C startup cutでは、出荷120Controller/Perception/Beatを固定してNavだけ交換した。旧phase FLOOR1/PAUSE予約から、新phase SYNC4・passage bit5/pending32・input0へ進み、最初のtickは追加入力を予約せず独立観測/fitを待つ。未来画像・begin/実gesture/ACKは補完していない。最終owned freezeと校正/原ログはGit外 `analysis-evidence/test121-gold/` に保持し、rootの独立差分確認へ渡す。
