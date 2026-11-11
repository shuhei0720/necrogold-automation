"""Run TEST081 stopped-shop fixes and opt-in restart evidence with named related regressions.

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


NATIVE_CASES = (
    ('tests.test_native_side_gate081', 'NativeSideGate081Tests', 'test081-side-gate', frozenset({
        'test_fixed_axis_strong_52_bands_95_percent_and_all73_15pp_competitor_rules',
        'test_known_phase_requires_same_unit_all_dependencies_bands_finite_scores_and_exact_limits',
        'test_new_gate_requires_unknown_or_dirt_projections_and_orthogonal_two_cell_geometry',
        'test_old_noncollinear_stones_and_all_nine_translations_reject_different_pair_ambiguity',
        'test_public_four_direction_side_gate_unit_keeps_next_navigation_unentered',
        'test_raw_high_finite_unit_gap_all73_and_known_primary_outputs_are_preserved',
        'test_scope_requires_floor_candidate_unknown_goods_no_items_protection_and_old_endpoints',
        'test_stationary_reverse_two_cells_eight_and_half_pixels_never_receive_unit_credit',
    }), True),
    ('tests.test_native_closed_refresh081', 'NativeClosedRefresh081Tests', 'test081-closed-refresh', frozenset({
        'test_direct_anchor_strict_proof_and_independent_current_prefix_are_required',
        'test_four_direction_closed_gate_refresh_accepts_remote_stone_without_credit',
        'test_geometry_near_cells_and_all_protection_materials_bound_stone_scope',
        'test_goods_cancel_phase_owner_and_unknown_sent_input_preempt_refresh',
        'test_original_horizons_current_hud_and_fifty_ms_preparation_remain_frozen',
        'test_published_identity_source_and_old_refresh_scope_do_not_broaden',
    }), True),
    ('tests.test_native_clipped_entry081', 'NativeClippedEntry081Tests', 'test081-clipped-entry', frozenset({
        'test_clipped_partial_goods_preserve_original_up_entry_then_real_move_and_goods_hold',
        'test_goods_cancel_owner_and_started_unknown_send_override_clipped_retention',
        'test_new_protection_nonedge_items_gold_or_near_changes_cannot_use_quarantine',
        'test_original_deadline_actual_commit_prefix_and_total_budgets_remain_fixed',
        'test_source_mask_and_top_gold_quarantine_survive_mask_zero_return',
        'test_unopened_other_direction_or_entered_state_does_not_gain_clipped_permission',
    }), True),
    ('tests.test_native_navigation', 'NativeNavigationTests', 'test081-related-navigation', frozenset({
        'test_closed_gate_high_intensity_rescue_and_repeated_texture_rejection',
    }), False),
    ('tests.test_native_closed_gate078', 'NativeClosedGate078Tests', 'test081-related-closed-gate', frozenset({
        'test_cache_equals_direct_scalar_all73_and_camera_center_bands_are_independent',
    }), False),
    ('tests.test_native_revealed_gate079', 'NativeRevealedGate079Tests', 'test081-related-revealed-gate', frozenset({
        'test_public_four_direction_reveal_is_a_unit_then_nav_approaches_without_entry',
        'test_raw_normal_side_unit_gap_and_known_output_boundaries',
    }), False),
    ('tests.test_native_sparse_gate080', 'NativeSparseGate080Tests', 'test081-related-sparse-gate', frozenset({
        'test_phase_all73_matches_independent_scalar_specification',
        'test_public_four_direction_sparse_arrival_reaches_closed_door_without_entry',
    }), False),
    ('tests.test_native_observation072', 'NativeObservation072Tests', 'test081-related-observation', frozenset({
        'test_current_floor_refresh_rejects_changed_action_protection_and_old_input_authority',
        'test_current_hud_fifty_ms_preparation_and_original_budgets_remain_required',
        'test_exhausted_same_chain_reobserves_floor_before_a_new_future_ticket',
        'test_independent_floor_proof_and_published_ticket_keep_full_current_permission',
        'test_protected_gold_wall_does_not_block_the_same_observed_entry',
        'test_refresh_limit_is_once_per_verified_progress_and_eight_per_session',
    }), False),
    ('tests.test_native_open_entry077', 'NativeOpenEntry077Tests', 'test081-related-open-entry', frozenset({
        'test_accepted_new_gold_cannot_disappear_or_shift_within_same_ticket',
        'test_opened_entry_reveal_preserves_ticket_then_enters_on_original_beat',
        'test_original_deadline_prefix_goods_and_control_priority_remain',
    }), False),
    ('tests.test_native_shop071', 'NativeShop071Tests', 'test081-related-shop', frozenset({
        'test_unknown_entry_synth_never_reuses_the_quiet_permission',
    }), False),
)

CLIENT_CASES = (
    ('tests.test_native_profile081', 'NativeEvidenceProfile081Tests', 'test081-evidence-profile', frozenset({
        'test_every_revision_binds_profile_api_and_aggregate_without_wire_upgrade',
        'test_fresh_cap15_start_uses_v16_evidence_profile_and_existing_paged_wire',
        'test_fresh_client_rejects_cap14_only_app_before_any_start',
        'test_manifest_checkpoint_and_image_bounds_are_selected_by_trusted_profile',
        'test_never_started_v1_migrates_both_contract_fields_once_with_same_uuid',
        'test_paged_v2_above_four_mib_verifies_every_png_cursor_and_published_zip',
        'test_started_v1_recovery_preserves_all_fifteen_uuid_api_and_no_new_start',
        'test_v1_wire_start_remains_allowed_and_claimed_v2_status_cannot_upgrade_v15',
    }), True),
    ('tests.test_native_compat070', 'NativeCompatibility070Tests', 'test081-related-compatibility', frozenset({
        'test_all_historical_journals_keep_their_api_limit_and_required_evidence',
        'test_encrypted_current_run_roundtrips_eight_in_status_manifest_and_both_journals',
        'test_never_started_v14_upgrades_only_its_first_start_and_rejects_an_old_ipa',
        'test_persisted_preflight_and_result_api_cannot_cross_revision_boundaries',
        'test_started_v14_recovers_same_uuid_and_original_api_without_a_new_start',
        'test_status_and_manifest_limits_are_bound_to_expected_api_and_reject_invalid_types',
        'test_unbound_diagnostics_keep_three_while_trusted_new_status_keeps_eight_recursively',
        'test_version_map_and_feature_memberships_preserve_every_prior_revision',
    }), True),
    ('tests.test_native_walk', 'NativeImageTests', 'test081-related-legacy-images', frozenset({
        'test_invalid_saved_image_metadata_and_limits_are_journal_errors',
        'test_old_journal_images_project_extra_fields_and_resave_no_secrets',
    }), False),
    ('tests.test_native_recovery_results', 'RecoveryResultsTests', 'test081-related-recovery-results', frozenset({
        'test_current_revision_requires_new_api_capability_and_test061_output',
        'test_each_revision_binds_preflight_status_and_result_metadata_to_one_api',
        'test_literal_v1_through_v13_recover_ready_old_api_journals_with_no_get_or_start',
        'test_never_started_old_journal_uses_v15_contract_for_its_first_start',
    }), False),
    ('tests.test_native_motion_references', 'MotionReferenceTests', 'test081-related-motion-references', frozenset({
        'test_client_055_revision_capability_and_output',
        'test_current_revision_and_required_capability',
        'test_literal_v11_started_recovery_allows_absent_trace_without_schema_or_start',
        'test_literal_v12_encrypted_manifest_still_requires_motion_references',
        'test_literal_v12_started_recovery_keeps_trace_uuid_and_both_journals_without_schema_or_start',
    }), False),
    ('tests.test_native_paged_results', 'PagedResultsTests', 'test081-related-paged-results', frozenset({
        'test_new_paged_export_uses_remaining_180_seconds_and_old_journal_keeps_its_185_seconds',
    }), False),
)

PACKAGE_CASES = (
    ('patches.loopctrl.test_apply_ngg2', 'NGG2ApplyTests', 'test081-related-package', frozenset({
        'test_native_v14_package_requires_actual_api16_and_strict_profile_v2',
        'test_native_v15_evidence_package_keeps_api16_and_strict_profile_v2',
    }), False),
)

CORE_MODULES = ('tests.test_native_controller', 'tests.test_native_recovery',
                'tests.test_native_beat', 'tests.test_native_perception',
                'tests.test_native_motion067', 'tests.test_native_blocked067',
                'tests.test_native_observation072', 'tests.test_native_ui073',
                'tests.test_native_passage_unsent076', 'test_native_perception')
NATIVE_BASELINE = 'acf684bd0eb7b73ac5239e02f0879f9474470b35'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Navigation.c', 'LoopCtrlUITests/NG2Controller.c',
                           'LoopCtrlUITests/NG2Runtime.swift', 'LoopCtrlKit/RPCMethod.swift'}
CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.test081',
                         'necroprobe.validation', 'necroprobe.protocol')
FIXTURE_OVERRIDE_PREFIXES = ('NECRO_TEST063_BASELINE_', 'NECRO_TEST071_BASELINE_',
                             'NECRO_TEST072_BASELINE_', 'NECRO_TEST074_BASELINE_',
                             'NECRO_TEST075_BASELINE_', 'NECRO_TEST076_BASELINE_',
                             'NECRO_TEST077_BASELINE_', 'NECRO_TEST078_BASELINE_',
                             'NECRO_TEST079_BASELINE_', 'NECRO_TEST080_BASELINE_',
                             'NECRO_TEST081_BASELINE_')

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
        if name not in ('necroprobe.test081', 'necroprobe.native_walk') and raw != subprocess.check_output(
                ['git', 'show', NATIVE_BASELINE+':'+relative], cwd=driver):
            raise ValueError('unchanged TEST081 client source differs from the baseline: '+name)
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
    entry = importlib.import_module('necroprobe.test081')
    if publication.native is not native:
        raise ValueError('production publication wrapper is not bound to the actual driver client')
    if entry.device_main is not publication.main:
        raise ValueError('TEST081 entry is not bound to the actual driver publication wrapper')
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
    (output/'test081-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
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
        raise ValueError('TEST081 sealed source identity is not installed')
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'], cwd=driver, text=True))
    baseline_sources = {name: row['patched_sha256'] for name, row in baseline['files'].items()}
    baseline_sources.update({name: row['sha256'] for name, row in baseline['additions'].items()})
    current_sources = before['native_source_sha256']
    changed = {name for name in current_sources if current_sources[name] != baseline_sources.get(name)}
    if set(current_sources) != set(baseline_sources) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('TEST081 native change scope differs')
    native_change_scope = {'baseline': NATIVE_BASELINE, 'changed_sources': sorted(changed),
                           'unchanged_sources': len(current_sources)-len(changed)}
    client_before = client_source_identity(driver)
    suites = native_suites(upstream) + client_suites() + package_suites()
    selected_cases(case for _label, cases in suites for case in cases)
    fixture = importlib.import_module('tests.test_native_controller')
    abi = {name: ctypes.sizeof(getattr(fixture, name))
           for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    if abi != {'Scene': 23864, 'Status': 192, 'Event': 128, 'MotionWait': 48, 'RecoveryStatus': 456}:
        raise ValueError('native ABI layout changed')
    record = {'scope': 'TEST081 side-gate motion, bounded closed refresh, clipped goods entry and opt-in all-restart evidence; device feedback first',
              'source_identity': before, 'native_change_scope': native_change_scope,
              'client_source_identity': client_before,
              'fixture_source_policy': {'baseline_override_env_prefixes': list(FIXTURE_OVERRIDE_PREFIXES),
                  'baseline_override_env_names': ['BASELINE_NAV'],
                  'baseline_overrides': 'forbidden even when empty',
                  'core_binding': 'all canonical and existing bare fixture CORE paths before selection'},
              'abi_bytes': abi, 'device_test': 'not_run',
              'not_run': ['full native suites and unrelated historical regressions',
                          'Runtime integration/mutations (only selected 070 and 081 Mac steps)',
                          'synthetic shop/world suites and private recorded-image corpus',
                          'unrelated full RPC, publisher and package suites'],
              'selection_reasons': {
                  'test081-side-gate': 'all old motion proofs UNKNOWN; exact orthogonal side gate may contribute an independently bounded unit without entry credit',
                  'test081-closed-refresh': 'closed gold gate approaches retain the original anchor proof and limits while tolerating only remote unprotected stone differences',
                  'test081-clipped-entry': 'opened UP entry retains immutable source quarantine for clipped top-edge partial goods without ignoring strict-zero or new protection',
                  'test081-evidence-profile': 'v16 opt-in profile exports all bounded restart evidence while preserving v1 revision/profile/API/budget and no-resend recovery',
                  'test081-related-navigation': 'old high-intensity and repeated-texture rejection remain unchanged',
                  'test081-related-closed-gate': 'cached all73 scalar evidence and camera-center disjoint bands remain unchanged',
                  'test081-related-revealed-gate': 'old singleton reveal unit and raw/known result limits remain unchanged',
                  'test081-related-sparse-gate': 'old all-positive-infinite rescue and scalar all73 phase arithmetic remain unchanged',
                  'test081-related-observation': 'old same-chain proof, original source permissions, current HUD, fifty-ms preparation and session limits remain unchanged',
                  'test081-related-open-entry': 'old four-direction opening/entry separation, accepted GOLD and original deadline/prefix priorities remain unchanged',
                  'test081-related-shop': 'started UNKNOWN entry never gains new quiet resend permission',
                  'test081-related-compatibility': 'all API14/15/16 evidence-count and durable preflight/result revision boundaries remain unchanged',
                  'test081-related-legacy-images': 'old 4MiB journal bounds and secret-field projection remain unchanged',
                  'test081-related-recovery-results': 'old started recovery sends no fresh start; unstarted migration preserves UUID and strict API mapping',
                  'test081-related-motion-references': 'motion references and original selected sources survive legacy encrypted recovery without new starts',
                  'test081-related-paged-results': 'old 185-second and existing paged read-only collection deadline boundaries remain unchanged',
                  'test081-related-package': 'new cap15 and existing cap14 require API16 Runtime plus both strict compiler proofs',
              }}
    for label, cases in suites:
        run_scope(label, cases, output, record)
    # Workflow and selection changes have their own small unit set, without
    # automatically discovering the historical package/Swift fixture suite.
    for module_name, classes in (('test_device_ci081', ('DeviceHostSelection081Tests',)),):
        module = importlib.import_module(module_name)
        cases = [case for name in classes for case in
                 unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module, name))]
        run_scope('test081-'+module_name, cases, output, record)
    if verifier.inspect_native_sources(upstream, driver) != before:
        raise ValueError('selected tests changed sealed production source')
    reject_fixture_overrides()
    if client_source_identity(driver) != client_before:
        raise ValueError('selected tests changed the pinned production client')
    record['sealed_sources_unchanged_after_tests'] = True
    record['client_source_unchanged_after_tests'] = True
    record['manifest_sha256'] = hashlib.sha256((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes()).hexdigest()
    (output/'test081-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
    print('PASS TEST081 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
