# TEST115 検証記録

2026-11-18（日本時間）。[計画](../plans/test115-device-failures.md)・[修正表](../fix-records.md)。TEST114実機4周は不合格であり、この記録のソフト試験は実機改善完了を意味しない。

## 受領・原因

8ZIP/4固有run、96PNG/106記録をCRC/path/参照/hashchain/原RGBAまで照合。端末の開始単調時計で2b78→00bf→1386→2fd3の順。全3商品観測・陰性判断・商品後RSの成功記録は4回とも0。goods停止やcompleted_shops=1だけを成功に数えない。通常判定は約4.96/3.94msで、終了後回収70〜89秒とは別である。

実際の停止条件と修正は計画の対応表に固定した。128→129は送信前の直接零/同判断、129→後続は通常MOVED。30は実金セル0の上左通路。上部入口は旧全4歩予約の過剰な150ms先取り、2商品ケースは旧上端投影の無効化後に現在PARTIALへ進めない問題。4周は実金0の候補分類/途中blur/元2拍期限を分けた。

## 設計・差分確認

独立設計確認でP0なし。R1は実tile mask4をquietが消す前に処理し、一物理票につき一回、元準備epoch/票/原anchorを保持する。R4はREADY/OBSERVE/ISSUEDを分け、確実未送信だけ退役し、元2拍W（未解決）と元親P（確認後）を既076と同じ状態別に保持する。R3は単一の未使用観測枠、元hard拒否/商品保護和集合/共用DATA2、直接2零/新fit/実drainを維持する。単純なFULL資格緩和や2歩枠の新設はしない。

Nav差分は独立確認済み。既20helperのbytes、raw73/.45/95%/300/各帯100/75%/15pp、実GOLD/ITEM/DOOR/保護の除外を保持。追加の共有案では通常Motionの元全25段を同じ順で維持し、局所View/候補の再計算だけを省く。差分はC/NavとRuntimeの送信直前時計へ限定し、Ring/Perception/header/ABI/G1/R12/元予算は変更しない。全差分と配布用checkerの最終確認は別に閉じる。

## 新試験の根拠と限界

修正前の意味あるassertion Redを機能別に保存。初期のctypes型/fixture不足/compile失敗はRedへ数えず、直した最終fixtureでも旧Cへ戻して確認する。旧assertを削除・skipしない。

R2は正常Perception/Ringの手続き的画像、約276ms ACKと実機に対応する取得/phase更新を用い、左右両方の全HHDD・実MOVED・完全陰性・新PAUSE・永続化/intent・RSまで確認する。R3は正常producerで上端二重投影→現在PARTIALを作り、新DATA/2零/新fit/一回UPを検証する。UP後UNKNOWNは保持、別の手続き的FULL画像では正常完全陰性→RSまで確認する。これらの未来画像は実機の未収録画像を再現したものではない。

R4の初期新試験は票の発行だけを確認し、実行可能性が不足していた。実86のnotBefore−52.313208msと97の経過513.735958msに合わせ、現在commit直後のtick・50ms準備・begin成功・ACKの信用0・通常MOVEDを追加した。その後、初案の「確認後もW内に入力」は既076と異なる過剰制約と分かった。W内に再確認したREADYは元Pまで新拍を選べる既契約へ戻し、最早準備を逃す場合もP内の次拍/実beginへ進める。W以降に不明へ戻る場合は終了する。未配布の旧案/試験/logを保存し、既076のassertは変更しない。

時間確認では、通常Motion＋補助零がホスト約10〜13ms、同じ現画像の公開/beginでも再計算され、初期の模擬時計だけでは費用を含まないことを確認した。一呼出し内の重複を除く案は約6〜7msで、通常出力37pair全bytesを保持する。元10ms入力窓はRuntimeのC.begin後にも現在時計で検査する追加境界を選ぶ。実機費用/毎拍到達は未確認であり、host時間を端末受入に置き換えない。約48KBの追加proof cacheは採用しない。

## 保持した成功

実TEST113の候補236と正常陰性→再開成功177は原ZIP/PNG/RGBA/記録連鎖を特定。通常Perception/Ring/kernel/headerの16入力と旧library SHAを全照合し、元bytesと一致した。今回のC/Navはこのproducerへ入らないため、元の正常分類を再利用し、不要な再compile/再分類を行わない。新しいCの候補優先と陰性採用は関連試験で別に確認する。236はcandidateとして保持した成功であり、TARGET確定や通知の端末受信証明とは区別する。

## 配布前の残り

最終author inventory/独立差分確認、選択した関連回帰、実Macの旧C指定Redと現Runtime3ケース、実Python3.9、seal/実compiler/IPA/完全sourceの同一性、固定Releaseの匿名全GETを未実施のまま成功にしない。実機改善・毎拍歩行・人より速い速度は次の実機で評価する。

