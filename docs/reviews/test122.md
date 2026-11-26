# TEST122: 受領・差分検証と配布確認

2026-11-26（日本時間）。[計画](../plans/test122-device-failures.md)。基準は出荷TEST121/build270/CODE4574786、保存HEADd78159a。今回の新IPA・完全source・実機改善はまだ確認中であり、過去の合格を新しい結果へ読み替えない。

## 原本・原因・既成功

8ZIP/4root/4campaign・96PNG/111記録/223memberを全照合。CRC/SHA、安全な一意path、全PNG/RGBA、記録鎖/prefix/escrow/実順、内包lastZIP全bytes、回収completed/drainedを確認。欠損0。実順fbbd→de9f→ca23→7a9d。7a9/source233だけ原どおりinflight/stable=falseを保持。生原本・画像・Scene/report/全source校正はGit外。

| 実機の主指標 | 今回の原記録 |
| --- | --- |
| 初回リスタート/実歩行/開扉 | 4/4・4/4（6/5/5/7歩）・3/4 |
| 全商品可視/その後の実RS | 2/4・0/2 |
| 正常UNKNOWNの期限内採用 | 3件。後のfailure status上書きと区別 |
| 新floor/次child | 0/0（今回の実成功として数えない） |

独立受領/成功監査は `test122-intake/receipt.json` SHA7eb484d1、`test122-success/receipt.json` SHAc5f8ef52。出荷28項目を照合したが、返却spoolにCODE/build/IPA/cap識別子がないためZIP単独のinstalled binary証明は不可。全96正常Sceneは旧119/120/121で同bytes。旧121新Nav32は全96Sceneの必須AND部分で拒否され、保持画像での適用外だけを証明した。未保持途中frameの全mask/hitなしとは言わない。

原153の強いunit証拠、原124のPRICE64、上部入口の4材質、原234のcap不足と235/236の既完全NEGを分けた。cause receiptsはGit外 `test122-movement` / `test122-goods`。UNKNOWNを未実行・時間切れ・陰性と同一視しない。同症状の再発は4件、同根因通算は不明を維持する。

## 設計と検証範囲

通常反復として4短計画と独立差分レビュー1回を使う。独立担当はupper/full-halo/singleton/price-independentの短計画にP0/P1なしと確認した。全旧資格を先に保持し、新しい正資格は各原因の限定条件へ閉じる。元P/W/D・150/100/10ms・owner/prefix/取消・UNKNOWN無再送・共有DATA2・drain・候補優先は変更しない。

価格独立21/4の全帯探索は同immutable呼出内の完成済OfferSweepProofをexact row/strip一致で再利用する。元ローカルmemoはsweep毎に解放されるので、別sweepへ自動継承されると扱わない。再利用によるchecks差は実走査数として残し、未実行分の加算でpacketを偽装しない。旧成功・対象探索/名前veto/tail保持と元100/150msを確認する。host所要時間をphone速度の受入にしない。

client/cap13pathの独立静的確認はP0/P1なし。新122は121継承で識別/namespace/capだけ追加、旧entry/shell/metadata body保持、旧試験のfuture-invalid番号は122→123の2literalだけ。正式Red17件/28assertion failures/errors0→Green17件、実Python3.9.25関連186件合格。元receipt/ownedpatch/全freezeとのbytes照合を行い、独立レビューでの再走は0。`test122-success/client-scaffold-review.json` SHA0b416243。

新native正式Red→Green・直接関連、combined最終差分、封印、実IPA/CI/全source、固定公開と匿名全取得の結果は、実施後にこの文書へ追加する。実機の商品到達/実RS/連続子周回/毎拍・速度の受入は新しいユーザー結果まで未確認である。

## 正式TDDと凍結source

| 境界 | exact出荷121での意味Red | 新/直接関連Green | 原画像での限定校正 |
| --- | --- | --- | --- |
| singleton dependency Motion | 公開Motion32subcase＋公開earned LEFT後UPの第8枠unit1、計33assertion failure/errors0 | 新Motion7＋C ACK3、旧関連34 | 固定134→140..151はUNKNOWNを保持、153だけunit。元visual内のcommitはanalysis→cleanupの因果boundで、実commit dumpとは言わない |
| V2上部入口 | 新9method中12意味assertion failure/errors0 | 新9＋旧関連24 | 340→402..407の旧静止validation9→0。保存末尾から残5歩のbudget成立は主張しない。早い公開earned current→HHDDDは独立モデル |
| FULL halo DATA | 新8method中3意味assertion failure/errors0、既拒否5を保持 | 新8＋旧関連15 | 234→235/236の旧pair0を保持、新DATA資格だけ1。235/236の通常NEG7/数値証明/C1は旧から同じ |
| 価格独立21/4 | corrected procedural4methodで4assertion failure/errors0、原124の正常UNKNOWN7→新21/4 NEG期待も別Red | 新4＋旧121 coverage7/single-sign103の8 | 原122..125全て正常NEG21/4・Ring証明/C各1。7a9の234はUNKNOWN、235/236は既NEG7の全6112bytes同値 |

無効fixtureのSIGN背景消去、cleanup PAUSEを誤拒否したoracle、共有Cの一時compile失敗は、訂正前原出力を残し最終の意味Redへ算入しない。既snapshotで見つけた退行も隠さず、H1後のUNKNOWN→DIRTをSTONEと誤説明した記録を訂正した。新upperはV2の初回H1前（inputs/horizontal/down全0）へ限定し、H1後の旧bridge/rebound/既assertを保持した。3counterの増分bodyは出荷121同bytes、原28開扉後MOVE begin/MOVED0からphaseを推論し、privatecounter dumpとは言わない。

