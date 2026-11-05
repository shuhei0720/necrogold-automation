# セキュリティ・運用レビュー 第1周

レビュー日: 2026-11-05（日本時間）

対象は要件・再実装プラン・保存資料であり、実機試験やR12の修正ではない。R12の既存挙動は再実装計画への反映漏れを確認する根拠に限って参照した。`legacy/r12/` は変更していない。

## 判定

P0: 0件、P1: 2件、P2: 1件。現時点の保存物から機密値の実在は確認していない。P1は入力方式を確定する前にプランへ補足する必要がある。保存継続を妨げる実機試験の要求ではなく、今後の実装ゲートの不足を指摘する。

## SEC-01 / P1: 送信済み入力の取消・期限・前面確認を誰が保証するか未定義

- 位置: `docs/plans/rebuild.md:32`、`docs/plans/rebuild.md:34`、`docs/plans/rebuild.md:50`、`docs/plans/rebuild.md:78`、`docs/plans/rebuild.md:92`。
- 根拠: 操作直前の入力先確認、期限、cancel generation、予約取消、結果不明入力の非再送は記載されている。一方、制御側から送信済みで端末内の実行待ちとなった入力に、その制約を適用できるかがP1の能力確認・不合格条件として定義されていない。`docs/requirements/necrogold.md:26` は予約中・待機中を含む停止と別画面への誤入力防止を要求する。
- 既存資料の示す境界: R12は前面確認後に独立したtap RPCを送る（`legacy/r12/phone.py:290`、`legacy/r12/phone.py:322`）。停止は子プロセスへのterminateである（`legacy/r12/runner_status.py:72`）。これらだけから、既に端末へ到着した要求が取り消されるとは証明できない。旧版の改修要求ではない。
- 壊れる例: 前面をゲームと確認→入力を送信→端末側で待機→利用者が別アプリへ移動または停止→遅延した入力が実行、という順序。クライアントのキューを空にし再送を止めても防げない。読み戻した画像が正常でも、さらに遅れて到着する入力が残っていれば、直ちに安全な再開とは判定できない。
- 修正案: 入力状態を少なくとも「未送信・送信済み結果不明・端末受付済み・反映確認済み・取消確認済み」に分ける。P1で、端末側の対象アプリ/画面世代の検査、実行期限、取消、受付済み要求の照会能力を測る。対応していない方式では新規入力禁止と停止未確認を明示し、未処理入力の失効または終了を確認するまで再開させない。要求する停止・誤入力防止が実現できない場合は方式変更とし、ローカルフラグのみで合格にしない。
- 追加試験: T09/T10へ、送信直後・端末受付後・実行直前の停止/前面変更、遅延応答、取消応答喪失、切断後の遅延実行を追加する。停止受付・新規送信禁止・端末停止確認を別時刻で記録し、実際に端末で反映された入力を検査する。

## SEC-02 / P1: 外部応答・画像・設定の入力制限が設計と試験にない

- 位置: `docs/plans/rebuild.md:19`、`docs/plans/rebuild.md:24`、`docs/plans/rebuild.md:32`、`docs/plans/rebuild.md:71`、`docs/plans/rebuild.md:79`。
- 根拠: 破損画像・時刻・寸法変更は扱っているが、通信応答の読み込み上限、JSONの型/深さ、base64の展開量、画像の画素数、座標値の有限性、設定値の許容範囲をどの責務で検査するかと拒否試験がない。「すべての待機に期限」だけでは、無制限のメモリ確保や重い復号・展開中の停止不能を防げない。
- 既存資料の示す境界: R12は画像ヘッダの寸法と形式を検査する（`legacy/r12/phone.py:220`）が、RPC本文は上限なしのread（`legacy/r12/loopctrl_rpc.py:273`）、画像データは寸法検査より前のbase64展開（`legacy/r12/phone.py:215`）。この一部の防御だけを新実装の入力契約として継承してはいけない。
- 壊れる例: 壊れた取得経路が巨大な応答や過大な符号化画像を返すと、画像の無効判定までにメモリ・時間を使い切る。NaN/Infinityを含むpt寸法や未知形式の設定が比較をすり抜ければ、不正な座標をアダプターへ渡し得る。敵対的端末を前提にしなくても、取得不具合で発生し得る。
- 修正案: P1のアダプター契約に、認証した相手・期待する応答IDの照合、受信バイト数・復号後バイト数・JSON構造・画像幅高さ/総画素数・配列件数の上限、座標と時刻の型/有限性/範囲の検査を記載する。制限値は実測して版管理し、上限超過・不正応答は追加入力0で停止または期限付き取得回復へ遷移する。採用する管理UIがある場合は、ローカル接続範囲、認証、許可操作、Host/Origin、本文上限、読み込み期限も同じ契約に含める。
- 追加試験: 最大値直前/一致/超過、巨大Content-Length、長さ不明の過大本文、途中切断、不正base64、画像展開量超過、型不一致、NaN/Infinity、未知コマンド、異なる応答ID。拒否後の入力0と停止応答性を確認する。

