# 検証の入口と証明範囲

件数/commit/配布/実機結果は[status](status.md)、条件は[契約](contracts/native-control.md)、受入は[要件](requirements/necrogold.md)。本書はsuiteの入口であり実行記録ではない。

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

## 必須実画像とCIの除外

現行local再生集合は203 image paths。`tests/test_native_perception.py` の `required_profile_fixtures` と各manifestで件数/path/hashを検査し、未配置・不一致は失敗する。raw画像はGit外。

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
| `tests/test059-fixtures.json` | `NECRO_TEST059_FIXTURE_ROOT` | 12 |
| `tests/test060-fixtures.json` | `NECRO_TEST060_FIXTURE_ROOT` | 14 |

各rootへ相対pathで配置する。058 manifestは受領057の完成7/報告11枚、059は受領058全12枚、060は受領059の完成14/報告16枚。AI目視は暫定、商品未観測は陰性にしない。元ZIPもGit外へ置き、`NECRO_TEST055_RECORDING_ZIP=/private/test-054.zip`、`NECRO_TEST058_RECORDING_ZIP=/private/test-057.zip`、`NECRO_TEST059_RECORDING_ZIP=/private/test-058.zip`、`NECRO_TEST060_RECORDING_ZIP=/private/test-059.zip` をexportする。SHA256は対応test/manifestに固定。

[native workflow](../.github/workflows/loopctrl-geometry.yml) は私有資料31methodを名前の厳密照合で除外する。各受領画像のPerception/Nav/Motion parityと実記録評価を分ける。057は未完了unknown/exit2、058は整合pass・商品未達fail/exit1、059は複数run/partでinvalid/unknown/exit2。未収録操作の未来画像は使わない。local全件・CI除外・旧suiteの外部画像不足skipは別集計。既知調整画像/同run隣接画像は未見評価に数えない。

## TEST058の独立合成商店world

`ngg2_shop_world_tests.swift` の公開入口は `SmallShopWorld` へ実gestureの方向/時刻を渡す。自身の地形・扉・掘削・位置・商品遮蔽から896×414 RGBAを描き、report/Decision/期待操作列をworld更新のoracleにしない。独立epoch/520ms周期、150ms先行±10ms受付・同拍重複拒否は合成条件。

[16ケース](tests/test058-world-cases.md) は四方向×閉じた木/鉄扉の正常8例（方向入力4/変位3）、四方向の迂回掘削4例（7/5）、PF（遠いPARTIAL→VISIBLE）、PA（隣接PARTIAL保護停止）、CA（未送信取消）、UN（消費済みUNKNOWN・無再送）。開通/掘削だけでは変位せず、商品確認後は追加方向入力0・PAUSE1。CA/UNはPAUSE0で別検証する。production C/Runtimeの合成結合であり、実ゲームの受付・成功率・iPhone受入を証明しない。

## TEST060の連続初回予約と長経路world

`test_native_goal_world.py` は[固定期待](tests/test060-world-cases.md)の160終端/遅延停止、Controllerは全1ms位相を別検査する。source200ms/公開100msは[新方針](plans/test060-continuous-admission.md)。独立地形/時計/受付から開扉→進入→商品/PAUSEと連続拍を検査し、実1px揺れ/実ゲームの再現とは呼ばない。

## 代表コマンド

rootでPython/Pillow/C compilerとfixture rootsを準備する。methodは [context](context.md) から `rg -n` で絞る。

Nativeのlocal全件:

```sh
PYTHONPATH=tests python3 -m unittest test_native_perception test_native_navigation test_native_beat test_native_controller test_native_raster test_device_recording test_native_goal_world -v
```

Client・実HTTP・回復:

```sh
PYTHONPATH=tests python3 -m unittest test_protocol test_http_and_cli test_http_diagnostics test_native_walk test_native_connect test_native_results test_native_paged_results test_native_export_batch test_native_motion_references -v
```

Patch・compile/package監査:

```sh
python3 -m unittest discover -s patches/loopctrl -p 'test_*.py' -v
```

Swift/fault/実compiler/IPAは[native workflow](../.github/workflows/loopctrl-geometry.yml)、暗号clientは[client workflow](../.github/workflows/native-client.yml)。helper単独の成功は全工程完了ではない。

## 原トレース再生方針

`tools/evaluate_device_recording.py` は単一runの元ZIPから整合性・商品可視/ポーズ・実C部分評価・欠落を別に返す。複数run/余分なファイルは評価不能。CLIはpass0/fail1/不正・unknown2。TEST054の既知未到達はexit1。評価器のGreenは実機失敗を成功へ変えない。

完全Controller再生は未実装。原PNG/HUD・取得/処理時刻・prefix/inflight・ACK begin/endを同runで保持し、実Cの部分評価へ渡す。理想clock/合成HUDへ置換せず、途中停止も評価する。

入力prefixが収録と異なれば先は評価不能。欠落画像・export省略・未知入力を明示し、未収録after frameを流用しない。原トレースは既知の退行検出であり、新操作列への応答や未知配置の合格を示さない。

## Mac実ゲームの導入条件

[自己窓CI42545599822](https://github.com/shuhei0720/necrogold-automation/actions/runs/42545599822) は外部取得PNGの赤→青とキー押下/解放を実測。正規ゲーム導入/認証/起動・adapterは未成立で、実ゲーム試験は未実施。

導入後は正規日本版/固定viewportでproduction CへGUI capture/inputを接続。独立の移動/商品oracleと配置別の時刻/画像/拍/全成否を保存し、fake値で成功にしない。

Mac/GUI成功をiPhone受入にしない。touch/取得/LoopCtrl経路・実性能はiPhoneで確認し、通常運用をPC必須へ変えない。
