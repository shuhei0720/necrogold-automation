# NG-G1取得元寸法修正のレビュー

2026-11-05（日本時間）。TEST-009受領後の別変更単位。

## 計画①〜③

設計・試験・安全のfresh-context担当が2周レビュー。第1回で既存encoderの元画像fallback、bundle_idの再取得、scale/round順、画像pt定義、型不正のnil化、ホーム画面hint上書き、schemaの入力換算説明、Swift試験と本番の結合を指摘した。

[計画](../plans/p1-source-geometry.md)に、新モードのstrict encoder/RPC error、bundle_id指定拒否、要求scaleの有限判定と有効scaleの利用、丸め前後の上限、最終warn、型不正拒否を明記。本番関数を試験し変異を検出すること、Actions commit固定・persist-credentials:false・成果物manifestを追記した。第2回は全担当P0/P1なし。数値試験とUIKit/実機を混同しない。

## 実装前Red観測用の小CI

取得元の修正本体を作る前に、固定元ソースから実際の2つの寸法式を取り出してSwiftでコンパイルし、横長契約の期待値に失敗することを確認するcheck_baseline.pyとmacOS CIを準備した。Linuxでは元blob一致・ハーネス生成・改変ソース拒否を確認。Swiftはこの環境にないためローカルでは実行していない。

この小CIを別のfresh-context設計/試験/安全担当が独立レビューし、全員P0/P1なし。コンパイル失敗は別に停止させ、期待するRedは「実行終了1＋指定assert本文完全一致＋stderr空」の場合だけ受理する。

Swift寸法契約がRedであることと、期待Redを検出するCIジョブがGreenであることを区別する。現時点ではCI結果待ち。コード本体、iOSビルド、IPA、実機の横長取得/性能は未完了。
