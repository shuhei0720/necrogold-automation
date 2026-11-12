#!/bin/sh
# 保存済みTEST087の対象判定・ZIP保存を同じ実行IDで再開する。
set -eu
if [ "$#" -ne 0 ]; then
    echo 'TEST-087: 回復用コマンドには引数を付けないでください。' >&2
    exit 2
fi
cd "$(dirname "$0")"
recover_pid=
stop_recovery() {
    trap '' INT TERM
    if [ -n "$recover_pid" ]; then
        kill -TERM "$recover_pid" 2>/dev/null || true
        wait "$recover_pid" 2>/dev/null || true
    fi
    echo 'TEST-087: 回復を取り消しました。端末内の記録を保持しています。'
    exit 130
}
trap stop_recovery INT TERM
python3 -m necroprobe.recover087 &
recover_pid=$!
result=0
wait "$recover_pid" || result=$?
recover_pid=
exit "$result"
