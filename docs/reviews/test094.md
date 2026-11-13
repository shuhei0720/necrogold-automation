# TEST094 受領・実装・検証

2026-11-13（日本時間）。実装中・未配布。iPhone受入は未確認。[計画](../plans/test094-native-goods-cycle.md)・[Nav限定](../plans/test094-shadow-passage.md)・[修正表](../fix-records.md)。

## 093の受領

3 ZIP/60 PNG/14,057,803 ZIP bytes。CRC、サイズ/SHA、strict load、certificate、canonical sidecar、登録集合を照合し全回収を確認した。実順は4de4→ee2a→70cd（添付順と区別）。4de4はgoods/6 moves/8 inputs/5 restart/14.732秒、ee2aはgoods/6 moves/7 inputs/1 restart/9.297秒、70cdはlimit/0 move/12 restart/20.456秒。goods完了は視覚条件であり、最終入力ACKを追加の実変位へ読み替えない。

4de4のauthority326はコンパス/スピア/あかるいトーチ、ee2aのauthority151はトーチ/ブラストヘルム/閉じた宝箱。旧判定は実施済みでtarget/candidate一致未確認、対象なし確定ではない。151の宝箱を当初の独立目視でarmourと推測した記録は訂正し、最新ユーザー指示によりclosed containerの正の識別だけを対象外へする。原156の通路候補は70cdに属する。

## 設計・独立レビュー

最初の設計/網羅/安全重点レビューで、coverageの具体predicate不足P0、PARTIAL再開/API互換・PNG同一性/回復/通知のP1を具体化した。新inputの作成は新profileに限定し、実データ校正とcallback検証を配布条件へ残した。

実装の独立static reviewでP0なし、P1としてSEARCH restartの誤接続、初期画像保持profile漏れ、次floor goods制限、full template/宝箱の範囲不一致、UNKNOWN/frozenの診断拒否、回復status/未解決intent、journal二重rename中断、無圧縮ZIP、壊れたledger反復、不正rangeの全体poisonを検出・修正した。静的確認と意味assertの実行を区別する。

元のSIGN component二点/SHOP全文一つ/独立merchant/全3品のname+icon+price/endcap/独立余剰列挙の組合せは有限CadenceJP1-1 layoutの証明として独立レビュー済み。全物理板の黒い外周、屋根、店全体は不要。追加のframe再構成が失敗しても元の有効branchを取り消さない。原326は元pairも不成立でunknownを維持し、期待へ閾値を合わせない。

## 現在の証拠

- 新clientの有効Red: 旧profile拒否1、開始前取消1。独立review後の3 assertionはfail3/errors0→実Python3.9の全30 Green。UNKNOWNの診断回収は入力再開を許可しない。
- Controller: 新25＋旧goods/restart/UNKNOWN5＋093入店6の36 Green。旧Status192/Event128/Scene23864 byte layoutを維持し、companion216を別ABIへ追加。合成Scene/時計であり実機到達率ではない。
- Nav: 新6＋関連19をO0/strictO2でGreen、原156は一度だけ現在Perceptionで校正。観測床3歩の仮説で、未知セルを変えない。
- native fast4: host分類326=43.9ms/151=24.1ms/309=10.8ms/225=27.2ms。既23 slotの安全上界が全て旧exact以上、対象309を保持した。iPhone/p95ではない。
- feature bank: named8品、closed chest2 poseを分離。閾値を先に固定し8×8交差・対象/別ring/2containerを校正。未知配置の正解率へ数えない。
- 原225の元RGBAと実Perceptionでcomplete coverage2、raw board mode1、唯一row、known IDs6/7/8・3価格・余剰0を確認。merchant .99984809/coverage1、SHOP全文1/1、両endcapが成立。aggregate有効化前のhost分類28.2msで、実機成功ではない。
- installer当初46、cycle専用のprofile3 binding Red→Green追加後47 Green。固定upstream+G1に実patch check。Swift実行・実compiler/IPA/配布物・完全sourceは次工程で結果を追記する。

## 未受入・残事項

iPhoneの到達率、native判定p95/人との比較、陰性→次の商店の一連動作、稀な対象の未知精度・長期耐久は未受入。bank外/原326・151のlayout不足は保持する。遅延した有効positive証拠は保存・追加入力0だが専用通知は未実装P1。session/回復ledger各128件の保持上限と自動整理なしはP2。全画像の照合を省いて通常完了にしない。


## CI161と限定した追加修正

code5d1b9fbb828bf4d9fc28f450e352b535638a751a/run43379010666/build161。host新95＋関連36＋selector5の136件は成功。Macの実API owner/schemaと実FS spool/故障mutation/全pixel stored PNGは成功した。ExportはSwift compile後のlinkでng2_orient_rgba不足となり停止、Runtime/IPAは未実行。試験runnerに実Perception objectを追加し、製品の意味Redとは扱わない。独立Mac4検査は、一件の失敗でも残る検査を走らせ、どれか失敗ならIPAへ進まない条件へ変更した。

追加読取で、開始前の通知拒否/準備拒否後もlocal journalを回収扱いし、未開始UUIDを永久保持する接続不足を発見した。認証済み専用-32095のdefinitive-not-startedだけを未開始へ戻し、次の明示実行で同UUIDを使う。通信不明/不正なerror形はUNKNOWNのまま。実3.9で意味Red2→全33 Green、認証済み保存故障-32096はpendingとして再試行しないRed1→Greenも含む。

SEARCH restart直後の最初のFLOORが商品可視の場合、goods latchが元restart baselineを失うP1を公開C APIで確認した。C新29＋旧5＋093入店6の40件を確認。元ACK/prefix/4秒とfingerprintを守って新floor creditを分け、変化不成立は分類/保持PAUSEだけ、再歩行/陰性restart0とする。初期header保存故障では同UUIDのread-only診断へ戻し、保存不能は固定エラーとして明示する。回復runの出版ACKを、同UUIDの停止済みcurrent gateへも反映する。Runtime新11＋旧3 fixtureは次のMac CIで実行し、未実施を成功にしない。

遅延結果のterminal保存と制御採用を表示側でも区別した。terminal単独の判定を未実施とせず、同job/captureを重複集計しない。未採用negativeを対象なし確定として表示しない有効Red1→実Python3.9の全34 Green。画像保存完了とinput4/frozenの動作成功を区別する。

実行済UNKNOWNと実worker処理中を専用回収statusで区別した。全worker/lease/capture/main/save drain後だけmanifestを許可し、input4/frozen/global poisonは保持する。terminal/drain後はpositive通知優先の一度だけ終了通知を出し、陰性周回の途中では終了通知を出さない。実failed-fastTap・回収ACK後の新開始拒否までをMac fixtureで確認する。
