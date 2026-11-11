# 最新状態

更新: 2026-11-11（日本時間）。TEST078実機3run/53原画を受領。最初の2回は全3商品を原画で確認、3回目は候補未出現のまま元restart上限12で終了。[最新受領記録](reviews/test078-received.md)。全3sessionは商品確認2/候補未出現上限1、候補発見2runで到達2/2。標本2の部分受入であり全要件合格ではない。

## 最新の根拠と保留

実順d578a956→05285d99→1c8f99e0（添付順とは異なる）。1は3restart/5MOVED7入力/1開扉、原217に3商品25/8/150。2は2restart/8MOVED9入力/1開扉、原230に3商品13/25/8。2のcmd13はprimary197→208 UNKNOWNから資格付きreference196の新unit証明でMOVEDを採用し、開扉→実進入→全商品確認へ進んだ。旧Navでは同referenceがUNKNOWNであり078修正の実効を確認。

3は12restart/方向入力0/limit。保持されたlevel4〜12のFLOOR10原画は金/対象通路候補なし、利用者観察とも整合する。非保持画像や世界全体へ店なしを一般化しない。

1回目の候補見逃し疑いは未確認。見送り3配置の判断用ゲームPNGがすべて省略され、最初のcapture1もiSH画面である。metadataの200ms/独立stable/current-prefix条件は成立するが、候補分類の正誤を原画像で確認できない。全53選択PNG/manifest/schema/実publicationの回収照合は完了、capture/dispatch failure/timeout0、host error/cancel0/status41回max1.236秒。保存されなかった過去画像は補完しない。

入力間隔は1に約1.040秒の空き1区間、他は約.500〜.525秒。4歩目の実変位確認後にVISUAL_SCHEDULE回復を記録し、後続SAME再予約は同拍を保持。未保持の途中画像から確認遅延の詳しい理由/不要待機かは判定できない。2は全8区間が約.512〜.530秒。入力間隔と実ゲーム受付・恒久毎拍/人超えは分ける。

## コード・配布

現行[TEST078/build126](https://github.com/shuhei0720/necrogold-automation/releases/tag/test078-build126)、code `954c6f39725a6b593566fa214e8cc5faa159fc6b`、配布closing `52adb7af2f1c0117e083d10d664d263c1a1b592c`。[計画](plans/test078-closed-gate-motion.md)・[実装検証](reviews/test078.md)。今回は受領解析と文書のみ、製品/試験/APIABI/閾値/予算/IPAは無変更。

[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test078-build126/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test078-build126/source.zip)。IPA0.3.4/build126、17,608,587B/SHA `8daf50aa751a8e09f8ebe079292557943fa5fc7de29f15fbe8ea391cbc6dde95`。build126の限定CI25・5実物verifier/22seal Nav1他21/actualcompiler/全9MachO/全576source/固定3asset匿名全GET照合済みは同bytesの過去結果。今回の新CI/IPA/製品試験は実施しない。

## 次の課題

見逃し疑いの検証に必要な、見送り初期原画像の優先保持/出力を既予算内で改善する設計を追跡する。今回だけで候補条件を変更せず、回収済み078の追加回収/再実行は要求しない。新TEST079は未作成。

全対応配置の安定到達/見逃し率、恒久毎拍・人超え、対象アイテム認識/通知/対象なしの自動周回は未受入。通常利用は同じiPhoneのみ、ユーザーはMacなしで実機担当。実機主軸/品質維持/時間上限なし、無関係な全Runtime/worldは追加しない。raw/Scene/秘密値はGit外。[索引](context.md)から必要範囲だけ読む。
