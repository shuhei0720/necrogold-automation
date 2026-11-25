# TEST120: 普通PARTIALのbeginと実Runtime送信直前gate

2026-11-25（日本時間）。[全体計画](test120-device-failures.md)・[同一零proof計画](test120-partial-proof-cache.md)に対応する最小Mac境界。caseは `partial_begin_dispatch` の1件、短いsubrun `normal` / `post_guard_late` の2本だけとする。計画段階であり、新checker/fixtureの実装・CI実行は未着手。rootのレビュー・GO後に着手する。

## 確認する境界と保持するもの

実2d1は原287/298/300が正しい2商品PARTIALで、CはLEFT22を承認したが、RuntimeのsendNowが元Dを50,136ns超えた。begin_nsからsendNowまで7,466,542nsはpreparation/getter・Cbegin・外部owner/lock/時計を含む全区間であり、実機のC単体費用は未記録。この全区間をMotion費用と断定しない。

`cycle_partial_static` はvalidation enumを返し、0（`NG2_REVALIDATE_NONE`）が成功である。通常のstatic/route成功後、旧 `cycle_partial_relation` は必ず元anchorから通常Motionを再計算する。新実装は同じ元anchor/current・予約済commandに得た直接strict BLOCKED零だけを再利用する。この旧beginのMotion1回→新hitの0回を実sourceへ結び、その後も同じ実Runtimeのmain/post gateが元Dを守ることを確認する。

Runtime原本SHA256 `58c6de6535dbe204e0e9ae39958a5e4c0edfc80a92a428e5b29cb0843d44a420`、shared fakes、既119正式fixture、Perception/Ring/kernelは変更しない。元10ms/D/P、source150ms/worker100ms、通常準備・鮮度・owner/取消・UNKNOWN無再送・epoch getterの意味を維持する。raw preparation_epochと公開getterが返す0を同一視せず、新proofはstamp時のraw epochも含む完全一致を製品側で要求する。fixtureからprivate proof/Scene/resultを注入しない。

## 公開RGBAとearned setup

新しい公開generator/C fixtureは、既 `generate_shop119_queue_pixels.py` のように公開の描画関数と特徴資産を明示的なsource/hashへ結ぶ。通常のRGBAで金入口・内床・独立rail・正に見える対象外2商品と価格を描き、3品目は未観測のままにする。normal PerceptionがFLOOR/PARTIALを返し、normal RingがUNKNOWN/incomplete、partial-safe/no-positiveを返すことを実際に要求する。Sceneのgoods/ITEM/保護やRing結果の直書きは禁止する。

公開C lifecycleで同期・実unit証明・同方向開扉・既知ACKを得るbefore-ACK preludeは、手続き的なcomponent setupと明記する。必要な過去の拍・ACK時刻は模擬setupの宣言であり、実ゲームや過去iPhoneの再生とは呼ばない。画像のRGBA→Perception/irregular解析は各sourceで1回だけ行い、その実費とC setup実費を記録する。私的C状態を保存/復元せず、同じpublic C coreとstatus/command/eventからRuntime bookkeepingを作る。

after-ACKの対象区間はoffset0の実monotonicだけで動く。新RGBAをその時点で生成し、実取得開始/終了・解析開始/終了を持つimmutable frameとしてRuntimeの通常latest/observe/cycleへ渡す。実worker begin→通常Ring→実C採用・callback returnを経てordinary PARTIALの観測creditとfuture MOVE ticketを得る。元sourceと新currentは別IDで保持する。

元anchor/currentには、origin/next・GOLD・ITEM/保護・同choiceを保つ遠隔FLOOR→DIRT等の画素差を入れる。normal Perceptionで実際に材質差が生じ、static validation0と元anchorからの通常strict零が同時に成立することを要求する。差分はside-paletteの既domain内とし、金/保護や未観測商品を補わない。単なる同Sceneに簡略化して実2d1の状態差を消さず、staticが非0になる画像をcacheで通さない。

既HOST `scheduleTicket` seamで予約済callbackを一度保持し、同じ元Dのまま予約後の独立currentを通常Runtime観測へ渡す。このobserveは元anchorから通常Motionを実行し、C-owned currentとして採用されたときだけ新proofが得られる。後から別commandへproofを付けず、既ticketを作り直さない。

## 実Runtimeでの2subrun

