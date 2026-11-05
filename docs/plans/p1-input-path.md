# P1: 続行対象の入力方式を実機で選ぶ（TEST-011）

2026-11-05（日本時間）。TEST-010で横長原画像の修正を確認した。次の限定的な診断で、画像座標を推測せず「ゲームを続行」の参照がゲームのアクセシビリティに実在するか確認する。診断P1.5と導入済みNG-G1を維持する。

## 1. 概要

ゲームを1回開き、前面確認と横長原画像取得を行い、固定ゲーム・完全一致の「ゲームを続行」をfind_elementで1回だけ照会する。戻ったrefの有無、label一致、frame、hittable/visibilityを限定情報として保存する。refの値自体は持ち越さず、tapを実装しない。終了時の前面と原画像も保存する。

## 2. 背景

画像896×414と入力側414×896は別。画像だけから正しいtapを決められない。固定取得元のfind_elementはlocateElementによるAX照会で、scroll_to_elementとは別の読み取り専用処理。画面OCRは既存の縦横仮定を使うため、座標の独立根拠としない。AX参照が確認できれば次の入力試験はそれを都度取り直す方式を候補にできる。確認できない場合は、専用の無害なタップ検証画面による入力backendと画像の対応を検討する。

入力の取消/期限は別の未解決事項。現行取得元のUIキューはHTTP期限が過ぎても処理を実行し得るため、今回のhost停止を入力取消保証にはしない。入力を行う版には端末の実行直前ガードが必要。

## 3. 詳細設計

- 新しい診断モジュールと起動shを追加。既存capture、Client、R12は変更しない。
- 専用Client派生型でfind_elementの固定paramsだけ追加許可。対象bundleはGAME、element_idは「ゲームを続行」、matchはexact。送信前に1回の権利を消費する。screenshotも固定paramsのみ許可し、親のClientへ無条件に検査を委譲しない。tap/tap_element/scroll/run_steps/rotate/config等は拒否する。
- 初回device_infoでcapabilitiesがlistで、完全一致のscreenshot_image_geometry_v1を含むことを必須とする。その後launch_appは1回まで。
- launch後device_infoのforeground=game、screen_locked=falseを要求。unknown/別アプリ/欠落なら照会も取得も中止。これは瞬間の観測であり、競合中のアプリ切替を防ぐ保証ではない。
- screenshotはJPEG quality0.6 scale1 geometry=image_size_v1。既存inspect_payload/validate_source_geometryで原バイト、実寸、EXIFを確認して保存。画像を変換しない。前画像取得後にdevice_infoを再確認してからfind_elementを呼ぶ。
- find_elementのRPCエラー/timeoutは理由を推測せず「参照未確認」。自動再試行、部分一致/OCR/scroll/tapへのfallbackはしない。全RPCエラー、画像検査/保存失敗、checkpoint失敗でも追加RPCを送らず終了する。
- 成功時は応答をwhitelist化。labelは一致bool、refは存在boolのみ保存。数値は有限・座標±4096/幅高さ0超4096以下、既知type/visibilityだけ採用。exists/hittableはbool厳密。match_count > 1またはalternativesが1件以上なら曖昧扱い。match_count/alternativesの型不正・矛盾も未確認。文字列本文/value/hint/ref/任意の例外文は保存しない。
- AXの確認判定は、exact label一致、exists=true、refあり、hittable=true、有限非空frame、応答で複数候補が報告されていないこと、前後foreground=gameかつunlockedの全条件。合格表現は「候補参照を確認」であり、タップ成功・座標検証・遮蔽なし・P1合格ではない。hittableは取得元のinView近似なので実際の遮蔽を保証しない。
- 成功応答後もdevice_infoと後画像を取得し、前後のゲーム表示は目視評価する。両画像とも取得直後のdevice_infoでgame/unlockedを確認してから原画像を確定保存する。別アプリ/unknownならその画像は保存しない。通知や観測間の一時切替の保証ではないため送付前の目視も必要。後画像の検査・保存を含む全段階が完了して初めて候補確認を確定する。自動GAME PAUSE分類器は今回実装しない。
- worker内のOwnedRpcTimer、親から50秒のプロセス監視、終了理由/子終了状態を使用。各段階でreportをatomic保存。新CLIで親SIGTERMをKeyboardInterrupt相当の停止受付へ接続し、既存superviseによる子terminate→期限付きkill/reapへつなぐ。終了理由は固定コードを保存。元々入力APIはないが、親停止後の継続RPCも止める。すでに端末へ送った照会の取消とは呼ばない。端末の継続用readerは既存手順と同じ一時的catで値を破棄、終了時停止要求のみ、保存後iSH終了を案内。
- device_infoは既存safe_info、画像は既存検査の固定fields、AXは限定値を保存。親の再読込はTEST011の固定kind/stage/input_authorized=falseとschemaを厳格に検査し、未知field/生ref/任意文字列や破損・過大JSONを拒否して安全な初期reportへ戻す。capture専用read_checkpointを流用しない。候補一意性は全ツリー未観測なので保証しない。
- runを分離し、既存reportの上書きなし。ペアリング情報は既存ファイルを読むだけでZIPへ含めない。

## 4. 影響範囲

新モジュールnecroprobe/input_path.py、test_011.sh、tests/test_input_path.py、手順/計画/レビュー。P1.5captureの131試験は保持。IPA再インストールなし。今のゲーム状態を変えるコマンドは既存のlaunch_appのみで、ポーズを解除しない。

## 5. 新規テスト

実装前Red: 固定find許可と一回制限、別bundle/部分一致/別ラベル/未知params/操作API拒否、capなしと前面unknown/lockedでfind未送信、画像契約違反で停止、findエラーで後続RPCなし、成功でもinput_authorized=false、曖昧/不正数値/未知文字列/偽ref型を候補確認にしない、原画像バイト保持、親期限で子終了、結果を再読込した時の許可値保持。さらに親だけのSIGTERM、全段階の保存/RPC失敗で後続0、後検査完了前は候補未確認、ref/数値/曖昧性の厳密型、schema未知field/欠落/許可値true・1・null/NaN/過大JSON/秘密文字列注入のRedを追加。capabilitiesはlist内完全一致を要求。既存全ホスト試験も回帰。実機試験は未実施と明記する。

## 6. 実装順

①本計画→②③fresh-context設計/異常系/安全レビュー→④⑤ホストRed→最小実装→Green→⑥独立実装レビュー最大3周→⑦ユーザーへ完整コード・実行1行・結果の返し方を提示。⑧必要な整理のみ。TEST-011の結果でAX方式か専用入力検証画面かを分岐し、闇雲な座標タップを試さない。

## 7. 保存前確認

固定取得元の照会経路が入力を含まないこと、許可メソッド/params、host試験、秘密値のwhitelist、reportの保存、独立レビュー、R12 tree不変。read-onlyテストの完了を実ゲーム続行の合格としない。

## 8. スコープ外

ゲーム内入力、Options、リスタート、購入、UI探索、座標推測、画像の後変換、通常ループの高速化、長期耐久、旧report編集、原APIの取消可能性の偽装、別IPA導入。
