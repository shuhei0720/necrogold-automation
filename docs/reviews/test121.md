# TEST121: TEST120の扉前・商品確認後の停止と通路候補

2026-11-25（日本時間）。[計画](../plans/test121-device-failures.md)・[修正表](../fix-records.md)。基準はTEST120/build268、CODE723c1c6、保存HEAD55a762f。限定実装・関連検証・独立レビューを完了し、CI270と実IPAの5確認が合格。iPhone受入は未完了。

## 実機で確認した成功と失敗

7ZIP/4run/3campaign・99PNG/117記録を、CRC/SHA・全原寸PNG・metadata/prefix・親子・内包lastZIPまで全照合した。提出欠損はない。原本・画像・Scene/packetはGit外へ保存する。実順は3a4a→5572→a084 child→18c0で、ZIPの添付順とは異なる。

3a4aは6実歩行後の扉前で停止。5572は全商品観測と正常policy17陰性→期限内C採用→耐久保存→実RS24→別floor306→同Runtimeのchild歩行が成功した。a084と18c0は全3商品が見える画像に到達したが、正常UNKNOWNを期限内に採用し、PAUSEの実ACK・耐久保存後にGOODS終了した。未分類やタイムアウトを原因とした修正はしない。

今回の観測4runでは全商品位置への到達3/4、その3件で商品観測後の実RSは1/3だった。これは受領したTEST120の結果で、TEST121の改善率ではない。未出力の過去jobやprivate予算/modeを補って実機再生と呼ばない。

## 原因に対応する変更

| 対象 | 確定した原因 | 限定する修正 |
| --- | --- | --- |
| 3a4a扉前 | 同じ閉扉・同じ判断・通常の直接零でも、後方対角1セルのDIRT→STONEを旧quietが拒否 | 未開始の同じ予約に限り、両方とも通行不能な1セルの材質差を認める。元ID/source/期限/親予算は維持 |
| a084商品確認後 | 文字で同じ看板が2成分へ分かれ余剰判定。まとめても左端の床支持で別に拒否 | 物理看板の全成分を確認するgroupと、元床閾値を保つ非重複UL/LRの別証明。真正な余剰や対象候補は保持 |
| 18c0商品確認後 | 正確3ITEM・7GOLD・床端は成立するが、暖色の文字が既SHOP認証から外れる | 既文字形と元一致率を使い、正のSIGN背景との相対明暗で別認証。新しい商品登録・名称OCRは追加しない |
| a084 capture1 | 左FLOOR口と黒い分断屋根が旧cap仮説の適用外 | 既候補集合を優先し、旧mask0だけで両端壁・側壁・正床から再観測候補を追加。未知床へ進めない |

新商品proofは別の有限policyとして表し、独立C consumerも自分のScene・3商品・対象/候補・数値witnessを再検査する。UNKNOWNを陰性にせず、既成功policy17/9/7/4、初回RS、連続周回、元期限と送信後UNKNOWN無再送を維持する。

## 検証の選択と現在位置

旧出荷120の同条件assertion Red→限定実装→Greenと直接関連を選ぶ。原215/125の通常producerとC採用、実機で成功した5572のpacket保持、原3a4a guard、全99＋旧170画像のNav差分は別々に記録する。既知校正を未知精度と呼ばない。

TEST121 client/capは独立最終レビューP0/P1なし。新client11＋cap6＋直接旧関連89の実CPython3.9.25の106件は合格。旧client/shellは同bytes、旧将来無効番号の8 literalだけを更新した。これはnativeやIPAの検証とは別である。

閉扉はexact旧120で最終fixtureの主assert8件が失敗し、修正後は新6＋直接旧14の固定20件が合格。原125→126の限定cutもquiet0→1だけで、成功5572のUNKNOWN/gate-refitは維持する。新helperとquietの差以外は全Controller bytesを保持した独立最終レビューP0/P1なし。ACKを開扉や実歩行に数えず、元D/P/IDを保持した。原private model全履歴の再生や、まだない実機成功とは区別する。

Navは正式新8件をexact旧120で10 assertion失敗/error0に固定し、最小修正後は新8＋直接旧9の計17件がO0/strict O2で合格。全269画像のScene差・書換えは0、旧nonzero5件をすべて保持し、差分はa084 capture1の0→32だけだった。旧helperとchooser以降の全bytesを保持した独立最終レビューはP0/P1なし。原frameだけの限定C cutも、PAUSE予約から候補保持/SYNC4/input0へ変わる。次画像・実入力・金露出や入店の証明ではない。

