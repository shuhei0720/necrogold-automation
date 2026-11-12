# TEST090: 実089の3停止と判定待ち

2026-11-13（日本時間）。基準169eb67bc4906c83e6bedf30678b99a240b44522。通常の実機反復として、下記の限定境界を同じ独立担当1名が確認する。元の入力予算・期限・UNKNOWN無再送・商品保持は変えない。

## 1. 受領と期待

実順はnative開始時刻からc11722aa→4bca6a1d→059f6b82→848d9572。4ZIP/80PNGを全CRC/SHA/strict load/publication certificate/canonical sidecarへ照合済み。実1は全3商品可視、中央はカリスマのゆびわであり、のろいの見逃し根拠はない。残りは商品未確認の失敗とする。実1のauthority最終chunk応答→次bulk要求5.276秒は保存・engine配置/検証・PNG・分類等の合計で、純C秒ではない。rawと診断はGit外に保存する。

## 2. 実2: HUDへ隠れた移動anchor

source99→観測109..119は実UP1。残る旧STONE2個は保存されるが、旧STONE1個の投影先が心臓HUD内となりUNKNOWNになったため、旧全STONE保持条件が失敗した。global motion/閾値を変更せず、UNKNOWNの後だけ専用proofを追加する。

ちょうど1個の元可視STONEだけが投影先の固定HUDサンプル範囲へ入りUNKNOWN、残る可視旧STONE≥2全部保持、旧DIRT≥9/非共線、0/±1/±2の9候補で唯一の同方向unit、従来raw/band強条件・world blur95%/両領域各100/全73比較15pp差・axis75%/同領域/全73差を全てANDする。保護・商品・未知次セル・別材質・原点矛盾を拒否する。HUD外の消失やcontradictionを許可しない。

## 3. 実3: 新しい入口と遠方の床判定

未送信LEFT ticket14のsource243→244で前方3セルの扉・隣の金壁が露出し、同時に遠方DIRT→FLOORが生じた。方向・床の次セル・目標(-2,0)は同じだがreason8→7に変わり、元monotone条件を満たさず停止した。

global monotoneを緩めず、前方3セルの新bracket扉、片側の旧金保存と他側の旧DIRT→GOLD、方向/target/FLOOR一致・reason8→7、DIRT→FLOORは遠方≥6かつ原点/次セル近傍/保護外だけ、旧GOLD/DOOR/STONE/ITEM保存、残変化は旧monotoneという限定proofを検討する。厳密BLOCKED・確実未送信・元ticketの全時刻/ordinal/chain2/run8と完全Decision検証を維持し、既FRESHへ退役/別ID再予約する。未確認ACKの再送や元入力creditの流用はしない。

## 4. 実4: 薄い鉄扉の開通

source108→115は画面移動0で鉄扉が開き商人が露出したが、薄い閉扉を25×25中央値でFLOORと読んだため、既DOOR→FLOORの開通確認が成立せずBLOCKED停止した。商品は未確認。Perceptionで既FLOOR・上下GOLD bracket・原点以外・非HUD・商品UNKNOWN・非保護のセルに限り、tile基準cx−8..cx−5、cy−23..cy+1の4縦列を調べる。中立色minRGB≥45/max−min≤45の支持≥20/25かつ上12行/下13行で各≥8を3列以上要求する。実108は各列19/21/22/22で後3列が両帯を満たし、開扉後115は3/12/13/13で全列不成立となる。

元の一般tile閾値・木扉・他材質は変えず、薄鉄の限定pixel証拠からDOORへ回復する。短い線/横棒/片金/色ずれ/範囲外/保護を拒否し、通常FLOOR全体を扉へ変えない。開扉は0歩で既DOOR_OPENED経路を使い、その後の進入/下側商品可視を実機で確認する。

## 5. 判定kernelの意味不変整理

のろい以外の全商品識別/新しい陰性確定や閾値変更を混ぜない。icon内の累積4本をint32へ縮め、total²・total×target_sumの積は左operandからint64へ拡張する。n≤344/RGB≤255でdot≤67,105,800、total≤263,160、square/cross≤201,317,400、中間も全てint32内。gain×byteの同じvolatile binary64積を256個へ一候補位置ごとに保持し、同じ積を再利用する。演算順・round・全slot/word・first-tie・rawprotocolは不変。

追加回答により「判定だめそう」はiSHの「不明」表示が理由と確認した。unknownの表示literalだけを「のろいのゆびわとの一致は未確認（対象なしとは未確定）」へ変更し、全品種識別結果/陰性確定との混同を避ける。outcome/schema/判定条件/制御は不変。表示訂正はsourceの厳密逆変換比較と選択済み関連で確認し、実装を写す新テストは増やさない。

これは振る舞い不変の整理として、既Green・保存済みmode0/1原309/235packetと今回204の全raw同値を結合する。source15検証を削らず、最終static i386/manifestを再生成・同toolchain再build照合する。開発秒を実iSHや人超えの合格にしない。

## 6. 実装と試験

各歩行変更は公開C/controllerの有効assertion Red→最小Green。原画像で確認した証拠の陽性と、HUD外・石矛盾・非unit/逆・保護・商品・期限/予算・旧ID・非bracket/薄い床等の拒否を検証する。原Sceneは校正とし、未来の画像を作って商品到達再現とは呼ばない。変更部と関係する既単体だけを選び、無関係な旧全33群や全Runtime故障は再実行しない。共用現C解析probeを再利用し、原画の無目的な全走査をしない。

## 7. 封印・CI・配布

実patched upstreamとrepo C/source/22seal/API16/cap15/ABIを照合する新090 host selectorで変更部＋関連回帰を実行し、新IPAを標準macos-26で作る。Runtime等の不変範囲は既証拠へbytesを結合し、今回実行したとは呼ばない。実compiler/RSP/Mach-O/全source/IPAの同一性を実物で確認する。新090入口は089の公開・早期判定を引き継ぐ。

製品/文書をskip-ciで保存し必要な配布だけを起動する。完全source/未署名IPA/SHAを新しい固定GitHub Releaseへ保存し、匿名全GET/CRC/全tracked blob/actualtagを照合する。旧公開assetは変更しない。

## 8. 返却と未受入

新IPA更新/LoopCtrl完全終了→起動/Start Server/通常VPNを説明し、通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認を一連で依頼する。返却は自動保存された全run ZIP。実089の追加回収・のろいが出るまでの周回は不要。商品可視・停止位置・暫定判定/全回収の時間を分ける。実到達率・未知陽性精度・毎拍/人超え・OS背景通知/対象なし循環は単体や静的reviewだけでは受入にしない。
