# TEST085受領とTEST086

2026-11-12（クライアント日本時間）。[計画](../plans/test086-vantage-gold.md)・[独立レビュー](test086-independent.md)。基準 `843d401ecaff22607063bd4fad744aefc8ec51f5`、TEST085/build144。raw/ログ/SceneはGit外 `received085` / `test086-*`。

## 実機結果と受領

started_ns順。添付表示順の2・3は実順と逆だった。

| 実順 | run先頭 | 終了 | inputs/moves/restarts | 原画の結果 |
| --- | --- | --- | --- | --- |
| 1 | 10554662 | LIMIT14 | 0/0/12 | 候補093を見送り、商品未到達 |
| 2 | c4817849 | GOODS1 | 8/6/1 | 全3商品・価格8/100/75可視 |
| 3 | 6a0429bf | GOODS1 | 7/5/2 | 全3商品・価格150/50/375可視 |
| 4 | 153e6565 | MOVEMENT10 | 3/2/1 | 実画面でUP1と整合するが移動確認UNKNOWNで停止 |

4ZIP/80PNG・18,473,950画像Bを現API16閉schema/client_load・ZIP/PNG chunk CRC/SHA/PIL/896×414/export全offset・prefix/cursor/test069実publication gateへ全照合。全paused/terminal/drained/回収完了、選択native行欠損0。見送り判断source16/16は既知見逃し093を含み、正常negative16件とはしない。omitted582/省略参照52で全取得保存ではない。監査receipt3758B/SHA `0cb4e751afe89380f0e63fef7cb97eebe0e8e948bc84d28db04f3847673a4d41`。085再実行/追加回収不要。

監査担当が実2原212と実3原218で商品3点を視認しnative GOODS2/4と一致。対象識別/通知の受入とは分ける。成功2runの入力開始間隔はそれぞれ511.9–524.2ms/517.1–529.7ms。2拍ごとの送信はないが、各入力が物理的毎拍へ受理されたことや人超え達成は証明しない。

共通Sceneは現8sourceとの一致を確認したTEST085 final C4 library `08d2fc652fde7eefb03311284d25c7a1dc60d710c926e3733975ecf1b2fbc384`を再利用して80原画を一度export。調査用再compileは行っていない。

## A: 見逃した角通路へ既知床だけで近づく

原093の左口(-3,-2)/外(-4,-2)はFLOOR・両flankDIRT、内側(-2,-2)はUNKNOWN。初FLOOR88から200.947250ms経過後のPAUSE判断sourceであり、元200ms描画待ち不足ではない。inboard full中央値2/0/1・黒450/625、lower非黒175/325も中央値6/4/4で、明るい床の色witnessはない。PerceptionのUNKNOWNを床へ書き換えず、上の黒い口を根拠にしない。

上/左の固定10口中k=±2の4cornerだけ、観測口/外床・両脇壁・同初期壁列3支持・金なし・元protected cross/材質/経路条件に加え、内側UNKNOWNのroom内側接線endpointまで観測FLOORの旧最短BFS3がある場合に候補を保持する。元chooserは原093でLEFT/reason10/goal(-2,-1)/path3。未知cell/扉/商品へ踏み込まず、観測不能は元有限wait/NO_PATHを保持する。旧10bitと既分岐/chooser/Controller/Perceptionは不変。

新A6は有効な公開Scene/元UNKNOWN/口外両壁/chooser path3/source不変を先assertしたO0/strictO2意味Red→初回6Green。4corner、経路3/迂回5/不在、保護/金/商品/invalid、旧10口不変、公開Nav各step実FLOOR・UNKNOWN手前保持を確認。新Controller結合は増やさず、同bytesの旧bit-admission/finite-budget/UNKNOWN関連exact CIを選ぶ。同じ独立担当が範囲にGO、旧単体local再実行0。

## B: 金壁1枚を維持した一歩の確認

実4cmd6 UPのbeginは元10ms窓内、ACK成功。適格原100–106/110の8枚で旧15段全UNKNOWN、最後commitにも元visualPは約1.903秒残る。authority92→110で地形が画面下36px動き実UP1と整合する。ACKを歩行成功に読み替えない。GOLD1→1・旧STONE3全保持・旧DIRT19中16保持/非共線10・9translation一意camera(0,+1)。旧083は0→1、旧085zeroは金候補外のため、この1→1は既proofの対象外だった。

