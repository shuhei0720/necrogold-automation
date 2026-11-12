"""Run TEST087 wait-entry diagnostics and post-run target publication with exact related regressions.

Controller fixtures bind to the sealed patched upstream used by the IPA.
The existing evaluator NativeCore compiles repository C after all eight source
and header hashes are bound to that same seal. Historical synthetic worlds
and Runtime mutation suites remain explicit lanes.
"""
import argparse
import ctypes
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import unittest


NATIVE_CASES = (('tests.test_native_wait_entry087', 'NativeWaitEntry087Tests', 'test087-wait-entry', frozenset({'test_entry_payload_records_true_row_major_deltas_and_roundtrips_existing_schema', 'test_nonzero_floor_reveal_wait_entry_keeps_original_ticket_credit_and_horizons', 'test_ineligible_or_mask_zero_observations_do_not_create_wait_entry_diagnostics'}), True), ('tests.test_native_wait_diagnostics082', 'NativeWaitDiagnostics082Tests', 'test087-related-diagnostics082', frozenset({'test_mask_zero_metadata_issued_clock_and_goods_do_not_create_false_trace', 'test_rejected_independent_route_retains_true_source_diff_without_authority_change', 'test_ready_unknown_motion_records_only_real_nonzero_scene_diff'}), False), ('tests.test_native_stationary_wait076', 'NativeStationaryWait076Tests', 'test087-related-wait076', frozenset({'test_parent_horizon_caps_new_ticket_schedule_and_visual_authority', 'test_unknown_shop_and_mask_zero_passage_retire_without_motion_credit'}), False), ('tests.test_native_controller', 'NativeControllerTests', 'test087-related-controller', frozenset({'test_scene_detail_query_is_bounded_and_leaves_existing_abi_unchanged'}), False))

CLIENT_CASES = (('tests.test_native_results', 'NativeResultsTests', 'test087-related-results', frozenset({'test_bad_scene_change_required_values_are_rejected'}), False), ('tests.test_target_assessment087', 'TargetAssessment087Tests', 'test087-target-assessment', frozenset({'test_icon_only_wrong_slot_name_only_dark_and_hud_preserve_uncertainty', 'test_png_crc_geometry_alpha_inflate_filters_trailing_and_cancellation_fail_closed', 'test_sidecar_unknown_fields_foreign_identity_source_changes_and_symlinks_are_rejected', 'test_prepare_is_deterministic_atomic_and_keeps_closed_original_reports_unchanged', 'test_all_png_filters_reconstruct_exact_original_opaque_rgba', 'test_same_slot_icon_and_name_on_complete_observed_shop_is_target'}), True), ('tests.test_target_publication087', 'TargetPublication087Tests', 'test087-target-publication', frozenset({'test_interrupted_publication_reuses_frozen_sidecar_archive_and_receipt_without_prepare', 'test_valid_closed_sidecar_is_accepted_and_original_zip_layout_stays_valid', 'test_incomplete_or_changed_native_evidence_never_calls_prepare', 'test_foreign_changed_malformed_sidecar_and_every_unrelated_extra_are_rejected', 'test_new_entry_connects_prepare_and_displays_only_target_candidate_or_unknown', 'test_prepare_follows_certificate_and_its_sidecar_is_in_the_same_verified_zip'}), True), ('tests.test_native_publication069', 'Publication069Tests', 'test087-related-publication069', frozenset({'test_missing_drain_safety_fields_cannot_certify_publication', 'test_resolved_without_receipt_publishes_only_and_archive_contains_exact_snapshot', 'test_failure_before_receipt_retries_publication_without_a_native_call', 'test_missing_png_or_incomplete_cursor_cannot_be_published_or_start_fresh'}), False), ('tests.test_device_recording', 'DeviceRecordingTests', 'test087-related-evaluator', frozenset({'test_zip_paths_duplicates_symlinks_extra_and_multiple_runs_are_invalid', 'test_strict_json_rejects_duplicates_nonfinite_depth_and_mismatch', 'test_procedural_visible_goods_and_confirmed_pause_pass_bounded_milestone', 'test_png_digest_crc_iend_and_geometry_are_verified'}), False))

PACKAGE_CASES = ()

