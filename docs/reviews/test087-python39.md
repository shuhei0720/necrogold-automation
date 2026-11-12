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

作者freezeは回復3ファイルのみ、`recover087.py` SHAは上記、shは `21f991a0f2a85ec227316a3d60431f0668f5b22bcf699852181fe2bda210531d`、単体は `969a263ea5990bab63ee997c30f079509dad8bbbf00ee95af611fe7f765ee41d`。target6/回復3の有効Red/初回Green・原309・全native/R12と既entry等119path不変の作者証跡はGit外 `test087-python39` に保存。独立担当の120参照にはこれらと追加参照を含む。新しい実機結果や未回収の2回目の判定を推定していない。
