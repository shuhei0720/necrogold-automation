# TEST081 独立レビュー

2026-11-11（日本時間）。独立レビュワー1名が設計・境界/異常系・安全運用を確認する。通常修正として同じ1名が計画と最終差分/実ログを確認し、形式的な3担当/複数周は追加しない。

## 計画レビュー

対象は baseline `acf684bd0eb7b73ac5239e02f0879f9474470b35` と [TEST081計画](../plans/test081-batch-stops-evidence.md)。製品変更前。AGENTS/status/context、要件正本、開発フロー、architecture/testing/review規則、native-control/passage-approach契約、Navの既079/080境界、Controllerのquiet/refresh/商品優先、Runtimeのcache/pin/priority/export経路を静的に確認した。製品・試験の編集/実行は行っていない。raw/Sceneの全件照合や実機成立は本レビューの証明範囲外。

**実装着手GO。P0/P1/P2指摘なし。** 六runで確認した三停止原因と証拠保持をまとめ、原因未確定の初期見逃しを別に扱うscopeは要件に整合する。各境界の公開assertion Red→最小Green、Dのみ標準Macのtest-only Redを先行させる順序も妥当。

- Aは旧判定後UNKNOWNだけに独立したAND証拠を追加し、旧079/080のscope・閾値・全73/unique9・商品保護・実unitを保持する。MOVEDを開扉/入店のcreditへ流用しない。
- Bは正式refreshの閉門3ahead/target2分岐だけ。固定正式anchorから最新へ直接strict0を確認する計画で、元beforeのquiet救済や隣接frameの0の推移を使わない。旧reason8等は拡張しない。
- Cは同方向DOOR_OPENED ACK後の未入店UP床進入票だけ。上端y=-5かつimmutable sourceのprotected内だけを隔離し、現在保護は元集合の部分集合、新保護/境界外gold消失/near差を拒否する。元票/before/元保護supersetを維持し、Scene/画素の偽正規化を行わず、mask0復帰でも同資格・clock・strict0を一度検査して共有する計画を確認した。
- Dは既initial枠の一度だけの置換で、current未送信PAUSE/sourceの正当性、stable current-prefix/generation/非inflight、owner/取消を守る。cache(false/true)双方のpin前保存、旧初期imageへの追加strong referenceなし、terminal/found/最新比較の順序と20pin/4MiBを維持する。初期原画欠落の修正を候補見逃しの修正と呼ばない。

最終差分では上記の実装一致、Cの保護候補/source不変とmask0、Bの固定anchor、Dの両cache経路・ロック/世代/取消・一度だけ/欠落source・retention予算を重点確認する。各Redはcompile失敗でなくassertion失敗、Green/関連回帰と実sealed source/IPAの対応を実ログで確認する。最終判定および実機受入は未実施。

## D改訂の計画確認

ユーザーの「初回に見逃すってことはどこで見逃すかわからん」を反映した計画5/6/7/8節とheaderの改訂を、同じ独立レビュワーが確認した。上のD first-only判定/条件は本節で置き換える。A/B/Cの既GOは不変。新Runtime/client製品適用前の計画確認であり、製品・試験の編集/実行やRed/Greenの重複実行は行っていない。

**D改訂も実装着手GO。P0/P1なし。P2文書追従1件は最終差分の工程で確認する。**

- 全mapの正常未送信negative PAUSE判断をrestarts 0…11の同index最新sourceとして残す。Controllerはrestarts>=12で正常見送りPAUSEの前にLIMITへ移るため、この上限は既予算に対応する。以前の取消判断はevent/referenceを保ち、画像のmissing/omittedを隠さない。
- 12判断＋既terminal/found/最新比較最大7は重複除去して19枠、dispatch sourceの一時pinを含め20枠内に収められる。source置換/旧bootstrap参照解放/既critical優先を要求し、run.lock→Runtime.lockの逆順や追加C/AX/同期PNG生成を持ち込まない。
- 新profile `normal-1-1-evidence-v2` だけ最大20PNG/各512KiB/合計10MiB・paged-onlyとし、default/明示bulkを拒否する。v1のretention/priority/4MiB/legacy+pagedを不変にするので、暗号plaintext8MiB/HTTP12MiBを広げる必要はない。
- API16据置でcap15を追加しcap14を維持する。runのimmutable profileと応答profileを一致させ、clientはrevision16の信頼mappingからprofile2/10MiBを選ぶ。wire自己申告のprofile/totalで予算を増やさない。started旧journalは元UUID/API/profile1/4MiBの読取回収だけ、未started旧journalは同UUIDでrevision/profileを対で移行する。
- 固定旧Runtime/合法v1入力でmulti-map evictionのassertion Redを先行させ、v2 Green/別v1互換caseとの入力差を明記する。旧first-only Red132を新仕様の根拠に流用しない。専用fixture/checker、client8methodsとcap/package境界はこの証明範囲に対応し、模擬保存の成立をゲーム到達/見逃し解消へ読み替えない。

