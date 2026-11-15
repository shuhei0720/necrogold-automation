# 最新状態

更新: 2026-11-15（日本時間）。TEST103の修正と独立確認完了、IPAビルド準備中。TEST102は3runを照合し、3周目1店で完全陰性→次floor成功、残3停止を確認。修正後の実機改善は未確認。[計画](plans/test103-observation-coverage.md)・[受領/検証](reviews/test103.md)・[修正表](fix-records.md)。全171原本/88record/77PNGを照合済み。

停止原因はCLEAR通路の静止資格不足、ACK待機中のicon一時遮蔽、同列入口/片看板、遮蔽後に残る下入口商品のcoverage不足。元期限・確実未送信world保持下の別plural補助、UNKNOWNで新入力せず同ACK確認待ち、別policy7/8の固定壁/実看板/完全商品帯とC独立検査を追加した。候補/未観測は保持し、対象はのろいのゆびわだけ。

C最終40件成功、Nav29件はO0/strict O2成功。Ring59fcの53成功後、numeric7半セル検査P2だけ修正して関連3件成功、独立確認GO。元商品画像494/281は通常判定で完全陰性約38ms、最終Cへも採用された。元時刻の正規化/prefix0を伴う校正で、実履歴や端末Runtimeの再現ではない。最終選択CIは128件/23scope、IPA作成/照合/固定公開はこれから。

native36の変更はController/Navigation/Core/Ringだけ。Coreはprototype追加、旧ABI構造/旧Motion/singleton/旧policy/旧assert、残32native/Perception/Runtime/canonical15/ELF/G1/R12/共有099は保持。Mac191は旧C4101の歴史的部品試験。新Runtime/Mac部品試験は追加しない。16入力/12restart・45秒walk/180秒session・UNKNOWN無再送・全画像/ZIP照合を維持。

現配布は[旧IPA194](https://github.com/shuhei0720/necrogold-automation/releases/download/test102-build194/LoopCtrl.ipa)・[旧完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test102-build194/source.zip)。今回の修正版は検証後に固定Releaseへ保存する。

次はIPA更新・LoopCtrl完全再起動・Start Server/通知/通常VPN、通常1-1ポーズから完全sourceの sh test_103.sh --until-target を実行。候補探索→入店→全商品確認→対象なしなら次周回を確認し、全画像/ZIP照合後の表示campaign ZIPを返却、全run原本を保持。毎拍/人超え速度/未知精度/耐久、旧097実1/098の未確定停止、遅延positive通知P1/native旧ledger整理P2は継続。[索引](context.md)。
