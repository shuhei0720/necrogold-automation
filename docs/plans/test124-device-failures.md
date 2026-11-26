# TEST124: TEST123実機5周の停止と対象見逃しを修正する

2026-11-27（日本時間）。出荷基準CODE578a9ef/IPA274/SOURCE8c85a8a、保存HEADfd5901d。TEST123の期限/所有/候補保持と既成功を維持し、[開発フロー](../development-flow.md)・[制御契約](../contracts/native-control.md)に従う。コード/文書・標準Actions・実IPA/完全sourceの固定Release配布の既承認を継続し、再承認を求めない。遠隔iPhone環境は再開しない。

## 原本と受入の基準

10ZIP/5run/5campaign・278member・120stable PNG/138記録を全照合、不足0。CRC/SHA/全decode/RGBA/metadata/記録鎖/prefix/owner/世代/clock/escrow/ledger/drainと全5campaign内包lastZIPの提出原本全bytesが一致。同Runtime・非重複の原開始順はd7a4→b48e→aa0d→ea66→6fa4であり添付順ではない。生原本/Scene/report/log/秘密値はGit外。

初回RS要求＋knownACK5/5、各rootで実unit成立5/5、開扉4/5。native FULLは1/5(root5)、人が原画像で3商品iconを見られるのは2/5(root3+5)で、両者を混ぜない。root3は対象実在1/候補検出0、root5だけ対象外の全商品可視だが商品後RS0。新floor/childへの商品後継続0。入力ACKと実unit・開扉を分けて数える。

| 原実順 | 原記録で確認した事象 | 調べる境界 |
| --- | --- | --- |
| root1 d7a4 | 開扉後、商品判定job0のままSCREEN17。未開始LEFT23のguardはBUDGET5、continuous更新8枠を消費 | 先行8更新が必要だったか、変わらない安全な判断の再検査で無駄に枠を消費していないか。枠増量で隠さない |
| root2 b48e | 上部入口。正常PARTIAL job2/source278 UNKNOWNを採用して停止 | 元PARTIALの再観測・PAUSE/入力予約・全商品可視へ進む資格を原時刻と結ぶ |
| root3 aa0d | 原source196にのろいのゆびわのsprite/名称が実在。正常job1はrow0/partial0、UNKNOWN/incompleteを元D前約88msで採用 | 商品候補の抽出段階。時刻超過やCのNEG拒否として修正せず、名称/価格を必須にしない正の画像候補探索を検討 |
| root4 ea66 | 最初のLEFTは実MOVED。次票でFRESH/SAME更新後、3度目の再検査で未送信SCREEN17 | chain2消費と次票の直接静止/地形/候補/経路・元凍結境界を分離 |
| root5 6fa4 | 正常FULL job2/source188 UNKNOWNを採用し、実RSなし | 原通常producerの不足を同画像/Scene/full packetで分離。未確認を陰性へ書き換えない |

root1/4のevent end/stop_detailはcapture_endを渡す経路があり、実Ccommitとは限らない。analysis_end下限・実出力された時刻・guard理由を分ける。未出力のjob1結果やprivate caller/counter/future画像は復元しない。

## 変更と検証の順序

1. 出荷123の全1243blob原本を私有baselineに固定し、各原画像の正常producer、Scene/Motion/Nav、実採用/拒否guardと元時刻を校正する。前版122との同入力比較で回帰/既条件外を分ける。
2. 原因の確定後に短い機能別計画を置き、同条件の意味あるassertion Red→必要最小Greenと直接関連へ進む。抽出不能な対象を未観測と同一視しない。対象/候補は未完の商店でも保持する。
3. 元P/D/W/source150/worker100/input10ms、owner/世代/prefix、取消・UNKNOWN無再送、既候補/word veto、実unit/ACK・return fence、初回RS/連続周回を維持する。未観測商品をNEGにせず、価格/名前や全商品登録・宝箱探索を周回の前提にしない。
4. 通常の独立差分レビュー1回と必要な局所delta確認。関係しない全Runtime/worldを追加せず、境界を実際に変えた場合だけその結合を選ぶ。
5. native/capが変わったら新IPAを実ビルドし、seal/全source/実compiler/配布物を照合。IPA/完全source/SHA表を固定Releaseへ保存し匿名全取得を確認する。
6. 通常1-1ポーズから初回RS→候補/通路→開扉→商品が全て見える位置→対象候補保持、または対象外の実RS→次周回を一連で実機依頼する。新実機の到達/精度/速度を補助試験の合格で先取りしない。

root1/2/3/4は意味Red→限定Green・直接関連・独立差分確認を完了。root3は原対象を候補として保持し、他24packetを全bytes保持。root2は新12/関連15Green、有限7potential/元Pと壁沿い経路を保持した。root4の新GOLD復帰P1も新14/関連16Greenで閉鎖。root5はA/B各意味Red後、新9/関連7/旧affected1GreenでC2fde2c4cを凍結し独立確認を完了。client/cap124は17意味Red→Green・実Py39直接220・独立確認を完了。機能combined残0、fresh G1から37sourceの実封印/適用・3変更34保持を照合。最終scope137/native109/CORE66/Py39108を固定、selector14旧11意味Red→新14Green、独立finalscope07ad3777残0。CODE/実CI/新IPA・実機改善は後続工程。
