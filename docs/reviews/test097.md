# TEST097: TEST096の実機失敗を受領

2026-11-13（日本時間）。CI/配布物照合済み、実機改善未確認。[計画](../plans/test097-arrival-continuation.md)・[修正表](../fix-records.md)。CIや画像校正を商品到達成功へ数えない。

4 ZIP/85 PNG、計17,744,224B。全CRC/SHA・manifest/record chain・全画像metadata・登録集合・ZIP inventoryを照合。全complete/terminal/drained、回収不足0。添付順と実行順は異なり、以下はsession開始時刻順とユーザー指定captureを照合した順序。

| 実順 | run | 受領時の事実 | 商品判定 |
| --- | --- | --- | --- |
| 1（添付3） | bc23961d | 通路へUP3歩後、次の実UPがUNKNOWN8回。候補028/052を見送り | 未実施 |
| 2（添付4） | e50394be | 5歩/開扉成功。商品が上端で切れ、部分slot0件の結果を保持してPAUSE | 2.858ms・時間内採用、UNKNOWN/INCOMPLETE。対象なし未確定 |
| 3（添付2） | 4b8f8b38 | 7歩/開扉成功。部分結果からの観測継続で176→178を拒否、次MOVE未発行 | 13.842ms・時間内採用、UNKNOWN/INCOMPLETE |
| 4（添付1） | 6f62db92 | 5歩/開扉成功。414→416の観測継続を拒否。候補130/254を見送り | 9.333ms・時間内採用、2partial/row0・UNKNOWN/INCOMPLETE。対象なし未確定 |

前回のPAUSEによる採用遅延は、この3判定で再観測していない。全てを同じ原因とも、修正済みとも扱わない。実1は旧FR079/081/096の広い移動判定系列、実3/4は旧FR094/095の観測継続系列として再調査する。実2の空の部分slotを「対象なし」とみなして先へ進ませない。

指定4枚は全て、見送りPAUSEの実判断sourceとして保持されている。単なる描画途中画像ではない。既存094/095の厳密なUNKNOWN/壁列条件が、より見えている内側FLOORや壁列の切れ目、外側が折れる口を扱えない。各原画像のPerceptionは一度だけ実行し、元RGBA/Scene・hash・実compiler/sourceをGit外へ保存。以後は保持Sceneで候補と経路だけを検査し、再Perceptionや未知評価への再利用はしない。

## 修正と局所確認

Navは旧sourceを削除せず78行追加。上左の暗い口/左上の折れた口と、旧金1を保持する接近の移動証明だけを追加した。新候補8＋旧31の39、移動8＋旧24の32をO0/strict O2で確認。既095の転置拒否を破る不足を関連試験で検出し、対岸屋根の遠側にも正の壁支持を追加、旧assertは維持した。旧086のNav5件は現source8ファイルのsnapshotで確認し、Ring導入前の8件固定と非互換な第6Controller wrapperは未実施と明示する。

保持Sceneの最終Nav校正は各一回。候補028/052/130/254のmaskは1/32/1/1、観測床経路4/5/3/4歩。原178→196はMOVED/UP1、Scene不変・追加Perception0。店の存在、未来の商品到達や未知精度をこの校正で証明したとは扱わない。

Controllerは既071の開扉後shielded材質関係と遠方STONE→DIRTを新cycleへ限定接続。空の部分判定には、実UP開扉後・安全床・上端ITEM/保護の強い包絡による独立した1入力framingを追加した。空結果のUNKNOWN/INCOMPLETE/安全flag0は変更しない。価格adapter案は位相仮説が多くなり、既入力権限との区別が明確な観測案を選んだ。Ring/Runtime/Wire/ABI/canonicalは不変。

作成中framing待機へ新FULLが来た場合の通常job引継ぎ不足と、非FLOORも結合し得る不足を検出し、framing限定・独立した正常FULL/FLOORからの再分類へ訂正した。旧ticket/旧jobは再利用しない。新Controller16＋旧cycle29/partial5/shop071の5＝55件が成功。最初のprivate集計wrapperは53を期待して失敗したが、unittest自体はreturn0/55件成功。元ログを保存し集計だけ訂正、製品や試験を再実行していない。

独立した設計/差分確認で、修正済み指摘以外のP0/P1なし。FULL引継ぎを含む新32・関連100、選択CIはhost132/16scope＋selector5/1scope＝137/17scope。CIのController61は局所55へ旧093の6件を追加する。全world/全故障集合ではない。Macは現sourceのAPI/spool/Exportと既Runtime096の12callbackを実行し、古い094 Runtimeの順序依存fixtureは保存したまま未実行にする。ビルド/配布物照合と実機改善はこの段階では未確認。

## 最終CIと配布物

code `eb48c1479d3662bda10812af8c604f5f619228c9`、run43439504944/build173。現sourceのhost132/16scope＋selector5/1scope＝137件/17scopeが成功。Macの現API owner/schema・実FS spool・Exportと既Runtime096の12callback・旧Runtimeの指定assert Redが成功。旧094のobsolete Runtime fixtureは保存したまま未実行であり、今回実行したとは扱わない。実C producerの5入力は既policy2であり、全iPhone画像精度を示すものではない。

保持SceneのController最終校正2関係・原167のframing許可条件1件は成功。入力/追加Perception/Ring分類0、Scene/source不変。原167後の独立したFLOORは未収録なので、実歩行や未来の商品到達とは扱わない。

rootの実物5種類は計5試行/5種類で合格。36seal/2変更、実C8/Swift5/profile3のRSP/FileList・9Mach-Oと旧748＋新79の禁止827marker、canonical15source/56,088B ELF・旧Bank/Coverage・G1/R12全40・build source821ファイルの全bytes/CRCを照合した。IPA 18,015,742B、SHA `0ee31166348555b69076c4856a2f5ddaede4afb7ab5b2c0ebb0bf37a7a9249f5`。motion作者Redは原assert失敗とcompiler/source/test束を保持しているが、元shellが数値のprocess exitを保存しなかったため未保持と明示し、exit1を作らない。現CI Greenを原Redの完全なprocess receiptへ読み替えない。

closingは文書だけを変更し製品/試験/seal不変。[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test097-build173/LoopCtrl.ipa)・[全コード](https://github.com/shuhei0720/necrogold-automation/releases/download/test097-build173/source.zip)を固定Releaseへ保存し、公開後の匿名全GET/SHA/実tag/closing source全bytesを私有配布記録で照合する。次の実機は通常1-1ポーズから候補探索→入店→3商品可視→対象だけ判定→対象なしなら次周回。停止通知後、iSHの全保存/ZIP照合終了を待ち表示ZIP全体を返却してもらう。実機到達・速度・未知精度は未確認。
