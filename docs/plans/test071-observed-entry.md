# TEST071: 2商品で止まらず入店し、見え直した床から判断し直す

2026-11-10（日本時間）。baseline `acfeb7a210d2a67a0ae509ec25417650dc3aa3c2`。

## 1. 目的

最新受領は1回目商品可視、2回目開扉後2商品のみ、3回目店前停止。残る2回を途中成功にせず、必要な商品全体が見えるまでの動作を改善する。新照明による経路判断は必要な1〜2拍の待ちを許容、既知安全通路の毎拍・UNKNOWN無再送・商品/保護/元期限は維持する。

## 2. 実機根拠

添付順は実行順ではない。device monotonic started_nsは4ae60e18=29470231642500、c94d9812=29574144432916、3c1a844d=29674045626541で、ユーザー説明と原画の対応はこの順に整合する。4aeは3商品/GOODS/PAUSE、方向入力間隔約.52秒。c94は2商品/PARTIALが正しく、3rd slotは未観測。3c1は商品不可視/UNKNOWNが正しい。Perception閾値を緩めて解決しない。

c94原画124→125は同UP/reason5/target(0,-1)/FLOOR、同gold/全protected・strict BLOCKED。開扉ACK後、唯一の変化(-1,-2)DIRT→FLOORが金bracket背後の斜め近傍としてquiet拒否、PARTIALを許さない一般safe_floorへ落ちFLOOR7/SCREEN停止。observeは元Dの89.610ms前。

3c1原画120→121は未送信id12のLEFT/reason6/target(-1,0)/DIRTが、最新LEFT/reason7/FLOORへ変化。actual CはTERRAIN_OPENED(0,0)、他は遠方(10,1)FLOOR→DIRT、gold/全protected不変。strict BLOCKEDではないためSAME/FRESHへ混ぜない。observeは元Dの36.326ms前、dispatch失敗なし。

## 3. 開扉直後の入店1歩

同じ金bracketの観測済FLOORへ向かう未送信reason5票だけ、直前のlast_completed_idが同方向の実DOOR_OPENED/ACKであり、まだ入口を通過していないことを要求する。変更セルがforward2/lateral±1かつその手前(coord-direction)が両SceneでGOLDの場合だけ、FLOOR↔DIRTの分類揺れを許す。一般の3×3近傍を広げない。

元/最新full5・同gold/全protected・origin/実next FLOOR・strict BLOCKED・model/source/phase/元notBefore/D/period/ordinal/元予算を維持し同IDを保持する。PARTIALをVISIBLEにせず、保護/次床/金/DOOR/ITEM・別経路変化は拒否する。入店後は新Sceneを判断し、未観測商品を陰性にせず、商品が隠れていれば既存plannerの観測床vantageを継続する。

## 4. 未送信dig対象の新床観測

lead確認済み・実MOVED後・確実未送信state1/event begin0/outcome0のreason6/DIRT adjacent targetから、最新reason7/FLOORの同unit方向/targetへ変わり、TERRAIN_OPENED zero vectorが実証される場合だけ1run1回の別経路へ入る。元/最新のorigin FLOOR・gold/全protected・許可済み遠方terrain変化も確認する。旧ticketはnot_sentとして永久撤回し、入力/開通/歩数creditは加えない。

最新FLOOR/full5をanchorとして固定し、後続の独立・非交差current-prefix画像でstrict BLOCKEDと同full5/gold/全protected/origin/next床を証明するまで発行しない。既存private gate_refreshのOBSERVE/READY/ISSUEDを共有してよいが、closed gate predicateは保持しmode/usedを分ける。terrain usedは1run1回、finish/beginでmodeだけ撤回、usedは保持する。

元latest_verified_ns+12秒・既存command_sync_deadline・walk45/session180のminを固定する。新IDの将来拍はprep50ms以上、model sample ID≥独立proof ID必須。現在のHUD modelが有効なら再利用し、形式的な2秒再fitを強制しない。古いID/期限/epochを復活せず、原beforeでのUNKNOWN/送信済み/非zero motionに救済を使わない。旧callbackは新状態不変、最終beginの最新proofIDを確認する。

## 5. 互換と範囲

Controllerだけの限定変更を基本とし、Runtime/Ticket/Nav/Perception/取得/実入力/各閾値は変えない。wire/ABI/API1.98.16/cap14/clientv15は不変。診断は既存recovery reason6/clock3・元snapshotを用い、新enum/未観測creditを増やさない。TEST071は既存publication入口に試験番号を渡す小module/launcherだけ追加し、全画像のlocal保存/検証済ZIP公開・旧原本保持・未公開runの次start禁止を維持する。

## 6. TDDとレビュー

実Cのpublic fixtureで意味的Red→最小Green。開扉4方向/両側/床茶壁揺れ、開扉ACKなし/別方向/next/保護/金/ITEM/期限の拒否、新床観測の独立pair/元budget/旧ID/一回上限/partial・goods・権限・非zero/未知送信/phase/prep拒否を確認する。受領原画は既知調整資料、未収録の次画面を合成して到達成功にしない。独立差分レビュー1回を基本にP0/P1を解消する。

## 7. 配布前確認

変更単体と入店/未送信再予約/前面epoch/元clockの関係回帰を選ぶ。新Cの未送信回復が入力権限を変えるため、既存の限定Mac dispatch/取消境界を新Cへリンクして確認してよいが、全Runtime/worldを累積しない。native変更の新IPAを標準Macでビルドし、22seal/実compiler/全Mach-O/完全sourceを照合する。生ZIP/PNG/report/派生証跡はGit外。

## 8. 実機依頼

固定Releaseの新IPA/sourceを返し、SideStore更新→LoopCtrl完全終了/起動→Start Server、新通常1-1の金壁可視ポーズからtest_071.shを依頼する。まず2回、開扉後に入店して必要な全商品が見えるか・既知通路の拍間隔・新照明での待ち・終了位置を確認し、自動runtime/test-071-<run_id>.zip全回分を返してもらう。回収済み070の再実行は依頼しない。
