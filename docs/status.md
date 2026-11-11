# 最新状態

更新: 2026-11-12（日本時間）。TEST082/build137。[計画](plans/test082-materials-motion.md)・[受領/実装/検証](reviews/test082.md)。code `c28c087b36742543c134ac1d8384160c1ca3b522`、run43055416759。TEST081の5run/97原PNGを全照合、原275で全3商品100/50/100を確認し到達1/5。全PAUSE/完収、正常見送り判断18/18枚と最終criticalを保持した。全取得画像保存ではない。

## 変更と根拠

既DIRTの追加pixel証拠で、bright FLOOR/半可視FLOOR/STONEの境界誤分類を補う。元palette行・gate/wood処理を維持し、固定非重複領域・元色/texture・黒入口条件を要求。校正97画像の29セルだけ変更、商品/保護/拍/署名等の非tile bytesは不変。逆方向移動と初回候補見逃しの観測原因へ対応した。

無金の実UP1は074の全旧STONE/非共線DIRT unique9と075の既pixel証拠をAND。正しい床補正で露呈した旧LEFT1回帰には、075唯一L/有限phaseとblur95%品質、別raw gradient75%品質/全73の元15pp識別をANDする。支持は合算せず、旧関数/閾値本文を変更しない。旧known27全部維持・回帰0、旧UNKNOWN9は実1だけUP1へ改善し残8維持。これは既資料の校正で実機受入ではない。

未発行stationary waitの拒否は元anchor同一/独立current-prefix/真mask非0だけ既ROUTE/MOTION診断へ記録する。ISSUED・mask0・期限/prefix不成立に偽行を足さず、停止/入力/票/予算・UNKNOWN無再送を維持。Runtime/core4・API16/cap15/client16/profilev2の20PNG/10MiBと旧v1回収は同一bytes。

## 検証・配布

新18作者単体Red→Green。同codeのhost43全Green（native36/client4/selector3）、旧070/081保存試験も今回実行。独立最終レビューGO。5実物verifier各1回PASS、失敗/再実行0。実C4/Swift5/RSP6・全9MachO/208marker不在・全612sourceとIPAを照合。Runtime048a…は未変更、別runの保存意味Red133を再利用し今回のGreenと区別する。公開後、固定3assetを匿名全GET/SHA/CRC照合して返す。

[TEST082/build137](https://github.com/shuhei0720/necrogold-automation/releases/tag/test082-build137)。[IPA](https://github.com/shuhei0720/necrogold-automation/releases/download/test082-build137/LoopCtrl.ipa)・[完全source](https://github.com/shuhei0720/necrogold-automation/releases/download/test082-build137/source.zip)。IPA0.3.4/build137/min16、17624649B/SHA `fcc148ce172dde647d541876ba0533f27935b7e3fcd7e147e1cf110de85178da`。closingは文書3件だけで製品不変。

SideStore更新→LoopCtrl完全終了/起動→Start Server/通常VPN。展開したtest_082.shのフォルダを選びiSHで実行する。

```sh
mkdir -p /mnt/necro_test082
mount -t ios . /mnt/necro_test082
cd /mnt/necro_test082 && sh test_082.sh
```

fresh通常1-1ポーズからrestart→金壁/通路候補→商店→全商品確認を5回。5秒以上ポーズならiSHへ戻り全画像/ZIP照合完了を待ち、runtime/test-082-<run_id>.zip全回分と商品全体可視/停止位置/逆方向/候補見逃し/拍間隔を依頼。081追加回収/再実行不要。

実5の最後のLEFT移動確認は未解決、実2の最初の拒否は原128/129不足で未確定。新実機の到達/見逃し率・恒久毎拍/人超え・対象認識/通知/対象なし自動周回は未受入。実機主軸/品質維持/固定時間上限なし。同じiPhoneのみ、raw/Scene/秘密値はGit外。[索引](context.md)。
