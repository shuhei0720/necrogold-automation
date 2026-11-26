# TEST122: 価格に依存しない全商品帯の対象なし証明

2026-11-26（日本時間）。基準は出荷TEST121/CODE4574786、保存HEADd78159a、Ring6127e5f9/Controller554b6ae4/Perception19ff0492。**本書は短計画のみ。正式assertion Red・製品変更はrootの別GO後に行う。** [要件](../requirements/necrogold.md)・[対象契約](../contracts/target-assessment.md)・[native契約](../contracts/native-control.md)・[修正表](../fix-records.md)を維持する。

実施追記: rootの正式GO後、原124の正常producer→新21/4/NEG→Ring証明1/独立C1を期待する旧121のassertion Red、procedural4件のRedを確認し、最小実装と関連検証へ進んだ。製品はRing426c19d2/Header7c067c31とnegative専用C hunkへ固定し、独立combined差分確認を行う。以下は承認時の設計と、実装時に確認した限定補足である。

## 原因と採用判断

TEST121実機の第2root de9f/source124/job2は、正常producerのOK/UNKNOWN・incomplete・policy7/PRICE64を元Dより56,066,834ns前に採用し、PAUSE ACK→耐久保存→GOODS終了した。未分類・期限超過・誤NEG・独立CによるNEG拒否ではない。原122〜125で旧120/出荷121のSceneは同bytes、Ringはchecks以外同値だった。

中央の価格は[299,235,10,8]と左右より下がり、同じx列の小さい白断片もある。既`side_separate_price_witness`は原画で成功するが、通常row_count=1のsingle policy7はそのhelperを呼ばず、count0の別row発見時だけlayout3を使う。FR119の適用漏れである。ただし今回さらに白価格patchを重ねず、ユーザー指定の「全商品登録・名称確認・価格確認を必須にせず対象の絵柄を判断する」に従い、**正に閉じた全商品帯を別の新coverageで証明する**。旧7のUNKNOWNを直接NEGへ書き換えない。

原124は既single-sign構造とexact offer footprintがともに1、全3下床FLOOR、両元endcap1、raw3物体のbright支持420/407/282（元24以上）、merchant .996278409/coverage1、唯一row(267,153)が成立する。原画像・SHA・source/prefix・clock/D・採用はGit外`analysis-evidence/test122-goods/{cause-calibration,normal-results,guard-results}.json`に結ぶ。これは既知原画の校正であり、新正常producerや実機改善の合格ではない。

## 新しい正の全被覆

対象をnormal mode2の単一完全SIGN＋既merchant認証に限定する。原観測から一つの物理商品列を選べる場合だけ、以下を全ANDとする。

- 既`single_sign_scene_row`の7以上の実GOLD、5セルsolid side、対向2post、同段のFLOOR/DOOR入口、完全faceとcount150以上を要求する。既merchant全phaseのscore≥.94/coverage≥.95、36×36の実boxと元位置範囲を保持する。新relative glyph認証は追加せず、SIGN以外の余剰物理看板を捨てない。
- 既`offer_footprint_scene_row`の全230セルを検査し、同じ列の正確3ITEM・余剰ITEM0・全canonical halo同値、下3FLOORと左右の正FLOORを要求する。PARTIAL、下床UNKNOWN、欠商品、余剰商品、halo欠けには資格を与えない。
- 同じopaque RGBA原画の非HUD中央領域にB=[left−54,sy+24,180,67]を完全内包する。各36×42の元商品窓でluma>55の支持24以上を測り、`observed_items=3`を実測から得る。商品名・catalog ID・閉宝箱の分類は要求しない。
- 両側25×25の元`endcap_witness`をそのまま要求する。floor full/upper/lower=1、可視90%以上（black≤62/625）、bright<24、元白ink<18・元色/textureを保持する。ここは商品の外側が空である証明であり、商品価格の読取りではない。各capの`price_ink_count`には実測した外側白inkを保存し、0に偽装しない。
- 元1〜4 rowをすべて保持し、選択rowとのleft/sy差各±2かつ同じ整数world列へ閉じることを要求する。各aliasの全5cell・全canonical target spriteの整数poseと広い名前unionを、既kernel/閾値/順序で最後まで検査する。TARGET/CANDIDATE/名称vetoを先に保持する。先頭partial2件は選択row両端の実sweep、元alias union外のpartialは元順tailとして残す（総数2〜12、超過/重複/不正座標は未確認）。tailを追加商品の被覆に使わず、全tailの候補・名称保護を維持する。

全条件を満たさなければ元UNKNOWN/incompleteを保持する。非OK、取消、期限超過を正常UNKNOWN/NEGへ変換しない。既旧branchの完全陰性を先に返すため、旧成功に新認証や追加sweepを課さない。

row発見にも価格依存があるため、元`ring_observe`を変えず、新21内だけ元row_count=0のときに実単一SIGNのcx/syから一つの相対候補を導出する。完全faceの実幅/高さ各29〜30と上記全Scene/auth/raw3/cap証明で閉じ、全5cell/word/元partialを必ず検査する。固定座標、未観測商品、名前や価格の補完は行わない。原124のrow_count=1・既完了proof再利用とは別の正の発見である。

## 数値表現と独立consumer

`policy_version=board_mode=21`、`layout_version=4`を新しい価格独立証明専用にする。現行Ring/Controllerのlayout1〜3とpolicy20までの分岐を検索し、21/4に既存採用を見つけていない。実装前に全consumerの検索結果を固定し、旧tagとの混用を拒否する。struct/field追加なし、RingResult6112B・既POD/ABI/API/profile3を維持する。

