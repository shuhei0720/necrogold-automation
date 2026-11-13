# TEST093: 開扉後の安全な入店を再判断

2026-11-13（日本時間）。基準 `732a3d33a5c7512b0185ec2430aed187cdd0ec78`。[修正表](../fix-records.md)のFR-071-SHIELD/077-NEW-GOLD/081-CLIPPED-ENTRY/090-THIN-IRON/091-OPEN-BLUR/092を照合する。Controller内の限定適格条件と既存未送信回復だけを変更し、旧guard/helper・期限/予算を保持する。

## 根拠

092受領4ZIP/80PNGは全CRC/SHA/strict load/certificate/canonical sidecar/登録集合が整合し全回収済み。実順4062→a6b6→e3a6→ebf。最初2回は同配置の停止と直後再試行、3回目は商品確認、最後も開扉後停止。全失敗はDOOR_OPENEDの0変位を確認済みで、次の入店MOVEをbegin前に拒否した。鉄扉型誤認や開通UNKNOWNの再発とは分ける。

4062 source243→246は上端の商品ITEM/protected投影の拡大と遠方材質差。初期partial-shop lost-GOLD guardが最初に拒否する。直前244/245のrawは未保持で復元しない。a6 source128→130は投影縮小と遠方DIRT→STONEで旧clipped条件が外れ、一般FRESHのPARTIAL対象外へ進む。ebf source213→215は入口2セル先DIRT→FLOORと遠方STONE→DIRTが旧quiet/global monotoneの対象外。直前212→213のFRESHは成功している。validation番号の正本はFLOOR7/GOLD8/PROTECTED9。

原7PNGの一度の解析と保存済み現Cで、実visits/位置を復元して4pairの完全Decision5が同一・次FLOOR・strict BLOCKED0を確認済み。新しいNav/Perception証明は不要。原246/130にはのろいの名/絵があるが2商品のみでauthorityなし、個別照合/通知未実施。matcherの偽陰性・対象なしにはしない。

## 別IDの入店権限

state1の確実未送信event(begin/outcome0)、同方向の最後のACKがDOOR_OPENED0、未入店・lead/実MOVED確認済み、両FLOOR/CANDIDATE・同じUNKNOWNまたはPARTIAL、同じ完全Decision5(reason5/隣接FLOOR)、同じ金bracketを要求する。原点/次床と十字近傍の保護、元source判断、元時刻/chain2/run8/入力16等を維持し、strict BLOCKED0を1回確認する。旧quietを広げず、旧IDを永久撤回して最新sourceのFRESH12へ渡す。target/NB/D/ordinal/epoch/親horizonは同じ、移動/開通creditは0。

- 上端PARTIAL: 実際のITEM footprintからPerceptionと同じ中心＋十字1セルの投影を導出する。3セル以上の連続したITEM footprintと共通保護coreを保持し、ラベル/保護の出入りは観測商品の投影端だけ。投影外のGOLD/ITEM/保護、原点/次床/金bracketは保持する。遠方の非商品材質差は両局所域の外に限る。特定PNGのx座標や、無関係な遠方差の有無で旧negativeを避けない。
- UNKNOWN: 保護不変、sourceと直前観測のGOLDを保持。局所差は開通済み次FLOORの奥の軸2セル目DIRT→FLOORだけで、原点/次セルは変えない。遠方差は非商品材質に限定。旧071のPARTIAL対角脇条件や旧077新金条件は不変。

4062の早期lost-GOLD拒否は、限定適格形だけを後続の全権限検査へ通す。形だけで入力・旧ID保持を許可せず、mask0でも新権限の検査を省略しない。UNKNOWN入力/送信済み、全商品可視、保護近傍、欠けたbracket、非zero/不明motionには適用しない。

## 元窓に間に合わない場合

ebfの実C commitは元NBまで0.719539ms/Dまで10.719539msで、capture endからの残時間と混同しない。FRESH発行・mainの実begin・complete0で元Dを守り、窓や準備50msを延長しない。

既存の確実未送信expired回復はUNKNOWN向けで、PARTIALには入れない。開通確認済みの同じreason5/FLOORで、最新tiles/保護が新authorityと完全一致、完全Decision/安全床/bracket/strict0が再成立するPARTIALだけを既存有限回復へ追加する。旧ID/旧event/creditは不変。旧slots/epochを捨て、独立した新しい画像/HUD資格と実際の将来拍・準備50msから別権限を作る。新scopeの親期限は元visualDと既12秒/45秒/180秒の最小で短縮だけ。回復を重ねて期限を更新しない。最新画像がさらに変わった場合は同一画像の証明として通さない。

実退役時刻もprivateに保持し、退役前に取得を始めた画像を新しい独立画像へ見せかけない。新しいprivate親horizon/適格scopeは、093の完全proofが最初にFRESHを許可した時だけ作り、旧quiet PARTIALへ自動付与しない。同scopeの退役/FRESH/再回復でrenewせず、予約・実begin・complete0・独立将来prepも親以内へ制限する。finish/terminal/level切替・実MOVEDで撤回する。

## 検証と配布

新6methodで投影拡大/縮小、4方向の奥床、保護/金/局所面/不明・非zeroの拒否、旧ID/元窓・epoch・actual begin、expired PARTIALの独立将来権限、商品/取消/ACK_UNKNOWN/prefix/全予算を確認する。実装前のassertion Redを保持し、環境/型エラーをRedへ数えない。旧081/071/077/065の必要関連assertは変更せず、実runnerの同process/import順で実行する。未保持の未来画像で実機到達を合成しない。

変更はControllerとseal・093 entry/限定CI・文書。Runtime/Nav/Perception/UI/engine/API16/cap15/ABI/G1/R12はbyte保持。Runtime092の9＋旧1は過去証跡として結合し、今回再実行しない。単体/必要関連と独立差分レビュー1担当、IPA実build/実compiler/全Mach-O・全source同一性確認後に固定Releaseへ配布する。新しい実機の改善は未確認のまま、通常1-1ポーズから一連4回と全run ZIPを依頼する。
