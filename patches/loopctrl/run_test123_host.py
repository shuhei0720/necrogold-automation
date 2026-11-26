"""TEST123 exact source and boundary selection; pending scopes fail closed."""
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
_spec = importlib.util.spec_from_file_location('test123_shared117', HERE/'run_test117_host.py')
shared = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
selected_cases, method_cases, manifest_sources = shared.selected_cases, shared.method_cases, shared.manifest_sources
NATIVE_BASELINE = 'c7e0944badaf0fad0fb1d21345441ea7371c71df'
SCOPE_FINALIZED = True
MAC_SCOPE_FINALIZED = True
# Final authored AST selects host83/native55/selector14 and Python3.9 exact97.
# Scope flags freeze inventory; source identity is verified against the final seal/CODE before tests.
EXPECTED_SELECTED_METHOD_COUNT = 83
EXPECTED_NATIVE_METHOD_COUNT = 55
EXPECTED_CORE_MODULE_COUNT = 50
PENDING_SCOPE_ITEMS = ()
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlKit/RPCMethod.swift',
    'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Ring.c', 'LoopCtrlUITests/NG2Ring.h'})
EXPECTED_NATIVE_ADDITIONS = frozenset()
EXPECTED_REPOSITORY_CHANGES = frozenset(('.github/workflows/loopctrl-geometry.yml',
 'necroprobe/campaign116.py',
 'patches/loopctrl/apply_ngg2.py',
 'patches/loopctrl/ngg2-manifest.json',
 'patches/loopctrl/ngg2.patch',
 'patches/loopctrl/ngg2/NG2Controller.c',
 'patches/loopctrl/ngg2/NG2Ring.c',
 'patches/loopctrl/ngg2/NG2Ring.h',
 'patches/loopctrl/verify_package.py',
 'tests/test_continuous_client117.py',
 'tests/test_continuous_client118.py',
 'tests/test_continuous_client119.py',
 'tests/test_continuous_client120.py',
 'tests/test_continuous_client121.py',
 'tests/test_continuous_client122.py'))
# All new fixture and client paths are explicit before source pinning.
NEW_PATHS = frozenset(('necroprobe/test123.py',
 'patches/loopctrl/run_test123_host.py',
 'patches/loopctrl/run_test123_python39.py',
 'patches/loopctrl/test_device_ci123.py',
 'test_123.sh',
 'tests/test_continuous_client123.py',
 'tests/test_native_partial_top_wall123.py',
 'tests/test_native_two_sign_goods123.py'))
