# TEST089: 実088の判定待機を置き換える

2026-11-12（日本時間）。[8項目計画](../plans/test089-native-ring.md)・[契約](../contracts/target-assessment.md)。基準e3eb9d59b10d2335a47f9c2d01296d908c7e92f2。生資料/実profile/試験logはGit外。

## 原因と変更

受領test-088-evidence-73de7920は4,742,615B、SHA bc20b823854aae61c6eb15338afdf70f4dd2ad61af68946f257285fbccbb5371。22member/20PNGの全CRC/SHA/size/strict load/certificateを照合。元report/画像不変。対象は最終authority235だけ、SHA c661e2427972e375abd42571ac02a10fa00367a9945c98c37f58ba7c68d2ce40。1行[267,153]、既判定はunknown、word0。人の対象なしラベルはなく陰性へ数えない。

実CPython3.9の1回profileは2.887717秒、icon2.021593秒(70.0%)、PNG復元.780522秒(27.0%)、Paeth345/414行。実機128秒超は表示停止ではなくPython画素処理の問題だった。小さなループ整理を重ねず、全画素処理を同じiSHのstatic Cへ移す。Pythonの厳密PNG検証/有限inflateと有限集約は維持する。feature/閾値/探索順・同率/first target/最大2画像/schemaは変えない。

host全体約43.8秒に対しnative相対実行約10.9秒で、残り約33秒には判定前の全画像回収等がある。時計の絶対値は混ぜない。TEST089はauthority先行取得/暫定表示、全診断回収、最終certificate/cache再結合/正式sidecarの順とし、判定を全画像待ちから外す。全画像・未完pendingは維持する。

## 実行ファイルと数値

Zig0.15.2/x86-linux-musl/i386、SOURCE_DATE_EPOCH=0、strict double/非fastmath/static/strip。56,136B、SHA30967425eb55fd281a1cbea816d300d933f19839f01dd9d1d41630def69e3c02。C13 source/licenseとfeature/manifest generator計15sourceのSHAを結合。ELF32/LE/i386・PT_INTERP/PT_DYNAMICなし、専用homeへ0700配置。異なるsource絶対cwdの同toolchain再buildは全bytes一致。

3.9–3.11/mode0と3.12/mode1を区別、future版拒否。全原309/今回235の既C校正はmode0/1全field一致、最終strip版の4保存packet replayもraw JSON bytes一致。strip前とはtextが112B変わったため、text一致とは呼ばない。親のfloat()正規化で1.0のcanonical bytesを維持する。名前探索が空の左右端はnull→candidate保持。rawscore上界1.000001は固定featureとdouble誤差を包む余裕で、1.5は拒否する。

## 選択検証

新bridge4は有効assertion Red→実3.9/3.12 Green。cache/ELF/source/packet schemaと有限pipe、overflow/nonzero/timeout/取消、TERM無視→kill/reap、原本不変を確認。public classifierのPython画素ループ不使用/正例/空名候補2は実3.9+実i386/QEMU Green、canonical floatの有効Red→修正後対象1Green。新active decoder/packet2は同環境Greenで、filter0..4の同判定、ROI外alpha254拒否、truncated/extra/mode/feature/filter/length不正を実ELFで確認。

新publication2は同088の保存済みrunを実Cで判定し通常immutableZIP/receiptまで完了、noRPC・原本/旧証拠bytes/mtime保持、固定reason/INTTERM/失敗時のpendingを確認。有効Redは固定reason表示不足のassertion失敗、修正後Green。

新合成accuracy1method/5casesは明度.75/.9/1.15・位置・第三slot・名上4行70/239ink削除を先固定し、実3.9+実Cで全期待Green。欠けはcandidate。固定実8runも各1C callで保存済みPython oracleと全field/canonical bytesが一致。人陰性4で誤target0、不明4は採点外。旧Python再分類0、未知陽性holdout0。正例309/今回235や合成変形を未知評価へ転用せず、稀な対象の実機周回を依頼しない。

新早期observer6は実3.9・暗号化HTTP・実i386/QEMUでGreen。意味Redは旧public clientが診断1/proof6/authority7の順で取得することを確認したassertion失敗、Greenではauthority7を先に取得。元manifest/全cursor順、bulk前の暫定表示/sidecar0、最終cache再利用でengine1回、candidate時だけproof優先、既完了画像の再downloadなしで同run回復、失敗後も全画像回収、最終資格消失/foreign/run/export/source/feature拒否、取消時cursor保持/新cancelRPC0を確認。

選択関連18（旧target6/回復3/進捗2/出版4/collection3）は同じ実3.9で成功。初回の14成功は再実行せず、socket作成EPERMで未実行だった4だけloopback許可で実行してGreen。環境失敗をRed/製品回帰に数えない。精度実行時target sourceへ今回のoptional prepare callbackだけを逆変換すると全bytes SHAが一致し、画素/集約関数の不変へ証拠を再結合した。新17methodsと選択関連18を区別し、実8画像をunit件数へ足さない。

全Mac/旧33群/新IPAはiOS native変更がないため実行しない。開発Linux/QEMU秒をiSHや人間速度達成として扱わない。

## 配布と未受入

標準public ubuntu-latestで同toolchain再buildと同梱ELFの全bytesを照合し、固定Release test089-native-ringへ完全source/SHAを保存する。全tracked blob/CRC/匿名全GET/actualtagを確認して返す。IPA148の再作成は0、iOS native/API/全R12不変。

