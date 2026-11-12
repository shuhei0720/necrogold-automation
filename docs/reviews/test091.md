# TEST090受領・TEST091の検証

2026-11-13（日本時間）。基準c9e087050f5d6c7c30d8385014ea0909e534c963。[計画](../plans/test091-device-stops.md)・[修正記録](../fix-records.md)。実機改善は未確認。実090の全商品確認は0/3であり、扉を開けたことを商品確認成功にしない。

## 受領と原因

実時刻順c4109c61/3c04c7df/ec411d6fの3ZIP、各20枚/計60原PNGをCRC/size/SHA、native strict load、出版certificate、canonical sidecar、登録file集合へ照合。全回収完了。生ZIP/原PNG/Scene/ログはGit外に保持する。

| 実順 | 入力/移動/restart | 最後の動作 | 根拠と限界 |
| --- | --- | --- | --- |
| 1 | 0/0/6 | LEFT14を送る前にSCREEN拒否 | source174は正常CLEAR候補。最初拒否175は未保持。後187のUNKNOWNを175の代用にしない。確定原因は未送信初歩のScene拒否まで |
| 2 | 3/2/8 | UP20のACK後8UNKNOWN | source308→原326は旧STONE2/非共線DIRT17を保つ実UP1。旧17段UNKNOWN。raw左右の左帯がrunnerでINF、blur8px競合の差不足。090のHUD喪失は0で適用外。316〜322未収録の初回評価まで再現したとはしない |
| 3 | 7/6/2 | UP17で木扉を開けて8UNKNOWN | source166のDOOR→原184のFLOOR、同gold bracket/unique zero。rawzero .45546、detail355/不一致37、gradient223で旧証明不足。薄鉄型の認識失敗とは別。原184はPARTIALのままで3商品不可視 |

過去表とコードを修正前に照合。FR-074-FADE/FR-076待機は初歩票確定後かつlead0の今回条件を覆わない。FR-074/082の通路unit証明とFR-072/074の開通証明に未対応条件が継続する。既対策を消した回帰とは断定せず、未対応だった条件を新証明で分ける。修正後の実機結果は未確認。

## のろいのゆびわ

実3原184はユーザー申告と独立目視で対象名/絵を確認した。全3商品は見えていない。native goods0で正式sidecarはsources=[]/no_authority、個別matcherは未呼出。

調整前に原184/SHA/人ラベル/現feature・ELF・sourceを凍結し、公開classifierを実CPython3.9/QEMUで一回だけ診断評価した。結果はunknown/no_complete_row・rows=[]、icon/name未実行。開発単発0.062秒はiSH速度の受入ではない。画像はこの調整前診断として保存し、今後使って調整した場合に未知陽性へ再利用しない。今回classifier/kernel/閾値/authorityは変更せず、対象が出るまでの周回は依頼しない。

## 実装と確認の範囲

初歩は確実未送信票だけの有限再観測、通路は旧全STONEを保つ独立unit証明、木扉はblur絶対品質と既raw/detail/unique bracketを組み合わせた開通zero証明を追加する。旧17段・既閾値・UNKNOWN無再送・元期限/予算を保持する。初歩拒否rawはv2の余剰1pinだけを使用し旧critical7/map12を削らない。

新規/関連の意味試験と独立差分レビュー、必要なIPA/source同一性確認は実施結果を追記する。未来の進入後画像/実ゲーム応答は作らず、単体/校正/CIを実機到達成功と呼ばない。

作者段階では新通路4/開通5/初歩8がGreen。初歩は最初6methodの有効assertion Redを先行確認し、追加の交互gold負例は新2枚を混ぜない確認として分ける。旧候補の口がUNKNOWNのままmask0になる例も有効Red→Greenで補強し、旧074の確かな閉塞条件を維持した。通路の競合fixtureがSTONE/DIRTを自己矛盾させた1件は、二translationという期待を保った作図訂正後に最終4method全Green、失敗ログも保持した。既assert削除/skipで通していない。

