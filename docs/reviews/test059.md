# TEST059 レビュー・検証

2026-11-09（日本時間）。[計画](../plans/test059-next-slot.md)。TEST058はLEFT2/MOVED2後に未予約の次slotが空窓となり停止し、商品未達。原ZIP/12PNG/reportはGit外。

## 計画と期待値

fresh計画第1周は安全clear、設計/網羅は未予約中の追加HUDでtargetだけが再更新される曖昧さをP1、網羅は旧期待2箇所の明記をP1、新world表示時刻の未固定をP2として指摘。第2周でcandidateの対更新→初回reserve凍結を明記し、親/既存ticket不変を保持。旧controller期待はcontinuous HUD refreshとinitial replanの子deadline2箇所だけを変更。新しい位相worldは作らず、実C合成HUD境界＋既存world16の無変更回帰に限定した。3担当ともP0/P1/P2なし。

## TDDとlocal回帰

固定旧Cはhandoff `f65c45d5963eb6440bca02604b164cbb670b90b9`、SHA `61df3ba3edceadc1eb76114485ce836edbb2b90ac327bb119decb74760b3c47f`。旧153件Green後、公開Cの実ACK/translated MOVEDと合成HUD差を与える新testを先に追加し、compile成功・1failure/errors0/skip0・指定assertion Redを確認した。次targetが+13.436191ms補正され、親motion期限に299.999998ms残るのに子予約がlateとなる同型で、欠落した実機未来画像の再生ではない。

`update_next_slot_candidate` の最小実装後Green。Controller.cだけを変更し、未予約/input0/pendingなし・同nominal/元period・8%/算術拒否の下でtarget/deadlineを対更新する。親motionと予約済み/SAME/FRESHの窓は変更しない。新12件は正逆位相、複数observe/非累積、10ms/+1ns、8%/+1ns、overflow/underflowのatomic拒否、state/pending/sticky、親motion期限、予約後HUD/reissue、child失効/no次拍探索、ACK/UNKNOWNを検査。旧153＋新12＝165件、32.018秒、errors0/skip0で成功。旧test削除0、旧assert変更は計画の2子deadlineだけ。

app C profile（Controller/Beat O0・Nav/Perception strict O2）の7variationもGreen。公開CI用 `check_next_slot.py` は同じpublic C testを固定旧C/current/旧式rollbackへ適用し、Red/Green/Redを確認する。compile/setup/error/skipはRedとして受理しない。新rollback1件は旧Runtime59＋TEST058の2件と別集計。

他native/evaluator99件・189必須paths/skip0、package228件成功（同期helper追加後）。合計native/evaluator264件。原058の12PNGは全Scene O0/strictO2/Pillow、Nav/Motion/全73scoreを照合。40→47・47→54 LEFT MOVED、46/53 UNKNOWN、cap54の未実行DOWN/FLOORを分けた。完全ZIPのstrict評価は整合pass・商品到達fail/exit1。既知runを未知評価へ数えない。CI private除外は28methodの厳密集合、公開対象は236件。

## 独立実装レビューと配布前

設計/網羅/安全のfresh実装第1周は静的追加P0/P1/P2なし。source C SHA `b3fe3644eb5d3041f18bafa1771186e5a1e091c99e55468f7ccf73d28d2e0a08`、manifest SHA `fd95ed27d135c58ebd8872c6c9611a2c41913db3b4e4808bc4b7c9e197543190`。22seal中Controller.cのみ変更、他21・R12原40/G1は維持する。

client v13/API1.98.14/cap12は不変で、client CI19の197件が成功。Macの全旧59/Raster3/C parity-field/実RPC・実compiler・新IPAの最終検証は実行中。native変更のため新IPAをビルドしてからTEST059実機を依頼する。iPhoneの商品到達・毎拍・人より速い性能は未受入。


## Macの同期補足と最終run

Mac85は公開native236件/private28除外と、新Cの固定旧Red/current Green/rollback Redが成功した後、既存TEST058 direct_due fixtureの時刻assertで失敗。実第3入力は元D内だったが、境界前に取得済みの旧capture40が意図した新41より先にC observeへ入り、armedな時刻をD−7.017107msで記録した。これは5.017107ms予算の試験設定と不一致で、成功扱いしない。

同期修正はHOST fixtureのみ。境界で1captureだけ許可し、expectedObserveEndに達したhookだけを記録、実replacement source rowのobserve_endと一致するassertも追加した。既存全assert・残余5,017,107ns・AX11,311,875nsは保持。固定旧d936 fixtureは元hash `1d17bcf7a5c4c3b0eca981de7cb6f161827fcfbbcbb71be180cfdf952f5f2c10` 検査後に同じ同期を挿入し、実行hash `cbcca005f3a8a3d1ce8c93a0f95b3e2b1e358a4ee37a43e23e80f7a2ae9b539a` を別記録。逆除去すると元bytesへ完全復元できる。production/Runtime/sealは不変、3担当が同059第1周の補足でclear。

[Mac86重点回帰](https://github.com/shuhei0720/necrogold-automation/actions/runs/42602660535)は固定旧Red・current15/identity/chain/pressure・058新2故障・world16・旧Runtime全Greenが成功。3担当が原artifact（203,262bytes/SHA `f23a448e485967372dbd7217ad4bc0f9f79370bb30cc885603122c2b4464b247`）とsource/fixtureの同一性を照合した。

[最終Mac87](https://github.com/shuhei0720/necrogold-automation/actions/runs/42603972916)はcode `96c0596a4b7fcad401eb41ceae928af13752ead8` を対象に実行中。build-source ZIP455全tracked bytes/CRC/path一致、SHA `0149ce97e5f8a0bd432a41d80556eb4d9d321c9344ad730a82147010ded78874`。実compiler/IPA・配布用最終sourceの同一性は完了後に追記する。合成GreenはiPhone到達の受入ではない。
