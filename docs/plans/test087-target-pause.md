# TEST087: 対象指輪のローカル判定と通路停止

2026-11-12（日本時間）。基準 `6a937163ac87dde049887eaf56a65f9dda757911`、TEST086/build146。実機主軸・品質維持・時間上限なし。新ユーザー指示で「のろいのゆびわ」判定を追加。同じ独立担当1名が設計/最終差分/実物を確認する。native入力権限/API/ABI/Runtimeは拡張しない方針。

## 1. 背景と受領

実順76e862cd/f7fae670/1b3efc43/c9bca989。4ZIP/80PNG・19,260,301画像Bを全CRC/SHA/PIL/API16閉schema/client_load/prefix/cursor/実publication gateへ照合、4回収完了/terminal/drained/paused。見送り判断source21/21保持、全取得画像保存ではない。実1〜3は全3商品可視、実3中央の対象名/茶灰ring/価格250をroot/監査/独立担当が視認。実1の別ringは「ゆうきのゆびわ」で近いnegative。価格は対象識別条件に使わない。全実画面は校正データで未知評価ではない。

実2はresult_json rpc_deadline3・host_deadline/cancel2/native_cancel_requestedを伴うがnative GOODS/PAUSEで回収完了。実1途中too_late1後も成功。実4の原16だけnative bounded capture行がなく、exportmetadata/PNGは正常。他79は全一致。omitted799/ref96を再構成しない。監査receipt7231B/SHA `06cb7b20d1192a5aa990e2689697de0d4af03b22326dfc84a9ac4b98d9fe3cb5`。追加回収/086再実行は不要。

## 2. 期待する動作と責務

既nativeの全商品可視→ポーズ成立/terminal/drained→全画像の永続保存/検証の後、同じiPhoneのiSH内で個別識別し、結果を表示・返却ZIPへ保存する。外部画像送信、新しい入力/購入/リスタートは追加しない。target/candidate/unknownを区別し、確信のないものを対象なしにしない。OSバックグラウンド通知・対象なし自動循環・恒久毎拍/人超え・新版実機到達率は今回達成済みとしない。

## 3. 対象識別の設計

新host moduleへ bounded PNG decode・3商品row抽出・指輪icon/表示名の独立witnessを分離する。Runtime/Scene.goodsは従来の可視性のまま。元R12/ring.pngは不変・public既存assetを出典にしたderived featureを使う。実3原309の対象文字はPIIを含まない数値glyph特徴へ限定し、raw/crop全体はGit外に保つ。出典SHA/bbox/校正用途を記録する。

対象表示名とiconの両方が強く一致した場合だけtarget。iconだけ/文字欠け/部分像はcandidateまたはunknownとして保持する。価格250やrun/capture番号/固定商品位置を条件にしない。商品rowは看板/3価格/36px間隔・原寸896の観測から抽出。sourceは最終ACK PAUSEのauthority1枚を先に評価し、candidate/unknown時だけ必要な保持proof1枚を追加する。両sourceは同run/同ACK-prefix・stable・非inflight・取得の非交差/authority以下の保持画像に限る（実3の308はinflightなので本番入力から除外）。最大2枚・有限slot/scale/探索範囲・各段階取消で処理量を制限し、存在しない元後処理deadlineを捏造しない。原寸probe（Git外native-feature-probe.json）で3derived spriteは32×28/33×28/34×29、対象309 icon.953305/308 .956985・負例最大.476866/別ring.313027。309文字bbox(368,54,452,65)の84×11/239inkからderived maskを作り、309 IoU1.0、同run308 .643110、別ring近傍最大.393229。新原寸ではicon≥.80をcandidate、同一認証PNG・同じ商品slotへ空間的に結合したicon≥.88かつword IoU≥.82/coverage≥.90をtargetの全ANDとして凍結。308のicon-onlyはcandidate、309はtarget、無matchはunknown。旧597版の.76/.64を新原寸scoreと同一視しない。

decoderは追加依存を要しないstdlibを優先。実frame RGBA8/896×414/noninterlace・chunk CRC/長さ/色/alpha/filter0〜4・inflate/入力byte上限・余剰/破損/取消を検査する。元ring assetのruntime再decodeやfull597画像resizeを避け、必要な特徴を事前固定してiSHの負荷を抑える。全80枚走査を通常処理にしない。

## 4. 永続化と出版の境界

closed active/report JSONへfieldを追加しない。初回archive前の明示optional hook（旧entry既定None）でcertificate済みの同run画像だけを評価し、version付き `target-assessment.json` をatomic保存して元inventory/ZIP/receiptへ含める。順序はcertificate→対象処理/sidecar→inventory/archive→コピー検証→receipt。対象処理未完なら新startせず同runを再開する。

