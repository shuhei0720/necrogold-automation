#!/bin/sh
# TEST075: 端末内へ全画像を永続保存し、検証済みの返却ZIPを一度公開する。
set -eu
if [ "$#" -gt 1 ] || { [ "$#" -eq 1 ] && [ "$1" != '--python-crypto' ]; }; then
    echo 'TEST-075: 引数なし、または単独の --python-crypto だけを指定してください。' >&2
    exit 2
fi
cd "$(dirname "$0")"
if ! client_version=$(python3 -m necroprobe.test075 --check); then
    echo 'TEST-075: 軽量クライアントの確認に失敗しました。' >&2
    exit 1
fi
if [ "$client_version" != 'native-walk-v15 / 1.98.16-ngg2' ]; then
    echo 'TEST-075: 軽量クライアントの版が一致しません。試験は開始していません。' >&2
    exit 1
fi
if [ ! -r /dev/location ]; then
    echo 'TEST-075: /dev/locationを読めません。試験は開始していません。' >&2
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
    echo 'TEST-075: 取消を要求しました。端末内の記録を保持しています。ゲームと保存結果を確認してください。'
    exit 130
}
trap cleanup 0
trap stop_probe INT TERM
sleep 1
if ! kill -0 "$keeper" 2>/dev/null; then
    echo 'TEST-075: 継続用プロセスを開始できませんでした。' >&2
    exit 1
fi
echo 'TEST-075: 接続を確認し、全画像の保存とZIPの照合まで行います。位置情報は保存・送信しません。'
python3 -m necroprobe.test075 "$@" &
probe_pid=$!
result=0
wait "$probe_pid" || result=$?
probe_pid=
exit "$result"