# Explicit authored methods and directly related regressions, not whole old suites.
# Final source-only AST methods. Scope flags prevent every fixture import/execution.
CASES = (
    ('tests.test_native_partial_top_wall123', 'NativePartialTopWall123Tests', 'test123-native-NativePartialTopWall123Tests', frozenset({
        'test_actual_commit_parent_before_equal_after_is_independent_of_capture_analysis',
        'test_both_rails_bind_new_source_with_frozen_parent_and_no_move_credit',
        'test_current_metadata_release_source_age_and_owner_are_not_borrowed',
        'test_existing_credit_and_reserved_move_are_never_rescued_by_new_data',
        'test_immutable_hud_history_is_retained_but_old_model_slot_and_epoch_are_revoked',
        'test_new_candidate_or_unproved_current_keeps_data_and_never_resends',
        'test_new_safe_unknown_needs_independent_current_and_fit_before_up_actual_unit',
        'test_original_geometry_support_and_five_cell_crosses_remain_required',
        'test_original_phase_budget_with_new_worker100_and_current31ms_reaches_up_unit',
        'test_retained_hud_history_cannot_replace_current_freshness_prefix_or_owner',
        'test_second_projection_job_cannot_rearm_one_use_or_refund_shared_data',
    }), True),
    ('tests.test_native_two_sign_goods123', 'NativeTwoSignGoods123Tests', 'test123-native-NativeTwoSignGoods123Tests', frozenset({
        'test_all_alias_edges_and_tail_keep_candidate_priority',
        'test_deadline_cancel_mode_boundaries',
        'test_fixed_vertical_cap_covers_all625',
        'test_missing_observation_or_actual_face_stays_unknown',
        'test_normal_bbox_seed_set_and_deterministic_master',
        'test_normal_durable_public_restart',
        'test_numeric_expected_rows_and_full_outer_prefix_reject_deletion_or_reorder',
        'test_vertical_numeric_stats_and_tags_reject_forgery',
    }), True),
    ('tests.test_native_top_projection106', 'NativeTopProjection106Tests', 'test123-related-NativeTopProjection106Tests', frozenset({
        'test_new_target_candidate_and_missing_independent_zero_hold_after_the_new_job',
        'test_new_top_projection_retires_reserved_credit_and_classifies_latest_before_up',
        'test_projection_does_not_restore_the_one_use_exposed_item_allowance',
        'test_projection_requires_the_unchanged_supported_lower_row_and_explained_halo',
    }), False),
    ('tests.test_native_partial_roles107', 'NativePartialRoles107Tests', 'test123-related-NativePartialRoles107Tests', frozenset({
        'test_growth_over_supported_top_gold_composes_with_far_palette_before_new_job_and_move',
        'test_mixed_refresh_real_up_and_current_normal_producer_reach_durable_restart',
        'test_new_job_target_candidate_and_missing_independent_zero_hold',
        'test_remote_protected_non_item_top_exposure_reclassifies_once_without_old_credit',
        'test_role_support_geometry_authority_and_original_deadline_are_required',
        'test_supported_roles_translate_to_the_other_observed_top_columns',
        'test_top_alias_reduction_and_old_shielded_palette_share_one_static_proof',
    }), False),
    ('tests.test_native_partial_wall_refresh105', 'NativePartialWallRefresh105Tests', 'test123-related-NativePartialWallRefresh105Tests', frozenset({
        'test_latest_positive_candidate_and_unproved_zero_never_resume_old_move',
        'test_new_protected_wall_withdraws_credit_and_any_definitely_unsent_ticket',
        'test_remote_observed_gold_retires_job_and_waits_for_latest_result_and_independent_zero',
        'test_wall_refresh_rejects_other_protected_changes_and_missing_original_authority',
    }), False),
    ('tests.test_native_partial_refresh104', 'NativePartialRefresh104Tests', 'test123-related-NativePartialRefresh104Tests', frozenset({
        'test_far_refresh_does_not_consume_or_restore_old_exposed_item_once_allowance',
        'test_new_far_gold_and_material_refresh_withdraw_credit_and_reserved_ticket',
        'test_refresh_requires_fresh_stable_prefix_original_parent_and_control_owner',
    }), False),
    ('tests.test_native_price_independent_goods122', 'NativePriceIndependentGoods122Tests', 'test123-native-NativePriceIndependentGoods122Tests', frozenset({
        'test_every_cell_and_original_partial_keeps_image_and_word_candidate_priority',
        'test_normal_price_free_producer_reaches_durable_public_restart',
        'test_numeric_price_free_tag_and_own_anchor_reject_forged_fields',
        'test_price_independent_full_strip_requires_real_goods_auth_and_observation',
    }), True),
    ('tests.test_native_goods_coverage121', 'NativeGoodsCoverage121Tests', 'test123-related-NativeGoodsCoverage121Tests', frozenset({
        'test_complete_single_shop_uses_relative_glyph_without_a_merchant_identity',
        'test_every_numeric_alias_keeps_five_cell_target_candidate_priority',
        'test_group_ownership_and_diagonal_floor_cannot_discard_other_boards_or_support',
        'test_new_numeric_tags_caps_and_auth_fields_are_independently_rechecked',
        'test_normal_new_producer_reaches_public_C_durable_restart_and_next_floor',
        'test_relative_glyph_needs_complete_ink_sign_support_and_exact_offer_scene',
        'test_three_owned_components_and_one_diagonal_floor_prove_complete_grouped_offer',
    }), False),
    ('patches.loopctrl.test_apply_ngg2', 'NGG2ApplyTests', 'test123-package-related', frozenset({
        'test_changed_and_new_source_install_together',
        'test_native_cycle_requires_strict_ring_profile_three_without_changing_legacy_cap',
        'test_native_v14_package_requires_actual_api16_and_strict_profile_v2',
        'test_native_v15_evidence_package_keeps_api16_and_strict_profile_v2',
        'test_package_provenance_rejects_changed_native_source',
        'test_package_provenance_rejects_even_resealed_stale_runtime_envelope_api',
        'test_seal_pins_each_canonical_shared_source_without_repository_copies',
        'test_seal_still_rejects_empty_native_assets_despite_shared_kernel',
    }), False),
    ('patches.loopctrl.test_device_ci123', 'DeviceImplementationCapability123Tests', 'test123-capability', frozenset({
        'test_123_cannot_bypass_the_existing_122_package_binding',
        'test_current_patch_adds_123_without_replacing_118_119_120_or_121_or_122',
        'test_historical_122_manifest_gets_no_unrequested_123_field',
        'test_package_has_separate_123_field_and_unchanged_prior_API_and_profile',
        'test_resealed_mismatched_123_metadata_patch_or_rpc_is_rejected',
        'test_sealing_requires_one_real_uncommented_123_array_entry',
    }), True),
    ('tests.test_native_shop115', 'NativeShop115Tests', 'test123-related-NativeShop115Tests', frozenset({
        'test_partial_projection_change_queues_independent_current_data',
        'test_partial_requires_yield_profile_matching_prefix_and_original_parent',
        'test_partial_two_zeros_without_a_new_phase_sample_cannot_use_old_fit',
    }), False),
    ('tests.test_native_partial116', 'NativePartial116Tests', 'test123-related-NativePartial116Tests', frozenset({
        'test_issued_but_unbegun_credit_is_retired_without_refunding_an_input',
        'test_reverse_top_projection_keeps_fixed_epoch_and_original_one_up',
        'test_reverse_top_relation_rejects_unexplained_goods_floor_gold_and_motion',
        'test_top_transition_after_unused_credit_starts_independent_data',
    }), False),
)
# Import/source binding only; execute only the explicit CASES.
# Source-only static import closure; no fixture or runner was imported to construct it.
CORE_MODULES = ('tests.test_beat_sync',
 'tests.test_native_beat',
 'tests.test_native_blocked067',
 'tests.test_native_bottom_shop103',
 'tests.test_native_classification111',
 'tests.test_native_closed_offer105',
 'tests.test_native_controller',
 'tests.test_native_current_view114',
 'tests.test_native_cycle094',
 'tests.test_native_cycle_binary095',
 'tests.test_native_entry_corridor102',
 'tests.test_native_entry_episode102',
 'tests.test_native_full_framing101',
 'tests.test_native_goods113',
 'tests.test_native_goods_coverage121',
 'tests.test_native_irregular110',
 'tests.test_native_motion067',
 'tests.test_native_motion075',
 'tests.test_native_navigation',
 'tests.test_native_observation072',
 'tests.test_native_observed_shop_controller104',
 'tests.test_native_offer_controller105',
 'tests.test_native_offer_coverage104',
 'tests.test_native_opened_entry093',
 'tests.test_native_opened_fade100',
 'tests.test_native_partial116',
 'tests.test_native_partial_entry097',
 'tests.test_native_partial_framing097',
 'tests.test_native_partial_refresh104',
 'tests.test_native_partial_roles107',
 'tests.test_native_partial_top_wall123',
 'tests.test_native_partial_wall_refresh105',
 'tests.test_native_perception',
 'tests.test_native_price_independent_goods122',
 'tests.test_native_recovery',
 'tests.test_native_ring094',
 'tests.test_native_ring_bank094',
 'tests.test_native_shop115',
 'tests.test_native_shop_coverage102',
 'tests.test_native_shop_geometry101',
 'tests.test_native_side_shop100',
 'tests.test_native_single_offer108',
 'tests.test_native_single_sign_shop103',
 'tests.test_native_static075',
 'tests.test_native_structural_cycle096',
 'tests.test_native_structural_shop096',
 'tests.test_native_top_projection106',
 'tests.test_native_two_sign_goods123',
 'tests.test_native_upper_entry112',
 'tests.test_target_assessment087')
