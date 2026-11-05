# P1.4 / BUG-P1-003 独立レビュー記録

日付: 2026-11-05（日本時間）。修正対象はTEST-003のゲーム起動前timer_already_in_use。P1.3以前のレビューとは別のスコープ。最大3周で実施。

担当: `p14_timer_design`（設計・異常系・網羅）、`p14_timer_safety`（安全性・停止・例外）。新規コンテキストで資料と対象ファイルから独立確認。実装は主担当が行い、レビュー担当はread-only。

## 第1周: 原因・プラン

- iSH公式timer_new/timer_setの旧値が活動状態の証拠にならないことを確認。解除後の負値や生成直後の未初期化値を復元する方式は廃止。
- 専用子プロセスのmain threadで明示所有し、Clientへ注入する案を採用。一般プロセスの既存タイマーを保護・復元するAPIとはしない。iSH fork側のitimer=NULLも確認。
- safety担当は旧方式のSIG_DFL復元後にpending SIGALRMで子が-14終了する例を再現。また、cleanupエラーがKeyboardInterruptを覆う問題を指摘。worker期間のhandler保持/終了時SIG_IGN、元理由維持と別cleanup診断を計画へ追加。
- 旧値の初回無視だけではなく連続RPCと終了処理、実親子HTTP経路を試験する要求を追加。

## 実装前Redと初回Green

実setitimerの動作は残し、戻り値の読み取りだけを禁止する故障注入。旧P1.3で連続取得の1試験が旧値比較により失敗した。[Redログ](../validation/p1-owned-timer-red.txt)。OwnedRpcTimer分離、必須注入、固定エラー・poison、worker診断へ実装した後、初回全93試験通過。

## 第2周: 実装レビュー

両担当が旧値への非依存と所有契約、模擬HTTPでの12枚保存を確認。safety担当は互換性23、親子HTTP3、停止6の計32試験を独立実行し通過。以下の指摘は主担当が再現・修正。

| 指摘 | 対応と回帰 |
| --- | --- |
| 設計P1: 期限前のSIGALRMを捨てると、現在のone-shotの早期発火時にRPC期限が消える | iSHのrealtimeタイマーと単調時計の差を前提に、残り時間で再arm。早く実タイマーを消費する故障で0.5秒まで待ってしまうRedを観測し、0.08秒の期限で中断するGreenへ |
| 両担当P2: sys.exc_infoは呼出側の外側exceptを拾い、成功RPCのcleanup失敗を抑制する | deadline自身から伝播する例外をexcept BaseExceptionで明示追跡。外側の処理済み例外に左右されないよう変更 |
| safety: 初期化途中のKeyboardInterruptでowner/handlerが残る | __enter__で中断時もcloseし、元のKeyboardInterruptを保持 |

追加テストは先に実行し、28件中4失敗を確認（[追加Redログ](../validation/p1-owned-timer-review-red.txt)）。早期通知の再arm失敗時poison、各固定エラーで次のRPCへ進まない試験も追加。全98試験通過。

## 第3周: 最終確認

両担当とも前回指摘の解消を確認し、今回範囲で追加のblocking指摘なし。設計担当は関連9試験、safety担当はタイマー28＋親子HTTP3の31試験を独立実行し全通過。safety担当は初期disarm中断とcleanup失敗の併発でも元KeyboardInterrupt・固定診断・所有解放を追加確認。保存済み全98試験ログも確認した。3周を終了し、第4周は行っていない。実機合格は主張しない。

## 合格としていないもの

実iSH、実LoopCtrl、ゲーム起動成功、画面の新鮮さ/向き/座標、入力、操作速度、長時間動作。TEST-003は不合格、TEST-004は未実行。P1全体のゲートは通過していない。人間レビュー後の独立したリファクタリング工程は未実施。
