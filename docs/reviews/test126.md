# TEST126起動memory: 受領・検証記録

2026-11-28（日本時間）。[計画](../plans/test126-startup-memory.md)。製品基準1617fd2、nativeはTEST125/build278 CODEc18db303。client修正1の待機/元期限/UNKNOWN無再送を継承する。

OS Jetsamは同App PID11645 LoopCtrlAllInOneにper-process-limit、2098MiBを記録する。App build278との結合は既App logの同PIDに基づく。JetsamのbuildはOS buildでありapp版の証明にしない。largestProcessだけではkillを断定せず、当該processのreasonで判定した。killDelta/timeDeltaは保存し、正確な終了時刻や経過時間へ換算しない。原本/個人情報はGit外で保全する。

[Apple一次資料](https://developer.apple.com/documentation/xcode/identifying-high-memory-use-with-jetsam-event-reports)の定義に照らして独立担当が同じ値を確認した。通知/VPN/Wi-Fiの設定不備へ原因を戻さず、割当元はsourceと限定fixtureで調べる。静的解析で確認した保持・読込経路を実機のallocation traceと同一扱いしない。

設計確認は独立担当1名でP0/P1なし。validated seal/chain由来のmembership、欠損header推定slot/競合root、quota代入前後のpublication別判定、owner/input_authority=false/receipt-only sibling、streamSHAのFD/EOF条件を最終差分で確認する。実装試験・IPA・公開は未完了。実機改善は次の受入まで未確認。


変更前の意味Redを実Macで確認した。専用run46128930089/job140929615823、commit2ece9ba9・baselineSpool SHA242cdabf。元配布の全bytesとcmpした上で、同一temporary counter注入のfixtureを実Swift6.3.3.1.3/-Ononeでcompile成功。3別processは、work64 metadata load（8namespace、上限32）、同時保持8（上限4）、hash scratch1483776B（上限65536）でそれぞれ指定assertion1件だけ失敗した。exact pending/原本全file不変/終了後解放は先に成功している。compile/環境失敗をRedに数えていない。

元artifact15257096891はGitHub digest SHA0aa5c94d311016ec2aa209218d73342833460290d54c0aea649bf1efb91b2047と全bytes/CRCを確認した。CLIのAzure直取得は拒否されたため、GitHub connectorのartifact取得→file参照から原本を保存した。memoryの構造上限を測る試験であり、RSSやiPhoneで2098MiBから減った実測とは扱わない。Red確認後にSpoolの振る舞い変更へGOした。


client/capabilityは実Python3.9.25で4件の意味Red（fail5/error0）後に選択53件が合格した（新126client14＋新cap6＋起動待機14＋直接19）。旧117〜124 namespace91件も合格し、旧567assertを保持した。旧117〜125の変更は未来拒否126→127のliteralだけ。独立最終読取でclient/package指摘0、旧125入口/初回RS/起動待機と旧API/profile/capを保持すると確認した。

Spoolはcompact facts/scan-local quota・source/ledger一件処理と64KiB逐次SHAへ変更した。validated seal next/reservationは先行own identityへ絞らず、元順序を保存してreverse推定後parentでfirst-matchを実行する。独立レビューの残差確認も指摘0（e3c011478faaa436fa8f58ed9518344444ff8a9a27b23f05130db26a41c7fbe3）。新Greenは境界3＋既116helper7＋094由来の新snapshot_parity＋新hash FD/short/growth3の14case。旧094本体を再実行したとは扱わない。元Red対象discovery/hash関数は同一bodyで、新FDobserver/counter追加は別来歴として保持した。

native manifestを最終sourceへ整合し、37件の変更RPCMethod/Spoolのみ・保持35、compile用addition28全bytesを確認した（manifest7afb305e）。Rootの新selector8は実Py3.9で合格。これは配布用scopeの検査でありiPhone改善ではない。実Swift Green/実IPA/compiler/全9MachO・完全CODE/source・固定公開の検証は次工程である。


## 実CI・原本配布前照合

CODE `75d328237c3ed8a5bbb72cc22e43f69f930d4dd9`、専用CI run46129888763/#1の2jobが成功。appbuildは明示式1000+run_numberの1001であり、CI run_numberと混同しない。host14（cap6＋selector8）、実CPython3.9.25の47（新14＋起動14＋直接19）、実Swift6.3.3.1.3の14（新境界3＋旧116helper7＋新snapshot_parity1＋新FD3）で失敗/skip0。実Mac計測は8namespaceでmetadata20/同時source2、hash scratch65536B。元Redの64/8/1483776Bから変化し、exact pending/原本全bytesとdigest/snapshot/publication/破損/容量の境界を保持した。これは模擬データ/実FSの確認で、iPhone RSSの実測ではない。

元package artifact15257770438/SHA `4fc82ac7255eb691467e3246bfbd9768079e2d01202c3bd4fe0354768e34c9a9`、validation15256754749/SHA `aa112fb34c0122a3c22668343d456dee965c1577ebb3ce83f4148539fed95bb6`、host15257292966/SHA `a7e4f9831b5bebf2156232aac850f57b1c71a2151c19cadc8ab3f2594fa5ddea` を全取得し、GitHub digest/全bytes/size/CRCへ結合した。

新しいreaderはsource-only準備・独立最終読取後、rootの明示GOで原本の五項目をattempt1に一度ずつ照合した。CI/全source-package/host実Py39/実iOScompiler/全9MachOがPASS、verification SHA `2f8f2aca94a529e0057c31fe4141d7163110182992f0c236202b6c0b37c054fb`。全1294Git blob、native37の変更2/保持35、compile addition28、canonical15＋binary/R12原本40、profile3の実PBX/log/RSP/必須C/Swift source、全9MachOと全世代HOST/fixture marker不在を確認した。reader自身のclassifier/compiler実行は0。古いC/gameplay/fullRuntime/fault/world成功を今回の実行と数えない。

IPAは18,536,391B/SHA `788720feec4d1324d4da573830815b46293ba82b8d2e26d42133bdee4374c64f`。CODEの完全flat archiveは1294Git blob/全bytes/CRC一致（10,851,631B/SHAa6e75e1c）。次の公式SOURCEはCODEから文書4件だけを変え、固定Release `test126-build1001` へ原IPAと完全source/SHA表を公開する。公開後の匿名全取得は別工程であり、この合格に含めない。新iPhone受入は未確認。


TEST126固定公開確認（2026-11-28）: CODE75d3282から文書4件だけの公式SOURCE `e9a86fa7597fb0e38c1bd294b8c5b1a62e7423bd`、完全1294Git blob/全bytes/CRC/同nativeを照合。source.zip11,018,665B/SHA `d25113b492a58cd2f84ef7ccddd346de04124d859f72ecbdeac9f6e2e6930137`。公開280/run46131121683は検証済みartifact15257770438の元IPAを再ビルドせずrelease461445393/test126-build1001へ保存した。CI build run #1/appbuild1001と公開workflow #280を混同しない。publish-download1job成功/他17skip。固定3assetを匿名全GET200し、原本全bytes/SHA/GitHub digest/size、両ZIP CRC、lightweight tag→SOURCEを確認（public receipt SHA `6b6673724e15be6d5fd45a5d5a2b54a8bcf6810d32a76c6c7f44431b2ab19f7b`）。IPA18,536,391B/SHA788720fe、SHA表156B/SHAb3af1faa。公開後は文書だけを追記し、asset/tagは置換しない。新iPhoneのmemory peak/起動/商品到達・実RS/速度・再発数は未受入。