`observed_prices=0`・`unmatched_prices=0`・3つの`price_boxes`全0は、**新tag下で価格証明を使用しない**意味とする。「価格が存在しない」「3価格確認済み」とは解釈しない。`name_boxes`も全0とし、word探索の実値は各slotに保持する。merchant/単一board/両cap/item_boxes/strip/各aliasとtailには実際の数値を保存する。`unmatched_items`は元item_witnessの実測値と0..(180×67)/24の元範囲を保持し、原124の2を消去しない。余剰の実ITEM/haloはScene検査で拒否する。`observed_items=non_target_items=3`はraw3存在＋全target sweepの証明であり、商品種類の登録を意味しない。ignored_containers=0で宝箱の中身を証明しない。

- `NG2Ring.c`の新coverageを既完全陰性の後・最終UNKNOWNの前に置く。既alias sweep/局所memoは同immutable呼出だけ再利用し、原画像を変更しない。`ng2_ring_negative_certificate`は21/4専用検証へ明示dispatchし、元数値範囲・全box/score/zero-field・auth/cap・全alias/partial/tail・候補拒否を検査する。旧policy consumerへ正規化しない。
- `NG2Controller.c`の`cycle_negative_witness`は21を専用structural witnessへ分ける。producerのScene/verdictを信用する代わりに、自分の`cycle_anchor`のFLOOR/FULL、exact3ITEM/halo/下床/GOLD/enclosure、full_seen、非partial/非candidateとpacket全数値を独立検査する。旧`cycle_structural_witness`と19/20の条件は緩めない。source/run/owner/世代/clock/prefix/jobの既採用guardは既入口で維持する。
- `NG2CycleWire.swift`のcertificate出力、spool/checkpoint/terminal、iSH collector/ZIP/recoveryの全consumerを確認する。既int/boxを変更せず保存できることを、実3.9で新21/4・価格0の保存/回復原bytesへ結ぶ。過去packet/validator/履歴は変更しない。新証明の識別はTEST122の専用capへ結び、rootが起動側と調整する。

## 所有・期限と意味Red

製品候補はNG2Ring.cの限定coverage/数値検証、NG2Ring.hのtag定数、Controllerのnegative dispatch/専用structural witnessだけ。Controllerのupper/current DATA helper・移動admissionはmovement担当で、全file上書きをしない。7a9/source234は元cap条件でUNKNOWNを保ち、235/236の既normalNEG7採用は別DATA計画へ分離する。

source150ms/worker100ms・元D/P/W・取消/owner/prefix・全上限・UNKNOWN無再送・候補先・耐久保存/既PAUSE/RS資格を保持する。追加MOVE/worker/期限延長をこの証明から与えない。全価格が不要でも元D内の正常producer完走と独立C採用が必要である。

性能は同immutable呼出の**既完了pixel proof再利用を優先する**。de9の旧処理はworker開始から採用まで約44msで、元worker100ms期限の残りは約56msである。旧`coverage121`が価格で失敗しても、呼出内の`OfferSweepProof proofs[4]`には完了した各aliasの全5cell・word結果、row/両端partial/stripが残る。新21へこの同じ配列を渡し、同row-index・left/sy・strip identityと完了資格が一致するaliasだけを既reuse経路で採る。元のalias順・候補先・tail保護・reuse時checkpointを保持し、別画像/別呼出/別sourceの結果や数値certificateをpixel proofへ代用しない。原124は新21による追加pose/bound実計算0を確認する。未完了aliasだけ既kernel/全対象/整数visit順/全checkpointで走査し、既`NG2BoundCache121`の有限局所memoを使えるが、これは各sweep終了時にfreeされ、前のsweepから自動共有されるとは扱わない。全出口で解放し、失敗時にNEG資格を作らない。

原124はreuse有無の正常producer全packet・候補/tail・独立Ring/C証明を比較し、追加pose/bound実計算数・checksと実時計費用を校正する。旧成功5packetと19/20全7caseも正常packet/独立Cを保持し、別caseの追加費用は別に測る。100/150ms・元Dの合格を時間assertの緩和で作らず、Linux/Mac host時間やclock固定の校正をiPhone速度/期限内完走の合格へ流用しない。新21/4・価格0の実3.9保存/復元確認も予定のまま維持する。

GO後は、まず出荷121に対し「de9原124の通常producerが正の新21/4で完全NEG、Ring数値証明1、対応own-anchor C採用1」という意味のあるassertion Redを実測する。手加工packetでNEGにしたcut、compile失敗、clock固定だけの時間診断をそのGreenへ数えない。次に最小実装で原124を通し、元UNKNOWN・商品欠け/未観測・merchant欠け/偽face・halo/下床欠け・alias/tailの対象候補・非finite/不正box/tag/価格field非0を拒否する。通常public lifecycleの陰性→durable→既RS資格は別に検証し、実iPhoneのRS成功とは区別する。

旧成功5packetは全6112bytes同値、新121のpolicy19/20全7caseと直接関連の候補/UNKNOWN/独立C改ざん拒否を維持する。procedural画像の価格非表示・名称非表示でも他の正証明が完全なら新証明を妨げず、商品本体や観測欠けならUNKNOWNにする。独立差分レビュー1回の後、rootの選んだ関連結合・実IPA/封印/完全source同一性確認へ進む。実機の商品確認・継続・速度は次の実機結果まで未確認とする。
