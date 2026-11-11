# TEST082 独立レビュー

2026-11-12（日本時間）。TEST081とは別increment。独立レビュワー1名が設計・境界/異常系・安全運用を確認し、同じ担当が後の最終差分/実ログを確認する。

## 計画レビュー

対象は baseline `7d4f8f435ad54daca79a1ec89b04dfdc6d30e625` と [TEST082計画](../plans/test082-materials-motion.md)。製品/試験の編集前。AGENTS/status/context、要件・開発フロー、architecture/testing/review規則、native/通路契約、関係するPerceptionのtile→gate/wood→merchandise順、Navの旧074/075証明、Controllerのstationary wait/record_changeとGit外prototype/根拠記録を静的に確認した。レビュー側の製品・試験の編集/実行はない。

**実装着手GO。P0/P1/P2指摘なし。** 確認できた材質/無金unitの原因と、原因未確定箇所の診断追加を分けた局所scopeは要件に整合する。元入力権限/期限/予算/API/商品保持を変更する計画ではない。

- Aは旧DIRTだけを、旧paletteとGOLD/gate/wood処理後・merchandise前に原pixelの追加証拠で再検査する。brightの差1…77、STONEの差−76…0、半可視の固定上下割合、全witnessの元入口R≥6/G≥3とtexture、固定非重複2ROIを要求する。未知/HUD/木扉/金/既STONEを形だけで床に変換せず、後続の商品の認識/保護と既Navの観測床/近傍検査を通す設計を確認した。prototypeで見つかったfloor witness入口guard漏れは計画に禁止条件として反映済みで、最終公開negativeに含める。29変更セルの原画ラベルは校正資料として扱い、未知評価や全配置正解と呼ばない。
- Bは全旧Nav後UNKNOWN・無金/無商品/無保護だけ。有限high rawの同方向厳密unit、074の全旧STONE保持/非共線DIRT/unique9、075の左右独立phaseと21依存worldBlur/固定52帯/300・95%・各100・全73/15ppをANDする。旧関数/順序/閾値は維持し、両phase bandで有限unit/競合を確認してINF差をgapの根拠にしない。元phase bandに存在しない絶対score上限を変更したと誤記しない。MOVEDだけで開通/入店creditを作らず、次の入力は通常判断へ戻す。
- Cは未発行stationary OBSERVE/READYのSCREEN拒否直前だけの既record_change追加。退役済み未送信event、元before全bytes=固定anchor、world/安定prefix/独立ID・取得区間、pendingなし、真のmask非0を要し、実拒否箇所に対応する既validation/replan_allowed0を記録する。ISSUED/別anchor/入力済み/UNKNOWN送信/metadata・signature-only/mask0/期限拒否には偽行を作らず、元状態/票/権限/時計を維持する。既first1/latest2とRuntime比較優先の利用だけで保存予算を増やさない。

公開assertion Red→最小Greenと、Perceptionのpalette/gate/商品/fringe、Navの旧074/075/079…081、Controllerのstationary/保存schemaから選ぶ関連回帰は変更境界に対応する。実画像差分/nonTile bytesと旧known/UNKNOWN・Nav full5の比較、3source変更/他19・Runtime/client/API/cap/予算不変、今回実ビルドと過去Redを分けたsource/実compiler/IPA/固定Release照合を最終差分で確認する。全Runtime/worldの追加や同じ試験の重複実行は要求しない。

実5の金壁LEFT移動確認は証拠不足で未解決、実2の最初の拒否画像128/129と私的stateは欠落しており原因修正済みと扱わない。正常見送り18/18の判断画像保持を全取得画像保存とも呼ばない。5ZIP/97PNG全監査・商品到達1/5は受領記録に基づく事実であり、本静的レビューでの再実行/全件監査ではない。TEST082の実装・最終CI/IPA・iPhone受入はこの時点で未実施。

## 最終差分の静的レビュー

同じレビュワーが3製品・新公開試験・関連選択/薄い起動口・文書と作者の実ログを確認した。**静的最終GO、残P0/P1/P2なし。** 保持比較で発見したP1回帰は下記B2の限定修正と最終共通C4の再比較で解消を確認した。レビュー側の製品・試験編集/実行はない。code commit後のhost43/18scope、Mac保存fixture、実compiler/全MachO/全source/IPA/固定配布物、iPhone受入はこの時点で未実施として区別する。最終CI/成果物の実結果は後でmessageで確認し、rootが主レビューのclosingへ反映する。

製品SHA256は Perception `2818660c755078d24785b8ae7424de1b3c236a29a3eab5de21ce183075539dd2`、Nav `dce5f19e9efa38e390c1f71c4d82019ddcf339a395e6da58ed08388e1043c19e`、Controller `12d3a59a29ccd465c4e3983c637b2e8bf6cefa4c5ed166005be840b90d740250`。Runtime048a…とcore client4ファイルは081と同じbytes。

