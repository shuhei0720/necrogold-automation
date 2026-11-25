#!/bin/sh
# TEST119: 端末内で連続周回し、停止後に全周の画像・記録を回収する。
set -eu
if [ "$#" -gt 3 ]; then
    echo 'TEST-119: --until-target、--recovery、--python-crypto を必要に応じて指定してください。' >&2
    exit 2
fi
recovery_requested=0
until_requested=0
for option in "$@"; do
    case "$option" in
        --recovery) recovery_requested=1 ;;
        --until-target) until_requested=1 ;;
        --python-crypto) ;;
        *) echo 'TEST-119: 引数は --until-target、--recovery、--python-crypto だけを指定してください。' >&2; exit 2 ;;
    esac
done
if [ "$recovery_requested" -eq 1 ] && [ "$until_requested" -eq 1 ]; then
    echo 'TEST-119: --until-target と --recovery は同時に指定できません。' >&2
    exit 2
fi
cd "$(dirname "$0")"
if ! client_version=$(python3 -m necroprobe.test119 --check); then
    echo 'TEST-119: 軽量クライアントの確認に失敗しました。' >&2
    exit 1
fi
if [ "$client_version" != 'native-device-failures-trial-v119 / 1.98.16-ngg2' ]; then
    echo 'TEST-119: 軽量クライアントの版が一致しません。試験は開始していません。' >&2
    exit 1
fi
if [ ! -r /dev/location ]; then
    echo 'TEST-119: /dev/locationを読めません。試験は開始していません。' >&2
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
    echo 'TEST-119: 取消を要求しました。原本を保持しています。終了表示と保存結果を確認してください。'
    exit 130
}
trap cleanup 0
trap stop_probe INT TERM
sleep 1
if ! kill -0 "$keeper" 2>/dev/null; then
    echo 'TEST-119: 継続用プロセスを開始できませんでした。' >&2
    exit 1
fi
if [ "$recovery_requested" -eq 1 ]; then
    echo 'TEST-119: 前回の全周の記録を回収します。新しいゲームは開始しません。位置情報は保存・送信しません。'
elif [ "$until_requested" -eq 1 ]; then
    echo 'TEST-119: 対象・候補・障害・容量上限・停止まで端末内で連続周回し、停止後に全周を回収します。位置情報は保存・送信しません。'
else
    echo 'TEST-119: 通常の有限runを一回試験し、全画像・記録と返却ZIPを照合します。位置情報は保存・送信しません。'
fi
python3 -m necroprobe.test119 "$@" &
probe_pid=$!
result=0
wait "$probe_pid" || result=$?
probe_pid=
exit "$result"
