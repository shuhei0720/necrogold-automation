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


def main():
    upstream, driver, ipa = map(Path, sys.argv[1:])
    report = inspect_ipa(ipa)
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
