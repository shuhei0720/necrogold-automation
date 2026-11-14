#!/bin/sh
# TEST098: native内の商品判定と対象なし周回を行い、全記録を照合してZIPを公開する。
set -eu
if [ "$#" -gt 2 ]; then
    echo 'TEST-098: --recovery と --python-crypto を必要に応じて指定してください。' >&2
    exit 2
fi
recovery_requested=0
for option in "$@"; do
    case "$option" in
        --recovery) recovery_requested=1 ;;
        --python-crypto) ;;
        *) echo 'TEST-098: 引数は --recovery または --python-crypto だけを指定してください。' >&2; exit 2 ;;
    esac
done
cd "$(dirname "$0")"
if ! client_version=$(python3 -m necroprobe.test098 --check); then
    echo 'TEST-098: 軽量クライアントの確認に失敗しました。' >&2
    exit 1
fi
if [ "$client_version" != 'native-cycle-v1 / 1.98.16-ngg2' ]; then
    echo 'TEST-098: 軽量クライアントの版が一致しません。試験は開始していません。' >&2
    exit 1
fi
if [ ! -r /dev/location ]; then
    echo 'TEST-098: /dev/locationを読めません。試験は開始していません。' >&2
    exit 1
fi
cat /dev/location >/dev/null 2>/dev/null &
keeper=$!
probe_pid=
cleanup() {
    kill "$keeper" 2>/dev/null || true
}
stop_probe() {
    trap '' INT TERM
    if [ -n "$probe_pid" ]; then
        kill -TERM "$probe_pid" 2>/dev/null || true
        wait "$probe_pid" 2>/dev/null || true
    fi
    echo 'TEST-098: 取消を要求しました。端末内の記録を保持しています。ゲームと保存結果を確認してください。'
    exit 130
}
trap cleanup 0
trap stop_probe INT TERM
sleep 1
if ! kill -0 "$keeper" 2>/dev/null; then
    echo 'TEST-098: 継続用プロセスを開始できませんでした。' >&2
    exit 1
fi
if [ "$recovery_requested" -eq 1 ]; then
    echo 'TEST-098: 前回の結果だけを回収し、全画像とZIPを照合します。新しいゲームは開始しません。位置情報は保存・送信しません。'
else
    echo 'TEST-098: 接続を確認し、端末内で商品判定・対象なし周回を行い、全画像とZIPを照合します。位置情報は保存・送信しません。'
fi
python3 -m necroprobe.test098 "$@" &
probe_pid=$!
result=0
wait "$probe_pid" || result=$?
probe_pid=
exit "$result"
