# TEST077: TEST076受領と商品可視位置への継続

2026-11-11（日本時間）。baseline `d3e9bbde44ceb41dac43beaf818043c588cc3aab`、[計画](../plans/test077-shop-visibility.md)。raw/Scene/解析はGit外received076/test077-*。第三のログは未受領で原因未判定、必須回収や再実行を求めない。

## 受領と停止根拠

2ZIP/37原PNG（20/17）を全SHA/ZIP・PNG chunk CRC/896×414/manifest全offset・hash・cursor/prefix/active-report、実API16 validator・publicationへ照合。両PAUSE/resolved/terminal/drained、取得failure/timeoutなし。2はretained20/export17/4,159,984Bで4MiB内、保持省略を補わない。iSH status28回エラー/取消0、最大1.110秒。preflight server.buildは文字列時刻2026-11-11 04:27でCFBundleVersion122とは異なる型の値。

| 実順/run | ZIP bytes / SHA256 | restart | MOVED/方向入力 | 停止 |
| --- | --- | --- | --- | --- |
| 1/1f2371f7 | 3,329,857 / `36e76aa5a403428d2bb06b01a1eb3cfcdff5002eccf15916651f3b631b036b88` | 6 | 2/2 | screen |
| 2/013ca451 | 4,408,454 / `354f71baaa5a32d1a8919a9f8d47410720d389fbaea3fe09b12892b9678dc119` | 3 | 6/7 | screen |

全商品到達0/2。2は開扉1回だが商品は画面下側に未確認、開通を入店/全商品成功へ数えない。ユーザー報告第三回の開扉後停止は未検証でこの表に混ぜない。

1は実2LEFT後、pose(-2,0)・固定候補bit5/world口(-3,-2)に対する未送信cmd16/UP/source248→250。両CLEAR/GOODS_UNKNOWN、origin/next床・フル5 UP/reason10/target(-1,-2)/FLOORは同じだが、off-route(1,-1)FLOOR→DIRT、(2,1)DIRT→FLOOR、(3,1)FLOOR→DIRTで076待機の近傍材質拒否に当たった。motionはUNKNOWN、待機record0。C7.979875ms、終了NB−6.835326ms/D−16.835326msで期限超過ではない。247/249原画は未保持。

2はcmd17/LEFT/source212で実DOOR_OPENED、次cmd18/LEFT/source220→221が未送信SCREEN。pose(-4,-2)でまだ入口creditなし。両PARTIAL/同protected12・フル5 LEFT/reason5/target(-1,0)/FLOOR、strict BLOCKEDだが、遠方(-7,-1)DIRT→GOLD一点でsame_goldを拒否。generic validation7はFLOOR、validation8はGOLDなので混同しない。C終了D−91.921093msでlateではない。

同runの先行cmd11/ordinal4はgate D+11.907651msでtoo_late・未送信/LATE9へ確定し、次拍別IDcmd12/同ordinal4が実MOVED。076の未送信late回復は実際に成立しており、最終SCREENと分ける。

## 局所修正と証明範囲

製品はControllerのみ。通路待機だけ、実origin/nextと全保護/固定world/full5を保持するoff-route近傍palette差を許す。UNKNOWNはUNKNOWNのまま権限を捨てて待機し、元anchorへの後続独立strict0/PW/別IDが必要。shopの従来near拒否を保持する。

開扉ACK直後と実MOVED後入口validのPARTIAL床移動だけ、両3×3/全保護外のUNKNOWN/DIRT→遠方GOLD追加を同票へ許す。元GOLDと直前accepted GOLDを保持し、追加金の消失/shiftはmask0・非zeroの両方で一般refresh前に撤回。診断は実maskだけを記録する。元before/ticket全bytes/全期限/full5/strict0を維持し、閉扉/普通approach/UNKNOWN motion/新保護や商品を一般許可しない。既存の不変ITEM/保護が存在するだけでは拒否しない。商品VISIBLE優先と開通/実進入creditの分離を保持。

新public C単体2module各6method。旧076製品はcompile成功後40 assertion failures/error0/skip0の意味的Red、最小実装は12method Green/error0/skip0。全既存assert不変。新paletteのDOOR negative補足は該当1methodだけ追加確認。手続fixtureで同票bytes→NB begin→ACK/実MOVED→入口/次Navを検査し、未来の実画像/端末全状態を再現したと呼ばない。

独立1名が計画/最終差分を静的レビューし製品P0/P1なし。通路のみの差、元anchor/PW、PARTIALの二系統/金保持、mask0の撤回、商品/全保護・期限/ABI/閾値の維持を確認。DOOR補足も差分/既実行ログ確認で閉じ、残P0/P1/P2なし。レビュワーによる単体再実行はなし。無変更の共通owner/時計等は静的確認とし、全live admission/実機到達・毎拍・人超えの証明へ一般化しない。

製品Controller SHA `fca0e50f8e3b61d68c86e76476365f34a076b0795b7e50a759eb1186a226d416`。fresh G1→seal/applyで22中Controller1だけ変更、他21不変。Nav/Perception/Runtime/JSON/全header/ABI/API16cap14v15/G1/R12原40/閾値/元予算不変。

限定CIは新12+stationary076全8+shop071全5+gate069の静止/幾何2+商品同frame移動1+passage UNKNOWN無再送1+ABI1=Native30、selector3を合わせ33件。実sealed CORE canonical/bare依存と5client HEAD/4実callable、無変更旧4client bytesを固定。063/071/072/074/075/076/077 baseline env・BASELINE_NAVは空値も拒否。新Nativeの重複ローカル実行や無関係な全Runtime/world積み増しはしない。

原PNG由来Sceneの局所照合でも248→250はorigin/next/全保護/full5不変で新palette条件適合・motion UNKNOWN維持、220→221は実新Cのdistant_gold_growth=1・旧金保持・全保護材質/full5不変・strict BLOCKED0を確認。private world/model/clock/ownerは復元せず、未保持future proofやlive admissionを補わない。

限定CI・actual compiler/IPA/全source・固定Releaseの匿名全GETは実物完成後に追記する。新実機は未実施。
