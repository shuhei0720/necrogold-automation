# TEST058 レビュー・検証

2026-11-09（日本時間）。[計画](../plans/test058-shop-dispatch.md)と[合成world期待16例](../tests/test058-world-cases.md)。実機の商品到達は未受入。

## 計画レビュー

fresh安全第1周clear。設計第1周P1「証跡snapshot/pinとJSON延期が未分離」、P2「world拍受付が未定義」を具体化し第2周clear。網羅第1周P1「旧FRESHの別AX期待との矛盾」「16例の初期条件/期待一覧不足」を、限定したAX共有期待への置換とworld表で解消し第2周clear。実Cで判明したsouth最小2goldのHUD隠れを、Red前のworld定義で正面5セル幅へ訂正した。入力4/7予算と商品/開通/進入の期待は緩めず、最終差分を確認する。

## ControllerのTDD

新query未対応の互換stub（常時0）でcompile成功→semantic assertion Redを観測し、private preparation epoch/getterの最小実装後、全153件（既存145＋新8）成功。初歩/retune/旧ID/ACK/UNKNOWN/取消/非MOVEは0、SAME/FRESHと2chainの同epoch、別logical MOVEの別epoch、元deadlineとsource/phase/walk/session horizonの等号/+1nsを検査した。旧symbolそのままのbaselineではないことを記録し、Red時sourcehash未採取を最終hashで代用しない。証拠はGit外 `test058-controller-tdd.json`。

## Runtime・world・実物

旧Runtimeの実Mac assertion Redと新Runtime/worldの検証は未実施。compile/環境失敗をRed、合成worldを実ゲームE2E、既知7PNGを未知受入と扱わない。実行後に結果を追記する。
