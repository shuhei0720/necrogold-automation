"""Compile the actual normal profile C and actual Swift binding on macOS.

No device, network, signing, private configuration or game-input action exists.
The binding is extracted from the sealed production Runtime, never duplicated.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('shared_host_overlay',HERE/'apply_overlay.py')
overlay=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(overlay)
BEGIN='// NG2 DEVICE GEOMETRY BINDING BEGIN\n'
END='// NG2 DEVICE GEOMETRY BINDING END\n'


def run(command,env=None):
    value=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=120,env=env)
    if value.returncode:
        raise RuntimeError(json.dumps({'command':str(command[0]),'exit':value.returncode,
            'stdout':value.stdout[-32768:],'stderr':value.stderr[-32768:]},sort_keys=True))
    return value.stdout.strip()


EXPECTED_GAP_RED = 'FAIL identical_geometry_renders_when_input_gap_mask_0\n'
OBSERVED_SCALER_VM_LINE = 'IOServiceMatchingfailed for: AppleM2ScalerParavirtDriver\n'


def gap_red_proof(value):
    if value.returncode != 1 or value.stdout or value.stderr not in (EXPECTED_GAP_RED, OBSERVED_SCALER_VM_LINE + EXPECTED_GAP_RED):
        raise RuntimeError(json.dumps({'code':'raster_gap_assertion_red_not_observed',
            'exit':value.returncode, 'stdout':value.stdout[-4096:],
            'stderr':value.stderr[-4096:]},sort_keys=True))
    return {'exit':value.returncode,'stdout':value.stdout,'stderr':value.stderr,
        'observed_scaler_vm_line':value.stderr.startswith(OBSERVED_SCALER_VM_LINE)}


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
    raster_red_proof=None
    support_proofs={}
    if 'LoopCtrlUITests/NG2DeviceRaster.swift' in expected:
        run([*common,'-c',upstream/'LoopCtrlUITests/NG2DeviceRaster.c','-o',output/'raster.o'])
        run([*common,'-c',upstream/'LoopCtrlUITests/NG2Perception.c','-o',output/'perception.o'])
        run([*common,'-c',upstream/'LoopCtrlUITests/NG2Navigation.c','-o',output/'navigation.o'])
        run([*common,'-c',upstream/'LoopCtrlUITests/NG2WorldSupport.c','-o',output/'world.o'])
        run([*common,HERE/'tests/NG2DeviceRasterTests.c',obj,output/'raster.o',output/'perception.o',
            output/'navigation.o',output/'world.o','-lm','-o',output/'raster'])
        raster_proof=run([output/'raster'])
        support_proofs={}
        for name in ('lab_dispatch_fixture.c','bound_world_support_fixture.c',
                     'motion_profile_fixture.c','motion_world_support_fixture.c','ui_world_support_fixture.c'):
            executable=output/Path(name).stem
            run([*common,HERE/'tests/v2'/name,obj,output/'raster.o',output/'perception.o',
                output/'navigation.o',output/'world.o','-lm','-o',executable])
            support_proofs[name]=run([executable])
        reduction=output/'world-reduction';reduction.mkdir()
        for name in ('perception_support_fixture.py','perception_support_fixture.c'):
            shutil.copyfile(HERE/'tests/v2'/name,reduction/name)
        environment=dict(os.environ)
        environment['NG2_CANDIDATE_SOURCE_DIR']=str(upstream/'LoopCtrlUITests')
        environment['NG2_LEGACY_SOURCE_DIR']=str(HERE.parent/'ngg2')
        support_proofs['perception_legacy_reduction']=run([sys.executable,reduction/'perception_support_fixture.py'],env=environment)
        fixture_directory=output/'raster-fixture';fixture_directory.mkdir()
        main=fixture_directory/'main.swift'
        main.write_bytes((HERE/'tests/NG2DeviceRasterTests.swift').read_bytes())
        header=upstream/'LoopCtrlUITests/NG2DeviceRaster.h'
        actual=upstream/'LoopCtrlUITests/NG2DeviceRaster.swift'
        legacy=upstream/'LoopCtrlUITests/NG2Raster.swift'
        link=[obj,output/'raster.o',output/'perception.o',output/'navigation.o',output/'world.o']
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
        raster_red_proof=gap_red_proof(rejected)
    result={'schema':'ng2-shared-device-host-v1','status':'pass','source_sha256':expected,
        'binding_sha256':hashlib.sha256(binding.encode()).hexdigest(),
        'dispatch':dispatch,'swift':swift,'raster':raster_proof,'raster_swift':raster_swift_proof,'raster_gap_red':raster_red_proof,'world_support':support_proofs,'physical_device_acceptance':False,
        'new_profile_input_authorized':False}
    (output/'host-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':'pass','actual_c_dispatch':dispatch,'actual_swift_binding':swift,'actual_raster':raster_proof,'actual_swift_raster':raster_swift_proof,'raster_gap_red':raster_red_proof,
        'physical_device_acceptance':False},sort_keys=True))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();check(args.upstream,args.output)


if __name__=='__main__':main()
