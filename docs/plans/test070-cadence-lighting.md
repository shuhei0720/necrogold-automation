# TEST070: 新可視地形を確認し、既知通路の余分な空拍を減らす

2026-11-10（日本時間）、baseline `5782a4aac6ed3f2878bea0f5c97fb6cea8cb035a`。

## 1. 目的

最新ユーザー指示は「明かりで地形が新しく見え、ルートを読み直す必要がある場合は1〜2拍許容。それ以外は毎拍動く」。既知で安全な通路で確認/準備遅延による空拍を減らす。必要な地形/商品/保護対象の確認は維持し、既知の根拠がない次入力は送らない。

## 2. 実機根拠

[069受領](../reviews/test069-received.md)の3run/50原画で商品可視到達3/3、全画像回収。自動GOODSは1/3。方向入力間隔は約.52秒に対し1.04/1.57秒がある。fc37はscene_changesなしでも2空拍区間があり、地形更新だけが原因ではない。現Perception/Navと同hashの実Cで、保存済み早期UNKNOWNペアと後のMOVED、早期MOVEDの正例も確認した。未収録の途中画像は補完しない。

Controllerは初回即時・2回目1/10周期・未確定時の3回目を元1周期後に評価しており、次拍を待ちで失う。別箇所では12.556msの再検証が10ms送信窓を超え、また前面照会開始自体がD後となった。地図全体を作り直す固定待ちではない。

## 3. 詳細設計

同一ACK-known MOVEの画像評価を最大8回へ変更する。初回即時、2〜7回目は直前評価の取得開始から元period/10以上、8回目は同spacingと初回開始+元1周期以降を要求する。UNKNOWN/TWEENを途中で確定扱いせず、旧実装の遅い最終機会より前に評価予算を消費し切って終了しない。strict MOVED/開通等が得られれば即座に既存処理へ進む。元before/ACK/current-prefix/source/phase/ordinal/visualD・3秒/12秒/45秒/180秒・16入力・取消/GOODSを維持する。入力の再送回数は増やさない。

Runtimeは既存の早期ticket公開→preparePipeline→前面照会→notBefore callbackとfinal定数時間guardを利用する。重いCobserveより未検証旧画像のticketを優先して入力する変更、未発行票への権限prefetch、送信10ms窓の延長はしない。必要なら、発行後のdiagnostic cacheを権限準備/即時dispatchより後ろに置く等の最小手当を、実Runtime fixtureのRedと根拠がある範囲に限定する。現フローが十分ならRuntime本体を形式的に変えない。

新可視地形は最新Scene/full Decisionで判断し、実際に次の一手が変わる/未観測の安全性を確認する場合だけ経路更新として扱う。明るさや遠方可視範囲だけの変化を常時待ちの免除にしない。既存SAME/FRESHの全gold/保護/元clock/strict BLOCKED条件は維持する。

商品可視とGOODS判定の不一致は同じ画像認識の境界として原因を限定調査する。SHOP看板等のanchor不足が実画像/元条件で確定し、小さな安全な修正で成立する場合だけ本版に含める。単にVISIBLEへ寄せる閾値緩和や未観測商品を陰性にする変更はしない。調査で全sprite可視の証明に別の幾何定義が必要と分かったため、今回の商品検出変更は採用せずPerception/Navを維持する。

## 4. 互換と範囲

現closed motion_waitはattempts≤3。新8回を旧reportへ黙って許容せず、新native-walk-v15/API1.98.16-ngg2/cap14で識別する。v14はAPI1.98.15/上限3、v1〜v13はAPI1.98.14/上限3を固定して回復する。fresh新規だけv15へ移行、旧UUID/clock/export/cursor/診断を保持。ABI/layoutは不変。wireの他の変更を混ぜない。

TEST069のlocal保存/検証済run別ZIP公開は再利用し、TEST070のlocal namespace/ZIP名/launcherへ分ける。完成前の終了表示/次start禁止・同UUID回復・独立read-only300秒と取消境界は維持する。旧069の原本は保持する。汎用frameworkへの大きな移動はしない。

## 5. 試験期待

意味的Red→最小Green。3回目以降の短間隔strict proofが元次拍へ進む例、8回上限/spacing/旧最終機会/元期限・商品/UNKNOWN/取消/権限拒否を実Cで検査する。明かりによる新地形を判断する既存SAME/FRESH・経路差/保護の関連回帰を選ぶ。原画50枚は既知の調整資料で、未知実機の速度合格へ再利用しない。

clientはv15の4〜8受理・9拒否、旧v14以前の4拒否と各固定API/同UUID回復、freshだけ新version、closed schemaと全PNG回収を検査する。実Runtimeの前面準備/期限/取消/prefix境界を変更範囲だけ実行し、全Runtime/worldを既定で累積しない。

## 6. 実装とレビュー

Controller、Runtime境界、実画像/商品、client互換を担当分割し所有ファイルを固定する。設計/網羅/安全の独立差分レビューで新評価予算・旧互換・最終権限を確認し、P0/P1を解消する。小さな原因修正を優先し、全体再実装を混ぜない。修正込み最大3周、必要時間は使うが確認済み/未解明/次工程を報告する。

## 7. 配布前検証

変更単体・関係回帰と変更したRuntime境界だけをdevice CIで選択する。native変更の新IPAを標準macos-26でビルドし、API/cap/v15・22seal・実compiler/全Mach-O/完全sourceを照合する。コード/資料は既承認branchへ保存し、生ZIP/原画/report/派生証跡はGit外。無変更の全Runtime/world全体を速度改善の証明にしない。

## 8. 実機依頼

固定Releaseの新IPA/sourceを返し、SideStore更新→LoopCtrl完全終了/起動→Start Server→新通常1-1の金壁可視ポーズからtest_070.shを依頼する。商品全体の可視・既知通路の毎拍・新地形での必要待ち・自動GOODS/停止・ZIP保存完了を確認する。全回分の自動ZIPを返してもらい、069の回収済みrunを再実行させない。
