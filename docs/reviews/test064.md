# TEST064: 未送信の同じ1歩を遠方揺れで失わない

2026-11-10（日本時間）。[計画](../plans/test064-stationary-step.md)。TEST063ユーザー商品可視1/3、プログラム完全商品判定0/3。新しい実機到達を未実施の単体で成功扱いしない。

受領43原画のSHA/bytes/寸法/全CRC/manifest一致、3run resolved/terminal/drained、active=最後のreportを確認。実Perception/Nav/Motionで、1/2回目の開扉後120→121/139→140は同FLOOR/PARTIAL・全5field入口判断・金/保護/局所近傍不変・strict BLOCKED。3回目83→84も同FLOOR/UNKNOWN・全5field・strict BLOCKEDだが、actual commitがnotBefore−90,059,648nsで旧quiet50ms窓外、初期再予約2回を既に消費していた。画面分類不良ではなく、未送信の変化判定が停止原因。

初歩の既発行ticketのquietを公開100msへ揃え、lead確認/実移動済みの入口FLOOR1歩へ同IDquietを追加。全5field/金/全保護/局所床/厳密BLOCKED/元source・phase・model・全期限で拘束し、商品VISIBLE/取消/owner/lock/未知入力/送信済みは維持する。既存safe_floor/実再予約counter/FRESH/初歩校正は緩めず、source/ID/拍/全期限を変えない。

新初歩5methodは旧Cの意味的Red（5assert failures/errors0）、新入口6methodは旧Cの正常系4subcaseでRed（compile成功/errors0）。新Cで初歩5+旧quiet3の8件2.896秒、最終入口6件1.899秒がGreen。入口は全4方向×UNKNOWN/PARTIAL、元ID/全command bytes/待機期限/回復状態保持、近傍/金/保護/商品/署名/期限/owner/lock/前面/取消/不安定prefix/送信済み拒否を確認。既存061の50ms窓期待を100msへ根拠付き変更し、再予約positiveは新remoteSTONEへ替えてassertを維持した。

原画2組を新quiet helperへ直接渡す適合評価も両方1。geometry/実C判断/strict motionは原画から、未収録のmodel/ticket/timeは明示した合成文脈。完全な実機再生や将来の商品到達を証明したものではない。

## CIの選択

新初歩5/入口6、旧quiet3、関連continuous/公開窓8、ABI1、063未送信回復4のC27＋試験選択器3で30methodを選ぶ。native source22の前後同一性/ABI/全実行ID/0skipを実IPAへ結ぶ。不変のcadence・残unsent・workflow/publisher・全Runtime/world/Kit/clientは再実行しない。関係のない試験やassertは削除せず、選択と省略理由をhost metadataへ保存する。YAML/publisherは不変。

Controller C SHA `d1ce74e3b321cb5f777ba8315373569f01fd0f81e45bb18a10b79e3fd50777d6`、manifest SHA `e7e57d6b093ac70f660f3fbd9fe6a7194761fac54b86af06e2ef66d95118aa1f`。22source中Controllerだけ変更、その他21/API15/cap13/client v14/公開ABI/R12/G1は維持。独立差分レビュー1回でP0/P1/P2指摘なし。全4方向×UNKNOWN/PARTIALの8手続きで、3回の遠方揺れ後ACK→実C MOVEDまで確認した（実機商品到達とは別）。Mac/実配布物の結果は配布前に追記する。


## 最終Mac98と実配布物

code `3d8334249394ae81ed8d449d4925dc2eb85c35d3`、[Mac98](https://github.com/shuhei0720/necrogold-automation/actions/runs/42747426496) device成功。実IPA build98 SHA `34a588f1e53808f97e62681df83513b9d1b38456d66dfda8bc0e5a4992af0c53`、外ZIP SHA `6ba6b4416d3b1420ca4114ca207eb8be0584a11f339dde79e9dd7e460b835e9e`。

hostの全30実行ID/生ログ/0skip/error/選択理由/22seal前後/ABIが実IPAと一致。実4C/5Swift/6RSP/PBX/raw引数はPerception/Nav strictO2、Controller/BeatO0、SwiftOnoneでHOST macroなし。全9Mach-Oで従来100marker+064の計101が非混入。22native source中Controllerだけ変更、他21/R12原40/G1維持。build-sourceは全488tracked bytes/path/CRC一致。配布最終source差分は文書3件のみと確認する。

Git外host検証器はABI scope1件のunittestログ単数「Ran 1 test」を既存の複数regexが拒否したため、実件数に応じた単数/複数の厳密検査へ修正して実物照合を完了。製品/CI/test期待値を変更せず、実suiteの再実行は不要だった。

[固定配布/実機手順](../status.md)でIPAと完全sourceを返し、商品可視位置への実機到達を依頼する。TEST064の受入は未実施。原画2組のhelper適合や合成ACK→MOVEDを、下方商品の将来画像や実機商品到達の証拠にはしない。
