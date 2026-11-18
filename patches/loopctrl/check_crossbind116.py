"""Read-only actual Swift export -> Python client proof, with no game RPC.

Input is normal_chain from check_runtime116's actual Mac artifact. Its clock,
pixels and archive claim are procedural; its Spool/RPC bytes are actual. No
fields are repaired, no native result is classified here, and no ZIP claim is
turned into proof of an actual host archive or iPhone acceptance.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct
import sys
import tempfile
import zlib

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from necroprobe import campaign116 as campaign
from necroprobe import native_cycle as cycle

SPEC = cycle.IRREGULAR_PROTOCOL
RASTER_BYTES = 896 * 414 * 4


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read(root, name, limit=2 * 1024 * 1024):
    path = PurePosixPath(name)
    require(not path.is_absolute() and path.parts and all(p not in ('', '.', '..') for p in path.parts),
            'artifact_path')
    current = root
    require(not root.is_symlink(), 'artifact_symlink')
    for part in path.parts:
        current = current / part
        require(not current.is_symlink(), 'artifact_symlink')
    with current.open('rb') as handle:
        raw = handle.read(limit + 1)
    require(len(raw) <= limit, 'artifact_size')
    return raw


def object_bytes(raw, limit=2 * 1024 * 1024):
    value = cycle.json_object(raw, limit)
    return value


def png_rgba(raw):
    """Bounded RGB/RGBA8 inflate/unfilter, without Pillow or classification."""
    cycle.verify_png(raw)
    channels = {2: 3, 6: 4}[raw[25]]
    compressed = bytearray()
    offset = 8
    while offset < len(raw):
        count = struct.unpack_from('>I', raw, offset)[0]
        if raw[offset + 4:offset + 8] == b'IDAT':
            compressed.extend(raw[offset + 8:offset + 8 + count])
        offset += count + 12
    stride = 896 * channels
    expected = 414 * (stride + 1)
    inflater = zlib.decompressobj()
    filtered = inflater.decompress(compressed, expected + 1)
    require(len(filtered) == expected and inflater.eof and not inflater.unused_data
            and not inflater.unconsumed_tail, 'artifact_png_inflate')
    previous = bytes(stride)
    pixels = bytearray()
    for y in range(414):
        begin = y * (stride + 1)
        method = filtered[begin]
        require(method <= 4, 'artifact_png_filter')
        row = bytearray(filtered[begin + 1:begin + 1 + stride])
        for x in range(stride):
            left = row[x - channels] if x >= channels else 0
            up = previous[x]
            corner = previous[x - channels] if x >= channels else 0
            if method == 1:
                estimate = left
            elif method == 2:
                estimate = up
            elif method == 3:
                estimate = (left + up) // 2
            elif method == 4:
                p = left + up - corner
                a, b, c = abs(p - left), abs(p - up), abs(p - corner)
                estimate = left if a <= b and a <= c else up if b <= c else corner
            else:
                estimate = 0
            row[x] = (row[x] + estimate) & 255
        if channels == 4:
            require(row[3::4] == b'\xff' * 896, 'artifact_png_alpha')
            pixels.extend(row)
        else:
            for x in range(0, stride, 3):
                pixels.extend(row[x:x + 3]); pixels.append(255)
        previous = row
    require(len(pixels) == RASTER_BYTES, 'artifact_rgba_size')
    return bytes(pixels)


def inventory(folder):
    raw = read(folder, 'receipt.json')
    receipt = object_bytes(raw)
    require(receipt.get('schema') == 'test112-synthetic-runtime-export-v1'
            and receipt.get('case') == 'normal_chain'
            and receipt.get('client_archive_receipt_is_simulated') is True
            and receipt.get('client_archive_sha256') == 'a' * 64
            and receipt.get('published_record_present') is True, 'artifact_receipt_scope')
    rows = receipt.get('files')
    require(type(rows) is list and 0 < len(rows) <= 256, 'artifact_inventory')
    names = set()
    total = 0
    for row in rows:
        cycle.closed(row, ('name', 'bytes', 'sha256'), 'artifact_inventory')
        require(type(row['name']) is str and row['name'] not in names
                and type(row['bytes']) is int and row['bytes'] > 0
                and cycle.digest(row['sha256']), 'artifact_inventory')
        data = read(folder, row['name'], 8 * 1024 * 1024 if row['name'] == 'records-rpc.json' else 2 * 1024 * 1024)
        require((len(data), digest(data)) == (row['bytes'], row['sha256']), 'artifact_inventory_hash')
        names.add(row['name']); total += len(data)
    require(total <= 64 * 1024 * 1024, 'artifact_inventory_total')
    actual = set()
    for path in folder.rglob('*'):
        require(not path.is_symlink(), 'artifact_symlink')
        if path.is_file() and path.name != 'receipt.json':
            actual.add(path.relative_to(folder).as_posix())
    require(actual == names and 'root-status-rpc.json' in names, 'artifact_inventory_set')
    return receipt, digest(raw), total


def child(folder, base, descriptor, native):
    receipt, receipt_sha, size = inventory(folder)
    run = descriptor['run_id']
    require(receipt['run_id'] == run and folder.name == run, 'artifact_child_identity')
    payload = object_bytes(read(folder, 'manifest-rpc.json'))
    manifest, raw, sha = cycle.read_manifest(dict(schema=SPEC.schema, run_id=run, profile=SPEC.profile,
        mode='manifest', payload=payload), run, protocol_spec=SPEC)
    require(raw == read(folder, 'manifest.json') and sha == receipt['manifest_sha256']
            and manifest['export_id'] == receipt['export_id'], 'artifact_manifest_binding')
    require(manifest['complete'] and not manifest['interrupted'] and not manifest['diagnostics'],
            'artifact_normal_manifest')
    status = cycle.status(dict(schema=SPEC.schema, run_id=run, profile=SPEC.profile,
        mode='status', payload=object_bytes(read(folder, 'runtime-status.json'))), run, protocol_spec=SPEC)
    require(status['state'] == descriptor['state'] and status['terminal'] and status['workers_drained']
            and all(status[k] == manifest[k] for k in ('input_state', 'native_inflight', 'ui_frozen')),
            'artifact_runtime_manifest_status')
    pages = object_bytes(read(folder, 'records-rpc.json', 8 * 1024 * 1024), 8 * 1024 * 1024)
    require(set(pages) == {str(r['sequence']) for r in manifest['records']}, 'artifact_record_set')
    dest = base / ('cycle-' + run)
    (dest / 'records').mkdir(parents=True)
    (dest / 'images').mkdir()
    (dest / 'native-manifest.json').write_bytes(raw)
    frame_ids = set()
    expected_spool = {'session.json', 'export-' + manifest['export_id'] + '.json'}
    for row in manifest['records']:
        data = base64.b64decode(pages[str(row['sequence'])], validate=True)
        require((len(data), digest(data)) == (row['bytes'], row['sha256']), 'artifact_record_bytes')
        body = object_bytes(data)
        if row['kind'] == 'session':
            source = 'session.json'
        elif row['kind'] == 'frame':
            capture = body['capture_id']
            require(capture not in frame_ids, 'artifact_frame_duplicate')
            frame_ids.add(capture)
            source = 'frame-' + format(capture, '016x') + '.json'
            rgba_name = source[:-4] + 'rgba'
            rgba = read(folder, 'spool/' + rgba_name)
            require(len(rgba) == RASTER_BYTES and digest(rgba) == body['raw_sha256'], 'artifact_raw_hash')
            expected_spool.add(rgba_name)
        else:
            source = cycle.record_name(row)
        require(data == read(folder, 'spool/' + source), 'artifact_rpc_spool_record')
        expected_spool.add(source)
        (dest / 'records' / cycle.record_name(row)).write_bytes(data)
    require(frame_ids == {r['capture_id'] for r in manifest['images']}, 'artifact_all_frame_images')
    for image in manifest['images']:
        stem = 'png-' + format(image['capture_id'], '016x')
        png = read(folder, 'spool/' + stem + '.png')
        require((len(png), digest(png)) == (image['bytes'], image['sha256'])
                and digest(png_rgba(png)) == image['raw_sha256'], 'artifact_png_raw_hash')
        metadata = object_bytes(read(folder, 'spool/' + stem + '.json'))
        require(metadata.get('schema') == 'ngg2-cycle-png-v1' and metadata.get('run_id') == run
                and metadata.get('capture_id') == image['capture_id']
                and metadata.get('png_sha256') == image['sha256']
                and metadata.get('png_bytes') == image['bytes']
                and metadata.get('metadata', {}).get('raw_sha256') == image['raw_sha256'], 'artifact_png_metadata')
        expected_spool.update((stem + '.png', stem + '.json'))
        (dest / 'images' / image['name']).write_bytes(png)
    require(read(folder, 'spool/export-' + manifest['export_id'] + '.json') == raw, 'artifact_spool_manifest')
    published = object_bytes(read(folder, 'published-rpc.json'))
    require(published.get('accepted') is True and published.get('export_id') == receipt['export_id']
            and published.get('manifest_sha256') == sha and published.get('archive_sha256') == 'a' * 64
            and published.get('receipt_sha256') == receipt['publication_receipt_sha256'], 'artifact_publication_rpc')
    pub_files = list((folder / 'spool').glob('record-*-published.json'))
    require(len(pub_files) == 1, 'artifact_publication_record')
    pub_name = pub_files[0].name
    pub_raw = read(folder, 'spool/' + pub_name)
    pub = object_bytes(pub_raw)
    require(digest(pub_raw) == receipt['publication_receipt_sha256'] and pub.get('run_id') == run
            and pub.get('kind') == 'published' and pub.get('payload') == dict(export_id=receipt['export_id'],
                manifest_sha256=sha, archive_sha256='a' * 64), 'artifact_publication_binding')
    expected_spool.add(pub_name)
    require({p.name for p in (folder / 'spool').iterdir()} == expected_spool, 'artifact_spool_set')
    record = cycle.fresh_record(run, protocol_spec=SPEC)
    record.update(start_intent=True, resolved=True, state=descriptor['state'],
        manifest_sha256=sha, export_id=manifest['export_id'],
        records=[dict(r, offset=r['bytes'], prefix_sha256=r['sha256']) for r in manifest['records']],
        images=[dict(r, offset=r['bytes'], prefix_sha256=r['sha256']) for r in manifest['images']])
    cycle.verify_evidence(base, record, protocol_spec=SPEC)
    campaign.verify_child(base, record, native, descriptor)
    return dict(run_id=run, index=descriptor['index'], receipt_sha256=receipt_sha,
        manifest_sha256=sha, files=len(receipt['files']), images=len(manifest['images']),
        records=len(manifest['records']), artifact_bytes=size, client_proof_verified=True)


def verify(normal_chain, runtime_proof):
    require(not normal_chain.is_symlink() and normal_chain.is_dir(), 'artifact_root')
    entries = list(normal_chain.rglob('*'))
    require(len(entries) <= 16 * 260 and all(not p.is_symlink() for p in entries), 'artifact_tree')
    proof_raw = read(runtime_proof.parent, runtime_proof.name, 8 * 1024 * 1024)
    proof = object_bytes(proof_raw, 8 * 1024 * 1024)
    normal = proof.get('cases', {}).get('normal_chain', {})
    require(proof.get('compile_errors') == 0 and normal.get('qualified') is True
            and normal.get('returncode') == 0, 'actual_mac_normal_chain_not_green')
    receipts = list(normal_chain.glob('normal_chain_child*/*/receipt.json'))
    folders = {p.parent.name: p.parent for p in receipts}
    require(2 <= len(folders) <= 16 and len(folders) == len(receipts), 'artifact_child_count')
    native_sources = proof.get('production_sources')
    required = ('NG2Controller.c', 'NG2Controller.h', 'NG2Runtime.swift', 'NG2CycleSpool.swift',
                'NG2CycleExport.swift', 'NG2Navigation.c', 'NG2CycleWire.swift')
    require(type(native_sources) is dict and all(cycle.digest(native_sources.get(name))
        and digest((REPO / 'patches' / 'loopctrl' / 'ngg2' / name).read_bytes()) == native_sources[name]
        for name in required), 'artifact_current_native_source_binding')
    roots = [read(folder, 'root-status-rpc.json') for folder in folders.values()]
    require(all(raw == roots[0] for raw in roots), 'artifact_root_reply_changed')
    reply = object_bytes(roots[0])
    native = campaign.status_reply(reply, reply.get('run_id'))
    require(native['state'] == 'stopped' and native['terminal'] and native['workers_drained']
            and not native['native_inflight'] and set(folders) == {r['run_id'] for r in native['children']},
            'artifact_root_children')
    with tempfile.TemporaryDirectory(prefix='crossbind116-') as temporary:
        rows = [child(folders[d['run_id']], Path(temporary), d, native) for d in native['children']]
    native_exports = proof.get('synthetic_exports', {})
    require(type(native_exports) is dict, 'artifact_mac_receipt_inventory')
    for row in rows:
        receipt = folders[row['run_id']] / 'receipt.json'
        name = receipt.relative_to(runtime_proof.parent).as_posix()
        require(native_exports.get(name) == row['receipt_sha256'], 'artifact_mac_receipt_binding')
    sources = {str(p.relative_to(REPO)): digest(p.read_bytes()) for p in
        (Path(cycle.__file__), Path(campaign.__file__))}
    return dict(schema='test116-actual-native-client-crossbind-v1',
        scope='Actual Mac procedural Runtime/Spool/RPC bytes -> actual Python client proof; no phone acceptance',
        root_id=native['root_id'], root_status_sha256=digest(roots[0]),
        runtime_proof_sha256=digest(proof_raw), native_sources=native_sources,
        client_sources=sources, python_version=list(sys.version_info[:3]),
        children=rows, all_children_verified=True, input_or_rpc_sent=False,
        archive_claim='Native fixture uses simulated a*64 claim; no actual client ZIP publication is certified')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('normal_chain', type=Path)
    parser.add_argument('--runtime-proof', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        args.output.resolve().relative_to(args.normal_chain.resolve())
    except ValueError:
        pass
    else:
        raise ValueError('output_cannot_modify_input_artifact')
    require(args.output.resolve() != args.runtime_proof.resolve(), 'output_cannot_modify_runtime_proof')
    result = verify(args.normal_chain, args.runtime_proof)
    require(not args.output.is_symlink(), 'output_symlink')
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print('PASS TEST116 actual native/client crossbind: ' + str(len(result['children'])) + ' children')


if __name__ == '__main__':
    main()
