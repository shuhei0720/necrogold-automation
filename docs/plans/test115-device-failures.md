# TEST115: TEST114実機4周の停止・候補見逃し

2026-11-18（日本時間）。製品基準はTEST114/build232（CODE d5360e1）、保存HEAD c84e74f。4周とも商品確認までの一連の動作は不合格。過去の対策・単体合格を実機改善完了と扱わない。

## 1. 概要・受領

8ZIP＝4固有run、96PNG・106記録をCRC/path/hashchain/参照/原RGBAまで照合。端末の開始単調時計で対応し、添付順だけで周を決めない。原本・詳細診断はGit外。installed IPAのbuild/sealはrun資料にないため、名前とAPIだけで同一性を断定しない。

| 周 | run先頭 | 記録された停止と根拠 |
| --- | --- | --- |
| 1 | 2b78 | LEFT12はACK後、元128→135..141の8評価がUNKNOWN。送信前129への直接静止は成立し、129→同じ後続は通常MOVED。30はGOLD実セル0の上左通路で、既遮蔽口の外側FLOOR形が適用外 |
| 2 | 00bf | 開扉117後MOVE0。119の通常UNKNOWNは約4.96ms、7ITEM/正のLEFT床/上部入口は既条件内。記録target/周期/元親期限では4歩の先行確保が23.286ms不足 |
| 3 | 1386 | 開扉後MOVE0。148の通常UNKNOWN約3.94ms。最初の新鮮150は上端重複ITEMの消失とGOLD露出で旧framingを正しく無効化するが、現在のPARTIAL/UP床を独立再判定する経路がない |
| 4 | 2fd3 | LEFT4の実MOVED後、LEFT5はbegin0/not_sent。84→後続は通常UNKNOWN。数値零証明は成立するが実GOLD0のCANDIDATE分類が既CLEAR専用条件から外れる。89はblur .450321で元.45を超え、単に分類だけ許可しても足りない |

FR-112上部入口・FR-113未送信静止/上端観測・FR-114現在FULLを照合。いずれも同症状が継続し、過去修正を削除した回帰とは未実証。上部入口のprivate stageは保存されていないため、2周の条件代入と分岐の完全再生を区別する。

## 2. 背景・詳細設計

### 通路の送信前sourceと候補

1周129はLEFT12のbeginより約54ms前に解析済み。確実未送信の限定passage MOVEだけを新ID/最新129でFRESH再予約する案を検証する。実際の変化は遠方4セルのDIRT→STONE（tile mask4）で、一つの物理票につき更新は最大一回。完全不変/署名だけの画像で枠を消費しない。同じ方向/完全Decision・正の床・全保護/金壁・元128からの直接strict零を要求し、target/notBefore/D/ordinal/preparation epochと既chain2/run8を共有する。新しいreferenceを古いreference欄へ偽装しない。begin済み/UNKNOWN後の更新・再送は禁止。実Runtimeの同一準備epochのcallback境界を追加検証する。

30の見逃しは金色画素の閾値ではなく、既上左遮蔽通路の観測FLOORの縁の形を限定追加する。既壁支持・正のvantage床・局所予算・各歩後の再観測を維持し、未知口へ直接歩かない。

4周の固定anchor待機では、実GOLDセル0のCANDIDATEに限り既数値条件を適用する。CLEAR全般や実金壁/商品へ拡大しない。途中の数値不成立は入力資格を取り消したOBSERVEで元2拍期限Wまで待ち、blur閾値を緩めない。直接anchor→新画像の零と新sample/fitが戻るまで入力不可。[既076](test076-stationary-recovery.md)の状態別期限を継承し、W内に確認したREADY/ISSUEDは元親期限P内で新拍を選ぶ。W/P・位置・visits・prefix・旧not_sentを保持し、零の連鎖やW/Pの再設定は禁止。READY後に再び不明となった時点がW以降なら、OBSERVEを延長せず終了する。

### 上部横入口と現在PARTIAL

2周の全4歩見通しで、最後のMOVEに必須の最早visual80msと、正常DATA取得の**最大**150msを同じMOVE親期限から差し引いている。150msを最低所要時間とする予約は過剰。4歩の見通しと80msは保持し、実MOVE/ACK/visualの元期限とDATA自身の150ms/worker100msは据え置く案を検証する。入力後の新しい床を毎歩確認し、2歩横→壁沿い下の未観測床を先に許可しない。実機相当ACK約275msで全行程・正常producer・候補優先・期限境界を確認し、初歩だけ進む試験で解消扱いしない。

