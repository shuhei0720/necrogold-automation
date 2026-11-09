# 検証の入口と証明範囲

実行件数・対象commit・配布物・実機結果は [status](status.md)、条件は [制御契約](contracts/native-control.md)、受入は [要件正本](requirements/necrogold.md) を参照。本書のコマンドはsuiteの入口であり実行記録ではない。

## 検証層

| 層 | 主な入口 | 確認するもの・限界 |
| --- | --- | --- |
| C/Pythonの単体・画像再生 | `tests/test_native_perception.py`、`test_native_navigation.py`、`test_native_beat.py`、`test_native_controller.py`、`test_native_raster.py` | 実Cの状態機械、画像/算術/境界/ABI。合成texture・clock・HUDは実機再生と別集計 |
| Swift公開結合・故障検出 | `patches/loopctrl/check_ngg2.py`、`ngg2_runtime_tests.swift`、`ngg2_runtime_fakes.swift` | production Runtime/C/Rasterを接続し、guardを壊すmutationが指定assertionで落ちること。UIKit/XCTest/daemonとゲーム応答はfake |
| 暗号通信とclient回復 | `tests/test_native_*results*.py`、`test_native_connect.py`、`test_native_motion_references.py`、`test_protocol.py`、`test_http*.py` | 実暗号HTTP/認証、取消、閉schema、journal/回収。外側state/画像がfixtureならproducer接続も診断データ結合の証明に限る |
| Compiler・IPA | `patches/loopctrl/test_*.py`、`check_perception_build.py`、`check_ngg2_rpc.py`、`verify_package.py` | 実compile/profile/所有者callsite/封印/配布物の来歴。ゲームが入力を受けた証明ではない |
| 原トレースの時系列再生 | 下記の追加方針 | 実収録prefixと時刻・画像に対する退行。異なる操作への未来応答を録画から生成しない |
| Macの実ゲーム | 下記の導入条件 | 正規ゲームを実際に起動して到達/開通/商品を独立確認。未導入・未実施 |
| iPhone実機E2E | [実ゲームE2E](device-tests/game-e2e.md)、最新statusのTEST手順 | 同じLoopCtrl/ゲーム/取得/touch経路で実画面の移動・拍・商品・ポーズ・性能を確認。HTTP成功やACKだけを成功にしない |

Swiftの通常fixtureは `fastGesture` で位置、`walkedPNG` で画面を合成する。ゲーム全体の再現ではない。受入は全対象実行を分母に成否/未判定・停止理由・配置/設定を記録し、ホスト件数を実機突破率にしない。

## 必須実画像とCIの除外

現行local再生集合は177 image paths。`tests/test_native_perception.py` の `required_profile_fixtures` と各manifestで件数/path/hashを検査し、未配置・不一致は失敗する。raw画像はGit外。

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
| `tests/test055-fixtures.json` | `NECRO_TEST055_FIXTURE_ROOT` | 11 |
| `tests/test057-fixtures.json` | `NECRO_TEST057_FIXTURE_ROOT` | 18 |
| `tests/test058-fixtures.json` | `NECRO_TEST058_FIXTURE_ROOT` | 7 |

各rootへmanifest相対pathで配置する。TEST058 manifestは受領TEST057の完成7PNG。報告11枚の回収は未完了で、AI目視は暫定、商品未観測を陰性にしない。元ZIPもGit外へ置き、`NECRO_TEST055_RECORDING_ZIP=/private/test-054.zip` と `NECRO_TEST058_RECORDING_ZIP=/private/test-057.zip` をexportする。SHA256は対応test/manifestに固定。

[native workflow](../.github/workflows/loopctrl-geometry.yml) は私有資料25methodを名前の厳密照合で除外する。追加3件は受領画像のPerception/strict parity、Nav/Motion parity・実RIGHT/未送信UP部分再生、不完全ZIP評価（`active_report_mismatch`・unknown・exit2）。未収録UPの未来画像は使わない。local全件・CI除外・旧suiteの外部画像不足skipは別集計。既知調整画像/同run隣接画像は未見評価に数えない。

