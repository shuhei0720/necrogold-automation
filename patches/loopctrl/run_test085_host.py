"""Run TEST085 verified scheduling and independent stationary proof with exact related regressions.

All native fixtures compile the sealed patched upstream used by the IPA.
Historical synthetic worlds and Runtime mutation suites remain explicit lanes.
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


NATIVE_CASES = (('tests.test_native_proof_scheduling085', 'NativeProofScheduling085Tests', 'test085-verified-scheduling', frozenset({'test_qualified_reference_move_is_already_verified_for_recovery', 'test_publication_and_source_boundaries_keep_old_admission_limits', 'test_parent_horizon_goods_and_cancellation_remain_authoritative', 'test_existing_sync_episode_and_future_preparation_bound_new_slot', 'test_only_same_ack_known_move_proof_can_enter_recovery', 'test_late_verified_move_reacquires_without_reusing_old_ticket'}), True), ('tests.test_native_stationary_texture085', 'NativeStationaryTexture085Tests', 'test085-independent-stationary', frozenset({'test_phase_alias_noise_and_blur_dependency_counterexamples_stay_unknown', 'test_public_controller_observe_proof_reaches_ready_before_original_w', 'test_original_numeric_support_agreement_bands_and_competition_boundaries', 'test_old_unit_tween_reverse_and_opening_outputs_are_never_overwritten', 'test_public_clear_floor_zero_requires_independent_stationary_evidence', 'test_observed_terrain_goods_gold_door_and_protection_guards'}), True), ('tests.test_native_controller', 'NativeControllerTests', 'test085-related-controller', frozenset({'test_next_unreserved_candidate_expiry_and_stale_authority_never_choose_another_beat', 'test_continuous_candidate_expiry_precedes_late_hud_update', 'test_continuous_first_reservation_requires_source_start_window', 'test_continuous_candidate_expiry_precedes_delayed_commit_tick', 'test_continuous_first_reservation_waits_until_publication_window', 'test_scene_detail_query_is_bounded_and_leaves_existing_abi_unchanged'}), False), ('tests.test_native_recovery', 'NativeRecoveryTests', 'test085-related-recovery', frozenset({'test_post_move_recovery_reserved_before_budget_cannot_begin_after_budget', 'test_goods_after_visual_deadline_are_held_without_move_credit', 'test_late_real_move_enters_reacquisition_without_old_next_beat'}), False), ('tests.test_native_stationary_wait076', 'NativeStationaryWait076Tests', 'test085-related-wait076', frozenset({'test_wait_deadline_is_fixed_and_unknown_frames_do_not_extend_it', 'test_parent_horizon_caps_new_ticket_schedule_and_visual_authority', 'test_ready_or_issued_unknown_does_not_reopen_the_same_wait'}), False), ('tests.test_native_static075', 'NativeStatic075Tests', 'test085-related-static075', frozenset({'test_shift_partial_and_reverse_do_not_manufacture_a_static_proof', 'test_weak_single_band_aliased_or_opposite_edges_remain_unknown'}), False), ('tests.test_native_motion075', 'NativeMotion075Tests', 'test085-related-motion075', frozenset({'test_full_kernel_rejects_hidden_changed_or_ui_dependencies', 'test_world_letters_cannot_move_a_static_or_partial_background'}), False), ('tests.test_native_motion067', 'NativeMotion067Tests', 'test085-related-motion067', frozenset({'test_existing_normal_moves_blocks_openings_and_unexpected_are_preserved'}), False))

CLIENT_CASES = (('tests.test_native_publication069', 'Publication069Tests', 'test085-publication', frozenset({'test_missing_png_or_incomplete_cursor_cannot_be_published_or_start_fresh'}), False),)

PACKAGE_CASES = ()

CORE_MODULES = ('tests.test_native_beat', 'tests.test_native_blocked067', 'tests.test_native_controller', 'tests.test_native_motion067', 'tests.test_native_motion075', 'tests.test_native_navigation', 'tests.test_native_observation072', 'tests.test_native_passage072', 'tests.test_native_passage_unsent076', 'tests.test_native_perception', 'tests.test_native_proof_scheduling085', 'tests.test_native_recovery', 'tests.test_native_static075', 'tests.test_native_stationary_texture085', 'tests.test_native_stationary_wait076')
NATIVE_BASELINE = '0443bc9abc5c814ed620d09afdd487af203eb681'
RETAINED_RUNTIME_SHA256 = '048a462811edabbef4544b2b83ffaadcedbdc654d8675fad4143a6432bc299da'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Navigation.c'}
CORE_CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.validation', 'necroprobe.protocol')
CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.test085', 'necroprobe.validation', 'necroprobe.protocol')
FIXTURE_OVERRIDE_PREFIXES = ('NECRO_TEST063_BASELINE_', 'NECRO_TEST071_BASELINE_', 'NECRO_TEST072_BASELINE_', 'NECRO_TEST074_BASELINE_', 'NECRO_TEST075_BASELINE_', 'NECRO_TEST076_BASELINE_', 'NECRO_TEST077_BASELINE_', 'NECRO_TEST078_BASELINE_', 'NECRO_TEST079_BASELINE_', 'NECRO_TEST080_BASELINE_', 'NECRO_TEST081_BASELINE_', 'NECRO_TEST082_BASELINE_', 'NECRO_TEST083_BASELINE_', 'NECRO_TEST083_FRAMING_BASELINE_', 'NECRO_TEST084_BASELINE_', 'NECRO_TEST084_NONFLOOR_', 'NECRO_TEST085_PROOF_', 'NECRO_TEST085_STATIONARY_')

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
    code = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=driver, text=True).strip()
    sources = {}
    for name in CLIENT_SOURCE_MODULES:
        module = importlib.import_module(name)
        relative = name.replace('.', '/')+'.py'
        path = driver / relative
        if Path(module.__file__).resolve() != path:
            raise ValueError('client module was imported outside the actual driver: '+name)
        committed = subprocess.check_output(['git', 'show', code+':'+relative], cwd=driver)
        raw = path.read_bytes()
        if raw != committed:
            raise ValueError('client module differs from the pinned driver commit: '+name)
        if name != 'necroprobe.test085' and raw != subprocess.check_output(
                ['git', 'show', NATIVE_BASELINE+':'+relative], cwd=driver):
            raise ValueError('unchanged TEST085 client source differs from the baseline: '+name)
        sources[name] = {'path': relative, 'sha256': hashlib.sha256(raw).hexdigest()}
    if (native.REVISION != 'native-walk-v16' or native.API_VERSION != '1.98.16-ngg2'
            or native.CAPABILITY != 'necrogold_native_v15'
            or native.PROFILE != 'normal-1-1-evidence-v2' or native.LEGACY_PROFILE != 'normal-1-1-v1'
            or native.MAX_TOTAL_IMAGES != 4*1024*1024 or native.MAX_EVIDENCE_IMAGES != 20*512*1024):
        raise ValueError('collection client revision/API/capability changed')
    if (protocol.json_object is not validation.json_object
            or protocol.Client._call.__globals__.get('json_object') is not validation.json_object
            or native.json_object is not validation.json_object
            or native.Client is not protocol.Client):
        raise ValueError('actual RPC client is not bound to the pinned JSON validator')
    return {'modules': sources, 'driver_commit': code, 'revision': native.REVISION, 'api_version': native.API_VERSION,
            'capability': native.CAPABILITY, 'profile': native.PROFILE,
            'baseline_unchanged_core_modules': list(CORE_CLIENT_SOURCE_MODULES),
            'legacy_profile': native.LEGACY_PROFILE, 'profile_total_bytes': native.MAX_EVIDENCE_IMAGES,
            'legacy_total_bytes': native.MAX_TOTAL_IMAGES,
            'json_binding': {'protocol_json_object_is_validation_json_object': True,
                            'client_call_global_is_validation_json_object': True,
                            'native_json_object_is_validation_json_object': True,
                            'native_client_is_protocol_client': True}}


def client_suites():
    modules = {name: importlib.import_module(name) for name in dict.fromkeys(row[0] for row in CLIENT_CASES)}
    native = importlib.import_module('necroprobe.native_walk')
    publication = importlib.import_module('necroprobe.test069')
    entry = importlib.import_module('necroprobe.test085')
    if publication.native is not native:
        raise ValueError('production publication wrapper is not bound to the actual driver client')
    if entry.device_main is not publication.main:
        raise ValueError('TEST085 entry is not bound to the actual driver publication wrapper')
    for name, module in modules.items():
        alias = sys.modules.get(name.rsplit('.', 1)[-1])
        for fixture in (module, alias):
            if fixture is not None and getattr(fixture, 'native', native) is not native:
                raise ValueError('collection fixture is not bound to the actual driver client: '+name)
            if fixture is not None and getattr(fixture, 'publication', publication) is not publication:
                raise ValueError('publication fixture is not bound to the actual driver wrapper: '+name)
    return [(label, method_cases(getattr(modules[name], class_name), methods, exact=exact))
            for name, class_name, label, methods, exact in CLIENT_CASES]


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
    (output/'test085-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
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
        raise ValueError('TEST085 sealed source identity is not installed')
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'], cwd=driver, text=True))
    baseline_sources = {name: row['patched_sha256'] for name, row in baseline['files'].items()}
    baseline_sources.update({name: row['sha256'] for name, row in baseline['additions'].items()})
    current_sources = before['native_source_sha256']
    changed = {name for name in current_sources if current_sources[name] != baseline_sources.get(name)}
    if set(current_sources) != set(baseline_sources) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('TEST085 native change scope differs')
    native_change_scope = {'baseline': NATIVE_BASELINE, 'changed_sources': sorted(changed),
                           'unchanged_sources': len(current_sources)-len(changed)}
    if current_sources['LoopCtrlUITests/NG2Runtime.swift'] != RETAINED_RUNTIME_SHA256:
        raise ValueError('TEST085 retained Runtime source changed')
    client_before = client_source_identity(driver)
    suites = native_suites(upstream) + client_suites() + package_suites()
    selected_cases(case for _label, cases in suites for case in cases)
    fixture = importlib.import_module('tests.test_native_controller')
    abi = {name: ctypes.sizeof(getattr(fixture, name))
           for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    if abi != {'Scene': 23864, 'Status': 192, 'Event': 128, 'MotionWait': 48, 'RecoveryStatus': 456}:
        raise ValueError('native ABI layout changed')
    record = {'scope': 'TEST085 verified late-source scheduling and independent clear-floor stationary proof; device feedback first',
              'source_identity': before, 'native_change_scope': native_change_scope,
              'client_source_identity': client_before,
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
              'selection_reasons': {'test085-verified-scheduling': 'only an already verified same-ACK MOVE with a late proof source may withdraw its unissued next candidate into the existing bounded synchronization episode; all original source/preparation/deadline guards remain', 'test085-independent-stationary': 'a separate final zero-only proof requires current clear-floor terrain, independent blur/phase/gradient evidence and original fixed numerical boundaries; the old14 stages and known outputs stay first', 'test085-related-controller': 'old100ms publication,200ms source admission, early candidate expiry and delayed-tick rejection remain outside the new qualified path; bounded ABI/query is unchanged', 'test085-related-recovery': 'late real proofs use bounded synchronization; original episode and visual goods priorities remain', 'test085-related-wait076': 'the independent stationary wait keeps original parent and two-beat bounds; UNKNOWN never extends or reopens it', 'test085-related-static075': 'static pixel proof still rejects weak bands, aliases, opposite edges, partials and false unit shifts', 'test085-related-motion075': 'the old full blur/phase pixel dependencies and dynamic-letter rejections remain enforced', 'test085-related-motion067': 'old known movement, blockage, opening and unexpected direction outputs remain intact', 'test085-publication': 'new entry reuses full-evidence ZIP publication; incomplete PNG/cursor data cannot publish or start fresh'}}
    for label, cases in suites:
        run_scope(label, cases, output, record)
    # Workflow and selection changes have their own small unit set, without
    # automatically discovering the historical package/Swift fixture suite.
    for module_name, classes in (('test_device_ci085', ('DeviceHostSelection085Tests',)),):
        module = importlib.import_module(module_name)
        cases = [case for name in classes for case in
                 unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module, name))]
        run_scope('test085-'+module_name, cases, output, record)
    if verifier.inspect_native_sources(upstream, driver) != before:
        raise ValueError('selected tests changed sealed production source')
    reject_fixture_overrides()
    if client_source_identity(driver) != client_before:
        raise ValueError('selected tests changed the pinned production client')
    record['sealed_sources_unchanged_after_tests'] = True
    record['client_source_unchanged_after_tests'] = True
    record['manifest_sha256'] = hashlib.sha256((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes()).hexdigest()
    (output/'test085-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
    print('PASS TEST085 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
