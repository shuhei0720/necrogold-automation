# 最新状態

更新: 2026-11-09（日本時間）。TEST056を受領し、床の色境界を修正するTEST057を検証中。履歴の「現在」「次」は記録時点を示す。

## 受領結果と今回の修正

TEST056はLEFT→RIGHT→LEFTの3入力/3MOVED後late停止、商品0。同じworld目標への通路がRGB1〜2の変動でFLOOR/DIRTを跨ぎ、上予約を取り消していた。最終SAME検証終了は元deadlineの1.567ms後。最新比較103/104/105は全て保存され、TEST056の診断目的は達成。到達受入は不合格。[受領事実](device-tests/README.md#test056受領結果2026-11-09-日本時間)。

TEST057は明るい床band内のB下限だけに155の色幅を加え、他の色/texture条件、Nav/Controller/Runtime、run8/chain2/input16・入力期限・UNKNOWN無再送は維持する。既存152＋受領18の全170画像を検証し、既知の最終3枚の分類が一致する。全ての色揺れ・未知配置の往復を解消した保証ではない。[計画](plans/test057-floor-quantization.md)・[検証](reviews/test057.md)。

## 開発・配布状態

TEST057の旧C/Pythonで実画像・合成のassertion Redを観測した。local238件の初回に旧再解析期待1件が失敗し、そのmoduleの期待・未観測分岐を訂正して22/22成功。他216件は不変で成功。全170path/skip0、package221、client197成功。独立3観点sourceレビューの指摘を解消し、実Mac/IPA検証へ進む。新IPA/完全sourceはまだ未配布、旧TEST056は回収済みで再実行しない。

native22sourceのうち変更はPerceptionだけ、他21は同一。seal `cee2d62641fdbb29fc235158568afdcafe6a5aba30e7ae0eb0f70a022583c4e5`。client v13 / API1.98.14-ngg2 / cap12、R12/G1原bytesを維持する。認識がnative側のため、TEST057は新IPA更新後に実機を依頼する。

## コンテキストと未受入

AIの初読を約177KBから約11KBへ整理し、旧4資料・要件・履歴を保持。[索引](context.md)。原ZIP/PNG/report・解析はGit外。AIによる原画像の暫定目視を人間確認済みlabelや未知評価に数えない。人間の最終受入は次のiPhoneテストで行う。

ユーザーはMacを持たずCIでの実ゲーム試験を想定。[自己窓CI](https://github.com/shuhei0720/necrogold-automation/actions/runs/42545599822)は画面取得/キー/原PNG赤→青を実測したが、正規ゲーム導入/認証/起動は未成立。実ゲーム試験は未実施、iPhone単体要件を維持する。

TEST057 iPhone受入、全経路毎拍・人より速い性能・商品/指輪の未知評価と通知・自動周回・耐久、Mac実ゲームは未受入。

<a id="test-011結果と今回の変更"></a>

TEST011の記録は [整理前statusの固定版](https://github.com/shuhei0720/necrogold-automation/blob/420c7ce3fb2e1fbe9f9ab7086891dd7e1118ba2e/docs/status.md#test-011結果と今回の変更) へ保存した。
