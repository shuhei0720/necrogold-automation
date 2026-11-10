# TEST062: 実機反復の差分・検証

2026-11-10（日本時間）。[短い計画](../plans/test062-device-cycle.md)。実機061商品0/2を受け、実機結果→局所修正→単体/関連回帰→必要なIPA→次の実機を既定とする。時間上限なし・品質/安全条件は維持。

## Red/Greenと独立差分レビュー

旧Cで初歩の無害遠方揺れを同IDで維持するassertがRed。cadence新8件は旧Cで4assert Red/errors0、compile成功。修正Cは新3+8の11methodが2.420秒で成功。実画像は061の原画/C部分解析、単体は手続きtexture/clockであり未収録未来画像の再現ではない。

独立担当1人がC差分・新単体・device CIを設計/網羅/安全から確認。P0/P1なし。P2文言（即時なのは初回適格評価、UNKNOWN後はcheckpoint待ち。初歩窓はNB−50ms〜元D）を計画へ反映。再レビューの形式的な複数周や別scopeの修理は行わない。

local device runnerは実patched upstreamの22sealを前後照合し、新11+関連旧8+Recovery期限4=23 C単体、小workflow/selector12が成功。0件/skip/error/重複/別CORE参照を閉じる。API15/cap13/client v14/公開ABIは不変、nativeはController.cだけ変更。Runtime/Beat/Nav/Perception/Raster/入力座標/全閾値・R12/G1は不変。

## 今回選ぶ範囲

新規・関連単体とactual IPA/実compiler/PBX/profile/seal/全source照合をdevice CIで実施する。未変更Runtime公開suite/全故障/shop16/Kit・全Controller184・client212は今回の前提にしない。旧Mac93/client22結果は過去結果であり、今回の再実行成功と書かない。変更したC境界は今回の23単体で確認し、実機到達はユーザーの次テストで受け入れる。配布物・CI結果は完了後に追記する。


## Mac94 device・配布物の最終確認

code `afcb339624a4007390bbb326edabd3962057e758`、[Mac94](https://github.com/shuhei0720/necrogold-automation/actions/runs/42729732582) device成功。今回のC単体23+小検査12をrawログ/全実行IDで照合し、0件/skip/errorなし。ABIと22sealの試験前後/実IPA一致を確認。Runtime061公開/全故障/shop16/Kitはdeviceで明示省略、全Controller184/client212も再実行していない。

実IPA/build94 SHA `645848e0d5d59b97e9338af586440df6f3f814008c56bb229e103bfb6e2eddd1`、外ZIP SHA `cfb84047de76feed4e3c19384d8fb6cdbe51ee9cfc5f7664f263653cb988f241`。実4C/5Swift/6RSP/PBX/profile/生compiler引数を照合、全9Mach-O/99 HOST・旧API marker非混入。22中Controller.cだけ変更、残21/R12原40/G1は不変。build-sourceは全479tracked bytes/CRC/path一致。最終source更新は文書だけと確認する。

実機商品到達・速度の受入はこれから。新TEST062を通常1-1から実行し、runtime/test-062全ZIPで確認する。回収済み061は再実行しない。
