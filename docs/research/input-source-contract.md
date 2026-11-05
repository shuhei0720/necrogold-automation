# 取得元の入力・期限契約の調査

2026-11-05（日本時間）。公式LoopCtrl v0.3.4 commit `6e25cf6a9f65bc86c372cdce94bdb151d0cf6767` と、その固定元へNG-G1パッチを適用したActionHandlerを対象。TEST-010の横長原画像から入力の合格を推定しないための調査。新機能の実装済み仕様ではない。

## 現実装から確認したこと

| 対象 | 確認した契約 |
| --- | --- |
| cached pointSize | SpringBoardとして生成されたappのframeを初回キャッシュする。今回の414×896は画像896×414と別情報 |
| 既定tap | x/yをそのままFastActionHandler.fastTapへ渡す。XCPointerEventPathのCGPointでdown0秒/up0.05秒。画像由来の回転変換なし |
| fast:false | SpringBoard appの正規化原点にx/y offsetを加えXCUICoordinate.tapを呼ぶ。別のnative fast_inputというAPIは確認できない |
| source_orientation | UIImageのimageOrientation。XCUIDevice.orientationではなく、数値2だけでtap変換方向を確定しない |
| foreground/lock | device_info.systemの観測値。前面のbundle解決はPID/AXとキャッシュ等を使う。unknownをgame扱いしない |
| rotate | 読取りではなく端末向き変更・待機・キャッシュ削除を伴うため診断の読取りに流用しない |
| find_element | スクロールしないAX label/id検索。ref/frameを返し得る。hittableはsnapshot内のinView近似で遮蔽を保証しない。複数候補の報告がないことは全ツリーの一意性ではない |
| screen_text | CGImageを.upでOCRしcachedPointSizeへ比率換算する。今回検証したい幾何仮定を再使用するため独立した座標根拠にならない |
| ACTION touch表示 | 合成イベント送信前の予定座標通知。実際の着地点を記録した証拠ではない |
| HTTP timeout | UIキューが詰まった要求はtimeout応答後も実行され得る。開始したXCTest呼出しは強制取消できない |
| control release/pause | 操作者表示の解除や入口制御。待機済み入力が取り消された証拠にはならない |

## 原ソース

- [FastActionHandler.swift](https://github.com/Souitou-iop/LoopCtrl/blob/6e25cf6a9f65bc86c372cdce94bdb151d0cf6767/LoopCtrlUITests/FastActionHandler.swift): 合成イベント、fastTap。
- [LoopCtrlUITests.swift](https://github.com/Souitou-iop/LoopCtrl/blob/6e25cf6a9f65bc86c372cdce94bdb151d0cf6767/LoopCtrlUITests/LoopCtrlUITests.swift): SpringBoard app、nonUI queue、rpcTimeout、watchdogでのqueued/unknown応答。
- [ForegroundApp.m](https://github.com/Souitou-iop/LoopCtrl/blob/6e25cf6a9f65bc86c372cdce94bdb151d0cf6767/LoopCtrlUITests/ForegroundApp.m): 前面PID/bundle解決。
- [ActionHandler.swift](https://github.com/Souitou-iop/LoopCtrl/blob/6e25cf6a9f65bc86c372cdce94bdb151d0cf6767/LoopCtrlUITests/ActionHandler.swift): pointSize、tap、findElementInfo、locateElement、screenText。

NG-G1は画像出力式とgeometry契約を変更した。上記入力とwatchdogの問題は変更していない。

## 次工程で満たす必要があること

まず[TEST-011](../plans/p1-input-path.md)でゲームの続行対象がAX参照として取れるか確認する。取れない場合の座標正解は、専用の無害な診断画面で実touch受信位置と画像内markerを対応させ、校正に使わない点で検証する案がある。追加実装と実機試験が必要で、現在ある機能とは呼ばない。

実際に入力を行う版には、端末の実行直前に期限・期待アプリ・lock・観測/幾何の契約を確認する処理が必要。取消と未送信→submittedの状態遷移は同じlock下で決め、入力送信中はlockを保持しない。開始済み入力を取消済みと偽装せず、submitted/unknownとする。再送は自動で行わない。

前面を前後2回読んでも観測間のゲーム→他アプリ→ゲームは検出できない。「観測世代」をOSの切替世代と同一視しない。API呼出し開始/終了の単調時刻も、OS内部の画像生成時刻とは別。100/300msの停止目標、150ms/10Hzの鮮度目標は実機結果で判定する。
