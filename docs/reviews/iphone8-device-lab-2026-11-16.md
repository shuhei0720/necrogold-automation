# iPhone 8の診断harness検証

2026-11-16（日本時間）。[計画](../plans/iphone8-device-lab.md)に対応。対象は新規 `necroprobe/device_lab.py` と関連試験で、native製品・R12・既配布IPAは変更しない。

## 検証結果

- 対象取り違え・自動Network fallbackを許す仮実装に対し、4条件でassertion Red（error 0）を確認してから、expected UDID/明示transportの選択を実装。期限・app ID・host依存・Windows OWNER RIGHTSにも個別のRed→Green履歴がある。
- 独立差分レビューでWindowsのPython3.14が作るOWNER RIGHTS ACEの扱いを修正。実ownerをSYSTEM/Administrators/実行者へ制限した上でOWを許可し、不適格ownerや他readerを拒否する。修正確認後の未解決P0/P1はない。
- 最終関連検証は `python -m unittest tests.test_device_lab tests.test_capture -q` の37件成功（harness25＋既capture12）。対象固定、切断/入替、timeout/取消、保存衝突、画像/metadata拒否、公開summaryへのprivate sentinel非混入、署名suffixのpresence限定を含む。
- 追加の独立レビューで、Developer Mode不成立時のcapture理由がDDI欠落になるP2を修正。新1test/6条件のRed（5assert失敗・error0）→37件Green、該当差分の再確認で追加指摘なし。VPNのConnected確認とSideStoreの未到達も文書で分けた。
- Windows実backendはPython3.14.2/pymobiledevice3 11.55.1。USB要求はtransport_missingで停止し、Networkへfallbackしない。Networkを明示したcheckでlockdown/Developer Mode/DDIとcleanupを確認した。
- 同じ実機のNetwork captureはPNG 750×1334を生bytesで保存し、Windows→Cloudの全bytes/hash一致を確認。画像・manifest・設定はGit外。画像取得の成功をゲームの鮮度・geometry校正・認識や操作成功へ昇格させない。

最終版のWindows配置とUSB/Network checkは再確認した。初期captureは前提理由P2修正前の実績として保持。接続復旧後のHealth Check画面は最終版でも別runで新規取得し、PNG750×1334と全bytes/hash一致を確認した。

## 証明範囲と未確認

`input_authorized=false` / `automation_ready=false` を常に出力する。serverはnot_run、geometryはblocked。アプリpresenceは署名/ABI同一性を証明しない。iPhone 8へのLoopCtrl導入・組込みXCTest・実ゲーム試験は未完了。

取得時刻はWindows hostのmonotonic要求/応答域だけで、端末capture時刻やfreshnessは証明していない。実transportは固定PMDの選択APIと前後のusbmux列挙で照合し、sessionから独立に再測定したtransportではない。PMD connect factoryの途中で取消された未返却resourceの内部cleanupは未確認であり、その場合のcleanupをpassとしない。

新規harness/取得境界の関連検証を選び、無変更nativeの全体CI/IPA再ビルドは実施しない。旧私有資料は未移送のままで、未知評価・TEST107受入・商品到達率・速度・耐久を今回の合格へ含めない。
