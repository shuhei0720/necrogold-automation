"""Run only TEST069 gate/collection/publication changes and related units before device feedback.

All native fixtures compile the sealed patched upstream used by the IPA.
Historical synthetic worlds and Runtime mutation suites remain explicit lanes.
"""
import argparse
import ctypes
import hashlib
import importlib
import io
import json
from pathlib import Path
import sys
import subprocess
import unittest


GATE069_METHODS = frozenset({
    'test_new_independent_stationary_pair_and_fresh_hud_open_then_enter',
    'test_unknown_pairs_cannot_authorize_and_original_sync_budget_expires',
    'test_geometry_protection_goods_and_known_motion_drift_end_refresh',
    'test_expired_original_ticket_and_sent_unknown_never_refresh',
    'test_refresh_uses_actual_commit_and_rejects_unstable_or_wrong_prefix',
    'test_goods_and_owner_guards_preempt_the_refresh_or_new_ticket',
    'test_new_ticket_signature_failure_cannot_restart_another_refresh_episode',
    'test_stationary_proof_requires_a_hud_sample_at_least_as_new_as_the_proof',
})
COLLECTION069_METHODS = frozenset({
    'test_slow_stopped_collection_finishes_after_game_and_old_export_deadlines',
    'test_missing_or_unsafe_terminal_fields_keep_the_original_export_deadline',
    'test_unsafe_manifest_cannot_borrow_the_trusted_status_collection_budget',
    'test_nonterminal_unknown_input_still_uses_the_bounded_cancel_cleanup',
    'test_cancel_during_trusted_read_only_collection_sends_no_native_cancel',
    'test_cancel_before_terminal_confirmation_keeps_the_short_cleanup_budget',
    'test_storage_failure_after_trusted_stop_has_no_emergency_native_cancel',
    'test_collection_deadline_starts_at_trusted_observation_before_journal_io',
    'test_interrupted_export_recovers_same_uuid_export_and_cursor_with_no_keepalive',
    'test_final_journal_over_collection_deadline_keeps_complete_evidence_unresolved',
})
COLLECTION069_CLI_METHODS = frozenset({
    'test_outcome_receives_record_and_cancel_state_before_any_completion_display',
})
PUBLICATION069_METHODS = frozenset({
    'test_resolved_without_receipt_publishes_only_and_archive_contains_exact_snapshot',
    'test_only_a_separate_invocation_after_verified_publication_can_start',
    'test_missing_png_or_incomplete_cursor_cannot_be_published_or_start_fresh',
    'test_failure_before_receipt_retries_publication_without_a_native_call',
    'test_interrupted_provider_rename_retains_local_and_retries_without_start',
    'test_interrupted_or_corrupted_provider_copy_is_never_published_and_can_retry',
    'test_existing_different_final_is_never_overwritten',
    'test_changed_mount_or_deleted_zip_is_publication_only_even_with_local_receipt',
    'test_preflight_failure_is_not_a_completed_result',
    'test_cancellation_and_old_runtime_leave_every_source_byte_intact',
    'test_wrapper_uses_stable_local_output_and_honors_the_native_outcome_cancel',
    'test_provider_part_symlink_cannot_modify_an_unrelated_file',
    'test_mutation_between_certificate_and_inventory_is_not_certified_as_a_snapshot',
    'test_missing_drain_safety_fields_cannot_certify_publication',
    'test_launcher_delegates_completion_to_the_verified_local_publication_wrapper',
})
RELATED_DOOR_METHODS = frozenset({
    'test_unchanged_door_survives_distant_palette_drift_and_opens_before_entry',
    'test_door_requires_strict_blocked_signature_proof',
})
RELATED_EDGE_METHODS = frozenset({
    'test_one_verified_edge_step_returns_to_normal_gold_route_but_never_repeats_hint',
    'test_unstarted_edge_deadline_can_refit_without_reusing_id_or_sync_budget',
})
RELATED_CADENCE_METHODS = frozenset({
    'test_second_proof_checks_actual_commit_against_unchanged_visual_deadline',
    'test_early_second_move_can_publish_the_original_next_beat_without_reacquiring',
})
RELATED_MOTION_METHODS = frozenset({
    'test_extra_evidence_requires_exact_closed_gold_bracket',
})
RECOVERY_METHODS = frozenset({
    'test_additive_queries_preserve_layout_and_initial_zeroes',
})
RELATED_PAGED_METHODS = frozenset({
    'test_export_completion_does_not_resolve_unknown_input_or_ui_frozen',
    'test_manifest_identity_cannot_change_between_recovery_invocations',
    'test_final_journal_io_cannot_publish_a_late_or_newly_cancelled_export_as_resolved',
})
RELATED_COLLECTION_METHODS = frozenset({
    'test_completed_metadata_never_replaces_validation_of_saved_bytes_or_the_full_cursor',
    'test_literal_legacy_recovery_keeps_its_api_uuid_clock_and_complete_image_evidence',
})
NATIVE_CASES = (
    ('tests.test_native_gate069', 'NativeGate069Tests', 'test069-gate', GATE069_METHODS, True),
    ('tests.test_native_device066', 'NativeDevice066Tests', 'test069-related-door', RELATED_DOOR_METHODS, False),
    ('tests.test_native_edge068', 'NativeEdge068Tests', 'test069-related-edge', RELATED_EDGE_METHODS, False),
    ('tests.test_native_cadence067', 'NativeCadence067Tests', 'test069-related-cadence', RELATED_CADENCE_METHODS, False),
    ('tests.test_native_motion067', 'NativeMotion067Tests', 'test069-related-motion', RELATED_MOTION_METHODS, False),
    ('tests.test_native_recovery', 'NativeRecoveryTests', 'test069-related-recovery', RECOVERY_METHODS, False),
)
CLIENT_CASES = (
    ('tests.test_native_collection069', 'NativeCollection069Tests', 'test069-collection', COLLECTION069_METHODS, True),
    ('tests.test_native_collection069', 'NativeCollection069CliTests', 'test069-collection-cli', COLLECTION069_CLI_METHODS, True),
    ('tests.test_native_publication069', 'Publication069Tests', 'test069-publication', PUBLICATION069_METHODS, True),
    ('tests.test_native_paged_results', 'PagedResultsTests', 'test069-related-paged', RELATED_PAGED_METHODS, False),
    ('tests.test_native_collection068', 'NativeCollection068Tests', 'test069-related-collection', RELATED_COLLECTION_METHODS, False),
)
CORE_MODULES = ('tests.test_native_controller', 'tests.test_native_recovery',
                'tests.test_native_beat', 'tests.test_native_perception', 'tests.test_native_navigation')
