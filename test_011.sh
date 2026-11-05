#!/bin/sh
# TEST-011: 導入済みP1.5で原画像と続行対象の候補参照だけを調べる。
set -eu
cd "$(dirname "$0")"
if ! python3 -c 'import necroprobe; raise SystemExit(0 if necroprobe.VERSION == "P1.5" else 1)'; then
    echo 'TEST-011: P1.5の展開先で実行してください。試験は開始していません。' >&2
    exit 1
fi
if ! python3 -c 'from PIL import Image' >/dev/null 2>&1; then
    echo 'TEST-011: Pillowが必要です。試験は開始していません。' >&2
    exit 1
fi
if [ ! -r /dev/location ]; then
    echo 'TEST-011: /dev/locationを読めません。試験は開始していません。' >&2
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
    echo 'TEST-011: 継続用プロセスの停止を要求します。結果保存後にiSHを終了してください。'
    exit 130
}
trap cleanup 0
trap stop_probe INT TERM
sleep 1
if ! kill -0 "$keeper" 2>/dev/null; then
    echo 'TEST-011: 継続用プロセスを開始できませんでした。' >&2
    exit 1
fi
echo 'TEST-011: 継続用プロセス開始。位置情報は保存・送信しません。'
python3 -m necroprobe.input_path --output runtime/test-011 "$@" &
probe_pid=$!
result=0
wait "$probe_pid" || result=$?
probe_pid=
echo 'TEST-011: 継続用プロセスの停止を要求します。結果保存後にiSHを終了してください。'
exit "$result"
