# TEST118: V2実unit後の未発行次拍を保つ

## 1. 目的と範囲

既上部routeの同じ安全証明をV2の実unit後へ統合する。H1/H2/D1/D2の正常MOVEDを受けた後、次のH2/D1/D2/D3だけが対象となる。初回H1、開扉、V1、他route/profile、入力・DATA回数・元allocated Pは拡張しない。既定の50ms準備で選ぶslotと、既Runtimeの実AX/送信guardは維持する。

## 2. 原因と前の限定修正との差

CI261ではsource65/job3の返却後に取得した66の観測commitが、次D1の50ms準備機会に遅れ、H2→D1で一拍失った。66は返却後に取得開始しておりearly snapshotの不足ではない。ただし原66のRAW/永続frame metadataはretainedされておらず、原65→66 strictzero・全Scene一致・当時のprivate cache資格を独立に再現したとはしない。保存されたdiagnostic/model/ledgerのstable非inflight/prefix/同poseと時刻、新公開試験の宣言modelを区別する。新helperの実行時normal zero必須条件は維持し、次の実Macではauthorityになった原sourceを保存して確認する。

D3自体は通常50ms準備で予約し実ACKしたが、ACKが元Pを47.939920ms越え、P内の正常unit画像がなかったためMOVED/新FULL job/陰性RSには至らなかった。

前のD3限定例外はこのrunで未行使だった。既定slotが元Pに入る場合でも、まだ未来にある未発行次physical beatを50ms準備だけで捨てると後続全体の余裕を消費する。今回は同じ正常unit・直接零・未発行拍の証明をpostunit全体へ適用する。元Pや50ms tailを延ばす計画ではない。

## 3. 統一した資格

既private helper/typeをpostunit名へ揃え、`upper_tick`からの呼出しを再利用する。新Controller field・pending proof状態・ABIは追加しない。V2/既`restart_yield.enabled`/stage2/steps5、inputs1..4を要求し、horizontal=min(inputs,2)、down=max(inputs−2,0)とする。最新eventは、そのcounterに対応する同routeの実ACK/通常unitでなければならない。inputs1/2の直前方向は元水平方向、inputs3/4はDOWNとし、Motion dx/dyはその厳密な単位変位と一致させる。

最新event/現command/upper.issued/ordinal/last_completed/cycle prefix/upper prefix/元unit画像IDの一致、nowとcurrent sourceがACK end以降である条件を維持する。後続の発行済み/NOT_SENT/STARTED/UNKNOWN eventが一つでもあれば資格はない。freshで有効なcurrent model、`model_capture_id>=proof_capture_id`、同job/episode/anchor/current全bytesとmetaに結んだ実normal zero cache、world/床/保護、正常UNKNOWN/INCOMPLETE採用、worker/assessment非実行、候補なし、入力非実行という既資格は維持する。

## 4. 次physical beatと元境界

既定`prepare_recovery_slot`が計算済みで、sync/phase等でfinish/slotclearしていないことを前提とする。同current modelの`ng2_next_target(now,lead)`が、最新ACKの不変target+凍結command periodを既`corrected`で写した次physical beatと一致し、既定50ms slotはそのさらに一拍後と一致する場合だけ選び直す。必要性のfilterはOR形とする。旧defaultの`upper_budget`が不適合なら既資格を維持する。defaultが適合する時だけ、最新eventのobserved ID==cycle capture==upper captureであり、通常unit bindの凍結`upper.anchor_end`が不変target以降であることを要求し、offset=anchor_end−targetを求める。残歩数remainingのdefault末端=defaulttarget+(remaining−1)*currentperiodをoverflow拒否後に計算し、default末端+offset>元Pを必須とする。加算自体はPからの差との比較でoverflowを避ける。

このoffsetは直前の正常unit画像を実際に取得できたまでの観測値で、未来費用の下限・保証・画像権限には使わない。新候補自身は従来の残routeの元Pへ既`upper_budget`で適合しなければならない。新しいexpiryや追加periodは作らない。

