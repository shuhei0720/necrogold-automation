# 最新状態

更新: 2026-11-11（日本時間）。TEST079実機3run/58原画を全照合、原画像の商品到達1/3。[受領/修正検証](reviews/test080.md)・[TEST080計画](plans/test080-sparse-gate-closed-mouth.md)。実順1f2b84fa→93a2ca80→d6cbad28、2の原368に3商品100/150/50が全可視。全PAUSE/完収、capture/dispatch failure/timeout0、host error/cancel0。

## 原因と今回の作業

1は実UP1歩で閉金扉前へ到達したが、狭く暗い画面で元phaseが全73INF、旧強証明の独立帯も不足し8UNKNOWN停止。元入力窓内、visualD残約1.602秒。3は固定通路口の内側隣接まで実3歩、口がDIRT/両脇壁となり観測床経路なしでNO_PATH。応答160原画は省略済み、私的wait状態を補完しない。

080はNavへ元phase全正INFの場合だけの閉金扉unit別証明（全3×3依存が既知同材質の新phase/固定65独立2帯＋旧3feature総強証明）を追加する。旧raw/旧strongの条件は維持。Controllerは独立2観測で閉口を確認した候補だけをprivateclosedへ退役し、他候補/既restartへ戻す。外目標到達済み・未判定と区別し、未知入力再送/元期限・予算を広げない。

新単体14の公開assertion Red→Green、独立1名の最終差分レビューP0/P1/P2なしでGO。限定CI34（新14/関連17/selector3）・新IPA/固定asset照合を進める。全Runtime/worldは積み増さない。

## 現行配布

現在は[TEST079/build128](https://github.com/shuhei0720/necrogold-automation/releases/tag/test079-build128)、code `6b54170593bdbdf7ae42cdb4f2ee9f7a410f721a`。[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test079-build128/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test079-build128/source.zip)。実CI34/5verifier/22seal/actualcompiler/全9MachO144marker/全583source/固定asset匿名全GETは[079検証](reviews/test079.md)の過去結果で、080へ流用しない。

## 残る受入

新080を検証・公開後、通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認をまず2回、全画像照合後runtime/test-080-<run_id>.zip全回分を依頼する。079の追加回収/再実行は不要。

全配置の安定到達・見逃し率、恒久毎拍/人超え、対象認識/通知/対象なし自動周回は未受入。初期見送り原画の保持不足は別追跡。実機主軸/品質維持/固定時間上限なし。通常利用は同じiPhoneのみ、ユーザーはMacなしで実機担当。raw/Scene/秘密値はGit外。[索引](context.md)から必要範囲だけ読む。
