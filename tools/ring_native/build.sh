#!/bin/sh
set -eu
if [ "$#" -ne 1 ]; then
    echo 'usage: sh build.sh OUTPUT' >&2
    exit 2
fi
cd "$(dirname "$0")"
python3 generate_features.py --check
${CC:-cc} -std=c11 -O2 -fno-fast-math -ffp-contract=off -fexcess-precision=standard -frounding-math -fno-stack-protector -Wall -Wextra -Werror -static -s -Wl,--build-id=none main.c unfilter.c observe.c icon.c word.c -o "$1" -lm