## TEST058の独立合成商店world

`ngg2_shop_world_tests.swift` の公開入口は `SmallShopWorld` へ実gestureの方向/時刻を渡す。自身の地形・扉・掘削・位置・商品遮蔽から896×414 RGBAを描き、report/Decision/期待操作列をworld更新のoracleにしない。独立epoch/520ms周期、150ms先行±10ms受付・同拍重複拒否は合成条件。

[16ケース](tests/test058-world-cases.md) は四方向×閉じた木/鉄扉の正常8例（方向入力4/変位3）、四方向の迂回掘削4例（7/5）、PF（遠いPARTIAL→VISIBLE）、PA（隣接PARTIAL保護停止）、CA（未送信取消）、UN（消費済みUNKNOWN・無再送）。開通/掘削だけでは変位せず、商品確認後は追加方向入力0・PAUSE1。CA/UNはPAUSE0で別検証する。production C/Runtimeの合成結合であり、実ゲームの受付・成功率・iPhone受入を証明しない。

## 代表コマンド

rootでPython/Pillow/C compilerとfixture rootsを準備する。methodは [context](context.md) から `rg -n` で絞る。

Nativeのlocal全件:

```sh
PYTHONPATH=tests python3 -m unittest test_native_perception test_native_navigation test_native_beat test_native_controller test_native_raster test_device_recording -v
```

Client・実HTTP・回復:

```sh
PYTHONPATH=tests python3 -m unittest test_protocol test_http_and_cli test_http_diagnostics test_native_walk test_native_connect test_native_results test_native_paged_results test_native_export_batch test_native_motion_references -v
```

Patch・compile/package監査:

```sh
python3 -m unittest discover -s patches/loopctrl -p 'test_*.py' -v
```

MacのSwift/Raster/実C・fault検出→実compiler/IPAの順序、upstream/flagsは [workflow](../.github/workflows/loopctrl-geometry.yml) を参照。入口は `check_ngg2.py`、LoopCtrlKit tests、`check_ngg2_rpc.py`、IPA build、`check_perception_build.py`、`verify_package.py`。client CIは [別workflow](../.github/workflows/native-client.yml)。helper単独の成功は全工程完了ではない。

## 原トレース再生方針

`tools/evaluate_device_recording.py` は単一runの元ZIPから整合性・商品可視/ポーズ・実C部分評価・欠落を別に返す。複数run/余分なファイルは評価不能。CLIはpass0/fail1/不正・unknown2。TEST054の既知未到達はexit1。評価器のGreenは実機失敗を成功へ変えない。

完全Controller再生は未実装・資料不足。原PNG/HUD、取得start/end、decode/analysis/observe時刻、prefix/inflight、ACK begin/end、実画面の移動を同runで保持し、実C Perception/Nav/Motionの評価可能な部分へ渡す。理想clock・合成HUDへ差し替えず、途中停止を含む原時系列で進捗/停止理由を検証する。

入力prefixが収録と異なれば先は評価不能。欠落画像・export省略・未知入力を明示し、未収録after frameを流用しない。原トレースは既知の退行検出であり、新操作列への応答や未知配置の合格を示さない。

## Mac実ゲームの導入条件

[自己窓CI42545599822](https://github.com/shuhei0720/necrogold-automation/actions/runs/42545599822) は外部取得PNGの赤→青とキー押下/解放を実測。正規ゲーム導入/認証/起動・adapterは未成立で、実ゲーム試験は未実施。

導入後は同じ正規日本版・固定viewport/操作設定でproduction CへGUI capture/inputを接続し、独立した移動/開通/商品oracleを用意する。配置/animation別に実入力時刻・画像・拍・全実行の成否を保存し、fakeの成功値をoracleにしない。

Mac/GUI成功をiPhone受入にしない。touch/取得/LoopCtrl経路・実性能はiPhoneで確認し、通常運用をPC必須へ変えない。
