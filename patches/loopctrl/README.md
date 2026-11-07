# LoopCtrl取得元の画像寸法修正 NG-G1

TEST045ではNG-G2を更新する。初方向が確実未送信の場合だけ最新sceneで安全床と同方向を再検証し、元拍/期限内の再計画を通算2回まで許可する。旧callbackはcommand IDで隔離し、実終了まではdrainへ計上する。差分元/差分後の画像と固定診断を保持する。新capability `necrogold_native_v2` をv1と併記し、新clientはv2を必須とするため、新IPAへのSideStore更新が必要。API `1.98.14-ngg2` と旧v1契約は維持する。新IPA/ホスト・CIの最終検証と実機確認は[既存台帳](../../docs/device-tests/README.md)末尾を参照する。

## NG-G2 / TEST043 native制御の追加

固定上流とNG-G1の画像幾何を保持し、NG-G2ではiPhone内のC判定・拍同期とSwiftの取得・期限付き単発入力を組み合わせる。API版は`1.98.14-ngg2`、capabilityは`necrogold_native_v1`。iSHは`necro_native_start/status/cancel/results`から実行と記録を管理し、capabilityのないNG-G1へ新しい入力を要求しない。商品候補を保持し、自動購入しない。実機の毎拍成功・所要時間はTEST043で確認する。

NG-G2は既存9ファイルへの差分と`ngg2/NG2*`のC/Swift/Objective-Cソースを含む。実RPC契約のSwift試験だけは`Tests/LoopCtrlKitTests`へ配置する。`ngg2-manifest.json`がNG-G1適用済み入力、差分、追加ソースの全SHA-256を固定する。追加先の既存ファイル・symlink・不一致・二重適用は導入前に拒否し、置換障害では導入したファイルを戻す。CIはmanifestを生成せず、レビュー済みmanifestに一致するソースだけをビルドする。

```sh
python3 patches/loopctrl/apply_patch.py /path/to/LoopCtrl
python3 patches/loopctrl/check_geometry.py /path/to/LoopCtrl /tmp/ngg1-contracts
python3 patches/loopctrl/apply_ngg2.py /path/to/LoopCtrl
python3 patches/loopctrl/check_ngg2.py /path/to/LoopCtrl /tmp/ngg2-contracts
```

取得開始/完了、入力呼出開始/完了は端末monotonic時計の境界であり、画面の厳密な生成時刻・タッチ受領時刻・ゲーム受付時刻ではない。実行済みか不明な入力は再送しない。端末キャンセルは未開始の入力を止め、開始済みsynthesizeの取消成功を意味しない。

開発時にソースを更新した場合は、固定上流にNG-G1だけを適用した別checkoutで`python3 patches/loopctrl/apply_ngg2.py --seal /path/to/ngg1-checkout`を実行し、manifest差分もレビューする。既存NG-G1のパッチ・manifestとR12は変更しない。

macOS workflowはmanifestのない先行段階ではコンパイル可能なSwift stubの挙動Redだけを実行する。manifest保存後はNG-G1/NG-G2契約、unsigned IPAと既存LoopCtrlKit試験、構成・来歴検査へ進み、IPA・SHA-256・manifest・改変取得元と追加ソースの全文をprivate Actions artifactへ保存する。SideStoreでの更新とTEST043実機確認が別途必要で、CI成功を実機合格にはしない。

native Cのsynthetic契約はUbuntu CIでも実行する。private実画像が必要な6試験はCIの明示除外一覧に記録し、既知画像全件の比較と実画像sanitizerはローカルの必須試験で実行する。画像不足をskipして全件成功にはしない。

公式v0.3.4 commit `6e25cf6a9f65bc86c372cdce94bdb151d0cf6767` に適用する診断用パッチ。API版は `1.98.14-ngg1`、新capabilityは `screenshot_image_geometry_v1`。変更済みの取得元3ファイルはActionsの配布artifactにも全文を含める。

`screenshot` に `geometry: "image_size_v1"` を明示した場合、キャッシュされた入力側寸法ではなく、取得したUIImage自身の寸法・scaleから出力を計算する。ゲーム画像が1792×828、deviceScale=2なら、scale1で896×414、scale2で1792×828が期待値。既存の描画・符号化1回で返し、受信後の縦横変換は追加しない。画像のpointと入力のpointの対応は未検証なので、タップ座標には使わない。

指定なしの従来経路を保持する。新モードのbundle_idは拒否し、取得を全画面1回に限定。未知/空/null/型不正のgeometryは取得前に拒否する。寸法上限・丸め後上限を検査し、描画/符号化失敗を元画像へのフォールバックで隠さない。

## 試験と実行

[実装前のSwift Red](../../docs/validation/ngg1-baseline.json)は観測済み。元寸法式が期待896×414に対して414×896を返すことを確認した。最初のCIはコンパイル失敗だったためRedに数えていない。CoreGraphicsを明示importした実行でコンパイル成功後の期待する失敗を確認した。

macOSと、固定commitのLoopCtrl checkoutを用意して実行する。ソースパッチは3ファイル全ての元SHA-256/blobと適用後SHA-256を検証する。不一致、欠落、二重適用、差分破損は書き換え前に停止する。

```sh
python3 patches/loopctrl/check_baseline.py /path/to/LoopCtrl /tmp/ngg1-baseline
python3 -m unittest discover -s patches/loopctrl -p 'test_*.py' -v
python3 patches/loopctrl/apply_patch.py /path/to/LoopCtrl
python3 patches/loopctrl/check_geometry.py /path/to/LoopCtrl /tmp/ngg1-contracts
```

Swift契約試験は本番関数を直接切り出して実行する。元のキャッシュ式へ戻した変異も失敗することを確認する。UIImageの実描画、ゲーム表示、速度はこの数値試験で証明しない。

専用[workflow](../../.github/workflows/loopctrl-geometry.yml)は、上記試験、unsigned IPA build、既存LoopCtrlKit tests、.xctest/CLI同梱と個人プロビジョニング情報がないことを確認する。IPAとSHA-256、上流/driver commit、patch SHA、toolchain情報をprivate Actions artifactへ保存する。署名・端末への導入・端末受入は別工程。公開releaseは作らない。

取得元修正のCI・独立レビューは完了。Swift91契約、IPA build、既存LoopCtrlKit tests、構成検査が成功。新capabilityを確認するP1.5も用意し、次は[TEST-010](../../docs/device-tests/010-source-landscape.md)のSideStore更新と実機試験。R12は変更しない。

## ライセンス

LoopCtrlの原ソースはApache-2.0。[LICENSE](LICENSE-LoopCtrl.txt) と [NOTICE](NOTICE-LoopCtrl.md) を保持する。改変3ファイルに変更を明記する。第三者コンポーネントの通知は上流のパッケージ処理を保持する。
