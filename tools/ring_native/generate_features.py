"""Reproduce C constants only from the fixed public derived feature asset."""
import argparse
import hashlib
import json
from pathlib import Path

EXPECTED = '202322326d86f600b300713ca8572b592f3beb59ceff6e6f6e58ef9cb3b728b4'


def outputs():
    base = Path(__file__).resolve().parents[2]
    raw = (base/'necroprobe/target_ring_features.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise ValueError('ring_features_changed')
    value = json.loads(raw)
    if value['schema'] != 'ngg2-ring-features-v1' or value['word']['ink'] != 239:
        raise ValueError('ring_features_invalid')
    lines = ['/* Generated from fixed derived features; no original images. */',
             '#include "feature_sha.h"',
             'typedef struct { int dx,dy,r,g,b; } Bright;',
             'typedef struct { int dx,dy; } Dark;',
             'typedef struct { int width,height,count,dark_count; const Bright *bright; const Dark *dark; int64_t energy,target_sum; double target_var; } Sprite;']
    rows = []
    for index, sprite in enumerate(value['icons']):
        bright, dark = sprite['bright'], sprite['dark']
        intensities = tuple(sum(point[2:]) for point in bright)
        total = sum(intensities)
        energy = sum(sum(c*c for c in point[2:]) for point in bright)
        variance = sum(v*v for v in intensities)-total*total/len(bright)
        lines.append('static const Bright bright_%d[] = {%s};' %
                     (index, ','.join('{'+','.join(map(str, point))+'}' for point in bright)))
        lines.append('static const Dark dark_%d[] = {%s};' %
                     (index, ','.join('{'+','.join(map(str, point))+'}' for point in dark)))
        rows.append('{%d,%d,%d,%d,bright_%d,dark_%d,INT64_C(%d),INT64_C(%d),%s},' %
                    (sprite['width'], sprite['height'], len(bright), len(dark), index, index,
                     energy, total, float(variance).hex()))
    lines += ['static const Sprite sprites[] = {', *rows, '};']
    word = ['/* Generated from the same fixed derived feature asset. */',
            'static const uint64_t word_reference[11][2] = {']
    for row in value['word']['rows_hex']:
        bits = int(row, 16)
        word.append('{UINT64_C(0x%016x),UINT64_C(0x%05x)},' % (bits&((1 << 64)-1), bits >> 64))
    word.append('};')
    return {'feature_sha.h': '#define FIXED_FEATURE_SHA256 "'+EXPECTED+'"\n',
            'features.h': '\n'.join(lines)+'\n', 'word_features.h': '\n'.join(word)+'\n'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent
    for name, text in outputs().items():
        path = folder/name
        if args.check:
            if path.read_bytes() != text.encode():
                raise ValueError('ring_generated_constants_changed')
        else:
            path.write_text(text)


if __name__ == '__main__':
    main()
