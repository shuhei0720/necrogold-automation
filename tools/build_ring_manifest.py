"""Bind the shipped static i386 helper to its complete source and toolchain."""
import argparse
import hashlib
import json
from pathlib import Path

from necroprobe.ring_native import _elf
from necroprobe.target_assessment import FEATURE_SHA256


FLAGS = ('-target x86-linux-musl -mcpu=i386 -std=c11 -O2 -fno-fast-math '
         '-ffp-contract=off -fexcess-precision=standard -frounding-math '
         '-fno-stack-protector -Wall -Wextra -Werror -static -s -Wl,--build-id=none -lm')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    binary = root/'necroprobe/bin/ring-i386'
    raw = binary.read_bytes(); _elf(raw)
    paths = sorted(p for p in (root/'tools/ring_native').iterdir() if p.is_file())
    paths += [root/'necroprobe/target_ring_features.json', Path(__file__).resolve()]
    sources = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    assert sources['necroprobe/target_ring_features.json'] == FEATURE_SHA256
    value = dict(schema='ngg2-ring-engine-v1', protocol='ngg2-ring-raw-v1', binary='ring-i386',
        binary_bytes=len(raw), binary_sha256=hashlib.sha256(raw).hexdigest(),
        features_sha256=FEATURE_SHA256, sources=sources,
        toolchain=dict(name='zig', version='0.15.2', target='x86-linux-musl', cpu='i386',
            flags=FLAGS, libc='musl-bundled-with-zig-0.15.2', source_date_epoch='0'))
    manifest = root/'necroprobe/ring_native_manifest.json'
    encoded = (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()
    if args.check:
        assert manifest.read_bytes() == encoded, 'ring manifest differs from packaged sources'
    else:
        manifest.write_bytes(encoded)
    print(json.dumps(dict(binary_bytes=len(raw), binary_sha256=value['binary_sha256'],
                          sources=len(sources), check=args.check)))


if __name__ == '__main__':
    main()
