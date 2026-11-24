#!/usr/bin/env python3
"""TEST118 finite public shop drawing; no phone pixels or Scene injection."""
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
    namespace = dict(WIDTH=896, HEIGHT=414, FEATURES={},
        bank_data=lambda: json.loads(inputs[INPUTS[3]]), auth_data=lambda: {})
    for name, names in ((INPUTS[0], ('complete_shop',)),
                        (INPUTS[1], ('_put', 'draw_faces')),
                        (INPUTS[2], ('shop_pixels',))):
        tree = ast.parse(inputs[name], filename=name)
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        if tuple(node.name for node in functions) != names:
            raise ValueError('exact public TEST118 drawing function inventory: '+name)
        exec(compile(ast.Module(body=functions, type_ignores=[]), name, 'exec'), namespace)
    # One actual SHOP face has two possible three-slot interpretations while
    # clipped: five potential cells. The physical offers remain three.
    left, sy = 267, 299
    pixels = namespace['shop_pixels'](left=left, sy=sy, faces=((-15, -14, 30, 29), None))
    patch = b''.join(pixels[4*(y*896+177):4*(y*896+430)] for y in range(264, 410))
    if len(patch) != 253*146*4 or any(patch[i] != 255 for i in range(3, len(patch), 4)):
        raise ValueError('TEST118 public shop drawing dimensions or opacity')
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
            runs.append((end-start, *colour)); start = end
    text = ('/* Public procedural drawing; not phone pixels or state. */\n'
        '#ifndef NG2_RUNTIME118_SHOP_PIXELS_H\n#define NG2_RUNTIME118_SHOP_PIXELS_H\n'
        '#include <stdint.h>\n'
        'typedef struct {uint16_t count;uint8_t r,g,b;} NG2Shop118Run;\n'
        'static const NG2Shop118Run ng2_shop118_upper[] = {\n'+
        ''.join(' {'+','.join(str(v) for v in item)+'},\n' for item in runs)+'};\n#endif\n')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text)
    result = dict(schema='test118-procedural-shop-pixels-v1',
        generator_sha256=sha(Path(__file__).read_bytes()), source_sha256=identities,
        header_sha256=sha(destination.read_bytes()), width=253, height=146,
        left=177, top=264, rgba_sha256=sha(patch), run_count=len(runs),
        private_pixels_used=False, private_scene_used=False)
    if metadata is not None:
        metadata.write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('header', type=Path); parser.add_argument('--metadata', type=Path)
    args = parser.parse_args()
    print(json.dumps(generate(args.header, args.metadata)))
