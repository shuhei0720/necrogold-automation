# サブiPhoneによる遠隔実機試験の引き継ぎ

2026-11-16（日本時間）。接続準備の記録であり、実機試験の成功記録ではない。最初に `AGENTS.md`・`docs/status.md`・`docs/context.md` を読む。

## 目的と製品の状態

無料で、開発側から Windows＋USB接続のサブiPhoneを使って日本版ネクロダンサーを実行・診断する。通常運用を同じiPhoneだけで完結する要件は維持する。有料Mac・大型CI runnerは導入しない。

- repo: `shuhei0720/necrogold-automation`、branch: `work/p1-capture-probe`。この引き継ぎ前のHEADは `c3d2926`。
- 製品は [TEST107/build204](https://github.com/shuhei0720/necrogold-automation/releases/tag/test107-build204)、実装CODE `cfdb690`。IPAと完全sourceは同Releaseの固定asset。TEST107の実機受入結果は未受領。
- 主目標は、金壁／通路候補探索→入店→全3商品確認→のろいのゆびわの判定→対象なしなら次周回。対象候補は保持し、自動購入しない。CI合格を実機到達率・未知精度・人超え速度の達成としない。

## 確認済みの準備と停止点

| 対象 | 確認済み／未完了 |
| --- | --- |
| 端末 | メインiPhone 11、サブiPhone 8。サブの最終申告OSは16.7.7。更新を案内したが、更新後の版は未確認。iPhone 8はiOS18へ更新できない |
| アカウント | iCloudは両端末で同じ。署名専用には新しい別Apple Accountを作成済み。iCloudからのサインアウトは不要 |
| サブのアプリ | 日本版ゲーム・iSH導入済み。iloaderでSideStore導入、信頼・開発者モード・ログインまで進んだ。LoopCtrlの導入成功は未確認 |
| Windows | iTunes導入、USB接続・信頼・認識、iloader使用済み。Tailscaleのインストール・ログイン・端末登録は画面で確認。OpenSSH設定とCloudからの実接続は未実施 |
| Cloud | 現環境はVPN未設定、設定変更用ツールは提供されていない。設定のCodex Cloud一覧も「保存されている環境はありません」。新規環境はR12中心の準備まで進んだが、最新branchとTailscale接続の設定は未確認 |

SideStoreは `DeviceEndpointNotInitialized` で停止。LocalDevVPN表示はTunnel IP `10.7.1.1/32`、Device IP `10.7.0.1/32`。SideStore自動検出はN/A。Use Local VPN＝ON＋手動Device IP、OFF＋Remote Endpointへの直接指定の両方で改善しなかった。同じ設定変更を成功扱いして繰り返さない。[iOS16の継続報告](https://github.com/SideStore/SideStore/issues/1466)もあるが、今回の根本原因は未確定。

## 導入前に解く条件

1. **Tailscale登録だけでPC操作はできない。** Windows OpenSSH Server・公開鍵認証・接続元制限は未設定。既存SSH設定を確認し、Cloud側の接続元を具体化してから設定内容をレビューする。SSHで行えるのはPC側のUSB診断・ログ回収・導入処理。iPhone画面のタップ操作はLoopCtrl起動後。
2. **iloader Import IPAを確実な代替としない。** `isideload 0.5.2` はPlugIns内のbundleを拡張として列挙し、mainより長いbundle IDを要求する。TEST107の `.xctest` はmainと同じ `top.ebato.loopctrl` のため、`InvalidBundle` となる具体的条件がある。[処理](https://github.com/nab138/isideload/blob/main/isideload/src/sideload/application.rs)。未修正・実機未確認。
3. **iOS16のLoopCtrl起動も未確認。** 配布IPA本体/XCTestの最低OSは16.0、Live Activity拡張は16.2。固定上流のlegacy DDI mount・in-process XCTest bootstrapは実機未検証。[固定上流](https://github.com/Souitou-iop/LoopCtrl/blob/6e25cf6a9f65bc86c372cdce94bdb151d0cf6767/README.md#requirements)。サブ専用pairingが必要で、メインのファイルは流用しない。
4. **現行の自動歩行はiPhone 8に未対応。** Rasterの896:414固定比率に1334×750は一致しない。画像・HUD・拍・商品領域・入力座標の校正が必要。単なる画像の引き延ばしや拒否条件削除では対応しない。

## 次の手順と引き継ぎ

1. Windows版ChatGPTで `Ctrl＋,` →設定→Codex Cloud→環境→「＋環境を作成する」。対象repoを選ぶ。画面を確認しながら進め、未確認のボタン位置を推定しない。
2. 環境設定のTailscale横の鉛筆から接続資格情報を登録。Auth keyは **Reusable・Ephemeral** を有効にし、会話やGitへ貼らず設定画面へ入力。保存・公開後、新しいタスクで実接続を確認する。[公式手順](https://learn.chatgpt.com/docs/environments/cloud-environments)。既存タスクにVPNが追加されたと推定しない。
3. 新環境で状態とrepo/branchを確認し、Windows SSH接続を設定・実測する。旧環境で準備した秘密鍵はGit外にあり、会話で移送しない。Windowsへまだ鍵未登録なので、新環境で専用鍵を生成できる。
4. USBで端末情報・署名／導入エラーを調べ、LoopCtrlの基本サーバー起動を確認。その後、iPhone 8対応を別計画で実装・検証して実ゲーム試験へ進む。

新環境は旧会話の未commitファイル・私的raw解析資料を自動継承しない。旧会話とworkspaceを削除せず保持し、必要な原資料だけを非公開ファイルで移す。秘密値、pairing、個人設定、ユーザー名、メール、端末識別子、接続先IP、生画像／ZIP／ログは公開repoへ置かない。今回の記録は製品修正ではなく、新IPA・CI・形式的な再試験は実施していない。