3周は旧148の入力資格を失効したまま、現在150を独立した正常PARTIAL DATAとして再判定する。元親期限/共用DATA最大2/同期期限を保持し、実drainを保証するyield profileだけに限定する。確実未送信の同一PAUSEだけを撤回し、begin/ACK/不明は停止を維持。現在anchorへの直接零2枚と新fitで正のUP床を確認し、既framingの未使用一回分だけを移す。古い上端の潜在商品領域は経路保護から消さず、古いSceneの書換えや未観測の陰性化をしない。実画像150はUPが安全であり、2周のDOWNを機械的に適用しない。移動後も通常の全商品証明なしにリスタートしない。

新PARTIALの通常UNKNOWNに安全な部分probeがある場合も、空結果に限定して捨てない。row0、既entry_result_safe/positivehint0、部分検出ありならsafe1、各probeが現在のrow−4 ITEMへ正確に対応し元ROI/保護和集合を保つ場合だけ一回の観測資格を与える。名称や全商品登録を増やさず、部分probeは陰性/RSの資格にならない。

## 3. 試験影響

Controller/Navを対象にし、下記の追加設計でRuntimeの最終時計確認を限定変更する。Ringの閾値/価格/対象bank、G1/R12、ABI/既wire意味、全累積予算は変更しない。

回収のJSON前検査について不要な文字列割当を調べたが、最小案は実3.9の同bytesベンチで遅くなったため不採用。別の複雑な最適化を混ぜず、validation.pyは元bytesへ戻した。回収70〜89秒は未改善として残す。

## 4. 新規ケース・期待値

- 元128→129の直接零/同Decisionでのみ未送信更新。begin/ACK/UNKNOWN/別prefix/新保護/期限・chain超過は拒否。新sourceの実unitだけ加算し、古い通常UNKNOWNは書き換えない。
- 遮蔽口のFLOOR縁の正例と、壁支持不足/非FLOORvantage/別口/未観測の反例。実30は校正資料で未知評価ではない。
- 84anchorから86/88/89/後続の時刻付き列。READY後のblurは元W内だけ入力を撤回して再観測。W内の確認後はWを越えても元P内で新拍/実入力へ進み、P越境を拒否。READY後のblurがW等号/以降なら即終了。実金壁/商品/保護/動き/chain零を拒否。
- 275ms ACKと新しい床を使う全HHDD、正常の3商品陰性→PAUSE実ACK/新画像/永続化/RS。各元期限・DATA上限・candidate/UNKNOWNを独立に検証する。未来の電話画像は未収録であり合成結合と区別する。
- 新PARTIALの正常producer/直接2零/新fit/既一回観測枠。旧hard保存、古い商品影・新GOLD・実drain/PAUSE開始済み・期限・予算・一枚/連鎖零の反例。現在150以降の実機成功は未確認。
- Python3.9では新115入口と既114診断の継承を確認。JSON最適化試作のRed/比較は不採用の私的証跡であり、配布機能の成功件数に算入しない。

## 5. 実装順

限定設計の独立確認→機能ごとの意味ある旧assertion Red→最小変更→直接関連回帰/原候補236・正常RS成功保持→独立差分レビュー→変更境界の実Mac結合→seal/IPA/完全source照合→固定Release→次の実機。Cの同時編集は避ける。

設計確認: 独立担当が具体的なP0なし、P1を実装/配布前の必須条件として整理。通路はquietがmask4を消す前に更新し、元準備epochを実callbackで確認する。静止待機はREADY/OBSERVEの証明を取り消し、ISSUEDは確実未送信票だけ退役する。元W/Pを状態別に保存し、古い回復slotを再利用しない。PARTIALはFULL条件の緩和やentryの2歩枠へ置換せず一回を移す。これらの実装・検査完了までは合格としない。

## 6. コミット前・配布確認

今回の影響境界だけを選び、実施commit/件数/結果/再利用の理由を記録する。既assert削除・skip、合成世界だけの到達、送信成功を実機成功にしない。native変更は実compiler・36資産差分・G1/R12/保護資産・IPA/完全source/hashを照合し匿名全GETで配布を確認する。

## 7. 残課題と運用

実機主指標は全商品の観測→判定→対象なし時RSまでの到達率。全4周の不合格と同症状継続を修正表へ記録し、次の実機確認までは未確認。終了後の70〜89秒はhost復号/応答解析の寄与を確認したが、端末暗号providerや背景化の原因は未確定。古い背景marker反復を新しい原因として扱わない。

## 8. 範囲外