回収のJSON割当最適化は、実3.9の同bytes比較で遅くなったため不採用。validation.pyは元bytesへ復元し、新試験/試作はGit外に保存。終了後70〜89秒の回収遅延は残課題である。

送信直前時計の実TDD: CI234は初回に継承したFULL商品fixtureへ入る指定外失敗で、compileエラー0でもRedではない。新nativeV1二caseだけ既RGBA hookを解除し、CI235/run44235308732/CODE3d35a7cでは旧Runtime dc082の指定Red1（D+1nsで実gesture1/ACK/input1）を確認。原artifact138045bytes/SHA8557502eを全取得・CRC・全実ソースと照合後にRuntime e655aa10を反映した。最終製品sourceはC8c740b31/Nav9c872fd8/Runtime e655aa10、36資産中3変更/33保持、seal766070e1。最終4case/時計7条件とIPAはまだ未確認である。

CI236/run44237233905/CODE3faf423: host65（native57/selector8）、実CPython3.9.25の4件、Macの旧C/旧Runtime指定Redは成功。現Macはpartial_cancelと送信時計7条件が成功し、lateD+1の方向入力0/加算0/既知未送信、等号の許可と取消競合を確認した。後続の安全なPAUSEは方向入力の件数とは別で、全UI0とは書かない。他2caseはcameraのfake82ms進行と、postUP第3worker中の明示cancelで不合格。製品3ファイルは保持し、新115Swiftだけ616fba28へ訂正した。全assert/元絶対時刻/厳格な正常producer検査は保持。実4case全体の成功・IPAは未確認である。236のhost/validation ZIPは全bytes/SHA/CRCを保存し、5実物gateは開始していない。

## 最終CI237と実物照合

CODE `1028137a0b9db599b32185b728492fdb6fb9b20b`、run `44239484029` は全必須job成功。host65（native57/selector8）、実CPython3.9.25の4件、実Macの現4case（passage_fresh/partial_view/partial_cancel/post_begin_clock）・時計7条件、旧C053b/旧Runtime dc082の指定assertion Red各1を同じCODEへ結合した。未知caseを拒否し、skip/期待失敗で成功にしない。変更のない分類/ヘルパーの過去結果は再利用理由を明記し、不要な全体再実行は加えない。

正常producer/実callbackの手続き的Spool2export/各24PNG、計48PNGを全照合。nativeは36資産中C/Nav/Runtimeの3変更/33保持。Ring/Perception/全header/ABI/G1/R12/feature/ELF（56088bytes）/数値条件/全累積予算を保持した。5gateはpackage/host/retained/macho/compileの初回5attemptで全成功、失敗0。確認のための新しいsemantic/compile/classifier実行は0。

| 配布物・照合 | 結果 |
| --- | --- |
| IPA | 18,250,993bytes、SHA256 `107e3db9ee265f6dabdca7b8cfe3a027b603aa8d87b951db073e8f5e062d3990` |
| 実bundle | `Payload/LoopCtrlAllInOne.app`、build237、最低iOS16.0 |
| seal | `766070e1b45a3166195360fe6756cdb2266ff07014311802a2ab030a8cbb5d49` |
| 全CODE source | 1082files、SHA256 `7424a3f5329a9a1e26d3e06aea010fde5ff546913f8081d7bca27e1f88135f4b` |
| 全実物gate結合 | `f787c4dcdb0a6c9ed7c617a95f7877086eb5ac74e214fa5566a8ee45a19fa2b1` |

最終sourceと固定Releaseはdocsのみの締め後に照合する。実機の商品到達/対象候補精度/毎拍/人より速い受入は未確認。次回は通常1-1のポーズからTEST115を `--until-target` で実行し、campaign索引＋最後のrun全ZIPを返却、全runtime原本を保持する。

## 固定公開と匿名取得

配布source `4765027db5c4a24d9689fa54786099fe282901cd` はCODE1028137との差がstatus/context/本検証/修正表のdocs4件だけで、全製品bytesは不変。完全codeload ZIPの全1082files/CRC/path/各Git blobを照合し、9,963,234bytes/SHA256 `7e1060160844b3cb0f130d230d65c425dfcd3d900901583c2c1586da2f08ef96` を保存した。

[test115-build237](https://github.com/shuhei0720/necrogold-automation/releases/tag/test115-build237)（Release449551269）はpublisher238/run44242624277で公開。空draft/正しいtargetからだけupload/publicへ進め、tag→上記sourceを確認した。IPA/source/SHA表の3assetは匿名の全GETで200、全bytes/SHA/Release digest/hash表一致を確認。SHA表156bytes/SHA256 `895867837aa152eed777da62b041e756abc6ad84c0078b26f1539b8509d87ae7`。公開後の追記はdocsだけでassetを置換せず、検証のための再compile/再分類/再試験も行っていない。実機改善/速度未確認と回収遅延の残課題は維持する。
