# TEST088: 判定待ちを経由しない証拠回収

2026-11-12（日本時間）。[計画](../plans/test088-evidence.md)。fix2実機画面は「全画像の照合が完了→指輪判定中→経過128秒」まで継続。判定区間の長時間化が確定し、前修正では解消していない。128秒で無期限loop/CPUとI/Oの全内訳までは断定しない。元codeは1画像最大4行×3slot×3scale×34y×17x=20,808位置を探索する。単に待ってもらう説明では不十分で、実データ回収と根本の処理方式を見直す。

標準lib C-iteratorへの追加試作は製品外で原309の全field一致だが、同開発3.9の1.799→1.255秒程度で十分とは判断せず未採用。iSHでの解消や新機能完成とはしない。別のportable C数値kernel実験も製品外で、今回の配布の前提にしない。

## 回収専用の境界

所有新3ファイルはevidence088.py/evidence_088.sh/tests/test_evidence088.pyのみ。同088の旧publication.lockを使う純local入口で、strict load→元_certificateを再利用。別storage/.test-088-evidenceと別schema ngg2-evidence-088-v1、別filename runtime/test-088-evidence-<uuid>.zipへ保存する。通常_publish/_inventory/判定/Client/session/RPC0。通常receiptを作らず、既normal ZIP/sidecar/原report/PNGはbytes/mtime不変。診断後の通常未出版はprepareへ戻り新start0。

原本は2+len(record.images)の固定whitelistだけで、active.jsonとnative-<uuid>/report.jsonと全登録PNG。元partやsidecarは削除せず混入させない。元certificateと全CRC/SHA/size/順序/元sourceの再照合、別保存先/再実行で同bytes、破損/foreign receipt/ZIP/変更PNG・未回収・symlink拒否、INT/TERM保持・handler復旧を確認する。診断ZIPが対象判定や通常出版の完了を示すことはない。

作者の実CPython3.9.25有効Redは、既normal test088委譲では診断期待を満たせずAssertion失敗（setup/import失敗ではない）。新4methodsは実3.9で全Green。証跡はGit外test088-evidence/red.log/green.log/inventory.json。CRC故障・異schema/余剰/誤SHA receipt・foreign archive・両signalを含む。新旧native/C/17群や実画像全scanは実施0、判定性能の成功へ数えない。

## 配布と実機確認

新固定Release test088-evidence-recoveryへ完全source/SHAを保存し、全blob/CRC/安全entry/匿名全GET/actualtagを確認して返す。既087/088公開assetは変更しない。IPA148・判定module・通常test069/test087/test088/sh・全native/R12は元c3ac8ebと不変。今回の許可は同088の回収だけで、重い判定を繰り返す通常テストは依頼しない。

ユーザーは現在処理をCtrl+Cで止めprompt復帰してからevidence_088.shを実行する。元device_lockはLOCK_NBなので、旧processがまだ動けばalready_runningで拒否される（lock待ちへ入らない）。保存済み全画像の照合と診断ZIP完了後、runtime/test-088-evidence-<uuid>.zipを返却依頼。個別指輪判定は未解決、通常出版もpendingのまま保持し、受領画像で比較回数/処理位置を調べた後に根本実装へ進む。

## 同人の最終製品差分レビュー

TEST086から継続する同じ独立担当が新3ファイル・計画・診断例外契約・status/台帳を静的確認し、未解決P0/P1/P2なしでGO。独立の意味試験・compile・実画像走査は0。最終SHAはevidence088.py `f887e5a265ee538c4c5902e3bc64d65f59922a305f68cc26c6dab617118fda95`、evidence_088.sh `a79050c3f53fbe8f1b7cf7d6f4147aee2879f5166edee0f84c5f3c1dbc8e961e`、新test `817b07d0e5f435f0174822ec5ce4d6260f487d078295aca5c0b8655898b47061`。

固定088の既非blocking publication lock下でstrict loadと元certificateを使い、登録済み原画像と同bytesのactive/reportだけを出す。通常の再帰inventory・prepare/classifier・native/session/RPCは呼ばず、既sidecar/中断partや通常archive/receiptに書き込まない。新receiptは別storageのexact5field/別schemaで、run/report/archive SHAとint byte数を検証し、bool・余剰field・異schemaを拒否する。診断ZIP内は従来のraw-only閉layoutを維持し、区別は専用filename/storage/receiptが担う。通常評価器がrawを読めても通常出版や対象識別の完了を示すものではない。

元sourceの前後digest、ZIP_STORED/固定日時・全member CRC/SHA/size/order、別destinationへの同bytesコピーと既fileの再検証、破損fileの非上書き、親pathを含むsymlink拒否、取消時の原本とsignal handler保持を確認した。通常pendingは診断後も元prepareへ戻り、新sessionを開始しない。既通常出版が有る入力にも虚偽の未完を断定しないよう成功表示を修正し、旧/新SHAと表示Constant以外のAST同一を独立に照合した。この表示だけの修正で元Greenを再実行していない。

作者の実CPython3.9.25記録は、正常に読める保存runに対する公的診断期待が旧通常入口委譲では0対2となる有効Assertion Red、新4methods全Green（0.591秒）。通常経路/判定/RPCの禁止、原bytes/mtime、全raw member、再実行/別保存先、破損CRC/foreign/閉receipt、未回収・symlink、INT/TERM、通常未出版継続を確認する範囲で十分。procedural PNGと保存境界の検証であり、実機ゲームやiSH速度の再現ではない。

旧test069/test087/test088/target module/feature/通常shは基準c3ac8ebと同bytesで、native/IPA/R12を変更しない。初期3文書16,057B・native契約12,277B、diff checkも確認済み。全682sourceの配布実物・固定URL/actual tagの確認は次段階で同人が別に行う。判定128秒超は未解決、診断exportの実機所要時間も未測で、歩行停止・対象精度・通常一連試験の受入へ昇格させない。

配布差分も同人で静的GO。元c3ac8ebから新3/関連docs5/stage workflowの9pathだけ、候補全682filesと新3SHAを照合した。旧native/通常entry/target等124path・R12全40の元bytes不変を独立確認。workflowは固定draft442982728/tag test088-evidence-recovery/初期target c3ac8eb、prefix necro_test088_evidence、空assetsと返却tag/target/draftを検証して固定IDへsource/SHAの2POSTだけを行い、公開しない。全blob/CRC/安全entry照合を維持し、既公開assetを変更しない。今回pathは旧Python3.9 CIのwatch集合外で、単一pushのsource-stageだけを実行する。実物と公開後の確認は引き続き別gateとする。
