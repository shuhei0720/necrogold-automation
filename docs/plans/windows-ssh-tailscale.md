# Tailscale経由のWindows SSH設定

2026-11-16（日本時間）。[全体引き継ぎ](../handover-2026-11-16.md)と[サブiPhone接続記録](spare-iphone-remote-setup.md)に続く接続準備。製品の同じiPhoneだけで完結する要件、TEST107の実機未受入、iPhone 8未対応は維持する。

## 今回確認した事実と未確認

| 対象 | 結果 |
| --- | --- |
| Git | `origin` の `work/p1-capture-probe` を照会し、当時の最新 `4e908ed468f917d5e95204e387116e7c42b5fb76` を取得。要件・修正記録・107の未確認を引き継いだ |
| 固定Release | TEST107/build204の `LoopCtrl.ipa` / `source.zip` / `SHA256SUMS.txt` を再取得し、各GET200・全bytes/SHAが引き継ぎと一致。sourceは955files・全CRC正常。実機受入とは区別する |
| Cloud環境 | 選択環境のstatusは最新観測・running・connected。VPN failureなし。live proxy statusはTailscale `configured=true`、`state=Running`、`routing_ready=true` |
| 接続方式 | 起動時policyは `automatic_tailscale_access=true`。Cloud内にTailscaleを追加インストールせず、管理プロキシのTCP CONNECTを使う |
| Cloud側の準備 | 新しい専用Ed25519鍵をGit外に作成。チェックサム固定のsocat 1.8.0.3をGit外へ配置し、cacheからの再利用とTCP/PROXY機能を確認。外側executorから管理TCP CONNECT listenerへ到達した |
| Windows | PowerShell 5.1、OpenSSH Serverが `NotPresent` だったことを確認後、標準機能追加の成功結果（Online true / RestartNeeded false）を受領。WindowsのTailscale IPv4とLinux peer情報、追加後のsshd/設定/Firewall初期状態も確認 |
| Windows初期状態 | sshdはStopped/Manual、標準実行パス、確認済みアカウントはAdministrators所属、config未作成だった。既定SSH allowを無効化し、Windows Tailscale IP:22宛・今回のCloud IPv4だけのruleを作成。全profileでFirewall有効/既定Inbound Block。SSH親directoryはSYSTEM/Administratorsのみ書込み可で、一般認証ユーザーは読取/実行のみ |
| 新規SSH設定 | 専用鍵file・鍵認証必須/対象user限定/Windows Tailscale IPだけでlistenするconfigを作成。host key生成と実Windowsの `sshd -t` が成功。手動生成したhost private keyの所有者/個別ACEに起因するLocalSystem起動条件の不足を補正後、サービスが起動した（修正表 `FR-SSH-HOSTKEY-SYSTEM`） |
| 起動前検証 | 対象接続の `sshd -T -C` で鍵認証必須・password無効・対象user/専用鍵file/listenを確認。公開ホストfingerprintと各file ACLを受領。Firewallの潜在候補42件にはAppX限定ruleも含まれ、Tailscale-Inの包括allowも確認。既存ruleを変更せず、SSH宛TCP22だけにCloud1IP以外のIPv4補集合blockを追加し、ActiveStoreへの反映・authenticated bypass 0件を確認した |
| Tailscale実疎通 | 同名online Cloud候補が2台あり、一時TCP listenerで今回の接続元を実測。管理プロキシのCONNECT 200とWindowsからの接続元報告を受信し、Cloud→WindowsのTCP疎通と今回のCloud IPv4を確定。probeの受信許可は候補2台・専用ポートだけ、Windows側スクリプトはfinallyでlistener/ruleを片付ける構成 |
| 接続受入 | 管理CONNECT経由のTCP22が200。Windows側で受領したEd25519ホストfingerprintと実受信keyを照合し、専用known_hostsへ固定。StrictHostKeyChecking/IdentitiesOnly/pubkey onlyでSSH `whoami` が成功し、確認済みWindowsユーザーと一致。空batchのSFTPも成功し、ファイル転送はしていない |
| 最終状態 | SSH 9.5.6.4、LocalSystemでRunning、待受はWindows Tailscale IPv4だけ。一時probe rule残存0。TailscaleはRunning/Auto、sshdはAutoかつDelayedAutoStart trueへ設定し読戻し済み。PC再起動後の疎通は未試験 |
| 実機資料 | ダウンロード不能・旧環境で原本保持。Windows/新環境への移送、パック受領/hash照合は未完了のまま |

