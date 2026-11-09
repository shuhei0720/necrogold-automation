# 最新状態

更新: 2026-11-09（日本時間）。TEST056を受領し、床の色境界を修正するTEST057を配布する段階。履歴の「現在」「次」は記録時点を示す。

## 受領結果と今回の修正

TEST056はLEFT→RIGHT→LEFTの3入力/3MOVED後late停止、商品0。同じworld目標への通路がRGB1〜2の変動でFLOOR/DIRTを跨ぎ、上予約を取り消していた。最終SAME検証終了は元deadlineの1.567ms後。最新比較103/104/105は全て保存され、TEST056の診断目的は達成。到達受入は不合格。[受領事実](device-tests/README.md#test056受領結果2026-11-09-日本時間)。

TEST057は明るい床band内のB下限だけに155の色幅を加え、他の色/texture条件、Nav/Controller/Runtime、run8/chain2/input16・入力期限・UNKNOWN無再送は維持する。既存152＋受領18の全170画像を検証し、既知の最終3枚の分類が一致する。全ての色揺れ・未知配置の往復を解消した保証ではない。[計画](plans/test057-floor-quantization.md)・[検証](reviews/test057.md)。

## 配布版

| 項目 | 同一性 |
| --- | --- |
| native code / Mac CI | `0ea4689e08069579d472ac151ad920987d24a4af` / [CI75](https://github.com/shuhei0720/necrogold-automation/actions/runs/42553613021) |
| IPA | [build75 ZIP](https://github.com/shuhei0720/necrogold-automation/actions/runs/42553613021/artifacts/13648160394) / SHA `3ade6cbf0e47e5ee2e0f9991268002912b5743268a82c0d658b17b920fe35ac2` |

native22sourceのうち変更はPerceptionだけ、他21は同一。seal `cee2d62641fdbb29fc235158568afdcafe6a5aba30e7ae0eb0f70a022583c4e5`。client v13 / API1.98.14-ngg2 / cap12、R12/G1原bytesを維持。

**[TEST057の実機テスト](device-tests/README.md#test-057実行手順)をお願いします。** 認識がnative側なのでIPA更新が必要。LoopCtrl完全終了/SideStore更新/Start Server後、新sourceの `sh test_057.sh` を新1-1ポーズから実行し、終了後 `runtime/test-057` 全ZIPを返す。歩行中はゲーム画面、自動ポーズ後はiSHへ戻って終了表示を待てる。回収済みTEST056は再実行しない。

## 検証範囲

旧C/Pythonの実画像・合成assertion Red→最小修正。local238件の初回に旧再解析期待1件が失敗し、対象moduleの期待・未観測分岐訂正後22/22成功、他216件は不変で成功。全170path/skip0、package221、client197成功。公開native CI216/private22除外、client CI197成功。Mac全59故障/Raster3/C全Scene/Decision parity-field・旧色式semantic Red/実RPC/実compilerを確認。IPA22seal/9Mach-O非混入も照合した。実producer3+2→暗号client/journal一致はfixtureの結合試験で、実ゲームE2Eではない。[検証](reviews/test057.md)。

## コンテキストと未受入

AIの初読を約177KBから約11KBへ整理し、旧4資料・要件・履歴を保持。[索引](context.md)。原ZIP/PNG/report・解析はGit外。AIによる原画像の暫定目視を人間確認済みlabelや未知評価に数えない。人間の最終受入は次のiPhoneテストで行う。

ユーザーはMacを持たずCIでの実ゲーム試験を想定。[自己窓CI](https://github.com/shuhei0720/necrogold-automation/actions/runs/42545599822)は画面取得/キー/原PNG赤→青を実測したが、正規ゲーム導入/認証/起動は未成立。実ゲーム試験は未実施、iPhone単体要件を維持する。

TEST057 iPhone受入、全経路毎拍・人より速い性能・商品/指輪の未知評価と通知・自動周回・耐久、Mac実ゲームは未受入。

<a id="test-011結果と今回の変更"></a>

TEST011の記録は [整理前statusの固定版](https://github.com/shuhei0720/necrogold-automation/blob/420c7ce3fb2e1fbe9f9ab7086891dd7e1118ba2e/docs/status.md#test-011結果と今回の変更) へ保存した。
