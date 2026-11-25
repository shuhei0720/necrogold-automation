# TEST119: TEST118の実機停止を直す

2026-11-25（日本時間）。基準CODE/配布はTEST118/build263、作業開始HEAD64f7b4f。通常の実機反復として原因に結ぶ修正と関連検証へ絞る。[修正表](../fix-records.md)のFR118ほかを修正前に照合し、過去のMac成功を今回の実機失敗解消にしない。

## 受領と原因の切り分け

9ZIP、4campaign/5run・132PNG/154recordsを全照合。原本/画像/記録はGit外へ保存・検証する。順序はsession accepted_started_nsで確定する。1歩後の未送信SCREEN、開扉後のPARTIAL観測不足、商品可視で正常分類が期限外、全商品可視でもUNKNOWNを、それぞれ元Scene/PNG・入力/ACK・通常Ring・各元期限に結び付ける。4周目rootの正常陰性→耐久保存→実RS→新floor→successorは成功として残し、次childの失敗と区別する。

原因の具体predicateと変更範囲は解析確定後に追記する。未保存のprivate状態/未来画像を生成して実機再現と呼ばず、未観測商品を陰性にしない。元target/worker/source/親期限やUNKNOWN無再送を、結果を通すために広げない。

## 実装と確認

各修正は原因となった原capture/SHA/prefix/時刻/通常producerと拒否guardを結ぶcutで旧assertion Red→最小Greenを確認し、変更部の単体と直接関連回帰を行う。入力資格/期限の契約変更が必要なら別の設計を先に記し、独立レビューを受ける。既存assertの削除/skipや未知を陰性へ変換して合格にしない。

TEST119の新client/同じiSH entryを設け、初回root RSと`--until-target`、全run回収を維持。119固有capで旧IPAをstart前に拒否し、116/117/118のcapとcollection namespaceは保存する。API/native_v15/ABI/profile3は変更しない。clientは実Python3.9で検証する。

通常は選択hostと実IPAビルド/実compiler・seal/配布物・完全ソースの照合で次実機へ返す。新しく変更する通信/queue境界がある場合だけ該当Mac結合を追加する。全Runtime故障集合・大型worldを機械的に再実行しない。37nativeの変更/保持を明示し、RuntimeやR12全40/G1/特徴資産は関係する原因がない限り保持する。

最後に独立差分レビュー1回、承認済みbranchへ保存し、検証済みIPA/完全sourceを固定Releaseへ置いて匿名全GET/SHAまで確認する。何をどう直したか、未確認、更新/再起動、iSHコマンド、具体的な実機確認と`runtime/test-119*.zip`全返却を短く依頼する。新版iPhone受入は新結果受領まで未確認。


### 配布識別の限定変更

119clientは118clientを継承し、新cap `necrogold_native_device_fixes119_v1`を両modeの開始前に要求する。RPCは118までのタグを残して119を追加する。既118の`device_fixes_capability`は変更せず、119用metadata `device_fixes119_capability`を別fieldで実patch/実RPCの配列宣言へ厳密結合する。旧manifestは119宣言がなければ新fieldを得ない。collectionの許可値へ119だけ追加し、旧試験の不許可サンプル119は次の未許可120へ移す。新試験で116/117/118/119の相互分離、旧IPA拒否、初回RS一回、saved recovery同root、引数・shellを確認する。これは原因不明の歩行/判定を書き換える処理ではなく、次の試験資材の識別を確実にする変更である。


## 確定原因と限定修正

### 1歩後の通路判断変更