新NB>nowかつ残準備<既50ms、新NBにpublication100ms/source200ms、元source/model/session/root/walk45/cycle/upper capを適用する。tail=lead+50msは別の鮮度余裕として維持する。新deadlineは旧slot/鮮度上限と新NB+10msのmin、visual/scheduleも旧値と現在の元境界のminとし、overflowを先に拒否する。local全成立後だけ同tick内で未発行slotをpublishし既reserveへ渡す。reserve0では提案slotを清算し、旧finish/holdへ閉じる。新しいperiod、古いticket、過去NBへの再送は認めない。

## 5. 旧D3試験を削除せず継承する方法

旧`test_native_upper_last_slot118.py`の原本（SHA1ad39494037af92a501ccc27627288664b6bb75684cdc5a8e15e41bdb94c07b6）、旧693a/51721 source、Red/Green/logと元CI260/261時刻は私的に保存する。元80の遅いproofはNB自体がまだ未来だったため、統合後にそのD2を救うことが新しい期待となる。この旧「D2は救わない」assertを消すだけでは受け入れない。

新統合試験側は元CI260/261の相対capture/worker/ACK/commit機会を保持し、旧51721が次H2/D1/D2を発行できない意味Red、新版の元次physical beat予約と元P/counter維持を確認する。既D3境界側には、独立した明示的新入力として「D1後の最初control tickが次physical target+既20ms cadence後」という遅延を与える。ここではNB自体が既pastなので統合後もそのD2を救えない。一拍lostのassertと後続D3の例外・veto・再送拒否を残す。この変更後の独立fixtureを元CI260の完全時刻再生と呼ばない。

## 6. TDDと検証範囲

8項目の設計P0解消後に新公開試験を用意し、旧51721で左右・各後続H2/D1/D2の意味Redを保存する。opaque注入や都合のよいphase移動を使わず、公開ACK/MOVED/worker/source/独立snapshotで状態を作る。D3は既最後slot境界を継承する。初回H1/V1/feature-off、候補、未知/保護床、prefix/modelの失効、過去NB、既発行/NOT_SENT/UNKNOWNを拒否し、元P/10ms/通常MOVEDだけのcreditを確認する。

新統合試験、更新した既D3試験、直接upper7/cache8/snapshot3/V1関連3を限定回帰とする。各guardの新動的subcase・既回帰・静的source確認・専用negative未実施をguard-mapへ分け、新数件の成功で全guardの動的実証としない。実装は設計レビューと旧意味Redの後、rootの明示許可を受けてから行う。

今回の区分は私的`postunit-guard-map.json`へ記録する。新3methodは左右×postunit1/2/3の資格前提付き正例、default予測がfitする2種、feature-off/候補/床/保護/prefix/phase/過去NB、公開済み/NOT_SENT/UNKNOWNの再送拒否を実行する。改訂D3の3methodと既21を合わせた全27methodで回帰する。初回H1の除外はliteral guardの静的確認、V1は既関連回帰、job/anchor/current全bytes等は既cache試験と静的比較へ対応付ける。source200/pub100/tail50/個別上限/overflow/reserve0等の専用negativeを全て新注入したとはしない。

## 7. 配布と実Runtime受入

source/test/function/plan SHAをfreezeし独立diffレビュー後、同Runtime/fixture時計/ACK/generatorの実Macで全HHDDDの正常unit、正常FULL陰性、耐久RS、次childを確認する。CI261のinflight assertionは別担当が原境界を調べ、今回のslot変更で成功扱いへ置き換えない。元失敗・欠測・最終保存fitと実live modelの違いを残す。iPhoneの受入・速度は別未確認とする。

## 8. リスクと対象外

50ms未満では実AX準備が間に合わず、既Runtime guardがNOT_SENTとして閉じる可能性がある。default適合時の観測offset filterは、原失敗に近い遅延域へ適用を絞る品質上のヒューリスティックである。過去offsetは未来の下限ではないため、旧defaultなら後続が速く成功し得たrunを短AX窓のNOT_SENTで失うtradeoffは残り、悪化しないとは断定しない。安全な送信境界の保持と成功率の評価を分け、実Macで確認する。

元Pに入らない実ACK/画像からMOVEDを付けたり、speculative FULLに入力権限を与えたりしない。P/10ms/source/worker延長、一般の準備50ms変更、数値20/45ms等の製品threshold追加、Runtime/renderer/camera/ACK/phase変更、初H1/V1/開扉への拡大、過去eventのperiod推定、新period/旧ticketの再利用、新pending状態は対象外とする。
