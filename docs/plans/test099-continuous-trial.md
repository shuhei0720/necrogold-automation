# TEST099: 原因が残る通常試験と連続運転試験

2026-11-14（日本時間）。基準bd5edaa。[要件](../requirements/necrogold.md)・[制御契約](../contracts/native-control.md)。新しい利用者指示は「通常にテストできる版」「対象まで周回し、障害時にログで特定する」。実機成功/速度/未知精度を保証しない。

## 1. 受領と目的

098run97afbの18PNG/20recordを全照合し、回収は成功。元実行は3歩/1restart後にNO_PATH、商品判定0。保存Sceneは当初bit5だけ、最後にも同候補のUP/FLOOR経路がある。2beat待機の期限との時刻対応はあるが、待機kind/anchor/途中画像がないため原失敗条件は未確定。推測で入力条件や期限を緩めない。097実1の継続許可後の再検査も未解決で、098の診断はその分岐へ届いていなかった。

## 2. 診断の変更

旧Status/Event/Scene ABI・旧入力条件を保ち、読み取り専用の別getterで最初の停止と通路待機の情報をimmutable snapshotにする。stage、拒否条件、時刻/期限、source/観測/anchor capture ID、prefix、world位置、通路bit/候補状態/待機kind、最後の待機比較結果を残す。cycle_failure/finishで情報を消す前に初回だけ凍結し、cleanup/PAUSEで上書きしない。post-creditのrelationは一度評価し、元の停止は維持する。

Runtimeはcycle profileだけで現待機anchorと初回停止の判断画像を既有限保存へ接続する。無制限な全frame保存にはしない。記録の許可を入力/再同期/陰性証明へ使わない。既critical/判断画像を押し出さず、cycleだけpin/終端選択を20→24へ増やす。旧profile20・spool44画像/64MiB・元入力予算は保持する。新しい再観測条件を原不具合の修正済みとは呼ばない。

## 3. 連続運転の境界

最初の実用に近い試験は、既nativeの有限runを自動でつなぐ明示した--until-targetとする。各runの16入力/12restart/45秒/180秒/4商店、元UUID/世代/取消/UNKNOWN無再送は保持する。LIMITなら一律再開せず、Cからの読み取り専用handoff証明と、そのrun全記録/画像/ZIPの検証・公開ACKが揃った場合だけ別UUIDの通常startへ進む。画像回収のために各区切りで停止時間が入る試運転であり、最終の人超え性能達成とはしない。Runtimeの128run上限/保存容量の限界も異常終了として明示し、無断解除/自動LoopCtrl再起動しない。

handoffは後からLIMITと残存outcomeを推定せず、以下の正常区切り分岐で直接凍結する。handoffを認めるのは2種類。A: 正常・完全な対象なし判定、候補0/不明0、durable checkpoint成立、入力0・実PAUSE確認後、4商店またはrestart予算による正常区切り。B: 実restart後の新levelで方向入力/移動0・原点・全初期観測完了、金/商品/通路候補/未解決状態なし、既skip資格を持つFLOORをsourceとした実PAUSE確認、restart上限での正常区切り。いずれもterminal/全worker drain/noinflight/未知入力0、同run/prefixの凍結sourceとpause実観測を必要とする。NO_PATH/BEAT/SCREEN/期限/取消/UNKNOWN/商品未確認/候補保持では証明0、次run開始0。

古い票や進路を引き継がず、新runは既通常入口から新鮮なPAUSE→RESUME/1-1認識を経る。店内の陰性区切りでは新しい画像で再判定し、対象候補を捨てる権限を過去の陰性から作らない。旧profileの通常単発動作は変更しない。handoffは新しい入力APIではなく、完全に終了した通常runの後に次startを呼ぶクライアントの資格である。

## 4. クライアントと記録

099は通常の単発試験と--until-targetを提供し、--recoveryは新startなしで同runを回収する。元098spoolとは別にする。campaign ledgerは原子的に保存し、未公開runを飛ばして新UUIDを発行しない。開始/回復時はまず既active journalを、published=trueでもrecovery_onlyで照合/再保存し、run ID・ZIP hash・handoff証明をcampaign索引へ結ぶ。通常publication.runは公開済みrunから新UUIDを作るため、照合前に呼ばない。次run intentを原子的に保存してから通常の新startへ進み、途中crashではactive journalと索引を突き合わせて未確認startを飛ばさない。startの曖昧な応答では同UUID回収だけ、restartやstartを自動再送しない。TARGET/CANDIDATE/実際の商品判定UNKNOWN/障害/停止は即ループ終了。Bは当該levelの商品判定が未実施であることを必要とする。job0の既定outcome=unknownは商品判定UNKNOWNと別で、明示的なclear_search_limit証明がある場合だけ継続を認める。過去levelの判定が残る場合は、直前の採用済み完全陰性/durableと実restart後のSEARCH資格が必要で、未解決の実判定を無視しない。

