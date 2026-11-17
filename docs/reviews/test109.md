# TEST109: TEST108実機失敗の受領・検証

2026-11-17（日本時間）。基準 `7fe34ff`。[計画](../plans/test109-device-failures.md)・[修正表](../fix-records.md)。今回の実機失敗を、旧108の補助試験合格で改善済みと扱わない。

## 受領と原因

6添付を3固有run/73 PNG/82記録/161論理ファイルへ照合。全CRC/安全path、campaign内ZIPの完全一致、native manifest/記録hashchain、896×414 RGBA hashが一致。原本・Scene・校正はGit外。単調時刻順は56b→a782→7853で利用者の3周に整合するが、明示周番号は記録にない。

| run | 正常判定と停止 | 確認した不足 |
| --- | --- | --- |
| 56b… | 開扉後source522はUNKNOWN/policy2/flags258、GOODS1でPAUSE32 | 3品の投影はあるが第三品直下UNKNOWN、片側SHOP faceも旧完全閾値未達。現在画像を陰性にできない。新108の開扉履歴/観測入口床は成立し、後続のpartial union left135<安全域143で観測一歩を拒否 |
| a782… | 開扉後入店せず、safe PARTIALが23job、元DでLATE9 | 原234→236/244→246は同じ完全LEFT判断/通常strict零。遠方UNKNOWN→DIRT/FLOOR等でROUTE10となり、分類・準備を反復。固定227→後続20枚と234→後続13枚でも直接通常strict零/同じITEM・全GOLD・保護・一歩近傍が成立 |
| 7853… | 原275/276はUNKNOWN/policy9/flags80、3非対象商品でも全被覆不成立 | 11白画素の非価格成分を第4価格として計数。別に左cap上半分だけの床palette不成立。PRICEとENDCAPを別々に直す必要がある |

3runで、開扉後の適格な対象なし採用から次周回へ進んだ証拠はない。ログのUNKNOWN保持は仕様通りだが、入店/検出の不足が継続している。原記録はIPA/buildの来歴を証明しておらず、未導入と推測しない。

候補は保存された全13開幕見送りsourceを通常nativeで確認し、実GOLD0/mask0だった。56b原323は観測口/屋根/下側壁・既床3歩を持つ別形状で、実PAUSE/RESTARTへ進んでいる。利用者の見逃し番号が未記載なので、323を利用者指定の箇所とは断定しない。

## 検証の範囲

原画像校正と手続き的なC契約試験を区別する。56b522後の同prefix原PNGは未保存で、保存済み532/533はPAUSE後の別prefix。後続の静止/入店成功は実機で未確認。a782最終246採用時点の残時間は短く、早い227からの固定比較と、未収録の実予約/実ゲーム応答を混同しない。7853は正常producerの全被覆とC採用/保存/次周回の接続を別々に確認する。

作者のRed/Green・直接関連、独立レビュー、最終選択CI/IPA/完全source/固定配布の実結果は、成立した時点で以下へ追記する。現在は未実施を合格扱いしない。新TEST109の実機到達率・未知精度・毎拍/人超え速度・耐久は未受入。

## 作者確認・原画像校正

- Cの遠方材質関係は、同方向開扉・外側の連続4GOLD・単一連続ITEM行/正確保護・原点/次床3×3・完全Decision・元anchorへの通常strict零を要求する。初期案の非公開one-use flagは元画像がなく値を証明できないため使わず、原で見える外壁支持に置き換えた。旧104の新ITEM再分類assertは保持。
- Cのpartial端ROIは正の直後開扉だけ。観測済みicon core・上下全範囲・現在可視のunionを保つ方向だけ許し、旧row/ITEM ROIとcx150のHUD拒否は不変。最終test bytesで遠方/端ROI各1methodが変更前Cに2assert失敗/error0。最終Cで新8+7・直接旧45の計60件が失敗/error/skip0。手続き画像/時刻で通常採用→別fresh画像→将来票→begin/ACK→unit MOVED、旧ID/候補/取消/元D/UNKNOWN無再送を確認した。
- 原227固定から後続228〜247の20比較は、通常Motion strict BLOCKED零・同完全判断・新static NONEとなる。中間pairへanchorを移していない。原522の通常UNKNOWNと実開扉履歴は新admission1。保存のない後続画像で入店成功とはしていない。
- Ringの価格支持は既有効価格と同じ18白画素以上。capの局所証明は既full25×25床とScene FLOORに加え、halfのtexture/90%可視率・scaled明画素/価格不在・赤基準の色度差3%以内・赤輝度比4/5〜5/4を要求。既policy9/11のみ、旧global/legacy/閉容器10は不変。価格だけ・capだけ・両方の変更前Red3method/5assert/error0から、新12と直接旧33が成功。最終testの独立した緑色度拒否subcaseも新12で成功した。
- 7853の**実採用job2の分類sourceは275/prefix14**。原checkpoint/terminalのcycle.capture_idとassessment_adopted=trueで確認し、276は後続のPAUSE資格sourceと区別した。新通常producerで275はNEGATIVE/COMPLETE/policy9/flags0/3価格・数値証明1、元Scene/ResultのC独立検査1。ホスト43.596msは元100ms worker予算内だがiPhone速度の証明ではない。原276は3%色度条件外でUNKNOWN/ENDCAP16を保持し、閾値を拡げていない。56b/a782の未観測は引き続きUNKNOWN。新公開producer→C採用/PAUSE/耐久保存/intent/RESTART ACK/新floorは手続き的な契約確認で、元runの実リスタート成功とはしない。
- Navは変更前1method/1assert失敗から新7/直接旧12がO0/strict O2で成功。原323の通常mask0→32、既chooserはLEFT/既床3歩/(-2,-1)、Scene不変。残り15保存PAUSE sourceの結果は不変。関数20行とbit5のORを除く全Nav bytes（Motion/chooser/旧guard含む）は基準と一致する。