旧15段の順序/閾値と全Controller期限/予算を維持し、最後UNKNOWNだけへ単金保持のunit-only ANDを追加する。金1→1、扉/商品/保護なし、origin/次床、全旧STONE最低2/非共線DIRT9/一意geometry、raw73全finite/expected9px最良/score>.45/gap≥.08、元independent_phase、worldblur95%/300/両帯100、axis52 75%/300/両帯100・両全73の元texture_lead15ppを要求する。停止/開通/入店creditやUNKNOWN再送・新予算は増やさない。

原101はraw .548093498/runner .831152607/gap .283059109・blur611/28bad/帯368/243・axis613/72bad/帯485/128で成立。原100は強度/位相不足、102–106はblur競合差不足を維持、110も成立するので受理する。frame番号は製品条件にしない。旧081実5は金1→2/newDOOR/STONE欠損で新対象外・未解決を保持する。

作者単体最終結果、source固定・保持原画校正・seal/選択CI/実IPA/公開GETは後続記録へ結合する。新実機到達率、恒久毎拍/人超え、対象識別/通知/対象なし循環は未受入。

## 作者B・最終source/保持原画

Bは旧Nav27fa…から公開Motionの必要MOVEDに対し全15段UNKNOWNとなる16subcase（4方向×2金位置×O0/strictO2）で有効Red、構築エラー0。新6は初回成功3＋訂正した3だけ再確認して全Green。訂正は既ng2_entered_gateの非入店return0/valid0、PAUSE enum2、再利用083 isolated component2に対する元independent_phase=trueの期待だけ。単金proof/閾値/要求MOVEDは変更せず、失敗logも保存。公開Controller結合は同ACK/prefix・earliest直前無credit→適格画像のunit1・再観測無再credit・旧票/元P/10ms窓保持・次票/GOODS優先を確認。

B testSHA `d5c3880e1e10d0a2d9851bbb0bec9d4a4387a8460847b1e0f67341ebb207d367`、A testSHA `1eae5be8b3a3ad5fa1d8337fdf538cdc6669a31af5b372491b24ace76f3c6096`。新B HOST guarded Cは新export5＋旧083再利用7（export6/static1）の計12。製品static helperと区別し、全宣言coverageを実MachO検査へ渡す。作者旧semantic local0。

finalNav `3e428bec78cf0b530252a9d6c2032ed59054515cbc0d6f5ef2321498b430afd8`、Controller/Beat/Perception他7C/Hは元085と一致。新helper2/call2以外の全旧Nav bytes、旧15段の本文/順序を維持。root最終C4を一度compileしlibrary `b53f3dffff7dfa9d35e357692c97a1168bd0875efe046ff0c7be3904642bfdad`へ固定。

原417画像（08197/08280/08380/08480/08580）のScene全bytes同一。候補差は原085093だけ0→32、旧候補bit欠落0。保守的stable ACK-prefix/元earliest以後/native終了前/source+3秒以内の213pixel組は旧known134全維持。UNKNOWN→UP1が08592→101/110と083da1051fd100→112の3組。rootと独立担当は083原100/112も視認し、同じ地形が画面下36px移りUP1と整合することを確認。112には新露出の扉状画素も見える。DOOR0という資格はScene分類値であり、原画に扉が存在しないとは主張しない。unit確認は開扉/入店creditを追加しない。085全適格8枚では100/102–106のUNKNOWNを保つ。校正であり私的visualDや欠落future frame/新iPhone継続成功を再構成しない。比較JSON SHA `2bbc2dda20d5fa19a3b09258174ade4dc9ee7a1852c7a20be5cc616450a00e11`。rootも085原212/218の3商品を視認した。

fresh pinned Git/G1→seal/applyを一度実施、9既存＋13追加=22中Nav1変更21不変、manifest `a6567aa71c033c86ea6d94df190401dfa220ea338c2a0feb13784f3556e9cd2d`。全applied hash/Runtime/G1/core4同bytes。rootのmetadata集計が追加13だけを22と誤期待したassertは合計22へ訂正、構築/適用は再実行0・製品変更0。限定CI/実物と公開GETは後続。
