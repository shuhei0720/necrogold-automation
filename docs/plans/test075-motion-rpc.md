# TEST075: 静止・移動の証拠とiSH応答処理

2026-11-11（日本時間）。baseline `488155f871a777652f9942af67d03b56b92546db`。通常の原因限定修正として単体/関係回帰・独立差分レビュー1回・必要な新IPAと実物照合・一連の実機試験を行う。

## 根拠と期待

TEST074の実順46efced0→0372e82b→1834cdeb。3ZIP/54選択PNG（15/19/20）の全hash/CRC/manifest/prefix/cursor/reportとstrict schema一致、全回収完了。商品全体可視0/3。raw/Scene/派生proofはGit外received074/test075-scenes。省略captureを未来画像で補完しない。

1は4UPの実MOVED後、金を発見して通常shop plannerへ移行済み。次LEFT/reason8/target(-1,-1)/FLOORは未送信。56→57の局所/全金/保護/full5不変、遠方2cellがSTONE→DIRT/DIRT→FLOORへ変わる。原raw最良zero/.310936/差.48398は元基準内だが通常texture支持283<300でUNKNOWN。既存quietが失敗してSCREEN。C実終了で元Dまで2.259ms、capture終了基準44.552msと区別する。

2は3入力目UPが元窓NB+2.406msで送信され、原画は正しいunit変位を示すが8評価全UNKNOWN。最後のC終了もvisualDまで1.927秒残り、deadline/再送/再同期が原因ではない。raw最良(0,+9)/score.58458/差.32166、旧detail611/逆77、既存勾配617/逆47で強95%未達、STONE0なので074石アンカー補助は対象外。単に元閾値を弱めない。

3は6restart後の金可視回で初歩公開窓の123.003ms前にhost cancel。statusのresult_json段階がRPC2秒を超え、native初歩の制御失敗ではない。HTTP約50ms/復号約110msの後が支配的。成功時の同段階も333/261/482/663/881/1205/1520msと増える。失敗reply plaintextは未保持なのでexact再現/OS停止影響は断定しない。

## 限定変更

Navのprimaryと旧全proof/全数値閾値を維持し、UNKNOWNの場合だけ、実原画で強度/唯一性/独立領域が成立する追加証拠を設ける。1は074の固定中心勾配をzero-onlyの静止証拠へ再利用する案。原56→57は538支持/逆1、上293/下245、全73競合条件を満たす。同gold非空集合/全保護・観測origin/実nextFLOOR・両3x3近傍材質不変を要求し、MOVED/開通creditを作らない。原raw最良zero≤.45/差≥.08を維持し、既存の中心差分5点known面で全73/300/95%/上下100を要求する。これはprimaryのzero raw条件を強い別texture面で確認するzero-only補助で、追加の恣意的なnearestStone選別は設けない。2は次の限定的な追加proofへ確定する。旧primary/旧全証拠面・mask・閾値は不変とし、UNKNOWN/両GOLD_CLEAR・金0/商品0/全保護0/ITEM0/旧originと実入力nextFLOOR・新originFLOORにだけ適用する。

- 初期beforeのFLOOR内角・内側2FLOOR・直交するDIRT/STONE各3連続セルからsupported L-cornerを抽出する。各Lは非共線の6壁と3床の2D構造であり、一本壁ではない。beforeの全Lを全9translation（0/±1/±2tile）で照合し、同向き・全床/全壁の材質まで完全対応する旧Lが1個以上、対応translationが1種類だけで、原raw最良と同じ厳密unitでなければ拒否する。旧L消失は許すが支持に使わず、最新だけのLで旧支持を補わず、別shift対応が1個でもあれば拒否する。遠方の孤立palette分類変化を全地図不一致として拒否する条件は加えないが、採用L内部の既知矛盾は全拒否する。
- 新しいworld観測面はfixed HUD/player/heart/minimapを除き、旧opening面で外していた開始部屋のworld内文字領域も同じ既知world cellの画像として扱う。文字を固定地形や特別anchorとは呼ばず、文字だけの変化では通さない。3×3boxblur（既存viewで算出するもの）の中心半差contrast6を使い、実際の21依存画素全てが両画像の対応同材質・既知cell/実mask/UI/ITEM/保護外であることを要求する。UNKNOWNや新露出を支持にしない。新world面の上下二帯は固定camera/player原点(448,207)/4に由来するy52を境界とし、半径2のkernelが重複しないよう両画像で50..53行を除外する。旧opening/静止補助の65境界は変更しない。支持300/95%/各帯100と全73競合への旧15ppルールを全て要求する。
- 原primaryの全73raw位相が同方向厳密unitを唯一最良/差≥.08とすることに加え、左右の独立raw bandでも全73が同じunit最良/差≥.08、各300有効画素・元contrast/gain条件を満たすことを要求する。band位相が使う3×3依存もUI/player除外へ侵入させない。幾何はgrid配置、raw位相はpixel位相、新blur面は強い対応を担い、corner単独で8/8.5pixelを除外したとは主張しない。

