# TEST064: 同じ未送信歩行を遠方の描画揺れで失わない

2026-11-10（日本時間）。TEST063はユーザーの商品可視1/3。2回目は開扉後の次MOVE前、3回目は初歩前に停止。3run全てSCREEN17だが実Cの画面判定はFLOORで、遠方1cellの変化に対する予約再検証が直接原因。原画・時刻・hashはGit外、受領要約は台帳へ置く。

## 原因と変更

- 初歩83→84はreplan2回を消費後、元notBefore約90ms前の遠方DIRT→UNKNOWN。全5field判断/金/保護/局所歩行床/strict BLOCKEDは同じだが、quiet処理の50ms窓外だった。既に公開された初歩ticketの100ms公開期間までquietを適用する。未発行ticketを作らず、再予約回数・元12秒・元ID/拍/全期限は維持する。
- 1回目120→121、2回目139→140は開扉後のgate_single_probe/FLOOR、商品PARTIALで全5field同一・strict BLOCKED・金/保護不変。遠方DIRT↔STONEだけの変化も既存safe_floorのgate/PARTIAL拒否で終了した。lead確認/実移動済み・state1確実未送信の入口1歩に限り、同IDのquietを追加する。before/current FLOOR、同goods UNKNOWN/PARTIAL、origin/next床・金bracket・保護と局所近傍不変、遠方UNKNOWN/FLOOR/DIRT/STONEのみ、全5field同一、strict BLOCKED、元source/model/全期限を必須にする。

quietは入力の再送・source/期限延長・実再予約ではない。既存continuous/FRESH/初歩校正のsafe_floor条件とcounterを変更しない。VISIBLE商品/取消/owner/lock/prefix/世代/未知入力/送信済みの禁止は既存通り。画面/商品認識閾値・Navigation・Runtime・公開ABI/API/cap/clientは変更しない。下方の商品を未観測のまま陰性にせず、停止原因を除いて既存plannerが追加移動を判断する。実機到達は次試験で確認する。

## 確認と返却

元画像を実Perception/Navigation/Motionへ渡し上記条件を照合する。初歩と入口の新単体を旧Cでassertion Red→修正Green。公開窓、同ID/全時刻不変、全方向、遠方揺れ、近傍/金/商品/保護/判断/署名変位/期限/入力状態/取消の負例を選び、変更境界に関係する旧回帰を実行する。独立差分レビュー1回、必要なdevice laneの実IPAビルド・seal/実compiler/来歴/完全source照合後、固定ReleaseのTEST064を返す。全Runtime/world/未変更clientを毎回再実行しない。
