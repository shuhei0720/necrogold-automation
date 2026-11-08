# TEST055 検証・独立レビュー

2026-11-09（日本時間）。正本: [8項目計画](../plans/test055-latest-plan.md)。挙動不変のcontext整理は [別工程](context-refactor.md) で完了しており、本記録は新しい挙動修正に対応する。

## 計画レビュー

freshな設計・網羅・安全の3観点で実施。設計/網羅第1周はP0/P1/P2なし。安全第1周のP2「旧v12 clientの新規起動と、新v13が旧v12 literal journalを読む回復の混同」は、後者だけを互換範囲としTEST055新source/launcher必須と明記して修正した。安全第2周は残P0/P1/P2なし。start RPCへ新パラメータは追加せず、旧実行ファイルのfresh互換を主張しない。

レビューで重点確認した条件は、source/最新Decisionを一度の証明として扱うこと、全230セルの保守的な分類更新、GOLD/STONE/DOOR/保護の不変、元の全期限/共有予算、最新direction/x/y、FRESH→SAMEの旧方向逆戻り防止、optional reference失格、旧callback実return/AX lease、旧literal回復、実記録のgoalと欠落/未収録の分離である。

## 実装前Red

旧Cで実画像69/70と実位置/visits/入口を使い、旧UP不送信・最新LEFT/DIRT予約の主2assertion failures/0errorsを観測後に変更した。model/HUD/lead-inは明示的な合成であり、完全な実機時系列再生とは呼ばない。clientは旧190件が成功したまま新3assertion failures/0errors、評価器は読込可能stubからgoal failの1assertion Red、packageは新cap/profileの2assertion Redを先に観測した。

## 実装・ホスト確認

- Controllerは旧119＋新23の142件、28.493秒、skip0。旧SAME/reason8・安全条件を維持し、合法FRESHへ変わる旧5methodsの期待を根拠付きで更新した。全ケースを保持。環境復帰で重複していたhelper定義は12状態のScene全bytes/方向delta一致を確認し、同値な後方定義1個だけを除去した。
- 全152必須画像pathを含むnativeと評価器は229件/112.152秒、skip0。内訳はC/画像/拍/Controller/Raster207＋評価器22。CIと同じ選択もlocalで208件/46.960秒、private21を名前で明示除外して成功した。実画像の不足/hash不一致はlocal失敗のまま。
- client197件/51.831秒、公開[CI42500150606](https://github.com/shuhei0720/necrogold-automation/actions/runs/42500150606)も197件/47.672秒で成功。literal v12の同UUID・GET0/start0・4chunk回復とmotion traceを維持。package/compiler監査208件/1.588秒成功。
- 評価器の実TEST054はintegrity passだが `goods_visible_and_paused=fail`/exit1。原PNG/HUD/時刻を変えず、60→68UNKNOWN、60→69DOWN MOVED、69→70BLOCKEDとUP/FLOOR→LEFT/DIRTを確認。54画像/初期model履歴が不足し、完全Controller再生=false、LEFT後はnot_recorded。元ZIPを成功へ読み替えない。
- native22seal `3812b22751076748cf7ce868fc774efe6ce95c5846c84e8406900c2b21cc2be5` を実適用して照合。変更はController C/header・RPC cap広告・RPC試験だけ。production Runtime/他native18・G1/R12は不変。C SHA `bea121f49d85c6fedcdd5c08182d4a2b5e5affd4e8fdaf33bde6f7c181202de1`。

## 実装レビュー第1〜2周

fresh3観点で実施。固定C/header/client/fixture/helperの第1周にP0/P1/P2なし。評価器第1周の安全P1「active/report比較のPython等価性でreportだけtrue/1.0にした不正型をpass」、P2「result_metadata=[]/nullの未捕捉AttributeError/exit1」を、新2methods/4assertion failures/0errorsで再現した。raw active/report同一bytesの検査とmetadata dict入口検査で修正し、元20＋新2の22件がGreen。第2周は全3観点P0/P1/P2残件なし。実Mac配布物補足は同じ第2周の未完了工程とする。

旧55 named faultsを保ち新FRESH無効/旧direction再利用の2実C故障を加え57予定。旧target-drift-after-actionは故障本体を変えず、FRESHが正当に再予約するため既存のSAME validation2/counterを検査するdetail assertionへ期待名を更新した。旧progress assertionも保持。Linux実Cでnormal2→同故障12、pending故障の不送信を確認した。old/new snippet・source hash・stageの静的57集合はGit外に保存。Swift実行成功の代用にはしない。

## 最終Mac・実配布物の検証

code `4eb44648b673ada10a878a6e8753cb53e75e9678` / [CI42503501049](https://github.com/shuhei0720/necrogold-automation/actions/runs/42503501049) / IPA build72。Runtime57 named faults（旧55＋新2）、Raster3、両C O0-only対strictO2/field故障、LoopCtrlKitと実暗号RPCのowner-callsite故障検出、実compiler/IPAを確認した。実PBX/raw log/6responsefilesはPerception/Navigation strictO2、Beat/ControllerO0、Swift5Ononeへ結び付けた。

IPA ZIPは17,793,378bytes/SHA `f760348b6e24582205e652504b8bf3ee7bc61c0a0cfb053f923a71e7497fc0b8`、内部IPA SHA `c9eae0e8524ca8d8aa4d5efbb24f5db732b80d75989fb91d93b93c920da63c84`。検証ZIPは440,811bytes/SHA `14fbc73e86fe0a474cd1d1070e887381de775ec9b9da6ff4404601ef244f34c1`。全22seal、全9Mach-OのHOST/fixture/spy非混入、実app/runner API/capを確認した。

実producerの旧reference3report SHA `08e0fc15648ae38aefa0b170a778068129dcbe81d140adf4fc796a4643cb06b4` と新FRESH2report SHA `f26cb788d581d19b5b49c477ac571f0e1b12b1e1a40393e8891dd821b8c56c89` は同じ最終artifactへ結合した。旧3件はstdoutの全値/型と保存JSON digestを確認し、新2件はstdout各JSON objectの元bytesも一致する。新v13へ実暗号HTTPで渡し、motion_references/scene_changes/scene_change_detailsとactive/report両journalの型を含む一致を確認した。外側RPC状態・画像はfixtureであり、診断接続の検証である。

同じ実装第2周の補足として、独立した設計・網羅・安全の3担当が実物と全sourceを確認し、残P0/P1/P2なし。codeから既知5資料だけを更新した `ee30c48857631a719e754c68559e62fa789976c4` の完全ZIPは、全435tracked filesのbytes/CRC/path/重複が一致した。実57故障・compiler・22seal・9Mach-O・旧3/新2producer・実暗号HTTPへの診断接続も独立照合し、後者は別担当でも再実行した。生証拠はGit外に保存した。

実装/配布物レビューはclose。Mac実ゲーム/iPhoneの新TEST055・毎拍/速度/商品/周回の受入は未完了であり、具体的な新IPA/source更新・実機依頼・終了後の全runtime ZIP返却を台帳へ保存済み。
