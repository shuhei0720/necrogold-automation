# TEST069: 回収完了まで一回で保存し、未送信開扉の観測を取り直す

2026-11-10（日本時間）。baseline `a5757228d867855af81d1325feca7fc7e7c14f5f`。

## 1. 目的と背景

最新指示は「画像全部保存し終わってない。これやめろ」。TEST068は4歩後の扉前停止、16枚中12枚だけ保存して終了を表示した。今回の成功条件は、入力終了と結果保存を分離し、通常の一回の実行で検証済み全選択画像を返却用ZIPへ出すこと。未完了を終了扱いせず、未出版runを残したまま次のゲームを始めない。

## 2. 実機の根拠

受領ZIP SHA `ac50e2c7c4ba25ec1848a096bbf3a30e8e8eb1563ea68deb687a983bf2e32ce5d`。run `cf5147ae1c8d428a8ad9e84eee1fffdc`、nativeは6.706秒でSCREEN停止、4入力/4MOVED、開扉/商品0。原画130→133は同じLEFT/reason5/target(-1,0)/DOOR、gold2・局所/保護不変。遠方2セルだけ変化したがmotionはUNKNOWN（最良zero score .50899、構造支持95%未達）。5番目の入力id9はbeginなしで撤回され、期限の14.751ms前なので時間切れではない。

回収manifestから最終chunkまで87.728秒、RPC23.596秒・呼出間64.132秒。109 atomic保存/14,443,914 bytesを書き、90秒で打ち切った。残877,583 bytes。TEST068の最適化は再開時だけで初回保存負荷を直していなかった。未収録4画像/未来画像は補わない。

## 3. 詳細設計

### 回収の期限

ゲームの180秒、歩行45秒、再同期12秒、入力上限/UNKNOWN無再送は不変。native terminal・workers_drained・input_state 0/3・非inflight・非ui_frozenを確認した後だけ、同UUID/export_id/cursorのread-only回収に独立300秒を与える。従来の90秒をゲーム残時間へ収める規則はこの安全停止後の回収だけ変更する。根拠はゲームが既に停止しており、実測の保存負荷が入力期限と無関係なため。unsafe/未知入力/非terminalには従来のcancel/cleanup期限を維持する。回収中のstart/方向入力/keepalive/cancel追加は禁止。

### iSH内の永続保存と単一ZIP公開

TEST069だけ固定local spool `~/.necroprobe/runtime/test-069` を使い、checkpoint/両journal/画像をiSH内にdurable保存する。共有フォルダへ小さい同期書込を繰り返さない。旧TEST068や旧journalを削除/移行しない。nativeのdevice_lockと別のspool/publication lockで同時実行を拒否する。

resolved、terminal、manifest全画像のcursor/end/full SHA/PNG header/dimensions/prefix・active/report一致を確認してから、対象runtimeだけをZIP_STOREDでlocal archive化。path/inventory/CRC/全bytesを照合し、共有側 `runtime/test-069-<run_id>.zip.part` へ一度copy、whole SHA確認後にfinal rename・final再確認・local receipt保存。秘密値/設定/HOME/source全体は含めない。local原本を消さない。

起動入口は、前runがresolvedでも現在の共有先に同一hashのZIP公開が証明できるまでpublish-onlyとし、run_sessionへ入らない。resolved保存直後/receipt作成前のクラッシュも検出する。receiptだけを信用せず実際のfinal ZIPも照合する。different bytesのfinalを上書きしない。nativeが起動前失敗と確定したresolved/stopped・native_state/reportなし・export/画像なしだけは「未開始」として別扱いにし、今回の完了/画像回収を主張せず次回の再接続を許す。start_attemptedは送信前に保存するため、そのbitだけで未開始を決めない。取消/障害/未回収には未完了を表示し、`終了・このZIPを返却`は全公開検証後だけ表示する。正常な一回で回収・ZIP作成まで自動で行い、利用者に途中の再回収操作を要求しない。

### 未送信開扉の再観測

UNKNOWNをBLOCKEDへ読み替えず、.45/.08・構造95%等の閾値を維持する。begin前・reason5・同closed DOORのcontinuous候補だけ、1run1回に限定する。元/最新の完全5field・gold・局所・全保護・prefixと許可済遠方変化を照合し、UNKNOWNで確実未送信ticketを永久撤回する。最新self→selfのstrict BLOCKEDは低texture除外だけに用い、入力権限にはしない。

新しい待機状態で固定anchorの全条件を毎frame照合し、独立した後続画像とのstrict BLOCKEDが得られてからfresh HUD fit/sample≥proofID・将来拍prep≥50ms・別IDで予約する。UNKNOWNは観測seedだけ更新可、TWEEN/MOVED/UNEXPECTED/開通/権限/局所変化は停止。新ticketもaccepted current-prefix全観測でanchor→最新strict BLOCKEDを再確認しbeginは最新proofIDのみ。同期期限は直前の実MOVED+12秒と既存期限のmin、45/180秒・16入力不変。旧ID/期限を復活せず、送信UNKNOWNを再送しない。

## 4. 変更範囲と互換

新TEST069 wrapper/launcher、native_walkのterminal回収期限と結果hook、Controllerの限定再観測が対象。wire/ABI/API15/cap13/clientv14・既存旧journalの読込を維持し、wrapper公開receiptは別schemaにする。Runtime/Swift/取得/実入力/owner構造は変更しない。seal変更は実際のnative差分だけ。初読3文書16KiB・native契約12KiBを維持する。

## 5. テスト期待

意味的Red→Greenで、ゲーム期限後の安全回収・unsafe期限保持・同UUID/offset/no mutation、local staging先、全画像未完了拒否、ZIP一致/不一致、copy/rename/receiptの各中断、resolved直後の再起動で新start0を検査。nativeは元原画のUNKNOWNを保持し、未送信候補の新観測と旧ID拒否、送信UNKNOWN/商品/保護/局所/期限の拒否を検査する。実未来画像を合成して到達成功とは呼ばない。

## 6. 実装とレビュー

collection、local spool/publication、native停止原因を独立担当で並行実装。設計/網羅/安全は変更した境界の独立レビューで確認し、P0/P1を修正、残るP2は根拠を記録する。レビュー最大3周。入力予算・閾値を緩めて試験だけ通さない。品質のための必要時間は使い、長時間の無報告は避ける。

## 7. 配布前検証

変更単体・関係する公開回帰とpublication境界試験をdevice CIで選ぶ。無変更Runtime/world全体を累積しない。native変更時だけ新IPAを標準Macで作り、seal/実compiler/IPA/全sourceを照合。Git外の受領原画・SHA・集計はGitへ入れない。固定Releaseの匿名GET/SHAを確認する。

## 8. 実機依頼とスコープ外

新IPAがある場合SideStore更新→LoopCtrl完全終了/起動→Start Server。新通常1-1ポーズからtest_069.shを実行し、歩行中ゲーム前面、自動ポーズ後iSH前面でZIP保存完了表示まで待つ。自動作成されたrun別ZIPをそのまま返してもらい、商品全体の可視・停止位置・間隔・保存完了を評価する。TEST068の追加回収は依頼しない。未観測地形/実ゲームCI/速度や到達の成功保証、別のリファクタリングは混ぜない。
