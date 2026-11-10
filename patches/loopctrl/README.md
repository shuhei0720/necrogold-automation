# LoopCtrl取得元の画像寸法修正 NG-G1

TEST050では、1歩の確認後に次拍期限を超えたTEST049を受け、既存のPerceptionに加えNG2Navigation.cだけを -O2 -fno-fast-math -ffp-contract=off でビルドする。C算法・判定閾値・元拍/入力期限、他C2個/ObjC/Swift/全体Debugは維持する。成功commit gate内のC observe直前にobserve_start_nsを記録し、既存observe_end_nsとの区間を次の実機で計測する。実生成PBXとraw Clang/response証跡のprofilev2をnative_v7のpackageで必須とし、旧native_v6のprofilev1検証を保持する。clientv8/test_050.shは新IPAが必要。SideStore更新後はLoopCtrlを完全終了/起動してStart Server。新IPA/全sourceの証跡と実機依頼は[既存台帳](../../docs/device-tests/README.md)末尾のTEST050を参照する。毎拍歩行と人より速い性能は実機受入まで未完了。

## NG-G2 / TEST043 native制御の追加

固定上流とNG-G1の画像幾何を保持し、NG-G2ではiPhone内のC判定・拍同期とSwiftの取得・期限付き単発入力を組み合わせる。API版は`1.98.15-ngg2`、capabilityは`necrogold_native_v1`。iSHは`necro_native_start/status/cancel/results`から実行と記録を管理し、capabilityのないNG-G1へ新しい入力を要求しない。商品候補を保持し、自動購入しない。新clientはnative-walk-v14/cap13を要求する。商品到達・毎拍性能はTEST061実機で確認する。

NG-G2は既存9ファイルへの差分と`ngg2/NG2*`のC/Swift/Objective-Cソースを含む。実RPC契約のSwift試験だけは`Tests/LoopCtrlKitTests`へ配置する。`ngg2-manifest.json`がNG-G1適用済み入力、差分、追加ソースの全SHA-256を固定する。追加先の既存ファイル・symlink・不一致・二重適用は導入前に拒否し、置換障害では導入したファイルを戻す。CIはmanifestを生成せず、レビュー済みmanifestに一致するソースだけをビルドする。

```sh
python3 patches/loopctrl/apply_patch.py /path/to/LoopCtrl
python3 patches/loopctrl/check_geometry.py /path/to/LoopCtrl /tmp/ngg1-contracts
python3 patches/loopctrl/apply_ngg2.py /path/to/LoopCtrl
python3 patches/loopctrl/check_ngg2.py /path/to/LoopCtrl /tmp/ngg2-contracts
```

取得開始/完了、入力呼出開始/完了は端末monotonic時計の境界であり、画面の厳密な生成時刻・タッチ受領時刻・ゲーム受付時刻ではない。実行済みか不明な入力は再送しない。端末キャンセルは未開始の入力を止め、開始済みsynthesizeの取消成功を意味しない。

開発時にソースを更新した場合は、固定上流にNG-G1だけを適用した別checkoutで`python3 patches/loopctrl/apply_ngg2.py --seal /path/to/ngg1-checkout`を実行し、manifest差分もレビューする。既存NG-G1のパッチ・manifestとR12は変更しない。

macOS workflowはmanifestのない先行段階ではコンパイル可能なSwift stubの挙動Redだけを実行する。現在は実機反復の手動deviceを既定、focused/fullは影響範囲や節目で明示選択する。関連NG-G2契約、unsigned IPA、LoopCtrlKit試験、構成・来歴検査を行い、IPA・SHA-256・manifest・改変取得元と追加ソース全文をpublic Actions artifactへ保存する。SideStore更新と実機確認が必要で、CI成功を実機合格にはしない。

native Cのsynthetic契約はUbuntu CIでも実行する。private実画像のCI除外名を厳密に記録し、関連する実画像再生はlocal必須として別集計する。画像不足をskipして全件成功にはしない。Raster専用のC呼出spyは別objectだけをrenameしてリンクし、本番とRuntimeは元の4 C objectsを使う。

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

専用[workflow](../../.github/workflows/loopctrl-geometry.yml)は、上記試験、unsigned IPA build、既存LoopCtrlKit tests、.xctest/CLI同梱と個人プロビジョニング情報がないことを確認する。IPAとSHA-256、上流/driver commit、patch SHA、toolchain情報をprivate Actions artifactへ保存する。署名・端末への導入・端末受入は別工程。最新ユーザーの期限切れしない配布指定により、検証済み未署名IPAと完全sourceだけを固定Release assetでも配布する。raw実機資料/秘密値は含めない。

取得元修正のCI・独立レビューは完了。Swift91契約、IPA build、既存LoopCtrlKit tests、構成検査が成功。新capabilityを確認するP1.5も用意し、次は[TEST-010](../../docs/device-tests/010-source-landscape.md)のSideStore更新と実機試験。R12は変更しない。

## ライセンス

LoopCtrlの原ソースはApache-2.0。[LICENSE](LICENSE-LoopCtrl.txt) と [NOTICE](NOTICE-LoopCtrl.md) を保持する。改変3ファイルに変更を明記する。第三者コンポーネントの通知は上流のパッケージ処理を保持する。