NATIVE_BASELINE = 'a5757228d867855af81d1325feca7fc7e7c14f5f'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Controller.c'}
CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069')


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
    return [(label, method_cases(getattr(modules[name], class_name), methods, exact=exact))
            for name, class_name, label, methods, exact in NATIVE_CASES]


def client_source_identity(driver):
    native = importlib.import_module('necroprobe.native_walk')
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
        sources[name] = {'path': relative, 'sha256': hashlib.sha256(raw).hexdigest()}
    if (native.REVISION != 'native-walk-v14' or native.API_VERSION != '1.98.15-ngg2'
            or native.CAPABILITY != 'necrogold_native_v13'):
        raise ValueError('collection client revision/API/capability changed')
    return {'modules': sources, 'driver_commit': code, 'revision': native.REVISION, 'api_version': native.API_VERSION,
            'capability': native.CAPABILITY}


def client_suites():
    modules = {name: importlib.import_module(name) for name in dict.fromkeys(row[0] for row in CLIENT_CASES)}
    native = importlib.import_module('necroprobe.native_walk')
    publication = importlib.import_module('necroprobe.test069')
    if publication.native is not native:
        raise ValueError('production publication wrapper is not bound to the actual driver client')
    for name, module in modules.items():
        alias = sys.modules.get(name.rsplit('.', 1)[-1])
        for fixture in (module, alias):
            if fixture is not None and fixture.native is not native:
                raise ValueError('collection fixture is not bound to the actual driver client: '+name)
            if fixture is not None and getattr(fixture, 'publication', publication) is not publication:
                raise ValueError('publication fixture is not bound to the actual driver wrapper: '+name)
    return [(label, method_cases(getattr(modules[name], class_name), methods, exact=exact))
            for name, class_name, label, methods, exact in CLIENT_CASES]


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
    (output/'test062-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
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
    if (before['api_version'] != '1.98.15-ngg2' or before['client_capability'] != 'necrogold_native_v13'
            or len(before['native_source_sha256']) != 22):
        raise ValueError('TEST069 sealed source identity is not installed')
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'], cwd=driver, text=True))
    baseline_sources = {name: row['patched_sha256'] for name, row in baseline['files'].items()}
    baseline_sources.update({name: row['sha256'] for name, row in baseline['additions'].items()})
    current_sources = before['native_source_sha256']
    changed = {name for name in current_sources if current_sources[name] != baseline_sources.get(name)}
    if set(current_sources) != set(baseline_sources) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('TEST069 native change scope differs')
    native_change_scope = {'baseline': NATIVE_BASELINE, 'changed_sources': sorted(changed),
                           'unchanged_sources': len(current_sources)-len(changed)}
    client_before = client_source_identity(driver)
    suites = native_suites(upstream) + client_suites()
    fixture = importlib.import_module('tests.test_native_controller')
    abi = {name: ctypes.sizeof(getattr(fixture, name))
           for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    if abi != {'Scene': 23864, 'Status': 192, 'Event': 128, 'MotionWait': 48, 'RecoveryStatus': 456}:
        raise ValueError('native ABI layout changed')
    record = {'scope': 'TEST069 gate/collection/publication units and named related regressions; device feedback first',
              'source_identity': before, 'native_change_scope': native_change_scope,
              'client_source_identity': client_before,
              'abi_bytes': abi, 'device_test': 'not_run',
              'not_run': ['full Controller/Recovery/Beat/Perception/Navigation suites',
                          'Runtime synthetic public/mutation suites', 'synthetic shop/world suites',
                          'unselected client and RPC suites', 'unrelated initial/icon/unsent suites',
                          'unchanged workflow/publisher unit suites', 'private recorded-image corpus (local only)'],
              'selection_reasons': {
                  'test069-gate': 'retire a known-unsent door ticket, require an independent stationary pair and fresh HUD, and preserve original budgets and authority',
                  'test069-collection': 'only trusted terminal drained safe-input status authorizes independent read-only collection; unsafe and cancelled paths cannot mutate native',
                  'test069-collection-cli': 'pass the native outcome and cancellation state to publication before showing completion',
                  'test069-publication': 'durable local spool, complete verified PNG/cursor inventory and atomic single ZIP publication; interrupted publication must never start a new game',
                  'test069-related-door': 'retain original closed-door quiet proof and opening versus entry distinction',
                  'test069-related-edge': 'retain successful edge-to-gold path and original unstarted edge recovery budget',
                  'test069-related-cadence': 'preserve successful original next beat and actual-commit visual deadline',
                  'test069-related-motion': 'retain exact closed gold bracket requirement without lowering motion thresholds',
                  'test069-related-recovery': 'unchanged public ABI confirmed through actual C queries',
                  'test069-related-paged': 'unsafe input must not resolve, export identity stays fixed and final IO rechecks cancel/deadline',
                  'test069-related-collection': 'retain completed-byte validation and literal legacy same-run evidence'}}
    for label, cases in suites:
        run_scope(label, cases, output, record)
    # Workflow and selection changes have their own small unit set, without
    # automatically discovering the historical package/Swift fixture suite.
    for module_name, classes in (('test_device_ci', ('DeviceHostSelectionTests',)),):
        module = importlib.import_module(module_name)
        cases = [case for name in classes for case in
                 unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module, name))]
        run_scope('test062-'+module_name, cases, output, record)
    if verifier.inspect_native_sources(upstream, driver) != before:
        raise ValueError('selected tests changed sealed production source')
    if client_source_identity(driver) != client_before:
        raise ValueError('selected tests changed the pinned production client')
    record['sealed_sources_unchanged_after_tests'] = True
    record['client_source_unchanged_after_tests'] = True
    record['manifest_sha256'] = hashlib.sha256((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes()).hexdigest()
    (output/'test062-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
    print('PASS TEST069 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