まず新sourceのtest_088.shで同088の通常保存を完了し、runtime/test-088-<uuid>.zipを返却依頼。続いて通常1-1ポーズからtest_089.shで一連3回、全商品可視・候補見逃し・暫定表示/全保存の各時間と全run ZIPを依頼する。既evidence回収やtarget待ち周回は要求しない。実iSH速度・未知陽性精度・毎拍/人超え・歩行停止は未受入。OS背景通知/対象なし循環は今回未実装、候補破棄/自動購入0。

## 同一担当の正式差分レビュー

TEST086から継続する同じ独立担当が計画・全変更源・実行証跡・配布構造を読み、製品は未解決P0/P1/P2なしでGO。独立の意味試験・compile・実画像再分類は0、編集は本reviewへの追記だけ。実物sourceとUbuntu再build・公開後の照合は次gateとして分ける。

CのPaeth同率/byte wrap/全画素alpha、white/sign/HUD、BFS各pixel一回、component全tuple降順top12、同一rowの後代入、最終row順位、word first-tie、iconの整数moments/固定hex literal/volatile各binary64演算を元実装と照合した。C内ではdecimal roundや対象確定をせず、親のfloat正規化と元min/round9・slot/row選別を保持する。raw上限2の広すぎる受理は固定featureの整数分散/targetVarに基づく1.000001へ修正し、1.5/上限超過の有効Redと境界Greenを確認。canonical1.0が整数1へ変わる問題も型assertion Red後に修正済み。空wordは元探索範囲が空の左右端だけで、読める絵をcandidateとして保持する明示的な潜在bug修正である。

固定80B/有限filtered入力と閉JSONを読み、SHA echoをC内独立hashと取り違えないことを確認した。最終ELFは56,136B/SHA `30967425eb55fd281a1cbea816d300d933f19839f01dd9d1d41630def69e3c02`、ELF32/LE/i386/非dynamic/非interpreter、manifest `d133c59f3ececfbbd2b374b8d80cf1aee828decf4da1ef615feed06aeb00b1cc` の15sourceを独立に全hash照合。cacheはrun外の0700で、既不一致/symlinkを修復せず失敗し、絶対path/空env/shellなしで起動する。bounded pipeと30秒watchdog/取消/非zero/不正応答から必ずFD close・terminate/kill/reapし、失敗をunknownや陰性にしない。30秒は故障境界であり実iSHの所要時間保証ではない。

早期observerはread-only/drained terminalと最終ACK PAUSEの適格metadataだけを使い、取得indexだけを優先する。manifest/offset/prefix/保存画像順と閉schemaは元のまま、既完了画像のresume fastpathにも通知がある。個別SHA/durable保存後の表示は暫定と全照合継続を明記し、sidecar/通常完了/次startの権限を与えない。helper/observer例外を既nativeの緊急cancel経路へ漏らさず全診断回収を継続し、最終prepareで失敗を必ず再確認する。全certificate後のbefore_prepareは選択画像0でも動き、cacheのrun/export/最終source role-ID-SHA/feature/classifier/protocolと再読込pixelを照合してから再利用する。cacheはcanonical bytesのmemory限定で、既定Noneの旧経路と通常immutable出版を保持する。

作者の有効Redと実3.9/3.12 bridge、最終i386/QEMUのbackend/active decoder/packet/publication、早期6、合成5caseと固定8runの記録を確認した。旧filter試験はreference decoderであるため、active Cのfilter0..4同結果・ROI外alpha拒否・実packet不正は別の新2methodsで確認済み。関連18は14成功を保持し、socket権限で未実行だった4だけをloopback許可で再実行して成功（環境13 sub-errorsは意味Redや製品回帰へ数えない）。新sourceのoptional prepare callbackだけを逆変換するとaccuracy試験時source SHA `31b56c2d443126a1c23b50c0d3518c6be7d131b1620b83e3d0cbfa63d732ccfe` に全bytes一致することも独立に確認し、8run/原309・235を再分類せず数学部分の証跡を結合した。固定8は陰性4の誤target0/不明4採点外、未知陽性holdout0を維持する。

基準e3eb9d59からiOS native/R12の114pathとprotocol/validation/feature/旧088entry/sh/証拠回収入口等8path、計122path・R12全40は全bytes不変。初期3文書15,945B/native契約12,277B、diff checkを確認した。製品/文書を先にskip-ciで凍結し、新source-stage workflowだけにその実SHAを固定してUbuntuの同toolchain再build/同梱ELF全bytes比較→全tracked source/CRC/SHA→固定draft443057841への2assets stagingを行う構成は妥当。現CODE placeholderの確定と実物/actual tag/匿名全GETは引き続き同人で確認する。商品到達・暫定指輪表示・全画像/ZIP完了の三つの時間を分け、実iSHでの速度・人超えや旧歩行停止が解決したとは主張しない。

同じearly1methodのCLI結合補強も確認しGOを維持する。最終test SHAは `a68f107fdcd08bea7f0a90f8f6952e4a7d48e2a644015f0ab57dea88321ff958`。public test KEY/TOKとloopback transportだけをfixtureへ向け、実test089.main→test069.main→native.main→run_session→先行観測→全certificate→before/cache→通常ZIPを実3.9/最終ELFで通す。早期表示時の保存画像1枚/sidecarとZIP不在、authority先行、最終分類1回、通常sidecarの期待は弱めず、補強した同1methodだけ1.607秒でGreen。製品source SHAは元6Green時と不変、unique6を増量せず、旧5methodsやaccuracyを再実行していない。独立担当は差分・実log/source bindingを読取確認し、追加実行0。
