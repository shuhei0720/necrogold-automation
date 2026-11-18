"""Selected TEST114 native contracts, bound to installed sealed sources.

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
_spec = importlib.util.spec_from_file_location('test114_source_utils', HERE/'run_test094_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
selected_cases, method_cases = shared.selected_cases, shared.method_cases
NATIVE_BASELINE = '25d9f0d057c97fbab61f8f5d8d23d6b567cb1620'
SCOPE_FINALIZED = True
RUNTIME_SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Ring.c'})
EXPECTED_NATIVE_ADDITIONS = frozenset()
CLIENT_PRODUCT_CHANGES = frozenset({
    'necroprobe/native_cycle.py', 'necroprobe/cycle_publication.py',
    'necroprobe/campaign099.py', 'necroprobe/trial_evidence099.py',
})
CASES = (
    ('tests.test_native_offer_coverage104', 'NativeOfferCoverage104Tests', 'test114-native-NativeOfferCoverage104Tests', frozenset({
        'test_all_strip_templates_and_strong_name_keep_target_priority',
        'test_numeric_certificate_keeps_mapping_finite_score_box_and_absence_guards',
    }), False),
    ('tests.test_native_goods111', 'NativeGoods111Tests', 'test114-native-NativeGoods111Tests', frozenset({
        'test_cancellation_or_deadline_during_independent_fallback_is_not_unknown_success',
        'test_first_incomplete_proof_is_kept_when_no_independent_proof_completes',
    }), False),
    ('tests.test_native_upper_adoption111', 'NativeUpperAdoption111Tests', 'test114-native-NativeUpperAdoption111Tests', frozenset({
        'test_normal_upper_producer_requires_durable_pause_intent_and_real_restart_outcome',
    }), False),
    ('tests.test_native_offer_witness109', 'NativeOfferWitness109Tests', 'test114-native-NativeOfferWitness109Tests', frozenset({
        'test_half_hue_gain_texture_visibility_and_bright_bounds_are_independent',
    }), False),
    ('tests.test_native_goods113', 'NativeGoodsDataRetry113Tests', 'test114-native-NativeGoodsDataRetry113Tests', frozenset({
        'test_a_begun_pause_is_not_withdrawn_or_replaced_by_data_retry',
        'test_candidates_targets_and_malformed_results_never_wait_for_absence_retry',
        'test_changed_item_gold_protection_motion_prefix_cancel_and_parent_cannot_rebind',
        'test_intermediate_unknown_frame_neither_poison_data_retry_nor_grant_authority',
        'test_only_a_definitely_unbegun_pause_can_yield_to_the_fresh_data_wait',
        'test_prepared_pause_does_not_hide_inflight_hard_source_invalidation',
        'test_safe_full_unknown_waits_for_new_normal_negative_without_any_input',
        'test_two_pairwise_zeros_cannot_replace_direct_original_full_proof',
        'test_unknown_and_deadline_retries_share_the_original_two_replacement_budget',
    }), True),
    ('tests.test_native_goods113', 'NativeGoodsUpView113Tests', 'test114-native-NativeGoodsUpView113Tests', frozenset({
        'test_a_prior_real_up_move_keeps_its_single_credit_while_the_new_view_is_independent',
        'test_existing_entry_episode_cannot_gain_an_independent_third_up_allowance',
        'test_known_ack_unknown_motion_gets_one_new_up_ticket_then_real_move_and_normal_negative',
        'test_later_up_ticket_needs_unchanged_original_material_and_direct_zero',
        'test_prepared_pause_cannot_replace_cached_prior_move_source_or_ordinal',
        'test_unknown_after_actual_new_up_does_not_restore_the_single_view_allowance',
        'test_unknown_synth_is_never_reinterpreted_as_known_visual_unknown',
        'test_up_observation_needs_positive_floor_exact_projection_and_single_shop',
        'test_up_view_normal_positive_candidate_preempts_initial_observation',
    }), True),
    ('tests.test_native_ring114', 'NativePhysicalPair114Tests', 'test114-native-NativePhysicalPair114Tests', frozenset({
        'test_alias_exclusive_name_edge_is_swept_before_any_negative',
        'test_cancel_deadline_and_legacy_modes_cannot_gain_alias_absence',
        'test_extra_physical_component_cannot_be_collapsed_into_the_original_pair',
        'test_independent_policy_reuses_its_exact_completed_sweep_within_worker_budget',
        'test_independent_upper_proof_can_use_the_other_measured_row_of_same_pair',
        'test_late_alias_cancel_and_deadline_keep_monotonic_work_and_no_absence',
        'test_other_alias_full_strip_crossing_fixed_hud_cannot_be_collapsed',
        'test_policy_filtered_physical_alias_keeps_its_complete_positive_name_union',
        'test_policy_filtered_physical_alias_keeps_its_complete_primary_strip',
        'test_same_pair_cannot_borrow_a_different_world_item_row_or_protection',
        'test_target_at_other_alias_full_strip_edge_cannot_be_lost',
        'test_target_in_original_row_or_partial_keeps_priority_over_all_aliases',
        'test_two_row_centers_from_one_original_pair_have_one_physical_coverage',
        'test_unobserved_third_sku_price_or_outer_cap_never_becomes_absence',
    }), True),
    ('tests.test_native_ring114', 'NativePhysicalPairAdoption114Tests', 'test114-native-NativePhysicalPairAdoption114Tests', frozenset({
        'test_initial_full_normal_negative_still_needs_new_pause_durable_and_intent',
    }), True),
    ('tests.test_native_current_view114', 'NativeCurrentView114Tests', 'test114-native-NativeCurrentView114Tests', frozenset({
        'test_begun_acknowledged_or_unknown_pause_is_never_retired_for_current_data',
        'test_candidate_from_old_or_new_normal_pixels_has_priority_over_view',
        'test_current_geometry_and_own_normal_result_need_no_relabelled_old_history',
        'test_current_normal_job_two_direct_proofs_new_fit_then_one_up_and_normal_restart',
        'test_current_unknown_motion_or_changed_material_is_sticky_and_cannot_migrate',
        'test_later_static_frame_after_reservation_preserves_the_frozen_current_ticket',
        'test_missing_positive_current_floor_projection_and_expired_parent_do_not_rebind',
        'test_one_direct_proof_and_old_fit_cannot_authorize_current_up',
        'test_only_exact_unbegun_pause_can_withdraw_before_current_bind',
        'test_post_up_unknown_never_restores_current_epoch_or_single_view',
        'test_profile_without_runtime_return_drain_fences_cannot_requalify_current_view',
        'test_two_pairwise_zeros_do_not_bridge_the_immutable_current_anchor',
    }), True),
    ('tests.test_native_positive114', 'NativePositive114Tests', 'test114-native-NativePositive114Tests', frozenset({
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
    'tests.test_native_controller',
    'tests.test_native_current_view114',
    'tests.test_native_cycle094',
    'tests.test_native_cycle_binary095',
    'tests.test_native_entry_corridor102',
    'tests.test_native_entry_episode102',
    'tests.test_native_full_framing101',
    'tests.test_native_goods111',
    'tests.test_native_goods113',
    'tests.test_native_handoff099',
    'tests.test_native_irregular110',
    'tests.test_native_motion067',
    'tests.test_native_motion075',
    'tests.test_native_navigation',
    'tests.test_native_observation072',
    'tests.test_native_offer_coverage104',
    'tests.test_native_offer_witness109',
    'tests.test_native_opened_entry093',
    'tests.test_native_opened_fade100',
    'tests.test_native_partial_entry097',
    'tests.test_native_partial_framing097',
    'tests.test_native_passage072',
    'tests.test_native_perception',
    'tests.test_native_positive114',
    'tests.test_native_recovery',
    'tests.test_native_restart_yield112',
    'tests.test_native_ring094',
    'tests.test_native_ring114',
    'tests.test_native_ring_bank094',
    'tests.test_native_shop_coverage102',
    'tests.test_native_shop_geometry101',
    'tests.test_native_side_shop100',
    'tests.test_native_single_offer108',
    'tests.test_native_single_sign_shop103',
    'tests.test_native_static075',
    'tests.test_native_stop099',
    'tests.test_native_structural_cycle096',
    'tests.test_native_structural_shop096',
    'tests.test_native_upper_adoption111',
    'tests.test_target_assessment087',
)
CURRENT_MAC_CASES = ('current_view', 'current_cancel')
NEW_PATHS = frozenset({
    'necroprobe/campaign_diagnostics114.py',
    'necroprobe/test114.py',
    'test_114.sh',
    'patches/loopctrl/check_runtime114.py',
    'patches/loopctrl/ngg2_runtime114_current_fixture.c',
    'patches/loopctrl/ngg2_runtime114_tests.swift',
    'patches/loopctrl/run_test114_host.py',
    'patches/loopctrl/run_test114_python39.py',
    'patches/loopctrl/test_device_ci114.py',
    'tests/test_campaign_diagnostics114.py',
    'tests/test_native_current_view114.py',
    'tests/test_native_positive114.py',
    'tests/test_native_ring114.py',
})
BASELINE_RUNTIME_SHA256 = 'dc082fd9658df32924c90423c544030d327c744f4224d4d8c868762a6e2e741f'
BASELINE_NAV_SHA256 = 'fd172e5fad6a6809d0b53fe88955f21117c466946a67ee53168510273cdc729a'
PRODUCT_PATHS = ('necroprobe/test114.py', 'test_114.sh', 'necroprobe/campaign_diagnostics114.py')


def reject_fixture_overrides():
    if any(name == 'BASELINE_NAV' or name.startswith('NECRO_TEST')
            or re.match(r'^NECRO[0-9]+_', name) for name in os.environ):
        raise ValueError('TEST114 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not RUNTIME_SCOPE_FINALIZED or not CURRENT_MAC_CASES:
        raise ValueError('TEST114 native/client/current Mac author scopes are pending')
    labels = [row[2] for row in CASES]
    if not CASES or len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST114 empty or duplicate selected scope')
    if not NEW_PATHS or not CLIENT_PRODUCT_CHANGES:
        raise ValueError('TEST114 exact repository source scope is pending')


def native_delta(before, current, allowed=EXPECTED_NATIVE_CHANGES):
    changed = {path for path in current if before.get(path) != current[path]}
    if (set(before) != set(current) or len(current) != 36
            or changed != set(allowed) or not allowed):
        raise ValueError('TEST114 exact 36-source native delta differs')
    return changed


def manifest_sources(manifest):
    return {**{name: row['patched_sha256'] for name, row in manifest['files'].items()},
            **{name: row['sha256'] for name, row in manifest['additions'].items()}}


def runtime_source_identity(before, current):
    if not RUNTIME_SCOPE_FINALIZED or not CURRENT_MAC_CASES:
        raise ValueError('TEST114 current Mac source scope is pending')
    for name, wanted in (('NG2Runtime.swift', BASELINE_RUNTIME_SHA256),
                         ('NG2Navigation.c', BASELINE_NAV_SHA256)):
        key = 'LoopCtrlUITests/'+name
        if before.get(key) != wanted or current.get(key) != wanted:
            raise ValueError('TEST114 retained native source differs: '+name)
    return dict(policy='selected_current_runtime_boundaries_required',
        baseline_runtime_sha256=before['LoopCtrlUITests/NG2Runtime.swift'],
        current_runtime_sha256=current['LoopCtrlUITests/NG2Runtime.swift'],
        current_controller_sha256=current['LoopCtrlUITests/NG2Controller.c'],
        current_ring_sha256=current['LoopCtrlUITests/NG2Ring.c'],
        current_mac_execution_required=True, expected_current_mac_cases=list(CURRENT_MAC_CASES),
        before_runtime_api_assertion_required=False, executed_in_host_selector=False)


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
        raise ValueError('TEST114 installed native sources differ from pinned manifest')
    expected_api = dict(api_version='1.98.16-ngg2', client_capability='necrogold_native_v15',
        cycle_capability='necrogold_native_cycle_v1', cycle_profile='normal-1-1-cycle-v1',
        irregular_capability='necrogold_native_irregular_v1', irregular_profile='normal-1-1-irregular-v1',
        image_price_capability='necrogold_native_image_price_v1', compiler_profile_version=3,
        restart_yield_capability='necrogold_native_restart_yield_v1', restart_yield_start_flag='yield_after_restart')
    if any(manifest.get(key) != value for key, value in expected_api.items()):
        raise ValueError('TEST114 API/capability/profile identity differs')
    baseline_paths = {p.decode() for p in git(driver, 'ls-tree', '-r', '--name-only', '-z', NATIVE_BASELINE).split(b'\0') if p}
    differences = {p.decode() for p in git(driver, 'diff', '--no-renames', '--name-only', '-z', NATIVE_BASELINE, code, '--').split(b'\0') if p}
    existing = {path for path in differences & baseline_paths if not path.startswith('docs/')}
    approved = {'patches/loopctrl/ngg2/NG2Controller.c', 'patches/loopctrl/ngg2/NG2Ring.c',
        manifest_path, '.github/workflows/loopctrl-geometry.yml', *CLIENT_PRODUCT_CHANGES}
    added = {path for path in differences-baseline_paths if not path.startswith('docs/')}
    if existing != approved or added != set(NEW_PATHS):
        raise ValueError('TEST114 exact changed/new repository source paths differ')
    if git(driver, 'diff', '--no-ext-diff', '--name-only', code, '--',
            'tests', 'necroprobe', 'tools/ring_native', 'legacy/r12', 'patches/loopctrl',
            '.github/workflows/loopctrl-geometry.yml', 'test_114.sh').strip():
        raise ValueError('TEST114 working source differs from pinned CODE')
    ring_raw = pinned_bytes(driver, 'necroprobe/ring_native_manifest.json', code)
    if ring_raw != git(driver, 'show', NATIVE_BASELINE+':necroprobe/ring_native_manifest.json'):
        raise ValueError('TEST114 canonical ring manifest changed')
    ring = json.loads(ring_raw)
    if len(ring['sources']) != 15 or sum(path.startswith('legacy/r12/') for path in baseline_paths) != 40:
        raise ValueError('TEST114 canonical/R12 source inventory differs')
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
            raise ValueError('TEST114 fixture import escaped pinned driver: '+name)
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
    (output/'test114-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
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
        raise ValueError('TEST114 public ABI changed')
    output.mkdir(parents=True, exist_ok=True)
    evidence = dict(scope='TEST114 selected device-failure contracts', source_identity=sealed,
        production_source_binding=binding, abi_bytes=abi, device_test='not_run',
        not_run=['historical whole host/Runtime suites', 'iPhone reach rate, rare-target precision and human speed acceptance'])
    for label, cases in suites:
        run_scope(label, cases, output, evidence)
    selector = importlib.import_module('test_device_ci114')
    run_scope('test114-selector', unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection114Tests), output, evidence)
    if verifier.inspect_native_sources(upstream, driver) != sealed or source_identity(driver, sealed) != binding:
        raise ValueError('TEST114 tests changed sealed source')
    reject_fixture_overrides()
    evidence.update(sealed_sources_unchanged_after_tests=True,
        manifest_sha256=sha((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes()))
    (output/'test114-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS TEST114 selected source-bound contracts; Mac execution and phone acceptance remain separate')


if __name__ == '__main__':
    main()
