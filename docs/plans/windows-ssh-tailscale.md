# Tailscale経由のWindows SSH準備

2026-11-16（日本時間）。[全体引き継ぎ](../handover-2026-11-16.md)と[サブiPhone接続記録](spare-iphone-remote-setup.md)に続く接続準備。製品の同じiPhoneだけで完結する要件、TEST107の実機未受入、iPhone 8未対応は維持する。

## 今回確認した事実と未確認

| 対象 | 結果 |
| --- | --- |
| Git | `origin` の `work/p1-capture-probe` を照会し、当時の最新 `4e908ed468f917d5e95204e387116e7c42b5fb76` を取得。要件・修正記録・107の未確認を引き継いだ |
| Cloud環境 | 選択環境のstatusは最新観測・running・connected。VPN failureなし。live proxy statusはTailscale `configured=true`、`state=Running`、`routing_ready=true` |
| 接続方式 | 起動時policyは `automatic_tailscale_access=true`。Cloud内にTailscaleを追加インストールせず、管理プロキシのTCP CONNECTを使う |
| Cloud側の準備 | 新しい専用Ed25519鍵をGit外に作成。チェックサム固定のsocat 1.8.0.3をGit外へ配置し、cacheからの再利用とTCP/PROXY機能を確認。外側executorから管理TCP CONNECT listenerへ到達した |
| Windows | Tailscale登録済み・SSH未設定というユーザー申告を継承。Windows IP、CloudノードのTailscale接続元IP、アカウント、既存OpenSSH/Firewallの診断結果は未受領。Windowsへの設定変更は行っていない |
| 接続受入 | Windows宛のTCP22到達、SSHホスト鍵照合、公開鍵ログインは未実施。VPN経路準備や中継listener到達で代用しない |
| 実機資料 | ダウンロード不能・旧環境で原本保持。Windows/新環境への移送、パック受領/hash照合は未完了のまま |

接続先IP、ノード一覧、Windowsユーザー名、公開鍵を含む実接続設定はGitへ保存しない。専用秘密鍵・known_hostsもGit外で保持する。パスワード、PIN、Tailscale Auth key、pairingは返信やログへ求めない。

## Windowsの初回確認（読み取りのみ）

Windowsの「ターミナル（管理者）」でPowerShellを開き、次を実行する。Tailscale peer一覧はLinuxだけを表示する。Cloudノードが複数ある場合は、どれが今回のノードか確定するまで接続元IPを推測しない。

```powershell
whoami
$ts = Join-Path $env:ProgramFiles 'Tailscale\tailscale.exe'
& $ts ip -4
$s = & $ts status --json | ConvertFrom-Json
$s.Self | Select-Object HostName,OS,Online,TailscaleIPs
$s.Peer.PSObject.Properties.Value | Where-Object OS -eq 'linux' | Select-Object HostName,Online,TailscaleIPs
Get-WindowsCapability -Online -Name 'OpenSSH.Server*' | Select-Object Name,State
Get-Service sshd -ErrorAction SilentlyContinue | Select-Object Name,Status,StartType
if (Test-Path "$env:ProgramData\ssh\sshd_config") {
    Get-Content "$env:ProgramData\ssh\sshd_config" | Where-Object {
        $_ -match '^\s*(Port|ListenAddress|PubkeyAuthentication|PasswordAuthentication|AuthenticationMethods|AuthorizedKeysFile|AllowUsers|Match)\b'
    }
}
```

管理者として別のアカウントを使って開いた場合、`whoami`はそのアカウントになる。ログイン対象を別途確認する。追加診断でOS、sshd実行ファイル/サービス起動引数、対象ユーザーの実グループ所属、鍵ファイルとACL、適用中Firewall policyを確認する。初回の抜粋だけで既存設定の全体を把握したと扱わない。

## 診断後に確定する設定差分

