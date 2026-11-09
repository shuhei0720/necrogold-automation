# 最新状態

更新: 2026-11-09（日本時間）。TEST055を受領し、診断版TEST056を配布して実機結果を待つ段階。履歴の「現在」「次」は各記録時点を示す。

## 受領結果と今回の修正

TEST055は5入力/5MOVED後、扉前で停止。入力間隔は約0.52秒、歩行開始→初入力2.212秒。最後は再予約run8の上限（validation5）で未送信取消→ポーズ。開通0/商品0。新FRESHと旧reference fallbackは動いたが、店到達の受入は未完了。[受領事実](device-tests/README.md#test055受領結果2026-11-09-日本時間)。

停止直前125/126/127のPNGがpin飽和・20枚選択から欠けたため、TEST056は最新2比較と最新MOVE source・初期/商品/停止画像を、pin保持とexportの両方で優先する。最大8優先・pin20/選択20/各512KiB/総4MiBを維持。歩行のrun8/chain2/input16・認識・入力/期限/UNKNOWN無再送は変更していない。扉前停止の制御修正は、回収する原画像を使って判断する。[計画](plans/test056-stop-evidence.md)。

## 配布版

| 項目 | 同一性 |
| --- | --- |
| native code / Mac CI | `8639b96b40679c7c4d8a72920d9a0cbad62a1199` / [CI42540821478](https://github.com/shuhei0720/necrogold-automation/actions/runs/42540821478) |
| IPA | [build74 ZIP](https://github.com/shuhei0720/necrogold-automation/actions/runs/42540821478/artifacts/13642073084) / 内部IPA SHA `c875a3407fb7c9b05e89d6c3180f5536d6f87a7a07c45bb56f9b950afa5fbebe` |
| client / API / capability | v13 / 1.98.14-ngg2 / necrogold_native_v12 |
| native seal | `de8650590944bcfa77064ba90b500edebfa5978b1d81033eafdddb32df81247d` / 全22source一致 |

**[TEST056の実機テスト](device-tests/README.md#test-056実行手順)をお願いします。** 新IPAへSideStore更新→LoopCtrl完全終了/起動→Start Server、新sourceの `sh test_056.sh` を新1-1ポーズから実行し、終了後 `runtime/test-056` 全ZIPを返してください。画像保存がnative側のためIPA更新が必要。TEST055は回収済みで再回収目的の再実行はしない。

## 検証範囲

local native/評価器229件・全152必須画像/skip0、package221、client公開CI197が成功。client関連50入力fileはCI版と同一。native公開CI208/private21明示除外、実Mac旧Runtime assertion Red→新保存Green・旧57＋新2故障/Raster3/C同値-field/RPC/実compiler/IPAを確認した。全9Mach-OのHOST/fixture非混入も照合。[検証記録](reviews/test056.md)。

実生成report3+2を暗号HTTPのclientへ渡し、3診断配列と両journalを照合した。外側RPC状態/画像はfixtureで実ゲームE2Eではない。実TEST055はintegrity pass・商品未到達fail/exit1、78画像不足で完全Controller再生=falseのまま。

## コンテキストと未受入

AIの初読を約177KBから約11KBへ整理し、旧4資料・要件・履歴を保持。[作業索引](context.md)。

ユーザーはMacを持たずCIでの実ゲーム試験を想定。[自己窓CI](https://github.com/shuhei0720/necrogold-automation/actions/runs/42545599822)で画面取得・キー押下/解放・原PNGの赤→青を実測した。正規ゲーム導入/認証/起動は未成立で、実ゲーム試験は未実施。App StoreもmacOS未検証を表示。Metalは列挙だけ、iPhone単体要件を維持する。

TEST056 iPhone受入、全経路毎拍・人より速い性能・商品/指輪の未知評価と通知・自動周回・耐久、Mac実ゲームは未受入。

<a id="test-011結果と今回の変更"></a>

TEST011の記録は [整理前statusの固定版](https://github.com/shuhei0720/necrogold-automation/blob/420c7ce3fb2e1fbe9f9ab7086891dd7e1118ba2e/docs/status.md#test-011結果と今回の変更) へ保存した。