接続先IP、ノード一覧、Windowsユーザー名、公開鍵を含む実接続設定はGitへ保存しない。専用秘密鍵・known_hostsもGit外で保持する。パスワード、PIN、Tailscale Auth key、pairingは返信やログへ求めない。

## Windowsの初回確認（読み取りのみ）

Windowsの「ターミナル（管理者）」でPowerShellを開き、次を実行する。Tailscale peer一覧はLinuxだけを表示する。Cloudノードが複数ある場合は、どれが今回のノードか確定するまで接続元IPを推測しない。

```powershell
& { $ts=Join-Path $env:ProgramFiles 'Tailscale\tailscale.exe'; whoami; & $ts ip -4; $s=& $ts status --json | ConvertFrom-Json; $s.Self | Select-Object HostName,OS,Online,TailscaleIPs; $s.Peer.PSObject.Properties.Value | Where-Object OS -eq 'linux' | Select-Object HostName,Online,TailscaleIPs; Get-WindowsCapability -Online -Name 'OpenSSH.Server*' | Select-Object Name,State; Get-Service sshd -ErrorAction SilentlyContinue | Select-Object Name,Status,StartType; if(Test-Path "$env:ProgramData\ssh\sshd_config"){Get-Content "$env:ProgramData\ssh\sshd_config" | Where-Object {$_ -match '^\s*(Port|ListenAddress|PubkeyAuthentication|PasswordAuthentication|AuthenticationMethods|AuthorizedKeysFile|AllowUsers|Match)\b'}} }
```

管理者として別のアカウントを使って開いた場合、`whoami`はそのアカウントになる。ログイン対象を別途確認する。追加診断でOS、sshd実行ファイル/サービス起動引数、対象ユーザーの実グループ所属、鍵ファイルとACL、適用中Firewall policyを確認する。初回の抜粋だけで既存設定の全体を把握したと扱わない。

## 採用した設定と運用上の確認

1. **宛先と接続元。** WindowsのTailscale IPv4と、CloudプロキシのtailnetノードのIPv4を確定する。コンテナーのIPや公開egress IPを代入しない。WindowsのTailscale peer表示と管理画面等を照合し、必要ならWindows側の観測でも実接続元を確認する。
2. **既存状態の保存。** 既存sshd設定・鍵ファイル・ACL・関連FirewallルールをGit外へ保存する。既存利用があれば、ユーザーや認証を一律置換せず変更差分を決める。OpenSSH Serverが未導入ならWindows標準機能を追加する。
3. **接続範囲。** サービス開始前に、SSHの受信をWindowsのTailscale IP宛・CloudのTailscale IPv4 `/32` 発へ限定する。新しい狭いallowだけでは既存の広いallowを打ち消せない。`OpenSSH-Server-In-TCP`のほか、別名のport/program/all-portルールと有効なprofileを確認する。全22番blockとの併用はblockが優先するため使わない。ルーターの公開ポート開放は不要。
4. **公開鍵とログイン対象。** 確認した対象ユーザーに新しい専用公開鍵を登録する。標準ユーザーの既定はプロファイル内の `.ssh/authorized_keys`、Administrators所属の既定は `ProgramData/ssh/administrators_authorized_keys`。UACによる非昇格シェルの判定だけで所属を決めない。管理者用鍵ファイルは共用なので、専用鍵だけで対象アカウントを限定したとは扱わない。
5. **鍵ファイルの保存。** 既存行を維持して重複なく追記し、PowerShell 5既定のUTF-16/BOM保存を避ける。管理者用ACLはSYSTEMとAdministratorsへ限定する。`icacls`へ数値SIDを渡す表記は先頭の `*` を付けた `*S-1-5-18` / `*S-1-5-32-544`。`icacls /inheritance:r`や`/grant:r`だけでは他SIDの明示ACEが残り得るので、変更前後のACL全体を確認する。
6. **有効な認証設定。** 対象接続で `PubkeyAuthentication yes`、`PasswordAuthentication no`、`AuthenticationMethods publickey` を確認する。既存 `Match` の位置と先勝ちを考慮し、単に末尾へ追記しない。実Windowsの `sshd.exe -t` と `sshd.exe -T -C user=…,addr=…,host=…,laddr=…,lport=22` で検証してから開始/再起動する。Windows非対応のLinux向け設定を混ぜない。
7. **ホスト同一性と実接続。** Windows側の公開ホスト鍵fingerprintを別経路で確認し、Cloud側で取得したものと照合して専用known_hostsへ固定する。`StrictHostKeyChecking=yes`、`IdentitiesOnly=yes`、公開鍵認証だけで、管理プロキシを通してWindowsの `whoami` を実行する。未照合の鍵を自動承認しない。
8. **結果と戻し方。** TCP到達・ホスト鍵・認証を別々に記録する。失敗時は段階とsanitized errorを残し、接続範囲や認証を無条件に広げない。戻す場合は今回作成したrule/公開鍵行/設定差分だけを対象にし、元の設定・ACL・サービス状態を保存記録から戻す。既存ホスト鍵を削除しない。