## SEC-03 / P2: 保存前の機密検査と実行生成物の隔離を明示する

- 位置: `.gitignore:7`、`docs/rules/architecture.md:10`、`docs/plans/rebuild.md:104`。
- 根拠: 秘密値をgitへ入れない方針は明記されているが、保存コミットの検査項目に秘密値・私的設定・画面内容の点検がない。`.gitignore` はLoopCtrlの鍵類とruntimeを除外する一方、旧版がコード直下へ出力する `results/`、`start-failed.jpg`、`failure-frame.jpg`、`loopctrl-frame.jpg`、`loopctrl-landscape.jpg` と、ホームに生成する `.necro-panel-key`、`.necro-gold-menu.json`、ログ類の取り込み防止は具体化されていない。
- 根拠位置: `legacy/r12/panel.py:19`、`legacy/r12/panel.py:20`、`legacy/r12/calibrate.py:9`、`legacy/r12/phone.py:441`、`legacy/r12/phone.py:608`、`legacy/r12/phone.py:702`、`legacy/r12/phone.py:718`。
- 壊れる例: 実機の診断後に一括保存すると、別画面や通知が写った画像・個人設定・操作用URLを含むログが証拠画像に混ざる。除外設定だけでは既追跡ファイルへの書込みを防げず、保存対象として意図した既存の黒画像まで一律削除する解決も不適切。
- 修正案: R12を変更せず、リポジトリの除外規則と新実装の保存先設計を補足する。実行生成物は無視される専用ディレクトリへ隔離し、証拠としてgitへ昇格する画像・ログは秘密値と私的画面を確認したものだけに限定する。コミット対象一覧・鍵形式のパターン走査・設定/ログの内容点検・画像の目視を保存時の手順へ追加し、チェック結果と限界を記録する。

## 確認済み事項と限界

- `README.md:5` と `README.md:41` はR12を実機不具合のある保存旧版とし、旧起動手順・旧検証結果を現行推奨と扱わない。`docs/development-flow.md:25`、現行プラン、要件書も未実装・実機未検証・性能提案値を明記している。動作保証版と誤認させる新たな記述は、今回確認した現行説明には見つからなかった。
- R12の全40ファイルを `docs/r12-source-manifest.json` の各SHA-256と照合し、40/40一致、余分なファイル0、欠落0を確認した。実行、ビルド、旧版selftestの再実行はしていない。
- 走査時点のリポジトリ内67ファイルに対し、秘密鍵ヘッダ、代表的なGitHub/AWS/OpenAI鍵形式、長い秘密値代入をバイト列で検索した。該当0件。既知のtoken/pending-pair/private-config/log候補ファイルも未検出。これは任意形式の秘密値が絶対に存在しないことや、後続で追加されるファイルの安全を保証しない。生の値はレビューへ転記していない。
- `analysis/manual-video-1/IMG_8513.png` はゲーム画面、`evidence/start-failed.jpg` と `evidence/start-failed(1).jpg` は黒画像であることを目視した。全画像に対するOCRや隠しメタデータの完全な機密監査ではない。
- `docs/video-2-analysis.md` は初回読込時点では未存在だった。作業中に他担当が作成・変更する資料は末尾のハッシュ対象に含めていない。最終保存前に参照先と最終差分を再確認する。
- 本レビューは入力先の安全・停止性能・ポーズ保持の実機成功を証明しない。P1の解消は資料の再レビューと将来の実機ゲートで別々に確認する。

