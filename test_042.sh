#!/bin/sh
# TEST-042: 経路準備・拍同期・送信待機を改善。直線は最大4拍。画面端0・最大16入力。
set -eu
if [ "$#" -gt 1 ] || { [ "$#" -eq 1 ] && [ "$1" != '--python-crypto' ]; }; then
    echo 'TEST-042: 引数なし、または単独の --python-crypto だけを指定してください。試験は開始していません。' >&2
    exit 2
fi
cd "$(dirname "$0")"
if ! python3 -m necroprobe.preflight P1.5 shop-walk-v27; then
    echo 'TEST-042: P1.5 / shop-walk-v27とPillowの確認に失敗しました。試験は開始していません。' >&2
    exit 1
fi
if [ ! -r /dev/location ]; then
    echo 'TEST-042: /dev/locationを読めません。試験は開始していません。' >&2
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
    echo 'TEST-042: 継続用プロセスの停止を要求します。結果保存後にiSHを終了してください。'
    exit 130
}
trap cleanup 0
trap stop_probe INT TERM
sleep 1
if ! kill -0 "$keeper" 2>/dev/null; then
    echo 'TEST-042: 継続用プロセスを開始できませんでした。' >&2
    exit 1
fi
echo 'TEST-042: 継続用プロセス開始。位置情報は保存・送信しません。'
python3 -m necroprobe.shop_walk --output runtime/test-042 "$@" &
probe_pid=$!
result=0
wait "$probe_pid" || result=$?
probe_pid=
echo 'TEST-042: 継続用プロセスの停止を要求します。結果保存後にiSHを終了してください。'
exit "$result"
