# 最新状態

更新: 2026-11-09（日本時間）。TEST057の右1歩停止を受領し、送信準備と商店到達結合を改善するTEST058を開発中。履歴の「現在」「次」は記録時点を示す。

## 受領結果と今回の修正

TEST057はRIGHT1/MOVED1後、次UPの送信が期限に間に合わず停止。経路外のDIRT→FLOOR変動でSAME再予約し、observe後の残余5.017msに対しAX照会11.312ms。capture失敗ではない。次UPへの床は認識できるが、入店/商品確認は未達。[受領事実](device-tests/README.md#test057受領結果2026-11-09-日本時間)。

TEST058では同logical MOVEの資格をC epochで証明し、元のfresh前面確認/leaseを共有、重い診断JSONを入力直前から外す。全期限・予算・商品保護を維持する。独立な閉扉/壁/商品のworldで、実gestureから開通→進入→商品→PAUSEまでを結合する。[計画](plans/test058-shop-dispatch.md)・[16例の期待](tests/test058-world-cases.md)・[検証](reviews/test058.md)。Controller153件Green、旧RuntimeのMac assertion Redを準備中。新IPAは未配布。

回収ZIPは完成7PNGの途中checkpointで、直接停止の画像はあるが全11枚の回収は未了。追加回収の再実行は依頼せず、次の開発へ進む。

## 直前配布（受領済み）

| 項目 | 同一性 |
| --- | --- |
| native code / Mac CI | `0ea4689e08069579d472ac151ad920987d24a4af` / [CI75](https://github.com/shuhei0720/necrogold-automation/actions/runs/42553613021) |
| IPA | [build75 ZIP](https://github.com/shuhei0720/necrogold-automation/actions/runs/42553613021/artifacts/13648160394) / SHA `3ade6cbf0e47e5ee2e0f9991268002912b5743268a82c0d658b17b920fe35ac2` |

native22sourceのうち変更はPerceptionだけ、他21は同一。seal `cee2d62641fdbb29fc235158568afdcafe6a5aba30e7ae0eb0f70a022583c4e5`。client v13 / API1.98.14-ngg2 / cap12、R12/G1原bytesを維持。

TEST057は受領済みで、旧版を再実行しない。TEST058のIPA/完全sourceを検証してから、具体的な実機依頼を行う。

## 検証範囲

旧C/Pythonの実画像・合成assertion Red→最小修正。local238件の初回に旧再解析期待1件が失敗し、対象moduleの期待・未観測分岐訂正後22/22成功、他216件は不変で成功。全170path/skip0、package221、client197成功。公開native CI216/private22除外、client CI197成功。Mac全59故障/Raster3/C全Scene/Decision parity-field・旧色式semantic Red/実RPC/実compilerを確認。IPA22seal/9Mach-O非混入も照合した。実producer3+2→暗号client/journal一致はfixtureの結合試験で、実ゲームE2Eではない。[検証](reviews/test057.md)。

## コンテキストと未受入

AIの初読を約177KBから約11KBへ整理し、旧4資料・要件・履歴を保持。[索引](context.md)。原ZIP/PNG/report・解析はGit外。AIによる原画像の暫定目視を人間確認済みlabelや未知評価に数えない。人間の最終受入は次のiPhoneテストで行う。

ユーザーはMacを持たずCIでの実ゲーム試験を想定。[自己窓CI](https://github.com/shuhei0720/necrogold-automation/actions/runs/42545599822)は画面取得/キー/原PNG赤→青を実測したが、正規ゲーム導入/認証/起動は未成立。実ゲーム試験は未実施、iPhone単体要件を維持する。

TEST057 iPhone受入、全経路毎拍・人より速い性能・商品/指輪の未知評価と通知・自動周回・耐久、Mac実ゲームは未受入。

<a id="test-011結果と今回の変更"></a>

TEST011の記録は [整理前statusの固定版](https://github.com/shuhei0720/necrogold-automation/blob/420c7ce3fb2e1fbe9f9ab7086891dd7e1118ba2e/docs/status.md#test-011結果と今回の変更) へ保存した。
