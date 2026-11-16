# Windows SSH準備の差分レビュー

2026-11-16（日本時間）。基準は `4e908ed468f917d5e95204e387116e7c42b5fb76`。対象は[SSH/Tailscale計画](../plans/windows-ssh-tailscale.md)、全体引き継ぎ・サブiPhone接続記録・statusからの案内。

独立担当1名が要件との整合、確認済み/未確認の区分、SSH認証・Firewall・ACL・既存設定保持をレビューした。P0/P1なし。P2はstatus追記による初期3文書の16KiB超過1件。案内を短縮し、合計16,371Bで上限内を再確認した。参考改善として `icacls` の数値SIDに先頭 `*` が必要なことも明記した。

確認済みは、originの指定branch/HEAD、Cloud statusとlive proxyのTailscale状態、Git外の専用鍵と権限、チェックサム固定socatの機能/cache再利用、外側executorから管理TCP CONNECT listenerへの到達、文書の相対リンク・空白差分・初期読込量。製品/試験/nativeファイルに変更はない。

Windows側の初回診断はユーザーに依頼済みで未受領。設定変更、宛先TCP22到達、ホスト鍵照合、公開鍵ログインは未実施。原実機資料の移送も未完了。静的レビューとCloud側準備を、Windows接続・TEST107実機改善・iPhone 8対応の証明にしない。文書/環境準備だけなのでIPA再作成、フルCI、実ゲーム試験は実施していない。
