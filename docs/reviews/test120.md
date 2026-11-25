# TEST120: TEST119の停止4件と左上候補の修正

2026-11-25（日本時間）。[計画](../plans/test120-device-failures.md)・[修正表](../fix-records.md)。基準はTEST119/build266、製品CODE617fc248・保存HEAD1d9a0a4。製品実装と限定検証を進行中で、新IPA・実機受入は未完了。

## 実機原本と成功の確認

11ZIP/7run/4campaign・170PNG/203記録を全照合し、欠損はない。全ZIPのCRC/SHA/安全で一意なpath、全PNGのdecode/896×414 RGBA hash、metadata/stable prefix/記録鎖、escrow/campaignと内包lastZIP同bytesを確認した。原本・画像・SceneはGit外に保持する。

実順は723、1a358→ca2、6423→c41、aa8→2d1。成功した3rootはpolicy9/source173、policy7/source335、policy4/layout3/source235で正常完全陰性→C採用→durable→実RS→新floor→同Runtime child開始を確認した。policy7のunmatched_items=2、policy4の1は正式な成功条件なので、一律0へ狭めない。商品名なしの成功も保持する。後でresetされたassessment null/adopted falseは判定失敗ではない。

aa8は119の同列白点/独立低価格修正が実機で効いた例。同じ原画をexact263/119の通常producerへ通すと、旧UNKNOWN/PRICE64から119の完全陰性/cert1へ変わる。前2成功の通常packetは旧新全bytes一致。旧TEST118/3f policy17の成功も保持対象とする。これらの実RS成功と、その後のchild停止は別に評価する。

## 失敗の原因と限定した対策

| 原本 | 確認した原因 | 修正する境界 |
| --- | --- | --- |
| 723 | 元323→330はUNKNOWN、採用済み329→330は通常strict零。同じDOWNでもtargetが変わり、既stationary waitのsame_choiceが元P/W内でSCREEN | 採用済みの直前proofと現在の直接零を要求する、一回のDATA観測への引継ぎ。旧UNKNOWNを移動/零にせず、独立proof後だけ未来の新IDを予約 |
| ca2 | LEFT1実MOVED後、通常67→69零のままGOLD判断が旧UPからLEFTへ変化。旧通路FLOOR→DIRT等が既壁露出/開口証明外 | 未開始UPの撤回と有限route観測。元全GOLD/保護/正床/owner/P/Wと一回性を保持 |
| c41 | 通常122→123零。床1セル先の後に新DOOR・bracket GOLDが露出し、遠方DIRT→FLOORも併発。既証明は床2セルと旧DIRT扉を要求 | 別の閉じた近いbracket証明。既FRESHと同physical beat/epoch/元期限を使い、開扉や変位をcreditしない |
| 2d1 | 開扉後の2商品PARTIAL/UNKNOWNは正しい。LEFT22はbegin承認後、実送信の最終guardで元Dを50,136ns超過。同pairの通常Motionがbeginで重複 | 予約後の独立observeで得た通常零をC所有の全Scene/command/metadata/epochへ固定し、同一時だけ再利用。cheap static/route・元10ms・最終実時計guardは毎回維持 |
| aa8 capture62 | ユーザー赤丸は左上。旧新Scene全bytes同一、CLEAR/mask0。既fringeの外cap FLOOR条件に対し原画はDIRT、外側UNKNOWN | 全屋根/左壁/正内床を要求するmask0専用witnessを既bit5へ追加。DIRT扉/UNKNOWN外床、旧chooserと既nonzero maskを保持 |

2d1のbegin記録からsendNowまで7.466542msは、Cだけでなくpreparation/epoch getter・owner/lock等を含む区間。実機の個別内訳は未記録で、Linuxの通常Motion約4.5msをiPhone速度としない。staticの戻り値0はvalidation成功でありbool falseではない。原source/親P/worker100ms/入力10msは延長しない。

原画像と同じ拒否guardを結ぶ限定cutを使う。未保存private modelを宣言値で補ったcutや公開手続き画像は完全実機再生ではなく、存在しない未来画像を原本へ補完しない。candidate優先、全商品可視、未知入力無再送、既RS継承は維持する。

## 実装・検証の現在位置

左上Navは旧119で新6件中5件のassertion Red→最小修正後Green、直接旧39件を含む45件が合格。170原画で通常PerceptionのScene全bytes差0・書換え0、旧nonzero2画像のmaskも同一、指摘capture62だけ0→32となる。旧Navの全既存bytesとchooserを保持した独立最終差分レビューはP0/P1なし。未知画像や将来の商品到達を合格と扱わない。

client/capはTEST120を別namespaceと追加capへ登録し、旧118/119 helper/metadata・API/native_v15/profile3、初回RS/同root回復/連続周回を保持。独立レビューで新120タグのblock-comment誤認を検出し、新120だけdelimiter拒否へ修正した。既6method内の6反例でassertion Red→Green、旧metadata11件も合格。最終限定レビューはP0/P1なし。selector/workflow・実IPAは別に確認する。

PARTIALはexact119で正式6件中4 assertion Red→最小修正後6件Green、直接旧13件も合格。独立owned差分レビューはP0/P1なし。原287→300の同許可predicateは旧通常Motion1回→新0回、Linux診断9回の中央値4.447ms→0.030msだが、full begin/Runtime/実機費用とは区別する。既static/comparison・陰性証明/耐久RS・119 enteredの各関数は旧全bytesを保持した。route3境界は正式新9件・直接関連22件が最終CでGreen。独立combinedレビューが見つけた元Pのvisual/schedule継承漏れは、新route限定2行と8境界subcaseで12 assertion Red→Greenにし、正常P等号までのunitとP後credit拒否を分けた。最終C cf471e36のレビューはP0/P1なし。PARTIAL Cbeginと元Runtimeの間を変更するため、その境界だけMac1case・normal/post-guard-lateの2短subrunを計画する。旧全Runtime world/故障集合を今回の合格数へ加えない。

fresh G1から最終G2をseal/applyし、37native中Controller/Nav/RPCだけの3変更・34保持、追加0、旧118/119と新120cap、API/native_v15/profile3同一を照合した。Runtime/Perception/Ring/ABI headerとcanonical15/R12全40/G1は保持する。これはprecommit source照合で、実iOS compiler/IPAの合格とは別である。

実compiler/全source/seal/9MachOと配布物、匿名取得まで照合した固定IPA・完全sourceを次の実機へ渡す。実機での商品到達率・停止解消・毎拍/実効速度・未知判定精度は新版結果まで未確認。

関連旧076のREADY/ISSUED未知化を一律SCREENとする1methodは、exact119でも同じ2subcase不合格だった。既assert/sourceを保持して今回CIから未選択とし、元W内の無入力OBSERVE復帰を明示する現117の3methodへ対応付けた。新規成功へ数えず、代替を含む直接関連22件で最終Cを確認した。

Mac5sourceの静的最終差分レビューもP0/P1なし。原Runtime/fakes本文を保持し、publicC/normal RGBA・Ringから実Runtime dispatch/main begin/post gateへ結ぶ。旧119 Cの同公開前奏はbegin成功でもMotion1回に対し新期待0のassertion Red。purevalidatorの正常2/拒否38、C fixtureの厳格compileは合格。これらはMac callback合格ではなく、Swift nested aliasの型検査と実10ms内のnormal/実post lateは標準GHAで確認する。
