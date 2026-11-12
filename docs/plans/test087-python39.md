# TEST087 Python3.9互換修正と保存済み結果の回復

2026-11-12（日本時間）。基準 `b2b1cb003f51009ffe75f89080b9089a6cb2fed9` / TEST087/build148。ユーザー実機traceはPython3.9、20/20画像保存後、対象判定 `_observations` の `int.bit_count()`（3.10追加）でAttributeError。前回の実機Python版の検証不足を修正する。native/IPA/feature/閾値/入力権限・元087 spool/schemaは変更しない。

- 価格row1箇所・文字intersection/union2箇所のbit_countを、3.9で使える `bin(value).count('1')` へ同値置換。既positive testのfeature ink期待式も独立したbinカウントへ変え、前提assert通過後のpublic classify呼出しが未対応APIで落ちた場合を明示assertion失敗とする。実Python3.9で有効Red→最小Green、関連target6単体を選ぶ。
- 新しい回復専用入口を用意する。固定の `~/.necroprobe/runtime/test-087` / `.test-087-publication` に対し既publication lock→strict load→元certificate/prepare/publishを使う。native.main/Client/新ゲームsessionは呼ばない。保存済みrunがなければ説明して停止。既archive/receiptは元同一性検査のまま、何度実行しても新ゲームを開始しない。既通常test087 entry/spoolは維持する。
- 回復専用入口は、未出版resolved runで同UUID/原画像/report不変・ZIP/sidecar完成・session/RPC0、未完/空・既出版再実行で新start0を選ぶ公開単体Red→Green。SIGINT/TERMで元cancel確認を使いlocal dataを保持する。
- Python3.9の対象6＋必要な回復単体だけを新しい軽量Ubuntu CIへ固定し、実版を明示する。native全Mac/新IPA/既33のC全反復は不要。元build148のIPAは検証済みのまま再利用する。
- 同じ独立担当1名で差分と3.9/回復結果を確認する。完全sourceの固定Release assetと整合する修復手順を配布し、匿名全GET/SHA/CRCを照合する。新source folderで回復専用shをiSHへmountし、同087永続データから再開する実機テストを依頼。今回の20/20後例外は未公開ZIPのため、先に保存再開を依頼し、新しいゲーム試験を求めない。

新添付aeef427bはnative MOVEMENT10/GOODS0で、後続Pythonエラーのrunと別件。raw解析を並行するが、今回のhost互換修正へnative歩行修正を混ぜない。元runの再回収と新runの開始を区別する。
