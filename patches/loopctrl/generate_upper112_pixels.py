#!/usr/bin/env python3
"""Generate a procedural TEST112 shop patch from frozen public fixture inputs.

Uses Python's standard library only. It executes the named drawing functions
from existing tests with a fixed numeric bank, not Pillow or private images.
The generated header is a compiler input and belongs in the Runtime receipt.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUTS = (
    'tests/test_native_ring_bank094.py',
    'tests/test_native_shop_coverage102.py',
    'tests/test_native_offer_coverage104.py',
    'necroprobe/non_target_features094.json',
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def draw_patch(root=ROOT):
    inputs = {name: (root/name).read_bytes() for name in INPUTS}
    namespace = {'WIDTH': 896, 'HEIGHT': 414, 'FEATURES': {},
                 'bank_data': lambda: json.loads(inputs[INPUTS[3]]),
                 'auth_data': lambda: {}}
    for name, functions in ((INPUTS[0], ('complete_shop',)),
                            (INPUTS[1], ('_put', 'draw_faces')),
                            (INPUTS[2], ('shop_pixels',))):
        tree = ast.parse(inputs[name], filename=name)
        selected = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name in functions]
        if tuple(node.name for node in selected) != functions:
            raise ValueError('Exact procedural drawing function inventory changed: ' + name)
        module = ast.Module(body=selected, type_ignores=[])
        exec(compile(module, name, 'exec'), namespace)
    pixels = namespace['shop_pixels'](left=267, sy=267)
    patch = b''.join(pixels[4*(y*896+177):4*(y*896+430)] for y in range(232, 378))
    if len(patch) != 253*146*4 or any(patch[index] != 255 for index in range(3, len(patch), 4)):
        raise ValueError('Procedural patch geometry/opacity differs')
    return patch, {name: sha(raw) for name, raw in inputs.items()}


def generate(destination, metadata=None):
    patch, identities = draw_patch()
    runs = []
    for y in range(146):
        row = patch[y*253*4:(y+1)*253*4]
        start = 0
        while start < 253:
            colour, end = row[4*start:4*start+3], start+1
            while end < 253 and row[4*end:4*end+3] == colour:
                end += 1
            runs.append((end-start, *colour))
            start = end
    text = ('/* Generated from public procedural fixtures; no phone pixels. */\n'
            '#ifndef NG2_RUNTIME112_UPPER_SHOP_H\n#define NG2_RUNTIME112_UPPER_SHOP_H\n'
            '#include <stdint.h>\n'
            'typedef struct { uint16_t count;uint8_t r,g,b; } NG2Upper112Run;\n'
            'static const NG2Upper112Run ng2_upper112_runs[] = {\n' +
            ''.join(' {'+','.join(str(value) for value in row)+'},\n' for row in runs) +
            '};\n#endif\n')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text)
    result = dict(schema='test112-procedural-upper-shop-v1', source_sha256=identities,
                  generator_sha256=sha(Path(__file__).read_bytes()),
                  width=253, height=146, rgba_sha256=sha(patch), run_count=len(runs),
                  header_sha256=sha(destination.read_bytes()), private_pixels_used=False)
    if metadata is not None:
        metadata.write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('header', type=Path)
    parser.add_argument('--metadata', type=Path)
    args = parser.parse_args()
    print(json.dumps(generate(args.header, args.metadata)))


if __name__ == '__main__':
    main()
