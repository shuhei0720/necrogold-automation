# 最新状態

更新: 2026-11-25（日本時間）。TEST118/build263の実IPAを作成し、配布前8照合は各1回で全PASS。TEST117実機4周の停止へ、歩行前source更新、価格断片/床照明、pending FULL DATA受渡し、上部入口の内壁沿いHHDDD5歩と予約継続を実装した。[計画](plans/test118-device-failures.md)・[検証](reviews/test118.md)・[修正表](fix-records.md)。初回リスタートと`--until-target`の連続周回を維持する。

[CODEdca8ca3/Mac263](https://github.com/shuhei0720/necrogold-automation/actions/runs/45446666904)で選択host122件、実Python3.9の76件、Macの3結合ケースが合格。上部は全3商品判定→耐久保存→実RS→次child、別DATAも正常陰性→実RS→次childを確認した。これは手続き生成画像/実RuntimeによるMac検証であり、iPhone受入・到達率・毎拍/人超え速度は未確認。元4周の不合格は閉じない。

IPAは18,467,675B、SHA `5be4d1ca977cd65f33dd992152007a13747afbb9247b352ccf669f26d4668444`。固定配布先は[TEST118/build263](https://github.com/shuhei0720/necrogold-automation/releases/tag/test118-build263)（公開後の匿名全取得は最終記録で確定）。

新IPA更新→LoopCtrl完全終了/起動→Start Server。完全sourceの`test_118.sh`をiSHへmountし、通常1-1ポーズから`sh test_118.sh --until-target`。上部入口で全3商品確認、対象外の連続RSを試験し、終了後`runtime/test-118*.zip`を全て返す。
