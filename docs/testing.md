# 検証の入口と証明範囲

最新の実行件数・対象commit・配布物・実機結果は [status](status.md)、守る条件は [制御契約](contracts/native-control.md) を正本とする。本書のコマンドは対象suiteの入口で、実行したという記録ではない。要件IDごとの受入は [要件正本](requirements/necrogold.md) に対応させる。

## 検証層

| 層 | 主な入口 | 確認するもの・限界 |
| --- | --- | --- |
| C/Pythonの単体・画像再生 | `tests/test_native_perception.py`、`test_native_navigation.py`、`test_native_beat.py`、`test_native_controller.py`、`test_native_raster.py` | 実Cの状態機械、画像/算術/境界/ABI。合成textureや模擬clock・HUDを使うケースを実機再生と混同しない |
| Swift公開結合・故障検出 | `patches/loopctrl/check_ngg2.py`、`ngg2_runtime_tests.swift`、`ngg2_runtime_fakes.swift` | production Runtime/C/Rasterを接続し、guardを壊すmutationが指定assertionで落ちること。UIKit/XCTest/daemonとゲーム応答はfake |
| 暗号通信とclient回復 | `tests/test_native_*results*.py`、`test_native_connect.py`、`test_native_motion_references.py`、`test_protocol.py`、`test_http*.py` | 実暗号HTTP/認証、取消、閉schema、journal/回収。native producer reportの接続を行う場合も、外側state/画像がfixtureなら診断データ接続の証明に限定する |
| Compiler・IPA | `patches/loopctrl/test_*.py`、`check_perception_build.py`、`check_ngg2_rpc.py`、`verify_package.py` | 実compile/profile/所有者callsite/封印/配布物の来歴。ゲームが入力を受けた証明ではない |
| 原トレースの時系列再生 | 下記の追加方針 | 実収録prefixと時刻・画像に対する退行。異なる操作への未来応答を録画から生成しない |
| Macの実ゲーム | 下記の導入条件 | 正規ゲームを実際に起動して到達/開通/商品を独立確認。未導入・未実施 |
| iPhone実機E2E | [実ゲームE2E](device-tests/game-e2e.md)、最新statusのTEST手順 | 同じLoopCtrl/ゲーム/取得/touch経路で実画面の移動・拍・商品・ポーズ・性能を確認。HTTP成功やACKだけを成功にしない |

Swiftの通常fixtureでは `fastGesture` が歩行座標を更新し、`walkedPNG` が画面を合成する。ゲームの受付・衝突・描画の全ては再現していない。ホストの試験数や故障検出数を実機突破率として数えない。受入率は対象の全実行を分母にし、成功/失敗/未判定・停止理由・配置と設定を記録する。

## 必須実画像とCIの除外

現行のlocal再生集合は141 image paths。`tests/test_native_perception.py` の `required_profile_fixtures` と各manifestが件数/path/hashの検査元で、未配置・不一致は失敗する。raw画像はGitへ追加しない。

| Manifest | 環境変数 | path数 |
| --- | --- | --- |
| `tests/test043-fixtures.json` | `NECRO_TEST043_FIXTURE_ROOT` | 66 |
| `tests/test046-fixtures.json` | `NECRO_TEST046_FIXTURE_ROOT` | 8 |
| `tests/test047-fixtures.json` | `NECRO_TEST047_FIXTURE_ROOT` | 5 |
| `tests/test049-fixtures.json` | `NECRO_TEST049_FIXTURE_ROOT` | 8 |
| `tests/test050-fixtures.json` | `NECRO_TEST050_FIXTURE_ROOT` | 11 |
| `tests/test052-fixtures.json` | `NECRO_TEST052_FIXTURE_ROOT` | 9 |
| `tests/test053-fixtures.json` | `NECRO_TEST053_FIXTURE_ROOT` | 17 |
| `tests/test054-fixtures.json` | `NECRO_TEST054_FIXTURE_ROOT` | 17 |

各rootからmanifestの相対pathへ辿れるよう配置する。[native workflow](../.github/workflows/loopctrl-geometry.yml) は私有画像を持たず、16個のlocal必須replay methodを名前で明示除外し、除外集合が変われば失敗させる。local全件、CI除外、旧suiteの外部画像不足skipを別集計する。既知調整画像や同runの隣接画像を、未見評価として数えない。

## 代表コマンド

repository rootで、必要なPython/Pillow/C compilerと上記fixture rootsを準備して実行する。対象methodを調べる時は [context索引](context.md) から `rg -n` し、対応する部分だけ読む。

Nativeのlocal全件:

```sh
PYTHONPATH=tests python3 -m unittest test_native_perception test_native_navigation test_native_beat test_native_controller test_native_raster -v
```

Client・実HTTP・回復:

```sh
PYTHONPATH=tests python3 -m unittest test_protocol test_http_and_cli test_http_diagnostics test_native_walk test_native_connect test_native_results test_native_paged_results test_native_export_batch test_native_motion_references -v
```

Patch・compile/package監査:

```sh
python3 -m unittest discover -s patches/loopctrl -p 'test_*.py' -v
```

MacでのSwift/Raster/実C・fault検出から実compiler/IPAまでの完全な順序、固定upstream、flagsは [workflow](../.github/workflows/loopctrl-geometry.yml) を読む。主な入口は `check_ngg2.py`、LoopCtrlKit tests、`check_ngg2_rpc.py`、IPA build、`check_perception_build.py`、`verify_package.py`。client CIは [別workflow](../.github/workflows/native-client.yml)。一部のhelperだけの成功を全工程完了と呼ばない。

## 原トレースを保つ追加方針

これは試験強化の計画であり、実装済みではない。原PNG/HUD、取得start/end、decode/analysis/observe時刻、prefix/inflight、ACK begin/end、実画面で確認した移動を同じrunで保持し、production Perception/Beat/Controllerへ渡す。理想clock・合成HUDへ差し替えず、途中停止を含む実際の時系列で期待進捗と安全停止理由を検証する。

controllerの入力prefixが収録と異なったら、未収録のafter frameを流用せず、その先は評価不能とする。欠落画像、export省略、未知入力を明示する。原トレースは既知の退行検出に使い、新しい操作列への実ゲーム応答や未知配置の合格を主張しない。

## Macで実ゲームを動かす追加方針

日本版は [公式App Store](https://apps.apple.com/jp/app/id1085123767) にmacOS 11以降・Apple M1以降への対応が掲載されている。Macでの実行を不可能とは断定しない。現在の作業環境はLinuxでゲーム/Xcode/Steamがなく、標準Mac CIにも正規ゲームの導入・App Store権限・実画面取得/入力adapterは用意されていない。実ゲームのインストール・起動試験は未実施。

導入後は、正規に導入した同じ日本版、固定viewport/操作設定、production C判断につながるGUI capture/input、独立した移動/開通/商品oracleを用意する。配置・animationの異なるケースで実入力時刻、画像、拍、全実行の成否を保存する。現行のfakeが返した成功値をそのoracleに使わない。

Mac実ゲーム試験が実行できても、iPhoneのtouch/取得/LoopCtrl経路と実性能はiPhoneで確認する。Macは開発検証に使い、利用者の通常運用をPC必須へ変えない。
