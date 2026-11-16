# Windows SSH設定の差分レビュー

2026-11-16（日本時間）。基準は `4e908ed468f917d5e95204e387116e7c42b5fb76`。対象は[SSH/Tailscale計画](../plans/windows-ssh-tailscale.md)、全体引き継ぎ・サブiPhone接続記録・statusからの案内。

独立担当1名が要件との整合、SSH認証・Firewall・ACL・既存設定保持とWindowsへ案内する新規設定をレビューした。P0/P1の残件なし。P2の初期3文書16KiB超過は案内の短縮で16,371Bへ修正。数値SIDの先頭 `*` も明記した。別担当が固定Release実物を再取得し、Git外のホスト鍵照合helperも確認した。helperのfork子relay回収はprocess group全体の終了へ修正し、検証状態も宛先/fingerprintに結び付けた。

確認済み:

- originの指定branch/HEAD、Cloud status/live proxyのTailscale状態、Git外の専用鍵/権限、チェックサム固定socatとcache再利用、Cloud→Windowsの一時TCP probeで接続元を確定。
- Windows標準OpenSSHの追加、実版9.5.6.4、config/専用鍵file、対象接続の `-t/-T -C`、Owner/DACL、全Firewall profile有効/既定拒否、狭いallowと他sourceのSSHだけを拒否する補集合block、ActiveStore読戻し、authenticated bypass 0件。
- 管理者手動生成host keyのowner/個別ACEとLocalSystemの不整合を補正後、サービスRunning/限定IPv4:22で待受。同じ公開host fingerprintをOOB照合し、strict検証/pubkey onlyのSSH `whoami` と確認済みユーザーが一致。空batch SFTP成功、一時probe rule残存0。
- SSH遅延自動起動の設定とAuto/DelayedAutoStart trueの読戻し。TailscaleはRunning/Auto。PCは再起動していない。
- TEST107/build204のIPA/source/SHAが各GET200・全bytes/hash一致。source955files/全CRC正常。文書の相対リンク・空白差分・初期読込量、private接続情報がGitへ入らないこと。

修正記録は `FR-SSH-PASTE-ORDER` と `FR-SSH-HOSTKEY-SYSTEM`。1論理行の案内で逆順貼付を避け、host private keyは元SDDLを保存して今回使用するEd keyのACLだけを補正した。keyを再生成せず公開fingerprint一致も確認した。LocalSystem起動前の直接fatalログは取れておらず、1067・ACL差・補正後のRunning/実SSHという証拠と、公式実装の条件照合を根拠にする。

未確認はPC再起動後の接続、別ノードからの拒否の実測、USB/LoopCtrl/iPhone 8対応、TEST107の実機受入。原実機資料は旧環境保持・未移送のまま。接続やSFTPの成功を私有資料移送やゲーム改善の証明にしない。製品/試験/nativeファイルに変更はなく、IPA再作成・フルCI・実ゲーム試験は対象外。
