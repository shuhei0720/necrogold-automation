# 最新状態

更新: 2026-11-28（日本時間）。TEST126起動memory修正を開発中・未配布。[計画](plans/test126-startup-memory.md)。OS Jetsamは今回のLoopCtrl PID11645にper-process-limit、2098MiBを記録し、メモリ上限終了を確定した。割当元/正確な終了時刻は未確定。

保存scanの全peer/ledger保持・反復JSON読込をcompact summary/一件処理へ変更する。元sourceの実Mac意味Red→限定Green/関連回帰→独立レビュー→新IPA/全source照合を進める。Controller/Perception/Nav/Beat・既期限/予算/owner/UNKNOWN無再送は変更しない。実機改善は未受入。

配布済みは[TEST125修正1](https://github.com/shuhei0720/necrogold-automation/releases/tag/test125-startup-fix1)（client CODEc55192e/SOURCE48cc1be、既IPA278）。待機/誤表示は修正したが実機開始不可が残った。[受領](reviews/test125-startup-refused.md)。次版はclient待機を継承する。原本/設定を削除せず保存する。