sidecarはbounded閉schema、run/reportSHA/classifier版/featureSHA/sourceID・PNG SHA/slot evidence/outcomeと固定reasonだけ。現在時刻/自由path/任意例外文字列を入れずdeterministicにする。既sidecarは入力/版/bytes一致で再利用し勝手に上書きしない。既出版ZIP/receiptを後から変更しない。認識不足はunknownを記録するが破損・入替・symlink・報告hash不一致を成功へ丸めない。evaluatorは厳密にこのsidecar1名だけを検証付きで受理し、他extraの拒否と旧ZIP互換を維持する。

## 5. 通路停止の原因と修正ゲート

実4は4入力/4実歩後、cmd26 LEFTがbegin0/SCREEN17で確実未送信、その後BEAT8。最後DOWN346→354は公開MOVED、354/371の固定world口への元chooserはLEFT/reason10/観測FLOOR/path2でルートが残る。354→371は画面位置が同じでも公開motionはUNKNOWN。旧stationary085のlocal UNKNOWN→FLOOR、axis74.092%<75/9競合のlead不足があり、閾値を緩めてもよい根拠ではない。

最初の取消guardと後続準備50msの3.575ms不足/再同期停止を分離する。追加のSTONE-only原画校正もrawRGB勾配72.945%・候補分離不足、現signature支持87/帯42・45と不足し、新zero proofは製品化しない。旧P/W/50ms/10ms/8評価/入力予算・UNKNOWN無再送を広げない。歩行停止の修正は未解決として返し、次の証跡を改善する。

Aは**挙動不変の待機入口診断**に限定する。start_stationary_waitの全guard/scene資格/原motionUNKNOWN・selfBLOCKEDを通過し実OBSERVEへ入る場合だけ、元scene_changeの実mask!=0かつpassage_activeの場合だけ既record_changeへactual counts/allowed0/validation=MOTION11を1回記録する。前方宣言は移動だけ、新helper/Runtime/API/ABI/schema/イベントobserved欄の意味を広げない。mask0は元clientの1..15契約に従い記録せず、既0mask拒否assertを維持する。generic/shop側callerは元record_change済みなので新callの通路限定guardで二重記録を防ぐ。sourceは既元command/pending規則、bound first1/latest2を維持し既診断枠を消費することを記す。Runtimeの既latest2change source/observed priorityへ自動結合するため、requiredだけのevent案で20枚圧迫時に残らない問題を避ける。signature-only0maskの取消と欠損355の原因は未解決であり、この変更で初取消画像を必ず回収できるとは主張しない。公開新3methodsのRedで新実差分の入口traceのみ期待し、event/票/歩数/全期限を不変として適用する。元082の非zero入場後rows=[]期待と衝突する該当methodだけは、新entryrow＋後続拒否rowの順序/metadataを強める更新を行い、mask0拒否を保つ。変更した旧methodだけのauthor実行を未変更旧試験の形式反復と分けて記録する。

## 6. 試験と実装順

A=motion担当の非zero待機入口診断/公開Red/最小記録追加、B=candidate担当のbounded decoder/識別/単体、B子=publication/evaluator/hook/結合単体。地域/ファイル所有を分ける。各製品前に有効assertion Redを実測し、構築失敗をRedにしない。new author testを一度Green、編集methodだけ再確認し、旧意味試験のローカル反復を増やさない。

Bは正例/別ring・他商品/HUD・暗い/欠け/文字欠け/不一致、全3state、座標/3slot/入力寸法/CRC/filter/alpha/inflate/cancel/boundsを選ぶ。出版はcertificate前不実行・sidecar同ZIP・未完回復でstart0/同bytes・既出版不変・symlink/hash差/foreignrun/未知field/extrafile拒否・旧ZIP互換を選ぶ。単なるtemplate自己一致だけで実精度の証明にしない。

## 7. コミット前と実物検証

原因に関係する新単体/旧exact回帰・selector自己試験・画像全公開gateへ限定し、全Runtime/worldを既定にしない。source8/C4・保持実画面の校正を一度照合し、今回のnative診断変更時はfresh pinned G1/seal/apply→同code Mac実IPA→5実物verifier各1回/全tracked source/実compiler/MachO markerを照合する。Runtime/API16/cap15/client16/旧v1を変更しない場合は同bytes根拠で旧Runtime Redを分離再利用する。host core4のうちtest069を変更するため全4不変と誤記しない。

## 8. 配布と未受入

固定Releaseへ検証済みIPA/完全sourceを保存し、匿名全GET/digest/CRCを確認。新しい通常1-1ポーズから「候補までrestart→通路/金壁→店→全商品可視/PAUSE→対象判定保存」を実機で複数回依頼し全run ZIP/判定表示/途中停止/候補見逃しを受け取る。対象あり未出現runのunknownを対象なし合格としない。既R12全40/G1/入力取消・全安全契約を維持する。