campaignはrun ID/結果/回数/採用状態/原ZIP hashを小さな索引へ残し、各runの全ZIPはiSH原本/展開先へ保存して消さない。終了時は索引と最後のrun全ZIPをまとめた返却用ZIPを作り、障害の直接根拠を一度で返せるようにする。前runが必要な場合は索引から特定して追加返却を依頼する。全履歴の巨大ZIPを毎回転送せず、未観測/未知を陰性へ丸めない。

既Runtimeの128IDはprocess全体の上限で、campaignの128run上限より先に過去の単発実行で到達し得る。既generic拒否は未開始確定へ読み替えず、曖昧なstartとして同UUIDの回収だけに留める。今回この旧拒否schemaは変更しない。新IPA更新後の完全再起動から試す。有限runごとの通知はcampaign全体の終了とは限らず、iSHのcampaign終了・保存完了表示を終了条件とする。

## 5. Redと選択検証

新診断の初回固定/各stage・通路待機・source画像、handoff正常A/Bと全拒否、旧ABI/元予算不変をC公開単体で意味Red→Green。campaignは安全handoff後だけ次UUID、target/候補/unknown/障害停止、回収中断/公開前後のcrash、取消/同ID/索引/返却ZIPを実Python3.9で意味Red→Green。Runtimeは新snapshot/画像保持/実run終端→公開ACK→次startの該当callbackだけMacで選ぶ。全world/全Runtime故障は追加しない。

## 6. 独立レビュー

新しい自動start資格の設計は実装前に独立確認し、正常な陰性/見送りだけを次へ渡す条件と、未知・取消・入力中/未drainの拒否を重点確認する。実装後は該当差分1回、指摘の訂正は狭い差分だけ確認。既停止原因が未確定であることを隠さない。

## 7. 保存・配布

native変更が必要なので実IPA/封印/実compiler/全source同一性を確認し、固定ReleaseのIPA/完全コードを公開する。R12全40/G1・Ring/Bank/Coverage/判定kernelは不変。rawZIP/PNG/Scene/report/私的設定はGit外。修正表には診断不足と連続運転の資格を別行で記録する。

## 8. 実機確認

IPA更新・LoopCtrl完全終了/起動・Start Server/通知/通常VPN。通常1-1ポーズから099の通常試験、または--until-targetで探索→入店/商品確認→対象なしの次周回を一連で回す。対象/候補/故障/手動停止で停止通知後iSHへ戻り全保存/ZIP照合を待ち、返却用campaign ZIPを送ってもらう。原097/098の停止が解消したかと、次の停止条件が特定できる記録が揃ったかを区別する。

## 実装の読み取り専用schema

cycleのterminal/checkpoint recordのpayload.controllerへ、旧固定ABIと別のgetter snapshotから2辞書を追加する。旧HTTP reportの必須schemaや入力APIは変更しない。

`handoff`: 閉keyはschema/kind/allowed/reason/qualified_ns/source_capture_id/source_prefix/pause_capture_id/completed_prefix。schemaはngg2-trial-handoff-v1、kindはnone/negative_limit/clear_search_limit。allowedはbool。reasonは既enum、ns/ID/prefixは非boolの非負int。Cの正常分岐でsourceと時刻を凍結し、実PAUSEのACK/独立観測・terminal/input0・取消/障害なしが揃った時だけallowed=true。source/pauseの画像metadataとprefixはclientがmanifest登録集合へ照合する。Aのsourceは分類cycle.capture_id/prefixとして完全陰性採用記録と照合する。Bのsourceは再確認した実PAUSE用FLOOR画像/prefix、qualified_nsはその再確認時刻とし、元の正常分岐markerはC内部で不変に保持する。Bは実restart後の当該level状態を証明し、過去のjobがあればその最後の完全陰性/durableも確認する。途中のgeneric LIMITや過去levelの残存陰性からはmintしない。

`stop_detail`: schemaはngg2-stop-detail-v1。valid/stage/reason/at_ns/source_capture_id/observed_capture_id/anchor_capture_id/prefix/deadline_ns/wait_kind/passage_bit/passage_pending/passage_unresolved/passage_unlocalized_gold/x/y/validation/motion_kind/motion_dx/motion_dy/last_comparison_capture_idを記録する。stageはnone/generic/passage_wait/cycle_observe/cycle_credit。valid前もlive待機anchorをsnapshotし、Runtimeが有限に画像保持する。最初の失敗後は凍結し上書きしない。証拠を入力許可へ昇格しない。

通常start前の版検査は、既認証済みcycle queryへ読み取り専用trial_support modeを追加し、既run lookupより前で応答する。paramsはrun_id/mode/ownerだけ、payloadはstop_detail_schema/handoff_schema/maximum_run_ids/pin_limitの閉keyで上記schema名/128/24を返す。入力やrunを作らない。clientの専用subclassだけがこのmodeを許可し、通常check_schemaとこの機能検査を各新start前に行う。旧IPA175は未知modeとして拒否され、099の新ゲームを開始しない。既runの読み取り専用回収は機能検査失敗でも閉ざさない。RPCMethodの既cap一覧や旧profileへ変更を混ぜない。
