# TEST088: 判定と独立した証拠ZIP回収

2026-11-12（日本時間）。基準c3ac8eb357ab3c11adfdfe2ce60b1cc3fa125085。fix2実機画面で画像/実行記録の照合は完了し、判定経過が128秒以上継続した。前の軽量化では不十分。通常の対象判定が初ZIP前に同期されているため、計算未完だと全原画像も返せない。開発機だけの小改善を実機解消とは扱わず、まず現runの原本を回収する。

新evidence088/evidence_088.shは固定homeの同088spoolを、既publication.lock（非blocking）下でstrict load→元certificate後に読む。通常の_archive/_publish/receipt・classifier/prepare/device/sessionを呼ばない。active/report/登録済み全PNGのみのwhitelistを別.test-088-evidenceへdeterministic ZIP_STOREDで保存し、別schema receipt/出力test-088-evidence-<uuid>.zipへコピーする。sidecar/中断part/余計なrun内ファイルは原本のまま残して診断ZIPへ混入させない。

全CRC/SHA/byte数/元source再照合後だけ証拠回収完了と表示する。対象判定成功/陰性や通常出版完了とは呼ばない。通常pendingは残し、新ゲームstartの許可へ変換しない。別保存先/既診断archiveの再検証、既file/破損receiptの非上書き、symlink/foreignrun/未回収拒否、INT/TERM時の保持とhandler復旧を守る。

新4単体で有効Assertion Red→実Python3.9 Green。元PNG/report/通常sidecar/zip/receiptのbytes/mtime不変・診断後も通常はprepareへ戻り新session0を確認。同じ独立担当が差分と実物を確認し、native/判定は無変更のため旧17/全Mac/C/IPAを再実行しない。

固定Release test088-evidence-recoveryへ完全source/SHAを保存し、全tracked blob/CRC/匿名GET/actual tagを照合する。現在の判定はCtrl+Cで止めprompt復帰後、新sourceのevidence_088.shだけを実行する実機確認を依頼。画像/元データを削除せず、診断ZIPを返却してもらう。重い通常test_088.shの再実行や新ゲーム試験は今回要求しない。判定高速化と歩行停止は未解決で、受領する実画像の候補数/処理位置を確認して次の実装へ進む。