商品側は新7件がexact旧120で9 assertion失敗/error0。最終Ring6127e5f9/Controller554b6ae4/headera28215e7でcache有/無の新7件が各合格、直接旧16件も合格。原215は通常NEG20/partial5、原125はNEG19/partial3となり、各Ring証明と別のown-anchor C cutが成立した。公開CのPAUSE/耐久/intent/RS/newfloorはhost時計とACKモデルで、実UI/Runtime/iPhoneのRSとは区別する。

以前の成功5件（17/9/7/4/17）は6112byte packet全体・checks・固定時刻欄・Sceneが同一。85e32での各1回の正常分類と、最終6127への新19/20検査限定のsource差分を結び、旧COMPLETE先/新coverage未呼出を確認した。共用snapshot copyの追加はあり、全追加cost0とは主張しない。

a084の全3alias確認は同機Linuxで新uncached約96〜97msとなったため、同画像/sprite/整数座標のboundを呼出内だけ再利用した。全52839訪問の順序・全bound double bits・全packetは同じ、実計算22497/再利用30342。約62ms、最終別sample63〜72msだった。元source150ms/worker100ms/D/Pは保持し、iPhone速度をこの数値で代用しない。

配布前の追加反例で、bbox内先頭の小SIGN誤選択、床端確認前に全alias対象を調べない順序、tailの算術前bounds・非選択aliasのdomain・word数値整合を修正した。元失敗attempt/UBSan Red/改ざんaccept→rejectを保存し、既assertを維持した。これらはTEST121草案での検出で、元TEST120の実機再発数へ加算しない。

商品・最終selectorも独立レビューP0/P1なしで閉鎖した。公式選択はhost88（native60＋cap6＋package8＋selector14）、実Py39 75、fixture import/source binding48。未確定時の実行拒否とGit/source pinを保持し、Goodsのfile COREとaliasを封印済みRing.cへ結ぶ。旧119/120 runner全bytesとmetadata6先頭を保持した。

G2適用・封印は37 native中5変更（RPC/Controller/Nav/Ring.c/header）・32保持・追加0。API1.98.16/native_v15/POD/profile3、G1とR12全40を保持する。実CI/IPA/compiler/全Mach-O・完全sourceの確認は次工程で、この時点では未実施。

Runtime/queue/dispatch境界は変更しないため、新たな全Runtime worldやMacケースを既定にしない。変更したnativeの標準iOSビルド、seal・完全source・実compiler・全Mach-O・配布物同一性は別工程で行う。前回のMac成功を今回の新しい成功として数えない。実機の商品到達・連続周回・毎拍/速度・未知配置の受入は、次の利用者テストまで未確認。


## 配布前の実CIと実IPA

製品CODE `457478627d91136c3ff482f08b9a65314671b41e`、標準device CI270/run45566129079が合格。公式host88・実CPython3.9.25の75件は全件failure/error/skip/expected failure0。新Mac Runtimeは0で、前回のMac結果を今回の合格へ転用していない。

元3artifactのGH必須digest/size/CRC、CODE全1215Git blob、37native・5変更32保持・追加0、実iOS compiler/RSP/profileと全9MachO/fixture除外を、read-only5項目でattempt1合格。CODE flat source SHA2b66797b4aa60347687413e6148d33d9782d35da61e8c0f8ffed2df5591dd9dc。IPA18,493,552B、SHA `671bb82f1d14c732e668b7ecd7a7876e381cae0aa2af4d59551bec80cd620d97`。原helper/source/入力/assetは保持した。

[固定IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test121-build270/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test121-build270/source.zip)・[SHA表](https://github.com/shuhei0720/necrogold-automation/releases/download/test121-build270/SHA256SUMS.txt)。公開用SOURCEはCODEから文書4件だけを更新し、公式ZIP全Git bytes/CRC/同nativeと固定3assetの匿名全GETを公開工程で確認する。検証済みIPAを再ビルドせず保存する。

次は通常1-1ポーズから初回RS→通路候補/金壁→商店→全3商品確認→対象なしの正常判定/耐久/RS→次周回を依頼する。対象候補を保持し、回収完了まで待って全runtime/test-121 run/campaign ZIPを返却してもらう。iPhone到達率・毎拍/速度と元実機再発数の未確認を維持する。
