# コンテキスト整理の検証・レビュー

2026-11-09（日本時間）。対象: [8項目計画](../plans/context-refactor.md)。基準commit `420c7ce3fb2e1fbe9f9ab7086891dd7e1118ba2e`。この記録の完了は挙動不変の文書整理を指し、TEST054の実機不合格解消ではない。

## 計画レビュー

freshな設計・網羅・安全の独立3担当で実施。設計第1周のP2「保存する4文書が曖昧」「本整理とTEST055納品の境界」、安全第1周の同じ納品境界を修正し、設計/安全第2周で残P0/P1/P2なし。網羅は作成中の改訂版を第1周で再確認し、17項目移送の検査と4文書の特定を確認して残件なし。第4周は行わない。

## 整理前Greenと不変性

- native183件、全141必須image paths、skip0、99.584秒。
- client190件、skip0、49.132秒。実暗号HTTPの結合/回復を含む。
- package/compiler監査205件、skip0、1.663秒。

ログ・機械比較結果はGit外へ保存。元の418tracked filesのうち、変更対象5文書を除く413ファイルは全bytes不変。要件正本・rules・R12全40・G1・実行コード・launcher・fixture・workflow・native manifest/seal・配布IPAは変えない。コードが同一であるため、文書を短くした後に同じ実行試験を形式的に繰り返さず、この対応関係を確認する。

4原文の復元元・長さ・SHAは [snapshot manifest](../archive/context-pre-refactor/manifest.json)。実機台帳510,324 bytesの原本文全体は連続したbytesのまま保持し、冒頭案内と新受領記録だけを追加した。旧status fragmentも互換anchorで保持する。

## 不変条件の移送表

旧出典は [元AGENTS/flow](../archive/context-pre-refactor/README.md) のcurrent9–18行・安定規則97–124行・各旧増分の契約、および基準codeを使用する。下表の番号は [native制御契約](../contracts/native-control.md) の同番号の節に対応し、[索引](../context.md) から対象コード・試験へ辿れる。

| No. | 元出典・確認対象 | 移送先で保持する意味・値 |
| --- | --- | --- |
| 1 | 元AGENTSのFunctional requirements、要件正本 | iPhone単体、JP/Cadence/通常1-1、直接続行、向き/設定0、開幕部分gold、全入口、毎拍/人より速い、未知と不存在、候補保持/購入禁止 |
| 2 | 元AGENTS Evidence、R12 manifest、各増分freeze | R12全40/G1/対象外native維持、完全コード、raw/秘密値はGit外、未測定/欠落を成功にしない |
| 3 | 元NG-G2/048契約、Runtime/Ticket/Bridge | stable両境界prefix・inflight0、最新authority、controlQueue/worker/heap、owner/世代/取消commit、drain、AX lock外、query-start1秒、早期AX/pipeline lease維持・最終AXなし、final1synth、未知無再送 |
| 4 | 元TEST053契約、Controller initial slot | 一度だけlead+50ms選択、NB−100..50ms公開、前倒しticketなし、同じ拍/凍結境界、invalid model poison |
| 5 | 元TEST045/051/052契約、continuous_validation | initial2、continuous chain2/run8、両者の未送信/safe floor/same gold/BLOCKED、初歩の同方向と近傍保護、continuous全protected/元保存5field/最新action、reason8 target差、元拍/期限 |
| 6 | 元NG-G2契約、C/Runtime constants | 16方向/12restart、walk45s/session180s、source/phase3s/foreground1s/入力10ms、state4s/heartbeat5s/watchdog100ms、境界は短縮だけ |
| 7 | 元TEST034/035契約、Beat/retune | live profile、7lead有限列、ACKとstrict床BLOCKED後だけ再試行、実同方向unitMOVEDで選択、未知/gate/dirt禁止 |
| 8 | 元TEST046/050契約、resolve_move/Navigation | ACK≠移動、ACKprefix、取得start>=ACK/target+80ms、3attempt/元horizon、73scoresと既存閾値/texture、開通≠進入、fresh cleanup |
| 9 | 元TEST054 current、reference_* | continuous限定immutable元Scene、全presendへの直接BLOCKED/全context、sticky失効、qualified reissue、primaryUNKNOWN-only同方向unit、別ordinal/初歩へ持越しなし、legacy permission維持 |
| 10 | 元goods契約、Controller resolve/observe | 商品latchが先、同frame適格credit、UNKNOWNでも保持、early/lateで評価捏造なし、候補と未知商品の保持 |
| 11 | 元TEST054、header/Runtime/client parser | Status192/Event128/Scene23864・MotionWait不変、別80B/16行/12閉key、未評価0/selectedauthority、priorACKprefix、最終goodsだけeventobs例外、初回accepted維持 |
| 12 | 元TEST044〜054、client保存literal | 新cap確認、v12診断必須/旧版optional厳密検証、batch4/v9batch1/legacy、元UUIDのGET0/start0、unknown start無再送、preflight有限再試行 |
| 13 | 元TEST051/052、paged collect/Runtime export | PNG20/512KiB/4MiB、64KiBchunks/wire上限、4chunk/256KiB、atomic prefix/未検証suffix保存、RPC2/8s・90s/180s、currentowner terminal/drainedのみ |
| 14 | 元TEST049/050、compiler/manifest/package | strictO2-v2の2C、Beat/ControllerO0・SwiftOnone、旧profile互換、22seal/rawPBX/argv/response/IPA同一code、全MachO hook非混入、全source ZIP bytes |
| 15 | 元Evidence/testing、private fixtures/CI | local必須不足失敗とCI16除外を分離、unknown評価はrun分離、合成/通信/再生/実ゲーム/iPhoneを別証拠とする |
| 16 | 元flow36–57、固定原文/rules | 要件と8plan、fresh3役/最大3周、実assertionRed→Green→Refactor、skip成功化禁止、人間期待値/実機確認 |
| 17 | 元AGENTS Reporting・ユーザー指示 | 日本語/JST、完全source、native変更時新IPA/完全restart/StartServer、具体的CLI/終了後全ZIP、同時実行禁止/終了した未回収だけ同run回復 |

## 読込量・参照の検査

通常の初期3文書は11,019 UTF-8 bytes（AGENTS4,127、status3,401、context3,491）。従来必読集合177,127bytesに対し93.78%減。これは初期読込bytesの比較であり、タスクで追加する要件・契約・対象コードを省く意味でも、モデルの性能値でもない。必須の意味は移送表と独立レビューで確認する。

全active文書は計画の個別budget内、内部参照は対象ファイルが全て存在しfragmentも一致。snapshotは元bytes/SHAと一致。旧台帳の全本文/anchorと `status.md#test-011結果と今回の変更` を維持した。元相対リンクはarchive indexの元位置/固定commitを基準に読む。

## 独立実装レビュー

freshな設計・網羅・安全の3担当で実施。第1周の設計P2「早期AX照会から最終callback実returnまでのpipeline token保持と最終AX IPC禁止の移送漏れ」、網羅P2「初歩とcontinuousの保護/Decision条件の一括記載」を§3/§5と移送表row3/5で修正した。第2周は3観点ともP0/P1/P2残件なし。413対象外ファイル、4snapshot、台帳全bytes/旧anchor、内部参照、契約12,132B・入口11,019Bと証明範囲を独立確認した。

このcloseを含む完全source ZIPをGitHubから取得し、全tracked files/CRC/path/byteの照合後に次のTEST055計画へ進む。新IPAは本整理では生成しない。実行コードは基準版と同一で、TEST054の実機不合格と次工程の実機受入を維持する。
