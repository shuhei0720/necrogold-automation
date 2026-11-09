# TEST056: 停止直前の比較画像を保持する8項目計画

状態: fresh計画レビュー完了（設計/網羅第2周・安全第1周、残P0/P1/P2なし）。2026-11-09（日本時間）。本工程は診断保存の修正であり、TEST055の停止条件・認識・予約予算を緩和しない。

## 1. 目的

pin20/選択20/各512KiB/総4MiBの既存上限内で、停止に使った最新のScene比較を先に保持・公開する。再予約が増える原因を原画像で検証できるようにし、動作変更の根拠がないまま上限だけを増やさない。

## 2. 背景

受領TEST055は4,196,623bytes/SHA `b495fd5a09b4700d65eb54a31ed0d86383993e03cd36912be1310a41cac92506`。5入力/5MOVED、扉開通0/商品0。入力間隔522.931/515.793/516.647/517.386ms、model周期521.148ms。歩行開始から初入力は2,212.384ms。再予約FRESH12は実行されたが、その次がvalidation5/run8で停止した。

125→126はDIRT→STONEの2セル、126→127はSTONE→DIRTの1セル。3枚ともZIPにない。125/126はpin20飽和、127はrecentに残ったが選択20から外れ、63/64/74は選択後のbytes制限段階で省略された（元PNGがなく、各512KiB超過と総4MiB超過は個別に切り分けられない）。欠損は明示され、回収自体は完了している。既知runの再回収で復元できるとは扱わない。

静止した実画像111/112/113でも石壁の色がDIRT/STONE境界を跨ぐ。ただし最終3枚がないため、最終の完全DecisionやSAME可否は未確定。予算を増やせば店へ進めるとは断定しない。

## 3. 設計

controlQueueの既存C snapshotをcacheする際に、最新2件のSceneChangeのsource/observedと最新MOVEのsourceを、最大5IDの順序付き診断参照としてrunへ保存する。results/exportからCを新たに呼ばない。累積referencesは変更せず欠損を正直に報告する。

優先集合は既存initial/found/terminalの最大3anchorと上記最大5ID、計最大8。terminalはCのlast_capture_idを明示的な停止anchorにし、recent.lastが別画像なら後順位とする。利用可能な優先画像はpin20が満杯でも非優先pinを入れ替えて保持する。取得・解析・入力の再実行や待機は追加しない。

選択/exportも同じanchorと診断順を先にする。最大8枚が全て各512KiB以下なら4MiB内に収まる。元の上限・PNG bytes/寸法/時刻/prefix・原画素は維持。未保持/oversize/encoding failureを捏造せず、owner/世代/取消/drain/immutable cacheとlegacy/paged一致を保つ。過去run回収のため新しいrunを上書きしない。

## 4. 影響範囲

Runtimeのpin/選択とHOST限定fixture、必要なcheck helper/検証器、native sealと新IPA、`test_056.sh`、資料。Controller/Perception/Navigation/Beat/Ticket/座標・R12/G1、client v13/API/cap12/旧journal/通信schemaは不変。新launcherは同じv13でoutputだけruntime/test-056を指定する。

## 5. 検証

実装前に、pin20飽和後の比較source/observedをrecentから落とし、選択20/4MiBの両段階で欠ける旧Runtimeへ、最新比較が揃うassertion Redを実Macで観測する。HOSTのseedはfixture設定だけで、旧pin/選択のproduction処理を差し替えない。compile/環境失敗はRedに数えない。

Greenでは最新2比較＋latest MOVE source＋initial/found/terminal、重複、異なるrecent.last、anchor更新、比較0/1/2/3、欠損、pin20、各512KiB境界/4MiB/20選択、legacy/paged一致と元owner/drain/取消/キャッシュ退役を確認する。encoder nilはlegacy/pagedの両方でRPC error・未完成cache非公開・build token解放・正常再試行可能を期待する。実producer/export bytesへ結び付ける。新しいpin優先無効/選択優先無効の故障を個別に検出し、旧57/Raster3/C同値-field/RPCは保持する。

実TEST055の評価はintegrity pass/商品到達failのまま。17原PNGの既知解析と、合成された飽和fixtureを区別する。欠けた125/126/127や次の入力結果を生成しない。

## 6. 順序

fresh設計・網羅・安全の計画レビュー（最大3周）→実Mac旧Runtimeのassertion Red→pin/選択の最小Green→関連回帰→fresh3観点実装レビュー（同周の実IPA/全source補足、最大3周）→新IPAとTEST056の具体的実機依頼。

## 7. 配布前

関連host/client/package、実Mac全fault/Raster/C/RPC/実compiler、22seal/9Mach-O/IPA/全source ZIPのbytes/CRC/pathをcodeへ結合する。新IPAが必要なのは診断画像の保持がnative側にあるため。新ソースとbuild指定、LoopCtrl更新/完全終了/Start Server、通常1-1ポーズからiSH実行し「TEST-056: 終了」後runtime/test-056全ZIPを依頼する。今回の変更で店到達や毎拍・速度が達成したとは扱わない。

## 8. 対象外・未実施

予約run8/chain2/input16・期限・認識閾値・全230セルの安全契約の変更、扉/掘削の新許可、UNKNOWN再送、指輪/周回完成、Mac実ゲームの実行。Macの従来試験はfakeの応答であり、ZIP評価は実記録の部分検査に限る。正規ゲーム本体とGUI取得/入力adapterが未導入で、実ゲーム試験は未実施のまま。