包括allowが残る今回の構成では、block対象を「許可するCloud IPv4より小さい範囲」と「大きい範囲」に分け、Cloud自身をblock範囲へ含めない。全IPv4をblockして別allowで救済する方式は使わない。この追加blockもWindows Tailscale IP宛TCP22だけに限定する。Cloudノード交換時はallowとblock除外アドレスの両方を更新する。別ノードからの拒否は実測しておらず、今回の確認はActiveStoreとルール範囲の検査である。

初回導入の注意: `Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0` とsshdサービス開始は別操作。導入時には既定の広いFirewall allowが作成されるため、サービス開始前に上記の接続範囲を設定する。`sshd_config`とhost keyが未作成の場合は、存在しないことを確認して事前にconfigを用意し、`ssh-keygen.exe -A` で欠けたhost keyを生成してから設定を検証する。既定templateを採用する場合は同梱 `sshd_config_default` の内容とMatchも確認する。最初の `sshd.exe -t` がこれらを自動作成すると推定しない。導入完了・再起動要否・実行ファイル配置はWindowsの結果で確認する。

今回の新規設定案は、既存config/鍵がないことを確認した状態に限り、`AllowUsers`と専用の `ProgramData/ssh/necrocloud_authorized_keys` をglobal指定する。既定の管理者共用 `Match Group administrators` を入れず、既存の管理者共用鍵ファイルも変更しない。新規2fileのみ保護DACL（SYSTEM/Administrators Full）・UTF-8 BOMなしで作成し、既存directory ACLをリセットしない。生成後は `sshd -t`、別の読み取り段階で `-T -C`/公開ホストfingerprint/ACL/潜在的な別のFirewall allowを確認してから、別操作でサービスを開始する。作成途中で失敗した場合はfresh guardで再実行を止め、部分生成状態を確認する。

手動 `ssh-keygen -A` で作成したhost private keyは、管理者個人SIDがowner/ACEに残り得る。管理者ユーザーの `sshd -t` 成功を、LocalSystemサービスからのkey読取資格の証明にしない。今回使用するEd25519 private keyだけ、元SDDLを `ProgramData/ssh/necrocloud-hostkey-acl-before.txt` へ保存し、owner Administrators・SYSTEM/Administrators Fullの保護DACLに補正した。keyを再生成せず、補正後のサービス起動とOOBの公開fingerprint一致・実SSHログインを確認した。RSA/ECDSA keyや既存directory ACLには補正を広げていない。

## 次工程と検証範囲

SSH公開鍵ログインとSFTP接続までは完了。次はUSB診断、LoopCtrl導入/基本サーバー起動、その後に別計画でiPhone 8の画像・HUD・拍・商品窓・入力座標対応へ進む。これらの実行とTEST107実機受入は未完了。

sshdは遅延自動起動へ設定済みだが、PC再起動試験は行っていない。Tailscale IPv4が用意される前は固定ListenAddressで起動できない点を、再起動後の受入で確認する。別ノードからのSSH拒否も実測していない。

Windowsへの案内は、1つのコード枠に論理的な1行だけを入れて段階的に行う。複数行の逆順貼り付けが再現したため、同じ長い複数行blockを再案内しない。`>>` の未完了入力はCtrl+Cで通常promptへ戻し、出力行やpromptをコマンドへ混ぜない。

私有資料の移送は独立した未解決事項であり、接続の成功だけで完了させない。追加分割・同じダウンロード試験を繰り返さず、旧環境と原本を保持する。

今回の検証はCloud側の状態・中継ツール、Windowsでの有効設定/ACL/Firewall/service、TCP22/ホスト同一性/公開鍵SSH/空batch SFTP、固定Releaseの実bytes/hash、文書差分レビュー。native/製品コードは変更せず、IPA作成・フルCI・実ゲーム試験は対象外。TEST107の過去CIや原実機資料の校正を今回再実施したとは書かない。

参考: [Microsoft OpenSSH設定](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh-server-configuration)、[公開鍵と鍵管理](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_keymanagement)、[icacls](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/icacls)、[Firewall規則](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules)。
