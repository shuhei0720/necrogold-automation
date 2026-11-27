# TEST125: 起動前の状態を読む診断

2026-11-28（日本時間）。基準HEAD1fafd13、既存IPA278/元CODEc18db303は保持する。今回受領した日次runnerログ224行は通知許可/サーバー起動8回を記録し、最後は02:38:55のbackgroundで終わる。App Logsは起動とXCTest bootstrap成功までで、2/3は同一bytes。Network probe200はDDI配布先へのHEADであり、端末内サーバーの到達証明ではない。停止理由、native prepareの通知状態/保存準備、Wi-Fi原因は未確定である。

## 変更の範囲

新しい単独ファイル `diagnose_startup125.py` と直接試験だけを追加する。既存campaign116がready=falseを一律通知エラーへまとめる不備は確認済みだが、この診断ではゲーム/既存client/native/予算/再試行を変更しない。別版IPAの作成も行わない。

既存DeviceClient125とschema/cap検査、OwnedRpcTimer、Python crypto、既存prepare validatorを利用する。専用clientは `necro_native_irregular` の `prepare`、`request_authorization=False` だけを許可する。最初にGET /schema、到達後に既存pairingを読み、同じ一時probe IDでprepareを3回、間隔0.5秒で照会する。元RPCの有限timeout/暗号検査は保持する。start/cancel/keepalive/画像回収/出版/削除を呼ばず、準備完了後もゲームを開始しない。

出力はready、notification_authorization、recovery_scan、reason、未公開runの件数、失敗phase/codeと限定したtransport kind/stage/errno/statusのみ。key/token/probe ID/既存run ID/raw reply/例外本文/私的pathは出力しない。UTC時刻付きJSONを現在フォルダへ排他的に保存し、既存診断やruntime原本を上書きしない。実機の未確認を成功扱いしない。

## 検証・配布

最初にimportできるstubへ意味のあるassertion Redを置き、最小実装後にready/pending/拒否/scan失敗、接続断、途中失敗時の既取得分保持、秘密値非出力、prepare以外の拒否、排他的保存を確認する。実Python3.9でこの新規の直接試験だけを実行し、独立差分レビューを一回行う。既存のassertを変更せず、nativeビルド/全Runtimeを繰り返さない。

診断専用branch `work/test125-startup-diagnostic` に保存し、検証したcommitの固定raw URLから小さい診断ファイルを取得して実行する手順を返す。ゲーム側の承認branch/TEST125のCI選択・3asset/タグは変更しない。診断の保存・配布後は元branchへ戻す。利用者には診断JSONの返却を依頼し、その実結果から停止理由を絞る。
