# TEST082: 材質の境界と移動確認

2026-11-12（日本時間、11日受領のTEST081実機5回）。baseline `7d4f8f435ad54daca79a1ec89b04dfdc6d30e625`、code3676018/build135。実機の商品可視を主指標とし、原因を確認した3点と不足した停止証跡をまとめる。独立レビュワー1名、局所単体と関連回帰、必要な新IPA/固定Release照合。全Runtime/worldは追加しない。

## 根拠・期待・限界

実順1316c4ca→8e384afb→b2166957→48d5cb3c→8529e709。5ZIP/97原PNGをSHA/ZIP・PNG CRC/PIL/896×414/閉schema/client_load/manifest全offset・hash・cursor・prefix/test069公開gateへ照合。全terminal/drained/paused/完収、原275 stable prefix19に3商品100/50/100を視認し到達1/5。正常見送りの判断source18/18保持、全取得画像保存ではない。raw/Scene/数値はGit外received081/test082-*。

4は全6ACKが実MOVED。原111→112の同じ次床はRGB44/26/23→47/28/24でFLOOR→DIRT、通常NavのUP→DOWNへ変化した。原120→121でも同じ世界床が45/27/24→47/28/24へ揺れる。strict0、金/保護は不変。5の初回source21は上左の半可視床口をDIRT判定して候補mask0。口の旧full中央値7/3/3、上12行がほぼ黒、下13行には床textureが見える。最初FLOOR17→source21は232.662msで元200ms不足ではない。

1は原160→178で実UP1だが元窓内begin/ACK後8UNKNOWN。最終CreturnにもvisualD残約1.868秒。旧075 worldBlurは477/10bad/帯372・105、旧STONE3全保持unique9、左右phase有限・gap>.35で成立する別のAND根拠がある。5の原341→360も実LEFT1だがUNKNOWN。材質案で2STONE対応は戻るものの旧pixel支持/95%/phaseが不足し、試した別固定面も不成立。**5の最後の移動確認を解決済みとはしない。**

2はcapture128で未送信票が退役し独立静止観測へ。128/129原画とscene_change行がなく最初の拒否は未確定。保持126→130には材質/経路変化があるが欠落原画を補完しない。5のhost result_json期限4件/取消2回はnative movement停止と区別し、完収の再回収は依頼しない。

## A: 原pixelによる材質の追加証拠

Perceptionの旧palette/閾値/既GOLD・gate・wood変換を変更しない。元tile分類とgate/wood変換の後・merchandise前で、**既DIRTだけ**を再検査する。新しいScene enum/ABI/疑似金・将来画像・位置だけによる床化は追加しない。

- bright FLOOR: 元floor条件のうちB下限だけを外れ、RGB/分散の他条件を満たす39…52のfull中央値を対象にする。差 `55R-(100B+155)` は1…77だけ。77は8bit半LSBの係数上限 `(55+100)/2` の整数部分。事前固定した二つの分割、upper/lower又はupper-right/lower-leftのいずれかで、**非重複の両領域**が元floor palette/textureを満たすことを追加要求する。採点から都合の良いmaskを選ばない。
- 半可視FLOOR: full中央値が黒側6…12の既DIRTで、固定上12行の95%以上が黒、固定下13行の90%以上非黒・R中央値16…52・元floor palette/textureを要求。黒は元unknown入口条件R<6又はG<3で定義する。観測された下側の床pixelを根拠とし、外側UNKNOWNはUNKNOWNのまま。候補検出・移動権限は既Navの観測床/固定口/保護検査を通す。
- STONE: 元STONE条件のうちB下限だけを外れた既DIRT、元R/G条件を保持し `100B-53R` が−76…0だけ。76は `(100+53)/2` の整数部分。固定upper-right/lower-leftの非重複両領域が元STONE条件とtextureを満たすことを要求する。

各floor witnessも元unknown入口を除外しR≥6/G≥3を必須にする。中央値黒＋少数ノイズで分散だけが立つ画像をfloorとしない。純黒/低texture/暗いDIRT/木扉/未知/保護商品/HUD/金/既STONEを根拠なく変更しない。prototypeの校正97枚では29セル（FLOOR20/STONE9）の変更だけ、全29を原画で材質視認。非tile Scene bytesは全不変、見送り18枚では原21だけ候補0→bit0、他17は0を維持。これは既資料の校正であり未知評価ではない。最終製品でも全差分を照合し、真正wallの誤床化があれば修正する。

## B: 無金通路のunit確認を既証拠のANDで追加

Nav末尾の全旧判定後UNKNOWNだけにhelper1個とcallを追加し、旧全文/順序を保持。両FLOOR/GOLD_CLEAR/GOODS_UNKNOWN、全GOLD/ITEM/保護0、旧origin/実nextと最新origin床を要求する。元high raw score>.45・best/runnerupとも有限・gap≥.08・入力と同じ厳密9px unitを要する。

