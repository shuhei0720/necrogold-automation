# TEST116: 未起動の末尾childを診断として回収する

2026-11-18（日本時間）。新しい限定差分。正常なC terminalやゲーム成功を作らず、収集した診断記録と一覧を台帳へ残す。旧 `native_cycle`・`cycle_publication`・`inspect_run` は変更しない。

## 原因とNative契約

`abortPreparedChild` は子のSpool作成後、ゲーム用coreの受理前に取消等が成立した場合を末尾の `stopped / escrow_sealed=false / escrow_sha256=null` として残す。rootは停止・全drain済み、input=4 / ui_frozen=true / native_inflight=false。通常C terminalとcontinuation_sealは作らない。

既exportは `complete=false / interrupted=true / terminal=true / workers_drained=true / input_state=4 / ui_frozen=true`。sessionが未commitなら既 `session_header_uncommitted / authority=false`、完了したsessionがある場合は診断codeが空でもよい。原本を端末に保持し、旧方式でmanifestに列挙された全画像・正式記録・診断inventory、ZIP、公開ACKを照合する。artifact557は未commit片の名前・bytes・SHAの一覧であり、opaqueな未commit本文自体は転送しない。この本文は端末に保持し、全原本転送済みとは表示・計数しない。正常runの全画像・正式記録の照合要件は維持し、今回は未commit本文用の転送APIを追加しない。物理原本もない `-32096` は未回収として残す。

現在clientはZIP公開後の `inspect_run` がterminal欠落を拒否し、最後の行を保存できない。これは診断回収の不足であり、陰性判定や入力資格の不足を緩める理由ではない。

## 限定する資格

- 保存済みroot索引の末尾childのみ。rootは停止・drain済み・入力4/凍結、子はunsealed、index>0、直前の親UUIDと一致する。
- 親は完全な通常export・公開済みで、既 `verify_child` と陰性→実RS→新floor→source/epoch/期限の全証明を満たす。親の耐久 `continuation_reservation`（閉7key、token/156MiB）とsealのnext UUIDを子/root/index/predecessorへ結び、予約sequenceが実restart_intentより前であることを要求する。
- 子のsessionがあればroot/index/predecessor/元root期限・profile・ownerを親へ結ぶ。なければ既未commit診断が必要。子にゲームterminal・seal・checkpoint・入力記録・画像/frameがあればこの限定回収へ落とさない。artifactは未起動のsession/未commit metadataだけとし、ゲーム記録やraw/pngを診断成功へ置き換えない。
- 既manifest/全file/PNG/hash/ZIP/公開receiptは通常どおり必須。正の候補、未知の入力や検査失敗の理由を陰性へしない。

## 台帳と次の操作

新しい `collection_complete` と行の `diagnostic_only / verification_error / diagnostic_collection` で「診断の列挙範囲を収集済み」と表す。診断行の `diagnostic_collection` は `scope=manifest_files_and_artifact_inventory / opaque_uncommitted_bytes=device_retained_not_transferred` を明記し、正常行ではnull。対象行は `verified=false / outcome=unknown / assessment_adopted=false`、元ZIP/hash・元検査失敗codeを保持する。`complete` はfalseのまま、保存状態はstoppedに閉じる。正常terminalの不一致や資格不成立ではこの閉鎖を許可しない。

同じ呼出しでは新startを一切行わない。`--recovery` は保存済み診断の同一性を照合して返し、再びterminal欠落の例外で止まらない。次の明示した通常の `--until-target` 呼出しだけ、直前rootの全ZIP・公開receiptを再確認し、旧rootを保持してschema/prepareから新rootを開始できる。selectorが欠落してもactive-cycleのUUIDと保存historyを一意に対応させて当該rootを復元し、曖昧なら新startしない。全過去rootの巨大ZIPを毎回再hashする方式にはしない。未回収・未照合なら新startしない。古い画像・prefix・不明入力を新rootへ引き継がない。

## TDD・差分確認

実Nativeと同じsessionあり/なし・artifact診断・親reservation/sealを作る手続き的transportで、旧版の「末尾rowが保存されない／terminal欠落で回収が閉じない」意味Redを確認する。限定診断Green後は、同じrootの再回復・全ZIP不変・新start0、次の明示呼出しのみ新start、親/子identityやreservation不一致・ゲームterminalあり・未公開file・物理回収失敗の拒否を確認する。旧正常q1未使用last・全零拒否・候補保持・未知startのassertを維持する。実Python3.9とこの差分だけの独立確認を行い、実iPhone改善とは区別する。
