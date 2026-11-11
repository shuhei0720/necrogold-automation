# TEST080: 狭い閉金扉前の実変位と閉じた通路候補

2026-11-11（日本時間）。baseline `88705eac9c64ace365a1bc8e60bbc3f50399ec10`、TEST079/build128。通常の局所修正。Nav/Controller2source・新単体2module・関係する回帰・独立レビュー1名・新IPA/固定Release・一連実機を対象とする。Runtime/Perception/JSON/API16cap14v15/全ABI・G1/R12原40/元期限・予算/UNKNOWN無再送を維持。製品変更前に公開assertion Redを実測する。

## 受領と問題

079実順1f2b84fa→93a2ca80→d6cbad28、3ZIP/58選択原PNG（20/18/20）。全SHA/ZIP・PNG CRC/復号/896×414/manifest全offset・hash・cursor/prefix/strict schema/_load/実publicationを照合、全PAUSE/terminal/drained/完収。capture/dispatch failure/timeout0、host error/cancel0/status43回max1.358秒。原368で3商品と価格100/150/50をroot視認、到達1/3。raw/SceneはGit外received079/test080-*。

1は5restart/7MOVED8入力、最後cmd19 UP/source328→353をACK後8UNKNOWNでMOVEMENT停止。実beginはNB+1.077ms/D−8.923ms、最後visualD残約1.602秒。reference=authority328で別frame救済なし。原画は閉DOOR2ahead→adjacentの実UP1歩、金2枚exact・同法線・unique9成立。

元phaseは中央除外maskに支持が足りず全73でINF。元median148/bad0、expanded436/bad0。078固定3依存面は316/bad1だがcamera52帯68/248で各100未達。入力軸の固定x112分割も313/5で不成立、採用しない。元phaseの有限判定や支持/帯閾値を削って救済しない。

3は3restart/3MOVED3入力、cmd11 DOWN/source152→160でMOVED確定、pose(-2,1)。固定bit8 mouth(-3,1)/outerGoal(-4,1)の内側隣接へ到達したが口がDIRT、両脇も壁で観測床経路なし。保持152/177で口DIRTを確認。160の原PNGは省略されており、実wait anchorのScene/私的wait状態・成立時刻を再構成しない。旧コードの2拍BLOCKED待機→未判定NO_PATHと整合する。

## A. 元phaseが全て取得不能な閉扉unitの別証明

旧全関数と呼出し順を維持し、最終UNKNOWNかつ元73phaseが全正INF（NaN/負INF不可）のときだけ追加する。旧phaseに有限値が一つでもあれば新証明は使わない。両FLOOR/CANDIDATE/GOODS_UNKNOWN、全ITEM/保護0、旧origin/実nextと最新originの観測FLOOR、旧2ahead閉DOOR→最新adjacent閉DOOR/入力軸に合う金bracket、旧/新GOLDexact2・unique9を要求する。さらに保持された旧STONE由来の相異なる2点が旧門中心と非共線。消えた/変わったSTONEや新STONEを一致証拠に数えない。

別phaseは既opening_maskを固定して使い、normalized intensityの実依存3×3全点が両frameでmask/UI除外・観測済み同材質・非DOOR/ITEM/保護である場所だけから求める。黒・未知/新露出を支持にしない。元の計算順・300支持・mean6/contrast2.5・gain .65..1.55・nearest-evenを再利用する。この新phase自身に既gradient正本の固定65上下帯各100支持（両frameのcenter64/65を除外、3×3依存は上下で非重複）を要求し、zero/±1..18全73で同方向の厳密9px unitがscore≤.45/gap≥.08の唯一最良であることを要する。原phaseの値を書き換えたり、画像を動かして正解を作らない。

追加の符号証拠は078の各frame固定H→V・実3依存feature/camera52/両frame51,52除外をそのまま使い、総300/95%/全73元15ppを要する。新結合の独立2領域は上記phase側に課す。旧closed_gate_axis_strongの52帯100条件も本文も変更せず、新proofは別のANDとして実装する。078のcamera52/既5依存/旧65面を変更しない。

