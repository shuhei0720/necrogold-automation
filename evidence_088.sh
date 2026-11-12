#!/bin/sh
# 保存済みTEST088を、対象判定未完の証拠ZIPとして回収する。
set -eu
if [ "$#" -ne 0 ]; then
    echo 'TEST-088: 証拠回収用コマンドには引数を付けないでください。' >&2
    exit 2
fi
cd "$(dirname "$0")"
evidence_pid=
stop_evidence() {
    trap '' INT TERM
    if [ -n "$evidence_pid" ]; then
        kill -TERM "$evidence_pid" 2>/dev/null || true
        wait "$evidence_pid" 2>/dev/null || true
    fi
    echo 'TEST-088: 証拠回収を取り消しました。端末内の記録を保持しています。'
    exit 130
}
trap stop_evidence INT TERM
python3 -m necroprobe.evidence088 &
evidence_pid=$!
result=0
wait "$evidence_pid" || result=$?
evidence_pid=
exit "$result"
