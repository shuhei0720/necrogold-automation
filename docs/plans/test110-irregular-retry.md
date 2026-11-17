# TEST110: 敵による進行不能・死亡の明示的な再試行

2026-11-17（日本時間）。[最新要件](../requirements/necrogold.md#2026-11-17-敵による進行不能ゲームオーバー時の再試行)・[通常4停止](test110-device-failures.md)。基準c2f7624。新入力/保存境界を伴うため、本設計の独立重点レビュー後に実装する。入力権限・ABI・数値・保存予約の正本は[明示契約](../contracts/irregular-retry.md)。本文との相違は契約を優先する。

## 1. 概要

新capability `necrogold_native_irregular_v1` / profile `normal-1-1-irregular-v1` を明示選択した新TEST110だけ、正に確認した進行不能/死亡を再試行する。旧profile/Scene・Status・Eventのlayoutと旧action1〜4のschemaは維持し、API全体の緩いenum上限変更をしない。API `1.98.16-ngg2` を維持し、新query/schema/journal revisionを明示分離する。確定名・閉集合は上記契約に従う。

## 2. 背景・証拠

今回4run/98 PNGには死亡/被害の正の証拠がなく、近くの敵は停止原因と断定できない。通常4修正と分離する。R12の死亡prompt「ゲームオーバー！ タップで続行」は既資産から観測可能だが、タップ後の実画面は未受領。既死亡maskはFLOOR拒否用であり、単独boolを入力許可に変換しない。

## 3. 詳細設計

同じimmutable RGBAから別companionで死亡prompt/再開選択を正に検出し、従来Scene出力の意味を上書きしない。Runtimeの既owner/generation/取消・prefix/stability/取得両端/commit時計gateでCへ結合する。元画像を他runや別prefixのboolに取り替えられない構造とする。

進行不能は `stalled_after_ack` と呼び、敵の種類を推定しない。同MOVEのACK既知、入力前にlead確認済み、元beforeのorigin/進行先は観測非保護FLOOR。現在originもFLOOR、進行先はFLOOR又は正のenemy/bodyが当該セルを遮るUNKNOWNだけを認める。両post-ACK画像の指示方向enemy/body、同じ進行先/地形、元before画像へ通常strict BLOCKED零が必要。UNKNOWNを床へ補完しない。独立2画像は少なくとも元periodだけ離れ、後者は元earliest+period以降・元visualD/8比較内。早いanimationの2静止だけで再試行せず、途中のMOVEDは通常確認へ、UNKNOWN/TWEEN/非零を静止へ丸めない。

FSMは `quiesce -> checkpoint durable -> UI qualification -> restart intent durable -> RESTART -> changed normal floor -> outcome durable`。旧MOVE/slot/model/proofを撤回し、開始済callback/workerが実際にdrainするまで入力しない。pending Ringの正の対象/候補が来たら保持を優先する。障害/不明を商品陰性にせず、completed_shopsを増やさない。

生存時は新しいFLOORから通常PAUSEを1回、実ACKとfresh PAUSE/実restart labelの後だけRESTARTする。死亡時は全prompt・HUDと空のheart領域等の独立証拠から、専用action `DEATH_CONTINUE` kind5を1回だけ許す。promptの実観測点へtapし、RESUME/PAUSEへ偽装しない。ACKはリスタート成功ではない。

死亡続行後は新しいPAUSE/label、又は生きた通常1-1 FLOORからのPAUSEを認める。別result menuの場合は、有限の中央ROI内で既Quick Restart全glyphの唯一の一致clusterを探し、独立2枚のstable/current-prefix画像で同じ実bboxを確認して座標を導く。元glyph/visibility/色の正の支持を検査し、欠け/全面白/複数候補/別scale/残った死亡promptは拒否する。実メニューを認識できない場合は `irregular_menu_unrecognized` で画面を保持する。旧PAUSE座標の流用で成功扱いしない。

episode親Dをtrigger時に元transition/walk/sessionの最小で固定。保存・再観測で延長せず、各UI ticketも新しいsource/期限を持つ。12restart/16方向/45秒walk/180秒session、heartbeat/取消/前面/lock、UNKNOWN synthの凍結と無再送を保持する。再試行の新しいcampaign handoffを今回勝手に作らない。

## 4. 影響・互換

候補sourceはPerceptionの別positive companionと宣言header、CのFSM/companion getter、Runtime/CycleWire/Spool、new-profileだけの厳密client/parser/journal、新entry。既Ring/Nav/feature/canonical15/ELF/G1/R12は保持する。新Csourceが必要ならcompiler whitelist/sealの閉集合へ明示追加する。新wire companionとkind5は新profileだけ。旧request/response/保存原本へ余分fieldを混ぜない。追加file/API・288B companion・136×39全成分halo・kind5・保存tokenの集合は上記契約で確定した。

## 5. 新規試験

正の死亡promptと部分glyph/不正HUD/alpha/寸法/旧Scene不変、既知ACKの元period離れ2静止/全拒否、公開Cの保存・資格・intent/ACK・新floor、死亡続行1回・未知menu保持・唯一glyphと複数拒否、取消/owner/prefix/元D/保存失敗/UNKNOWN入力をRed→Greenで検査する。

現在の実Swift Runtime callbackでanalysis/control/main/saveの受渡し、pending positive、取消race、unknown fastTapの凍結、実drain/保存、診断画像保持を選択結合する。Python3.9で新旧profileの閉schema・kind上限・回復journal/ZIPを検査。手続きのmenu画像を未受領の実機画面として数えない。

## 6. 実装順

確定契約の独立設計/網羅/安全レビュー→機能ごとの実Red→positive detector/C FSM→Runtime/保存/parser→選択結合→独立最終差分レビュー→same-source seal/CI/IPA/実物照合→固定配布。通常4修正は並行するが、敵によるリセットで通常不具合を覆い隠さない。

## 7. コミット前確認

最終source/method集合、作者の元source/fixture/hash・実Red/Green、旧profile拒否assert、現在Runtime/境界の実選択結果を結合する。旧Mac191は新入力経路の証明に使わない。標準runner・実compiler/全source/IPA/Mach-Oを照合し、実機で未確認の範囲を残す。

## 8. 範囲外・返却

一般的なSCREEN/UNKNOWN再開、未知inputの解決、敵sprite全カタログ、未知メニューへの盲tap、商品陰性への偽装、対象/候補破棄、購入/宝箱、元予算の無限更新は範囲外。配布時に通常4修正とイレギュラーで実装した範囲・未受領の死亡後menuを分けて短く説明し、通常1-1からの実機テストと全照合済ZIPを依頼する。
