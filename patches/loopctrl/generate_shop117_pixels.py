#!/usr/bin/env python3
"""Finite TEST117 procedural shop drawings from frozen public fixture inputs.

Only named drawing functions execute; no test case, compiler, private PNG or
phone Scene is loaded. The resulting pixels test the declared model geometry.
"""
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
INPUTS = (
    'tests/test_native_ring_bank094.py',
    'tests/test_native_shop_coverage102.py',
    'tests/test_native_offer_coverage104.py',
    'tests/test_native_single_sign_shop103.py',
    'tests/test_native_closed_price106.py',
    'tests/test_native_ring117.py',
    'necroprobe/non_target_features094.json',
    'necroprobe/goldshop_auth_features094.json',
    'necroprobe/closed_container_features105.json',
    'necroprobe/target_ring_features.json',
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def declarations(inputs, path, names, namespace):
    tree = ast.parse(inputs[path], filename=path)
    found = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in names]
    if tuple(node.name for node in found) != tuple(names):
        raise ValueError('Exact TEST117 drawing inventory changed: '+path)
    exec(compile(ast.Module(body=found, type_ignores=[]), path, 'exec'), namespace)
    return namespace


def draw(root=ROOT):
    inputs = {name: (root/name).read_bytes() for name in INPUTS}
    bank = json.loads(inputs['necroprobe/non_target_features094.json'])
    auth = json.loads(inputs['necroprobe/goldshop_auth_features094.json'])
    feature = json.loads(inputs['necroprobe/closed_container_features105.json'])['entry']
    common = dict(WIDTH=896, HEIGHT=414,
        FEATURES=json.loads(inputs['necroprobe/target_ring_features.json']),
        bank_data=lambda: bank, auth_data=lambda: auth)
    declarations(inputs, INPUTS[0], ('complete_shop',), common)
    declarations(inputs, INPUTS[1], ('_put', 'draw_faces'), common)
    offers = declarations(inputs, INPUTS[2], ('shop_pixels',), dict(common))
    single = declarations(inputs, INPUTS[3], ('shop_pixels',), dict(common))
    closed = declarations(inputs, INPUTS[4], ('closed_entry', 'shop_pixels'),
        dict(common, single=SimpleNamespace(**single), closed=SimpleNamespace(FEATURE=feature)))
    current = declarations(inputs, INPUTS[5], ('single_face_pixels', 'separate_chest_price_pixels'),
        dict(common, offer=SimpleNamespace(**offers), closed=SimpleNamespace(**closed)))
    drawings = (
        ('one_face', current['single_face_pixels'](), 285, 8),
        ('mixed_price', current['separate_chest_price_pixels'](), 177, 118),
    )
    patches = []
    for name, pixels, left, top in drawings:
        if len(pixels) != 896*414*4:
            raise ValueError('TEST117 procedural drawing dimensions')
        patch = b''.join(pixels[4*(y*896+left):4*(y*896+left+253)]
                         for y in range(top, top+146))
        if len(patch) != 253*146*4 or any(patch[i] != 255 for i in range(3,len(patch),4)):
            raise ValueError('TEST117 procedural drawing opacity')
        patches.append((name, patch, left, top))
    return patches, {name: sha(raw) for name, raw in inputs.items()}


def generate(destination, metadata=None):
    patches, identities = draw()
    rows = []; manifest = []
    for name, patch, left, top in patches:
        runs = []
        for y in range(146):
            row = patch[y*253*4:(y+1)*253*4]; start=0
            while start < 253:
                colour, end = row[4*start:4*start+3], start+1
                while end < 253 and row[4*end:4*end+3] == colour:
                    end += 1
                runs.append((end-start, *colour)); start=end
        rows.append('static const NG2Shop117Run ng2_shop117_'+name+'[] = {\n'+
            ''.join(' {'+','.join(str(v) for v in item)+'},\n' for item in runs)+'};\n')
        manifest.append(dict(name=name, width=253, height=146, left=left, top=top,
            rgba_sha256=sha(patch), run_count=len(runs)))
    header=('/* Public procedural drawings; not phone pixels or state. */\n'
        '#ifndef NG2_RUNTIME117_SHOP_PIXELS_H\n#define NG2_RUNTIME117_SHOP_PIXELS_H\n'
        '#include <stdint.h>\n'
        'typedef struct {uint16_t count;uint8_t r,g,b;} NG2Shop117Run;\n'+''.join(rows)+'#endif\n')
    destination.parent.mkdir(parents=True, exist_ok=True); destination.write_text(header)
    result=dict(schema='test117-procedural-shop-pixels-v1',
        generator_sha256=sha(Path(__file__).read_bytes()), source_sha256=identities,
        header_sha256=sha(destination.read_bytes()), patches=manifest,
        private_pixels_used=False, private_scene_used=False)
    if metadata is not None:
        metadata.write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('header',type=Path);parser.add_argument('--metadata',type=Path)
    args=parser.parse_args();print(json.dumps(generate(args.header,args.metadata)))
