# CI自己窓診断: レビューと測定範囲

2026-11-09。[計画](../plans/ci-game-capability-probe.md)。phone TEST056は別branchであり、本工程は使い捨て標準Mac CI上の自己窓の画面取得/入力だけを測る。ゲーム本体/認証/実ゲームE2Eは未実施、Metalはdevice列挙に限る。

## 計画とsource確認

fresh設計・網羅・安全の計画第2周は残P0/P1/P2なし。実装第1〜3周でsender期限/keyup回復、cleanup割込み、判定のunknown分類・完了条件、300秒境界を指摘・修正した。設計/網羅第3周は指摘なしだが、安全第3周はcleanup呼出前try行への初回signalで子processが残るP1を再現し、clearとしていない。

そのP1へ最小の二段finally修正（内側finallyでcleanup phase、外側finallyで回収）を適用した。既知位置の故障と、子があるrun内12実行boundaryへの初回handler注入で、未完了/children0/cleanup passを自己確認した。旧caseを保持して102 assertions、py_compile、workflow静的検査は成功。環境失敗やこの測定を実ゲームのRed/Greenに数えない。

**独立sourceレビューは最大3周で終了し、最後の最小修正に対する第4周は未実施。** 未再確認の残余は、恒久的なCI adapterへ採用する前の次工程が担当する。今回は一回の測定に限定し、P0なし、自己窓PID宛・ゲーム/credentialなし・job8分・作業290秒/回収10秒・未完了結果はcapability passにならない境界を根拠に実行する。phone側の3観点レビューcloseと混同しない。

## 実測

Swift compile、実画面取得/入力、artifact/run/source/PNG hashesの照合は未実施。結果が揃った後に追記し、measurement完了とcapability passを分離する。
