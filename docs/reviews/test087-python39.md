# TEST087 Python3.9互換エラーと保存回復

2026-11-12（日本時間）。[短い計画](../plans/test087-python39.md)。基準 `b2b1cb003f51009ffe75f89080b9089a6cb2fed9`。TEST087/build148のnativeは再利用する。

ユーザー実機は `/usr/lib/python3.9/runpy.py`。20/20画像保存後、`test069._publish→test087._prepare→target_assessment.classify_png→_observations` の `int.bit_count` でAttributeErrorとなり、archive作成前に終了した。`int.bit_count` は3.10追加であり、前版の開発機だけの検証では3.9互換性を見落とした。失敗は対象判定段階で、20PNGの取得失敗とは区別する。

価格row1と文字intersection/union2の合計3箇所を `bin(value).count('1')` へ同値置換。新helper/feature/閾値/判定state/schema/ゲーム入力は変更しない。旧positive testのreference ink計数も3.9対応の独立bin countへ変え、前提通過後にpublic classifyで互換AttributeErrorが出た場合を明示assertion失敗とする。通常の期待値/assertは維持した。

作業用CPython3.9.25（bit_countなし）を取得し、header/239ink等の前提を通過した後に、ユーザーと同じunsupported integer APIの有効Assertion Red1を確認。3call置換後、同じ実3.9で対象6methods全Green（34.280秒）。原086実3の宣言済み校正原309も実3.9でtarget、中央icon.953305062・wordIoU/coverage1.0を維持。新しい未知陽性精度/実機速度/歩行成功の証明ではない。

回復専用入口は同じ `~/.necroprobe/runtime/test-087` の永続原本を読む。publication lock/strict load→既certificate/prepare/publishを使い、native.main/Client/session/新ゲームstart経路を持たない。空・未完は拒否、既出版も同bytes検証のみとし、SIGINT/TERM時は元cancel検査と保存を維持する。通常test087 entryを別番号へ変更せず、既報告/原PNG・UUIDとarchive/receiptの同一性を守る。作者の有効Red/回復単体・CIと同人差分レビュー結果は後続に記録する。

新しい軽量Ubuntu workflowはsetup-python公式v5 commit `a26af69be951a213d495a4c3e4e4022e16d87065`（GitHub APIで確認）を固定し、Python3.9実版・bit_count不在をassertして対象6/回復単体だけを実行する。native全Mac/新IPA/旧C全回帰は無変更なので実施しない。source-only固定Releaseと全ファイル照合/匿名GETを予定する。

新添付aeef427b（ZIP SHA `a51485556fb54ff62b674087b1439f66efcf5fec137095b07d0c4550fb94f31c`）は別のrun。native MOVEMENT10/GOODS0、inputs2/moves1/restart2/pose(-1,0)、20PNG/4,072,671画像B・CRC/SHA/PIL/API16/client_load/publication/sidecarは正常で回収完了。ACK済みcmd7 UPの移動確認8回でUNKNOWNとなり停止し、bit_count例外が起きた商品可視runとは別原因。今回の互換修正にnative修正を混ぜず、先に未出版runの保存回復を依頼する。raw/診断はGit外received087/aeef427bとstop-analysisに保存する。

## 同人のcode前差分レビュー

TEST086/087と同じ独立担当が短い計画・最終差分と作者証跡を確認し、P0/P1/P2なしでGO。前版レビューでもiSHの最低Python版に対するAPI確認が不十分だったため、今回は実3.9の有効Red/Greenと、新ゲームstartを構造的に持たない回復を確認範囲にした。独立の意味試験/compile再実行は0、製品/試験への編集0。

対象module `534a097428e6a893f602ffc82709dea746dcc28f9ad09f23360aee63fe2ad726` は元moduleから3つのpopcount式だけが変更されていることをbytesで確認した。非負の有限bit maskに対するbinの1文字数は元bit_countと同値で、feature/閾値/slot/3state/source選択/保存schemaは不変。新moduleと通常entry/import経路に他の明白なPython3.10以降専用API/構文の残留は見つからず、実3.9.25の対象6全Greenで該当経路を確認する。header/239ink前提後の互換Assertion Red1と34.280秒のGreen6、原309の校正target結果を実ログで確認した。新しい実機成功やiPhone速度とはしない。

回復module `03ff04f7c2ea315d6ba6ec08ecd919c9f2d37f1f11ef7607f3e3b06c215ea0a9` は固定087 home spoolをpublication lock内でstrict loadし、既certificate/prepare/publishまたは既出版の同一性検査だけを行う。通常test087の新session分岐へ委譲せず、native.main/run_session/Client/transportを呼ぶ経路を持たない。新3単体は同UUID・原report/PNG保持・target sidecar/ZIP/receipt完成、2回目の再分類/新start0、空/未完/破損とSIGINT/TERMの保存保持を明示する。旧通常entryへの委譲が既出版後にnative.mainを呼ぶ有効Redと、実3.9初回Green3（4.562秒）を確認。最初の広すぎたUUID guard失敗は一時ファイルUUIDの遮断であり、有効Redと混同していない。