| subrun | 実行・期待値 |
| --- | --- |
| `normal` | future ticketの元not_beforeに実時計で到達してから、保持した同callbackを1回解放する。通常preparation/getter→mainのCbegin→post owner/lock/実時計→fastGestureへ進む。予約後observeは通常Motionを実行、新Cbegin/post getterのMotion呼出0。MOVE synth1・実Runtime completeの既知ACK1、同command/ordinal/source・元D/P/入力予算を保持。ACKを実MOVEDや実商品到達に数えない |
| `post_guard_late` | 同じpublic setup/ordinary proofまで進み、Cbeginが元窓内で成功した後のHOST owner guardだけに宣言した有限実費を入れる。ownerの判定結果は維持し、実monotonicが元Dを超えるまでの有界仕事を同じmain gateで計上する。Runtimeの既post guardが `too_late` を記録してcomplete(0)へ進み、MOVE synth0・確実NOT_SENT、旧ticketの再arm/再送0。offset加算やD延長で失敗を作らない |

陽性は実時計のwindowに間に合ったときだけ成功とし、間に合わないhost負荷を時計変更・再試行で成功へ付け替えない。lateはCbegin拒否で代用せず、accepted beginの後に費用が発生し、実post gateが拒否したことを時刻とeventで区別する。両subrunともcallback実returnと取消/drainまで確認し、後続の余分なMOVEを止める。physical capture thread/iPhone/実gesture/毎拍・人超え速度は未検証と記録する。

## HOST計測と費用の一回計上

新checkerは旧119と同じinstalled native37/manifest/driver sourceを照合し、原Runtime bytesに新HOST prefix/suffixだけを結合したstaged入力を保存する。実C/Perception/Ring/Runtime/Ticketをリンクし、単一定義・compiler profile・実argv・object/executable SHAを記録する。readonly counterはControllerの通常Motion callをsymbol wrapperへ結び、同じ元kernelへ1回delegateする。Cbegin wrapperも元public beginへ1回delegateして結果と実入出時刻だけを観測する。結果・時計・private fieldを書き換えない。

late費用は、staged Runtimeからのみ参照するHOST owner adapterをprefix/suffixに設け、元AuthManagerへdelegateした同じowner結果を返す。対象commandの真begin成功をreadonly wrapperで観測した後の最初のpost owner呼出だけでarmし、宣言した有限範囲の実仕事を行う。既fakes/Runtimeファイルの本体を書き換えず、aliasとadapterの範囲・source/hashをreceiptへ列挙する。Swiftのaliasが元owner呼出以外へ影響する場合は、具体差分をrootへ戻してから方式を決める。

画像生成/Perception/irregular/Ring/Cobserve/Ctick/preparation/getter/Cbegin/owner/lock/実sendの区間を同一clockで記録する。包含区間と内訳を二重に足さず、未計測の費用を0扱いしない。preparation epochは既公開getterの観測値だけを記録し、raw private epochの仮定で権限を作らない。旧source runは同じnormal画像・同じ通常producerでbeginの通常Motion1回という指定assertion Redを確認し、新sourceは0回を要求する。計測時間だけをRedの根拠にしない。

## 所有ファイル・実行・返却

未確定なのは、正2商品/side-paletteを通常Perception/Ringで得る公開描画の詳細、原Runtime本体を変更しないHOST owner aliasのSwiftでの成立、通常host実費で陽性が元10ms窓へ収まるかの3点。前2点はGO後の公開producer/compile確認で閉じ、陽性の窓不足は実失敗として返す。未確定を既成功とせず、private状態注入や時計調整への代替は行わない。

この担当の実装予定は新 `check_runtime120.py`、`ngg2_runtime120_tests.swift`、専用C fixture/header、公開pixel generatorだけ。既 `check_runtime119.py` / `ngg2_runtime119_tests.swift` は構造の参照に限り、既formal結果を再走しない。Controller等の製品source・workflow・host selector・seal・配布はroot/各担当の所有とし、この担当から変更しない。

Mac実行はrootが標準GitHub Actions runnerで選択したこの1case/2subrunだけを行う。ローカルCI、全world、無関係な旧fault群を加えない。Linuxでは必要な公開RGBAと通常C producerの事前確認・同じ新fixtureの旧C counter Red、checkerの構文/receipt拒否等だけを行い、Mac callback成功とは呼ばない。旧subject Redは新境界の因果確認であり、旧119 formal Macの再走や3本目の製品subrunには数えない。

証跡は各source/frame/raw/Scene/分類packet hash、anchor/current/commandの役割、通常zeroのcall count、元not_before/D/P、begin/guard/send/ACKの実時刻、first failure、全callback/drain、compiler/全generated input・prefix/suffix/macro/argv/hashを含める。実workflowがteeした `runtime-command.txt` は、tee終了後にrootの最終file inventoryへ必ずbytes/SHA付きで含め、書込途中のhashを最終証跡にしない。

原実287/298/300は校正と拒否guard確認だけに用い、public Mac fixtureに私的画像を混ぜない。正常Mac componentでも実2d1の7.466ms全区間の改善、商品到達、実機毎拍・速度は未確認のまま、次のiPhone受入へ渡す。
