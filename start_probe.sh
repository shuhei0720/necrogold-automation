#!/bin/sh
set -eu
cd "$(dirname "$0")"
if ! python3 -c 'from PIL import Image' >/dev/null 2>&1; then
    echo 'Pillowが必要です。iSHで apk add py3-pillow を実行してから再実行してください。' >&2
    exit 2
fi
exec python3 -m necroprobe capture --launch-game "$@"
