# TEST125修正版: 連続試運転の起動準備待ち

2026-11-28（日本時間）。TEST125の実診断はHTTP200/通知pending→authorized、保存記録scanは3回ともpendingである。約1秒＋RPC時間の観測であり、scanが永久停止した証拠ではない。現行campaign116の単回prepareは、scan pendingを含む全ready=falseを通知権限エラーへ変換している。native側のscanが長い理由は別調査とし、未確認の理由で記録や安全条件を削除しない。

## 限定変更

既存の連続試運転で使う起動前prepareへ、DeviceClient125.wait_for_startup_ready=Trueだけの有限待ちを設ける。rootはclientのみのTEST125修正版を選び、既存IPA278を使う。TEST116〜124・FiniteClient125・回収/開始のwire/schema・capabilityはこの増分では変更しない。

- schema/cap検査後、最初のprepare前に既存と同じ8秒の開始資格期限を一度だけ設定する。同じprobe ID、request_authorization=Falseで照会し、pendingの場合だけ最大0.25秒間隔で再照会する。元のRPCは最大2秒で戻るため、既発行RPCの完了が8秒を越すことはあり得るが、そのlate readyを新startへ使わない。8秒は全処理完了の保証ではない。
- 期限は準備待ちの後に再設定しない。新しいゲーム開始のsole POST直前guardも同じ元期限を使う。nativeのP/D/W・入力窓・owner/prefix/予算は変更しない。
- query前後・待機前後で取消/実時計を検査する。期限ちょうど以後のreadyは新startへ使わない。通信切断/応答不明/不正応答はそのまま停止し、自動再送しない。
- unpublished IDが出たら既存の回収経路へ渡す。既発行RPCが開始資格期限後に返した認証済みIDも、取消がなければ新startではなく元の回収へ渡す。scan pending中の件数0を「未回収なし」として新ゲームへ進めない。recovery-onlyの「回収記録なし」もscan完了前には確定しない。
- scan failedは既存のcycle_recovery_scan_failed、明示的通知denied/not_determined/unavailableはcycle_notification_permissionとする。pending期限切れはscan/通知/一般準備のどれが残ったかを別コードで返し、一律の通知拒否と表示しない。
- 保存する診断が必要な場合は状態enum/件数/元deadlineとclockだけに限定し、key/token/raw reply/私的path/実行IDを新しい説明へ出さない。既存の回収・start-intent journalを削除/上書きして解決しない。

## 反例・検証

実行可能な現行campaign.runと既存の認証済み応答fixtureを使い、pending→authorized/scan readyで起動POST1回へ進める期待を固定する。修正前はcycle_notification_permissionで止まるassertion Redを先に確認する。模擬clock/sleepであり、実機scan完了の再現とは扱わない。

最小Green後、pending継続→元8秒で開始資格失効、期限境界ready拒否、通知拒否、scan失敗、未回収発見→回収、途中通信失敗→start0、取消、旧版の単回prepare不変、既存sole POST/不明POST無再送/保存後の期限再検査を直接確認する。実Python3.9の新規/関連client試験だけを選び、旧assertを変えず独立差分レビュー一回を行う。native解析/ビルドや全Runtime試験はrootが別増分として判断する。

意味Red1/errors0は変更前の実campaign経路で確認済み。fixture/計画は当初126候補名から125へrenameしただけで、反例の期待値を変えていない。実機改善は未確認、新IPAは作成しない。

実Python3.9.25で最終の新規14件と直接関連19件（既存TEST125の11件＋TEST116起動/回復8件）、計33件が合格した。元の旧試験assertは変更していない。late readyは元期限ちょうど/超過でPOST0、lateな認証済み未公開IDは新POST0で元回収、待機後の不明POSTも再送0を確認した。通常125連続実行には「起動準備修正1」の表示を追加し、`--check`/wire/provenance/capabilityは元のままである。

最終差分レビューで、期限到達時の明示通知拒否/scan failedがpending期限エラーへ隠れる境界を指摘された。新しい1件/2subcaseの意味Red後、取消→認証済みID回収→明示失敗→期限→readyの順へ限定修正した。pendingの説明文は確認できた保存準備の状態だけを述べ、通知拒否でないと断定しない。修正後の上記33件が合格した。
