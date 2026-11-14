# TEST098: 新しい床への進路変更と開扉後の再観測

2026-11-14（日本時間）。基準357337c。[受領](../reviews/test098.md)・[要件](../requirements/necrogold.md)・[制御契約](../contracts/native-control.md)。実機改善未確認。

## 1. 目的

通常1-1ポーズから候補探索→商店→必要な商品表示→のろいのゆびわ判定→対象なしの次周回を継続する。候補見逃し、未送信時の正当な進路変更、開扉後の再観測を修正する。全商品登録・購入・宝箱開封は追加しない。

## 2. 実機根拠と過去対策

097の3ZIP/64PNGを全照合。実順23aba→6df619→f8bce、添付1→3→2。実1/2の判定は正常・期限内採用だがPARTIAL/UNKNOWNで、対象なし未確定。実2は遠方FLOOR→UNKNOWNを継続条件が拒否。実1は最初の失敗画像が未保存で、後の234→242は全条件が成立するため原因未確定。最初の拒否predicateを後の画像から断定しない。

実3のDOWN入力は未送信。隣接(-1,0)DIRT→FLOORにより、完全判断がDOWN/reason8/(0,1)/FLOORからLEFT/reason8/(-1,-1)/FLOORへ変わった。GOLD/保護と厳密0変位は同じだが、旧monotoneと同判断refreshの適用外だった。候補135は実PAUSE判断元の、壁の外側に床が見える上左角。

FR095/097の材質継続、FR055/077/081/090/093のFRESH/未送信回復、FR084/086/094/095/097候補を照合。旧修正の削除や、前回のPAUSE採用遅延の再発とは断定しない。

## 3. 実装条件

### 未送信の直交側方開口

一般monotone/SAMEの意味を変えず、既observation refreshの限定した別admissionを追加する。元票は未送信・実beginなし・現owner/prefix/世代、旧新FLOOR/GOLD_CANDIDATE/商品UNKNOWN、同実GOLD・全保護/ITEMなし、旧新の完全reason8/FLOOR判断が必要。差は新しい隣接方向のDIRT→FLOOR一セルだけ、旧/新方向は直交。元の完全判断とキャッシュsourceを照合し、厳密0変位を証明する。

旧票を撤回して新しい判断をrefresh anchorへ固定する。既更新/独立画像/HUD/将来拍の準備から新IDへ進み、旧票を変更・延長・再送しない。新sideだけ、後続画像の厳密0をその固定anchorへ直接要求し、前画像の更新によるanchorの連鎖移動を許可しない。既12秒/refresh回数/phase・walk45秒/session180秒を維持する。具体的な既guardsと新しいprivate印の撤回箇所は担当が実装前に一覧化してレビューする。

### 開扉後の材質と再観測

実ACK済みの同方向DOOR_OPENED・隣接FLOOR・reason5の固定完全判断に限り、両3×3外・非保護の遠方FLOOR→UNKNOWNを追加する。同GOLD/全保護・同判断・厳密0変位は維持し、一般のPARTIALや非開扉には広げない。

実1について、上記の開扉来歴と静的条件が全て成立し、動き判定だけUNKNOWNのときは、入力を許可せずOBSERVE_MOREのまま元continuation horizon内で独立画像を待てるようにする。source/job/prefix/release/親期限を固定し、後の厳密BLOCKED(0,0)成立まではcreditを与えない。既知の移動・別判断・商品/保護変更・取消・入力不明・期限超過はこの待機で解除しない。実1の最初のガードが未確定なので、この待機が実際の停止を解消すると断言しない。

正常なOBSERVE_MOREに独立した新FULL/FLOORが来た場合は、旧097のframing専用と同じ条件で通常の新分類jobへ渡す。入力0/current prefix/新ID/start>=release/no sticky/no unproved restartを必要とし、旧移動権限を破棄する。新sourceの分類期限と旧入力horizonを混同しない。

