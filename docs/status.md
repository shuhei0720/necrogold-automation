# 最新状態

更新: 2026-11-28（日本時間）。TEST126/build1001の実build・配布前照合が完了。[計画](plans/test126-startup-memory.md)・[検証](reviews/test126.md)・[実行手順](device-tests/README.md#test-126実行手順)。CODE75d3282、実CI46129888763/#1、appbuild1001。[固定公開](https://github.com/shuhei0720/necrogold-automation/releases/tag/test126-build1001)済み。SOURCEe9a86fa、3asset匿名全GET/全bytes一致。

Jetsamは今回のPID11645にメモリ上限終了/2098MiBを記録。保存scanをcompact summary/一件処理/64KiB逐次hashへ修正。実Macでは8namespaceのload64→20、同時保持8→2。host14/実Py3947/Swift14と実IPAが合格、元3artifact全SHA/CRC・1294CODE blob・37native/実compiler/全9MachOの五項目照合PASS（2f8f2aca）。

変更nativeはRPC/Spoolのみ、35保持。ゲームのController/Perception/Nav/Beat・元期限/予算/owner/UNKNOWN無再送、初回RSと125起動待機を保持。旧IPA278では126を開始しない。新実機のmemory peak/起動/商品到達/実RS/速度は未受入。元記録とpairingは保全する。
