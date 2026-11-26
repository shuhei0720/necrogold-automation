# TEST123: TEST122実機の成功1件と停止4件を比較して修正する

2026-11-26（日本時間）。基準はTEST122/build272、CODE `f5143e339a1e6efddb3c24a69dbea163fd1007de`、保存HEAD `c7e0944`。Cff4d9531/Ring426c19d2/Header7c067c31/Nav e0c43a71。[開発フロー](../development-flow.md)・[native契約](../contracts/native-control.md)・[修正表](../fix-records.md)に従い、実機の失敗条件に限定する。GitHub/標準Actions/新IPA・完全sourceの固定配布の既承認は継続し、保存の確認を繰り返さない。

## 原本・実順・成功

提出9ZIP/4campaign/5run・281member、120PNG/143記録を全照合。CRC/SHA、安全な一意path、全896×414 PNG decode/RGBA hash、metadata/記録鎖/hash seal/escrow、strict ledger/checkpoint source・clock/generation・元時刻、内包last-run ZIPの提出原本全bytes、回収complete/drainを確認。不足0。3inflight（f5a3/233、66c8/147、4a98/167）は原状態のまま保ち、安定117枚と混同しない。原ZIP/画像/Scene/report/個人情報はGit外。

実開始時刻と同Runtime/uptime非重複、campaign親子から、周1f5a3→周2root66c8→child b6cb→周3 636e→周4 4a98と結ぶ。添付順ではない。初回RS4/4、実unit5/5、開扉5/5、全商品可視はroot3/4＋child1/1＝4/5。商品後の実RSはroot1/3＋child0/1＝1/4、新floor/次childは1件ずつ。

66c8/source148/job2は正常完全NEGATIVE/policy15/layout1/failure0をC採用し、durable→実RS15/既知ACK→新floor168/169→b6cb/index1開始まで原記録と画像で確認した。末terminalのpacket nil/adopted falseは明示resetであり、先の採用成功を否定しない。新21の成功hitではなく、upper/halo/singletonの私的途中hitは未出力で通しの不使用も断言しない。5runの通常商品Scene31件/全6112B packetは旧121/出荷122で同値。返却ZIP単独のinstalled binary証明と、出荷artifact/source来歴は別に扱う。

Git外証跡: `test123-intake/receipt.json` SHAc727205a、独立 `test123-success/receipt.json` SHA59bce319/identity SHA4347fab1、正常商品校正 `test123-goods/normal-results.json`、制御 `test123-control/receipt.json` SHAe2be1fa4。未出力の過去job/private mode/counter/未来応答を補わない。

## 確定した境界

| 実順 | 原sourceと通常結果 | 拒否条件と修正範囲 |
| --- | --- | --- |
| 周1/f5a3 | 235/job3、正常UNKNOWN/incomplete、policy2・BOARD/ROWS258をD内採用→PAUSE ACK→durable→GOODS | 全3商品が見えるが、縦6pxの2aliasと、実full看板は非HUDなのに探索ROIだけ1px HUDへ重なる。実faceによる正のcanonical rowと全alias対象探索を分離する案を校正。234は既NEG9であり、未採用画像の過去借用と新証明を混ぜない |
| 周2/child b6cb | 106/job2、正常UNKNOWN/incomplete、policy9 END_CAP16をD内採用 | 右capのfull/lowerは正Floor、upperの色条件が不成立。旧UL/LR等にも不足があり、旧資格を先行保持した別の固定vertical完全被覆を校正。105/108は既NEG4。UNKNOWN106自体を直接NEGへ書き換えない |
| 周3/636e | 119/job1の正常safe PARTIAL UNKNOWNをD前74.658ms採用、current121でROUTE10停止、元P残2.539秒 | 上端の支持されたITEM投影と、旧GOLD railの穴1セルUNKNOWN→GOLDの同時露出。[限定した新PARTIAL DATA](test123-partial-top-wall.md)。新GOLD単独も旧guard対象外で、既正資格2件の単純ORではない |
| 周4/4a98 | 169/job2、正常UNKNOWN/incomplete、policy3 ROWS256をD内採用 | 同physical rowの横1px alias2件を行数で拒否。正canonical/同格子/全alias画像・名前unionを維持する別証明を校正 |

商品停止3件はすべて正常UNKNOWNが元D内に採用され、その後にPAUSE/耐久保存/停止している。未実行や単純なリスタート命令不発として修正しない。周3の最終kernelは後続cycle_failureの上書きで、producer status okと区別する。保持されたf5a3/b6cbの現在FULL比較は旧DATA pairで既成立し、新122 halo資格を要する差はない。私的caller履歴・残枠が未出力なので通しの適用可否まで捏造しない。

## 実装と確認

原因/原時刻/通常producer/拒否guardを先に固定し、短い計画→exact出荷122で意味あるassertion Red→最小Green/直接関連→独立差分レビュー1回→必要な実IPAと照合→次の実機とする。商品側は別短計画でnumeric representation/consumer/候補・HUD・alias・空白capの正の証明を確定するまで製品・正式試験を始めない。control計画は独立P0/P1なしを確認し、限定DATA資格の正式TDDをroot GOした。

旧正常NEG15の実RS成功、旧5成功packet、19/20/21の原画を保持する。全商品登録・宝箱の対象化・価格/名称必須化を追加せず、未観測やUNKNOWNを陰性へ変えない。候補/名前veto、全aliasの全5cell、両外側partial/tailの探索を保持する。新しい正capは全領域を固定分割で覆い、元floor/可視/bright/ink条件を緩めない。どのfieldが未使用/別証明を表すかを明示し、旧証明を偽装しない。

P/W/D、source150/worker100/input10ms、owner/世代/prefix、取消、UNKNOWN無再送、DATA2・一用・実return fence、初回RS/連続周回を保持。新controlは旧MOVE救済ではなく、新immutable通常PARTIAL jobと別current/fitの後だけ将来UPを認める。原未来の全商品画像/RSは再現しない。Runtime/Swift/Clock/API/POD/保護資産は変更しない予定で、変更境界が必要と判明した場合だけ計画へ追加する。

client123は122を継承し識別/capability/namespaceだけ追加、旧entry/shell/default/metadata bodyを保持。selector/host/Py39は新境界と直接関連のexact methodを選び、native作者の関連Green後に同じlocal全集合を重複実行せず、CODE固定の標準CIへまとめる。native変更時はseal/来歴/実compiler/全9MachO/CODE全Git blobを照合し、検証済みIPA・完全source・SHA表の固定3assetを匿名全取得する。

次の実機は通常1-1ポーズから初回RS→候補/通路→開扉→全商品確認→対象外の実RS→次周回を一連で依頼し、停止後の全run/campaign ZIPを返してもらう。商品到達/実RS/連続周回/毎拍・速度の受入は新返却まで未確認とする。
