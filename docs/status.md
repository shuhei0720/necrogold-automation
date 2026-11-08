# 最新状態

更新: 2026-11-09（日本時間）。現在はTEST055を配布し実機結果を待つ段階。履歴の「現在」「次」は各記録時点を示す。

## 今回の修正

TEST054は1方向/1MOVED後、画像69→70でgold/doorの分類が増え、最新DecisionがUP/FLOORからLEFT/DIRTへ変わった。次UP予約は未送信、元期限は残っていた。[受領事実](device-tests/README.md#test054受領結果2026-11-09-日本時間)。

TEST055は旧予約を取り消し、最新Sceneの通常plannerが選ぶ別ID/方向で同じ元拍へ予約する。既知GOLD/STONE/DOORの消失・protected変更は拒否し、全期限/共有予算/UNKNOWN無再送/商品優先を維持する。旧SAME経路と元画像fallbackの限定条件も維持する。[正本計画](plans/test055-latest-plan.md)。

## 配布版

| 項目 | 同一性 |
| --- | --- |
| native code / Mac CI | `4eb44648b673ada10a878a6e8753cb53e75e9678` / [CI42503501049](https://github.com/shuhei0720/necrogold-automation/actions/runs/42503501049) |
| IPA | [build72 ZIP](https://github.com/shuhei0720/necrogold-automation/actions/runs/42503501049/artifacts/13627766971) / SHA `c9eae0e8524ca8d8aa4d5efbb24f5db732b80d75989fb91d93b93c920da63c84` |
| client / API / capability | v13 / 1.98.14-ngg2 / necrogold_native_v12 |
| native seal | `3812b22751076748cf7ce868fc774efe6ce95c5846c84e8406900c2b21cc2be5` / 全22source一致 |

**[TEST055の実機テスト](device-tests/README.md#test-055実行手順)をお願いします。** 新IPAへSideStore更新→LoopCtrl完全終了/起動→Start Server、新sourceの `sh test_055.sh` を新1-1ポーズから実行し、終了後 `runtime/test-055` 全ZIPを返してください。旧v12互換は新v13による旧journal回復であり、旧実行ファイルの新規起動を保証しません。

## 検証した範囲

local229件（native207＋評価器22）/全152必須画像、client197、package208が成功。client公開CI197、native公開CI208/private21明示除外。実Mac57故障/Raster3/C同値-field/暗号RPC/実compiler/IPAを確認。実生成report3+2個を実暗号HTTPのclientへ接続し3診断配列と両journalを照合した。外側RPC状態/画像はfixtureであり、実ゲームE2Eではない。[検証記録](reviews/test055.md)。

TEST054の記録評価はintegrity pass・商品未到達fail/exit1。54画像とmodel履歴不足で完全Controller再生=false、LEFT後は未収録。元PNG/HUD/時刻を変えず、既知不合格を成功にしない。

## コンテキストと未受入

[挙動不変の整理](plans/context-refactor.md)を2866be6で完了。旧4文書を元bytesで保存し、通常入口を約11KBへ縮小、要件正本と全履歴は保持した。[作業索引](context.md)。

日本版はApple Silicon Mac対応だが、現在は正規ゲーム本体/GUI adapter未導入で実ゲーム試験は未実施。利用可能な環境を確認中。Macを開発検証へ使い、利用者のiPhone単体運用を変えない。

全経路毎拍・人より速い性能・商品/指輪の未知評価と通知・自動周回・耐久はiPhone実機で未受入。

<a id="test-011結果と今回の変更"></a>

TEST011の記録は [整理前statusの固定版](https://github.com/shuhei0720/necrogold-automation/blob/420c7ce3fb2e1fbe9f9ab7086891dd7e1118ba2e/docs/status.md#test-011結果と今回の変更) へ保存した。
