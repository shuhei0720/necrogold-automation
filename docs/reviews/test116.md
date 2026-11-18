# TEST116の検証記録

2026-11-18（日本時間）。実機改善と速度は未確認。[全体計画](../plans/test116-device-failures.md)・[商店](../plans/test116-shop-continuation.md)・[連続化](../plans/test116-continuous-campaign.md)・[修正表](../fix-records.md)。

## 実機資料と成功の確認

TEST115の7ZIPは3campaign/4固有run。96PNG/110記録をCRC/path/bytes/SHA/原RGBA/寸法/時刻/連鎖/manifestまで照合し、同梱3ZIPは別添と全bytes一致した。受領の不足はない。rawと詳細証跡はGit外。

e0b8は3商品の完全陰性を正常分類45.157msで採用し、checkpoint→実RS16→新床159/160まで成功。PAUSE17/161は旧112の意図的な予算handoffであり、利用者の操作や不明なポーズと断定しない。次134e受理まで端末時計84.306183209秒。回収/検証/ZIP/公開の逐次待機を新opt-inでは周回中に挟まない。回収自体が高速化したとの証明ではない。

## 商店・観測口の限定変更

0084は静止credit後のPARTIAL移行呼出漏れ、36b6は115移行後の逆top投影、134eは早期FULL時に保留された元ACKの後続通常unitを独立DATAへ結べない境界。原画像を使う校正と、未来の手続き的な一回UP/全商品/正常陰性/保存RSを区別する。

Navは旧9c872fdで同一新6methodが41assert失敗/error0、変更後新6/直接旧68が成功。原25のScene不変・mask0→8、既床5歩だけで観測位置へ進み未知床へ入らない。原25は調整に使った既知校正で、未知評価や金壁露出成功と称さない。

商店は旧Cへの指定Redを保存した。新8＋旧33の41method試行では、追加trace検査の未定義便宜getterによるerrors4があった。意味assertや製品の失敗ではないが、41一括Greenとは記録しない。assertを残して実C getterへ接続し、同じ凍結C3596edf6の該当1method/4正例を再確認した。新8と旧33の閉鎖証跡を合成し、独立レビューはC3596edf6/Nav aa284ed0に対してP0/P1/P2=0。新continuousとの結合は別途確認する。

## 連続化の設計確認

設計R1のP0=0/P1=2/P2=1を改訂。successor activation0、正常陰性PAUSE後/RS前の容量・UUID予約、root絶対期限のC/最終実時計結合を明文化し、R2(plan SHA3ef7eb0d)のP0/P1/P2=0。設計合格は実装や実機の合格ではない。

新Cは旧enable/yield/permit/tickを保つbefore adapterで追加PAUSEを観測する意味Redを保存後、新6＋旧yield17の23methodを確認。元16/12/45/180、旧modeと旧handoffの意味を維持し、新しいC companionと閉modeだけを追加する。最終native/ABI/配布同一性は後続工程。

## 実Macの実装前Spool試験

CODE637e6efe14b8c08b1597b53130b7ab62740b0373、CI239/run44248770905。旧Spool074d76fc732a2287d14d8dd11256ac4d63462974556006b518f52ee66eefe84fを固定し、実Swift6.3.3/macOS26でコンパイルエラー0。次の3つはそれぞれreturn1、指定FAILちょうど1で一致した。

- 他slotの残予約を現在slotのwriteが食う。
- 17個目の未公開slotを受理する。
- continuation seal後に制御原画を追記する。

新API署名を旧独立Spool/汎用recordへ接続するtest-only adapterであり、旧115が未実装の新continuous modeを実機に公開していた証明ではない。原本bodyは変更せず、環境/compile失敗をRedに数えない。host/Python39/Runtime/IPAはこのlaneでは実行していない。

artifact14402872066・16,202bytes・SHA9971e751598e3451c715c2d80dcac9b80fa4a3d3b20908cd0df937da184f36fdを全取得しCRC/path/固定source/fixture/compiler/結果を照合した。Green実装のFS保存・正常export・fault・復旧とRuntime結合は次工程。

## 実Macの追加Redと途中の失敗

