# TEST066: 商店操作の予約維持とアイコン断片

2026-11-10（日本時間）。[計画](../plans/test066-shop-action.md)。TEST065の4run/67PNGは全SHA/bytes/896×414/CRC/manifest一致、全run resolved/terminal/drained。1回目自動全商品可視、2回目は下端2品のみ、3回目は人に3品可視/自動PARTIAL、4回目は未開扉で停止。実機商品可視と自動完了を分ける。

## 実画像と局所修正

4回目141→142は両FLOOR/GOODS_UNKNOWN・LEFT reason5 target(-1,0)/DOOR、全金/全保護/局所/strict BLOCKED不変。遠方(3,2)/(3,4)STONE→DIRTのみ。D前約35msで旧nextFLOOR条件から漏れて停止。新quietは同DOOR不変の入口1操作を保持し、校正/再予約/referenceのsafe_floorは拡げない。

2回目166→167は実入口通過済み、両PARTIAL・LEFT reason8 target(-1,0)/FLOOR、全金/保護/近傍/strict BLOCKED不変。遠方(5,2)STONE→DIRTのみ。新quietはentrance.valid1/両PARTIAL/reason8観測床・同全5fieldに限り同IDで保持する。入口の実証がない同形PARTIALは拒否する。

3回目143はポーズバー支持が11/12pxへ分断し、元13px opening後IoU.7764〜.7926<.8。既存13pxを優先し11px fallbackを追加。明度55/85・IoU.8・全参照/固定位置/全HUD/continue・death条件は維持。原画67before/afterは143のみUNKNOWN→FLOOR/PARTIAL/beat有効、他66は全Scene bytes一致。修正後141/143の全tile/全保護/金/全5field/strict BLOCKEDが一致し同frameの別変化拒否なし。model/未来応答の完全再生ではない。圧縮と描画の寄与を個別に特定したと断定しない。

## TDD・独立レビュー

新door6は旧Cで12semantic failures/errors0/1.730秒、修正後6Green1.907秒。全4方向×UNKNOWN/PARTIAL・遠方揺れ3回の元ID/全command bytes/時刻/回復状態保持→ACK開扉door1/moves不変→別entryACK→MOVEDを確認。

新shop4は旧Cで7semantic failures/errors0、修正後4Green1.855秒。全4方向・同5field/厳密motion・局所/金/保護/item/goods/signature/期限/owner/lock/前面/取消/不安定prefixを検査。独立レビューP2のpre-entry負例を既存negative内へpublic ACK+MOVED系列で追加し、4methodを保持してGreen4/4（1.767秒）。入口未通過・開扉0・両PARTIAL reason8・同全5field・遠方STONE→DIRTでも旧IDを拒否する。

新icon6は旧Perceptionで5semantic failures/errors0/.505秒、正式Cで6Green.572秒。public template由来のprocedural分断/短字、元明度境界、片バー/消失/白領域/8〜10px短字/色、他HUD/死亡/PAUSE優先/固定位置を検査。raw cropをGitへ混入していない。rootの新icon6+既存state guardは7Green1.158秒、新shop4+door6+旧gate6は16Green5.611秒。独立レビュー新16Green4.312秒、最終P0/P1/P2指摘なし。

## CI選択・同一性

新16+064gate6+065pending4+ABI1+Perception公開4=31、selector3で34method。新fixtureの自前COREと元Perception fixture双方をpatched sourceへ束縛。旧064初歩・広いcadence/Controller/Runtime/world/Kit/client/publisher・private原画はCIへ累積せず、必要な公開syntheticだけ既存期待を維持する。選択理由と未実施をhost metadataへ記録し、22source/ABI/0skip/errorを実IPAへ結ぶ。YAML/publisher不変、native_change_scopeはbaseline20aの22hashから2assetだけの変更を検査。

Controller SHA `c98427f2acd3c636bff080de0feae91d7096d9a59656934cbb69b913745aee2b`、Perception SHA `f0b3d6b4213820a6b82520a77628263e50677a5c5e59c9db4a4e4f9126a3457c`、manifest SHA `90013ef1425cae2a97b1bbfc1b366462d6e3bcfda65b984dfc80c35be55a97aa`。他20source/API15/cap13/ABI/client v14/R12原40/G1は不変。Mac/実IPA/実compiler/全Mach-O/完全sourceの結果を配布前に追記する。

ユーザーの現速度の暫定許容を記録し、今回は停止と商品確認を優先。送信済み23操作は20MOVED+3開扉で失敗0だが、VISUAL_PHASE/未送信期限切れ/遅い確認による空拍はあり、ゲーム受信時刻なしで完全同期とは言わない。TEST066の実機成功は未確認。


## 最終Mac102・実配布物

code `d16367570d12456c668648584253d721880b9e41`、[Mac102](https://github.com/shuhei0720/necrogold-automation/actions/runs/42774588299) device成功。新IPA/build102（0.3.4/top.ebato.loopctrl）、17,582,349bytes/SHA `080acc55eb847baaf1ea3a9db53a6b89fe7d94ec00dff50acecaeb9052f550c5`。外ZIP17,841,613bytes/SHA `6d709ee956db989d402a22866d9da07bb5f04357d8a0ca1817947289e51ddec0`。標準macos-26で同じビルドの完了を待ち、追加全体試験や再ビルドはしていない。

host34の全実行ID/生ログ/command/0fail/error/skip/xfailと選択/省略理由、ABI実query、22seal前後が実IPA sourceと一致。baseline20aからController/Perceptionだけ変更、他20source/R12原40/G1不変。実4C/5Swift/6RSP/PBX/raw compiler引数が一致、Perception/Nav strictO2・Controller/BeatO0・SwiftOnone/HOST macroなし。全9Mach-Oで従来102+066の計103marker非混入を確認。

build-sourceは全498tracked bytes/path/CRC一致、7,343,564bytes/SHA `ec0a759b2ea72b07d662895cf0cf1e0ddbbd63f7ffdb01cc37b417c342fdbecc`。最終sourceとの差分を文書3件に限定して検査し、固定Releaseのsource.zip/SHA256SUMSへ保存する。生ZIP/画像/ログ/receiptはGit外。固定公開後は匿名GETとSHAで両assetを確認する。

[配布/実機手順](../status.md)の新IPA更新・再起動・Start ServerからTEST066を依頼し、`runtime/test-066`全ZIPを返してもらう。未収録の先の商品可視やTEST066実機の成功を合成単体・CIの成功から断定しない。今回も商品確認までの到達率を主指標にする。