# TEST120 recorded the unchanged pre117 SCREEN assertion failing on119/120.
# Keep that historical exclusion; this123 scope selects its own direct methods.
EXCLUDED_LEGACY_METHODS = {
    'tests.test_native_stationary_wait076.NativeStationaryWait076Tests.test_ready_or_issued_unknown_does_not_reopen_the_same_wait':
        'Prior TEST120 evidence records the pre117 SCREEN expectation failing on119/120; its assertion remains unchanged and is not replayed in this123 scope.',
}
FILE_CORE_SOURCES = {'tests.test_native_goods_coverage121': 'NG2Ring.c',
    'tests.test_native_price_independent_goods122': 'NG2Ring.c'}
EXTRA_FILE_CORES = {'tests.test_native_two_sign_goods123': {
    'RING': 'NG2Ring.c', 'CONTROLLER': 'NG2Controller.c'}}
EXTRA_DIRECTORY_CORES = {'tests.test_native_controller': ('CORE',)}
MAC_CASE_GROUPS = ()
PRODUCT_PATHS = (*shared.PRODUCT_PATHS, 'necroprobe/test118.py', 'test_118.sh',
    'necroprobe/test119.py', 'test_119.sh', 'necroprobe/test120.py', 'test_120.sh',
    'necroprobe/test121.py', 'test_121.sh', 'necroprobe/test122.py', 'test_122.sh',
    'necroprobe/test123.py', 'test_123.sh')
