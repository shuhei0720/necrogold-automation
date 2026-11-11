# 最新状態

更新: 2026-11-11（日本時間）。TEST076の2run/37原画を受領、全商品可視0/2。第三回はログ未受領で原因未判定。[TEST077計画](plans/test077-shop-visibility.md)の局所修正・独立レビュー・限定CI33件・新IPA build124の実物照合を完了。[検証](reviews/test077.md)。実機未受入。

## 根拠と修正

実順1f2371f7→013ca451。全ZIP/PNG hash/CRC/strict schema/manifest/prefix/cursor/実publication一致、両PAUSE/完収。1は6restart/2MOVED後、固定通路への未送信UPが静止UNKNOWN、実origin/next/full5不変でもoff-route近傍3cellの材質差で待機が拒否。2は3restart/6MOVED+1DOOR後、strict BLOCKED・同full5の未送信LEFTが遠方DIRT→GOLD一点で拒否。2の両SceneはPARTIAL、商品は下側に未確認。

077は通路待機だけ実step以外の局所palette差を許し、全protected/world/full5/元anchor strict0/PWを保持。開扉ACK後と実入口validのPARTIAL床移動だけ、元/直前accepted GOLD保持・局所/保護外UNKNOWN/DIRT→遠方GOLD追加を許す。同ID追加GOLD消失はmask0でも撤回。before/ticket/元期限・閾値・不明入力無再送・商品優先は維持。

取得failure/timeoutなし、iSH status28回エラー/取消0/max1.110秒。2の先行ordinal4/cmd11のtoo_lateは次拍別IDcmd12へ回復して実MOVED、076late修正は成立。第三回をこの2runへ混ぜず、欠落ログを必須にせず回収済みの再実行も求めない。

## 検証と配布

code `f1ddc78642696ddae245a636ecacd0887eb8a79f`、[CI build124](https://github.com/shuhei0720/necrogold-automation/actions/runs/42983528253)。新12単体は意味的Red40→Green、CI Native30+selector3はfailure/error/skip0。Controller1/他21・R12/G1/API16cap14v15/ABI/閾値/元予算不変、actual4C/5Swift/6RSP、Runtime070 Red1/現6call、全9MachO139marker不在、全571source bytes/CRCを照合。無関係な全Runtime/worldは追加しない。

[TEST077/build124](https://github.com/shuhei0720/necrogold-automation/releases/tag/test077-build124)の固定[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test077-build124/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test077-build124/source.zip)。IPA0.3.4/build124、17,608,462B/SHA `2a4ad0b9c786f01b030b5c52a74f60dfccdac85c2680debcee1c8cdb9bc7c18c`。返却前に固定assetを匿名全取得しSHA/CRCを確認する。閉じる文書3件だけで製品を維持し、再ビルドしない。

開発環境の一時切断は復旧済みでGit外記録も現存。ユーザーのiPhone/添付/CIの失敗とは別で、単体や実機の再実行は不要。

## 次の実機

SideStoreで新IPA更新→LoopCtrl完全終了/起動→Start Server、通常VPN。毎回新しい通常1-1ポーズから候補までrestart→金壁/通路候補→接近/入店→全商品確認をまず2回。展開した完全sourceのtest_077.shを含むフォルダを選択する。

```sh
mkdir -p /mnt/necro_test077
mount -t ios . /mnt/necro_test077
cd /mnt/necro_test077 && sh test_077.sh
```

短いrestartポーズはゲーム前面、5秒以上続いたらiSHへ戻り全画像/ZIP照合完了を待つ。自動runtime/test-077-<run_id>.zip全回分と全商品/停止位置/拍間隔を依頼。到達率・毎拍/人超えは次の実機で評価する。同じiPhoneのみ、ユーザーはMacを持たず実機担当。実機主軸・品質維持・時間上限なし、raw/秘密値はGit外。[索引](context.md)。
