# 取得元照会補助の独立レビュー

2026-11-05（日本時間）。対象は `tools/inspect_capture_source.py` と試験/手順。P1.4本体は変更しない。

## 要件と範囲

ユーザーから「変換ではなく横長のまま取得し、性能要件を満たす」指示を受け、診断プレビュー案を撤回した。プレビューのコードは実装/配布せず、そのRedを横長取得の合格に流用しない。取得元の実機版が分からず適用可能なAPI/修正が確定できないため、既存P1.4で1回だけdevice_infoを照会する補助を完成させた。これは横長取得の修正本体でもP1.5リリースでもない。

## ①計画・②③設計/網羅レビュー

[8項目計画](../plans/p1-geometry-validation.md)を3担当でレビュー。設計・安全はP0/P1なし。テスト担当のP1は、標準入力実行の検証不足と、有効JSONの秘密追加キー/偽issues等の検証不足。配布方式を1ファイル追加による通常実行に限定し、特別なPYTHONPATHなしの親/子ファイル実行と版違いを実プロセス試験へ追加。有効だが不正なJSONの拒否試験も追加した。取得元版照会は横長/入力座標/鮮度/速度の検証ではない。

## ④⑤ Red → Green

- 情報抽出が期待値を返さないRedを確認後、型・範囲・長さ・既知能力の選別を実装。
- 親がJSONの秘密の追加キーを透過するRedを確認後、厳密な再検査と固定出力を実装。
- 起動/回収境界の不具合と連続signalは、指摘後に実子または故障注入でRedを再現し修正。
- 最終レビューのプロセスグループINT/TERM分類のP2も、追加試験のRedを確認後に修正した。

[検証結果](../validation/source-info-tests.json)と[全ホストログ](../validation/source-info-tests.txt)を保存。期待値を削除・skipして通す変更はしていない。

## ⑥ 独立実装レビュー（fresh context・最大3周）

| 周 | 設計 | テスト | 安全/運用 | 対応 |
| --- | --- | --- | --- | --- |
| 1 | P1: Popen返却前signalで子残存、cleanup例外で固定出力/handler復元欠落 | P2: 既知5能力中3種の固定期待値不足 | 同P1 2件、P2: 版違いJSONがworker_failedに隠れる | 起動中flag/回収finally、固定cleanup_error、5能力固定期待値、版違いworker0/親2を追加 |
| 2 | P1: 連続signalでcleanup境界から再度例外が出て子残存 | P0/P1なし、前P2解消 | 同P1 | handlerを常時flag専用へ整理。最大0.1秒の期限付き待機で中断を検出。連続signalと期限cleanup境界を実子で検証 |
| 3 | P0/P1なし。P2: グループINT/TERMがworker_failedになる場合 | P0/P1なし、17試験通過 | P0/P1なし、17試験通過 | 主担当がP2のRedを確認し、communicate成功後にもcancelledを再確認。全回帰を再実行 |

第4回の独立レビューはしていない。最終P2修正は主担当の試験で確認し、独立再レビュー済みとは扱わない。

## ⑦⑧・未完了

[TEST-009](../device-tests/009-source-info.md)を人間レビュー/実機照会へ提示。実機でのhelper動作・server_version/build取得・横長取得本体・性能合格は未完了。⑧の人間指摘後のリファクタリングも未完了。作業中のhandler責務整理はGreenで確認済み。

## 取得経路の根拠

公開LoopCtrl commit `6fc759fcce397c92482c2a8c6f90244e5374aac9` を参照。

- [ActionHandler.swift](https://github.com/Souitou-iop/LoopCtrl/blob/6fc759fcce397c92482c2a8c6f90244e5374aac9/LoopCtrlUITests/ActionHandler.swift): pointSizeをキャッシュし、screenshotをその寸法×scaleへ描画する。bundle_id指定でもtarget寸法は変わらない。
- [LoopCtrlUITests.swift](https://github.com/Souitou-iop/LoopCtrl/blob/6fc759fcce397c92482c2a8c6f90244e5374aac9/LoopCtrlUITests/LoopCtrlUITests.swift): 初期app参照はSpringBoard。
- [ScreenStream.swift](https://github.com/Souitou-iop/LoopCtrl/blob/6fc759fcce397c92482c2a8c6f90244e5374aac9/LoopCtrlUITests/ScreenStream.swift): CGImage寸法を基に縮小・動画符号化する。無変換・横長実機成立・iSHでの高速復号の証明ではない。
- [RPCMethod.swift](https://github.com/Souitou-iop/LoopCtrl/blob/6fc759fcce397c92482c2a8c6f90244e5374aac9/LoopCtrlKit/RPCMethod.swift): 公開ソースはserverVersion1.98.14、video_stream/stream_ticket。実機版との一致は未確認。