P2: [native-control.md](../contracts/native-control.md) §12/13と冒頭は現時点でv15/cap14/合計4MiB・080以外不変の記述が残る。新profileの合法な10MiB回収を契約違反と読めるため、最終文書工程でv1維持とv16/cap15/v2限定例外を追記する。担当はroot、最終差分確認で解消を確認する。新しい条件/予算自体は計画5節が明示しており、製品適用のブロックではない。

## 最終差分の静的レビュー

2026-11-11（日本時間）。同じ1名が baseline からの製品/試験/計画/契約/配布経路の差分と作者の実ログを確認した。レビュー側で製品・試験の編集/実行は行っていない。

**静的レビュー完了。残P0/P1/P2なし。** この時点の最終Mac保存Green6・旧070 Red1/Green6・実compiler/IPA/host CIは未実施であり、成功とは扱わない。code commit後の実結果/同一性は同じ担当が確認し、rootが主レビューのclosing記録へ反映する。iPhone受入も未実施。

確認した製品SHA256は Nav `ff3aa8ae932a39df75d6bc495b26ad9ab5ebcfbb11f2a1f0eb1747bf7d7fe3ef`、Controller `393180c768d84a3f684a69748bc98651959fab2e2c2742bea425e6e9a18fc60f`、Runtime `048a462811edabbef4544b2b83ffaadcedbdc654d8675fad4143a6432bc299da`、client `d3dc2493b4ca34ceffbeedbb8d429f13734aa24f2eea53af70f95c53efc520f9`。patch/RPC cap15追加・apply/verify・新profile試験はclient freeze inventoryと一致した。

- Aは追加3helper/末尾call以外の旧Nav全文不変の証跡、公開4方向×両側門×O0/strict O2の意味Red16、最初の新8Greenと変更主methodだけのGreenを確認。後続Navの期待reason8への訂正は旧通常plannerとのfull5field一致が根拠で、実unitの期待を緩めていない。旧全73/079/080閾値とscopeを維持する。
- BはSTONE差がある追加分岐だけ、正式immutable anchor→latestのstrict BLOCKEDを直接ANDし、既previous→latest検査も残す。近傍/full5/金/保護材質の保持と元refresh回数/期限/未来準備を確認。公開Red4方向、新6methodsのGreen履歴とfixture geometry訂正methodだけの再実行を確認した。
- Cはsource保護集合の部分集合、top y=-5限定、境界外全tile/保護と直前accepted GOLD保持、同observeのquiet結果共有、before/元票不変を確認した。静的レビューで下記P1を発見し、必要差分だけの修正確認を行った。
- Dは両cache経路でpin前に同helperを通り、current未送信negative PAUSEとsourceのowner/cancel/generation/current-prefix/非inflightを検査する。map ID集合以外のRGBA枠追加なし、同indexの置換/initial参照解放、critical7＋12判断と20pin/重複除去が整合する。v1は旧priority/4MiB/legacy+paged、v2だけimmutable profile/10MiB/paged-onlyとし、current/historicalのprofile変更/bulkを拒否する。run.lockからRuntime.lockへ逆順取得しない。
- clientはrevision16→API16/profile2/10MiB、旧1…15→各旧API/profile1/4MiBを信頼mappingで固定する。wire profile/totalから予算を広げず、started旧journalは同UUIDの読取回収のみで新start/新cap要求なし、未startedだけrevision/profileを対で移行する。protocol/validation/test069不変、chunk/cursor/hash/原本/ZIPの検証を維持する。client8Green/旧選択20Green/package2Green、bulk-v2拒否の追加意味Red→該当method Greenを確認。
- workflow/新host selectorは最終sealed 4source変更/他18不変、ABI、client/validatorの実binding、baseline fixture override拒否と明示method inventoryを検査する構成。全Runtime/worldを増やしていない。新Mac Red133は旧Runtime hash/固定fixture hash/API artifact/compile成功/return1/期待assertion1/stderr空の記録を確認した。旧first-only Red132は新仕様の証明に含めない。

P1（解消済）: Controller observeの旧 `32f751…` は、top ITEM→UNKNOWN/保護縮小を受理した後、元sourceへmask0復帰した場合に、直前GOLD消失がなければ計算済みquiet=falseを消費しなかった。UNKNOWN署名や元期限超過でも同じ未送信票が残り、計画のmask0 strict0/clock条件に反した。現在は対象clipped_entry・mask0・quiet=falseを必ずSCREEN退役するguardを追加。公開negative methodへ非GOLDのUNKNOWN署名/期限超過2subcasesを追加し、旧製品でcompile成功/assertionFAIL2→修正methodだけGreenを確認した。元票/source/時刻は変更しない。最終C試験SHAは `c7e526cad0a87ab912c0de1fa738a7797877f2d8d7b0c2c953be32849429ecb8`。

P2（解消済）: native-control冒頭/§12/13に081限定差分とv1維持/v16-cap15-v2条件が追記され、旧4MiBだけと読める矛盾は解消した。静的/模擬保存の成立を実機の商品到達・候補見逃し解消へ読み替える記述もない。
