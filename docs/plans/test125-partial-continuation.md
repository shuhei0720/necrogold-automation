# TEST125: PARTIAL継続の材質と投影縮退

2026-11-27（日本時間）。[実機計画](test125-device-failures.md)のd301/8831を対象とする短計画。基準CODE20778950、C SHA2fde2c4c。生画像・Scene・packet・時刻表はGit外。d301原因receipt506d1e94、8831原因receiptf91f0d35。実機改善・未来の到達は未確認。

## 原因と変更

原通常workerは元D内の正常UNKNOWNとして採用済み。d301の122→124は空PARTIALの既UP framingで、遠方の保護外UNKNOWN→FLOOR一セルだけが静的ROUTE10を起こす。8831の135→137は非空safe PARTIALで、下段5ITEMを全て保ったまま上端重複ITEMの一セルが既左レールに支持されたGOLDへ縮む。現行top-aliasはこの役割を扱えずROUTE10。両方とも原sourceへの通常MotionはBLOCKED/零で、停止診断Motion0は静的拒否前の初期値である。

変更は共通`cycle_partial_*`の読取専用関係に限る。新owner、DATA、再分類、予算、期限、Runtime、Ring、Perception/Nav、ABIを追加しない。別担当のupper slot/result修正とは関数を分ける。

1. 遠方・両画像で保護外のUNKNOWN→FLOORを、既存のclean safe PARTIALまたは空framing権限に限って静的材質関係へ加える。位置・入口方向をrun固有に固定せず、原点/次歩の各3×3、GOLD/ITEM/DOOR、保護セルには適用しない。UNKNOWN→DIRT/STONEは広げず、既存の材質対は保持する。元source・同じ5成分の選択・原点/次FLOOR・通常直接零を外側で再確認する。
2. 上端重複ITEM→GOLDを、旧top ITEM内の縮退としてだけ扱う。既clean safe PARTIAL、同じ実UP開扉、両方FLOOR/PARTIAL、正確なITEM＋cardinal halo、同じ連続下段3個以上、旧/currentの同じ列にある下方3GOLDレールと中央UP corridorの保持を要求する。新GOLDは旧ITEMだけから生じ、全旧GOLDを保持し、current ITEM/保護は旧集合の部分集合でなければ静的aliasにしない。旧sourceと大きいpotential/haloは書き換えない。上端両外縁のhalo脱落は、下段ITEMを持たない同一材質の外縁で、旧1→新0だけを正確なmaskから説明する。追加保護や他のhalo喪失は許さない。新ITEM/DATAとの混合は従来の新DATAまたは拒否へ残す。

後者は普通材質→新GOLDの許可ではない。元135の10ITEM/haloは新137の5ITEM/haloと支持GOLDを全て覆い、下段は不変。原正常packetを含む観測potentialの実測hullは旧[334,-59,634,127]、新[334,-23,634,127]で、同UPによって旧可視商品画素を失わない。offscreen/HUD画素は未確認のまま保持しNEGにしない。この実画像校正と、旧potentialを縮めず同じUPだけを認める集合関係を組み合わせる。現在のSceneへ旧ITEMを合成したり、packetのboxを改変したりしない。

追加DATA案は採用しない。8831 job1/2のpacket・currentUsed/shared DATA2は未保存であり、job3だから残枠があると仮定できない。既current PARTIALはframing/PROTECTED9に限定され原ROUTE10からも入れず、別の二重halo拒否もある。静的縮退の証明が成立しない変化は元のDATA/拒否のままにする。

## 状態への適用

| 状態/cut | 同じ関係を使う範囲 | 維持する権限・拒否 |
| --- | --- | --- |
| 元通常job pending | 今回の二関係だけで結果やMOVEを作らない | 原worker/D、候補優先、未採用画像の無権限 |
| 採用後OBSERVE_MORE | release後開始の独立currentをimmutable anchorへ直接比較 | 元job/source/prefix/P、同選択、次FLOOR、通常直接零。d301/8831の実停止cut |
| SEARCH/既continuation credit | 共通静的関係を同じ原anchorへ再適用 | source/job/credit/期限/消費済み枠を再発行しない |
| 未開始reserved/READY | 観測更新と準備時に同じ関係を検証 | command ID/ordinal/source/NB/D/owner/epochと既一用証明。予約を新MOVEへ作り替えない |
| begin | 同じ関係と既C所有直接零証明を確認 | 実return fence、freshness/source150ms/input10ms、foreground/lock/owner/取消/P |
| begun/ACK/UNKNOWN | 二関係から再送・追加歩行権を作らない | 既normal Motionだけで実unitを確定。ACKはunitでない。UNKNOWN無再送 |
| 正候補/強いword/非floor/古いprefix/期限切れ | 旧veto/holdを維持 | candidate優先、元P/D/W・worker100ms・全予算を変更しない |
| 普通材質→新GOLD、旧GOLD喪失、ITEM増加、別choice/足場/実変位 | 今回の静的許可は適用しない | 旧DATA・再評価・拒否を保持。元SOURCEをpatchして通さない |

原123(d301)/136(8831)は通常零でもrelease前開始であり、独立currentに流用しない。原C-returnは未保存なのでcaptureEnd/observeStartで代用しない。

## 意味Redと直接確認

実装前にpublic C callbackだけで開扉・正常UNKNOWN採用を稼ぐ二fixtureを準備する。非公開flag注入や原packetの改変はしない。d301型の空framing＋遠方UNKNOWN→FLOOR、8831型の非空safe＋支持GOLD縮退が、元124で正常compile後にSEARCH継続のassertionで落ちることを確認する。手続き画像・時計・将来応答は宣言したモデルであり、欠落実機画像や受入成功と呼ばない。

Greenでは同じ二fixtureのOBSERVE→SEARCH→予約→READY/begin、既ID/NB/D/Pと全入力/unit数保持を確認する。remote位置/入口方向、レール支持、old GOLD保持、lower ITEM保持、mask subset/余剰halo、原点/次FLOOR、候補/強word、Motion UNKNOWN/実変位、prefix/release/owner/取消/期限、普通材質→GOLD、UNKNOWN→DIRT/STONEの境界を関連する既試験と限定新caseで確認する。旧quiet/side-palette/top-role/beginの成功assertを変更しない。

続いて通常producerの不完全UNKNOWN→独立current→未来UP ticket→ACK→正常MOVED一unit→新しい通常producerの完全NEG→独立C採用→PAUSE/耐久保存/RS/次floorを宣言したcallbackモデルで結ぶ。旧実機の9043 policy19成功と実指輪候補の旧証拠は別の回帰根拠として保持する。影響のない全Runtime故障や全worldを既定で再実行しない。

独立計画レビュー後にRedを実行し、意味Redを確認してから最小実装へ進む。独立差分確認・必要な実IPA/source同一性確認と固定配布は実機計画へ記録する。