CORE_MODULES = ('tests.test_native_beat', 'tests.test_native_blocked067', 'tests.test_native_controller', 'tests.test_native_navigation', 'tests.test_native_observation072', 'tests.test_native_passage072', 'tests.test_native_passage_unsent076', 'tests.test_native_perception', 'tests.test_native_recovery', 'tests.test_native_stationary_wait076', 'tests.test_native_wait_diagnostics082', 'tests.test_native_wait_entry087')
NATIVE_BASELINE = '6a937163ac87dde049887eaf56a65f9dda757911'
RETAINED_RUNTIME_SHA256 = '048a462811edabbef4544b2b83ffaadcedbdc654d8675fad4143a6432bc299da'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Controller.c'}
CORE_CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.validation', 'necroprobe.protocol')
CHANGED_CORE_CLIENT_MODULES = ('necroprobe.test069',)
NEW_CLIENT_MODULES = ('necroprobe.test087', 'necroprobe.target_assessment')
RETAINED_COMPAT_ENTRY_MODULES = ('necroprobe.test086',)
CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.test087', 'necroprobe.target_assessment', 'necroprobe.validation', 'necroprobe.protocol', 'necroprobe.test086')
FIXTURE_OVERRIDE_PREFIXES = ('NECRO_TEST063_BASELINE_', 'NECRO_TEST071_BASELINE_', 'NECRO_TEST072_BASELINE_', 'NECRO_TEST074_BASELINE_', 'NECRO_TEST075_BASELINE_', 'NECRO_TEST076_BASELINE_', 'NECRO_TEST077_BASELINE_', 'NECRO_TEST078_BASELINE_', 'NECRO_TEST079_BASELINE_', 'NECRO_TEST080_BASELINE_', 'NECRO_TEST081_BASELINE_', 'NECRO_TEST082_BASELINE_', 'NECRO_TEST083_BASELINE_', 'NECRO_TEST083_FRAMING_BASELINE_', 'NECRO_TEST084_BASELINE_', 'NECRO_TEST084_NONFLOOR_', 'NECRO_TEST085_PROOF_', 'NECRO_TEST085_STATIONARY_', 'NECRO_TEST086_', 'NECRO_TEST082_DIAGNOSTIC_', 'NECRO_TEST087_')

def reject_fixture_overrides():
    present = sorted(name for name in os.environ
                     if name.startswith(FIXTURE_OVERRIDE_PREFIXES) or name == 'BASELINE_NAV')
    if present:
        raise ValueError('sealed fixture baseline overrides are forbidden: '+', '.join(present))


def selected_cases(cases):
    cases = list(cases)
    identifiers = [case.id() for case in cases]
    if not cases or len(identifiers) != len(set(identifiers)):
        raise ValueError('missing or duplicate device cases')
    return cases


def method_cases(case_type, methods, *, exact=False):
    available = set(unittest.defaultTestLoader.getTestCaseNames(case_type))
    if not methods or not methods <= available or (exact and available != set(methods)):
        raise ValueError('device method inventory changed: ' + case_type.__name__)
    return selected_cases(case_type(method) for method in sorted(methods))


def native_suites(upstream):
    reject_fixture_overrides()
    names = tuple(dict.fromkeys((*CORE_MODULES, *(case[0] for case in NATIVE_CASES))))
    modules = {name: importlib.import_module(name) for name in names}
    for module in modules.values():
        module.CORE = upstream / 'LoopCtrlUITests'
    # Support fixture imports under their historical bare names without
    # selecting either module's unrelated tests.
    for name in names:
        alias = sys.modules.get(name.rsplit('.', 1)[-1])
        if alias is not None:
            alias.CORE = upstream / 'LoopCtrlUITests'
    reject_fixture_overrides()
    return [(label, method_cases(getattr(modules[name], class_name), methods, exact=exact))
            for name, class_name, label, methods, exact in NATIVE_CASES]