- Aは旧DIRT限定、gate/wood後・商品前、全floor witnessのR≥6/G≥3、固定非重複ROI、full/部分割合/元texture条件に計画どおり一致する。元Perception本文は追加helper/callを除くと旧bytesへ復元する。公開3positiveのcompile成功・意味Redから最小適用→新7Green、境界を追加した6methodsだけの再Greenを確認した。brightの77/78はR39…52/RGB8で実現できないため最近接の75許可/85拒否を使用し、STONE76/77、上側285/284と下側293/292、salt-black両側/共通quarter/低texture/旧palette/gate/HUD/alpha拒否を直接確認する試験である。原21の半可視口と外側UNKNOWN、原112の次床も独立に目視した。最終製品と同hashのGit外full public pipelineは97原画/26変更原画/29セルのみ・非tile bytes不変で、29原画ラベルは校正資料として結合されている。
- Bは旧UNKNOWN後だけのhelper/call追加、旧Nav全bytes復元の記録を確認した。raw全73の有限best/runner-up/high score/元gap/unit、074の全旧STONEと非共線DIRT/unique9、075の両phase有限unit/競合、21依存worldBlur/52帯/300・95%・帯100/全73・15ppをANDし、将来のnext床を過去unit証明へ要求しない。公開4方向×O0/strict O2の意味Red8→主method Green、残4methods Greenと訂正phase methodのみGreenを確認。`.6+.08-.6` が実浮動演算で`.08`未満になる期待誤記の訂正であり、製品の`>=.08`は不変。上側の最小表現差の許可と丸め下側の拒否を検査する。
- Cはmetadata/world拒否→motion呼出の元short-circuit順を維持し、OBSERVE/READY・input0・退役旧MOVE begin0/outcome3・pendingなし・元before全bytes=anchor・独立current-prefix/world一致・真mask非0だけを既record_changeへ渡す。実拒否箇所のROUTE10/MOTION11とsource/observedの対応は正しく、mask0/署名のみ/ISSUED/期限・非独立・既UNKNOWN送信から偽行を作らない。元event/票/credit/Recovery/MotionWait/MotionReferenceは不変。公開主Redは同じSCREEN/権限を満たした後の行数1対0の意味失敗、新3methodsのGreenと既parser2validator正例を確認した。残2fixtureを旧generic trigger行のあるshopから元の公開noGold passageへ直した訂正は、旧assertの削除や製品権限変更ではない。

新試験SHAは A `3880719e32a83303226d632f293bcb8253ee5bd2bb705c4431cfacb5a252f8f4`、B最終 `f9585ba8c5e1c54f8205722e492e92068a343fd8fb99d2242eeb9450438bf099`、C `1edd1f401872745a8e4d4fa45602839df85c9ecb44f4d7d0eaba4dd65abc8e07`。新18methods（A7/B8/C3）の作者Green履歴とselector自己3Greenを確認し、既関連のローカル未実行を最新成功とは数えない。新selectorは3変更/他19・Runtime hash固定、全CORE/bare alias binding、空のbaseline overrideも拒否、ABI、core clientのbaseline全bytes、skip/error/重複拒否と前後source一致を保持する。予定選択43methods/18scopeと新thin entryへのworkflow切替は変更境界に整合し、旧runner/旧起動口・共通client/暗号/回収を改変しない。

P1（解消済、発見時の根拠）: 最終共通C4の97PNG/36pairの保持比較を作者が一度実施し、実2 `8e384afb` cmd6 LEFT/source116→126で、旧MOVED(-1,0)→新UNKNOWNを検出した。旧source116の材質差0、latest126の材質差3があるためPerceptionとの結合を単一pairへ絞って調査した。根拠のGit外 `test082-motion-fixture/retained-before-after082.json` は上書きせず保持している。実1UNKNOWN→UP1の改善でこの既知回帰を相殺せず、下記B2を加えて再確認した。

B2計画追確認: 正しいFLOOR2復元によって旧075 planeの8px競合支持が300を超え、9pxとの一致率差が4.416ppへ下がったことを局所根拠で確認。STONE追加は原因でなく、材質の偽正規化/旧15pp緩和で直さない計画修正を確認した。**B2の実装着手GO、追加の設計P0/P1/P2なし。** 既075 L unique9・有限raw high unit/gap・左右有限phaseに、worldBlurの95%/300/固定52両帯100というunit品質と、別の旧5依存gradient面の75%/300/固定65両帯100・全73元15ppという競合識別を別々にANDする構成は妥当。支持を合算せず、新mask/採点後の領域選択もせず、blurで15ppが成立したとは扱わない。gradient75%はこの新結合で採用する新条件と明記され、旧helperの95%や旧blur15pp自体は不変。旧075の判定を上書きせず新UNKNOWN proofだけへ限定し、無金/商品保護・元期限/UNKNOWN無再送・実5金case適用外も維持する。この計画追確認時点では追加Red/Greenと保持比較を未確認とし、P1の解消判定を下記の最終確認まで保留した。

B2最終確認: 上記計画に一致する限定helper/callを確認した。公開正例はO0/strict O2のcompile成功・全前提確認後に旧UNKNOWN対期待unitの意味Red2→新Green。独立境界の初回fixtureはUPに対してhorizontal aliasを誤生成していたため、vertical8pxへ方向だけ訂正し変更methodだけGreenを確認した。blur品質不成立、sharp75%不成立、sharp75%は成立するが全73 lead不成立、phase unit/競合の非有限、75/95・300/100・15ppの各境界、scope/L/nonunitを独立に拒否する。既B1の6methodsはhelper/default4pair不変を根拠に履歴を再利用し、意味試験の全体反復はない。新2helper/callを除く旧Nav全文bytesの復元も確認した。commentの旧gradientが75%だったと誤読できる表現は訂正済み。

修正後の `retained-before-after082-b2.json` は最終Perception281866…/Navdce5…/Controller12d3…を結合したlibrary SHA `9de2f122816374b7ae2d147f3118a91d44f4acd6bb90813f1a201fab36a73a48` に対応。97原画/36保持source-prefix比較で旧known27すべての出力維持/回帰0、旧UNKNOWN9中は実1cmd12/source160→178だけUP1 MOVEDへ改善し、残8はUNKNOWNを維持。実2cmd6/source116→126のLEFT1も回復を確認し、P1を解消とする。この比較は実機の再実行でも、未収録の未来応答の補完でもない。

実5金壁caseの移動確認は未解決、実2の未収録拒否原因も未確定のまま。新unitの単体成立や29セル校正を、全run到達・見逃し率・毎拍/人超え・対象認識の受入へ読み替える記述はない。
