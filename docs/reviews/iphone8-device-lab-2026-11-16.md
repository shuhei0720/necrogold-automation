# iPhone 8の環境・診断harness検証

2026-11-16（日本時間）。[計画](../plans/iphone8-device-lab.md)に対応。対象は `necroprobe/device_lab.py` の診断と、サブiPhone 8の導入・基本起動・暗号RPC確認。本番iPhone 11への接続/導入は0回で、11の座標/変換/閾値、native製品・R12・既配布IPAは変更していない。

## 検証結果

- 対象取り違え・自動Network fallbackを許す仮実装に対し、4条件でassertion Red（error 0）を確認してから、expected UDID/明示transportの選択を実装。期限・app ID・host依存・Windows OWNER RIGHTSにも個別のRed→Green履歴がある。
- 独立差分レビューでWindowsのPython3.14が作るOWNER RIGHTS ACEの扱いを修正。実ownerをSYSTEM/Administrators/実行者へ制限した上でOWを許可し、不適格ownerや他readerを拒否する。修正確認後の未解決P0/P1はない。
- 最終関連検証は `python -m unittest tests.test_device_lab tests.test_capture -q` の37件成功（harness25＋既capture12）。対象固定、切断/入替、timeout/取消、保存衝突、画像/metadata拒否、公開summaryへのprivate sentinel非混入、署名suffixのpresence限定を含む。
- 追加の独立レビューで、Developer Mode不成立時のcapture理由がDDI欠落になるP2を修正。新1test/6条件のRed（5assert失敗・error0）→37件Green、該当差分の再確認で追加指摘なし。VPNのConnected確認とSideStoreの未到達も文書で分けた。
- Windows実backendはPython3.14.2/pymobiledevice3 11.55.1。USB要求はtransport_missingで停止し、Networkへfallbackしない。Networkを明示したcheckでlockdown/Developer Mode/DDIとcleanupを確認した。
- 同じ実機のNetwork captureはPNG 750×1334を生bytesで保存し、Windows→Cloudの全bytes/hash一致を確認。画像・manifest・設定はGit外。画像取得の成功をゲームの鮮度・geometry校正・認識や操作成功へ昇格させない。

最終版のWindows配置とUSB/Network checkは再確認した。初期captureは前提理由P2修正前の実績として保持。接続復旧後のHealth Check画面は最終版でも別runで新規取得し、PNG750×1334と全bytes/hash一致を確認した。

## 直接導入・XCTest・暗号RPCの実測

SideStoreの.xctest metadataエラーで実install前に残った署名済IPAを、Windows RAM内で元TEST107と照合した。v4検査では9 Mach-O/9 CodeDirectory・15資産・既存2.appexの署名時metadata・profile条件を確認。CMS署名/chainの暗号検証は未実施であり、静的検査の成功とOSによる実受理を分けた。署名済IPAのCloud転送、p12 entryの読取り、必須.xctest削除は0回。

完了応答付きの事前Browse、AFC原bytes/hash/size/mtimeの再照合、排他的receiptの保存後、正規InstallationProxyのInstallを1回実行した。OS installerのCompleteを受信し、完了応答付きの導入後一覧で正確な署名後IDと元配布物の両versionを照合した。結果不明時の自動再送は許可せず、通常Browseの部分応答を未導入証明に使わない。共有staging pathの非原子性を踏まえ、他の書込みを止めて実行した。

iPhone 8実機のtestStartServer開始からbootstrap成功・setup完了・待受・run loop投入を実ログで確認した。今回の観測範囲にteardownはない。さらに所有するloopback/SSH経路でschema `1.98.16-ngg2` / protocol 1 / 期待cap、今回専用client鍵の暗号pairing、端末承認後のconfig/logsの認証済み非UI応答を確認した。秘密値・fingerprint・実宛先・全ログは公開文書へ載せない。これらは組込みXCTest/serverの基本成立を示し、ゲーム入力・速度・長時間耐久を示さない。

8の追加読取りでは、device_infoはportrait cached 375×667pt/scale2、ゲームpage_source rootは667×375pt、G1 JPEGは1334×750px/source667×375/source_scale2/UIImage orientation2だった。異なる取得空間をそのまま入力変換へ結合せず、G1再エンコードとproduction原JPEGを区別する。停止RPC後のNotRunningはWindowsの対象model/process lookupで独立確認し、再起動後のタイトルを実画像で確認した。タイトル進行tapは、初めの2回がpreflightのsystem階層誤読で送信前block（receiptなし）。source確認による補正後の3回目だけ送信1回/ACKが成立し、G1画像でホームのダンジョンマスター・All Zones/zone1階段・ケイデンス開始位置を確認した。UNKNOWN再送の実績ではなく、ホーム移動は0回。native原JPEG/入力profileの資格やSTART-03全体の受入ではない。

## 証明範囲と未確認

診断harnessは `input_authorized=false` / `automation_ready=false` を常に出力する。harness自体のserver stageはprobe対象外でnot_run、geometryはblockedのまま。別経路の上記XCTest/schema/暗号RPC実測と混同しない。アプリpresenceだけでは署名/ABI同一性を証明しない。

既取得のPMD原画像とG1再エンコード画像は診断・校正資料で、production direct JPEG・実向き・入力geometryの受入へ代用しない。iPhone 8のgeometry/input profileと、[START-03](../requirements/necrogold.md)の自動停止確認→起動→ムービー実観測/スキップ→タイトルのスタート→ホーム開始位置から左1歩/下2歩→通常1-1は未実装・未受入。home限定のbeat不要をダンジョンnativeへ広げず、未知画面へ連続タップしない。通常lifecycle RPCのACKや単発skipも、自動開始経路の受入ではない。本番11の既存挙動を保護し、8の校正位置や成功を11へ流用しない。

取得時刻はWindows hostのmonotonic要求/応答域だけで、端末capture時刻やfreshnessは証明していない。実transportは固定PMDの選択APIと前後のusbmux列挙で照合し、sessionから独立に再測定したtransportではない。PMD connect factoryの途中で取消された未返却resourceの内部cleanupは未確認であり、その場合のcleanupをpassとしない。

新規harness/取得境界の関連検証を選び、無変更nativeの全体CI/IPA再ビルドは実施しない。旧私有資料は未移送のままで、未知評価・TEST107受入・商品到達率・速度・耐久を今回の合格へ含めない。

本更新の文書差分は独立レビューでP0/P1なし。相対リンク・diff checkと新規の私有識別子/鍵/私有hash非混入を確認した。文書更新のためharness/native/実機試験は再実行していない。
