"""Selected TEST116 contracts over the exact sealed IPA source inventory.

The native/client/Runtime authors must freeze every scope and changed path
before CI can execute.  Historical suites are not implicitly replayed.
"""
import argparse
import ast
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
_spec = importlib.util.spec_from_file_location('test116_source_utils', HERE/'run_test094_host.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
selected_cases, method_cases = shared.selected_cases, shared.method_cases
NATIVE_BASELINE = 'c17ffd2e4c583b16b322dd9e8a973003e179389c'
SCOPE_FINALIZED = True
RUNTIME_SCOPE_FINALIZED = True
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlKit/RPCMethod.swift',
    'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Controller.h',
    'LoopCtrlUITests/NG2CycleSpool.swift', 'LoopCtrlUITests/NG2Navigation.c',
    'LoopCtrlUITests/NG2Runtime.swift'})
EXPECTED_NATIVE_ADDITIONS = frozenset()
EXPECTED_REPOSITORY_CHANGES = frozenset({
    '.github/workflows/loopctrl-geometry.yml',
    'patches/loopctrl/apply_ngg2.py',
    'patches/loopctrl/ngg2-manifest.json',
    'patches/loopctrl/ngg2.patch',
    'patches/loopctrl/ngg2/NG2Controller.c',
    'patches/loopctrl/ngg2/NG2Controller.h',
    'patches/loopctrl/ngg2/NG2CycleSpool.swift',
    'patches/loopctrl/ngg2/NG2Navigation.c',
    'patches/loopctrl/ngg2/NG2Runtime.swift',
})
NEW_PATHS = frozenset({
    'necroprobe/campaign116.py',
    'necroprobe/campaign_forensic116.py',
    'necroprobe/test116.py',
    'patches/loopctrl/check_cycle_spool116.py',
    'patches/loopctrl/check_crossbind116.py',
    'patches/loopctrl/check_runtime116.py',
    'patches/loopctrl/ngg2_cycle_spool116_before_adapter.swift',
    'patches/loopctrl/ngg2_cycle_spool116_tests.swift',
    'patches/loopctrl/ngg2_runtime116_admission.swift',
    'patches/loopctrl/ngg2_runtime116_tests.swift',
    'patches/loopctrl/run_test116_host.py',
    'patches/loopctrl/run_test116_python39.py',
    'patches/loopctrl/test116-spool-proof.json',
    'patches/loopctrl/test_device_ci116.py',
    'test_116.sh',
    'tests/test_continuous_client116.py',
    'tests/test_forensic_orphan116.py',
    'tests/test_native_continuous116.py',
    'tests/test_native_continuous_shop116.py',
    'tests/test_native_early_full116.py',
    'tests/test_native_navigation116.py',
    'tests/test_native_partial116.py',
})
CLIENT_PRODUCT_CHANGES = frozenset({'necroprobe/campaign116.py', 'necroprobe/campaign_forensic116.py'})
CURRENT_MAC_CASES = (
    'new_mode',
    'normal_chain',
    'history_mode',
    'nil_core',
    'candidate',
    'late_hint',
    'cancel_before_swap',
    'cancel_after_swap',
    'bootstrap_cancel',
    'bootstrap_deadline',
    'qualified_cancel',
    'successor_owner',
    'successor_locked',
    'successor_foreground',
    'main_return',
    'heartbeat',
    'root_clock_before',
    'root_clock_equal',
    'root_clock_late',
    'root_clock_ticket_before',
    'producer',
    'classification_commit',
    'capture_decode',
    'capture_control',
    'capture_thread_return',
    'seal_producer',
    'seal_commit',
    'writer:checkpoint',
    'commit:checkpoint',
    'writer:intent',
    'commit:intent',
    'writer:outcome',
    'commit:outcome',
    'writer:terminal',
    'commit:terminal',
    'post_begin_clock',
)
RUNTIME_CASE_GROUPS = (('check_runtime116.py', CURRENT_MAC_CASES),)
SPOOL_PROOF_PATH = 'patches/loopctrl/test116-spool-proof.json'
SPOOL_INPUT_PATHS = ('patches/loopctrl/ngg2/NG2CycleSpool.swift',
    'patches/loopctrl/check_cycle_spool116.py', 'patches/loopctrl/ngg2_cycle_spool116_tests.swift',
    'patches/loopctrl/ngg2_cycle_spool116_before_adapter.swift')
