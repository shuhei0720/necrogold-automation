# iPhone 8の自動実機テスト環境

2026-11-16（日本時間）。ユーザー指定のWindows＋接続中のサブiPhone 8で、開発側から診断・起動・取得・結果回収を行う環境を構築する。[全体引き継ぎ](../handover-2026-11-16.md)・[SSH設定](windows-ssh-tailscale.md)・[元の接続課題](spare-iphone-remote-setup.md)を引き継ぐ。通常製品の同じiPhoneだけで完結する要件は維持する。

## 計画と境界

1. **ホストと対象確認。** Windowsの既存Pythonを使った専用venvへ診断ツールを導入し、実版を保存する。expected UDIDと要求transportを私有設定で固定し、別端末やUSBからNetworkへ自動fallbackしない。PnP認識・usbmux列挙・lockdown sessionを別々に扱う。
2. **接続・開発者イメージ。** 対象の実OS/Developer Modeを確認。iOS16.7用の固定DDI全bytes/hashを照合してからmountし、既にmountedなら読み取り確認する。既存の別imageを強制unmountしない。pairing/秘密値は保護されたGit外へ保存し、再作成やTrustが必要なら実エラーを基に端末操作を依頼する。
3. **導入と基本起動。** LoopCtrl/SideStore/ゲームの実導入版を確認。LoopCtrlの署名・導入を解決し、DDI mounted後に通常アプリを起動して組込みXCTestとserverを実測する。AllInOneへ外部 `xcuitest` runnerを無理に指定しない。既存runをkill/restartして回収を失わない。
4. **取得と回収。** 生画像・向き・寸法・取得元・要求/実transport・host時刻域・hashを私有manifestへ保存する。画面取得や非黒画像をゲーム認識/商品到達の成立としない。server成立後は、対象transportを固定したWindows loopback forwardとSSH等の到達経路を別に実測し、iPhone serverをWANへ公開しない。診断用Networkの成功でUSB転送も受入済みとは扱わない。
5. **再実行可能な診断harness。** 最初はtarget固定のcheckと入力しないcaptureを用意する。host/transport/lockdown/DevMode/DDI/app/server/geometryをpass・blocked・fail・not_runへ分ける。checkからpairing再作成・設定変更・アプリ導入・ゲーム入力を自動実行しない。例外/raw JSONを公開summaryへ出さない。
6. **自動ゲーム試験。** iPhone 8のgeometry/input profileを別の設計で校正し、旧profile/ABI/閾値/期限/候補保持を保存する。正しい取得と座標が実測されるまでnative start・ゲーム入力は許可しない。環境のcheck/capture完了だけで自動周回環境全体を完成扱いしない。

## 現在の実測と停止点

| 対象 | 確認した事実 |
| --- | --- |
| Windows | SSH/SFTP受入済み。Apple USB deviceのPnPはOK。Apple Mobile Device Processがloopback 27015で稼働 |
| 診断環境 | Windowsローカルの保護された専用folder/venvへPython3.14.2・pymobiledevice3 11.55.1を導入。harnessもこの環境へ配置して実版APIで動作確認した。既存system Python/iSH環境は更新していない |
| iPhone | iPhone10,1、iOS16.7.7/20H330、Activated、Developer Mode true、EnableWifiConnections true |
| 実transport | PnP対象と同じ端末がusbmuxにはNetworkとして列挙され、lockdown/アプリ照会と実LAN62078到達が成功。USB transportは未掲載で、USB受入は未完了。診断用Networkを明示選択して進める |
| アプリ | 日本版ネクロダンサー1.05/build03、iSH1.3.2、SideStore0.7.0を確認。LocalDevVPNは旧互換設定でもActive No、直接Remote ServerもReachable No。WireGuard1.0.16/build27＋SideStore EMProxyへ切替後、Health CheckはReachable/Pairing Verified・Lockdownとなった。LoopCtrlの導入再試行はエラーを受領し、内容を調査中。署名・導入の成功は未確認 |
| DDI | 16.7用dmg 7,432,520B/SHA `6e4449ff8c751b4432934ade838382c79330b096b865eebabbc1fa42ead9c185`、signature128B/SHA `4e82ee8aa75c5ecdd320e075b7d9e4ea2fc1915d0bb776007e8dbc5728ca5d86`をWindowsで照合。明示したNetwork transportでmountが実機成功し、mounted Developer imageのsignatureも一致した |
| 原寸取得 | `com.apple.mobile.screenshotr` / PMD ScreenshotServiceでPNG750×1334を実取得し、Windows内の保護領域へ原bytes/manifestを保存。EXIFなしの取得であり、検査の既定値1を取得済みEXIFや実向きの証明にしない。画像のゲーム状態・geometry/input対応・端末capture時刻・鮮度は未確定 |
| 自動化の受入 | 診断のcapture成功まで。LoopCtrl server/組込みXCTest、正しいinput座標、ゲームの移動/商品確認は未受入。harnessは常に `input_authorized=false` / `automation_ready=false` と返す |