最初のcycle再観測拒否のsource/観測ID・差分を既SceneChange経路へ記録し、既Runtimeの判断画像保持に接続する。公開ABIとRuntimeは変えず、命令発行やreplan許可を診断記録から作らない。既record_changeの通常出力は保存し、記録数は有限にする。

発見した回収側の境界: 既clientはchange_maskを1..15に限定するため、材質差0で動き判定だけ失敗した記録を拒否する。偽の差分bitを作らず、現API1.98.16の非再帰レポートだけ、同state/goods・tiles/protected0・replan不許可/count0のmask0を診断として認める。必須の同command/source/observed IDのSceneDetailがMOTION=11・continuous/chain/cells/omitted各0であることを外側で照合する。旧API1.98.14/15、欠落/不一致のdetail、許可を伴う0は拒否し、通常1..15の意味は変えない。新client単体の意味Redと実Python3.9の関連報告/回収試験で確認する。入力権限やNative ABIの変更ではない。

差分0でROUTE等の非MOTION拒否は既schemaで表現できないため、行を追加せずfirst印も消費しない。実際の停止は保持し、全拒否画像の保存を保証したとは呼ばない。実Runtimeのserializerを確認し、SceneChange/Detailはrootだけ、motion referenceはflatなので再帰側へ例外を広げない。

### 候補135

既occluded-corner helperの共通FLOOR/CLEAR/商品UNKNOWN/金0/ITEM0/全保護0・中央2×2床・観測床3歩vantageを維持。外床(-4,-3)FLOOR・直接外(-4,-2)UNKNOWN、角/屋根(-3,-3)/(-2,-3)/(-1,-3)と左面(-3,-2)/(-3,-1)の5壁、内側(-2,-2)FLOORを必要とするbit5仮説を追加。既chooserだけで4歩の観測床へ近づき、壁/UNKNOWNへ入らず、金や外通路が存在すると断定しない。

## 4. 検証範囲

新しい候補/FRESH/部分観測の単体と、変更した既guardの関連回帰を選ぶ。Ring/Runtime/Wire/公開header・canonical15source/ELF・Bank/G1/R12は変更しない。既Mac API/spool/Export・Runtime096の選択境界と、実IPA/実compiler/封印/全sourceを確認。全world/全故障集合や未変更のRing単体を機械的に追加しない。

## 5. 期待値とRed

各機能で実装前に公開APIの意味Redを取り、最小Greenへ進む。未送信→新判断→独立画像→新票の正常系と、複数差/非直交/新FLOOR以外/保護・GOLD喪失/非0/owner/prefix/取消/元期限/旧ID再利用を拒否。部分再観測は開扉来歴・遠方だけ・UNKNOWN中無入力/不変source・期限終了・FULLの新jobを検証。候補は全5壁の材質組合せ、証拠欠け、既観測床だけの接近、既候補/反対向きの境界を確認。生画像は各一度だけ校正し、保持Sceneからの既知校正を未知評価や未来到達に数えない。

## 6. 実装・レビュー順

具体条件の独立確認→該当Red→最小修正→関連Green→独立差分確認→封印/選択CI/IPA。通常の差分レビューを基本とし、新しいrefresh admissionだけ入力権限の固定anchor・期限を重点確認する。指摘の修正確認はその差分へ限定する。

## 7. 保存・配布

修正表へ原因/対策/改善確認方法/再発数を記録し、未確定を0や改善完了へ変えない。rawはGit外。GitHub固定Releaseに完全source/IPAを保存し、公開後に実ダウンロードとhash/tagを照合する。文書だけのclosingで製品/試験/sealを変更しない。

## 8. 次の実機と未確認

通常1-1ポーズから一連を依頼する。対象外なら次周回へ進むか、上入口から下の商品が見えるか、新しい床で進路を切り替えられるかを確認。停止通知後iSHの全保存/ZIP照合完了を待ちrun ZIP全体を返却。実1の最初の原因、実機到達率・毎拍/人超え・未知精度は未確認。