原点52の最終面では実73→83が580支持/逆11/上下413/167、→85は574/12/328/246、→86は572/12/326/246で全73競合条件も成立する。80/82は独立phase不足、84と87/89は全73への差不足でUNKNOWNを維持する。旧opening由来の65では85/86下帯がちょうど100だったが、新world proofの観測原点という意味に合う52へ実装前に固定した。支持/95%/100/15pp等の閾値探索は行わず、full-known union/median9など条件不足の試案も採用しない。85/86では右上旧Lが消え、右下旧Lが完全対応して全9translationで唯一(0,+1)。全旧L2個を保持する案は過剰で、一つの完全2D形と強いpixel証拠のANDへ根拠を固定する。全known cellの矛盾0は元primaryにもない追加案で、採用L外の孤立DIRT/FLOOR分類変化を成功証拠に捏造せず支持から除外する。支持300/95%/全73競合への15pp（競合支持不足は旧規則）/独立2領域各100・厳密同方向unit・商品/保護を保持する。

静止補助の当初実装は既存gradient_textureを全73回使うため、Linux strictO2単発2.696→6.374msと増える。実Controller snapshot/未保持履歴はないが、実56/57・pose/visitsの限定suffix（任意reference→quiet→失敗時continuous、9回中央値）はreferenceなし旧5.487→新6.315ms、あり旧8.071→新12.557ms。旧実C終了D残2.259msに対し無条件の「新quiet1回で速い」とは言えない。配布前にzero-onlyで特徴cacheを加える。既存gradient関数を変えず、同じmask/5既知同材質・保護/axis/contrast/signを一度計算し、before強特徴のindexから全73の同じ支持/逆/上下を集計する。全73候補の全中間数値を実20pair/手続fixtureで完全照合し、元の証拠・しきい値・候補を一つも省略しない。通常の挙動不変整理として、既存Greenと同値照合・性能代理で確認し、実iPhoneの処理時間とは区別する。

受信側はvalidation.json_objectの三重Python走査を削減する。C実装regexのtoken検索＋既存C scanstringでparse前depth16/nodes10000を維持し、短い非escape keyはまとめて読み飛ばす。長いkey/escape keyの許容上限は変更せず従来処理へ戻す。finiteFloatはparse_floatで記録してduplicate/root型検査後に拒否し、元のerror優先順を維持する。size/UTF8/重複key/NaN/Infinity/overflow/深さ/nodesを弱めず、API/応答wire/RPC2秒/heartbeat5秒/取消/UNKNOWN無再送を変更しない。59KBのstatus形JSONでPython line work64.8%減、Linux約1.85倍の測定はiSH実測と区別する。

変更対象の単体・関係回帰だけを選ぶ。Nav変更なら新IPAが必要、Runtime/Ticket/Perception/Controller/元予算/ABI/wire/API16cap14v15/R12原40/G1は維持する方針。parserの機能同値/失敗優先順/実protocol deadline境界は関連client試験で確認し、無関係な全Runtime/worldを積み増さない。

## 検証・保存・返却

新Navは元Cのcompile成功の意味的Red→Green、正方向/zero/逆・部分/複数移動/曖昧texture/弱支持/領域不足/新金/保護/商品とlegacy primaryを選ぶ。受領原画は調整用ローカル回帰であって未知評価や実機到達ではない。parserは旧正常・異常・深さ/nodes事前拒否・error優先順の同値と、status形/長nsを含む差分検証を行う。CPU代理・Linux計測と実iSH2秒成立を区別する。旧assertを削除/skipしてGreenにしない。

同じ正規sourceをsealし、標準public Mac/Ubuntuの限定CI・実compiler/全Mach-O/全source/IPA照合を確認。検証済みIPAと全コードを固定Releaseで匿名全取得/SHA/CRCまで照合する。新しい通常1-1ポーズから候補までrestart→金壁/通路候補→入店→全商品確認を一連としてまず2回依頼し、全画像/ZIP保存照合完了後のruntime/test-075-<run_id>.zip全回分を受領する。回収済み074の再実行を追加回収のため依頼しない。実機到達/毎拍/人超えは未受入。


## 独立設計確認と必須拒否

通常の局所追加として独立担当が上の最終構造を確認。初期のblur中心のみ/union面の支持不足、partial候補を幾何で先に落として全73texture差を省く案は採用しない。最終面は全73/95%/15pp/2帯100を同時に満たし、旧proofを変更しない。全旧L2個保持は必要条件ではなく、完全L自体が2D形であり全L×全9shift列挙の一意対応を要求するため、matched L>=1を限定追加として明記する。ABI/取消/未知入力/期限を広げる構造変更はしない。

単体では旧Lの一部消失正例に加え、他shift対応混在/採用L内部1cell欠損/旧L無し・最新だけL、背景静止で文字だけ9/18移動・出現消失、背景8/8.5pixelに文字9・unitcornerのpartial、global/right unitだがleft非unit/低gap、左右/上下片面の支持不足、raw best非unit/gap.08境界、21kernel隠れ1点がUI/ITEM/protect/UNKNOWN→known、旧primary維持を確認する。実画像は調整用局所回帰であり、全8.5pxの識別や実機完走の保証をしない。