旧074 `unique_terrain_translation`（全旧STONE保持、少なくとも2点と非共線の保持DIRT、全9translationで唯一）と、旧075 `independent_phase`/`world_blur_texture` をそのままANDする。全21依存/固定52帯、元contrast/support300/95%/両帯各100/全73・元15ppを維持。独立phaseの両bandも有限のunitとrunnerupを要し、INF差をgap成立と呼ばない。MOVED unitのみで、開通/入店credit・元source/reference/期限/UNKNOWN再送権限を追加しない。5の金壁caseへ一般化しない。

### B2: 材質補正で露呈した既知unitの回帰

最終97原画/36保持ACK比較で、2のLEFT/source116→126が旧MOVED→UNKNOWNになるP1を発見した。正しいFLOOR2復元で075 worldBlurの8px競合がsupport384へ増え、9px unit574/18badと8px384/29badの一致率差が4.416ppとなり元15ppを満たさなくなった。旧判定は競合support<300で比較対象外だった。材質を偽DIRTへ戻す、HUDを解除する、15ppを緩める案は採用しない。

このpairは旧075のL corner一意(+1,0)・raw best .598053/gap .179268・左右有限phase/競合gap≥.095074・worldBlur品質96.86%/52帯244・330を満たす。旧5依存のraw gradient面は884/63bad・65帯666/218、全73の最小不一致率差15.4539ppを満たす。既detail95%や別contrast面は不成立として棄却した。

別の最終UNKNOWN/無金unit証明として、Bの両FLOOR/CLEAR/GOODS_UNKNOWN/全保護・金・ITEM0/実next床/high raw有限unit・gapを同じく要求し、旧075 L corner unique9と左右有限phaseを使う。**worldBlurは95%品質/support300/52両帯各100、旧raw5依存gradientは75%/support300/65両帯各100と全73元15ppの識別**を別々にANDする。支持を合算せず、blur自体が15ppを満たしたとは呼ばない。gradient側はこの組合せで75%の品質条件を新規採用することを明記し、旧gradient95%・旧075blur15ppのhelper本文は変更しない。新maskや採点に応じた領域選択は追加しない。固定2領域のphase、95%品質面、別面の競合識別を混同せず検証する。

追加公開正例の意味Red→最小Greenと、各面の品質/支持/帯・全73競合、L geometry/finite phase/score/非unit/商品等を個別に崩す拒否ケースを必要methodへ追加する。修正後だけ保持pairを再集計し、既knownの回帰を解消したことを確認する。未変更methodの単体全体再実行は行わない。これは5の金壁caseへは適用しない。

## C: 静止観測で拒否した原画を既診断へ結ぶ

Controllerのstationary waitで独立観測をSCREEN拒否する直前に、既record_changeを使える狭い条件だけで診断を残す。未発行OBSERVE/READY、begin0/outcome3の退役済み旧MOVE、pendingなし、元before全bytesと固定anchor一致、同world/安定current-prefix・id>trigger/start≥trigger_endの独立観測を要する。実scene_change maskが非0の場合だけsource/observed ID・材質差・replan_allowed0を記録する。既schemaはmask0を拒否するため、signature-onlyに偽bitを立てない。

source/比較が虚偽になるISSUED・別anchor・入力済み/UNKNOWN送信・旧世代/非独立を対象外とし、ROUTE/MOTION等の既validationを実際の拒否箇所と対応させる。失敗理由/入力/全票/期限/予算を変更しない。既3行first1/latest2とRuntimeの比較優先だけを使う。これは2の未確定原因の修正済み宣言ではなく、次の拒否画像の欠落を減らす診断修正。

## 実装・検証・配布

Aは公開analyze_RGBAの手続画像でbright/半可視/STONE各意味Redを先行、brightの実現可能な最近接境界75/85（R39…52/RGB8では77/78は実現不能）・STONE76/77、非重複片側不足/共通quarterだけ/分散/黒/木・金・商品/HUD等を6〜7methodsにまとめる。Bは公開motionの4方向正例・scope・地形unique9・旧各planeと競合/依存/境界・逆/非unit/既knownを6methods前後とB2の必要追加へ絞る。Cは公開Cの同じSCREEN退役と新診断行をRed→Green、source/anchor/mask0/署名のみ/期限・prefix/商品優先の拒否を必要methodsで確認。各作者だけが新規試験を実行し、変更method以外の反復を増やさない。既試験assertは削らない。

関連はPerceptionの既palette/gate/商品/fringe、Navの旧074/075/079…081、Controllerのstationary wait/保存schemaから明示選択する。各元原画の旧known/UNKNOWN・Nav full5変化を読取比較し、入力回数を成功としない。独立1名が計画/最終差分と実ログを確認する。

予定製品はPerception/Nav/Controllerの3source（他19不変）。Runtime048a…、API1.98.16/cap15/client16/profilev2・20PNG/10MiB/旧v1回収・G1/R12・全凍結期限/入力予算は同一bytes。新Runtime Mac Redは不要。旧070/081保存fixtureは今回ビルドでの実行と過去Red133を区別して結合する。実compiler/全MachO/全tracked source/IPA・固定Release匿名全GETを照合してTEST082を返す。通常1-1ポーズからrestart→候補→商店→全商品確認を5〜6回、全run ZIPと結果を依頼する。見逃し率/恒久毎拍/人超え・対象認識/通知/対象なし周回は未受入。
