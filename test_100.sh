#!/bin/sh
# TEST100: native内の商品判定と対象なし周回を行い、全記録を照合してZIPを公開する。
set -eu
if [ "$#" -gt 3 ]; then
    echo 'TEST-100: --until-target、--recovery、--python-crypto を必要に応じて指定してください。' >&2
    exit 2
fi
recovery_requested=0
until_requested=0
for option in "$@"; do
    case "$option" in
        --recovery) recovery_requested=1 ;;
        --until-target) until_requested=1 ;;
        --python-crypto) ;;
        *) echo 'TEST-100: 引数は --until-target、--recovery、--python-crypto だけを指定してください。' >&2; exit 2 ;;
    esac
done
if [ "$recovery_requested" -eq 1 ] && [ "$until_requested" -eq 1 ]; then
    echo 'TEST-100: --until-target と --recovery は同時に指定できません。' >&2
    exit 2
fi
cd "$(dirname "$0")"
if ! client_version=$(python3 -m necroprobe.test100 --check); then
    echo 'TEST-100: 軽量クライアントの確認に失敗しました。' >&2
    exit 1
fi
if [ "$client_version" != 'native-trial-v1 / 1.98.16-ngg2' ]; then
    echo 'TEST-100: 軽量クライアントの版が一致しません。試験は開始していません。' >&2
    exit 1
fi
if [ ! -r /dev/location ]; then
    echo 'TEST-100: /dev/locationを読めません。試験は開始していません。' >&2
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
    echo 'TEST-100: 取消を要求しました。端末内の記録を保持しています。ゲームと保存結果を確認してください。'
    exit 130
}
trap cleanup 0
trap stop_probe INT TERM
sleep 1
if ! kill -0 "$keeper" 2>/dev/null; then
    echo 'TEST-100: 継続用プロセスを開始できませんでした。' >&2
    exit 1
fi
if [ "$recovery_requested" -eq 1 ]; then
    echo 'TEST-100: 前回の結果だけを回収し、全画像とZIPを照合します。新しいゲームは開始しません。位置情報は保存・送信しません。'
elif [ "$until_requested" -eq 1 ]; then
    echo 'TEST-100: 対象・候補・障害・停止まで、正常な区切りだけ次runへ進む連続試運転です。区切りごとに画像を回収します。位置情報は保存・送信しません。'
else
    echo 'TEST-100: 通常の有限runを一回試験し、全画像・記録と返却ZIPを照合します。位置情報は保存・送信しません。'
fi
python3 -m necroprobe.test100 "$@" &
probe_pid=$!
result=0
wait "$probe_pid" || result=$?
probe_pid=
exit "$result"
