"""TEST122 exact source and boundary selection; pending scopes fail closed."""
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
_spec = importlib.util.spec_from_file_location('test122_shared117', HERE/'run_test117_host.py')
shared = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
selected_cases, method_cases, manifest_sources = shared.selected_cases, shared.method_cases, shared.manifest_sources
NATIVE_BASELINE = 'd78159a9d535178df8282d69f182b2ae544facf0'
SCOPE_FINALIZED = True
MAC_SCOPE_FINALIZED = True
# Final author source/method inventories verified against the root sealed37-source inventory.
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlKit/RPCMethod.swift',
    'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Navigation.c',
    'LoopCtrlUITests/NG2Ring.c', 'LoopCtrlUITests/NG2Ring.h'})
EXPECTED_NATIVE_ADDITIONS = frozenset()
EXPECTED_REPOSITORY_CHANGES = frozenset((
    '.github/workflows/loopctrl-geometry.yml',
    'necroprobe/campaign116.py',
    'patches/loopctrl/apply_ngg2.py',
    'patches/loopctrl/ngg2-manifest.json',
    'patches/loopctrl/ngg2.patch',
    'patches/loopctrl/ngg2/NG2Controller.c',
    'patches/loopctrl/ngg2/NG2Navigation.c',
    'patches/loopctrl/ngg2/NG2Ring.c',
    'patches/loopctrl/ngg2/NG2Ring.h',
    'patches/loopctrl/verify_package.py',
    'tests/test_continuous_client117.py',
    'tests/test_continuous_client118.py',
    'tests/test_continuous_client119.py',
    'tests/test_continuous_client120.py',
    'tests/test_continuous_client121.py',
))
# All new fixture and client paths are explicit before source pinning.
NEW_PATHS = frozenset((
    'necroprobe/test122.py',
    'patches/loopctrl/run_test122_host.py',
    'patches/loopctrl/run_test122_python39.py',
    'patches/loopctrl/test_device_ci122.py',
    'test_122.sh',
    'tests/test_continuous_client122.py',
    'tests/test_native_full_halo_data122.py',
    'tests/test_native_price_independent_goods122.py',
    'tests/test_native_singleton_dependency122.py',
    'tests/test_native_upper_material122.py',
))
# Explicit authored methods and directly related regressions, not whole old suites.
CASES = (
    ('tests.test_native_upper_material122', 'NativeUpperMaterial122Tests', 'test122-native-NativeUpperMaterial122Tests', frozenset({
        'test_after_first_unit_material_keeps_the_old_postunit_bridge',
        'test_before_first_unit_stone_material_keeps_the_same_static_job',
        'test_begin_reuses_only_the_current_normal_zero_and_keeps_same_command',
        'test_changed_current_and_discarded_capture_cannot_borrow_the_old_fact',
        'test_consumed_not_sent_or_unknown_command_never_rearms_the_fact',
        'test_material_does_not_rearm_an_existing_geometry_rebound',
        'test_original_parent_and_commit_clock_still_bound_material_observation',
        'test_same_job_material_can_frame_all_five_steps_without_new_data_or_parent',
        'test_step_cross_special_tiles_masks_and_unproved_motion_never_gain_input',
    }), True),
    ('tests.test_native_full_halo_data122', 'NativeFullHaloData122Tests', 'test122-native-NativeFullHaloData122Tests', frozenset({
        'test_exact_halo_exposure_queues_mode2_then_normal_negative_durable_restart',
        'test_item_mask_gold_door_and_walking_cross_cannot_borrow_halo_admission',
        'test_legacy_published_framing_move_started_or_ack_never_becomes_new_data',
        'test_new_normal_target_wins_without_move_or_restart',
        'test_new_unknown_is_held_and_cannot_remint_current_data_or_observation_move',
        'test_original_parent_and_actual_commit_are_not_extended',
        'test_two_halo_changes_reverse_and_other_materials_do_not_gain_data',
        'test_unknown_motion_feature_off_candidate_and_invalid_metadata_do_not_gain_data',
    }), True),
    ('tests.test_native_singleton_dependency122', 'SingletonDependency122Tests', 'test122-native-SingletonDependency122Tests', frozenset({
        'test_independent_signed_planes_require_their_own_quality',
        'test_missing_axis_support_and_band_cannot_be_replaced_by_dependency',
        'test_one_unavailable_dependency_alternative_remains_unknown',
        'test_public_motion_proves_unit_with_only_remote_blocker_losses',
        'test_raw_nonunit_wrong_direction_and_known_results_remain_unchanged',
        'test_supported_axis_competitor_requires_its_own_lead',
        'test_unique_old_world_and_safe_remote_loss_are_required',
    }), True),
    ('tests.test_native_singleton_dependency122', 'SingletonAck122Tests', 'test122-native-SingletonAck122Tests', frozenset({
        'test_capture_and_actual_commit_respect_visual_before_equal_and_after',
        'test_eighth_qualified_unit_credits_once_after_seven_unknowns_and_old_schedule',
        'test_missing_ack_wrong_prefix_and_unknown_synth_never_credit_or_resend',
    }), True),
    ('tests.test_native_price_independent_goods122', 'NativePriceIndependentGoods122Tests', 'test122-native-NativePriceIndependentGoods122Tests', frozenset({
        'test_every_cell_and_original_partial_keeps_image_and_word_candidate_priority',
        'test_normal_price_free_producer_reaches_durable_public_restart',
        'test_numeric_price_free_tag_and_own_anchor_reject_forged_fields',
        'test_price_independent_full_strip_requires_real_goods_auth_and_observation',
    }), True),
    ('tests.test_native_goods_coverage121', 'NativeGoodsCoverage121Tests', 'test122-related-NativeGoodsCoverage121Tests', frozenset({
        'test_complete_single_shop_uses_relative_glyph_without_a_merchant_identity',
        'test_every_numeric_alias_keeps_five_cell_target_candidate_priority',
        'test_group_ownership_and_diagonal_floor_cannot_discard_other_boards_or_support',
        'test_new_numeric_tags_caps_and_auth_fields_are_independently_rechecked',
        'test_normal_new_producer_reaches_public_C_durable_restart_and_next_floor',
        'test_relative_glyph_needs_complete_ink_sign_support_and_exact_offer_scene',
        'test_three_owned_components_and_one_diagonal_floor_prove_complete_grouped_offer',
    }), False),
    ('tests.test_native_upper118', 'NativeUpper118Tests', 'test122-related-NativeUpper118Tests', frozenset({
        'test_changed_protection_or_unknown_next_floor_cannot_fund_move',
        'test_first_v2_snapshot_may_finish_after_data_return_if_born_after_source',
        'test_row4_admission_allocates_one_period_once_and_funds_fifth_step',
        'test_row4_one_sign_route_keeps_parent_through_all_four_safe_steps',
    }), False),
    ('tests.test_native_upper_snapshot118', 'NativeUpperSnapshot118Tests', 'test122-related-NativeUpperSnapshot118Tests', frozenset({
        'test_same_job_result_and_bridge_rebind_do_not_rearm_early_qualification',
    }), False),
    ('tests.test_native_upper_begin118', 'NativeUpperBegin118Tests', 'test122-related-NativeUpperBegin118Tests', frozenset({
        'test_V1_retains_its_normal_begin_motion_call',
        'test_changed_floor_protection_or_old_gold_never_borrows_cached_zero',
        'test_exact_V2_pair_reuses_normal_zero_at_begin_with_newer_current',
        'test_owner_cancel_and_original_deadline_still_revoke_begin',
    }), False),
    ('tests.test_native_upper_postunit118', 'NativeUpperPostunit118Tests', 'test122-related-NativeUpperPostunit118Tests', frozenset({
        'test_each_postunit_shape_preserves_the_unissued_next_beat_with_observed_need',
    }), False),
    ('tests.test_native_upper_last_slot118', 'NativeUpperLastSlot118Tests', 'test122-related-NativeUpperLastSlot118Tests', frozenset({
        'test_last_full_D3_uses_only_the_unissued_next_beat_before_original_parent',
        'test_published_not_sent_or_unknown_D3_cannot_create_another_input',
    }), False),
    ('tests.test_native_shop117', 'NativeFullCurrentData117Tests', 'test122-related-NativeFullCurrentData117Tests', frozenset({
        'test_changed_goods_masks_player_neighborhood_walls_and_old_candidates_veto_data',
        'test_finite_latest_full_data_accepts_normal_negative_in_both_callback_orders',
        'test_new_current_epoch_invalidates_negative_but_keeps_bound_positive_priority',
        'test_parent_equality_or_stale_latest_cannot_start_a_new_data_epoch',
        'test_prepared_pause_is_retired_only_while_definitely_unbegun',
    }), False),
    ('tests.test_native_entered_current119', 'NativeEnteredCurrent119Tests', 'test122-related-NativeEnteredCurrent119Tests', frozenset({
        'test_data_two_budget_cannot_be_replenished_by_new_remote_material',
        'test_no_unit_floor_or_identity_shortcut',
        'test_original_unit_without_revealed_halo_binds_current_data_once',
        'test_pending_candidate_and_target_win_before_queued_source',
    }), False),
    ('tests.test_native_revealed_domain113', 'RevealedDomain113Tests', 'test122-related-RevealedDomain113Tests', frozenset({
        'test_complete_domain2_dependency_and_known_axis_prove_one_past_unit',
        'test_dependency_plane_cannot_replace_missing_known_axis_support',
        'test_one_unavailable_wider_alternative_rejects_despite_two_strong_winners',
        'test_raw_wrong_direction_nonunit_and_old_known_results_are_not_overridden',
    }), False),
    ('tests.test_native_revealed_motion108', 'RevealedMotion108Tests', 'test122-related-RevealedMotion108Tests', frozenset({
        'test_cached_dependency_mask_matches_the_full_domain_without_overrun',
        'test_texture_quality_and_bands_reject_with_every_phase_still_qualified',
        'test_world_mask_closes_all_dependencies_outside_ui',
    }), False),
    ('tests.test_native_revealed_ack113', 'NativeRevealedAck113Tests', 'test122-related-NativeRevealedAck113Tests', frozenset({
        'test_expired_visual_or_unknown_synth_never_acquires_movement_or_resends',
        'test_only_real_current_prefix_ack_gains_the_observed_unit_with_original_visual_deadline',
    }), False),
    ('tests.test_native_cycle094', 'NativeCycle094Tests', 'test122-related-NativeCycle094Tests', frozenset({
        'test_deadline_and_cancelled_worker_results_are_inert',
        'test_negative_authority_needs_durable_checkpoint_and_new_pause_source',
        'test_target_candidate_and_unknown_keep_pause_without_restart',
    }), False),
    ('tests.test_native_revealed_singleton096', 'NativeRevealedSingleton096Tests', 'test122-related-NativeRevealedSingleton096Tests', frozenset({
        'test_existing_nonunknown_motion_is_untouched_and_inputs_are_immutable',
        'test_nine_matched_old_dirt_and_noncollinear_old_gold_stone_support_are_required',
        'test_old_single_gold_closed_bracket_and_only_unknown_new_leaf_are_required',
    }), False),
    ('patches.loopctrl.test_device_ci122', 'DeviceImplementationCapability122Tests', 'test122-capability', frozenset({
        'test_122_cannot_bypass_the_existing_121_package_binding',
        'test_current_patch_adds_122_without_replacing_118_119_120_or_121',
        'test_historical_121_manifest_gets_no_unrequested_122_field',
        'test_package_has_separate_122_field_and_unchanged_prior_API_and_profile',
        'test_resealed_mismatched_122_metadata_patch_or_rpc_is_rejected',
        'test_sealing_requires_one_real_uncommented_122_array_entry',
    }), True),
    ('patches.loopctrl.test_apply_ngg2', 'NGG2ApplyTests', 'test122-package-related', frozenset({
        'test_changed_and_new_source_install_together',
        'test_native_cycle_requires_strict_ring_profile_three_without_changing_legacy_cap',
        'test_native_v14_package_requires_actual_api16_and_strict_profile_v2',
        'test_native_v15_evidence_package_keeps_api16_and_strict_profile_v2',
        'test_package_provenance_rejects_changed_native_source',
        'test_package_provenance_rejects_even_resealed_stale_runtime_envelope_api',
        'test_seal_pins_each_canonical_shared_source_without_repository_copies',
        'test_seal_still_rejects_empty_native_assets_despite_shared_kernel',
    }), False),
)
# Import/source binding only; execute only the explicit CASES.
CORE_MODULES = (
    'tests.test_beat_sync',
    'tests.test_native_beat',
    'tests.test_native_blocked067',
    'tests.test_native_bottom_shop103',
    'tests.test_native_classification111',
    'tests.test_native_closed_offer105',
    'tests.test_native_closed_price106',
    'tests.test_native_controller',
    'tests.test_native_current_view114',
    'tests.test_native_cycle094',
    'tests.test_native_cycle_binary095',
    'tests.test_native_entered112',
    'tests.test_native_entered_current119',
    'tests.test_native_entry_corridor102',
    'tests.test_native_entry_episode102',
    'tests.test_native_full_framing101',
    'tests.test_native_full_halo_data122',
    'tests.test_native_goods113',
    'tests.test_native_goods_coverage121',
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
    'tests.test_native_partial_refresh104',
    'tests.test_native_perception',
    'tests.test_native_price_independent_goods122',
    'tests.test_native_recovery',
    'tests.test_native_revealed_ack113',
    'tests.test_native_revealed_domain113',
    'tests.test_native_revealed_motion108',
    'tests.test_native_revealed_singleton096',
    'tests.test_native_ring094',
    'tests.test_native_ring117',
    'tests.test_native_ring_bank094',
    'tests.test_native_shop117',
    'tests.test_native_shop_coverage102',
    'tests.test_native_shop_geometry101',
    'tests.test_native_side_gate081',
    'tests.test_native_side_shop100',
    'tests.test_native_single_offer108',
    'tests.test_native_single_sign_shop103',
    'tests.test_native_singleton_dependency122',
    'tests.test_native_static075',
    'tests.test_native_structural_cycle096',
    'tests.test_native_structural_shop096',
    'tests.test_native_upper118',
    'tests.test_native_upper_begin118',
    'tests.test_native_upper_entry112',
    'tests.test_native_upper_last_slot118',
    'tests.test_native_upper_material122',
    'tests.test_native_upper_postunit118',
    'tests.test_native_upper_snapshot118',
    'tests.test_target_assessment087',
)
# TEST120 recorded the unchanged pre117 SCREEN assertion failing on119/120.
# Keep that historical exclusion; this122 scope selects its own direct methods.
EXCLUDED_LEGACY_METHODS = {
    'tests.test_native_stationary_wait076.NativeStationaryWait076Tests.test_ready_or_issued_unknown_does_not_reopen_the_same_wait':
        'Prior TEST120 evidence records the pre117 SCREEN expectation failing on119/120; its assertion remains unchanged and is not replayed in this122 scope.',
}
FILE_CORE_SOURCES = {'tests.test_native_goods_coverage121': 'NG2Ring.c', 'tests.test_native_price_independent_goods122': 'NG2Ring.c'}
EXTRA_DIRECTORY_CORES = {'tests.test_native_singleton_dependency122': ('CORE', 'CONTROLLER_CORE')}
MAC_CASE_GROUPS = ()
PRODUCT_PATHS = (*shared.PRODUCT_PATHS, 'necroprobe/test118.py', 'test_118.sh',
    'necroprobe/test119.py', 'test_119.sh', 'necroprobe/test120.py', 'test_120.sh',
    'necroprobe/test121.py', 'test_121.sh', 'necroprobe/test122.py', 'test_122.sh')
