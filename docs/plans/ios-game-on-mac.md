# 日本版iOSゲームをApple Silicon Macで試す

2026-11-16（日本時間）。ユーザーはiPhone環境をMac等で再現して実ゲームを試すよう指示し、本人のApple Accountでのログインを許可した。新規の課金環境契約はまだ承認されていない。

## 確認した条件

- 対象は日本版の `jp.co.spike-chunsoft.necrodancerjp`、App ID `1085123767`、掲載版1.05。[App Store公式](https://apps.apple.com/jp/app/id1085123767)はmacOS11以降・M1以降のMac互換を表示し、対象データの `isIOSBinaryMacOSCompatible` もtrue。「macOSでは検証されていません」とあるため、起動成功は未確認。
- iOS SimulatorへApp Storeの端末用アプリを直接導入する経路とは別に、Apple Silicon Mac上でiOSアプリを直接実行する経路を使う。Steam/Linux版への置換ではない。
- 標準GitHub Actions `macos-26` はM1のVM。[GitHub公式](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)。AppleはVM上のAccount/iCloudサインインと、利用できないApple Media Services（apps等）を区別する。[Apple公式](https://support.apple.com/en-us/120468)。既存CIへAccountを入れるだけでApp Store導入可能と扱わない。
- 現在の作業環境はLinuxで、接続可能な物理Mac/iPhoneは未提供。Accountの利用許可と、実行マシンの確保は別の条件。

## 具体的な導入先と未承認の費用

1. MacStadiumの専有物理M2 mini（8GB/256GB）。[公式価格表](https://macstadium.com/pricing)の表示は月109米ドル。M4 mini（16GB/256GB）は月149米ドル。Orka等のVMプランは選ばない。購入・契約・Appleログイン・ゲーム起動は未実施。
2. AWS EC2のApple Silicon bare-metal Mac Dedicated Host。[公式](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-mac-instances.html)では最低24時間課金。[GUI/VNC接続](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-to-mac-instance.html)が可能。地域ごとの現在単価と実利用Accountは未確定なので、金額を補完して契約しない。

## マシン確保後の順序

1. OS/Apple Silicon/非VM/GUIを確認。本人のApple Accountは安全な対話ログインで使用し、パスワードや2FAを会話・公開repo・CIログへ保存しない。
2. 日本のApp Storeから対象IDの購入済みアプリを導入。再購入が必要ならその時点で止め、購入前に確認する。ゲーム本体・receipt・Account情報を公開repoへ置かない。
3. 正規ゲームを実起動し、通常オールゾーン1-1/ケイデンス/向きと表示設定を確認。元画面・寸法・時刻を記録し、iPhoneと同一と推定しない。
4. Macのゲーム窓へ取得/入力adapterを用意してproduction C/Ring/Navigation/Beat/Controllerへ接続。viewport/倍率・座標を実測し、非一様変形や合成画像で認識を成立させない。foreground/期限/取消/UNKNOWN無再送・対象保持は維持する。
5. 実ゲームで候補探索→入店→全3商品確認→対象なし再周回を回す。実画面の移動/開扉/商品/拍を別に確認し、失敗も原画像・時刻・判断とともに保持する。自動購入は行わない。

Mac上のiOSアプリ実行も、iPhoneのAX/touch注入・アプリ切替・遅延の受入と同一ではない。既存LoopCtrl IPAがそのままMacで動くとは未確認。未導入・未起動・adapter未実装・未試験を成功とは記録しない。通常運用をiPhoneだけで完結する要件は維持する。
