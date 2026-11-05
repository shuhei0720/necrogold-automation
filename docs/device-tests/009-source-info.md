# TEST-009: 取得元の版と対応機能を1回だけ照会

状態: **実機照会結果を受領済み**。2026-11-05（日本時間）。診断本体はP1.4のまま。横長取得の修正完了ではない。

受信後の縦横変換は追加しない。実機LoopCtrlの版/buildが既存レポートに保存されていないため、その情報だけを取得して横長で返せる修正経路を決める。

## 受領結果

IMG_8533.pngの端末出力を転記。API 1.98.14、build 2026-11-01 16:49、protocol 1、point414×896、pixel828×1792、scale2、issuesなし。既知機能はrun_steps/wait_for/video_stream/stream_ticket。暗号はnative_i386。プロンプトへ戻った表示を確認したが、数値終了コード・実行時間は受領していない。

これはiSH前面の照会であり、縦寸法というだけでゲーム取得時の不具合を証明しない。video_streamの申告も動画取得成功や速度の証拠ではない。公式v0.3.4のAPI版と一致するが、同じ版番号だけではバイナリ同一性を確定しない。[転記JSONと出典ハッシュ](test-009-results.json)。

TEST-009の再実行は不要。次は[取得元の画像寸法修正](../plans/p1-source-geometry.md)をCIで検証する。現行LoopCtrlの削除・更新はまだ依頼しない。

以下は実施前手順を保持した履歴。

## 手順

1. [inspect_capture_source.py](../../tools/inspect_capture_source.py) をGitHubの「Download raw file」で保存し、iPhoneの「ファイル」で既存P1.4フォルダ（iSHの`/mnt/necro_p14`に対応するフォルダ）へ置く。フォルダ全体の再展開・再インストールは不要。このファイルにはペアリング情報を記入しない。
2. LoopCtrlを以前の接続状態にし、iSHを前面のまま次を1回実行する。

```sh
cd /mnt/necro_p14 && python3 inspect_capture_source.py
```

3. 出てきたJSONを貼り付けるか、その部分だけスクリーンショットを送る。原画像やZIPは不要。周囲に私的情報・秘密値が写っていないことを確認する。

通常は15秒以内に結果または固定エラーが表示される。期限は通信だけでなく暗号初期化も含めた子全体に適用する。終了時の回収待ちは最大1秒。Ctrl+Cで中断できる。位置情報reader・ゲーム起動・タップ・画像取得・変換は行わない。

| 結果 | 意味 |
| --- | --- |
| server.values / known_capabilities | サーバーが申告した版/build/寸法/既知機能。実機の横長画像・鮮度・入力座標・速度の証明ではない |
| requires_P1.4 | 実行場所の診断版が違う。既存P1.4フォルダを確認する |
| source_info_worker_failed | 子が異常終了。数値returncodeを残す。秘密値を含み得る例外本文は出さない |
| source_info_deadline | 15秒期限で子を停止。再実行を繰り返さず表示を共有する |
| source_info_invalid_output | 子の出力形式が不正で表示を拒否した |
| source_info_cleanup_failed | 子の停止・回収を確認できなかった。追加実行せず表示を共有する |
| source_info_cancelled | 利用者のINT/TERMによる中断 |

実機版が分かったら当該版の取得処理を確認し、画像自身の寸法を基準に返す取得側の修正を第一候補とする。動画配信経路への変更はiSH復号コストを含む実測が必要。画像変換で表示を整える案は採用しない。
