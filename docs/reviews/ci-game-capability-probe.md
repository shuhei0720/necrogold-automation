# CI自己窓診断: レビューと測定範囲

2026-11-09。[計画](../plans/ci-game-capability-probe.md)。phone TEST056は別branchであり、本工程は使い捨て標準Mac CI上の自己窓の画面取得/入力だけを測る。ゲーム本体/認証/実ゲームE2Eは未実施、Metalはdevice列挙に限る。

## 計画とsource確認

fresh設計・網羅・安全の計画第2周は残P0/P1/P2なし。実装第1〜3周でsender期限/keyup回復、cleanup割込み、判定のunknown分類・完了条件、300秒境界を指摘・修正した。設計/網羅第3周は指摘なしだが、安全第3周はcleanup呼出前try行への初回signalで子processが残るP1を再現し、clearとしていない。

そのP1へ最小の二段finally修正（内側finallyでcleanup phase、外側finallyで回収）を適用した。既知位置の故障と、子があるrun内12実行boundaryへの初回handler注入で、未完了/children0/cleanup passを自己確認した。旧caseを保持して102 assertions、py_compile、workflow静的検査は成功。環境失敗やこの測定を実ゲームのRed/Greenに数えない。

**独立sourceレビューは最大3周で終了し、最後の最小修正に対する第4周は未実施。** 未再確認の残余は、恒久的なCI adapterへ採用する前の次工程が担当する。今回は一回の測定に限定し、P0なし、自己窓PID宛・ゲーム/credentialなし・job8分・作業290秒/回収10秒・未完了結果はcapability passにならない境界を根拠に実行する。phone側の3観点レビューcloseと混同しない。

## 実測

[実CI42545599822](https://github.com/shuhei0720/necrogold-automation/actions/runs/42545599822) / source `8950e7be48c20bb927d204b34f4a835c1bd95beb` / attempt1で測定完了。arm64/macOS26.7.2、Swift compile成功、画面/入力preflight true。自窓400×272の外部PNGが赤100%から青100%へ変化し、外部CGEvent.postToPidの押下/解放、アプリ側keyDown/keyUp各1・draw1増分を記録。clock bracket/来歴/完了/cleanup（残process0）が揃い、自己窓のcapability_pass=true。game_e2e=false、MetalはApple Paravirtual device1件列挙だけでcommand実行は未検査。

artifact ZIP17,671bytes/SHA `3e0365451171a1a8d38af099bb51aa341e824e78f56e5b73cab2649a59af1a3c`。manifestにsource3件と元PNG/summaryのhashを保存し、Git外でgit show/CRC/path/全bytesと原画素を再計算した。before PNG SHA `f4831979a62b5e6f435094741da5407501c9bbaa94912fbad4ae01804fd517b5`、after `3d9932339e09c589c3648361ba36362e1641100e13258e9ef6fbdb1bcaa19db6`。nonce/所有のraw stateは非公開で、保存済みboolの整合だけを確認する。

この測定で正規日本版ゲームの導入/認証/起動を確認したとは扱わない。独立source第4周を行っていない留保も上記のまま維持し、今回の正常完了データの結論を恒久的なadapter運用へ広げない。
