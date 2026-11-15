"""Generate the native-only closed red container's inline numeric constants.

The fixed numeric JSON is the input; original images and the canonical i386
bank are not read or changed. The generated block belongs in NG2Ring.c after
the existing R94 bank type definitions.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEATURES = ROOT / 'necroprobe/closed_container_features105.json'
BEGIN = '/* BEGIN native-only closed red container105 generated numeric features */'
END = '/* END native-only closed red container105 generated numeric features */'


def generated_block(path=FEATURES):
    raw = Path(path).read_bytes()
    value = json.loads(raw)
    if (set(value) != {'schema', 'scope', 'entry'}
            or value['schema'] != 'ngg2-native-closed-container-feature-v1'):
        raise ValueError('closed105_schema')
    entry = value['entry']
    if (entry['id'] != 11 or entry['key'] != 'closed_red_chest'
            or entry['kind'] != 'ignored_container' or entry['word'] is not None
            or entry['contents'] != 'unobserved_and_out_of_scope'
            or len(entry['icons']) != 1):
        raise ValueError('closed105_entry')
    # Reuse the unchanged bounded generator's integer moments and array rules.
    spec = importlib.util.spec_from_file_location(
        'closed105_numeric_rules', Path(__file__).with_name('generate_non_target094.py'))
    numeric = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(numeric)
    key = 'r105_red_closed'
    lines = [BEGIN, '#define R105_CLOSED_RED_SHA256 "' + hashlib.sha256(raw).hexdigest() + '"']
    icon = entry['icons'][0]
    shape = entry['container_shape']
    if (icon['width'], icon['height'], shape['width'], shape['height']) != (36, 33, 36, 33):
        raise ValueError('closed105_dimensions')
    descriptor = numeric.icon_arrays(lines, key + '_0', icon)
    lines.append('static const R94BankIcon ' + key + '_icons[] = {' + descriptor + '};')
    for component in ('gold', 'dark'):
        numeric.word_array(lines, key + '_' + component,
            dict(width=36, height=33, ink=shape[component + '_ink'],
                 rows_hex=shape[component + '_rows_hex']), 36, 36)
    lines.append('static const R94ContainerShape ' + key + '_shape = '
        '{36,33,%d,%d,%s_gold,%s_dark};' %
        (shape['gold_ink'], shape['dark_ink'], key, key))
    lines.append('static const R94BankEntry ' + key + '_entry = '
        '{11,%s,%s_icons,1,0,0,0,0,R94_BANK_IGNORED_CONTAINER,&%s_shape};' %
        (json.dumps(entry['label'], ensure_ascii=False), key, key))
    lines.append(END)
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--features', type=Path, default=FEATURES)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument('--output', type=Path)
    destination.add_argument('--check-source', type=Path)
    args = parser.parse_args()
    body = generated_block(args.features)
    if args.check_source:
        source = args.check_source.read_text()
        if source.count(BEGIN) != 1 or source.count(END) != 1 or body not in source:
            raise ValueError('closed105_generated_block_changed')
    else:
        args.output.write_text(body)


if __name__ == '__main__':
    main()
