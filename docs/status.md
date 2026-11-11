# 最新状態

更新: 2026-11-11（日本時間）。TEST080/build130を実ビルド・照合済み。[計画](plans/test080-sparse-gate-closed-mouth.md)・[受領/実装/配布検証](reviews/test080.md)。TEST079実機3run/58原画は全照合、実順1f2b84fa→93a2ca80→d6cbad28、原368に3商品100/150/50が全可視、到達1/3。全PAUSE/完収、capture/dispatch failure/timeout0、host error/cancel0。

## 変更と根拠

1は実UP1歩で閉金扉前へ到達したが、狭い画面で元phase全73INF/旧独立帯不足により8UNKNOWN停止。元入力窓内、visualD残約1.602秒。3は固定通路の内側隣接へ実3歩、口がDIRT/両脇壁で床経路なしのNO_PATH。原160は省略済みで私的wait状態を補完しない。

Navは全旧判定後UNKNOWN/元phase全正INFの場合だけ、新phase（全3×3依存/UI/既知同材質・固定65独立2帯/元算術/全73）と旧3feature総強証明の別結合を追加。閉扉/金2exact/unique9/旧STONE非共線をANDしMOVED unitだけを返す。旧strong52帯100/旧全関数は不変。原22pairで旧known17/UNKNOWN4不変、328→353だけUP1MOVEDへ改善。

ControllerはACK実MOVEDで固定口内側隣接へ到達し、元2拍/horizon内の独立2観測/strict0/同壁口/両脇壁/金商品保護なし/経路なしを確認した候補だけprivateclosedへ退役。他候補/既restartへ戻し、外目標到達済み/未判定を区別。旧期限/予算/UNKNOWN無再送を維持する。

新14単体の公開Red→Green、実CI34（新14/関連17/selector3）全Green。独立1名の最終レビュー残P0/P1/P2なし。5verifier各1回でfreshG1/22seal（Nav/Controller2・他20）/actual4C・5Swift・6RSP/全9MachO147marker/全589sourceを照合。Runtimeは070 Red1/現6callのみ、全故障/world追加なし。

## 配布と次の実機

[TEST080/build130](https://github.com/shuhei0720/necrogold-automation/releases/tag/test080-build130)、code `15cdd72b0188e11970d6e547ee62b76ad5957e8e`。[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test080-build130/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test080-build130/source.zip)。IPA0.3.4/build130/min16、17,615,287B/SHA `cfdee552a92b02c8f4f992443438f651cbb6a57ac615efce5b8a1e9d71d4f885`。最終sourceは文書3件だけclosingで製品不変。固定3assetの匿名全GET/SHA/CRCを返却前に照合する。

SideStore更新・LoopCtrl完全終了/起動・Start Server/通常VPN。test_080.shで通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認をまず2回、全画像照合後runtime/test-080-<run_id>.zip全回分を依頼。079の追加回収/再実行は不要。

原353自己比較UNKNOWNは後続Scene/次入力の確定失敗を示さず、開扉/進入/全商品到達は新実機で評価する。全配置の到達率/見逃し率、恒久毎拍/人超え、対象認識/通知/対象なし自動周回は未受入。初期原画保持不足は別追跡。実機主軸/品質維持/固定時間上限なし。通常利用は同じiPhoneのみ、ユーザーはMacなし。raw/Scene/秘密値はGit外。[索引](context.md)。