全商品登録/名前必須化、未観測商品の対象なし化、UNKNOWN入力の再送、時間/入力枠増加、数値閾値緩和、無根拠の自動ポーズ解除、外部PC/副端末/Tailscaleによる新運用。既候補保持と購入禁止を維持する。

## 追加設計: R4の重複計算と実送信直前の時計

根拠/概要: 機能修正後のC5a6ffd/Nav13f7で、実97の通常Motion＋零証明はホスト約10〜13ms、記録時刻から最早準備への余裕は約8msだった。模擬時計での発行/begin成功だけではこの費用を含まない。またRuntime.executeはC.begin前に時計を読み、重いC検査後に時計を更新せずgestureを呼んでいた。MOVEの10ms入力窓Dの直前に入ると、検査中に越境して実送信し得る。既存構造にある問題だが、新しい費用で影響するため配布前に扱う。

詳細案A（計算共有）: 一回のprivate combined関数で通常Motionの全段を元順序のまま実行し、通常UNKNOWN(dxdy0)の場合だけ同じ局所View.blur/原73候補を新しい零証明に再利用する。通常BLOCKED/MOVED等は元結果を使い、補助boolは0。通常段が書き換えるtextureは零証明が使わず、blur/Sceneは不変。通常Motionのreturn/全出力/優先順位と、消費する零証明の全数値条件を維持する。共有は一呼出し内だけで、global cache/前後画像の付替え/未知Motionの捏造はしない。37実校正pairのprototype比較では通常出力が全bytes一致し、97のホスト費用は約6〜7msへ減った。これはiPhone速度の証明ではない。

詳細案B（実送信）: RuntimeはC.begin成功後、inFlight/gesture開始の前に現在時計でMOVEの入力窓、現在owner/lock/世代/取消とauthority鮮度を再確認する。C.beginが消費する準備epochをここで再要求しない。越境時はgestureを一切呼ばず、既complete(outcome0)の「開始許可後だが物理未送信」の経路を同じrun.lock内で確定し、自動再送/入力数加算をしない。begin済み許可とsynthの開始を混同せず記録する。public POD/getter/field/期限の増加は不要。

期限解釈の訂正: 追加案の初版は新候補のREADYにもWを強制し、D<=W−1を試した。しかし076正本23行・既単体218行は「W内に未解決なら停止、READY後の新ID/新拍は元Pを継承」と明記する。Wは未解決観測の期限、Pは確認後の入力/visualの元上限である。Wを確認後の全入力にも適用する変更は、既契約より狭くして回復を妨げるため取り消す。W/Pの値を増やさず既CLEARと同じ状態別意味へ戻す。W前に再確認しても最早拍を逃した場合、元P内の次拍へ進める。元W後に不明へ戻った場合は直ちに終了する。未配布の旧案・反例・試験は私的証跡に残し、期待値を訂正した理由を記録する。

試験/期待値: 共有前後の正常MotionとUNKNOWN時の零証明の同一性、数値拒否/実移動/実GOLD/商品/無効入力、既通常Motionの直接回帰を選ぶ。CはW前の直接確認後、最早準備を逃しても元P内の次拍でbegin/ACK/MOVEDできること、元P終了とW以降の不明を拒否することをRed→Greenで確認する。Runtimeは新旧Runtime双方で使えるtest-only C.begin-return wrapperで時計をD内/等号/越境へ進め、旧bodyの実Macで遅延gestureが発生するassertion Redを実装前に確認する。新bodyでは既知未送信・gesture0・再送0・入力加算0を確認する。fresh query/epoch/owner/世代/cancel/旧callback/drainの条件を保持する。開始許可後の未送信は同じrun.lock内でcomplete0を確定してからcancelを通し、同時取消でUNKNOWN/入力加算へ変わらないことも確認する。

順序/検査: 現機能版の凍結と旧証跡を保存→追加設計の重点確認→新assertion Red→最小共有/最終時計変更→変更境界だけの関連回帰→独立差分確認→実Macの追加時計caseと既FRESH/PARTIAL3case→seal/IPA/完全source。期待差分をC/Nav/Runtimeの3資産へ更新し、残33を保持する。先に固定した機能試験を削除せず、強い期限へ合わせたfixture変更は理由と前後sourceの結果を記録する。

範囲外/限界: 数値閾値/全体期限/元W/Pを緩めず、電話の未収録queueや入力応答を成功と仮定しない。毎拍/実機費用は次の実機で確認する。共用できない/正常出力が変わる/費用が改善しない案は採用しない。約48KBの別proof cacheは不要な権限管理の追加になるため採用せず、一呼出し内の計算共有に留める。