当時のController/Navを含む8sourceを凍結して共用strict O2 libraryを1回compileし、通路/開通の単体と原2pair校正へ再利用した。source308→326はUP1、166→184はDOOR_OPENED/移動0。両pairの旧17段はUNKNOWNのまま。Navの新2block/呼出2行を逆除去すると旧全文bytesと一致する。後のController追加補強はNav/Perception不変を照合して校正を結合し、原2pairの再分類/再compileは行わない。未保持の前段観測や未来の店内可視を復元したとは呼ばない。

Runtimeは新HOST fixture/hashを製品編集前に固定した。開発機にSwiftがなく、実意味Redを製品編集より先に実行したとはしない。最終Macの同じ限定jobで固定c9 Runtimeへ有効assertion Red、現Runtimeへ新保持境界/旧081関連Greenを各1回実行し、旧全Runtime故障/worldは選ばない。実行結果は以下へ別に追記する。

## 独立差分レビュー

同一担当が計画・Controller/Nav/Runtime・新単体/限定Runtime fixture・配布selectorを静的に1回レビュー。P0/P1なし。初歩回復はlevel入力0・旧ID退役・独立2観測・元期限/共用上限を保持し、旧候補口UNKNOWNを陰性へ変換しない。Navは旧17段を変更せずunit/開通zeroの別AND証明を追加し、開扉を歩数/商品確認へ代用しない。Runtimeは原点/lead未確認の未送信拒否を既余剰1pinへ残す診断のみで、累積input不変をlevel入力0と呼ばない。

作者の有効Red/Greenとsource/fixture receiptを読み、fixture構築衝突の修正後も公開Red assertion/競合拒否が維持されることを確認。独立compile/意味試験/原画分類の再実行は0。原184は対象名/iconを独立目視したが全商品不可視で、正式matcher未呼出と区別。拒否175の原因predicateは未確定のまま。P2の診断scope/未確定mask表現は訂正済み。

レビュー時点でRuntimeのMac意味Red/Green・sealed host CI・IPA/source実物5gateは未実施。静的レビュー/単体/保存pair校正は、実機到達率・毎拍/人間速度・未知陽性精度の合格ではない。

## 最終CI・実物確認

製品code f355a1dd2c37ecdb04fafa0aa853b0e26f71c0ac、標準Mac/Ubuntuのdevice run43265221701/build152。現sealed sourceで新17＋関連17＋selector4の38methods/11scopeが全Green。Macは固定c9 Runtimeの有効Red1と現Runtimeの新5＋不変081関連6が成功し、61拒否条件/原metadata/20pin/10MiB・旧4MiBを確認した。Swift不在による事前意味Redの時系列制限は上記のまま維持する。全Runtime故障/worldは未実行。

実artifact3件をAPI id/run/head/size/digestへ結合し全CRC/安全path/重複0を確認。IPA0.3.4/build152/min16は17,636,448B/SHA `cfb5cbe037bf2b8bbfaefd41d81010d65e041381b627e873f58276874a04973e`。22seal中Controller/Nav/Runtime3変更、残19と全40R12不変。旧293＋新49の342禁止markerが全9Mach-Oで不在。実C4/Swift5/RSP6・PBX/引数/rawlog/sourcehashを同じ実compile profileへ結合。build codeの完全731sourceも全tracked blob/CRC一致。

5gate readerは日本語NUL列挙/旧293markerを維持し、Macの実selected main/差込HOSTをsourceから再構成して結合した。package/host/retained/macho/compileは各1回・計5attempt全PASS、追加compile/意味/分類0。前回Runtime全体証拠は旧c9のbaselineとしてのみ使用し、今回の実行成功へ読み替えない。同じ独立担当が今回receiptの結合を確認し、P0/P1なし・配布工程GOとした。独立したgate再実行/compile/意味/分類は0。

closingはstatus/本review/実機台帳/修正表の4文書だけ。製品/試験/IPAはbuild codeのまま保持し、最終完全sourceの全blob/CRCを照合する。固定Release test091-build152へIPA/source/SHAを保存し、匿名全GET/actualtagを確認して返す。実機改善は未確認で、一連4回と全run ZIPを依頼する。