全authorの最終nativeはC `ff4d9531`、Nav `e0c43a71`、Ring `426c19d2`、Header `7c067c31`。Runtime `58c6de65`とPerception `19ff0492`、旧入力/取消/通常world・pair/bindの該当bodyは保持。各所有hunk/source-preservationと正式test/source freezeはGit外receiptへ結ぶ。singletonでは他guard適格下で15ppだけ不足する専用negative1種は未実施。既texture_lead同bytes/直接関連と全72競合の実支持/最小差23.460247pp、支持不足negativeの確認を代用範囲とし、専用case合格には数えない。

旧実成功5packetは出荷121実packetと新122の全6112bytes・Scene・NEG証明が5/5同値。`test122-goods/success-five/direct121-to122.json`へ保存。原124の完成proof再利用は追加pose/bound実計算0、checks4337。再利用なしは4520checks/17613計算で、checks以外の意味/全数値一致。local memo有無は21/19/20全6112bytes一致。新row1はhost実単調時計/新source-worker原点で100/150ms内の正常NEGを3call約61〜64ms、価格なしrow0は別1call36.726ms/残63.258msで確認。実phoneの旧残56msをhostへ流用しない。実CPython3.9.25で21/4価格0のatomic保存→ZIP回復のrawbytes/全型値も一致。これらは校正/補助試験で、未知配置精度やphone所要時間ではない。

証跡: goods `final-receipt.json` SHA45a99a43、upper `result.json` SHAa9984b96/`counter-source-proof.json` SHA4bd565e3、full-halo `FINAL-RECEIPT.json` SHAf4b7efa1、Motion `final-receipt.json` SHA3ccfc87a。新selectorは旧121のhost/Py39/workflowへ同assertを向け5件assertion failure/errors0/skip0（compile0）、Greenは封印後に実施する。

## 独立最終差分と封印

通常反復のcombined差分レビュー1回を完了、P0/P1なし。新selectorのログ名だけ121へ残ったP2は122へ修正し、同差分を再読して閉鎖した。旧guard44関数全body・旧assert保持、全17対象source/freeze、20group88method＋selector14＝host102、実Python3.9の86method選択を確認。レビュー中の試験/分類/compile/Git再実行は0。`test122-success/final-review/receipt.json` SHA7588e77b。

review後に固定upstream6e25cf6へ元G1f9508cd3→新G2をseal/applyし、全37nativeの実ファイルSHAをmanifestと照合した。5変更（RPC/Controller/Nav/Ring.c/H）・32保持・追加/削除0。manifest SHA1d0d2e27、patch SHA5cd7b910。API1.98.16-ngg2/native_v15/ABI1/profile3とRuntime/残Swift/Perception/R12/G1は保持する。Git外 `test122-root/seal-source-inventory.json` SHA320fb243。最初にmanifest entry辞書をSHA名のkeyへ置いた準備receiptは別保存し、実37SHA文字列へ訂正/全applied bytes再照合した現receiptを正とする。これは配布前のsource確認であり、実compiler/IPA gateの代替ではない。

封印後の正式selector14/14はGreen。最終source freeze SHA88c6db66でnon-doc895全bytes/hash、既存15変更/新10、全28additionのdriver/applied sibling、fixture67source/CORE59 import-only、31/102/86 methodを照合した。host final化はreviewed b9f02627から2flagと説明comment1行だけ（after9933b9c6、increment receipt SHA480b0f20）。実host102/実Py3986は重複したローカル全実行を増やさず、次のCODE固定の標準CI一回へ残す。local source freezeをGit CODE pin済みと誤表示しない。

## 実CI・IPAと配布前照合

CODE `f5143e339a1e6efddb3c24a69dbea163fd1007de`、[CI272/run45763652619](https://github.com/shuhei0720/necrogold-automation/actions/runs/45763652619)。標準Ubuntuのhost102（20group88＋selector14）・実CPython3.9.25の86、標準macos-26の実IPAが合格。必須18jobを全取得し、3active job成功/他15skipは選択どおり。全Runtime故障/合成worldの再実行0、新Mac Runtime0。正しいskipを実行合格へ数えない。

元3artifactのtyped ID/name/必須GitHub digest/raw全bytes/SHA/CRCを確認。package15091227992/c1755b92、validation15091263019/e94fa636、host15091575534/274aa2f9。IPAは元packageのmemberから全bytesを保存し、18,500,451B/SHA `a9affa880979b1abd05686c907f489c8ac355a89eb91ad829e2c833cd02efa96`。ローカルCODE flat ZIPは全1231Git blob/全bytes/CRC一致、10,492,397B/SHA0a502f63。

独立したread-only5項目（ci/source_package/host_python39/ios_compile/macho）はattempt1で全PASS。実compiler/RSP/PBX/profile3、37native、全9MachOとfixture marker3088、全source/host/実Py39方法/shaを確認した。新classification/compile/過去Runtime gateのローカル再実行0。`test122-delivery/actual272-attempt1/verification.json` SHA8b974960、readeredd3579/scope20c01e23。旧helper4/source9/data3とactual270由来の明示marker188＋legacy経路を保持。新scannerのescape疑義は標準re校正で誤読と確認、reader差分0。prep/actualのswitch・原input・失敗初稿を混ぜない。

[固定IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test122-build272/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test122-build272/source.zip)・[SHA表](https://github.com/shuhei0720/necrogold-automation/releases/download/test122-build272/SHA256SUMS.txt)。検証済みbuild272を再ビルドせず保存する。公開用SOURCEはCODEから文書4件だけを更新し、公式ZIP全Git bytes/CRC/同nativeと公開3assetの匿名全GETを別途確認する。iPhone受入は新返却まで未実施。