DDIの取得元は、固定LoopCtrl上流が指定する [DeveloperDiskImage pin](https://github.com/doronz88/DeveloperDiskImage/tree/6eae353ae694bda1c421d4a3eee5459ae59c99a1/DeveloperDiskImages/16.7)。iOS16の組込みXCTest起動は固定上流でも実機未検証であり、mountや配布物照合で代用しない。

## 診断harnessのAPI・配置・検証

[実装](../../necroprobe/device_lab.py)の入口は `python -m necroprobe.device_lab check|capture --config <私有設定の絶対path> --timeout <秒>`。Windowsの専用venvで実行し、iSH clientへ診断用依存を追加しない。私有設定は `expected_udid`・`transport`（USBまたはNetwork）・保護されたGit外の `private_dir` を明示する。実版11.55.1以外を勝手に受け入れず、別端末・別transportへのfallbackやautopairは行わない。

| API/operation | 実行範囲と出力の意味 |
| --- | --- |
| `check` | host版、target/transport、lockdown identity/既存pairing、Developer Mode、DDI、対象appの有無を読む。app presenceは署名ID suffixを含む存在確認だけで、署名/ABI/serverの同一性や入力許可ではない |
| `capture` | 上記に加え、取得の直前/直後にtargetを再照合し、ScreenshotServiceの原bytesを保存・検査する。capture operationのpassが他stageのblocked/not_runを上書きせず、端末の自動試験全体の合格にもならない |
| PMD adapter | `create_using_usbmux`へ対象serial・connection_type・`autopair=False`・私有pairing cacheを指定。アプリ照会は11.55.1のbrowse API、captureはScreenshotServiceの実APIを使用し、所有したservice/sessionを終了する。CLIはWindows用event loopを用いるPMDの `run_in_loop` で実行する |
| 公開summary | schema `necro-device-lab-v1`。host/transport/lockdown/developer_mode/ddi/apps/server/capture/geometry/cleanupの各stageをpass・blocked・fail・not_runで分ける。例外本文・backend raw JSON・私有識別子を出さず、許可されたfieldだけを再構成する。serverは未probe、geometryは未検証のまま |
| 私有artifact | runごとの新規directoryに `capture.bin` と `manifest.json` を保存。既存出力を上書きしない。source・要求/実transport・host monotonicのrequest開始/response終了・size/SHAを記録し、device capture時刻はnull、`freshness_verified=false` とする。host時刻を端末capture時刻へ置換しない |

新規[device_lab単体](../../tests/test_device_lab.py)25件と、[capture関連](../../tests/test_capture.py)全12件の計37件が最終関連検証で成功した。対象不在/別端末/曖昧な列挙、USB要求に対するNetwork-only、取得前後の入替、未検証geometryでの入力0、画像/metadata不一致、既存出力保持、timeout/取消・cleanup失敗、Windows保護ACL、私有sentinelの非公開を検査した。単体/fakeの成功とは別に、Windowsへの配置・PMD11.55.1 API・明示Network・実機DDI/原寸captureまで確認した。最終実行は `python -m unittest tests.test_device_lab tests.test_capture -q`。

独立レビューでcaptureの前提理由がDeveloper Modeの不成立をDDI欠落へ誤表示するP2を修正した。新1test/6条件のRed（5assert失敗・error0）→上記37件Green、差分再確認で追加指摘なし。最終版をWindowsへ別directoryで配置・全archive hashを照合し、USB/Networkのcheckを再確認した。初期captureは修正前の版の実績として保持。接続復旧後のHealth Check画面は最終版でも新規取得し、PNG750×1334の全bytes/hash一致を別runで確認した。

## WireGuard経路の接続復旧

1. LocalDevVPNのConnectedだけではSideStoreのTCP到達は成立しなかった。通常UIで設定をConfirmし、旧トンネルIPも1回比較したがActive No。直接LAN endpointもReachable No。OSのローカルネットワーク一覧にSideStoreは無く、これだけで権限拒否とは確定しない。
2. App Storeの公式WireGuardを導入。[固定SideStore.conf](https://github.com/SideStore/SideStore/blob/6032424a0e56c1c319762e786099bdd9186a238b/SideStore.conf)をWindowsで取得し、235B・Git blob `30b1954a1e0a5f4c6fa651b07fc4591e72ad0f2f`・SHA256 `3a6d33c9a03c9b0ec0b16b99086a61d0580cc5953cd40ad9da9c2a06ed6ff1a5`を照合。本文/鍵はCloudへ送らず、Phone Documentsへ配置して全hashを再照合した。
3. SideStore Developer OptionsのStart EMProxyを操作し、端末上で公式configをWireGuardへimport/ON。その後の実Health CheckでVPN Connected、Reachable、Pairing Verified、Lockdownを確認。Windows内で構造化した診断logでもpeerのTCP62078がreachableとなった。認証・鍵・全log本文はCloudへ出していない。
4. Health CheckのDDI Not Mountedと、独立PMDのDeveloper image mounted trueは分けて保存。[固定IdeviceGateway](https://github.com/SideStore/minimuxer/blob/98c3c79982f813878e922ab42f9545314a700f0c/DeviceGateway/idevice/IdeviceGateway.swift#L1665)の判定はPersonalized型/新mount pathだけを受理し、iOS16のDeveloper型を偽陰性にする。通常導入のisReadyはDDI検査を既定falseで呼び、JITの検査とは別。警告だけを理由に再mountせず、IPA導入へ進めた。

接続改善の範囲は上記の到達とpairingまで。次の導入失敗は `SideStore.OperationError 3` / `extension 'LoopCtrlUITests.xctest' not found in targetAppBundle`。固定SideSignモデルは.appexだけを拡張辞書へ入れるが、InstallAppOperationはPlugIns直下の全Bundleを照合するため、必要な.xctestで失敗する。保持/削除UIの再試行では直る根拠がなく、同じ要求を繰り返さない。

署名・IPA作成・AFC転送後、実install前の停止であり、通常AFCの `/PublicStaging/<targetID>/app.ipa` に今回分が残存することを確認した。元TEST107のコード/資産と署名をWindows内で検査し、合格した既存stagingを正規InstallationProxy APIへ渡す経路を準備中。署名済みIPAにはALTCertificate.p12が埋め込まれる場合があるため、Cloudへ送らず、そのentryを展開しない。導入・組込みXCTest・ゲーム対応は未完了。

ゲーム起動時のGame Centerログインは初回だけ。通常はゲーム起動からオールゾーン入口の階段へ進む。最初の横向きPNG1334×750はGame Center案内画面で、ゲームplay画面の校正へ使用しない。

公開するのは一般コード/文書/許可項目だけ。UDID・実IP・署名team・認証・pairing・生画像/ログはGit外。[検証資料](../testing.md)の区分を維持し、raw取得を画面認識/入力/実ゲーム成功へ昇格しない。

## 残る課題

- WireGuardで接続は改善したが、導入再試行のエラーを絞り、LoopCtrlの署名・導入とiOS16 Start Server/組込みXCTestを確認する。DDIのmount成功をLoopCtrl起動の代用にせず、iloaderの同ID xctest拒否や旧方式のendpoint失敗も根拠なく解消済みにしない。
- USB transportの実受入、LoopCtrl serverの接続経路、captureの鮮度・production JPEG経路、geometry/inputの校正。旧896×414/portrait414×896ptの固定条件ではiPhone 8を動かさず、aspect guardや既assert/閾値/期限を緩めない。
- 旧実機資料の移送は未解決。TEST107の実機受入も未完了。新たに得た校正run/隣接画像を未知評価へ流用しない。
