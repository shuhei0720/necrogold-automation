# TEST056 独立レビュー・検証

2026-11-09（日本時間）。正本は[8項目計画](../plans/test056-stop-evidence.md)。本工程は最新比較画像のpin/選択を優先する診断修正。TEST055のBUDGET停止や店未到達を直したと主張しない。

## 計画

freshな設計・網羅・安全の3観点で確認。安全第1周clear。設計P2「statusがTEST055結果待ちのまま」、網羅P2「encoder nilのerror/cache/token/再試行期待が未記載」を資料へ反映し、両第2周clear。残P0/P1/P2なし。pin20/選択20/各512KiB/総4MiB、入力/期限/全安全guard、既知不合格の評価を維持する。

## 実装・配布物

実装前に[Mac run42539749249](https://github.com/shuhei0720/necrogold-automation/actions/runs/42539749249) / code `ce874128a38d1656ab068e3baf2f913d283a42b3` / job128912128061で、固定旧 `2d77c02` のRuntime SHA `b83c19d30294228abb6aeae9a339917d3c9afde8f5a57d01b1575a2e3b76d261` を実compile/実行し、`FAIL stop_evidence_latest_scene_comparisons_survive_pin_saturation` / exit1 / stderr空を観測した。同一HOST seedのみを注入し、除去/var逆変換で元全bytesへ戻ることと旧pin/選択のbytes不変を検査した。fixtureは実rasterのcloneと合成診断snapshotであり、ゲーム到達の再現ではない。

Redステップ成功を確認してからpin/選択の修正へ進んだ。後で同runの生artifact ZIP 87,681bytes/SHA `70d40c2eef7e2672ae04541179b68c451a6ac5566c10deeb50e2a5fe39a16470` と両実行stdout/JSONを照合し、同じnamed assertionの失敗を確認した。test-only run全体は旧productionで新期待に失敗して終了し、IPAは生成していない。

local package/compiler/helperは221件/1.459秒成功。helperは空stdoutとEND-only markerの拒否も検査し、compile失敗をassertion Redに数えない。この確認時点では新pin/選択のMac Green・実配布物は未実施であり、後記の実物確認へ進んだ。iPhone TEST056とMac実ゲームは未実施。

local native/記録評価器229件/105.942秒、全152必須画像path、skip0で成功。seal `de8650590944bcfa77064ba90b500edebfa5978b1d81033eafdddb32df81247d` の全22sourceを実適用して照合し、Runtime以外21sourceは旧版と不変。Runtime SHA `35a23af11c4d1c4419d3f59b55a6f7498c434934e4a275584063060ee76cf667`。client v13のコードは不変で、新launcherを含む[CI42539749280](https://github.com/shuhei0720/necrogold-automation/actions/runs/42539749280)も成功した。

## 実装レビュー

fresh設計・安全の第1周はsourceに残P0/P1/P2なし。網羅第1周のP2「encoder nilが先頭失敗だけ」を、legacy/paged各々で先頭/1枚成功後の計4caseへ拡張した。試行順 `[1]` / `[1,100]` もassertし、RPC error・未完成cache非公開・token解放/正常再試行を維持。網羅第2周は残P0/P1/P2なし。既存の正しいguardを確認する追加試験であり、別の不具合Redを捏造しない。helper13件は各担当の独立実行でも成功した。

旧57故障のsource/名前を保持。新しい優先保持で累積reference欠損が隠れ得るため、既存difference-referenceの画像保持assertionに累積referenced IDs両方を追加して強化し、元assertを削らない。新pin優先無効/選択優先無効の2故障は別集合で扱いfull59を厳密照合する。Mac Green/全59・実配布物/全sourceは、上記と同じ実装レビュー周の補足工程で確認することとした。


## 実Mac・実配布物

[run42540821478](https://github.com/shuhei0720/necrogold-automation/actions/runs/42540821478) / code `8639b96b40679c7c4d8a72920d9a0cbad62a1199` / build74成功。Runtime旧57＋新pin/selection2の全59、Raster3、C全Scene/全Decision同値-field故障、LoopCtrlKit/実暗号RPC owner-callsite故障、実PBX/raw compiler/6RSP/IPAを照合。C4（Perception/Navigation strictO2、Beat/ControllerO0）・Swift5Ononeが実buildへ結合した。

IPA ZIP17,797,077bytes/SHA `9a23435129031f1af25c8e86905abbb01db78c78f38c7e09bcdba257b82bf776`、内部IPA SHA `c875a3407fb7c9b05e89d6c3180f5536d6f87a7a07c45bb56f9b950afa5fbebe`。validation449,539bytes/SHA `3713d2c8bc8b06c272605f16e0d0b0df7784de32bd2927f9fe8bd7fbfd8e0092`。全22source・seal・9Mach-OのHOST/fixture/spy非混入、arm64/API/cap12を実物で確認。native公開208件/49.791秒、private21除外集合も一致。client197件/49.93秒・関連50file同一を確認した。

旧3producer SHA `3812a98723dcbe47963ea2f9791980d5b626ec1c34001294d7feb615fd4ef884` はstdout全値/型、新2 SHA `6700c1a0d52c17ff3bfcc636e4e1bd7fcc91038cfe4491e86841fcd95d32cabf` は元JSON object bytesも一致。実暗号HTTP→v13→3診断配列/active・report両journal一致。外側RPC状態/画像はfixtureであり、診断接続の証明に限定する。

同じsource reviewの設計第1周・網羅第2周・安全第1周の実物補足は現時点P0/P1/P2なし。最終handover docsと全439file公開ZIPの補足を次に記録する。TEST056 iPhoneと実ゲームは未実施。
