# 最新状態

更新: 2026-11-11（日本時間）。TEST073の6run/114選択原画を受領。全商品可視0/6。前回のUI待ちは実restart計13回へ繋がったが、暗い開始画像の金見逃し・誤通路候補の固定、開扉/移動後UNKNOWNが残った。[TEST074計画](plans/test074-visible-evidence.md)・[受領と検証](reviews/test074.md)。Native局所修正と独立レビュー完了。新21/関係9/selector3のCI33と必要なIPAを実行する。074実機は未実施。

## 実機の根拠

started_ns実順4bc9e087→7414d4ee→0c7d26c2→2e5edcd9→c73a3854→5772e818。全6ZIP/114PNGのhash/CRC/manifest/prefix/cursor/report一致、全回収resolved/terminal/drained、全最終PAUSE成立。保持省略を未来画像で補わず、rawはGit外。

1/2/4/5は初期候補mask256/1/512/128が初歩前の独立画像で0、口もSTONE/DIRTに戻るが旧口へ進んだ。1/5は到達不能の2拍待ち後NO_PATH、2は未送信UPの静止UNKNOWNでSCREEN（Dまで51ms）、4はDOWN ACK後UNKNOWN8評価。1の原画31は左金壁が暗くr>52条件を満たさずpeak58/CLEARで見送り。3は実開扉後2商品だけ、6は実LEFT1tile後、双方UNKNOWN8評価でMOVEMENT停止。6の探索goal延長が必要とは未確定。

## TEST074の範囲

UI後の暗い最初のFLOOR1枚を陰性/通路権限にしない。初期200msと独立した新観測で描画・候補を確認し、初歩前同原点の古い候補を再検査する。新金/商品を優先し、移動後のworld口をcamera原点で再検出しない。描画途中の正常な不確実画像は元期限で待機。motionはprimary UNKNOWNだけへ強い既知地形のzero開扉/厳密unit証明を追加し、元閾値/UNKNOWN無再送/owner/prefix/取消/全期限・予算を維持する。

Controller/Navの変更単体・関連回帰→独立差分レビュー1回→必要な新IPAと実物同一性→実機。無変更Runtime/world全体を累積しない。既存assertを保持し、未実施を成功扱いしない。

## 現行配布と次の実機

現行は[TEST073/build116](https://github.com/shuhei0720/necrogold-automation/releases/tag/test073-build116)、code7da8f9cc/[検証](reviews/test073.md)。074は未配布。完成後は新IPA/完全sourceを期限のない固定Releaseへ置き、匿名全取得・SHA/CRCまで照合する。

次の実機は通常1-1ポーズから、候補までrestart→金壁/通路候補へ接近→入店→全商品確認を一連としてまず2回。短いrestartポーズ中はゲーム前面、ポーズが5秒以上続いたらiSHへ戻り全画像/ZIP保存照合完了を待つ。自動runtime/test-074-<run_id>.zipを全回分依頼する。回収済み073の追加回収・再実行は不要。

同じiPhoneのみ、ユーザーはMacを持たず実機担当。品質/安全条件不変・固定時間なし、既知通路は毎拍・新地形で判断が必要な1〜2拍だけ許容。raw/秘密値はGit外、既承認branchへ保存。初読3文書≤16KiB、[索引](context.md)から必要資料だけ読む。