CI240は固定旧Runtime e655aa10を実Swiftでコンパイルし、新flagを-32602で拒否する指定assertion Redを1件確認。新APIの未実装を示すもので、旧115に連続運転があった証明ではない。SpoolはCI241でPNG alias/回復slot、CI243で部分headerのstorage cohort反例を追加し、同じ旧074dの6指定assertion Redを確認した。原本の破損headerを修復して入力権限を復元する対策は採らない。

CI242は新Runtimeのstatic/instance呼出10件のコンパイル失敗で、意味Redではない。修正後のCI244はコンパイル成功・new_mode成功。normal_chainは正常Ring分類→実RS→新UUID/新fit/実MOVE→両child終端まで進み、最後の公開確認 cycle094_publication_ack で失敗した。配布成功に数えない。非current回復objectの解放と、同じpredicateを直後に再評価する既fixtureの境界を調査し、有限history64内の小さな公開ACK/receiptだけを保持する。全原画をRAMへ残す対策は採らない。

## 回収・障害診断の限定追加

新clientはlive中に原画exportをせず、停止・全drain後に各childを順序通り全照合する。入力不明・元header書込み失敗でC終端のない最終attemptは、親の耐久予約/linkと実artifact inventoryへ結合した診断として回収する。gameplay complete/verifiedはfalse・入力4/frozenを保持し、診断回収完了と区別する。未commitのopaque bytesは端末に保持し、転送対象はmanifest filesと名前/bytes/SHA inventory。全opaque bytesを転送済みとは報告しない。閉じた回収後も同call内の自動startは0で、次の明示実行で改めて事前確認する。

実CPython3.9.25で新client30＋診断10の40methodを確認し、独立R6はP0/P1/P2=0。旧共有5filesはTEST115と同bytesを維持した。ホスト単体と実端末の転送速度・ゲーム受入を区別する。

## 最終Spoolと関連単体

CI245はfixtureのclock重複宣言1件のコンパイル失敗で、Red/Greenには数えない。CI246は中間bbfaddの16ケースが通ったが、active一時予約を別ledgerの実usage refreshが消せる追加境界があり、最終結果へ流用しない。固定16ケース内にその割込みを追加した242cdabf/fixtured8611d6dをCI247(run44263970301/CODE4f3e2bc)で確認し、旧074dの指定7assertion Redと現16全Green・コンパイルエラー0が同fixtureで成立した。各atomic partを開く前に同slotのtemp2MiBと残予約を検査し、原本を削除せず回復できる。実APIのreceipt-only公開、hash/owner破損、未commit orphan、低容量を含む。独立Spool R3残P0/P1/P2=0。実機未確認。

CI248の凍結CODE c1384e6・seal e4142f29、36native中6変更/30保持、新既存path集合も固定。CI248のhost99(89native＋selector10)/実CPython3.9.25の40が失敗/エラー/skip0で通過した。Spool247は4入力SHAと実installed sourceが同bytesであることを照合して再利用し、同じ試験を形式的に再実行しない。

読取専用crossbind toolの独立reviewはP0/P1=0/P2=1。basename receipt.jsonの除外が全階層へ広がるため、今回の実物は別途、root receiptだけを除いたexact inventory集合・nested未列挙receipt0を確認する。製品source/入力権限の不具合ではなく、tool修正は別のvalidation-only工程へ分離する。

## CI248の具体的な不合格

Runtime36のうち34ケースは指定assertを通過したが、successor_locked/ownerが不合格でIPA作成には進まなかった。正常Ring→実RS→無PAUSE次child/fit/MOVE、冪等ACKとcaptureThread実return境界はこのソースでGreenログを確認した。full passとは扱わない。

lockedはbootstrap main guard失効を取消へ結ばず、後のactivation待機がcancel/lockを見ない製品境界。ownerは認証無効中のcampaign_statusを正しく拒否していたためfixtureが実drainを観測できない境界であり、認証guardの不具合とは断定しない。実lease解放・UI0を先に確認し、認証を戻した後に元の全root terminal/drain/owner reasonを検査する。

この実行はwriter:checkpoint等のcolonを含む出力名のためGitHub artifact uploadも拒否された。全job logは取得・保持したが、実receipt/Spoolの完全artifact照合は未実施のまま残す。case名とassertを変えず保存pathだけ可逆な安全名へ結ぶ。次の同範囲実行で閉じる。