## レビュー対象主要ファイルのSHA-256

以下は本レビュー作成時のスナップショット。行番号はこの版に対応する。

| ファイル | SHA-256 |
| --- | --- |
| `AGENTS.md` | `2256f88a42e9773dbf8e3a52ae3c4a467a72c814642220d5391f7cc3e6c8eafb` |
| `README.md` | `73db7ea04f693667aa5d3be3a4fd8f95367ad62d25850f414114e491716358f2` |
| `.gitignore` | `1c3f05f25323a1e605001014f6344a11ea495eda004a4c97c06741ab24a26367` |
| `docs/status.md` | `dfce536fa5ea0202679aeb87dc8a8e95e9177531588c4878a7544d84221576f6` |
| `docs/development-flow.md` | `8a249c6c31e0ec9403d292a34b2d6cb7d54d37050bd7e468aac4b28558dc2c70` |
| `docs/requirements.md` | `916c08fb09dae3d0e248bbd1a1b51d154e5cf76523ae33b3772d49af3f4b92b2` |
| `docs/rules/architecture.md` | `78ccfba91a0071e101f4defd7ba372efb1488dcdabd32487e916c3b596465b22` |
| `docs/rules/testing.md` | `e3f3739a7befca3741a4d7bb138fb7277bb571aba8f99599b91a4b4de3fd4cf9` |
| `docs/rules/review.md` | `4bcd5015ef5e1aed97775501ddee660871586e6600a47f9741c8d59d5653ca85` |
| `docs/requirements/necrogold.md` | `a231f127c21d776f06483c712a4956df6722c4a02c00795390643a1e33c6d8c9` |
| `docs/plans/rebuild.md` | `a1dad993b8cb7284bf49a1f375c994472d7877bc093864d5cb7b84ccf1b94ca7` |
| `docs/r12-source-manifest.json` | `8d0a54d8c3766b83dd7767e6a194a7aa33c75387cda106e5f686596fd99b41b3` |
| `legacy/r12/phone.py` | `fa63242ca1bb331c37e604ee75514b361bd37fa3399172a1202d5284c498fec1` |
| `legacy/r12/loopctrl_rpc.py` | `613c6888a80f32ff155f8aa19ff2a022ef2399f1e472c31e2325c2e3de9e6711` |
| `legacy/r12/panel.py` | `e4c52bb14b21b7c11200e663b5f085ae1664c9734f68f82b91b7649431bf0237` |
| `legacy/r12/calibrate.py` | `8a042e848d4309ef60d7e5bd2d964fcf5286a1048caada62884109f99d6f1707` |
| `legacy/r12/runner_status.py` | `6b1d49d0226b73303c2c397d4c2cc7afef6860b7955fc306b25f6d298abc7759` |
| `legacy/r12/diagnostics.py` | `783c23292aa45f75314fed3aa5fc76682ed633b752d763383faf67f522c3a0e3` |
| `legacy/r12/fast_crypto.py` | `e846181027226e59311c7cf246188429baaa86d86f443d3f49a0e2eb67786761` |
| `legacy/r12/fast_crypto.c` | `99b944d8ee537ab0867dd3e3226c8db339f76b723b4a7fd57e72119b9e3e275c` |
| `legacy/r12/pixels.py` | `567755eaf1228770fad77a1c807775d0eec18f3e2c98945afbb2e405907fd177` |
| `legacy/r12/start.sh` | `3b17c127342fce6b8699ccadbc837009c3426125c8565939a26f66f3e6c34084` |
| `legacy/r12/はじめに.txt` | `3ee6f178c0bae06c326097fc1a95f4f9a30b326da1430f845fec4a33247ccab8` |
| `legacy/r12/検証結果.txt` | `ea6ff8fa463f66c3d2a0b46fcd2f4a9e0a3cb41d239b0755d7efb8923243be99` |
