"""Standard-library-only C build/behavior/legacy-byte reduction proof."""
from pathlib import Path
import hashlib
import os
import json
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
CORE=Path(os.environ['NG2_CANDIDATE_SOURCE_DIR'])
BASE=Path(os.environ.get('NG2_LEGACY_SOURCE_DIR', '/workspace/necrogold-automation/patches/loopctrl/ngg2'))
source=(CORE/'NG2Perception.c').read_text()
world_prefix='''        /* NG2 WORLD PLANE BEGIN: UI state above always uses the input canvas. */
        const uint8_t *world_rgba=ng2_world_support_rgba(rgba,length,stride);
        if(!world_rgba)result=-1;
        else {
        if(world_rgba!=rgba)for(y=0;y<H;++y)for(x=0;x<W;++x)gray[y*W+x]=ng2_gray(world_rgba+y*stride+4*x);
'''
world_suffix='        } /* NG2 WORLD PLANE END. */\n'
assert source.count(world_prefix)==1 and source.count(world_suffix)==1
mask_only=source.replace(world_prefix,'').replace(world_suffix,'')
for function in ('ng2_gold','ng2_tiles','ng2_material_proofs','ng2_black_entry_floor',
                 'ng2_separated_floor_bands','ng2_merchandise','ng2_thin_gate_doors','ng2_lower_fringe'):
    assert mask_only.count(function+'(world_rgba,')==1,function
    mask_only=mask_only.replace(function+'(world_rgba,',function+'(rgba,')
reduced=mask_only.replace('#include "NG2WorldSupport.h"\n','')
for addition in (
    '    if(ng2_world_support_active())return !ng2_world_roi_observed(x0,y0,x1,y1);\n',
    '    int world_support=ng2_world_support_active();\n',
    '        if(world_support)excluded=!ng2_world_pixel_observed(x,y);\n',
    '    if(world_support&&out->gold_state==NG2_GOLD_CLEAR\n        &&ng2_world_support_clear_scope()!=NG2_WORLD_CLEAR_OBSERVED_FOV_MINUS_HUD)\n        out->gold_state=NG2_GOLD_UNKNOWN;\n',
):
    assert reduced.count(addition)==1,addition
    reduced=reduced.replace(addition,'')
fringe='            count+=(unsigned)((!ng2_world_support_active()||ng2_world_pixel_observed(x,y))\n                &&ng2_gold_pixel(rgba+y*stride+4*x));'
assert reduced.count(fringe)==1
reduced=reduced.replace(fringe,'            count+=(unsigned)ng2_gold_pixel(rgba+y*stride+4*x);')
assert reduced==(BASE/'NG2Perception.c').read_text()
flags=['cc','-std=c99','-O2','-fno-fast-math','-ffp-contract=off','-Wall','-Wextra','-Werror','-pedantic','-I',str(CORE)]
report={'scope':'Synthetic host-only world support regression','input_authorized':False,'qualification_gaps_unchanged':31,'legacy_source_reduction_exact':True,
        'review_notes':[
            'The enabled bitmap replaces legacy geometric exclusions only; colour predicates, blur kernels, thresholds and canonical cell geometry are unchanged.',
            'UI templates inspect the composite independently. Composite coverage excludes UI-copy destinations; exact pre-UI world coverage preserves observed world there. The context must use coverage for its own world plane, not the UI composite. Any extra unknown world holes require clear_scope0.',
            'Unknown pixels contribute no positive density. A low peak becomes CLEAR only with explicit complete local-FOV-minus-HUD scope1; it never means world-wide no shop.',
            'Generic optional RGBA context uses the exact same-capture pre-UI plane for existing world algorithms and gray/signature/fingerprint/material data. State templates and beat retain the UI composite. Source/frame binding belongs to the caller.',
            'TLS pointer storage is borrowed and immutable until leave; exact prior scopes restore nested calls. NULL+0 is explicit legacy, malformed enabled inputs reject all.',
            'FLOOR state and the legacy forced-origin tile are not coverage authority; the existing outer raster restriction remains necessary.',
            'No input/owner/prefix/ticket/ACK or Scene ABI change; gap31 and all device acceptance gaps remain open.'
        ]}
with tempfile.TemporaryDirectory(prefix='ng2-world-support-') as directory:
    mask_path=Path(directory)/'mask_only_perception.c';mask_path.write_text(mask_only)
    for name,perception in (('baseline',BASE/'NG2Perception.c'),('mask_only',mask_path),('candidate',CORE/'NG2Perception.c')):
        binary=Path(directory)/name
        subprocess.run([*flags,str(perception),str(CORE/'NG2WorldSupport.c'),str(HERE/'perception_support_fixture.c'),'-lm','-o',str(binary)],check=True)
        result=subprocess.run([str(binary),*(['--rgba-only'] if name=='mask_only' else [])],capture_output=True,text=True)
        report[name]={'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
        if name=='baseline':
            assert result.returncode==1 and 'partial marker oldGold1/peak0 scopedGold1/peak0' in result.stdout,report[name]
            assert 'FAIL line' in result.stderr,report[name]
        elif name=='mask_only':
            assert result.returncode==1 and 'UI-only fakeGold worldGold2/' in result.stdout,report[name]
            assert 'FAIL line' in result.stderr,report[name]
        else:assert result.returncode==0 and 'PASS world support:' in result.stdout,report[name]
for name in ('NG2Perception.c','NG2WorldSupport.c','NG2WorldSupport.h'):
    report[name+'_sha256']=hashlib.sha256((CORE/name).read_bytes()).hexdigest()
(HERE/'perception_support_fixture.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS compiled baseline/mask-only Red -> candidate Green; source reduction exact; standard library only')
