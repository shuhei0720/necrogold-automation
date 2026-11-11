# TEST078受領: 商品可視2回と候補未出現の上限終了

2026-11-11（日本時間）。対象code `954c6f39725a6b593566fa214e8cc5faa159fc6b`、配布closing `52adb7af2f1c0117e083d10d664d263c1a1b592c`、build126。受領解析/記録だけで製品・試験を変更しない。[実装/配布検証](test078.md)。raw/Scene/監査はGit外received078/test079-*、公開しない。

## 受領と結果

実行順はstarted_nsで確定し、添付順ではない。3ZIP/53原PNG（15/18/20）を全SHA/ZIP・PNG chunk CRC/PIL verify-load/896×414/manifest全offset・hash・cursor/prefix/厳密schema/_load/実test069 publicationへ照合。全選択画像のnative capture行一致、欠損0。全PAUSE/resolved/terminal/drained、capture・dispatch failure/timeout0、全host RPCエラー・取消0/status41回最大1.236秒。

| 実順/run | ZIP bytes / SHA256 | restart | MOVED/方向入力 | 開扉 | 終了 |
| --- | --- | --- | --- | --- | --- |
| 1/d578a956 | 4,369,619 / `cd2a42c116010f9ee5e7fd3c1c3967b6d48488653aaffc25cef94332d2c247be` | 3 | 5/7 | 1 | goods |
| 2/05285d99 | 4,404,622 / `668ce8a8591f68c4ec5808ac845ca2f5b1245cd745b1eec43a2c8da54b0a9001` | 2 | 8/9 | 1 | goods |
| 3/1c8f99e0 | 3,563,978 / `179b24cc519721501b6bff027f3171c5e42628e114bb3b7555f753ca11e2cacb` | 12 | 0/0 | 0 | limit |

各retained20、export15/18/20・画像計4,129,813/4,166,470/3,261,804Bで全4MiB以内。選択・出力済み画像は全て回収/照合完了。非保持/出力対象外画像を後続画像で補わず、選択済み画像の回収完了と全撮影画像の永続保存を混同しない。

rootが1の原217/2の原230を視認。1は3商品と価格25/8/150、2も3商品と価格13/25/8がすべて画面内にある。全3sessionでは商品確認2・候補未出現の上限1、候補発見2runでは商品到達2/2。標本2から全配置や恒久的到達率を認定しない。対象アイテムの有無は今回認定しない。

3は有限試験の元restart上限12で終了。方向入力/移動0、利用者も対象未出現と報告。保持されたlevel4〜12のFLOOR10原画はGOLD_CLEAR/通路candidate mask0で、root視認も対象なしと整合する。非保持level0〜3まで全画像で見逃しなしと主張せず、世界全体の店なしにも一般化しない。

## 新証明が実際に効いた箇所

2のcmd13/UPはprimary197→208がUNKNOWNだが、reportのreference196がeligible=true、fallback_attempted=true、fallback_motion=MOVED、selected_capture_id196/selected_motion1で実際に選択されている。原196→208を旧Nav `5b3fb3e8bfcc3586d65ce5576a12f9c4fc35a685891f8b8398a12c054ffcfd91` と新Nav `0da8483d7663ee4ae144ad6da35602e06b82b15ab49ca3eea5d16c2d791bec61` で照合するとUNKNOWN→UP1MOVEDへ変わる。

その後cmd14はDOOR_OPENED、cmd15は実MOVED/原230で商品可視、cmd16でPAUSE。078の新証明と既元画像fallbackが端末で移動を救い、開通/進入へ接続した証拠である。保持されたprimary24比較は旧新すべて不変、実際に選ばれたreferenceの1比較を別に追って効果を確認した。未保持futureを作ったり、異なる操作の結果を原記録から生成したりしない。

## 1回目の候補見逃し疑いは未確認

見送った3配置では、RESUME後17〜20、1回目RESTART後39〜43、2回目後66〜70のゲームPNGがすべて省略されている。最初の原capture1はiSHの起動コマンド画面（Scene.state0）で、GAME PAUSEではない。担当の初見推定は原画閲覧で訂正した。当時の金壁/候補の有無を確認できる原画像がないため、見逃しを肯定も否定もできない。

metadataではstable/current-prefixの独立4/5/5行があり、最初のFLOORからPAUSE sourceまで204.102/223.905/231.493msで元200ms再確認を満たす。時刻・prefix不備は見つからないが、物理的な候補の陰性分類が正しかった証明ではない。iSH回収失敗ではなく、過去の初期判断画像を照合できない保存上の制約として残す。

追跡課題は、見送り判断に使った初期原画像を既保存/出力予算内で優先保持できる設計。未確認の見逃しを根拠に候補条件や陰性判定を緩めない。受領解析だけで新しいIPAや回収済みrunの再実行は依頼しない。

## 証明範囲

入力間隔は1が約.500〜.525秒と1.039923秒の1区間、2は全8区間が約.512〜.530秒。ゲーム側の受付時刻・恒久毎拍/人超えの合格とは分ける。1の第4→第5実入力（cmd13→15）の約1.039923秒の空きには、4歩目のcapture184でMOVED確定後にVISUAL_SCHEDULE(reason6)へ回復した記録がある。CcommitはACK後260.9995ms。後続cmd14→15のSAME再予約はtarget/NB/D/ordinal/方向を全て維持し、cap194 commitもそのNBの63.274ms前であり、同拍再予約が追加空拍を作ったわけではない。180/182/184原画は非保持で、移動確認が遅れた詳しい理由や不要待機かは未確認。元command_period/scheduleDは個別未exportであり、後刻modelのperiodから正確な超過msを補完しない。

コード・新単体・API/ABI・閾値・予算・配布物は無変更。CI25/実compiler/22seal/全9MachO/全576source/固定3asset匿名全GETは、同codeのbuild126で実施済みの過去検証として保持する。今回新しい製品試験/CI/IPAは実施しない。起動20/20、全対応配置の到達率、見逃し率、対象アイテム認識/通知/対象なしの自動周回、恒久的速度の全要件を今回の2到達で達成扱いにしない。
