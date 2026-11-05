#!/bin/sh
# TEST-010: 前回と同じ一時継続処理で、取得元の横長出力を測る。
set -eu
cd "$(dirname "$0")"
if ! python3 -c 'import necroprobe; print(necroprobe.VERSION); raise SystemExit(0 if necroprobe.VERSION == "P1.5" else 1)'; then
    echo 'TEST-010: P1.5の展開先で実行してください。試験は開始していません。' >&2
    exit 1
fi
if [ ! -r /dev/location ]; then
    echo 'TEST-010: /dev/locationを読めません。試験は開始していません。' >&2
    exit 1
fi
cat /dev/location >/dev/null 2>/dev/null &
keeper=$!
trap 'kill "$keeper" 2>/dev/null || true' 0
trap 'exit 130' INT
trap 'exit 143' TERM
sleep 1
if ! kill -0 "$keeper" 2>/dev/null; then
    echo 'TEST-010: 継続用プロセスを開始できませんでした。' >&2
    exit 1
fi
echo 'TEST-010: 継続用プロセス開始。位置情報は保存・送信しません。'
result=0
sh start_probe.sh --source-geometry --samples 12 --seconds 45 --output runtime/test-010 || result=$?
if kill -0 "$keeper" 2>/dev/null; then
    echo 'TEST-010: 継続用プロセスの停止を要求します。結果保存後にiSHを終了してください。'
else
    echo 'TEST-010: 継続用プロセスは既に終了していました。'
fi
exit "$result"
