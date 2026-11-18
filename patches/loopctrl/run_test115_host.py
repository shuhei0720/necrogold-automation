"""Selected TEST115 native contracts, bound to installed sealed sources.

Author inventories must be finalized before any test is executed. Previous
device suites remain immutable history; they are not implicitly selected.
"""
import argparse
import ctypes
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import sys
import unittest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('test115_source_utils', HERE/'run_test094_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
selected_cases, method_cases = shared.selected_cases, shared.method_cases
NATIVE_BASELINE = 'c84e74f8934f88a05b02e4c58a899d2e3ebae519'
SCOPE_FINALIZED = True
RUNTIME_SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Navigation.c', 'LoopCtrlUITests/NG2Runtime.swift'})
EXPECTED_NATIVE_ADDITIONS = frozenset()
CLIENT_PRODUCT_CHANGES = frozenset()  # Existing Python product bytes are retained.
# Finalized only after the independent native authors freeze their selectors.
CASES = (
    ('tests.test_native_passage115', 'NativePassageFringe115Tests', 'test115-native-NativePassageFringe115Tests', frozenset({
        'test_fringe_needs_full_observed_support_and_positive_inside_floor',
        'test_fringe_rejects_nonclear_goods_protection_and_no_floor_vantage',
        'test_observed_floor_fringe_adds_only_upper_left_dark_mouth',
    }), True),
    ('tests.test_native_passage115', 'NativePassageSource115Tests', 'test115-native-NativePassageSource115Tests', frozenset({
        'test_clear_passage_presend_refresh_reissues_same_physical_ticket_and_epoch',
        'test_only_one_refinement_per_physical_ticket_and_repetitions_keep_its_source',
        'test_refinement_rejects_wrong_prefix_protection_local_material_choice_and_expiry',
        'test_started_ack_or_unknown_input_never_refreshes_or_resends',
    }), True),
    ('tests.test_native_passage115', 'NativeUnlocalizedZero115Tests', 'test115-native-NativeUnlocalizedZero115Tests', frozenset({
        'test_actual_gold_goods_protection_and_lost_material_are_not_qualified',
        'test_invalid_sources_directions_and_actual_translation_never_qualify_zero',
        'test_unlocalized_positive_uses_strict_zero_evidence_without_rewriting_motion',
    }), True),
    ('tests.test_native_passage115', 'NativeUnlocalizedWait115Tests', 'test115-native-NativeUnlocalizedWait115Tests', frozenset({
        'test_candidate_reproof_does_not_extend_original_two_beat_wait',
        'test_independent_candidate_zero_then_blur_waits_without_input_and_reproves',
        'test_issued_but_unbegun_candidate_blur_retires_only_its_permission',
        'test_issued_candidate_ticket_cannot_begin_beyond_original_parent',
        'test_ready_before_W_can_prepare_and_begin_after_W_within_original_parent',
        'test_ready_or_issued_blur_at_W_expires_without_renewing_observation',
        'test_ready_ticket_keeps_normal_window_and_original_parent_after_W',
    }), True),
    ('tests.test_native_shared_zero115', 'NativeSharedPassageZero115Tests', 'test115-native-NativeSharedPassageZero115Tests', frozenset({
        'test_invalid_layout_and_known_motion_keep_normal_precedence_and_full_result',
        'test_unknown_positive_reuses_two_views_and_all_original_raw_candidates',
    }), True),
    ('tests.test_native_shop115', 'NativeShop115Tests', 'test115-native-NativeShop115Tests', frozenset({
        'test_partial_forged_complete_negative_cannot_become_a_restart',
        'test_partial_normal_candidate_has_priority_over_any_observation',
        'test_partial_normal_probes_two_zeros_one_up_then_unknown_never_mints_second_up',
        'test_partial_one_up_then_normal_complete_goods_durable_and_restart',
        'test_partial_pairwise_zero_cannot_replace_the_fixed_new_anchor_or_retry_it',
        'test_partial_probe_result_boundaries_never_authorize_the_new_view',
        'test_partial_projection_change_queues_independent_current_data',
        'test_partial_requalification_rejects_real_goods_wall_route_and_unexplained_changes',
        'test_partial_requires_yield_profile_matching_prefix_and_original_parent',
        'test_partial_two_zeros_without_a_new_phase_sample_cannot_use_old_fit',
        'test_phone_delay_normal_hhdd_reaches_complete_negative_and_restart',
    }), True),
    ('tests.test_native_current_view114', 'NativeCurrentView114Tests', 'test115-native-NativeCurrentView114Tests', frozenset({
        'test_begun_acknowledged_or_unknown_pause_is_never_retired_for_current_data',
        'test_candidate_from_old_or_new_normal_pixels_has_priority_over_view',
        'test_current_normal_job_two_direct_proofs_new_fit_then_one_up_and_normal_restart',
        'test_only_exact_unbegun_pause_can_withdraw_before_current_bind',
        'test_profile_without_runtime_return_drain_fences_cannot_requalify_current_view',
        'test_two_pairwise_zeros_do_not_bridge_the_immutable_current_anchor',
    }), False),
    ('tests.test_native_upper_entry112', 'NativeUpperEntry112Tests', 'test115-native-NativeUpperEntry112Tests', frozenset({
        'test_four_started_inputs_exhaust_observation_without_general_navigation',
        'test_fresh_queued_full_after_fourth_input_or_move_parent_expiry_still_keeps_candidate',
        'test_initial_partial_counterexamples_do_not_gain_the_frozen_upper_route',
        'test_initial_partial_positive_hints_preempt_any_upper_input',
        'test_normal_producer_partial_probes_complete_public_c_hhdd_and_single_negative',
        'test_remaining_live_schedule_budget_never_renews_the_fixed_parent',
        'test_started_unknown_move_never_resends_or_credits_a_new_step',
        'test_unobserved_second_floor_waits_without_guessing_or_restoring_root',
    }), False),
    ('tests.test_native_passage_unsent076', 'NativePassageUnsent076Tests', 'test115-native-NativePassageUnsent076Tests', frozenset({
        'test_future_passage_ticket_and_stale_callbacks_never_reuse_old_authority',
        'test_passage_recovery_never_extends_proof_walk_or_session_budgets',
        'test_started_unknown_authority_and_changed_evidence_cannot_gain_passage_recovery',
    }), False),
    ('tests.test_native_stationary_wait076', 'NativeStationaryWait076Tests', 'test115-native-NativeStationaryWait076Tests', frozenset({
        'test_adjacent_blocked_frames_cannot_replace_the_original_anchor',
        'test_ready_or_issued_unknown_does_not_reopen_the_same_wait',
        'test_wait_deadline_is_fixed_and_unknown_frames_do_not_extend_it',
    }), False),
    ('tests.test_native_plural_wait103', 'NativePluralWait103Tests', 'test115-native-NativePluralWait103Tests', frozenset({
        'test_cancel_or_unknown_synth_cannot_reuse_the_plural_wait',
        'test_original_wait_and_parent_equalities_never_renew_from_plural_proof',
    }), False),
    ('tests.test_native_unsent_continuous', 'NativeUnsentContinuousTests', 'test115-native-NativeUnsentContinuousTests', frozenset({
        'test_same_and_fresh_reissues_retire_without_mutating_old_fields',
        'test_started_ack_unknown_cancel_and_goods_never_use_unsent_recovery',
    }), False),
    ('tests.test_native_controller', 'NativeControllerTests', 'test115-native-NativeControllerTests', frozenset({
        'test_fresh_and_same_share_run_eight_and_chain_two_budgets',
    }), False),
    ('tests.test_native_positive114', 'NativePositive114Tests', 'test115-native-NativePositive114Tests', frozenset({
        'test_pristine_image_with_price_and_no_name_keeps_target_and_no_handoff',
        'test_valid_price_ambiguous_image_is_retained_through_durable_pause',
    }), True),
)
CORE_MODULES = (
    'tests.test_beat_sync',
    'tests.test_native_beat',
    'tests.test_native_blocked067',
    'tests.test_native_bottom_shop103',
    'tests.test_native_classification111',
    'tests.test_native_clear_stationary095',
    'tests.test_native_controller',
    'tests.test_native_current_view114',
    'tests.test_native_cycle094',
    'tests.test_native_cycle_binary095',
    'tests.test_native_entry_corridor102',
    'tests.test_native_entry_episode102',
    'tests.test_native_full_framing101',
    'tests.test_native_goods113',
    'tests.test_native_handoff099',
    'tests.test_native_irregular110',
    'tests.test_native_motion067',
    'tests.test_native_motion075',
    'tests.test_native_navigation',
    'tests.test_native_observation072',
    'tests.test_native_offer_coverage104',
    'tests.test_native_opened_entry093',
    'tests.test_native_opened_fade100',
    'tests.test_native_partial_entry097',
    'tests.test_native_partial_framing097',
    'tests.test_native_passage072',
    'tests.test_native_passage115',
    'tests.test_native_passage_navigation072',
    'tests.test_native_passage_unsent076',
    'tests.test_native_perception',
    'tests.test_native_plural_stationary103',
    'tests.test_native_plural_wait103',
    'tests.test_native_positive114',
    'tests.test_native_recovery',
    'tests.test_native_restart_yield112',
    'tests.test_native_ring094',
    'tests.test_native_ring_bank094',
    'tests.test_native_shared_zero115',
    'tests.test_native_shop115',
    'tests.test_native_shop_coverage102',
    'tests.test_native_shop_geometry101',
    'tests.test_native_side_shop100',
    'tests.test_native_single_offer108',
    'tests.test_native_single_sign_shop103',
    'tests.test_native_singleton_stationary095',
    'tests.test_native_static075',
    'tests.test_native_stationary_texture085',
    'tests.test_native_stationary_wait076',
    'tests.test_native_stop099',
    'tests.test_native_structural_cycle096',
    'tests.test_native_structural_shop096',
    'tests.test_native_unsent_continuous',
    'tests.test_native_upper_entry112',
    'tests.test_target_assessment087',
)
CURRENT_MAC_CASES = ('passage_fresh', 'partial_view', 'partial_cancel', 'post_begin_clock')
NEW_PATHS = frozenset({
    'necroprobe/test115.py',
    'test_115.sh',
    'patches/loopctrl/check_runtime115.py',
    'patches/loopctrl/ngg2_runtime115_fixture.c',
    'patches/loopctrl/ngg2_runtime115_tests.swift',
    'patches/loopctrl/run_test115_host.py',
    'patches/loopctrl/run_test115_python39.py',
    'patches/loopctrl/test_device_ci115.py',
    'tests/test_native_passage115.py',
    'tests/test_native_shop115.py',
    'tests/test_native_shared_zero115.py',
    'patches/loopctrl/ngg2_runtime115_begin_fixture.c',
})

BASELINE_RUNTIME_SHA256 = 'dc082fd9658df32924c90423c544030d327c744f4224d4d8c868762a6e2e741f'
BASELINE_RING_SHA256 = '571ea39396521ceaf876f995b4c6db75d89410bdd453da56eb6eaa017b1cb879'
PRODUCT_PATHS = ('necroprobe/test115.py', 'test_115.sh', 'necroprobe/test114.py',
    'necroprobe/campaign_diagnostics114.py', 'necroprobe/validation.py', 'necroprobe/protocol.py')


def reject_fixture_overrides():
    if any(name == 'BASELINE_NAV' or name.startswith('NECRO_TEST')
            or re.match(r'^NECRO[0-9]+_', name) for name in os.environ):
        raise ValueError('TEST115 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not RUNTIME_SCOPE_FINALIZED or not CURRENT_MAC_CASES:
        raise ValueError('TEST115 native/client/current Mac author scopes are pending')
    labels = [row[2] for row in CASES]
    if not CASES or len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST115 empty or duplicate selected scope')
    if not NEW_PATHS:
        raise ValueError('TEST115 exact repository source scope is pending')


def native_delta(before, current, allowed=EXPECTED_NATIVE_CHANGES):
    changed = {path for path in current if before.get(path) != current[path]}
    if (set(before) != set(current) or len(current) != 36
            or changed != set(allowed) or not allowed):
        raise ValueError('TEST115 exact 36-source native delta differs')
    return changed


def manifest_sources(manifest):
    return {**{name: row['patched_sha256'] for name, row in manifest['files'].items()},
            **{name: row['sha256'] for name, row in manifest['additions'].items()}}


def runtime_source_identity(before, current):
    if not RUNTIME_SCOPE_FINALIZED or not CURRENT_MAC_CASES:
        raise ValueError('TEST115 current Mac source scope is pending')
    runtime = 'LoopCtrlUITests/NG2Runtime.swift'
    if (before.get(runtime) != BASELINE_RUNTIME_SHA256 or current.get(runtime) == BASELINE_RUNTIME_SHA256
            or not isinstance(current.get(runtime), str) or not re.fullmatch('[0-9a-f]{64}', current[runtime])):
        raise ValueError('TEST115 approved current Runtime delta differs')
    ring = 'LoopCtrlUITests/NG2Ring.c'
    if before.get(ring) != BASELINE_RING_SHA256 or current.get(ring) != BASELINE_RING_SHA256:
        raise ValueError('TEST115 retained Ring source differs')
    return dict(policy='changed_current_runtime_boundaries_required',
        baseline_runtime_sha256=before['LoopCtrlUITests/NG2Runtime.swift'],
        current_runtime_sha256=current['LoopCtrlUITests/NG2Runtime.swift'],
        current_controller_sha256=current['LoopCtrlUITests/NG2Controller.c'],
        current_ring_sha256=current['LoopCtrlUITests/NG2Ring.c'],
        current_navigation_sha256=current['LoopCtrlUITests/NG2Navigation.c'],
        current_mac_execution_required=True, expected_current_mac_cases=list(CURRENT_MAC_CASES),
        before_runtime_api_assertion_required=False, before_runtime_clock_assertion_required=True,
        executed_in_host_selector=False)


def source_identity(driver, sealed):
    ensure_scope()
    reject_fixture_overrides()
    code = git(driver, 'rev-parse', 'HEAD').decode().strip()
    manifest_path = 'patches/loopctrl/ngg2-manifest.json'
    manifest_raw = pinned_bytes(driver, manifest_path, code)
    manifest = json.loads(manifest_raw)
    old = manifest_sources(json.loads(git(driver, 'show', NATIVE_BASELINE+':'+manifest_path)))
    current = sealed['native_source_sha256']
    changed = native_delta(old, current)
    if manifest_sources(manifest) != current:
        raise ValueError('TEST115 installed native sources differ from pinned manifest')
    expected_api = dict(api_version='1.98.16-ngg2', client_capability='necrogold_native_v15',
        cycle_capability='necrogold_native_cycle_v1', cycle_profile='normal-1-1-cycle-v1',
        irregular_capability='necrogold_native_irregular_v1', irregular_profile='normal-1-1-irregular-v1',
        image_price_capability='necrogold_native_image_price_v1', compiler_profile_version=3,
        restart_yield_capability='necrogold_native_restart_yield_v1', restart_yield_start_flag='yield_after_restart')
    if any(manifest.get(key) != value for key, value in expected_api.items()):
        raise ValueError('TEST115 API/capability/profile identity differs')
    baseline_paths = {p.decode() for p in git(driver, 'ls-tree', '-r', '--name-only', '-z', NATIVE_BASELINE).split(b'\0') if p}
    differences = {p.decode() for p in git(driver, 'diff', '--no-renames', '--name-only', '-z', NATIVE_BASELINE, code, '--').split(b'\0') if p}
    existing = {path for path in differences & baseline_paths if not path.startswith('docs/')}
    approved = {'patches/loopctrl/ngg2/NG2Controller.c', 'patches/loopctrl/ngg2/NG2Navigation.c', 'patches/loopctrl/ngg2/NG2Runtime.swift',
        manifest_path, '.github/workflows/loopctrl-geometry.yml', *CLIENT_PRODUCT_CHANGES}
    added = {path for path in differences-baseline_paths if not path.startswith('docs/')}
    if existing != approved or added != set(NEW_PATHS):
        raise ValueError('TEST115 exact changed/new repository source paths differ')
    if git(driver, 'diff', '--no-ext-diff', '--name-only', code, '--',
            'tests', 'necroprobe', 'tools/ring_native', 'legacy/r12', 'patches/loopctrl',
            '.github/workflows/loopctrl-geometry.yml', 'test_115.sh').strip():
        raise ValueError('TEST115 working source differs from pinned CODE')
    ring_raw = pinned_bytes(driver, 'necroprobe/ring_native_manifest.json', code)
    if ring_raw != git(driver, 'show', NATIVE_BASELINE+':necroprobe/ring_native_manifest.json'):
        raise ValueError('TEST115 canonical ring manifest changed')
    ring = json.loads(ring_raw)
    if len(ring['sources']) != 15 or sum(path.startswith('legacy/r12/') for path in baseline_paths) != 40:
        raise ValueError('TEST115 canonical/R12 source inventory differs')
    fixture_paths = {name.replace('.', '/')+'.py' for name in (*CORE_MODULES, *(row[0] for row in CASES))}
    fixture_paths.update(path for path in NEW_PATHS if path.startswith(('tests/', 'patches/loopctrl/')))
    fixture_paths.update(('patches/loopctrl/run_test094_host.py', 'necroprobe/ring_native_manifest.json', *ring['sources']))
    fixture_sha = {path: sha(pinned_bytes(driver, path, code)) for path in sorted(fixture_paths)}
    products = {path: sha(pinned_bytes(driver, path, code)) for path in (*PRODUCT_PATHS, *sorted(CLIENT_PRODUCT_CHANGES))}
    return dict(driver_commit=code, native_baseline=NATIVE_BASELINE,
        changed_native_sources=sorted(changed), native_added=[],
        runtime_proof_policy=runtime_source_identity(old, current),
        preserved_native_source_sha256={name: value for name, value in current.items() if name not in changed},
        fixture_source_sha256=fixture_sha, product_sha256=products,
        changed_repository_paths=sorted(existing), new_repository_paths=sorted(added),
        unchanged_baseline_repository_paths=sorted(baseline_paths-differences),
        canonical_source_sha256={path: sha(pinned_bytes(driver, path, code)) for path in ring['sources']},
        native_manifest_sha256=sha(manifest_raw),
        limitation='Selected contracts and current Mac callbacks are software evidence; real phone acceptance is separate.')


def native_suites(upstream, driver):
    reject_fixture_overrides()
    names = tuple(dict.fromkeys((*CORE_MODULES, *(row[0] for row in CASES))))
    modules = {name: importlib.import_module(name) for name in names}
    for name, module in modules.items():
        if Path(module.__file__).resolve() != driver/(name.replace('.', '/')+'.py'):
            raise ValueError('TEST115 fixture import escaped pinned driver: '+name)
        module.CORE = upstream/'LoopCtrlUITests'
        alias = sys.modules.get(name.rsplit('.', 1)[-1])
        if alias is not None:
            alias.CORE = upstream/'LoopCtrlUITests'
    reject_fixture_overrides()
    return [(label, method_cases(getattr(modules[name], klass), methods, exact=exact))
            for name, klass, label, methods, exact in CASES]


def run_scope(name, cases, output, evidence):
    cases = selected_cases(cases)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(cases))
    log = stream.getvalue()
    (output/(name+'.txt')).write_text(log)
    print(log, end='', flush=True)
    evidence[name] = dict(selected=[case.id() for case in cases], tests_run=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped), expected_failures=len(result.expectedFailures))
    (output/'test115-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': all selected methods must execute Green')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('driver', 'upstream', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    driver, upstream, output = (getattr(args, name).resolve() for name in ('driver', 'upstream', 'output'))
    ensure_scope()
    sys.path[:0] = [str(driver), str(driver/'tests'), str(HERE)]
    verifier = importlib.import_module('verify_package')
    sealed = verifier.inspect_native_sources(upstream, driver)
    binding = source_identity(driver, sealed)
    suites = native_suites(upstream, driver)
    selected_cases(case for _, cases in suites for case in cases)
    native = importlib.import_module('tests.test_native_controller')
    cycle = importlib.import_module('tests.test_native_cycle094')
    abi = {name: ctypes.sizeof(getattr(native, name)) for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    abi['Cycle'] = ctypes.sizeof(cycle.Cycle)
    if abi != dict(Scene=23864, Status=192, Event=128, MotionWait=48, RecoveryStatus=456, Cycle=216):
        raise ValueError('TEST115 public ABI changed')
    output.mkdir(parents=True, exist_ok=True)
    evidence = dict(scope='TEST115 selected device-failure contracts', source_identity=sealed,
        production_source_binding=binding, abi_bytes=abi, device_test='not_run',
        not_run=['historical whole host/Runtime suites', 'iPhone reach rate, rare-target precision and human speed acceptance'])
    for label, cases in suites:
        run_scope(label, cases, output, evidence)
    selector = importlib.import_module('test_device_ci115')
    run_scope('test115-selector', unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection115Tests), output, evidence)
    if verifier.inspect_native_sources(upstream, driver) != sealed or source_identity(driver, sealed) != binding:
        raise ValueError('TEST115 tests changed sealed source')
    reject_fixture_overrides()
    evidence.update(sealed_sources_unchanged_after_tests=True,
        manifest_sha256=sha((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes()))
    (output/'test115-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS TEST115 selected source-bound contracts; Mac execution and phone acceptance remain separate')


if __name__ == '__main__':
    main()