PRESERVED_PATHS = (*shared.UNCHANGED_CONTINUATION_PATHS,
    'patches/loopctrl/ngg2/NG2Runtime.swift', 'patches/loopctrl/ngg2/NG2Ticket.swift',
    'patches/loopctrl/ngg2/NG2Raster.swift', 'patches/loopctrl/ngg1.patch',
    'patches/loopctrl/source-manifest.json', 'patches/loopctrl/apply_patch.py',
    'patches/loopctrl/ngg2/NG2Perception.c',
    'patches/loopctrl/run_test119_host.py', 'patches/loopctrl/run_test119_python39.py',
    'patches/loopctrl/run_test120_host.py', 'patches/loopctrl/run_test120_python39.py',
    'patches/loopctrl/run_test121_host.py', 'patches/loopctrl/run_test121_python39.py',
    'patches/loopctrl/test_device_ci121.py')
EXPECTED_API = dict(shared.EXPECTED_API,
    device_fixes_capability='necrogold_native_device_fixes118_v1',
    device_fixes119_capability='necrogold_native_device_fixes119_v1',
    device_fixes120_capability='necrogold_native_device_fixes120_v1',
    device_fixes121_capability='necrogold_native_device_fixes121_v1',
    device_fixes122_capability='necrogold_native_device_fixes122_v1')


