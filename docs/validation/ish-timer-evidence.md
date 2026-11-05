# iSHのタイマー互換性: 根拠と限界

確認日: 2026-11-05（日本時間）。GitHub公式リポジトリをAPIで取得し確認した。

| 一次資料 | 確認した事実 |
| --- | --- |
| [iSH kernel/calls.c](https://github.com/ish-app/ish/blob/master/kernel/calls.c)、取得blob `23e3306b87508c4cc94a6e64987b31e18df20ac4` | syscall 104のsetitimerあり、105のgetitimer登録なし。現在の未実装呼出しはENOSYS |
| [iSH kernel/time.c](https://github.com/ish-app/ish/blob/master/kernel/time.c)、取得blob `d46c8d5f86566258ccb0204e7fe615c9e3de3a22` | sys_setitimerは以前のdelay/intervalをold_val_addrへ戻す |
| [2023-10-29の公式変更](https://github.com/ish-app/ish/commit/f8a7e44ccf2d94192a15ca319ca7112e69a38a7c) | 未実装syscallでSIGSYSを送る挙動をENOSYSへ変更した差分 |
| 上記commit直前のkernel/calls.c、blob `5c199acca05c831a04c7611d0ebc35a354ad1354` | getitimer登録なし、setitimer登録あり、未実装でSIGSYS送信 |
| [Python 3.9 signal.setitimer](https://docs.python.org/3.9/library/signal.html#signal.setitimer) | 戻り値は以前のdelay/interval。秒に0を指定すると解除 |

P1.2は毎RPCの暗号化・HTTP開始より前にgetitimerを呼ぶ。TEST-002は最初のdevice_info開始記録後、266.901ms以内（親の終了回収等を含む）にSIGSYS終了し、launch記録なし。互換性不具合が実行経路上にあり、観測と整合する。

ただし端末のiSHビルドとsyscall traceは未取得。SIGSYSだけから実際の番号105を観測したとは書かない。端末上でP1.3が起動/取得に成功したかはTEST-003の結果で別途確認する。

ホスト故障注入ではgetitimerを呼ぶと子へSIGSYSを送り、修正前は終了-31、修正後は認証済みdevice_info応答まで到達した。これは未実装呼出しをしなくなったことの回帰試験で、iSHエミュレーター・実iPhone・実ゲームE2Eではない。

setitimerによるPythonのsignal handlerは、長時間戻らないネイティブC処理を即時中断できるとは限らない。この制限は修正前からあるため、別の親プロセスが全セッション期限を監督し、TERM後も終了しなければKILLで回収する。親監督の6結合試験も回帰対象にする。
