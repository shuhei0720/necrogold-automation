# 最新状態

更新: 2026-11-11（日本時間）。TEST076の2run/37原画を受領、全商品可視0/2。ユーザー報告の3回目はログ未受領で原因未判定。[TEST077計画](plans/test077-shop-visibility.md)の局所修正・新12単体Green・独立差分レビューを完了し、限定CI33件Green、新IPAはbuild124でビルド中。[検証](reviews/test077.md)。実機未受入。

## 根拠と次の修正

実順1f2371f7→013ca451。全ZIP/PNG hash/CRC/strict schema/manifest/prefix/cursor/実publication一致、両PAUSE/完収、保持省略を補わない。1は6restart/2MOVED後、固定通路への未送信UPの静止UNKNOWN、origin/next/full5不変だがoff-route近傍FLOOR→DIRT等3cellで076待機が拒否。2は3restart/6MOVED+1DOOR後、未送信進入LEFTがstrict BLOCKEDなのに、遠方DIRT→GOLD1点増加でquiet拒否。両PARTIALのためgenericもFLOOR validation7で拒否。商品は下側に未確認。

取得failure/timeoutなし、iSH status28回エラー/取消0/max1.110秒。2のordinal4/cmd11のtoo_lateは別ID/次拍cmd12に回復して実MOVED、076late修正は実際に成立。3回目の欠落をこの2runへ混ぜず、回収済みの再実行は要求しない。

077は通路待機だけoff-route局所palette差を許し、実origin/nextと全protected/フル5/world/PW/元anchor strict0を保持。開扉ACK後と入口validのPARTIAL安定移動だけ、旧/直前accepted GOLD保持・局所/保護外UNKNOWN/DIRT→新GOLD増加を許す。追加GOLDの消失はmask0でも撤回。before/ticket/元D・閾値・不明入力無再送は維持し、商品・保護・route変化を一般許可しない。

## 配布の中断と再開

code `f1ddc78642696ddae245a636ecacd0887eb8a79f`、[CI run42983528253/build124](https://github.com/shuhei0720/necrogold-automation/actions/runs/42983528253)。host33件はfailure/error/skip0で成功。完全code source571 files/7,626,906B/SHA `b6b7de6a5e3adb12dde208554ee082c4831d9c0dac389fed481882563b914c47` は全tracked bytes/CRC照合済。MacでIPAビルド継続中に開発環境がunavailableとなり、execもNo usable execution environmentを返す。端末成功・最終IPA/固定Release検証は未実施。

環境再接続後、GitHubの新文書commitへfast-forwardし、code commitを変えずartifact3点を取得、Git外verify_test077_* 5本を各1回実行する。既存CI/native単体を再実行せず、actual compiler/22seal/9MachO139marker/571source/IPAを照合して文書3件だけclose、固定Releaseへ検証済assetを公開・匿名全GET確認し、test_077.shの具体的な実機2回を依頼する。追加の076ログを必須にしない。

## 配布と運用

現行[TEST076/build122](https://github.com/shuhei0720/necrogold-automation/releases/tag/test076-build122)、[検証](reviews/test076.md)。code8bda0a7/closingd3e9bbd、実限定CI30/実compiler/22seal/全9MachO/全565source/固定asset匿名GET照合済。077は未配布。局所単体/関連回帰・独立差分レビュー・新IPA/配布実物照合後に固定Releaseと具体的な実機手順を返す。

通常1-1ポーズからrestart→金壁/通路候補→接近/入店→全商品確認をまず2回。SideStore更新/LoopCtrl再起動/Start Server/VPN、展開sourceのtest_077.shをiSHで実行。短いrestartポーズはゲーム前面、5秒以上続いたらiSHへ戻り保存完了を待ち、自動runtime/test-077-<run_id>.zip全回分と全商品/停止位置/拍間隔を依頼する。実機到達・毎拍/人超えは未受入。

同じiPhoneのみ、ユーザーはMacを持たず実機担当。実機主軸・品質/元予算不変/時間上限なし、無関係な全Runtime/worldは追加しない。raw/秘密値はGit外、[索引](context.md)から必要資料を選ぶ。
