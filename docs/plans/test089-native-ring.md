# TEST089: iSH内のコンパイル済み画素処理

2026-11-12（日本時間）。基準 e3eb9d59b10d2335a47f9c2d01296d908c7e92f2。

## 1. 目的と受領根拠

TEST088証拠73de7920の22member/20PNGを全CRC/SHA/size/strict load/certificateで照合。判定入力はauthority235の1枚、PNG SHA c661e2427972e375abd42571ac02a10fa00367a9945c98c37f58ba7c68d2ce40。実機は判定128秒超。開発実3.9の1回profileは2.888秒でicon70%・PNG復元27%、Paeth345/414行、1商品行・word0。調整runなのでholdoutへ数えない。小さなPython整理では解消しなかったため、画素ループを同じiSH内の静的i386実行ファイルへ移す。host全体は約43.8秒、nativeの相対実行時間は約10.9秒で、従来は全画像回収も判定前に直列化していた。両時計の絶対値を引かず、相対時間の差約33秒を診断回収等の待ちとして分ける。

## 2. 分担と非変更

Pythonは既PNGのformat/chunk/CRC/geometry/有限zlib inflateを維持し、filter付きrawをCへ渡す。Cはunfilter0..4/opaque確認・white/sign/BFS/商品行・icon・全3slotのwordの有限画素処理だけ。Pythonは最大4行×3slotのraw doubleを元のround9→word選別→3state→行選別で集約する。最終ACK PAUSE/最大2画像/feature/閾値/探索範囲・順/first-tie/sidecar/schema/元report/既immutableZIPを維持する。iOS app/API/native入力・歩行・IPA148は変更しない。host clientのoptional observerだけは今回拡張し、既定Noneを維持する。

TEST089のread-only/drained terminal manifestから最終authority画像を先に取得し、個別SHA/geometry/durable保存後に暫定結果を表示する。元image_export/offset/prefix/record.imagesの順序は変えず、取得するindexの順だけ優先する。targetならproof分類を省き、必要時だけ適格proofを優先する。cacheはmemoryだけにrun/export/source SHA/feature/classifierを結合し、全certificate後のprepareで画像と最終選択資格を再照合する。全画像照合前のsidecar/通常完了表示/入力許可は0。observer故障は固定reasonを保持して全画像回収を続け、最終prepareでpending失敗にする。取消は既条件のまま。画像回収自体の時間と判定時間は別指標とする。

## 3. 数値同値と有効範囲

Cの整数momentsは十分な幅で保持する。doubleの各単演算をvolatile64へ丸め、FMA/fastmath/excess precisionを抑制。mode0は3.9–3.11の逐次3値sum、mode1は3.12の補償sum。未来版を無条件でmode1へ入れず、未検証版はpending失敗とする。raw iconは0..1.000001だけを受理し、Pythonで元min(1.,raw)とround9を使う。固定featureのn320..344/targetVar>=7.65e6、RGBsum整数0..765、非定数sum variance最小(n-1)/nから、double誤差を包む1e-6の余裕を持つ数学上界とする。1.5等は拒否する。wordは全slotのraw最良を返し、Pythonでicon>=.80のslotだけ採用する。余分なC計算で候補条件を緩めない。C内のdecimal丸め/対象確定は行わない。名前探索範囲が幾何的に空の左右端だけword:nullを許し、読める絵はcandidateとして保持する（元None TypeErrorの潜在bugを修正）。

## 4. 閉プロトコル

stdinはmagic NG2RING1(8)、LE mode/length各u32、feature SHA32、raw SHA32の80B headerと、896×414 RGBA8 filter付きraw 1,484,190Bだけ。truncated/extra/mode/feature不一致拒否。SHAは親が証明済み入力から作り子が相関IDとしてechoするもので、CがSHAを独立計算したとはしない。fresh child/pipe・固定長とdigest結合で入力を結び付ける。

stdoutは最大8192B、protocol/features/input identity/rowsのexact schema。最大4row/各3slotのscore/box/wordだけ。親は重複key/NaN/余剰/数型/有限値/geometry/slot空間/IDを検証し、既sidecar validatorでも結果整合を再検証する。stderrも2048B上限。壊れた応答をunknownや陰性へ変換しない。

## 5. 子processと配布物

同梱の固定ELF32 little-endian i386 static helperをmanifestのsize/SHA/architecture/source/feature/toolchainへ結合する。Files providerのexecに依存せず、検証したbytesをhome/.necroprobe/enginesの0700専用cacheへatomic保存・再hash/ELF確認して絶対pathで起動する。cacheはrun inventory外。symlink/既cache不一致拒否、shell/envの任意pathや遅いPythonへの失敗fallbackは追加しない。

PollSelector等の非blocking pipeで有限stdin/stdout/stderrと取消を扱う。30秒期限・INT/TERM・非zero・protocol違反では子をterminate/kill/reapしFDを閉じ、sidecar未作成・通常pendingを維持する。時間切れをvalid unknownにしない。compilerは隔離したZig0.15.2/x86-linux-musl/i386、固定source/flags・musl/compiler runtime licenseを結合。Linux hostはIA32直接実行不可なので、QEMU i386で同じ実物を実行する。QEMU/Linux倍率をiSH秒の証明にしない。

## 6. 実装と独立レビュー

同じ独立担当が8項目計画/数値・境界を重点確認。C担当はtools/ring_native、bridge担当はnecroprobe/ring_native.py/対応単体、早期判定担当はring_early/optional observer、rootはPNG共有化/有限集約・manifest/binary/入口/配布を担当する。raw/実profile/元画像はGit外。P0は修正し、P1/P2の残存は理由と次工程を示す。最大3周の範囲で変更境界を確認し、過去版の閉じたレビューを形式的に再開しない。

## 7. 選択検証とコミット前条件

有効Assertion Red→最小Green。PNG全filter/alpha/CRC/finite inflate、CのBFS/行並び/word/同率/float境界、実i386 packet/出力境界、bridgeのhash/install/cache・truncated/extra/overflow/nonzero/timeout/INTTERM/子回収を選ぶ。旧3.9 target6/回復/必要publicationのみを統合後一回、元309と今回235は実i386の全field同値/所要時間を一回確認する。実機PNGは校正資料で未知評価とはしない。C全画素への移設は実物バイナリで検証し、x86_64版だけを配らない。

source/生成feature/ELF/license/manifestを全照合し、同toolchainの再build同一性も確認する。旧iOS native/API/IPAのbytes不変を検証し、新Mac/IPA/無関係な全33群は実行しない。

稀な対象の実機周回を精度検証の前提にしない。固定8runの人陰性4/不明4と校正画像、同じfeatureからの位置/明度/部分欠けの合成例を区別し、固定期待を変更せず実Cで検証する。未知陽性holdoutは0。早期判定の取得順/再開/cache結合/例外隔離/通常sidecar同一性は新単体で確認する。

## 8. 配布・受入・リファクタリング

固定GitHub Releaseに検証済みhelper入り完全source/SHAを保存し、匿名GET/CRC/全tracked blob/actualtagを照合。まず同088 pendingを新engineで判定/通常ZIPまで完了する実機確認、続いて通常1-1ポーズからTEST089の一連試験を依頼し全run ZIP/指輪表示/処理秒を受領する。既evidence回収を繰り返さない。判定失敗は理由を説明してpendingを残す。商品到達→暫定指輪結果→全画像/ZIP完了を分けて実iSH秒を測る。開発Linux/QEMU倍率を人間速度達成の証明にしない。iSHの実秒・到達率/未知陽性精度・歩行停止は未受入として区別し、実機結果後に必要な整理を行う。