PRESERVED_PATHS = (*shared.UNCHANGED_CONTINUATION_PATHS,
    'patches/loopctrl/ngg2/NG2Runtime.swift', 'patches/loopctrl/ngg2/NG2Ticket.swift',
    'patches/loopctrl/ngg2/NG2Raster.swift', 'patches/loopctrl/ngg1.patch',
    'patches/loopctrl/source-manifest.json', 'patches/loopctrl/apply_patch.py',
    'patches/loopctrl/ngg2/NG2Perception.c', 'patches/loopctrl/ngg2/NG2Navigation.c',
    'patches/loopctrl/run_test119_host.py', 'patches/loopctrl/run_test119_python39.py',
    'patches/loopctrl/run_test120_host.py', 'patches/loopctrl/run_test120_python39.py',
    'patches/loopctrl/run_test121_host.py', 'patches/loopctrl/run_test121_python39.py',
    'patches/loopctrl/test_device_ci121.py',
    'patches/loopctrl/run_test122_host.py', 'patches/loopctrl/run_test122_python39.py',
    'patches/loopctrl/test_device_ci122.py')
EXPECTED_API = dict(shared.EXPECTED_API,
    device_fixes_capability='necrogold_native_device_fixes118_v1',
    device_fixes119_capability='necrogold_native_device_fixes119_v1',
    device_fixes120_capability='necrogold_native_device_fixes120_v1',
    device_fixes121_capability='necrogold_native_device_fixes121_v1',
    device_fixes122_capability='necrogold_native_device_fixes122_v1',
    device_fixes123_capability='necrogold_native_device_fixes123_v1')


def reject_fixture_overrides():
    if any(name == 'BASELINE_NAV' or name.startswith(('NECRO_TEST', 'NECRO_NAV', 'NG2_TEST'))
            or re.match(r'^NECRO[0-9]+_', name) for name in os.environ):
        raise ValueError('TEST123 sealed fixture overrides are forbidden')


def ensure_scope():
    if (not SCOPE_FINALIZED or not MAC_SCOPE_FINALIZED or PENDING_SCOPE_ITEMS
            or any(type(value) is not int or value <= 0 for value in (EXPECTED_SELECTED_METHOD_COUNT,
                EXPECTED_NATIVE_METHOD_COUNT, EXPECTED_CORE_MODULE_COUNT))):
        raise ValueError('TEST123 author scopes are pending; no tests may execute')
    if not all((EXPECTED_NATIVE_CHANGES, EXPECTED_REPOSITORY_CHANGES, NEW_PATHS, CASES, CORE_MODULES)):
        raise ValueError('TEST123 source/method inventory is empty')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or any(not row[3] for row in CASES):
        raise ValueError('TEST123 empty or duplicate selected native scope')
    if MAC_CASE_GROUPS != ():
        raise ValueError('TEST123 declares no new Runtime/Mac boundary cases')