def reject_fixture_overrides():
    if any(name == 'BASELINE_NAV' or name.startswith(('NECRO_TEST', 'NECRO_NAV', 'NG2_TEST'))
            or re.match(r'^NECRO[0-9]+_', name) for name in os.environ):
        raise ValueError('TEST122 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not MAC_SCOPE_FINALIZED:
        raise ValueError('TEST122 author scopes are pending; no tests may execute')
    if not all((EXPECTED_NATIVE_CHANGES, EXPECTED_REPOSITORY_CHANGES, NEW_PATHS, CASES, CORE_MODULES)):
        raise ValueError('TEST122 source/method inventory is empty')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or any(not row[3] for row in CASES):
        raise ValueError('TEST122 empty or duplicate selected native scope')
    if MAC_CASE_GROUPS != ():
        raise ValueError('TEST122 declares no new Runtime/Mac boundary cases')


def native_inventory(old, current):
    """Check the complete sealed inventory before any selected C tests run."""
    changed = {name for name in set(old)&set(current) if old[name] != current[name]}
    added = set(current)-set(old)
    if (set(old)-set(current) or len(old) != 37 or len(current) != 37+len(EXPECTED_NATIVE_ADDITIONS)
            or changed != set(EXPECTED_NATIVE_CHANGES) or added != set(EXPECTED_NATIVE_ADDITIONS)):
        raise ValueError('TEST122 exact native changed/added inventory differs')
    return changed, added


def source_identity(driver, sealed, upstream):
    ensure_scope(); reject_fixture_overrides()
    code = git(driver, 'rev-parse', 'HEAD').decode().strip()
    path = 'patches/loopctrl/ngg2-manifest.json'; raw = pinned_bytes(driver, path, code)
    manifest = json.loads(raw)
    old = manifest_sources(json.loads(git(driver, 'show', NATIVE_BASELINE+':'+path)))
    current = sealed['native_source_sha256']
    changed, added = native_inventory(old, current)
    if manifest_sources(manifest) != current or any(manifest.get(k) != v for k, v in EXPECTED_API.items()):
        raise ValueError('TEST122 installed source/API/capability identity differs')
    pinned_bytes(driver, 'patches/loopctrl/apply_ngg2.py', code)
    spec = importlib.util.spec_from_file_location('test122_addition_roots', driver/'patches/loopctrl/apply_ngg2.py')
    applier = importlib.util.module_from_spec(spec); spec.loader.exec_module(applier)
    compile_binding = {}
    for name, row in manifest['additions'].items():
        source = applier.addition_source(driver/'patches/loopctrl/ngg2', name, row)
        logical = source.relative_to(driver).as_posix(); digest = sha(pinned_bytes(driver, logical, code))
        if digest != current[name] or sha((upstream/name).read_bytes()) != digest:
            raise ValueError('TEST122 driver compile addition differs from sealed source: '+logical)
        compile_binding[logical] = dict(native_path=name, driver_sha256=digest, sealed_sha256=digest)
    baseline = {p.decode() for p in git(driver, 'ls-tree', '-r', '--name-only', '-z', NATIVE_BASELINE).split(b'\0') if p}
    differences = {p.decode() for p in git(driver, 'diff', '--no-renames', '--name-only', '-z', NATIVE_BASELINE, code, '--').split(b'\0') if p}
    existing = {p for p in differences&baseline if not p.startswith('docs/')}
    new = {p for p in differences-baseline if not p.startswith('docs/')}
    if existing != set(EXPECTED_REPOSITORY_CHANGES) or new != set(NEW_PATHS):
        raise ValueError('TEST122 exact repository changed/new source paths differ')
    if git(driver, 'diff', '--no-ext-diff', '--name-only', code, '--', 'tests', 'necroprobe',
            'tools/ring_native', 'legacy/r12', 'patches/loopctrl', '.github/workflows/loopctrl-geometry.yml',
            'test_116.sh', 'test_117.sh', 'test_118.sh', 'test_119.sh', 'test_120.sh', 'test_121.sh', 'test_122.sh').strip():
        raise ValueError('TEST122 working source differs from pinned CODE')
    ring_path = 'necroprobe/ring_native_manifest.json'; ring_raw = pinned_bytes(driver, ring_path, code)
    if ring_raw != git(driver, 'show', NATIVE_BASELINE+':'+ring_path):
        raise ValueError('TEST122 canonical Ring manifest changed')
    ring = json.loads(ring_raw); r12 = sorted(p for p in baseline if p.startswith('legacy/r12/'))
    if len(ring['sources']) != 15 or len(r12) != 40:
        raise ValueError('TEST122 canonical/R12 source inventory differs')
    preserved = {}
    for name in (*ring['sources'], *r12, *PRESERVED_PATHS):
        data = pinned_bytes(driver, name, code)
        if data != git(driver, 'show', NATIVE_BASELINE+':'+name):
            raise ValueError('TEST122 preserved source changed: '+name)
        preserved[name] = sha(data)
    fixtures = {name.replace('.', '/')+'.py' for name in (*CORE_MODULES, *(row[0] for row in CASES))}
    fixtures.update(p for p in NEW_PATHS if p.startswith(('tests/', 'patches/loopctrl/')))
    fixtures.update('patches/loopctrl/run_test'+v+'_host.py' for v in ('094', '116', '117'))
    return dict(driver_commit=code, native_baseline=NATIVE_BASELINE, native_manifest_sha256=sha(raw),
        changed_native_sources=sorted(changed), native_added=sorted(added),
        preserved_native_source_sha256={n: v for n, v in current.items() if n not in changed|added},
        fixture_source_sha256={p: sha(pinned_bytes(driver, p, code)) for p in sorted(fixtures)},
        product_sha256={p: sha(pinned_bytes(driver, p, code)) for p in PRODUCT_PATHS},
        fixture_compile_source_binding=compile_binding, preserved_source_sha256=preserved,
        retained_root_compile_scope='driver source byte-identical to sealed additions; not sealed-location compilation',
        changed_repository_paths=sorted(existing), new_repository_paths=sorted(new),
        mac_case_groups=[dict(checker=checker, cases=list(cases)) for checker, cases in MAC_CASE_GROUPS],
        historical_runtime_replayed=False, limitation='Software checks do not establish iPhone reach rate or speed.')


def native_suites(upstream, driver):
    ensure_scope(); reject_fixture_overrides()
    shared.CASES, shared.CORE_MODULES = CASES, CORE_MODULES
    suites = shared.native_suites(upstream, driver)
    for name, source in FILE_CORE_SOURCES.items():
        if name in sys.modules:
            sys.modules[name].CORE = upstream/'LoopCtrlUITests'/source
            alias = sys.modules.get(name.rsplit('.', 1)[-1])
            if alias is not None:
                alias.CORE = upstream/'LoopCtrlUITests'/source
    for name, fields in EXTRA_DIRECTORY_CORES.items():
        for module_name in (name, name.rsplit('.', 1)[-1]):
            module = sys.modules.get(module_name)
            if module is not None:
                for field in fields:
                    setattr(module, field, upstream/'LoopCtrlUITests')
    return suites


def run_scope(name, cases, output, evidence, *, receipt_name='test122-host-scope.json'):
    if type(receipt_name) is not str or receipt_name not in ('test122-host-scope.json', 'test122-python39-scope.json'):
        raise ValueError('TEST122 scope receipt name is not permitted')
    cases = selected_cases(cases); stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(cases))
    log = stream.getvalue(); (output/(name+'.txt')).write_text(log); print(log, end='', flush=True)
    evidence[name] = dict(selected=[c.id() for c in cases], tests_run=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        expected_failures=len(result.expectedFailures))
    (output/receipt_name).write_text(json.dumps(evidence, indent=2)+'\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name+': selected methods must all execute Green')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('driver', 'upstream', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args(); ensure_scope()
    driver, upstream, output = (getattr(args, n).resolve() for n in ('driver', 'upstream', 'output'))
    sys.path[:0] = [str(driver), str(driver/'tests'), str(HERE)]
    verifier = importlib.import_module('verify_package')
    sealed = verifier.inspect_native_sources(upstream, driver); binding = source_identity(driver, sealed, upstream)
    suites = native_suites(upstream, driver); selected_cases(c for _, cases in suites for c in cases)
    native = importlib.import_module('tests.test_native_controller'); cycle = importlib.import_module('tests.test_native_cycle094')
    abi = {n: ctypes.sizeof(getattr(native, n)) for n in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    abi['Cycle'] = ctypes.sizeof(cycle.Cycle)
    if abi != dict(Scene=23864, Status=192, Event=128, MotionWait=48, RecoveryStatus=456, Cycle=216):
        raise ValueError('TEST122 existing public POD ABI changed')
    output.mkdir(parents=True, exist_ok=True)
    evidence = dict(scope='TEST122 selected native/client boundary contracts', source_identity=sealed,
        production_source_binding=binding, abi_bytes=abi, device_test='not_run',
        excluded_legacy_methods=EXCLUDED_LEGACY_METHODS,
        not_run=['old Runtime/fault/world collections: not replayed; no new Runtime boundary changed',
            'iPhone reach rate, precision and speed acceptance'])
    for label, cases in suites:
        run_scope(label, cases, output, evidence)
    selector = importlib.import_module('test_device_ci122')
    run_scope('test122-selector', unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection122Tests), output, evidence)
    if verifier.inspect_native_sources(upstream, driver) != sealed or source_identity(driver, sealed, upstream) != binding:
        raise ValueError('TEST122 tests changed sealed source')
    reject_fixture_overrides(); evidence['sealed_sources_unchanged_after_tests'] = True
    (output/'test122-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS TEST122 selected source-bound contracts; iPhone acceptance is separate')


if __name__ == '__main__':
    main()