CASES = (
    ('tests.test_native_navigation116', 'NativeCappedNeck116Tests', 'test116-native-NativeCappedNeck116Tests', frozenset({
        'test_both_observed_neck_cells_and_reachable_inboard_are_required',
        'test_cap_and_both_lateral_wall_segments_are_independent_required_evidence',
        'test_capped_observed_necks_keep_the_existing_world_bits_in_both_axes',
        'test_neck_refuses_goods_other_screens_and_observed_nonfloor_flanks',
        'test_outer_corner_cannot_replace_three_independent_room_boundary_walls',
        'test_unchanged_chooser_walks_only_known_floor_and_stops_at_the_outside',
    }), True),
    ('tests.test_native_passage_navigation072', 'NativePassageNavigation072Tests', 'test116-native-NativePassageNavigation072Tests', frozenset({
        'test_candidate_bits_cover_annotated_families_and_multiple_mouths',
        'test_chooser_rejects_unsafe_steps_invalid_world_targets_and_unreachable_floor',
        'test_fixed_second_mouth_remains_reachable_across_the_initial_room',
        'test_fixed_world_mouth_reaches_one_outside_with_real_floor_steps',
        'test_invalid_start_gold_goods_ordinary_exits_and_protection_do_not_explore',
        'test_shadowed_mouth_requires_outside_floor_and_wall_line_support',
        'test_shop_chooser_stays_separate_and_null_outputs_fail_closed',
        'test_unknown_outside_uses_a_monotone_observed_vantage_then_new_view',
    }), True),
    ('tests.test_native_passage115', 'NativePassageFringe115Tests', 'test116-native-NativePassageFringe115Tests', frozenset({
        'test_fringe_needs_full_observed_support_and_positive_inside_floor',
        'test_fringe_rejects_nonclear_goods_protection_and_no_floor_vantage',
        'test_observed_floor_fringe_adds_only_upper_left_dark_mouth',
    }), True),
    ('tests.test_native_partial116', 'NativePartial116Tests', 'test116-native-NativePartial116Tests', frozenset({
        'test_issued_but_unbegun_credit_is_retired_without_refunding_an_input',
        'test_reverse_top_projection_keeps_fixed_epoch_and_original_one_up',
        'test_reverse_top_relation_rejects_unexplained_goods_floor_gold_and_motion',
        'test_top_transition_after_unused_credit_starts_independent_data',
    }), True),
    ('tests.test_native_early_full116', 'NativeEarlyFull116Tests', 'test116-native-NativeEarlyFull116Tests', frozenset({
        'test_late_unit_new_normal_data_two_zeros_one_observation_then_real_negative_restart',
        'test_missing_original_unit_wrong_prefix_and_expired_bounds_never_add_credit',
        'test_normal_positive_remains_latched_ahead_of_late_unit_refresh',
        'test_original_up_ack_late_unit_is_credited_once_and_starts_only_fresh_data',
    }), True),
    ('tests.test_native_shop115', 'NativeShop115Tests', 'test116-native-NativeShop115Tests', frozenset({
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
    ('tests.test_native_current_view114', 'NativeCurrentView114Tests', 'test116-native-NativeCurrentView114Tests', frozenset({
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
    ('tests.test_native_goods113', 'NativeGoodsUpView113Tests', 'test116-native-NativeGoodsUpView113Tests', frozenset({
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
    ('tests.test_native_cycle094', 'NativeCycle094Tests', 'test116-native-NativeCycle094Tests', frozenset({
        'test_inflight_goods_credit_real_move_once_and_keep_unknown_motion_held',
    }), False),
    ('tests.test_native_continuous116', 'NativeContinuous116Tests', 'test116-native-NativeContinuous116Tests', frozenset({
        'test116_finish_requires_exact_source_permit_and_original_parent',
        'test116_normal_negative_restart_finishes_without_pause_or_budget_reset',
        'test116_root_deadline_cannot_be_extended_or_issue_at_equality',
        'test116_root_requires_pause_and_trusted_child_requires_fresh_floor',
        'test116_successor_unknown_waits_within_original_transition_then_needs_own_floor',
        'test116_unprocessed_or_positive_new_floor_cannot_finish',
    }), True),
    ('tests.test_native_continuous_shop116', 'NativeContinuousPartial116Tests', 'test116-native-NativeContinuousPartial116Tests', frozenset({
        'test_issued_but_unbegun_credit_is_retired_without_refunding_an_input',
        'test_reverse_top_projection_keeps_fixed_epoch_and_original_one_up',
        'test_reverse_top_relation_rejects_unexplained_goods_floor_gold_and_motion',
        'test_top_transition_after_unused_credit_starts_independent_data',
    }), True),
    ('tests.test_native_continuous_shop116', 'NativeContinuousEarlyFull116Tests', 'test116-native-NativeContinuousEarlyFull116Tests', frozenset({
        'test_late_unit_new_normal_data_two_zeros_one_observation_then_real_negative_restart',
        'test_missing_original_unit_wrong_prefix_and_expired_bounds_never_add_credit',
        'test_normal_positive_remains_latched_ahead_of_late_unit_refresh',
        'test_original_up_ack_late_unit_is_credited_once_and_starts_only_fresh_data',
    }), True),
    ('tests.test_native_restart_yield112', 'NativeRestartYield112Tests', 'test116-native-NativeRestartYield112Tests', frozenset({
        'test_death_retires_budget_into_existing_irregular_owner_after_worker_settles',
        'test_durable_first_newfloor_survives_unknown_tail_without_rewinding_ui',
        'test_enable_is_immutable_and_old_walking_restart_still_continues',
        'test_first_goods_is_data_only_and_partial_then_full_each_requires_positive_veto',
        'test_full_then_partial_sources_are_serial_once_and_pause_has_no_restart',
        'test_irregular_ui_companion_vetoes_floor_permit_and_pause_confirmation',
        'test_late_worker_hint_survives_frozen_data_timeout_without_handoff',
        'test_later_floor_observation_revokes_permit_without_renewing_parent',
        'test_old_negative_or_uncommitted_restart_is_not_a_yield_basis',
        'test_optin_after_durable_restart_never_enters_another_level_with_spent_budget',
        'test_optin_initial_floor_or_other_ui_is_input_free_but_old_start_is_unchanged',
        'test_original_budgets_cancellation_and_started_or_unknown_pause_cannot_mint_handoff',
        'test_positive_invalid_yield_cleanup_pause_ack_is_observed_without_handoff_or_resend',
        'test_retained_goods_cannot_replace_current_ui_scene_or_expired_prefix_source',
        'test_source_bound_permit_requires_live_current_floor_and_real_pause_confirmation',
        'test_stale_first_pause_or_invalid_pause_companion_never_opens_floor_start',
        'test_target_candidate_late_hint_and_malformed_results_never_allow_next_start',
    }), True),
)
CORE_MODULES = (
    'tests.test_beat_sync',
    'tests.test_native_beat',
    'tests.test_native_blocked067',
    'tests.test_native_bottom_shop103',
    'tests.test_native_classification111',
    'tests.test_native_clear_stationary095',
    'tests.test_native_continuous116',
    'tests.test_native_controller',
    'tests.test_native_current_view114',
    'tests.test_native_cycle094',
    'tests.test_native_cycle_binary095',
    'tests.test_native_early_full116',
    'tests.test_native_entry_corridor102',
    'tests.test_native_entry_episode102',
    'tests.test_native_full_framing101',
    'tests.test_native_goods113',
    'tests.test_native_handoff099',
    'tests.test_native_irregular110',
    'tests.test_native_motion067',
    'tests.test_native_motion075',
    'tests.test_native_navigation',
    'tests.test_native_navigation116',
    'tests.test_native_observation072',
    'tests.test_native_offer_coverage104',
    'tests.test_native_opened_entry093',
    'tests.test_native_opened_fade100',
    'tests.test_native_partial116',
    'tests.test_native_partial_entry097',
    'tests.test_native_partial_framing097',
    'tests.test_native_passage072',
    'tests.test_native_passage115',
    'tests.test_native_passage_navigation072',
    'tests.test_native_passage_unsent076',
    'tests.test_native_perception',
    'tests.test_native_plural_stationary103',
    'tests.test_native_plural_wait103',
    'tests.test_native_recovery',
    'tests.test_native_restart_yield112',
    'tests.test_native_ring094',
    'tests.test_native_ring_bank094',
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
    'tests.test_native_upper_entry112',
    'tests.test_target_assessment087',
)
PRODUCT_PATHS = ('necroprobe/test116.py', 'test_116.sh', 'necroprobe/native_cycle.py',
    'necroprobe/protocol.py', 'necroprobe/validation.py')
EXPECTED_API = dict(api_version='1.98.16-ngg2', client_capability='necrogold_native_v15',
    cycle_capability='necrogold_native_cycle_v1', cycle_profile='normal-1-1-cycle-v1',
    irregular_capability='necrogold_native_irregular_v1', irregular_profile='normal-1-1-irregular-v1',
    image_price_capability='necrogold_native_image_price_v1', compiler_profile_version=3,
    restart_yield_capability='necrogold_native_restart_yield_v1', restart_yield_start_flag='yield_after_restart',
    continuous_campaign_capability='necrogold_native_continuous_campaign_v1',
    continuous_campaign_start_flag='continuous_campaign')


def reject_fixture_overrides():
    if any(name == 'BASELINE_NAV' or name.startswith('NECRO_TEST')
            or re.match(r'^NECRO[0-9]+_', name) for name in os.environ):
        raise ValueError('TEST116 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not RUNTIME_SCOPE_FINALIZED:
        raise ValueError('TEST116 author scopes are pending; no tests may execute')
    if not CASES or not NEW_PATHS or not EXPECTED_NATIVE_CHANGES or not EXPECTED_REPOSITORY_CHANGES:
        raise ValueError('TEST116 source/method inventory is empty')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST116 empty or duplicate selected native scope')
    if not CURRENT_MAC_CASES or len(CURRENT_MAC_CASES) != len(set(CURRENT_MAC_CASES)) or not RUNTIME_CASE_GROUPS:
        raise ValueError('TEST116 current Runtime inventory is empty or duplicated')
    grouped = tuple(case for _checker, cases in RUNTIME_CASE_GROUPS for case in cases)
    if grouped != CURRENT_MAC_CASES:
        raise ValueError('TEST116 Runtime groups differ from exact current cases')


def manifest_sources(manifest):
    return {**{name: row['patched_sha256'] for name, row in manifest['files'].items()},
            **{name: row['sha256'] for name, row in manifest['additions'].items()}}


def native_delta(before, current):
    added = set(current)-set(before)
    changed = {path for path in set(before)&set(current) if before[path] != current[path]}
    if (len(before) != 36 or set(before)-set(current)
            or len(current) != 36+len(EXPECTED_NATIVE_ADDITIONS)
            or added != set(EXPECTED_NATIVE_ADDITIONS) or changed != set(EXPECTED_NATIVE_CHANGES)
            or not changed):
        raise ValueError('TEST116 exact native changed/added inventory differs')
    return changed, added


def validate_spool_reuse(proof, inputs, *, baseline_sha, green_cases, red_cases):
    required = {'schema', 'run_id', 'run_number', 'driver_commit', 'artifact_name',
        'artifact_sha256', 'source_inputs', 'before', 'current'}
    if (type(proof) is not dict or set(proof) != required or
            proof['schema'] != 'test116-spool-reuse-v1' or
            type(proof['run_id']) is not int or proof['run_id'] <= 0 or
            type(proof['run_number']) is not int or proof['run_number'] <= 0 or
            not isinstance(proof['driver_commit'], str) or not re.fullmatch('[0-9a-f]{40}', proof['driver_commit']) or
            proof['artifact_name'] != 'loopctrl-test116-spool-green' or
            not isinstance(proof['artifact_sha256'], str) or not re.fullmatch('[0-9a-f]{64}', proof['artifact_sha256']) or
            proof['source_inputs'] != inputs or set(inputs) != set(SPOOL_INPUT_PATHS)):
        raise ValueError('TEST116 reused Spool artifact/source binding differs')
    for key, baseline in (('before', True), ('current', False)):
        value = proof[key]
        cases = tuple(red_cases) if baseline else tuple(green_cases)
        if (type(value) is not dict or value.get('schema') != 'test116-spool-evidence-v1' or
                value.get('baseline_only') is not baseline or value.get('baseline_adapter_is_test_only') is not True or
                value.get('green_cases') != list(green_cases) or
                value.get('source_sha256') != (baseline_sha if baseline else inputs[SPOOL_INPUT_PATHS[0]]) or
                value.get('fixture_sha256') != inputs[SPOOL_INPUT_PATHS[2]] or
                value.get('adapter_sha256') != inputs[SPOOL_INPUT_PATHS[3]] or
                not isinstance(value.get('compiler'), str) or 'Apple Swift version ' not in value['compiler'] or
                value.get('device_acceptance') is not False or value.get('input_authority') is not False or
                type(value.get('results')) is not dict or set(value['results']) != set(cases)):
            raise ValueError('TEST116 reused Spool actual compiler/case inventory differs: '+key)
        for case, result in value['results'].items():
            if (type(result) is not dict or set(result) != {'returncode', 'compile_errors', 'failures'} or
                    type(result['returncode']) is not int or type(result['compile_errors']) is not int or
                    result['compile_errors'] != 0 or result['returncode'] != (1 if baseline else 0) or
                    result['failures'] != ([red_cases[case]] if baseline else [])):
                raise ValueError('TEST116 reused Spool case was not the exact assertion result: '+case)
    if proof['before']['compiler'] != proof['current']['compiler']:
        raise ValueError('TEST116 before/current Spool compiler identity differs')
    return dict(run_id=proof['run_id'], run_number=proof['run_number'], driver_commit=proof['driver_commit'],
        artifact_name=proof['artifact_name'], artifact_sha256=proof['artifact_sha256'], source_inputs=inputs,
        assertion_red_cases=list(red_cases), green_cases=list(green_cases), same_bytes_reused=True,
        compiler=proof['current']['compiler'], device_acceptance=False, input_authority=False)


def reused_spool_proof(driver, upstream, code=None):
    code = code or git(driver, 'rev-parse', 'HEAD').decode().strip()
    proof_raw = pinned_bytes(driver, SPOOL_PROOF_PATH, code)
    inputs = {name: sha(pinned_bytes(driver, name, code)) for name in SPOOL_INPUT_PATHS}
    if inputs[SPOOL_INPUT_PATHS[0]] != sha((upstream/'LoopCtrlUITests/NG2CycleSpool.swift').read_bytes()):
        raise ValueError('TEST116 reused Spool source differs from actual installed IPA source')
    tree = ast.parse(pinned_bytes(driver, SPOOL_INPUT_PATHS[1], code))
    constants = {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in {'BASELINE_SHA', 'GREEN_CASES', 'EXPECTED_RED'}}
    result = validate_spool_reuse(json.loads(proof_raw), inputs, baseline_sha=constants['BASELINE_SHA'],
        green_cases=constants['GREEN_CASES'], red_cases=constants['EXPECTED_RED'])
    return dict(result, proof_sha256=sha(proof_raw))


def source_identity(driver, sealed, upstream):
    ensure_scope()
    reject_fixture_overrides()
    code = git(driver, 'rev-parse', 'HEAD').decode().strip()
    manifest_path = 'patches/loopctrl/ngg2-manifest.json'
    manifest_raw = pinned_bytes(driver, manifest_path, code)
    manifest = json.loads(manifest_raw)
    old = manifest_sources(json.loads(git(driver, 'show', NATIVE_BASELINE+':'+manifest_path)))
    current = sealed['native_source_sha256']
    changed, added = native_delta(old, current)
    if manifest_sources(manifest) != current:
        raise ValueError('TEST116 installed native source differs from pinned manifest')
    if any(manifest.get(key) != value for key, value in EXPECTED_API.items()):
        raise ValueError('TEST116 API/capability/profile identity differs')
    baseline = {p.decode() for p in git(driver, 'ls-tree', '-r', '--name-only', '-z', NATIVE_BASELINE).split(b'\0') if p}
    differences = {p.decode() for p in git(driver, 'diff', '--no-renames', '--name-only', '-z', NATIVE_BASELINE, code, '--').split(b'\0') if p}
    existing = {path for path in differences&baseline if not path.startswith('docs/')}
    new = {path for path in differences-baseline if not path.startswith('docs/')}
    if existing != set(EXPECTED_REPOSITORY_CHANGES) or new != set(NEW_PATHS):
        raise ValueError('TEST116 exact repository changed/new source paths differ')
    if git(driver, 'diff', '--no-ext-diff', '--name-only', code, '--', 'tests', 'necroprobe',
            'tools/ring_native', 'legacy/r12', 'patches/loopctrl',
            '.github/workflows/loopctrl-geometry.yml', 'test_116.sh').strip():
        raise ValueError('TEST116 working source differs from pinned CODE')
    ring_raw = pinned_bytes(driver, 'necroprobe/ring_native_manifest.json', code)
    if ring_raw != git(driver, 'show', NATIVE_BASELINE+':necroprobe/ring_native_manifest.json'):
        raise ValueError('TEST116 canonical Ring manifest changed')
    ring = json.loads(ring_raw)
    r12 = sorted(path for path in baseline if path.startswith('legacy/r12/'))
    if len(ring['sources']) != 15 or len(r12) != 40:
        raise ValueError('TEST116 canonical/R12 source inventory differs')
    canonical = {}
    for path in (*ring['sources'], *r12):
        raw = pinned_bytes(driver, path, code)
        if raw != git(driver, 'show', NATIVE_BASELINE+':'+path):
            raise ValueError('TEST116 preserved canonical/R12 source changed: '+path)
        canonical[path] = sha(raw)
    fixtures = {name.replace('.', '/')+'.py' for name in (*CORE_MODULES, *(row[0] for row in CASES))}
    fixtures.update(path for path in NEW_PATHS if path.startswith(('tests/', 'patches/loopctrl/')))
    fixtures.add('patches/loopctrl/run_test094_host.py')
    products = {path: sha(pinned_bytes(driver, path, code))
        for path in dict.fromkeys((*PRODUCT_PATHS, *sorted(CLIENT_PRODUCT_CHANGES)))}
    return dict(driver_commit=code, native_baseline=NATIVE_BASELINE,
        changed_native_sources=sorted(changed), native_added=sorted(added),
        preserved_native_source_sha256={name: value for name, value in current.items() if name not in changed|added},
        fixture_source_sha256={path: sha(pinned_bytes(driver, path, code)) for path in sorted(fixtures)},
        product_sha256=products, changed_repository_paths=sorted(existing), new_repository_paths=sorted(new),
        canonical_source_sha256=canonical, native_manifest_sha256=sha(manifest_raw),
        reused_spool_evidence=reused_spool_proof(driver, upstream, code),
        current_mac_execution_required=True, expected_current_mac_cases=list(CURRENT_MAC_CASES),
        limitation='Selected software and actual Mac checks do not establish iPhone reach rate or speed.')


def native_suites(upstream, driver):
    reject_fixture_overrides()
    names = tuple(dict.fromkeys((*CORE_MODULES, *(row[0] for row in CASES))))
    modules = {name: importlib.import_module(name) for name in names}
    for name, module in modules.items():
        if Path(module.__file__).resolve() != driver/(name.replace('.', '/')+'.py'):
            raise ValueError('TEST116 fixture import escaped pinned driver: '+name)
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
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        expected_failures=len(result.expectedFailures))
    (output/'test116-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': selected methods must all execute Green')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('driver', 'upstream', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    ensure_scope()
    driver, upstream, output = (getattr(args, name).resolve() for name in ('driver', 'upstream', 'output'))
    sys.path[:0] = [str(driver), str(driver/'tests'), str(HERE)]
    verifier = importlib.import_module('verify_package')
    sealed = verifier.inspect_native_sources(upstream, driver)
    binding = source_identity(driver, sealed, upstream)
    suites = native_suites(upstream, driver)
    selected_cases(case for _label, cases in suites for case in cases)
    native = importlib.import_module('tests.test_native_controller')
    cycle = importlib.import_module('tests.test_native_cycle094')
    abi = {name: ctypes.sizeof(getattr(native, name)) for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    abi['Cycle'] = ctypes.sizeof(cycle.Cycle)
    if abi != dict(Scene=23864, Status=192, Event=128, MotionWait=48, RecoveryStatus=456, Cycle=216):
        raise ValueError('TEST116 existing public POD ABI changed')
    output.mkdir(parents=True, exist_ok=True)
    evidence = dict(scope='TEST116 selected device and continuation contracts', source_identity=sealed,
        production_source_binding=binding, abi_bytes=abi, device_test='not_run',
        not_run=['historical whole host/Runtime suites', 'iPhone reach rate, rare target precision and speed acceptance'])
    for label, cases in suites:
        run_scope(label, cases, output, evidence)
    selector = importlib.import_module('test_device_ci116')
    run_scope('test116-selector', unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection116Tests), output, evidence)
    if verifier.inspect_native_sources(upstream, driver) != sealed or source_identity(driver, sealed, upstream) != binding:
        raise ValueError('TEST116 tests changed sealed source')
    reject_fixture_overrides()
    evidence['sealed_sources_unchanged_after_tests'] = True
    (output/'test116-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS TEST116 selected source-bound contracts; iPhone acceptance is separate')


if __name__ == '__main__':
    main()