5fd原109→110は通常strict零で遠方DIRT→STONE2セルを既FRESHへ通す。110→111もstrict零だが新FLOOR露出で次判断がDOWNからLEFTへ変わり、refreshed-source証明拒否が既bounded ROUTE待機より先にSCREEN終了する。109→111自体はUNKNOWNのまま残す。同logical票を復活させず、確実未開始/clear/no商品・金/現在のstrict零等を満たす時だけ旧票を撤回して既ROUTE待機へ移す。待機Pは元の最新実MOVED由来sync12秒・既command sync・walk45秒・session180秒のmin、Wは既2period内。次の独立画像から同判断/直接零と通常model/準備を再証明するまで新MOVEを出さない。旧票のDやUNKNOWN入力は延長/再送しない。正式期待は旧SCREEN→無入力wait→独立proof後の新routeであり、111一枚だけのMOVE発行ではない。

### 3周目の価格証明と費用

893原322/344は3商品/3価格が見えるが、中央100価格と同じx列の上方に白1pxがあり、旧xgroupが高さ20へ連結する。さらに中央価格が左右より7px下のため旧3価格同baselineに入らない。正常完走でもUNKNOWN/PRICE64、端末最終workerは元source150msを1,875ns超過しており、期限だけを変えても解決しない。

既layout3の独立した低い価格geometryを2看板policy4へ限定継承する。全白pixelのxgroupを空白行で縦splitし、18ink以上の全runを7〜9px/所有slot/blank perimeterで検査、無視した全小run合計も18ink以上なら拒否する。exact3価格/唯一低い価格/左右共通span9等を要求し、未登録の商品名を追加しない。元target全域探索/候補優先/全3ITEM・cap/2看板・7GOLD支点は保持する。Ringの旧structural consumerと、元Sceneを持つCの独立side consumer双方で同layout/数値を再検査する。成立時だけ高費用な閉容器総当たりを避け、元source150/worker100/親期限は変更しない。設計の独立レビューP0/P1なし。元画像cutと左右/全lower slot、欠落/余分・分割第4価格/不正box/正候補/旧side・閉容器・singleの関連を検証する。

### 商品が欠けた入口からの観測継続

a1原233→235は同choice/両corridor/正確なITEMと保護/次FLOOR/通常strict零が成立し、遠方(7,4)のDIRT→STONEだけを旧quietが拒否する。既framingのこの全条件下に限って遠方の材質関係を許し、見える位置への観測を継続する。開扉や2商品可視を全商品確認とせず、陰性判定は出さない。新2件は旧Cでassertion Red、修正後と直接関連でGreen。独立差分レビューP0/P1なし。


### 現在の松明床の別証明

未記録の未来でDIRTがFLOORへ戻ることに依存する大きな新待機modeは採用しない。原175〜177の現在画素には、松明を挟む非重複UL/LRに旧floorの正の色/textureがあり、上帯/下3GOLD/有限warm成分も確認した。[別8項目計画](test119-torch-floor.md)の閉predicateで現在の床を正に証明する。正式5件と関連11件がGreen、旧Perceptionのassertion Redも確認した。全132PNGの通常Perception比較ではefの4画像/5セルのDIRT→FLOOR以外はScene全bytes一致、3f成功画像の正常判定packetも一致。独立最終レビューP0/P1なし。端末の未知画像精度は未確認。


### 早期FULL後の実入店と新DATA

現在のfloor証明が成立した場合に限り、元ACK166→176/177の真の通常unitから[限定entered/current計画](test119-entered-current.md)へ進む。protected露出0だけのtoken、共用DATA2/元P、遠方新GOLDの独立DATA・採用source所有を保つ。旧mode/価格guardは維持し、未分類結果や暗いcapを陰性にしない。新7件は旧Cで15 assertion Red、修正後と直接旧13件の計20件がGreen。独立最終差分レビューP0/P1なし。

元画像166/174/176/177と宣言した適合contextの限定cutでは、元LEFTのunitを一度反映し、新source176のDATA1とqueued177へ進む。通常Ringは3画像ともUNKNOWNのまま。欠けた178以降・未来MOVE/実RSを再現したとは主張しない。新source所有が実Runtimeのimmutable frame/worker返却を跨ぐため、[専用Mac確認](test119-runtime-queue.md)の1case/短い2subrunを追加する。価格guardを外す画像単独の陰性化は今回行わない。