1. **宛先と接続元。** WindowsのTailscale IPv4と、CloudプロキシのtailnetノードのIPv4を確定する。コンテナーのIPや公開egress IPを代入しない。WindowsのTailscale peer表示と管理画面等を照合し、必要ならWindows側の観測でも実接続元を確認する。
2. **既存状態の保存。** 既存sshd設定・鍵ファイル・ACL・関連FirewallルールをGit外へ保存する。既存利用があれば、ユーザーや認証を一律置換せず変更差分を決める。OpenSSH Serverが未導入ならWindows標準機能を追加する。
3. **接続範囲。** サービス開始前に、SSHの受信をWindowsのTailscale IP宛・CloudのTailscale IPv4 `/32` 発へ限定する。新しい狭いallowだけでは既存の広いallowを打ち消せない。`OpenSSH-Server-In-TCP`のほか、別名のport/program/all-portルールと有効なprofileを確認する。全22番blockとの併用はblockが優先するため使わない。ルーターの公開ポート開放は不要。
4. **公開鍵とログイン対象。** 確認した対象ユーザーに新しい専用公開鍵を登録する。標準ユーザーの既定はプロファイル内の `.ssh/authorized_keys`、Administrators所属の既定は `ProgramData/ssh/administrators_authorized_keys`。UACによる非昇格シェルの判定だけで所属を決めない。管理者用鍵ファイルは共用なので、専用鍵だけで対象アカウントを限定したとは扱わない。
5. **鍵ファイルの保存。** 既存行を維持して重複なく追記し、PowerShell 5既定のUTF-16/BOM保存を避ける。管理者用ACLはSYSTEMとAdministratorsへ限定する。`icacls`へ数値SIDを渡す表記は先頭の `*` を付けた `*S-1-5-18` / `*S-1-5-32-544`。`icacls /inheritance:r`や`/grant:r`だけでは他SIDの明示ACEが残り得るので、変更前後のACL全体を確認する。
6. **有効な認証設定。** 対象接続で `PubkeyAuthentication yes`、`PasswordAuthentication no`、`AuthenticationMethods publickey` を確認する。既存 `Match` の位置と先勝ちを考慮し、単に末尾へ追記しない。実Windowsの `sshd.exe -t` と `sshd.exe -T -C user=…,addr=…,host=…,laddr=…,lport=22` で検証してから開始/再起動する。Windows非対応のLinux向け設定を混ぜない。
7. **ホスト同一性と実接続。** Windows側の公開ホスト鍵fingerprintを別経路で確認し、Cloud側で取得したものと照合して専用known_hostsへ固定する。`StrictHostKeyChecking=yes`、`IdentitiesOnly=yes`、公開鍵認証だけで、管理プロキシを通してWindowsの `whoami` を実行する。未照合の鍵を自動承認しない。
8. **結果と戻し方。** TCP到達・ホスト鍵・認証を別々に記録する。失敗時は段階とsanitized errorを残し、接続範囲や認証を無条件に広げない。戻す場合は今回作成したrule/公開鍵行/設定差分だけを対象にし、元の設定・ACL・サービス状態を保存記録から戻す。既存ホスト鍵を削除しない。

## 次工程と検証範囲

次はWindows初回診断結果から具体的な設定コマンドを作り、公開鍵ログインを実測する。現時点ではWindows設定を実行済みとしない。接続後のUSB診断、LoopCtrl導入/基本サーバー起動、iPhone 8の画像・HUD・拍・商品窓・入力座標対応は別段階。

私有資料の移送は独立した未解決事項であり、接続の成功だけで完了させない。追加分割・同じダウンロード試験を繰り返さず、旧環境と原本を保持する。

今回の検証はCloud側の状態・中継ツール・listener到達と文書差分レビューに限定する。native/製品コードは変更せず、IPA作成・フルCI・実ゲーム試験は対象外。TEST107の過去CIや実物照合を今回再実施したとは書かない。

参考: [Microsoft OpenSSH設定](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh-server-configuration)、[公開鍵と鍵管理](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_keymanagement)、[icacls](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/icacls)、[Firewall規則](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules)。
