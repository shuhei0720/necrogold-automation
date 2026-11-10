# TEST073: 再開直後の見送りポーズを待機する

2026-11-11（日本時間）。baseline `c99f3850b315c82ef2330d50460415b6527e34b3`。通常の局所修正として単体/関係回帰・独立差分レビュー1回・必要な新IPA/実物照合・一連の実機試験を行う。

## 根拠と期待値

TEST072の実行順は2dd614cc→bd252a30→bd74dabe→f1bafe8d。全4ZIP/45PNG（16/7/7/15）のhash/CRC/bytes/896×414/manifest/cursor/prefix/report一致、全回収resolved/terminal/drained。

1は5MOVED+1開扉+商品優先UNKNOWN1で3商品100/125/30、4は6MOVED+1開扉+商品優先UNKNOWN1で3商品100/50/100、両GOODS/PAUSE成立。4には未送信too_late履歴と空拍があるが、その後の回復で商品へ到達している。今回この成功経路の速度/認識処理は変更しない。

2・3は通常FLOOR/CLEAR/実gold0/商品0/保護0/通路候補0。RESUME ACK後71.289ms/90.355msで見送りPAUSEを送ったが、ACK後もゲーム時刻1.61→5.90/1.57→5.82と進行、メニュー無し。最新画像は終端直前まで正常に受理、約4秒後CAPTURE理由で終了。RESTART未発行。取得/RPC障害やCLEAR不整合guardではない。UIが受け付けなかった物理原因と必要な待ち時間は未確定で、相関を実証と呼ばない。

期待は「候補なし→PAUSEの実成立→RESTART→次ラン→候補→商店→全商品確認」。送信ACKだけでポーズ成立にせず、既知失敗/未知送信の再送で通さない。

## 限定設計

既存のPAUSE→RESTARTにある200msのUI待ちと揃え、最後にACKが確定したRESUME/RESTARTから200ms未満ではPAUSEを予約しない。200msは今回の対策値であり端末の最短受付時間が測定済みという意味ではない。該当ACK後200ms以降に取得を開始した、最新stable/current-prefix FLOORが必要。時計だけ進めて古い画像から予約しない。

bounded events内の最新ACK済UI遷移を使い、旧callback・未送信・UNKNOWNを時刻根拠にしない。差分比較でoverflowを避け、level resetでも元のACK履歴を保持する。RESUMEなしで既にFLOORの場合は従来どおり。既に200ms以上経った商品確認後のPAUSEには待ちを足さない。

tickの見送りPAUSEと保持PAUSEの予約前、beginの最終判定へ適用。商品latchと追加MOVE/RESTART禁止は即時、物理PAUSEだけ必要なUI待ち/新鮮画像の証明を満たして送る。既にPAUSEなら余計な入力をしない。UI待ちの間に金/通路候補/商品/不明画像/取消が見つかれば最新Sceneの判断を優先する。level内inputs/moves0・原点・lead未確認の未送信見送りでは、初回候補0でも最新clearSceneの通路口を再検査し、候補出現で旧PAUSE/RESTART票を永久撤回して最新start_floorへ移る。送信済PAUSEから新MOVE/RESTARTは出さず候補保持、ACK済RESTARTは新levelのfingerprint証明を先に行う。

Controllerだけ変更、Runtime/Ticket/Nav/Core/Perception/取得/各閾値/API16/cap14/v15/wire/ABI不変。元16入力/12restart/45walk/180session、source3秒、遷移4秒、UNKNOWN無再送を維持。新たなPAUSE再送は実装しない。

## TDDと回帰

新public-Cで大きいuptimeも含め、RESUME/RESTART ACK+71/90msで予約0、200ms境界、時間だけ経過/古いprefix/交差・古い画像拒否、post-cutoff新鮮FLOORで1予約、旧ID/owner/foreground/lock/取消/UNKNOWN拒否を確認する。商品は即latch・待機中方向/RESTART0・準備完了後PAUSE、既に時間が経った商品PAUSEは即時。通路/実金の出現は見送りより優先、全予算は延ばさない。

既存のresume/restart成功fixtureでACK+100msのFLOORから即PAUSEを期待する箇所だけ、新鮮な200ms後画像へ時刻を調整し全assertを維持する。失敗timeout/旧callback/新level fingerprint/12回上限/072の一連flow/商品保持を関係回帰に選ぶ。合成UI応答や200msを実端末の受付成功と呼ばず、次の実機で確認する。

## 保存・返却

新073入口/launcherは既存のlocal永続保存と全画像/ZIP検証済公開を再利用。native1変更/他21をsealし、標準public Mac/Ubuntuで必要な単体/関係回帰と新IPAを作成。実compiler/全Mach-O/全source/実行IDを照合し固定Releaseを匿名取得確認する。無変更Runtime/worldの全試験は追加しない。

実機は候補なしの開始を含め、リスタート→候補発見→接近/入店→全商品を一連でまず2回。短いrestartポーズ中はゲーム前面、ポーズが5秒以上続いてからiSHへ戻り全ZIP保存完了を待つ。回収済み072の再実行・追加回収は不要。画像・ログはGit外。
