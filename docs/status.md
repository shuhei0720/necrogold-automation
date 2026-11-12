# 最新状態

更新: 2026-11-13（日本時間）。TEST090・LoopCtrl build150（実機改善未確認）。基準169eb67。[計画](plans/test090-device-stops.md)・[検証](reviews/test090.md)・[修正記録表](fix-records.md)。修正前に過去の同じ事象/原因を照合する。実機未確認は未確認、対策記録や単体合格を改善完了と扱わない。

## 実089の受領

開始時刻順c11722aa/4bca6a1d/059f6b82/848d9572。4ZIP/80原PNGを全CRC/SHA/strict load/certificate/sidecarへ照合し、全回収完了。商品全体確認1/4。実1中央はカリスマのゆびわで、のろいの見逃し根拠なし。「判定だめそう」はiSHの「不明」表示が理由と回答あり。全商品名識別/対象なし確定を実装したとはしない。

実2は実UP1後にSTONE1個が心臓HUDへ隠れ8UNKNOWN。実3は新しい金壁/扉と遠方床の露出で同じ次LEFTを未送信拒否。実4は薄い鉄閉扉をFLOORと読み、開扉をBLOCKEDとして入口停止。商品未確認を成功にしない。

## 今回の限定対策

- 元可視STONE1個だけが投影先心臓HUDでUNKNOWNになる場合を、残るSTONE/非共線DIRT・全候補の独立画像証拠で確認する。
- 前方3セルの新gold bracketと遠方床変化だけ、同方向/同目標/FLOORを元未送信ticketの期限/予算下で既FRESHへ移す。
- 金bracket内の観測された薄鉄縦線をDOORへ回復し、既開扉処理へ渡す。開扉は0歩。
- 指輪kernelの整数累積/同じ積の再利用だけを整理。原309/235/今回204のmode0/1全raw bytes同値。unknown表示は「のろいのゆびわとの一致は未確認（対象なしとは未確定）」へ変更。

feature/閾値/word・source15検証は維持。新ELF56,088Bの数値同値/別cwd再build一致と実3.9公開backendを確認。開発単発約18%短縮を実機速度の合格にしない。

## 配布・実機確認

[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test090-build150/LoopCtrl.ipa)・[完全ZIP](https://github.com/shuhei0720/necrogold-automation/releases/download/test090-build150/source.zip)。CI24件/9scope、新IPA・22seal/実compiler/9Mach-O/全720sourceを照合。公開後に匿名全GET/actualtagも確認して返す。API16/cap15/ABI・Runtime/G1/R12・旧公開assetは維持。実機改善は未確認。

IPA更新→LoopCtrl完全終了/起動→Start Server/通常VPN。完全ZIPを展開しtest_090.shのあるフォルダをiSHへ選ぶ。

```sh
mkdir -p /mnt/necro_test090
mount -t ios . /mnt/necro_test090
cd /mnt/necro_test090 && sh test_090.sh
```

通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認を一連で4回依頼する。商品到達後はiSHへ戻り、暫定表示と全画像/ZIP完了を別に確認し、表示されたruntime/test-090-<uuid>.zip全回分を返却。実089の追加回収や同088再実行・稀な指輪を出す周回は不要。

## 未受入

今回の対策は実機改善未確認。到達率・毎拍/人超え・未知陽性精度・OS背景通知/対象なし循環は未受入。単体/校正/静的reviewを実機成功と呼ばない。自動購入0、候補保持、UNKNOWN無再送・元期限/予算・全画像保存を維持。過去の同症状も対策済みという理由で原因候補から除外しない。raw/秘密値はGit外。[索引](context.md)。
