# 最新状態

更新: 2026-11-15（日本時間）。TEST104/build198は最終選択CI140件/29scope・IPA作成・実物5gate成功。修正後の実機改善は未確認。[計画](plans/test104-shop-continuation.md)・[受領/検証](reviews/test104.md)・[修正表](fix-records.md)。

TEST103の4run/99PNGを全照合。上部入口3停止は、遠方材質差で旧移動資格を撤回し最新画像へ再判定。下の商品・価格が見切れる場合は、全potentialから必要DOWN数と元親期限を固定し、各最新判定/独立零/実MOVEDを確認して進む。全商品帯のpolicy9と観測口116も修正。対象はのろいのゆびわだけ、候補/未観測は保持する。

初期C32件(d886)と追加C22件(e336)、Ring61件、Nav23件の作者証跡を区別し、最終CIは現Cを含む140件が成功。3/7ITEM投影から全商品可視→通常判定→保存/リスタート/次floorの制御試験も成功。原205の通常分類は約41ms、そのResultの公開C採用はd886時点の校正。C9証明body不変、現Cの通常producer接続は最終CIで確認。実ゲーム再現・未知精度の証明とはしない。

native変更はController/Navigation/Ringの3、残33/Core ABI/Perception/Runtime/旧1..8・旧assert・canonical15/ELF/G1/R12/共有099は保持。16入力/12restart・45秒walk/180秒session・UNKNOWN無再送・全画像/ZIP照合を維持。毎拍/人超え速度・耐久・一部の過去停止は未確認。

[新IPA198](https://github.com/shuhei0720/necrogold-automation/releases/download/test104-build198/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test104-build198/source.zip)・[SHA一覧](https://github.com/shuhei0720/necrogold-automation/releases/download/test104-build198/SHA256SUMS.txt)。固定公開済み。匿名全GET200/全bytes/hash/API digest/tag一致を確認。

次はIPA更新・LoopCtrl完全再起動・Start Server/通知/通常VPN、通常1-1ポーズから sh test_104.sh --until-target。候補探索→入店→下側を含む3商品確認→対象なし次周回を確認し、全画像/ZIP照合後の表示campaign ZIPを返却、全run原本を保持。[索引](context.md)。
