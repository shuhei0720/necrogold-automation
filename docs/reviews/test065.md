# TEST065: 再予約待ちの確実未送信期限切れ

2026-11-10（日本時間）。[計画](../plans/test065-pending-unsent.md)。TEST064受領59PNGの全SHA/bytes/CRC/寸法/manifest、4run完了/drainedを確認。商品可視3/4、自動全商品可視2/4。成功した商品保持・ポーズ/歩行を維持し、4回目state0/SAME待機中の純D超過だけを対象とする。

原画91→92を実Perception/Nav strictO2/Motionへ渡し、両FLOOR/GOODS_UNKNOWN/GOLD_CANDIDATE/origin床・全金/保護同一・full5 UP reason8 target(-1,-2)/FLOOR・strict BLOCKEDを確認。唯一(2,2)DIRT→FLOOR。位置/visitsは観測済み左2歩から再構成し、未収録モデル/未来画像を補わない。capture end D−25.952ms/C開始D−3.816ms/終了D+3.152ms/次tickD+3.357ms。旧event撤回済みstate0/pendingが旧063state1回復条件から漏れてLATE終了した。

新pending6methodを旧4a55 Cで意味的Red（6method/5assert failures/errors0/1.616秒）。修正後の新6＋旧expiry1は7件2.876秒Green。旧expiryの元ID/元D送信不可を維持し、停止期待だけを新将来slot・元予算維持へ根拠付き更新。SAME/FRESH/許可済みreason8 target drift、旧event全bytes/旧callback不変、actualclock/元12秒/45/180、fresh world/金/保護/署名/判断/入力状態/権限/商品拒否を検査する。

pending_choiceを両modeの再検証成功時に保存する。元source全5field証明を弱めず、回復直前のbefore/最新worldと保存判断を照合する。expected pointerだけ旧command_choiceへ戻す限定mutationでsame_driftのみassertion失敗（1method/1failure/errors0/1.069秒）、本筋のbaselineRedとは区別。独立レビュー途中のfixture enum期待は最終化時にSAME=2/FRESH=12へ整合し、新6の独立Green6/6（1.904秒）も確認。最終P0/P1/P2指摘なし。

## CI選択と同一性

新pending6＋064成功経路11＋旧continuous7＋063unsent4＋ABI1のC29、selector3の32を選択。元D/旧ID/counter2/8/prefix/送信済み/UNKNOWN/owner/pending拒否と元episode予算を含む。前回の旧quiet3は064新5の包含、残cadence/unsent/world/Runtime/Kit/client/publisher全体は不変のため配布前提へ累積しない。元試験/期待assertを隠すskipや削除は行わず、選択理由/未実施をhost metadataへ記録する。YAML/publisher不変。

C SHA `d97f217935274d7012db6e69663bfcf52f252cef94cb376a566637d1a8c4fee4`、manifest SHA `ec5ab1802c58bf38c82b292e8e01af94a176f370e875f16becba8dfd99c69524`。Controllerのみnative変更、他21source/公開ABI/API15/cap13/client v14/R12原40/G1は維持。Mac device/実IPA/実compiler/Mach-O/完全source照合の結果を配布前に追記する。実機TEST065は未実施。

3回目の金集合変化による正当拒否と、看板が画面外で商品UNKNOWNという残課題は今回変更しない。原画の商品可視とプログラム完了を区別し、次の実機で到達率/拍の空きを評価する。


## 最終Mac100・実配布物

code `51f555d47b7d703935e8ae2c032ba1ff446a3f1a`、[Mac100](https://github.com/shuhei0720/necrogold-automation/actions/runs/42758476882) device成功。新IPA/build100 SHA `e33fee16d42cdaaa636ecc3ff9002100f46115078c722b67a482714e7cc8d6b7`、外ZIP SHA `a73af05f1908f8f03dd12c29410bcb6a600552eeb0d56543d28f058cc376df55`。

host32の全実行ID/生ログ/0skip/error/選択省略理由/ABI実query/22seal前後が実IPA sourceと一致。実4C/5Swift/6RSP/PBX/raw compiler引数を照合し、Perception/Nav strictO2・Controller/BeatO0・SwiftOnone/HOST macroなし。全9Mach-Oで従来101+065の計102marker非混入。22source中Controllerだけ変更/他21・R12原40/G1は維持。build-sourceは全492tracked bytes/path/CRC一致、7,327,230bytes/SHA `3d5f6c46b1c6c86efbc7c234f76f784eb0f9b7bc476394eea2af80c7ecbaf605`。最終sourceとの差分は文書3件のみと確認する。

[固定配布・実機手順](../status.md)からIPA/全sourceを返し、TEST065の商品到達とruntime/test-065全ZIPを依頼する。TEST065は実機未実施、064の成功経路と合成単体の成功を新実機成功へ読み替えない。