新shは純local回復のみでlocation keeper/ゲーム操作を追加しない。軽量Ubuntu workflowは実3.9とbit_count不在をassertし、対象6/回復3の計9だけを選ぶ。通常087 entry/publication/native_walk/validation/protocol・featureおよびpatch/native/R12の計120参照pathは元配布commitと全bytes同一。native/IPA再ビルドとMac/旧C全回帰は不要で、build148の検証済みIPAを維持する。diffcheck PASS。以後は同codeの3.9 CI・全source ZIP/固定Releaseの照合とユーザーの保存回復確認を別工程で確認する。

作者freezeは回復3ファイルのみ、`recover087.py` SHAは上記、shは `21f991a0f2a85ec227316a3d60431f0668f5b22bcf699852181fe2bda210531d`、単体は `969a263ea5990bab63ee997c30f079509dad8bbbf00ee95af611fe7f765ee41d`。target6/回復3の有効Red/初回Green・原309・全native/R12と既entry等121path不変の作者証跡はGit外 `test087-python39` に保存。独立担当の120参照は起動shを除いた同じ集合。最初の作者記録119はGitのquoted Unicode path読取りでR12日本語名2件を列挙から落としていたため、NUL区切りで全121（R12全40含む）へ訂正し全bytes一致を確認した。新しい実機結果や未回収の2回目の判定を推定していない。

## 同人のPython3.9 CI確認

code `36fbcd3a776d5b866bcbe0d3176b848c512d8fed` / run43194860629はpushのattempt1でsuccess。default未登録workflowへのdispatch404はCI実行0であり、追加したwatch2pathはfeature/通常shだけで製品を変えていない。独立担当がartifact13933080579（920B/SHA `5d0bc67a8a8a130a4505ed9b8c857b62e190402a93466b0e5fc3c025e2d7df07`）の全CRC・単一実ログと抽出log同bytesを確認した。実Python3.9.25、target6/recover3の9件が56.187秒で全OK、記録された5source SHAは対象codeの全blob bytesと一致する。意味試験の独立重複実行0、native/Mac/IPA新ビルド0。P0/P1/P2なしでsource-only固定ReleaseへGO。全source/公開後GETの最終照合と実機の同087保存回復は後続工程であり、このCIを実機回復完了とはしない。

## CIと保存・配布

code `cfab9ff3a48bfa11dd094bea7c2db36f021d96ff` を保存。新workflowは既定branch未登録で手動dispatchが404（実行0）だったため、watchへfeature JSON/通常shを加えた `36fbcd3a776d5b866bcbe0d3176b848c512d8fed` のpushから限定CIを一度だけ起動した。run43194860629/attempt1/number1、標準ubuntu-latest、実CPython3.9.25かつbit_count不在assert成功。対象6/回復3の計9methods、56.187秒、全Green。Mac/新IPA/旧C群は実行0。

artifact13933080579/test087-python39-validationは920B、SHA `5d0bc67a8a8a130a4505ed9b8c857b62e190402a93466b0e5fc3c025e2d7df07`。GitHub APIの成功head/attempt/asset digest→実DL全CRC→ログ9件/版→対象/回復/通常test069/test087/featureの全5SHAをcodeと照合した。CIは開発機試験でありiSHの実速度や未回収runのtarget精度を証明しない。

closingはstatus/本レビュー/実機台帳の文書だけを更新し、完全671sourceと元build148のnative不変を照合する。source-only固定Release `test087-python39-fix1` に完全source/検証SHAを保存し、公開後の匿名全GET/SHA/CRC/全bytesを確認して返す。既build148 IPAを再利用し、今回の実機依頼は新ゲーム試験ではなく `recover_087.sh` による同087保存済み結果の判定/ZIP公開のみ。表示されたrun別ZIPを受領後に別件の歩行停止へ進む。

配布APIでdraft442755499を作成できたが、managed接続のuploads.github.comが401となりasset0のまま停止。期限付きリンクへ戻さず、固定draft専用の標準Ubuntu staging workflowを追加する。CI36fbcd3との差分を文書3件/当workflowだけへ制限し、全671source/CRC/全blob・元native等121を照合、fixed draft/tag/空assetを確認してtargetを同headへ結合し、source.zip/SHA256SUMSだけを非上書きuploadする。公開処理は持たず、rootの全source/asset digest確認後に公開し匿名GETを照合する。対象9件/Mac/IPAの再実行はしない。stage実行/実物証跡はGit外へ保持する。

同じ独立担当が配布専用workflowを静的確認し、stagingのみGO。固定repo/branch/draft ID/tag/空assetを検査し、CIとの差分allowlist・671全blob/CRC/safe path・R12全40を含む121保存pathを先に確認する。GH_TOKEN環境はupload stepへ限定し、source/SHA以外のasset作成・clobber・公開・製品試験の経路を持たない。release.target_commitishのPATCHは既存Git tag refを更新しないため、rootは公開前後にactual tag refが最終source commitと一致することも確認する。tag未作成なら更新後のtargetからpublish時に作成する。既refが旧commitならdraftの来歴を整えてから公開し、単にtarget fieldだけを同一性根拠にしない。独立意味/compile再実行0、配布実物の最終確認は後続工程とする。