## 独立レビュー・保全

独立担当review109は最終C `fc5ebd16b18a153b92130f395eaf164498903be3362f949a833666860f47e2b2`、Ring `d5946e2ca98e62577e9875c7a0216c6da10d9cfa507ddce3d0ca7af77179af4e`、Nav `a24b03cf66b5251f93c658201e09fe8205365022f93591bd3cf11c4dcc638e1b` と新4moduleを読取確認し、未解決P0/P1/P2各0。暫定の「276が実分類anchor」という指摘は原本のjob/capture/pause-sourceで検証して撤回した。276の正常UNKNOWNという境界は維持。レビュー担当の単体/native/CI/IPA/実機実行・編集は0。

固定upstreamの別試験用コピーへG1をhash照合して適用後、最終36 native sourceをseal/実適用した。manifest `2206cf69575a77e9a8be60c34c00e06a1a62f0c3336bafc5964bbd566820ca2a`、変更C/Ring/Nav3、他33とAPI/ABI/cap・Runtime/Raster/Perception/features/canonical15/ELF/G1/R12は不変。旧Runtime/Mac191は歴史証跡のまま。新Runtime/全故障/全合成worldの無関係な再実行は追加しない。

## 最終CIの選択

新34method/5class（4module）と直接旧90method/13classのproduct124、selector6の合計130method/19scopeを明示集合へ固定。新旧108runner/selectorは保持し、workflowは109の選択と既歴史Runtimeの実行除外条件だけ追加した。local selector6は失敗/error/skip0。空・重複・skip・失敗/環境errorを合格扱いしない。この確認は最終CI130件を実行済みという意味ではない。

同じ独立担当のrunner/selector/workflow補足読取レビューも未解決P0/P1/P2各0。明示124/18集合、共有108 helperの推移source binding、旧108保持、36中3変更/33保持、Runtime歴史証跡と現在実行の分離を確認した。補足レビューでの実行0。

test_109.sh/necroprobe.test109は108から番号だけ変更。sh構文、Python3.9 AST、API軽量checkは成功。クライアント本体・回収/永続化・通信は不変。source/IPAの最終CIと実物照合・固定公開は次工程。

## 最終CIと実物照合

CODE `270773b8def30876aa70078338c716a83fa83406` の[CI208](https://github.com/shuhei0720/necrogold-automation/actions/runs/44002618293)は現在sourceの130method/19scopeが失敗/error/skip/expected failure0で成功し、同source未署名IPAを作成した。旧Runtime42f2/Mac191は歴史証跡のまま、現在callbackの再実行へ昇格していない。

同runの3artifactをGitHub metadataの全bytes/digest/CRC/pathへ照合し、CODE完全source977 filesの全tracked bytes/CRC/pathをGitへ照合した。実package/host/retained/Mach-O/compileの5gateを各1回、計5attemptで全成功。実compiler/36source/9 Mach-O・旧feature/ELF/G1/R12・実行method集合・作者の真のRed/Greenへ結合した。検証器の追加native/分類/compiler実行は0。

IPAは18,066,363 bytes、SHA256 `3bf5ffca98a68766edbe50a1a0753226aeddb9a7b34c115a099c6798c2f9d21d`。bundle `top.ebato.loopctrl` / version0.3.4 / build208 / min iOS16.0。CODE完全sourceは9,386,824 bytes、SHA256 `c8c8a96d7583e8cbd9d0d8adf53713ea2c05a6b57499863eed152795c0695026`。固定Release `test109-build208` への公開は次工程。status/review/fix-recordsの閉じ文書3件だけを加えたclosing sourceを配布し、native/試験の不変を照合する。

実機改善は未確認。次はメインiPhone11で新IPA更新・完全終了/再起動/Start Server、通常VPN/通知、日本版ケイデンス・通常オールゾーン1-1ポーズから `test_109.sh --until-target`。候補探索→開扉後入店→全3商品確認→対象なし次周回を確認し、全画像/ZIPの保存・照合終了後の表示campaign ZIPと状態を受領する。全run原本を保持し、回収済みrunの追加回収だけの再実行を依頼しない。
