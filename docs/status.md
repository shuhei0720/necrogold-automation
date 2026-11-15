# 最新状態

更新: 2026-11-15（日本時間）。TEST102の修正・作者試験・独立確認完了、実機用ビルド準備中。TEST101実機2回とも商品UNKNOWNを採用して保持終了し、次周回へ未到達。全106原本/54記録/48PNGを照合した。[今回計画](plans/test102-shop-entry-cycle.md)・[受領/検証](reviews/test102.md)・[修正表](fix-records.md)。実機不合格を継続表示する。

実1は鉄扉開扉後、row-4の商品だけでは旧最上端ITEM条件を満たさず、入店の追加観測を拒否。実2は到着セルが非保護FLOORでも隣接のITEM保護範囲を重ねて拒否。さらに下壁の別DOORと片看板の上側欠損が完全判定に未対応。空拍/UNKNOWN入力の再送や不明の陰性化で解決しない。

102はController/Ringだけを変更。観測一歩の実footprint・全商品候補pixel保存・独立static/実MOVED/新job・元期限、別policy6の12固定GOLD/正のDOOR/看板共通底辺を独立再検証する。正常Ring結果からPAUSE/durable/intent/RESTART実ACK/新floorまでの限定試験は成功。新通路だけ合計2入力まで観測し、元親期限を全jobへ保持する。最終C41件とRing39件が成功し、選択CIは86件/16scope。計画/試験の記述と実機成功を区別する。

Runtime/Nav/Perception/header/旧ABI/保護資産/共有099 engineは不変。Mac191の証拠は旧C4101を使った歴史的部品試験で、現Cの実行へ流用しない。初期の16入力/12restart・45秒walk/180秒session・候補保持・UNKNOWN無再送・全画像/ZIP照合を維持する。対象はのろいのゆびわだけ。

現配布は[旧IPA192](https://github.com/shuhei0720/necrogold-automation/releases/download/test101-build192/LoopCtrl.ipa)・[旧全コード](https://github.com/shuhei0720/necrogold-automation/releases/download/test101-build192/source.zip)。これは今回の実機不合格版。前版のhost98件/19scope・Mac191・実物5gate・公開匿名全GET/hash/tag成功は[101検証](reviews/test101.md)に保存し、商品確認到達/次周回の成功とは扱わない。

次版は検証後に固定Releaseへ新IPA/完全source/SHAを保存し、通常1-1ポーズから候補探索→入店→全商品確認→対象なしなら次周回を依頼する。全保存/ZIP照合後の表示campaign ZIPを返却、全run原本を保持。毎拍/人超え速度/未知精度/耐久、旧097実1/098の未確定停止、遅延positive通知P1/native旧ledger整理P2は継続。[索引](context.md)。
