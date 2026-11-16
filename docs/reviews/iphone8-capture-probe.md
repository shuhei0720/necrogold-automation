# iPhone 8 capture-only probeのレビュー・検証

2026-11-16（日本時間）。[計画](../plans/iphone8-capture-probe.md)に対応。
**未実装・未配布。iPhone 11への接続・導入なし。** 通常TEST107、既定launcher、旧G1/G2 source・seal・workflowは維持する。

## 設計レビュー

基準は文書更新済み `f64e694` と固定LoopCtrl upstream
`6e25cf6a9f65bc86c372cdce94bdb151d0cf6767`。旧nativeは前基準 `95eb3b9` と同じbytes。

| 周回 | 指摘と対応 |
| --- | --- |
| 1 | 資格判定、IDの有限保持、受付期限、旧回収の継続、送信例外と実callback終了の分離、cycle prepareの副作用を具体化 |
| 2 | 旧callback末尾・app screenshot worker・非同期VT consumerまでの共存観測が必要と判明。これらの旧実装を修正済みとは扱わない |
| 3 | 8専用capture-only buildへ縮小。fresh process・旧資料検出時busy・旧producer開始0で共存を避け、独立NG8 bridge/overlay/二重封印を採用。設計/網羅/安全の残P0/P1なし |

最終の認証P1は、remote configの純読取と端末上のrevokeを区別して解消した。
既tokenだけを継承し、このmodeのPOST /pairと承認UIは無効化する。
typedなtrusted in-process adminだけにlocal read/revoke/pauseを許可し、callerのJSONやloopback推測から昇格させない。
全5 listener生成箇所で同mode/coordinator/runtime ID/seen/元期限を保持する。

この判定は設計の成立性だけを示す。起動入口のproducer開始0、認証origin、完全drain、通常11のfalse path同値、二重封印・実compiler・8実機は、実装後の必須gateである。

## 初回TDDの対象

最初は独立NG8 bridgeのcompile可能な未実装stubと、実Objective-C境界を通すfake daemon fixtureを用意する。
標準macos-26でcompile成功後、`primary` の
`FAIL capture_one_daemon_request` / exit 1を実測してからGreenへ進む。
compile・環境失敗はRedに数えない。23ケースの準備や静的レビューを、実行成功とは記載しない。

専用workflowは承認済みbranchと専用pathだけのpushを対象にし、閉じたhost phaseを実行する。
この段階ではIPA作成・導入・公開Releaseへの到達はない。通常workflowを変更しない。

## 現在の証明範囲

旧R12は40ファイルすべてmanifestと一致し、座標/capture/raster/閾値を含む保護対象99件は前基準と同じbytesだった。
これはsource検査であり、iPhone 11の物理受入や未移送の旧資料の代用ではない。

既TEST107による8の限定操作ではAll Zones 1-1到達を確認したが、本probe・8 native入力profile・正規START-03の自動一連・商品到達の受入には含めない。
原画像・端末ID・鍵・全ログはGit外に保持する。旧資料移送は未解決。
