"""unsigned IPAの構成と来歴を確認する。端末上の起動成功は判定しない。"""
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess
import sys
import zipfile


def inspect_ipa(path):
    base = 'Payload/LoopCtrlAllInOne.app/'
    plugin = base + 'PlugIns/LoopCtrlUITests.xctest/'
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('duplicate_zip_entry')
        if any(name.endswith('.mobileprovision') for name in names):
            raise ValueError('provisioning_profile_present')

        def required(name):
            if name not in names or archive.getinfo(name).file_size == 0:
                raise ValueError('missing_or_empty: '+name)
            return archive.read(name)

        app_info = plistlib.loads(required(base+'Info.plist'))
        test_info = plistlib.loads(required(plugin+'Info.plist'))
        for directory, info in ((base, app_info), (plugin, test_info)):
            binary = info.get('CFBundleExecutable')
            if not isinstance(binary, str) or not binary or '/' in binary:
                raise ValueError('invalid_executable_name')
            required(directory+binary)
        required(plugin+'loopctrl')
        if app_info.get('CFBundleIdentifier') != 'top.ebato.loopctrl' or test_info.get('CFBundleIdentifier') != app_info['CFBundleIdentifier']:
            raise ValueError('bundle_id_mismatch')
    return {'bundle_id': app_info['CFBundleIdentifier'],
            'version': app_info.get('CFBundleShortVersionString'),
            'build': app_info.get('CFBundleVersion'),
            'nested_runner_and_cli': True, 'provisioning_profiles': False,
            'ipa_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def command(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True, timeout=30).strip()


def inspect_native_sources(upstream, driver):
    """The packaged native build must use every sealed production source."""
    manifest_path = driver / 'patches/loopctrl/ngg2-manifest.json'
    if not manifest_path.is_file():
        raise ValueError('native_manifest_missing')
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    if (manifest.get('upstream_commit') != '6e25cf6a9f65bc86c372cdce94bdb151d0cf6767'
            or manifest.get('api_version') != '1.98.14-ngg2'
            or manifest.get('capability') != 'necrogold_native_v1'
            or manifest.get('client_capability', 'necrogold_native_v1')
               not in ('necrogold_native_v1', 'necrogold_native_v2', 'necrogold_native_v3', 'necrogold_native_v4')):
        raise ValueError('native_manifest_identity')
    patch = driver / 'patches/loopctrl/ngg2.patch'
    if hashlib.sha256(patch.read_bytes()).hexdigest() != manifest['patch_sha256']:
        raise ValueError('native_patch_hash')
    expected = {name: value['patched_sha256'] for name, value in manifest['files'].items()}
    expected.update({name: value['sha256'] for name, value in manifest['additions'].items()})
    for name, digest in expected.items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('native_unsafe_path')
        source = upstream / path
        if source.is_symlink() or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise ValueError('native_source_hash: ' + name)
    return {'api_version': manifest['api_version'], 'capability': manifest['capability'],
        'client_capability': manifest.get('client_capability', 'necrogold_native_v1'),
        'native_manifest_sha256': hashlib.sha256(manifest_raw).hexdigest(),
        'native_source_sha256': expected}


def main():
    upstream, driver, ipa = map(Path, sys.argv[1:])
    report = inspect_ipa(ipa)
    report.update(inspect_native_sources(upstream, driver))
    report.update({
        'upstream_commit': command('git', 'rev-parse', 'HEAD', cwd=upstream),
        'driver_commit': command('git', 'rev-parse', 'HEAD', cwd=driver),
        'patch_files_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted((driver/'patches/loopctrl').glob('*.patch'))},
        'toolchain': {'xcode': command('xcodebuild', '-version'),
                      'swift': command('swiftc', '--version'),
                      'rust': command('rustc', '--version'),
                      'xcodegen': command('xcodegen', '--version')},
        'device_acceptance': 'not_run',
    })
    if report['upstream_commit'] != '6e25cf6a9f65bc86c372cdce94bdb151d0cf6767' or not report['patch_files_sha256']:
        raise ValueError('source_provenance_mismatch')
    (ipa.parent/'build-manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    (ipa.parent/'SHA256SUMS.txt').write_text(report['ipa_sha256']+'  '+ipa.name+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
