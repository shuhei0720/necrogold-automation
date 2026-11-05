#!/bin/sh
set -eu
cd "$(dirname "$0")"
# Run on a Linux host with gcc's i386 code generator. No 32-bit libc is needed.
for name in pixel_ops fast_crypto; do
    case "$name" in pixel_ops) output=pixels_i386.so;; *) output=fast_crypto_i386.so;; esac
    gcc -m32 -march=i386 -mno-sse -mno-sse2 -O2 -fPIC -ffreestanding \
        -fno-stack-protector -fno-builtin -shared -nostdlib -Wl,--build-id=none \
        -o "$output" "$name.c"
done