最初の『新phase＋3feature固定65帯』案は、phase395/.05545648/有限2位.94774235は成立したが、符号支持281/帯196・85で不成立として不採用。任意帯の探索はせず、独立性をphaseの全3×3画素へ課す固定結合をread-only評価した。結果はunit(0,+9)/score .04768658424/支持347/帯192・155、旧3feature316/bad1。72競合phaseは支持最大285で全INF、符号競合も300未満で、有限競合との実.08差や十分支持競合との実15pp差を測ったとは呼ばない。これらの境界は手続単体で別確認する。

成立してもMOVED unitだけ、開通/入口/商品creditを作らず、最新の通常Navが次の扉を判断する。before/source/元visualD・8評価/同期・入力予算を変更しない。

## B. 内側から閉口を確認した候補だけ局所見送り

BLOCKED待機中・input0・最後のACK実MOVEDで固定mouthの内側隣接へ到達した場合だけ。初期原点の口を検出し直さない。旧anchorと後続の独立stable current-prefix（取得開始≥anchor終了、別ID）においてorigin床・口が同DIRT又は同STONE・両脇DIRT/STONE壁・両Sceneに次の観測床経路なし・strict BLOCKED zero・全GOLD/商品/ITEM/保護なしを確認する。外側goalのUNKNOWNや変化は陰性証拠に使わない。

元2拍/旧horizon/全予算内で成立した候補だけprivate `passage_closed` へ退役する。外側目標への到達済み `passage_inspected` と区別し、未判定 `passage_unresolved` を消さない。他候補があれば通常選択へ、残りが全て独立確認済みか閉口確認済みなら既PAUSE/RESTARTへ。未判定が残れば従来NO_PATHを維持する。start/level切替/初期候補更新でprivate閉口maskも撤回し、総counter/ID/clock/元予算を巻き戻さない。

旧GOALの外側到達確認・UNKNOWN待機・商品/新金/普通扉/保護/取消/owner/prefix/期限等号の優先は維持する。金根拠なしの壁掘り、未観測進入、世界全体の店なし判定、送信UNKNOWN再送の権限は追加しない。

## 単体・配布と未検証

Aは公開Cの旧UNKNOWN→期待unitMOVEDをcompile成功のassertion Red→Greenとする。手続fixture/原画Git外、4方向、旧phase全INF/NaN/有限拒否・新phase支持/score/gap/73候補・全3×3依存・phase固定65独立帯と符号総300/95%/15pp境界、閉bracket/oldSTONE/保護商品/旧known・次Nav開扉と未入店を確認する。

Bは公開Controllerで実MOVED→独立閉口確認→次候補又は既restartまでをRed→Green。未送信/UNKNOWN送信/初歩0移動/非隣接/口や脇UNKNOWN/FLOOR/異材質・GOLD/商品/ITEM/保護/owner/prefix/取消/2拍・horizon等号/未判定残存/新level撤回を拒否境界にする。C private seamなしを基本とする。

新単体の意味再実行を重ねず、関連17methods（旧Nav2/078閉扉2/079露出2/Controller2/072通路6/074初期1/076待機1/ABI1）とselector3だけを限定CIへ選ぶ。独立1名が計画と最終差分/既ログを確認。freshG1→22seal（Nav/Controller2変更/他20）・実compiler/全9MachO/完全source/IPA照合を実施し、固定Releaseの匿名全GET後に返す。全Runtime/worldや初期画像保存の別課題を混ぜない。原Scene純分類と欠落future/実機受入を分ける。

通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認をまず2回、新IPA更新・完全再起動/Start Server/VPN・test_080.shと全run別ZIP返却を依頼する。新実機の到達率/恒久毎拍/人超え・対象判定/通知/対象なし自動周回は未受入。
