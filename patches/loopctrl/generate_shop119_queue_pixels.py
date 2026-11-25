#!/usr/bin/env python3
"""Public procedural TEST119 queue component drawings, never phone pixels."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

INPUTS = ('tests/test_native_offer_coverage104.py',
          'tests/test_native_shop_coverage102.py',
          'tests/test_native_ring_bank094.py',
          'necroprobe/non_target_features094.json',
          'necroprobe/target_ring_features.json',
          'necroprobe/goldshop_auth_features094.json')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def generate(destination, metadata=None):
    inputs = {name: (ROOT/name).read_bytes() for name in INPUTS}
    identities = {name: sha(raw) for name, raw in inputs.items()}
    namespace = dict(WIDTH=896, HEIGHT=414,
        FEATURES=json.loads(inputs['necroprobe/target_ring_features.json']),
        bank_data=lambda: json.loads(inputs['necroprobe/non_target_features094.json']),
        auth_data=lambda: json.loads(inputs['necroprobe/goldshop_auth_features094.json']))
    # Load only the exact public drawing functions, with their data explicitly
    # bound above. Importing test modules would allow their fixture environment
    # overrides to select pixels not described by this receipt.
    for name, names in (('tests/test_native_ring_bank094.py', ('complete_shop',)),
                        ('tests/test_native_shop_coverage102.py', ('_put', 'draw_faces')),
                        ('tests/test_native_offer_coverage104.py', ('shop_pixels',))):
        tree = ast.parse(inputs[name], filename=name)
        functions = [node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name in names]
        if tuple(node.name for node in functions) != names:
            raise ValueError('TEST119 exact public drawing inventory: '+name)
        exec(compile(ast.Module(body=functions, type_ignores=[]), name, 'exec'), namespace)
    declarations = []
    patches = {}
    # A single full board deliberately lacks complete negative authority.
    # Three actual offers and prices are still positively visible.
    for name, target in (('normal', False), ('candidate', True)):
        raw = namespace['shop_pixels'](left=304, sy=87, faces=((-15, -14, 30, 29), None),
                          target=target, target_name=False)
        patch = b''.join(raw[4*(y*896+214):4*(y*896+467)] for y in range(52, 198))
        runs = []
        for y in range(146):
            row = patch[4*y*253:4*(y+1)*253]
            start = 0
            while start < 253:
                colour, end = row[4*start:4*start+3], start+1
                while end < 253 and row[4*end:4*end+3] == colour:
                    end += 1
                runs.append((end-start, *colour))
                start = end
        declarations.append('static const NG2Queue119PixelRun ng2_queue119_'+name+'[] = {\n'+
            ''.join(' {'+','.join(map(str, run))+'},\n' for run in runs)+'};\n')
        patches[name] = dict(rgba_sha256=sha(patch), run_count=len(runs))
    text = ('/* Public procedural drawings; no phone pixels or Scene state. */\n'
            '#ifndef NG2_RUNTIME119_QUEUE_PIXELS_H\n#define NG2_RUNTIME119_QUEUE_PIXELS_H\n'
            '#include <stdint.h>\n'
            'typedef struct {uint16_t count;uint8_t r,g,b;} NG2Queue119PixelRun;\n'+
            ''.join(declarations)+'#endif\n')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text)
    result = dict(schema='test119-procedural-queue-pixels-v1',
        generator_sha256=sha(Path(__file__).read_bytes()), source_sha256=identities,
        header_sha256=sha(destination.read_bytes()), left=214, top=52,
        width=253, height=146, patches=patches,
        private_pixels_used=False, private_scene_used=False)
    if metadata is not None:
        metadata.write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('header', type=Path)
    parser.add_argument('--metadata', type=Path)
    args = parser.parse_args()
    print(json.dumps(generate(args.header, args.metadata)))
