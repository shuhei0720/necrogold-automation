# 作業ごとのコンテキスト

最初は [AGENTS](../AGENTS.md)・[現在の状態](status.md)・本索引を読む。この3文書は合計16KiB以内とし、最新結果・今回の計画・必要な契約へ案内する。現行版、配布物、試験結果はstatusを正本とする。

機能を変える前に [要件正本](requirements/necrogold.md)、[開発フロー](development-flow.md)、[制御契約](contracts/native-control.md) の該当節を読む。TEST072の探索/level切替は[限定契約](contracts/passage-approach.md)も参照する。以下の表から対象の関数と試験を選び、`rg -n` で位置を探して周辺を読む。大きいファイルを一括で読んだことを、影響範囲の確認の代わりにしない。

| 作業 | 対象コード・入口 | 対応する試験・資料 |
| --- | --- | --- |
| 現在の不具合・今回の計画 | statusの結果と計画リンク | [検証の区分](testing.md)、該当する受領記録 |
| 入力予約・初歩・再予約・motion | `patches/loopctrl/ngg2/NG2Controller.c` の `reserve`、`ng2_controller_observe_at/tick/begin/complete`、`resolve_move`、`reference_*` | `tests/test_native_closed_mouth080.py`・`tests/test_native_dirt_ticket079.py`・`tests/test_native_passage_palette077.py`・`tests/test_native_open_entry077.py`・`tests/test_native_stationary_wait076.py`・`tests/test_native_passage_unsent076.py`・`tests/test_native_view074.py`・`tests/test_native_ui073.py`・`tests/test_native_observation072.py`・`tests/test_native_passage072.py`・`tests/test_native_shop071.py`・`tests/test_native_terrain071.py`・`tests/test_native_cadence070.py`・`tests/test_native_gate069.py`・`tests/test_native_edge068.py`・`tests/test_native_blocked067.py`・`test_native_cadence067.py`・`tests/test_native_device066.py`・`test_native_shop066.py`・`test_native_device065.py`・`test_native_device064.py`・`test_native_gate064.py`・`test_native_unsent_continuous.py`・`test_native_device061.py`・`test_native_motion_cadence.py`、旧回帰は`test_native_controller.py`・`test_native_recovery.py`、[制御契約](contracts/native-control.md) |
| 拍の取得・追跡 | `patches/loopctrl/ngg2/NG2Beat.c` のfit/track、Controllerのmodel検査 | `tests/test_native_beat.py`、`testInitialSlotPreparationPublic` |
| 地形・移動・入口・商品 | `patches/loopctrl/ngg2/NG2Navigation.c`、`NG2Perception.c`、`NG2Core.h` | `tests/test_native_sparse_gate080.py`・`tests/test_native_revealed_gate079.py`・`tests/test_native_closed_gate078.py`・`tests/test_native_static075.py`・`tests/test_native_motion075.py`・`tests/test_native_motion074.py`・`tests/test_native_passage_navigation072.py`・`tests/test_native_door072.py`・`tests/test_native_navigation.py`・`test_native_motion067.py`、`test_native_perception.py`・`test_native_fringe068.py`・`test_native_icon066.py`、必要時だけ[動画観察](video-2-analysis.md) |
| 取得・画像変換 | `patches/loopctrl/ngg2/NG2Raster.swift`、`NG2CaptureBridge.m`、Perceptionのorientation処理 | `tests/test_native_raster.py`、`patches/loopctrl/ngg2_raster_tests.swift` |
| 並行処理・前面・取消・drain | `patches/loopctrl/ngg2/NG2Runtime.swift`、`NG2Ticket.swift` | `patches/loopctrl/ngg2_runtime_tests.swift` の対応する公開fixture、`check_ngg2.py` の該当mutation |
| 診断・旧journal・結果回収 | `necroprobe/native_walk.py` の `_report`、`_load`、`_collect_paged`、`run_session`、Runtimeのcache/priorityCaptureIDs/selectedExportFrames/results | `tests/test_native_compat070.py`・`tests/test_native_release070.py`・`tests/test_native_collection069.py`・`tests/test_native_publication069.py`（`necroprobe/test069.py`のlocal spool/ZIP公開）・`tests/test_native_collection068.py`、`tests/test_native_results.py`、`test_native_motion_references.py`、`test_native_recovery_results.py`、`test_native_paged_results.py`、`test_native_export_batch.py` |
| 接続・起動・暗号HTTP | `necroprobe/native_walk.py` のpreflightとstart、`protocol.py` | `tests/test_json075.py`・`tests/test_native_connect.py`、`test_http_diagnostics.py`、`test_protocol.py`、`test_http_and_cli.py` |
| 実記録の評価 | `tools/evaluate_device_recording.py` のarchive/lineage/partial/milestone | `tests/test_device_recording.py`、[証明範囲](testing.md) |
| compiler・封印・IPA | `patches/loopctrl/check_perception_build.py`、`apply_ngg2.py`、`verify_package.py` | `patches/loopctrl/test_*.py`、[Mac workflow](../.github/workflows/loopctrl-geometry.yml) |

Swiftの公開fixtureは `testContinuousRevalidationCallbacksPublic`、`testPagedResultsPublic`、`testTargetDriftRevalidationCallbacksPublic`、`testInitialSlotPreparationPublic`、`testOriginalMotionReferencePixelProof` / `testOriginalMotionReferenceCallbacksPublic` を手掛かりにする。fixtureを選ぶhelperの文字列置換・対象範囲も確認する。

[実機台帳](device-tests/README.md)は履歴であり、全文を通常の初期コンテキストに含めない。必要なTESTの見出し・該当節だけ読む。[整理前の原文](archive/context-pre-refactor/README.md)は過去の事実の照会用で、現在の指示として適用しない。旧Python制御の調査では `necroprobe/shop_walk.py` と対応する旧TESTを別途選ぶ。
