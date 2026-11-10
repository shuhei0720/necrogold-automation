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


## 最終Mac110と配布物

code `f9bcc3bc7ec97ac4fa692bf388ffd64d79148e03`、[Mac110](https://github.com/shuhei0720/necrogold-automation/actions/runs/42818545816)成功。実IPA0.3.4/build110/top.ebato.loopctrl、17,588,671bytes/SHA `a5100f749b9f21b755292a8d5c2732743cc059fde1ac4a246c10ccca23ad1402`。unsigned artifact13766391271、17,853,847bytes/SHA `d72790df2a9a0f87378f82c2ad9ee8964ab5645c41d4de0b5222e535a784e1b9`。validation13767715273、1,190,667bytes/SHA `9c2f93507d4005d362e2a507a14cf6e293c0bbd317c007f9281faa7a2cf9f0e3`。host13765248938、12,063bytes/SHA `370cc1d227e90a2ec29b4ac9dd0582c7e67cd0474595ed3e2d573aff085f329e`。GitHub run/head/branch・全outer SHA/bytes/CRCを照合。

host39/16区分、全実行ID/生ログ/0fail/error/skip/xfail、実C ABI・22seal前後・3clientモジュールの実driver/HEAD Git blob/SHAを実IPA sourceへ結びつけた。API16/cap14/v15、native4（RPCMethod/Controller/Runtime/RPCContractTest）変更/他18・R12原40/G1不変。manifest SHA `0bb0670317691250b7cf3dfe9aa4bdc6fd5d7e40bd7b31567ce672a1e8f6f783`。

正式Runtimeは固定6180の原Runtime SHA f37ddcd1…に2HOST seamとAPI文字列だけ加え、旧順序の対象assert `FAIL MISSING_test070_due_reissue_prepares_before_evidence_retention`をRedとして確認。productionは新070・旧prefix/cancel/controller/deadline_equal4case・identityの6呼出を実行しGreen。実stage Swift/main/Fakes・compile/run生ログ・hostMach-O・4Cobjects/flags/SHAを実IPA sourceへ照合。新Runtime SHA `bfb0f271ca4504b7c428661a597c0fc070db29d993904f70c9020abb76b549f7`。この合成queue-cost境界の成功を実iPhoneの受付時刻/毎拍達成へ置き換えない。

実iOS compiler4C/5Swift/6RSP、rawlog/PBX/引数/profile一致。Perception/Nav strictO2、Controller/BeatO0、SwiftOnone、HOST macroなし。全9Mach-O/115禁止marker非混入、app/runnerAPI16/cap14/arm64を確認。build-source全526tracked bytes/path/CRC、7,449,909bytes/SHA `a5f0b6a779d07df95114a14bf35c5d658e3e989f3abaf9deaed045814aebebb9`。

ビルド後test-only `9aa9d9e2a0ea0a84615933a39fafe9153cca902d`で、NativeResultsTests.test_bad_trace_is_rejected_on_results_and_legacy_journal_reloadのlegacy copyをv14/API.15へ明示pinする2行を追加した。旧≤3拒否assertを新v15ログへ誤適用しない修正で、既存assertは保持。このmethodと未変更test_motion_wait_requires_all_seven_bounded_typed_fieldsの2件Green.028秒。製品/client/nativeは変更せず、IPAを再ビルドする理由はない。最終sourceとビルド対象との差分はこの1testとstatus/本review/台帳3文書だけで全製品bytes同一。sourceの全tracked照合と限定diffを別に確認して固定Releaseへ保存する。

独立レビュー最終P0/P1なし。実機の毎拍/商品可視/保存完了は新070で未確認、既知の商品認識1/3問題は未修正として記録。SideStore更新/完全終了・起動/Start Server、新1-1からtest_070.shをまず2回依頼し、既知通路の毎拍と新地形での待ち、商品全体、終了理由を自動ZIP全run分で確認する。[手順](../status.md)。
