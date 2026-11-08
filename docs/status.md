# 最新状態

更新: 2026-11-09（日本時間）。ここが現在の事実と次工程の入口。過去の「現在」「次版」は [履歴台帳](device-tests/README.md) の各記録時点を示す。

## 現在の課題

ユーザーからTEST054「一歩横に動いてポーズで止まった」を受領。方向入力1回・MOVED1・最終ポーズ/drain確認、商品未到達。2歩目のUP予約は未送信で、画像69→70の金壁追加/扉分類による `SCREEN17 / REVALIDATE_GOLD8` 停止。元期限はobserve終了時にも94.834709ms残り、期限切れではない。

画像69→70は実C/Pillowで厳密BLOCKED、原寸の位置も変わらない。金色領域の明るさが増え、DIRT→GOLDとDIRT→DOORの2セル変化を検出した。最新のDecisionはUP/FLOORからLEFT/DIRTへ変わるため、旧UP予約を無条件に通す修正はしない。TEST054の元画像fallbackは今回の初歩には適用されていない。[受領事実](device-tests/README.md#test054受領結果2026-11-09-日本時間)。

## 配布済みの基準版

| 項目 | 同一性 |
| --- | --- |
| 完全source | `420c7ce3fb2e1fbe9f9ab7086891dd7e1118ba2e` |
| native code / CI | `5dbf7a2acb49311e71fac68994c4e1fa0c9141ac` / [Mac71](https://github.com/shuhei0720/necrogold-automation/actions/runs/42490824375) |
| IPA | build71 / SHA `c17274153a4fbd2b5d03e3b620b7f5c6530cfcc263191fc27cbf9d2bd83b300e` |
| client / API / capability | v12 / `1.98.14-ngg2` / `necrogold_native_v11` |

受領preflightは対応capとbuild時刻を確認したが、実端末のIPA hash・数値buildは含まない。暗号学的な実端末binary同一性までは主張しない。

## 今回行うこと

1. [挙動不変のコンテキスト整理](plans/context-refactor.md)。旧指示を完全保存し、現行ルール・契約・状態・試験を分ける。
2. その後、今回の実画面・停止を再現するTEST055の別計画から修正する。古い予約を再利用する許可条件の緩和で済ませない。
3. 元PNG/HUD/取得・observe・ACK時刻/prefixを変えない実トレース再生を検討する。別入力に分岐した先の未収録画像を成功として合成しない。
4. 実ゲームのMac試験を準備する。公式日本版はApple Silicon Mac対応だが、現在の環境にゲーム本体や実ゲーム用adapterはなく未実行。利用可能な正規導入環境を確認中。

## 確認した範囲と未達

整理前の既存試験: native183件/全141必須画像path・client190件・package205件が全成功/skip0。Mac71ではRuntime55故障、Raster3、C同値、暗号RPC、実compiler/IPA/seal22と実生成診断のclient保存を確認済み。[試験の区別](testing.md)。

これらは実ゲームの商品到達率ではない。全経路毎拍・人より速い性能・商品/指輪認識と通知・自動周回・耐久は未受入。TEST054の不合格を維持し、整理だけで修正版IPAとは呼ばない。検証したTEST055成果物が完成した時点で具体的な実機テストと全runtime ZIP返却を依頼する。

<a id="test-011結果と今回の変更"></a>

TEST011の記録は [整理前statusの固定版](https://github.com/shuhei0720/necrogold-automation/blob/420c7ce3fb2e1fbe9f9ab7086891dd7e1118ba2e/docs/status.md#test-011結果と今回の変更) へ保存した。
