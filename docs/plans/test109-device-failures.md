# TEST109: TEST108実機の入店停止と未判定停止

2026-11-17（日本時間）。基準 `7fe34ff`。実機失敗を主に、確認した原因だけを修正し、変更部・直接関連回帰・独立差分レビュー・同source IPA照合を経て次の実機へ返す。遠隔/iPhone8開発は再開しない。

## 受領・原因の切り分け

6添付は3固有runとcampaign最終runの重複。全ZIP CRC/path、内包ZIP全bytes、manifest/hashchain、73 PNGの復号RGBAを照合。82記録/161論理ファイルと原本はGit外。単調時刻順は56b→a782→7853で利用者の3周に整合するが、記録に明示周番号はない。

- 56b: 開扉後のsource522は正常UNKNOWN/coverage未成立。新108の開扉履歴・入口の観測FLOOR/金壁bracketは成立するが、壁付近のpartial候補のpotential ROIが既安全範囲から外れ、FULL追加観測を拒否する。行/看板の正常検出を原画像で追加解析する。
- a782: 開扉後の正常safe PARTIALが23job続き、入店せず元continuation期限でLATE。原234→236/244→246は通常strict BLOCKED零・同じ完全LEFT判断・正確ITEM/保護だが、遠方のUNKNOWN→DIRT/FLOORでROUTE10となり、再分類・票/証明撤回を繰り返す。固定234からの後続には遠方FLOOR→DIRTもある。元3秒内で入店準備を完了できない。未収録frameや未来の入店を作って成功扱いしない。
- 7853: 商品3品を検出しても、11白画素の小成分を第4価格として数え、さらに左cap上半分の床palette条件に失格して正常UNKNOWN。表示「対象なし」への書換えで解消しない。上入口のFULL追加観測も従来の横方向/安全ROI条件外。
- 56b原323: GOLD0/mask0の見送りsource後に実PAUSE/RESTART。上左の観測口と暗い側方に対して旧106/108の壁支持条件が適用外。利用者の見逃し番号は未記載なので、該当番号だと断定しない。

FR104〜108の全被覆/開扉FULL/PARTIAL合成/元D内待機/候補を照合する。同じ見た目の継続失敗と、過去と同一根因の再発数は分け、単体合格を実機改善完了にしない。

## 変更・期待値・範囲

1. Navの原323は独立した屋根4セル・下側壁3セルと観測口FLOOR、外側/内側/側方のUNKNOWN、内側の観測床を要求する別witnessを追加する。既bit5の候補のみ。既FLOOR3歩のvantageまでとし、未知口の接続や店の存在を補完しない。既106/108の弱形拒否・chooser/runtime予算・Sceneを維持。
2. RingとCは原画像・正常producer・実採用状態から、最初に失格する検査と後続検査を別々に特定する。価格/床/入店それぞれの最小変更と期待値を本計画へ確定してから実装する。全3商品/対象候補保持/未観測不陰性/正の全被覆・入力権限は維持する。
   a782の既開扉safe PARTIALだけ、元分類済みanchorを保持したまま、全GOLD/ITEM/保護と原点/次床3×3・完全Decisionを不変にし、遠方非保護のUNKNOWN/FLOOR/DIRT相互変化を別のquiet証明へ渡す。同方向の一歩近傍外に連続4セルの観測済み外側GOLD壁と、単一行の連続した3以上ITEM/正確保護を正に要求する。原の外壁はx=-7で成立。元画像がない非公開flagの値を仮定せず、旧104の外壁支持がない新ITEM再分類条件を保持する。新STONE/GOLD/DOOR/ITEMは追加しない。各画像を元anchorへ直接通常strict BLOCKED零で検査し、失格を中間pairで橋渡ししない。元モデル/slotの通常検査・fresh ID/前面/prefix/取消/元D/累積予算を保持し、再分類だけでDや許可を延長しない。原pairの校正と公開Cの分類採用→独立画像→新しい将来拍/ACKの契約試験を別々に記録する。
   7853の価格は、既有効価格と同じ18白画素以上の支持を要求し、11画素の非価格成分を価格数へ加えない。正の3価格・余剰の支持された価格/第4Scene ITEM拒否・全B対象探索は維持。capは既full25×25床が成立する場合だけ、既half床判定に加えて、各halfのtexture/可視率/明るさ/価格不在とfull床との小さい色度差・限定した輝度比を正に検査する別証明を用意する。対応する観測Scene FLOORも必須。既target-only offer被覆に限定し、global material_floor/Perceptionや旧policyの閾値を下げない。実色はfull(35,20,18)/upper(40,23,20)で、同色相の照明差という仮説を独立guardで検証する。黒/無地/別色/暗い端/余剰品/対象を通さない。56bとa782の未観測商品は陰性化しない。
   56bは第三品直下UNKNOWNで現在の完全陰性は不成立。開扉直後の正の観測一歩だけ、partial slotのunionが水平方向の端で切れ、移動で中央へ入る場合を別証明する。既row/ITEM全ROIと旧cycle_full_roiは保持し、partialにも観測済みicon core(cx±18,sy+24..66)が安全中央域内・上下は既完全範囲内・現在可視unionの全てが移動後も可視、を要求する。LEFTの左端/RIGHTの右端だけで、逆向き・HUDにかかるcore・対象候補・不正prefix/保護は拒否。旧cx150のHUD拒否を保持し、原cx195のleft135だけを観測一歩へ渡す。上方向や全般のROI緩和は行わない。522後の同prefix原画像は未収録なので、原admission校正と公開Cの手続き的な後続検査を区別する。
3. 各機能で変更前の実assertion Red→最小Green、原画像の正常校正、直接関連回帰を残す。Cは純helperだけでなく、分類採用→独立新画像→予約/begin/ACKの届く範囲を検査する。受領にない実応答・後続画面を実機再現と呼ばない。

public API/ABI/cap、Runtime/Raster/Perception、既feature/canonical15/ELF/G1/R12、prefix/取消/元期限/累積予算、UNKNOWN無再送/購入禁止はscope外。追加変更が必要なら原因と範囲を先に追記する。

最終sourceの独立レビュー後、標準Macの選択CIとIPAを作成し、seal/実compiler/全source/IPAを照合して固定Releaseへ保存する。主指標は実機の商品確認到達率と対象なし後の次周回。次の実機結果を受領するまで各対策の改善は未確認とする。
