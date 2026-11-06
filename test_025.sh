#!/bin/sh
# TEST-025: 既存NG-G1で金壁から商品可視まで。画面端0、最大16入力、直線床は最大2拍。
set -eu
if [ "$#" -gt 1 ] || { [ "$#" -eq 1 ] && [ "$1" != '--python-crypto' ]; }; then
    echo 'TEST-025: 引数なし、または単独の --python-crypto だけを指定してください。試験は開始していません。' >&2
    exit 2
fi
cd "$(dirname "$0")"
if ! python3 -c 'import necroprobe; from necroprobe.shop_walk import REVISION; raise SystemExit(0 if necroprobe.VERSION == "P1.5" and REVISION == "shop-walk-v10" else 1)'; then
    echo 'TEST-025: P1.5 / shop-walk-v10の展開先で実行してください。試験は開始していません。' >&2
    exit 1
fi
if ! python3 -c 'from PIL import Image' >/dev/null 2>&1; then
    echo 'TEST-025: Pillowが必要です。試験は開始していません。' >&2
    exit 1
fi
if [ ! -r /dev/location ]; then
    echo 'TEST-025: /dev/locationを読めません。試験は開始していません。' >&2
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
    echo 'TEST-025: 継続用プロセスの停止を要求します。結果保存後にiSHを終了してください。'
    exit 130
}
trap cleanup 0
trap stop_probe INT TERM
sleep 1
if ! kill -0 "$keeper" 2>/dev/null; then
    echo 'TEST-025: 継続用プロセスを開始できませんでした。' >&2
    exit 1
fi
echo 'TEST-025: 継続用プロセス開始。位置情報は保存・送信しません。'
python3 -m necroprobe.shop_walk --output runtime/test-025 "$@" &
probe_pid=$!
result=0
wait "$probe_pid" || result=$?
probe_pid=
echo 'TEST-025: 継続用プロセスの停止を要求します。結果保存後にiSHを終了してください。'
exit "$result"
