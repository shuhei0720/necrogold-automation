# TEST070: 照明による経路判断と毎拍歩行

2026-11-10（日本時間）。[計画](../plans/test070-cadence-lighting.md)。新可視地形でルートの判断を更新する必要がある場合だけ1〜2拍許容し、既知で安全な通路は毎拍とする最新指示を[要件](../requirements/necrogold.md)へ記録した。未確認位置/未観測/商品/保護/取消/元期限は維持する。

## 実機根拠と対象

[069の3run/50原画](test069-received.md)で商品可視到達3/3、全画像保存完了、自動GOODS1/3。現hashのPerception/Nav実Cで再解析し、fc37 UP→UPの約1.05秒待ちは位置合わせした重複範囲に新露出0、1357 DOWN→LEFTの約1.04秒は新露出5cell/方向変更と区別した。早期MOVEDはACK後49〜99msの実正例があり、長い待ち区間の保存済み早期ペアはUNKNOWN、後の原画はMOVED。途中の未収録画像をMOVEDとして補わない。

Controllerの第3確認が元1周期後に固定されていた。また1357再予約ではobserve終了D−3.181msからAXquery開始D+3.282msとなり、約10.256msの再照会後は元10ms窓を超えた。元SAMEの空間/strictBLOCKED/full5は実Cで成立。diagnostic作業を除いた実所要時間は未測定なので、後段のMac fixtureは独立したqueue/照会costを使う合成境界試験とし、欠落画像/実IPCの再現とは呼ばない。

## 実装

Controllerは同一ACK-known MOVEの画像評価だけ最大8へ。初回即時、2〜7回は直前の評価開始+元period/10以降、8回目は初回+元1周期以降も必須。旧最終機会を残し、早いstrict proofを次拍へつなげる。before/ACK/prefix/source/phase/ordinal/visualDと元12/45/180秒・16入力・UNKNOWN synth無再送・商品優先を維持する。

Runtimeはcoherent C snapshot/現在source pinを先に公開し、重い画像参照集合/整列/退避を既存Cepochによる前面証拠再利用・due dispatch後へ移す。pin上限20/旧priority、取消/世代/owner/前面/最新Sceneのfinal begin・UNKNOWN poison・全callback drainは保持。遅延retentionはsnapshot identityを再確認し、ACK後の新snapshotを古いpriorityへ戻さない。未検証latest画像を飛ばして入力する処理はない。

closed motion_waitの旧上限3を黙って緩めず、v15/API1.98.16/cap14だけ上限8。v14はAPI.15/上限3、v1〜13はAPI.14/上限3、旧UUID/clock/owner/export/cursor/診断とfeature setを保持する。ABI/layoutは不変。Perception/Navは不変で、商品認識の看板/HUD問題は別課題。169原画のgoods試作は採用していない。

公開済みTEST069のpublicationを再利用し、追加は試験番号の閉検査とnamespace/root/filenameの引数化、新070入口/launcherだけ。旧default069を維持し、070のlocal spool/自動ZIPへ分ける。未公開runを次startより先に処理し、完了前の終了表示/原本削除はしない。

## TDDと検証範囲

新native8件は固定069 Controllerで意味的Red→最小Green。関連26と合わせ34件Green9.477秒、照明/SAME/FRESH/全Decision/保護/元期限の関連12件Green3.937秒。新契約と直接衝突する旧5メソッドだけ8評価/短間隔/旧最終機会へ更新し、全拒否assertを維持。旧Controllerの古spacing依存4件はbaseline069でも同じ失敗で、今回変更せず、成功群へ含めない。

新client互換8件は意味的Red2assert/errors0→Green.293秒。旧v14のfeature/API固定、recursive report/legacy診断の上限、8受理/9やbool等拒否、同UUID回復を確認。初回loopback拒否は環境errorとしてRedから除外、実暗号HTTPで正式検査。関連client5件/package4件もGreen。wrapper新3件は意味的Red8assert→Green.083秒、旧publication15件Green.550秒。fixture import path不足の初回errorはRedではない。

workflowに今回変えたdispatch境界のMac stepだけ追加、新1assert Red→workflow5件Green。Runtime helperは固定旧Runtime6180eacf/hashf37ddcへHOST retention hookとresponse API metadataだけ追加し、旧cache順序の対象assert Red→sealed新Runtime Greenを同Macジョブで順に実行する。productionは新070関数・旧prefix/cancel/controller/deadline_equal4case・identity matrixの計6呼出、全world/全mutation runnerは呼ばない。selector新Red1→helper40件Green。local Swift未導入のため、正式なSwift実行はMac待ちであり、この時点では成功を宣言しない。

独立の設計/安全差分レビューはP0/P1なし。最終seal/API/cap/実compiler/全Mach-O/全source/実Runtime RedGreenはMac完了後に記録する。実機で既知通路の毎拍と商品可視到達が成立したとは未宣言。固定Releaseの新IPA/sourceと再起動/Start Server/test_070.sh/自動ZIP全回分の具体的な実機試験を必ず依頼する。
