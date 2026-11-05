# TEST-010受領資料の独立レビュー

2026-11-05（日本時間）。対象: test-010.zip / IMG_8534.png、TEST-007比較、TEST-010手順と要件。主担当とは独立したfresh-context担当test010_evidence_reviewが原ZIP・生ns・原画像を検算した。診断コード変更はないため既存131ホスト試験は再実行していない。

## 結果と修正

- P0なし。ZIP CRC・安全な相対パス、原画像3枚の長さ/SHA/実寸/EXIF/輝度、両reportの3群×11区間の集計が一致。
- P1（判定範囲）: 12枚全てのゲーム画像目視、鮮度、座標、取消、人より速い周回、P1合格を宣言しない。原画像3枚と12行メタデータの証拠範囲を分離した。
- P1（遮蔽/反復）: 保存3枚の上部操作バナー、後半の同形式SHA反復を記録した。直前の異形式と比較するsame_bytes_as_previous=falseを鮮度根拠にしない。
- P2（性能）: 各4回、p95は最大値、warmup除外0。総画素数は前回と等しいが縦横寸法・表示・圧縮サイズ・実行条件は異なる。観測差をパッチだけの影響と断定しない。
- P2（同一性）: P1.5/geometry/capabilityは確認。端末ソースhash/API版文字列/IPA hashはreportにないため、配布物との同一性確認とは分けた。

判定: **取得元の横長出力・正常な比率は保存3原画像で確認。12回の寸法契約と正常終了を確認。P1全体は未合格。**

[再計算コード](../../analysis/test-010/analyze.py)は元ZIPを変更せず、保存画像と生タイムスタンプを検算し[派生結果](../device-tests/test-010-results.json)を生成する。画像の受信後変換は行わない。今回リファクタリングは不要。

## 次工程に向けた固定元の独立調査

別のfresh-context担当p1_next_source_reviewが固定LoopCtrl commit `6e25cf6a9f65bc86c372cdce94bdb151d0cf6767`を調査。

- 入力はFastActionHandlerのXCTest合成イベントかXCUICoordinate。別API「fast_input」は確認できない。
- pointSizeはSpringBoardのapp.frameのキャッシュ。画像のUIImage.orientationと入力系は別であり、縦横寸法の交換だけで変換方向を決めない。
- `LoopCtrlUITests.swift`のUIキューはHTTP側期限後も実行し得る（1633–1653行）。host側timeoutは端末の取消ではない。
- find_elementはスクロールしないAX照会。label/ref/frameが取れれば、画像変換に依存しない操作対象の根拠を得る候補になる。ただしhittableは遮蔽を保証せず、実タップ成功も未確認。
- screen_textのOCRは画像方向とcachedPointSizeの仮定を再使用するため独立した入力座標の正解に使わない。

次の[読取専用TEST-011計画](../plans/p1-input-path.md)は入力方式の選択に必要なAX候補を1回照会する。ゲーム内入力を行う版には別途、期限/取消の端末側ガードが必要。
