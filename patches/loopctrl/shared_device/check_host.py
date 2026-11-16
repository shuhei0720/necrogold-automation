"""Compile the actual normal profile C and actual Swift binding on macOS.

No device, network, signing, private configuration or game-input action exists.
The binding is extracted from the sealed production Runtime, never duplicated.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('shared_host_overlay',HERE/'apply_overlay.py')
overlay=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(overlay)
BEGIN='// NG2 DEVICE GEOMETRY BINDING BEGIN\n'
END='// NG2 DEVICE GEOMETRY BINDING END\n'


def run(command):
    value=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=120)
    if value.returncode:
        raise RuntimeError(json.dumps({'command':str(command[0]),'exit':value.returncode,
            'stdout':value.stdout[-32768:],'stderr':value.stderr[-32768:]},sort_keys=True))
    return value.stdout.strip()


def check(upstream,output):
    upstream=overlay._root(upstream)
    expected=overlay.verify_final(upstream)
    output=Path(output).absolute();output.mkdir(parents=True,exist_ok=False)
    runtime=overlay._read_path(upstream/'LoopCtrlUITests/NG2Runtime.swift').decode()
    if runtime.count(BEGIN)!=1 or runtime.count(END)!=1:
        raise ValueError('normal_binding_boundary')
    binding=runtime.split(BEGIN,1)[1].split(END,1)[0]
    wrapper='import Foundation\nimport CoreGraphics\nenum NG2RuntimeTestHooks { static var deviceGeometry: (() -> NG2DeviceGeometryBinding)? }\n'+BEGIN+binding+END
    (output/'binding.swift').write_text(wrapper)
    header=upstream/'LoopCtrlUITests/NG2DeviceGeometryProfile.h'
    source=upstream/'LoopCtrlUITests/NG2DeviceGeometryProfile.c'
    obj=output/'profile.o'
    common=['clang','-std=c99','-O2','-fno-fast-math','-ffp-contract=off','-Wall','-Wextra','-Werror','-I',upstream/'LoopCtrlUITests']
    run([*common,'-c',source,'-o',obj])
    run([*common,HERE/'tests/NG2DeviceDispatchTests.c',obj,'-lm','-o',output/'dispatch'])
    dispatch=run([output/'dispatch'])
    run(['swiftc','-Onone','-D','NG2_RUNTIME_HOST_TEST','-import-objc-header',header,
        output/'binding.swift',HERE/'tests/NG2DeviceBindingTests.swift',obj,'-o',output/'binding'])
    swift=run([output/'binding'])
    raster_proof=None
    raster_swift_proof=None
    if 'LoopCtrlUITests/NG2DeviceRaster.swift' in expected:
        run([*common,'-c',upstream/'LoopCtrlUITests/NG2DeviceRaster.c','-o',output/'raster.o'])
        run([*common,'-c',upstream/'LoopCtrlUITests/NG2Perception.c','-o',output/'perception.o'])
        run([*common,'-c',upstream/'LoopCtrlUITests/NG2Navigation.c','-o',output/'navigation.o'])
        run([*common,HERE/'tests/NG2DeviceRasterTests.c',obj,output/'raster.o',output/'perception.o',
            output/'navigation.o','-lm','-o',output/'raster'])
        raster_proof=run([output/'raster'])
        fixture_directory=output/'raster-fixture';fixture_directory.mkdir()
        main=fixture_directory/'main.swift'
        main.write_bytes((HERE/'tests/NG2DeviceRasterTests.swift').read_bytes())
        header=upstream/'LoopCtrlUITests/NG2DeviceRaster.h'
        actual=upstream/'LoopCtrlUITests/NG2DeviceRaster.swift'
        legacy=upstream/'LoopCtrlUITests/NG2Raster.swift'
        link=[obj,output/'raster.o',output/'perception.o',output/'navigation.o']
        compiler=['swiftc','-Onone','-import-objc-header',header]
        run([*compiler,legacy,actual,main,*link,'-o',output/'raster-swift'])
        # Reconstruct only the previously reviewed gap==31 rendering guard.
        # Both variants must compile. The negative must fail the precise
        # gap0 assertion with no toolchain error before the current Green.
        text=actual.read_text();needle='guard contract != nil, p.device == 8, p.legacy_passthrough == 0,'
        if text.count(needle)!=1:raise ValueError('raster_gap_red_variant_boundary')
        red=fixture_directory/'NG2DeviceRaster.swift'
        red.write_text(text.replace(needle,needle+' p.qualification_gaps == 31,'))
        run([*compiler,legacy,red,main,*link,'-o',output/'raster-swift-red'])
        # Run the current implementation first: its bounded failure output
        # must remain visible rather than being hidden by a later Red mismatch.
        raster_swift_proof=run([output/'raster-swift'])
        rejected=subprocess.run([str(output/'raster-swift-red')],capture_output=True,text=True,timeout=120)
        if rejected.returncode!=1 or rejected.stdout or rejected.stderr!='FAIL identical_geometry_renders_when_input_gap_mask_0\n':
            raise RuntimeError(json.dumps({'code':'raster_gap_assertion_red_not_observed',
                'exit':rejected.returncode, 'stdout':rejected.stdout[-4096:],
                'stderr':rejected.stderr[-4096:]},sort_keys=True))
    result={'schema':'ng2-shared-device-host-v1','status':'pass','source_sha256':expected,
        'binding_sha256':hashlib.sha256(binding.encode()).hexdigest(),
        'dispatch':dispatch,'swift':swift,'raster':raster_proof,'raster_swift':raster_swift_proof,'physical_device_acceptance':False,
        'new_profile_input_authorized':False}
    (output/'host-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':'pass','actual_c_dispatch':dispatch,'actual_swift_binding':swift,'actual_raster':raster_proof,'actual_swift_raster':raster_swift_proof,
        'physical_device_acceptance':False},sort_keys=True))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();check(args.upstream,args.output)


if __name__=='__main__':main()
