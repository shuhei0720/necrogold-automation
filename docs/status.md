# 最新状態

更新: 2026-11-11（日本時間）。TEST075実機は4run/69原画で全商品可視1/4。停止改善のTEST076/build122を作成し、限定CI30・実IPA照合完了。新実機未受入。[計画](plans/test076-stationary-recovery.md)・[検証](reviews/test076.md)。

## 根拠と変更

実順1828c816→05379963→6b407804→c43fa118。全4ZIP/69PNGのhash/CRC/strict schema/manifest/prefix/cursor/実publication一致、全PAUSE/完収。2回目は原198に3商品/価格50・50・100が可視。1/4は実2歩後、同full5/金/保護/局所床の次未送信票が静止UNKNOWNでSCREEN。3は実3歩後の未送信lateがCLEAR通路回復から除外されCAPTUREへ。取得failure/timeoutなし、3には別の初歩too_late診断あり。iSH status46回はエラー/取消0、075 parserの恒久合格とは区別する。回収済み075の追加回収/再実行は不要。

Controllerのみ変更。shopの既存mask変更拒否と、通路のmask0を含む静止確認失敗で、確実未送信票を永久撤回し入力せず再観測する。元anchorとworld/candidate/full5を固定、後続の直接strict BLOCKEDまで新票を出さない。親P/短期Wを固定し、新IDにも元Pと将来prep50msを継承。UNKNOWNのまま/隣接画像だけで姿勢を更新しない。CLEAR通路の確実未送信lateも全材質/full5/保護/strict0が同じ場合だけ元bounded recoveryへ。元Dの延長/始動済・不明入力の再送/未観測商品の陰性化はしない。

Nav追加Sobel案は全73差不足で不採用、Nav/Runtime/Perception/JSON/全public header/ABI/閾値/API16cap14v15/G1/R12原40は同bytes。新8+6methodは旧版でsemantic Red33subfail/error0→Green、補足P等号/新gold futurehandoff/observe先着latest拒否も該当method Green。独立差分レビュー残P0/P1/P2なし。実原画の純幾何適合と、未保持future・live状態非再構成の範囲を分ける。

## 配布と検証

[TEST076/build122](https://github.com/shuhei0720/necrogold-automation/releases/tag/test076-build122)、code `8bda0a7a4ffca107472117311c3ca0491182a5e4`。IPA0.3.4/build122、17,607,458B/SHA `4a4bec1ceaa0f33ad25ace737b6b24eeeb5c1ce048aa324a87e94d9c04572f18`。[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test076-build122/LoopCtrl.ipa)・[全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test076-build122/source.zip)。固定assetを匿名全GETして照合後に返す。

標準public Ubuntu/Macのdevice限定CI30（新14/関連13/selector3）はfail/error/skip0、actual compiler4C/5Swift/6RSP、22seal中Controller1/他21維持、既存Runtime070 Red1/現6call、9MachO/136marker無混入を実5verifier各1回で照合。code全source565 tracked bytes/CRC一致。最終sourceは閉じる文書3件だけを変えて製品bytesを維持。全Runtime/world累積は行わない。

## 次の実機

新IPAをSideStoreで更新→LoopCtrl完全終了/起動→Start Server、通常VPN。毎回新しい通常1-1ポーズから候補までrestart→金壁/通路候補→接近/入店→全商品確認をまず2回。展開sourceのtest_076.shがあるフォルダをiSHでmountして実行。短いrestartポーズ中はゲーム前面、5秒以上ポーズが続いたらiSHへ戻り全画像/ZIP保存照合完了を待つ。自動runtime/test-076-<run_id>.zip全回分と全商品/停止位置/拍間隔を依頼。全商品到達・毎拍/人超えは未受入。

同iPhoneのみ、ユーザーはMacを持たず実機担当。実機主軸・品質/元予算不変・時間上限なし。raw/秘密値はGit外、[索引](context.md)から必要資料を選ぶ。
