# 取得元の画像寸法修正（NG-G1）

2026-11-05（日本時間）。TEST-009で実機API 1.98.14 / build 2026-11-01 16:49 / protocol 1 / native_i386 / video_stream・stream_ticketを確認。公式v0.3.4は同API版を掲げるが、実機バイナリとcommitの同一性は未証明。

## 1. 概要

クライアントで歪みを戻す処理を追加せず、取得元が画像自身の比率に合う寸法で1回だけ描画・符号化する診断用変更を作る。既存screenshotの既定動作は保持し、geometry="image_size_v1"という明示指定で選ぶ。入力座標は検証済みとしない。

## 2. 背景

公式v0.3.4 commit `6e25cf6a9f65bc86c372cdce94bdb151d0cf6767` のActionHandler/RPCMethod blobは、既に調べた公開commitと同一。screenshotはcached pointSize×scaleへ描画する。AppleのUIImage.size契約は向きを反映した論理寸法で、size×image.scaleが表示ピクセル寸法。これを使えばキャッシュが414×896でも画像1792×828を896×414(scale1)として返せる計算になる。実際のキャプチャ内容と速度は実機確認が必要。

video_streamはH.264/HEVCを使い、iSHでの復号負荷が未測定。今回その依存は追加しない。

## 3. 詳細設計

### 取得元パッチ

3ファイル（ActionCommand、ActionHandler、RPCMethod）だけをSHA-256/元blobに一致したv0.3.4へ適用。既存ファイル不一致・二重適用は書換え前に停止。配布元の全ファイルを複製せず小さな差分と適用スクリプトを保存する。

ActionCommandにgeometryを追加。nilは従来どおり、image_size_v1のみ新モードとして受け入れ、未指定のみ旧モード。明示null/空文字/未知文字列/数値/bool/配列/objectはキャプチャ前に引数エラー。新モードではbundle_idの指定（空文字も含む）を取得前に拒否し全画面1回に固定。画像取得自体はXCUIScreenの既存処理を再利用。

要求scaleは既定2、有限数に限り既存同様0.05〜3へclampする（0/負数/0.04は0.05、4は3）。新モードの出力px = UIImage.size × UIImage.scale × effectiveScale / deviceScale（各軸）。image_point寸法 = UIImage.size × UIImage.scale / deviceScale。要求scaleは有限、画像寸法/image.scale/deviceScale/effectiveScaleと算出寸法は有限・正値、丸め前は各軸1〜4096・総画素8,000,000以下、四捨五入した最終整数にも同じ上限を適用。新モードでは描画後のjpeg/png符号化1回のみ、失敗/空データはRPCエラーにし元画像fallbackを禁止する。旧モードの既存fallbackは保持。余分なクライアントリサイズ、追加の画像取得、画面回転、位置設定変更はしない。sourceの向き・寸法・scaleと実際の出力寸法を返す。RGB/PNG/JPEGのデコード実寸を実機で確認する。

point_width/heightは既存の入力側申告値のまま保持し、表示画像由来のimage_point_width/heightを別にする。新モードのhintは「画像ptと入力ptの対応未検証」で置換し、input_geometry_verified=falseを付ける。ホーム画面を含む応答構築の最後に警告を付ける。schemaとdevice_infoのpixel/scale換算説明にも新モード除外条件を加える。旧screenshotのhintと出力は変更しない。版は1.98.14-ngg1、capabilityにscreenshot_image_geometry_v1を追加する。

### ビルドと配布

所有リポジトリの専用GitHub Actions workflowで、固定commitの公式ソースを取得しパッチを適用、Swiftの数値契約試験、公式と同じunsigned IPA buildとpackage-release.sh、既存LoopCtrlKit tests、.xctest/cliの同梱とプロビジョニング情報がないことを確認し、IPA・SHA256・ログをActions artifactとして保存。公開releaseは作らない。workflow permissionsはcontents:read、上限60分。Actionsは確認済みcommit SHAへ固定、checkoutはpersist-credentials:false。上流/driver commit、patch SHA、Xcode/Swift/Rust/XcodeGen版、IPA SHAをmanifestに残す。署名鍵・Apple ID・UDIDは使用しない。ビルド成功と実機への導入は別。

Swiftコンパイラ/UIKitは現在のLinux作業環境にない。Swift契約の実行とiOSコンパイルはmacOS CIで行い、動いていない段階で合格と書かない。CI起動権限やrunnerの利用可否で阻まれた場合は、その地点と実行可能な成果物を明示する。

### クライアントと端末受入

ビルド成功後、新capabilityを確認してgeometry指定を送る診断クライアントを用意する。旧版へ未知パラメーターを送り、無視された結果を成功としない。rawバイトを保存し、UIImage由来寸法と実px、原画像のゲーム表示、scale1/2別時間を比較する。P1.4の既存経路とR12は保持。試験用IPAの導入は完成・署名手順確認後に案内し、現時点で削除や再インストールを依頼しない。

## 4. 影響範囲

patches/loopctrl、専用workflow、試験と記録のみを先行作成。標準RPC/入力・認識・ゲーム操作には変更しない。necroprobeの新引数はCI結果を受けて別に受け入れる。legacy/r12全40ファイルは不変。

## 5. 新規試験

- パッチ元3ファイル完全一致、不一致/途中欠落/二重適用で全書込なし。
- 実装前に固定元ActionHandlerの寸法式をSwift harnessで実行し、横長契約のassert失敗を観測する（UIKit/実機の実行ではない）。実装後は本番ActionHandler内の純粋なNGScreenshotGeometry関数を切り出し、実ActionCommand/RPCTypesと一緒にSwiftで試験する。CI Redでは同じ関数のtargetだけを固定元ソースのcached式へ変異させ、コンパイル成功後にlandscape_scale1の寸法assertで失敗することを要求。Greenは本番関数そのものと同じ期待値で実行。終了コードとケース名を保存し、数値/選択/encoding closure/警告辞書の成功をUIKit実描画成功と呼ばない。
- ソース横長/縦長、UIImage.scale 1/2、deviceScale 2/3、requestedScale 1/2、非有限/0/超大/8M境界・丸め前4000.6×1999.6→丸め後8M超拒否・正方形・scale3、旧モードの寸法維持。
- 3ファイルだけ変更、旧標準経路不変、新hintが通常/ホームの最終応答で保持されinput_geometry_verified=false、JPEG/PNG失敗時は0バイト成功や元画像fallbackなし。bundle_id拒否、追加キャプチャ/クライアント変換なし。
- 実機: 同じGAME PAUSE・向きでraw896×414/1792×828と比率/EXIF/実保存/全体時間を確認。画像生成時刻や入力ptは別未検証。

## 6. 実装順

①本計画→②③設計/テスト/安全のfresh-contextレビュー→④⑤パッチ適用のホストRed、最小実装/回帰、CIでSwift Red/Greenとbuild→⑥独立実装レビュー最大3周→⑦完成配布物と端末受入を人間レビュー→⑧指摘を受け必要な整理。ビルドが阻まれた場合は⑥以前の未完了を明記し、IPAがあると称さない。

## 7. 保存前確認

原資料ハッシュとTEST-009転記、3ファイル制約、秘密値なし、固定commit・依存元、パッチ適用テスト、取得側コードの独立レビュー。CI結果・artifact・使用commitを追跡。ホスト式の成功とUIKit実機成功を分離する。

## 8. スコープ外

動画復号導入、取得後の縦横変換、推測タップ、オプション校正、再購入/探索/周回、OS回転・恒久位置情報、取得元の無断入替、署名鍵の保存、実測なしの速度達成宣言。