def client_source_identity(driver):
    native = importlib.import_module('necroprobe.native_walk')
    validation = importlib.import_module('necroprobe.validation')
    protocol = importlib.import_module('necroprobe.protocol')
    target = importlib.import_module('necroprobe.target_assessment')
    entry = importlib.import_module('necroprobe.test087')
    legacy = importlib.import_module('necroprobe.test086')
    publication = importlib.import_module('necroprobe.test069')
    audit = importlib.import_module('tools.evaluate_device_recording')
    code = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=driver, text=True).strip()
    sources = {}
    for name in CLIENT_SOURCE_MODULES:
        module = importlib.import_module(name)
        relative = name.replace('.', '/')+'.py'
        path = driver / relative
        if Path(module.__file__).resolve() != path:
            raise ValueError('client module was imported outside the actual driver: '+name)
        raw = path.read_bytes()
        if raw != subprocess.check_output(['git','show',code+':'+relative],cwd=driver):
            raise ValueError('client module differs from the pinned driver commit: '+name)
        if name in CORE_CLIENT_SOURCE_MODULES+RETAINED_COMPAT_ENTRY_MODULES and raw != subprocess.check_output(['git','show',NATIVE_BASELINE+':'+relative],cwd=driver):
            raise ValueError('retained TEST087 client source differs from the baseline: '+name)
        if name in CHANGED_CORE_CLIENT_MODULES and raw == subprocess.check_output(['git','show',NATIVE_BASELINE+':'+relative],cwd=driver):
            raise ValueError('TEST087 publication wrapper must differ from the baseline')
        sources[name]={'path':relative,'sha256':hashlib.sha256(raw).hexdigest()}
    artifacts={}
    for relative in ('necroprobe/target_ring_features.json','tools/evaluate_device_recording.py'):
        raw=(driver/relative).read_bytes()
        if raw != subprocess.check_output(['git','show',code+':'+relative],cwd=driver):
            raise ValueError('local target artifact differs from pinned source: '+relative)
        artifacts[relative]={'path':relative,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    feature=artifacts['necroprobe/target_ring_features.json']
    evaluator=artifacts['tools/evaluate_device_recording.py']
    if feature['bytes']>64*1024 or feature['sha256']!=target.FEATURE_SHA256:
        raise ValueError('target feature asset does not match its actual classifier')
    if (driver/evaluator['path']).read_bytes()==subprocess.check_output(['git','show',NATIVE_BASELINE+':'+evaluator['path']],cwd=driver):
        raise ValueError('TEST087 sidecar evaluator must differ from its baseline')
    evaluator['baseline_changed']=True
    if Path(audit.__file__).resolve()!=driver/evaluator['path'] or audit.ROOT!=driver:
        raise ValueError('actual evaluator is imported outside the pinned driver')
    if (native.REVISION!='native-walk-v16' or native.API_VERSION!='1.98.16-ngg2'
            or native.CAPABILITY!='necrogold_native_v15' or native.PROFILE!='normal-1-1-evidence-v2'
            or native.LEGACY_PROFILE!='normal-1-1-v1' or native.MAX_TOTAL_IMAGES!=4*1024*1024
            or native.MAX_EVIDENCE_IMAGES!=20*512*1024):
        raise ValueError('collection client revision/API/capability changed')
    if (protocol.json_object is not validation.json_object
            or protocol.Client._call.__globals__.get('json_object') is not validation.json_object
            or native.json_object is not validation.json_object or native.Client is not protocol.Client
            or audit.native_walk is not native or audit.json_object is not validation.json_object):
        raise ValueError('actual RPC/evaluator client is not bound to the pinned JSON validator')
    if (entry.device_main is not publication.main or entry.prepare_assessment is not target.prepare_assessment
            or legacy.device_main is not publication.main):
        raise ValueError('target/legacy entry binding differs from the actual publication modules')
    if any(function.__kwdefaults__.get('prepare','missing') is not None for function in (publication.main,publication.run,publication._publish)):
        raise ValueError('legacy publication optional prepare default must remain None')
    target_raw=(driver/'necroprobe/target_assessment.py').read_bytes()
    local_assets={'target_module':{'path':'necroprobe/target_assessment.py','sha256':hashlib.sha256(target_raw).hexdigest(),'bytes':len(target_raw)},
        'feature_asset':feature,'evaluator':evaluator,
        'contract':{'FEATURE_SHA256':target.FEATURE_SHA256,'CLASSIFIER':target.CLASSIFIER,'SCHEMA':target.SCHEMA,'SIDECAR':target.SIDECAR}}
    return {'modules':sources,'driver_commit':code,'revision':native.REVISION,'api_version':native.API_VERSION,
        'capability':native.CAPABILITY,'profile':native.PROFILE,
        'baseline_unchanged_core_modules':list(CORE_CLIENT_SOURCE_MODULES),
        'baseline_changed_core_modules':list(CHANGED_CORE_CLIENT_MODULES),'added_modules':list(NEW_CLIENT_MODULES),
        'retained_compat_entry_modules':list(RETAINED_COMPAT_ENTRY_MODULES),'local_target_assets':local_assets,
        'legacy_profile':native.LEGACY_PROFILE,'profile_total_bytes':native.MAX_EVIDENCE_IMAGES,
        'legacy_total_bytes':native.MAX_TOTAL_IMAGES,
        'json_binding':{'protocol_json_object_is_validation_json_object':True,'client_call_global_is_validation_json_object':True,
            'native_json_object_is_validation_json_object':True,'native_client_is_protocol_client':True}}


def repository_native_identity(driver, sealed):
    names=('NG2Controller.c','NG2Navigation.c','NG2Perception.c','NG2Beat.c',
           'NG2Controller.h','NG2Core.h','NG2Templates.h','NG2CaptureBridge.h')
    hashes={name:hashlib.sha256((driver/'patches/loopctrl/ngg2'/name).read_bytes()).hexdigest() for name in names}
    if any(sealed['native_source_sha256']['LoopCtrlUITests/'+name]!=digest for name,digest in hashes.items()):
        raise ValueError('repository C/H sources differ from the actual sealed IPA sources')
    return {'source_directory':'patches/loopctrl/ngg2','source_sha256':hashes,
        'all_eight_match_sealed_ipa_sources':True,'evaluator_source_policy':'repository production source; no CORE override',
        'evaluator_compiled_c':['NG2Perception.c','NG2Navigation.c']}


def fixture_bindings(modules, native, publication, target, audit, entry, legacy):
    expected={'native':native,'publication':publication,'target':target,'audit':audit,'test087':entry,'test086':legacy}
    for name,module in modules.items():
        for fixture in (module,sys.modules.get(name.rsplit('.',1)[-1])):
            if fixture is None:continue
            for attr,actual in expected.items():
                if getattr(fixture,attr,actual) is not actual:
                    raise ValueError('selected fixture is not bound to actual pinned module: '+name+'.'+attr)
    return {'target_fixture_is_actual_module':True,'publication_fixture_is_actual_wrapper':True,
            'evaluator_fixture_is_actual_module':True,'entry_and_legacy_fixture_bindings':True}


def client_suites():
    modules={name:importlib.import_module(name) for name in dict.fromkeys(row[0] for row in CLIENT_CASES)}
    native=importlib.import_module('necroprobe.native_walk')
    publication=importlib.import_module('necroprobe.test069')
    target=importlib.import_module('necroprobe.target_assessment')
    audit=importlib.import_module('tools.evaluate_device_recording')
    entry=importlib.import_module('necroprobe.test087')
    legacy=importlib.import_module('necroprobe.test086')
    if publication.native is not native or entry.device_main is not publication.main or entry.prepare_assessment is not target.prepare_assessment:
        raise ValueError('actual target/publication production bindings differ')
    fixture_bindings(modules,native,publication,target,audit,entry,legacy)
    return [(label,method_cases(getattr(modules[name],class_name),methods,exact=exact))
            for name,class_name,label,methods,exact in CLIENT_CASES]


def package_suites():
    return [(label, method_cases(getattr(importlib.import_module(name), class_name), methods, exact=exact))
            for name, class_name, label, methods, exact in PACKAGE_CASES]


def run_scope(name, cases, output, record):
    cases = selected_cases(cases)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(cases))
    log = stream.getvalue()
    (output / (name + '.txt')).write_text(log)
    print(log, end='', flush=True)
    record[name] = {'selected': [case.id() for case in cases], 'tests_run': result.testsRun,
                   'failures': len(result.failures), 'errors': len(result.errors),
                   'skipped': len(result.skipped), 'expected_failures': len(result.expectedFailures)}
    (output/'test087-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
    if (result.testsRun != len(cases) or not result.wasSuccessful()
            or result.skipped or result.expectedFailures):
        raise RuntimeError(name + ': selected device tests must execute Green without skips/errors')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('driver', type=Path)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    driver, upstream, output = (value.resolve() for value in (args.driver, args.upstream, args.output))
    output.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(driver), str(driver/'tests'), str(driver/'patches/loopctrl')]
    verifier = importlib.import_module('verify_package')
    before = verifier.inspect_native_sources(upstream, driver)
    if (before['api_version'] != '1.98.16-ngg2' or before['client_capability'] != 'necrogold_native_v15'
            or len(before['native_source_sha256']) != 22):
        raise ValueError('TEST087 sealed source identity is not installed')
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'], cwd=driver, text=True))
    baseline_sources = {name: row['patched_sha256'] for name, row in baseline['files'].items()}
    baseline_sources.update({name: row['sha256'] for name, row in baseline['additions'].items()})
    current_sources = before['native_source_sha256']
    changed = {name for name in current_sources if current_sources[name] != baseline_sources.get(name)}
    if set(current_sources) != set(baseline_sources) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('TEST087 native change scope differs')
    native_change_scope = {'baseline': NATIVE_BASELINE, 'changed_sources': sorted(changed),
                           'unchanged_sources': len(current_sources)-len(changed)}
    if current_sources['LoopCtrlUITests/NG2Runtime.swift'] != RETAINED_RUNTIME_SHA256:
        raise ValueError('TEST087 retained Runtime source changed')
    repository_before = repository_native_identity(driver, before)
    client_before = client_source_identity(driver)
    suites = native_suites(upstream) + client_suites() + package_suites()
    selected_cases(case for _label, cases in suites for case in cases)
    fixture = importlib.import_module('tests.test_native_controller')
    abi = {name: ctypes.sizeof(getattr(fixture, name))
           for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    if abi != {'Scene': 23864, 'Status': 192, 'Event': 128, 'MotionWait': 48, 'RecoveryStatus': 456}:
        raise ValueError('native ABI layout changed')
    record = {'scope': 'TEST087 passage wait-entry trace and post-run local target publication; walking-stop cause remains unresolved',
              'source_identity': before, 'native_change_scope': native_change_scope,
              'client_source_identity': client_before,
              'repository_native_source_identity':repository_before,
              'client_fixture_bindings':{'target_fixture_is_actual_module':True,'publication_fixture_is_actual_wrapper':True,'evaluator_fixture_is_actual_module':True,'entry_and_legacy_fixture_bindings':True},
              'retained_runtime_source_sha256': RETAINED_RUNTIME_SHA256,
              'fixture_source_policy': {'baseline_override_env_prefixes': list(FIXTURE_OVERRIDE_PREFIXES),
                  'baseline_override_env_names': ['BASELINE_NAV'],
                  'baseline_overrides': 'forbidden even when empty',
                  'core_binding': 'all canonical and existing bare fixture CORE paths before selection'},
              'abi_bytes': abi, 'device_test': 'not_run',
              'not_run': ['full historical native/client/package suites and unrelated regressions',
                          'new Runtime Red (Runtime body and preserved fixture bytes are unchanged)',
                          'synthetic shop/world suites and private recorded-image corpus',
                          'unrelated workflow/publisher/RPC suites'],
              'selection_reasons': {'test087-wait-entry': 'three public cases retain only true nonzero passage wait-entry diagnostics while preserving original command/credit/deadline and excluding mask-zero, goods and existing shop duplicates', 'test087-related-diagnostics082': 'two explicitly strengthened old methods verify entry-first/rejection-later order and unchanged mask-zero rejection; the old independent route rejection remains selected', 'test087-related-wait076': 'old unknown-shop/mask-zero no-credit and fixed parent/two-beat wait horizons remain authoritative', 'test087-related-controller': 'the original bounded scene detail query and ABI layout remain unchanged', 'test087-related-results': 'the production client still rejects missing scene-change required values', 'test087-target-assessment': 'six bounded stdlib PNG and same-slot icon/name cases cover target/candidate/unknown, immutable source lineage, strict deterministic sidecars and invalid/cancelled inputs; procedural tests do not establish device accuracy', 'test087-target-publication': 'six publication/evaluator/entry integration cases bind certificate-before-assessment, strict same-run sidecar, immutable ZIP recovery and fixed target/candidate/unknown display without new game input', 'test087-related-publication069': 'four old publication cases retain exact snapshots, complete PNG/cursor gate, no-start recovery and drain safety; the publication gate is selected once', 'test087-related-evaluator': 'four old evaluator cases retain bounded goods/PAUSE milestone, closed ZIP layout, strict JSON and original PNG integrity; its existing NativeCore compiles repository C whose eight source/header bytes equal the sealed IPA sources'}}
    for label, cases in suites:
        run_scope(label, cases, output, record)
    # Workflow and selection changes have their own small unit set, without
    # automatically discovering the historical package/Swift fixture suite.
    for module_name, classes in (('test_device_ci087', ('DeviceHostSelection087Tests',)),):
        module = importlib.import_module(module_name)
        cases = [case for name in classes for case in
                 unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module, name))]
        run_scope('test087-'+module_name, cases, output, record)
    if verifier.inspect_native_sources(upstream, driver) != before:
        raise ValueError('selected tests changed sealed production source')
    reject_fixture_overrides()
    if repository_native_identity(driver, before) != repository_before:
        raise ValueError('selected tests changed repository native source bytes')
    if client_source_identity(driver) != client_before:
        raise ValueError('selected tests changed the pinned production client')
    record['sealed_sources_unchanged_after_tests'] = True
    record['client_source_unchanged_after_tests'] = True
    record['repository_native_sources_unchanged_after_tests'] = True
    record['manifest_sha256'] = hashlib.sha256((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes()).hexdigest()
    (output/'test087-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
    print('PASS TEST087 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