## 修正後CI249と実保存データ

CODE98e2d2d0a694a26571b47162799249816caa378b・seal87918ba8、run44267350921。ロック時のnewmode開始待機とowner試験の観測を限定修正し、独立した当incrementのP0/P1/P2=0を確認。元Auth拒否と旧modeは維持した。出力名は論理case/assertを変えず、8colon caseだけ可逆UTF-8 hexへ写し、map/全log SHAを実receiptへ結合した。

修正後はhost99・実CPython3.9.25の40・実Mac Runtime新35＋保持時計1の36が全合格、コンパイルエラー/意味assertの失敗/skipは0。Runtime36の実log/map/source/compilerと全43child exportを読取り照合し、815記録RPCと実Spool、600原RGBAと600PNGの復号bytes、43耐久公開ACK/3identity/同再送ACKが一致。公開後pending0。owner/locked/Thread実returnと旧時計7条件/新root時計4条件を保持し、source150ms/worker100msや入力予算は増やしていない。Spool247は同じ4入力SHAで再利用した。

通常normal_chainは正常Ring5job・assessment overrideなし、実RS1→新UUID/新fit/実MOVE1、初回activation1で追加activationなし。PAUSE/RESUMEは通常初回/商品の各1で、RS後のhandoff命令は0。正常な陰性だけが継続し、新floorの候補/未知や新入力不明を旧陰性で上書きしない。これらは手続き的なMac worldであり、実ゲーム速度の受入ではない。

実Macの通常2childを実CPython3.9.25へ渡し、48PNG/元RGBAと58記録、root/clock/耐久seal/正常陰性→RSを既verify_evidence→verify_childで一度照合した。入力fieldの補修・再分類・RPCは0。native fixtureの模擬a*64 ZIP申告を実ZIP受入とは認定しない。P2の一覧境界は別々のexactset検査で補完し、root receiptだけを除外した218filesの欠落/余分/未列挙nested receiptは0。

IPAは実iOSビルド成功、18,442,194bytes・SHA551270d19f99a56dbff09b7d756602f3b55edaa78513a2abb48df6050489658d、main bundle build249/minOS16.0を確認した。package/validation/hostの全ZIP SHA/CRC/path/symlinkを確認し、validationは3,104files/1,043,468,413bytes。全source CODE ZIPは1,109filesをGit blobへ全照合した。読取照合のための追加compile/意味試験/分類は行っていない。

## 未完了

配布sourceのdocs更新・固定公開と実機受入は未完了。途中の件数や単体成功で実機不合格を完了扱いしない。

## 次の実機受入

新IPAでLoopCtrlを更新し、完全終了・再起動→Start Server。通常オールゾーン1-1のポーズから、展開したsource内で `sh test_116.sh --until-target` を実行する。金壁が見える配置へ手動で揃える依頼はしない。

商品が2個だけ見える上部扉の配置で、全商品が見える位置へ進むこと、正常な対象なし判定から実RSと次フロアの探索へ回収待ちなしで進むこと、対象/候補では保持・通知することを確認する。回数/48分/容量上限は有限停止として区別する。終了後の全周回収が終わるまで原本を保持し、runtime内のTEST116 campaign ZIPと各run ZIPを分けて返却する。実機の改善・速度はこの受入まで未確認である。

## IPA同一性の最終読取り確認

CI由来/package/host/Runtime/Spool/Mach-O/compiler/clientの8gateを実物へ結び、全合格。全9Mach-Oの既存/新host hook不在、新cap/startflag/C API、実iOS C8/Swift5とRSP6/PBX/rawargsを照合した。crossbinding SHA1e37d9679cd5fe617268883b75b99e68e93c4bd93af9a09c7b44b6adde76978d、実3.9別証跡SHA231c3c7b2c6dee4b6e814b569dd53c15dc73ae2661772f0bce5b992387c129ea。私的reader初回はGitHub生jobs形式の読取り型で失敗し、全jobのrun_id/head_sha/結論を検証する型adapterだけを加えた履歴を保持した。製品/input/元artifactは不変。最終8gate読取りで追加compile/意味試験/再分類は0、iPhone受入は未実施。