def native_inventory(old, current):
    """Check the complete sealed inventory before any selected C tests run."""
    changed = {name for name in set(old)&set(current) if old[name] != current[name]}
    added = set(current)-set(old)
    if (set(old)-set(current) or len(old) != 37 or len(current) != 37+len(EXPECTED_NATIVE_ADDITIONS)
            or changed != set(EXPECTED_NATIVE_CHANGES) or added != set(EXPECTED_NATIVE_ADDITIONS)):
        raise ValueError('TEST123 exact native changed/added inventory differs')
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
        raise ValueError('TEST123 installed source/API/capability identity differs')
    pinned_bytes(driver, 'patches/loopctrl/apply_ngg2.py', code)
    spec = importlib.util.spec_from_file_location('test123_addition_roots', driver/'patches/loopctrl/apply_ngg2.py')
    applier = importlib.util.module_from_spec(spec); spec.loader.exec_module(applier)
    compile_binding = {}
    for name, row in manifest['additions'].items():
        source = applier.addition_source(driver/'patches/loopctrl/ngg2', name, row)
        logical = source.relative_to(driver).as_posix(); digest = sha(pinned_bytes(driver, logical, code))
        if digest != current[name] or sha((upstream/name).read_bytes()) != digest:
            raise ValueError('TEST123 driver compile addition differs from sealed source: '+logical)
        compile_binding[logical] = dict(native_path=name, driver_sha256=digest, sealed_sha256=digest)
    baseline = {p.decode() for p in git(driver, 'ls-tree', '-r', '--name-only', '-z', NATIVE_BASELINE).split(b'\0') if p}
    differences = {p.decode() for p in git(driver, 'diff', '--no-renames', '--name-only', '-z', NATIVE_BASELINE, code, '--').split(b'\0') if p}
    existing = {p for p in differences&baseline if not p.startswith('docs/')}
    new = {p for p in differences-baseline if not p.startswith('docs/')}
    if existing != set(EXPECTED_REPOSITORY_CHANGES) or new != set(NEW_PATHS):
        raise ValueError('TEST123 exact repository changed/new source paths differ')
    if git(driver, 'diff', '--no-ext-diff', '--name-only', code, '--', 'tests', 'necroprobe',
            'tools/ring_native', 'legacy/r12', 'patches/loopctrl', '.github/workflows/loopctrl-geometry.yml',
            'test_116.sh', 'test_117.sh', 'test_118.sh', 'test_119.sh', 'test_120.sh', 'test_121.sh', 'test_122.sh', 'test_123.sh').strip():
        raise ValueError('TEST123 working source differs from pinned CODE')
    ring_path = 'necroprobe/ring_native_manifest.json'; ring_raw = pinned_bytes(driver, ring_path, code)
    if ring_raw != git(driver, 'show', NATIVE_BASELINE+':'+ring_path):
        raise ValueError('TEST123 canonical Ring manifest changed')
    ring = json.loads(ring_raw); r12 = sorted(p for p in baseline if p.startswith('legacy/r12/'))
    if len(ring['sources']) != 15 or len(r12) != 40:
        raise ValueError('TEST123 canonical/R12 source inventory differs')
    preserved = {}
    for name in (*ring['sources'], *r12, *PRESERVED_PATHS):
        data = pinned_bytes(driver, name, code)
        if data != git(driver, 'show', NATIVE_BASELINE+':'+name):
            raise ValueError('TEST123 preserved source changed: '+name)
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
    for name, fields in EXTRA_FILE_CORES.items():
        for module_name in (name, name.rsplit('.', 1)[-1]):
            module = sys.modules.get(module_name)
            if module is not None:
                for field, source in fields.items():
                    setattr(module, field, upstream/'LoopCtrlUITests'/source)
    for name, fields in EXTRA_DIRECTORY_CORES.items():
        for module_name in (name, name.rsplit('.', 1)[-1]):
            module = sys.modules.get(module_name)
            if module is not None:
                for field in fields:
                    setattr(module, field, upstream/'LoopCtrlUITests')
    return suites


def run_scope(name, cases, output, evidence, *, receipt_name='test123-host-scope.json'):
    if type(receipt_name) is not str or receipt_name not in ('test123-host-scope.json', 'test123-python39-scope.json'):
        raise ValueError('TEST123 scope receipt name is not permitted')
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
        raise ValueError('TEST123 existing public POD ABI changed')
    output.mkdir(parents=True, exist_ok=True)
    evidence = dict(scope='TEST123 selected native/client boundary contracts', source_identity=sealed,
        production_source_binding=binding, abi_bytes=abi, device_test='not_run',
        excluded_legacy_methods=EXCLUDED_LEGACY_METHODS,
        not_run=['old Runtime/fault/world collections: not replayed; no new Runtime boundary changed',
            'iPhone reach rate, precision and speed acceptance'])
    for label, cases in suites:
        run_scope(label, cases, output, evidence)
    selector = importlib.import_module('test_device_ci123')
    run_scope('test123-selector', unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection123Tests), output, evidence)
    if verifier.inspect_native_sources(upstream, driver) != sealed or source_identity(driver, sealed, upstream) != binding:
        raise ValueError('TEST123 tests changed sealed source')
    reject_fixture_overrides(); evidence['sealed_sources_unchanged_after_tests'] = True
    (output/'test123-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS TEST123 selected source-bound contracts; iPhone acceptance is separate')


if __name__ == '__main__':
    main()
