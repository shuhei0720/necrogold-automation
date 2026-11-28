# TEST126 開始拒否診断の修正

2026-11-28（日本時間）。[計画](../plans/test126-start-admission.md)。CODE `3bfc15e3444f502acfa3d30d0593f0ac7da9e22f`。

ユーザーの22:55のiSH画面で、TEST126/build1001の通常コマンド2回とも起動準備後に `cycle_start_not_admitted`。原画像はチャット添付のみでhash未計測。既存clientでこの表示になるのは認証/MAC/応答ID照合後のnative -32095。接続失敗・新たなJetsamを示す記録は今回ない。

prepare.readyの検査対象はscan・未出版記録・通知だけ。startには別にquota、pause、旧run、poison、drain、export、capture、UUID/process上限など計11出口がある。例えば出版済みでも保存namespace128件や空き容量不足でquota予約が失敗するが、これは静的反例であり実機原因とは未確定。今回確認した不具合は、全理由を汎用コードへ縮約し反復実行を促していたこと。起動拒否そのものの解消とは扱わない。

正確なirregular/continuous/initial_restart要求に対する固定11文言だけを閉じたコードへ写し、126連続clientの明示opt-inだけで既存last_errorと日本語説明に残す。自由文/data/秘密値は保存しない。未知文言は汎用コードと原因未特定の説明。元8秒期限、POST1回、拒否後intent解除、UNKNOWNの同UUID保持/無再送、旧client、有限126、ledger schema、native37/capを維持する。

## 検証と独立レビュー

- 新15試験で実装前Redを実測（25 assertion failures、errors0）。初回のPIL不足は環境エラーなのでRedに数えず、private targetへPillow11.3.0を用意して再実測した。
- 実CPython3.9.25で新15＋直接関連149＝164合格、失敗/エラー/skip0。暗号RPCのMAC/ID/shape、固定11理由、不正要求、pending→ready後の拒否、POST1/取消0、耐久journal、手動次回の同UUID/prepare、旧版、UNKNOWN回復、終了表示を検証。
- CODE固定の別client専用runnerで164件を実行し、importした全repository moduleとshellを同commitのGit blobへ照合。runner SHA `92f4e5d127f1172d2f45d78ac5b11bbf65a56a9b83f1b105ad37c3cd870239f9`、log SHA `936fde7420bbfb2136aedac6160004041a02601dd912e4a876971edd40ee1aa0`。既存native-build用selectorは元CODE75d3282専用であり、新client SOURCEの検証とは称さない。
- 独立差分レビュー1回で設計/異常系/秘密値/入力権限/運用を確認、修正必須の指摘なし。担当は静的差分とGreenログを確認し、自身で試験を再実行してはいない。

原本はGit外 `/workspace/analysis-evidence/test126-admission/`。新IPA/native CIは作らず、同一nativeの過去build1001検証だけを再利用する。完全sourceの全Git blob/CRC、保護生成入力・canonical/R12のGit mode/blob、既存IPA検証receiptとの対応を配布前に別途照合する。固定公開と匿名GETの結果は公開後に追記する。

build1001のまま新sourceから通常コマンドを一度実行する。拒否なら「停止理由」と「開始できない理由」の画面を受け取り、その条件を修正する。開始できた場合は通常1-1ポーズから初回RS→候補/通路→開扉→全3商品→対象外の実RS/次周回を確認し、終了後に全run/campaign ZIPを返してもらう。原本/pairingは保全。実機起動、メモリpeak、商品到達、実RS、速度は未受入。
