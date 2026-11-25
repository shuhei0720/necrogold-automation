"""TEST121 exact source and boundary selection; pending scopes fail closed."""
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
_spec = importlib.util.spec_from_file_location('test121_shared117', HERE/'run_test117_host.py')
shared = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(shared)
sha, git, pinned_bytes = shared.sha, shared.git, shared.pinned_bytes
selected_cases, method_cases, manifest_sources = shared.selected_cases, shared.method_cases, shared.manifest_sources
NATIVE_BASELINE = '55a762f61eaf010a2cb135836d3658b4225bb751'
SCOPE_FINALIZED = True
MAC_SCOPE_FINALIZED = True
# Final source inventory from the reviewed TEST121 author freezes.
EXPECTED_NATIVE_CHANGES = frozenset({'LoopCtrlKit/RPCMethod.swift',
    'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Navigation.c',
    'LoopCtrlUITests/NG2Ring.c', 'LoopCtrlUITests/NG2Ring.h'})
EXPECTED_NATIVE_ADDITIONS = frozenset()
EXPECTED_REPOSITORY_CHANGES = frozenset({
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
})
# All new fixture and client paths are explicit before source pinning.
NEW_PATHS = frozenset({
    'necroprobe/test121.py',
    'patches/loopctrl/run_test121_host.py',
    'patches/loopctrl/run_test121_python39.py',
    'patches/loopctrl/test_device_ci121.py',
    'test_121.sh',
    'tests/test_continuous_client121.py',
    'tests/test_native_closed_door_palette121.py',
    'tests/test_native_navigation121.py',
    'tests/test_native_goods_coverage121.py',
})
# Explicit authored methods and directly related regressions, not whole old suites.
CASES = (
    ('tests.test_native_closed_door_palette121', 'NativeClosedDoorPalette121Tests', 'test121-native-NativeClosedDoorPalette121Tests', frozenset({
        'test_direct_zero_full_choice_and_current_prefix_are_required',
        'test_near_admission_rejects_extra_corners_traversal_goods_and_protection',
        'test_old_far_quiet_and_unknown_gate_refit_keep_existing_qualification',
        'test_original_D_actual_commit_and_external_owner_guards_remain',
        'test_started_ACK_unknown_and_original_visual_parent_do_not_gain_authority',
        'test_unstarted_closed_door_keeps_same_id_source_bounds_and_zero_move_credit',
    }), True),
    ('tests.test_native_navigation121', 'NativeSplitRoofMouth121Tests', 'test121-native-NativeSplitRoofMouth121Tests', frozenset({
        'test_all_positive_inside_floors_and_the_mouth_are_required',
        'test_dark_cells_remain_unknown_without_erasing_existing_positive_mouths',
        'test_each_roof_end_cap_and_lower_boundary_is_independent_required_support',
        'test_fixed_coordinates_do_not_alias_new_directions_and_keep_old_transposed_shape',
        'test_legacy_nonzero_including_120_cap_and_simultaneous_lower_fringe_wins_exactly',
        'test_split_roof_observed_mouth_adds_only_its_fixed_left_bit5',
        'test_state_goods_gold_item_all_protection_and_black_or_door_only_are_refused',
        'test_unchanged_chooser_stops_after_three_floors_before_unknown_inboard_and_mouth',
    }), True),
    ('tests.test_native_device066', 'NativeDevice066Tests', 'test121-related-NativeDevice066Tests', frozenset({
        'test_changed_local_door_bracket_goods_or_protection_never_reuses_the_ticket',
        'test_door_goods_cancel_and_control_authority_preempt_distant_drift',
        'test_door_quiet_uses_actual_commit_and_frozen_deadline',
        'test_door_requires_strict_blocked_signature_proof',
        'test_unchanged_door_survives_distant_palette_drift_and_opens_before_entry',
        'test_unstable_prefix_and_started_or_unknown_door_cannot_gain_quiet_authority',
    }), False),
    ('tests.test_native_closed_floor113', 'NativeClosedFloor113Tests', 'test121-related-NativeClosedFloor113Tests', frozenset({
        'test_closed_floor_refresh_refuses_changed_local_material_route_or_protection',
        'test_remote_floor_palette_keeps_exact_unsent_ticket_without_same_reissues',
        'test_remote_stone_refresh_retires_then_requires_independent_future_ticket',
    }), False),
    ('tests.test_native_closed_refresh081', 'NativeClosedRefresh081Tests', 'test121-related-NativeClosedRefresh081Tests', frozenset({
        'test_four_direction_closed_gate_refresh_accepts_remote_stone_without_credit',
        'test_published_identity_source_and_old_refresh_scope_do_not_broaden',
    }), False),
    ('tests.test_native_observation072', 'NativeObservation072Tests', 'test121-related-NativeObservation072Tests', frozenset({
        'test_unknown_goods_observed_vantage_keeps_original_beat_for_irrelevant_drift',
    }), False),
    ('tests.test_native_opened_entry093', 'NativeOpenedEntry093Tests', 'test121-related-NativeOpenedEntry093Tests', frozenset({
        'test_goods_cancel_unknown_ack_prefix_and_original_budgets_stay_authoritative',
        'test_observed_inner_floor_after_opening_revalidates_in_four_directions',
    }), False),
    ('tests.test_native_navigation120', 'NativeCappedLeft120Tests', 'test121-related-NativeCappedLeft120Tests', frozenset({
        'test_cap_and_independent_boundaries_merit_only_the_fixed_left_bit5',
        'test_old_nonzero_masks_win_even_when_the_new_witness_also_matches',
        'test_unchanged_chooser_uses_four_known_floors_and_stops_before_the_opaque_mouth',
    }), False),
    ('tests.test_native_passage_navigation072', 'NativePassageNavigation072Tests', 'test121-related-NativePassageNavigation072Tests', frozenset({
        'test_candidate_bits_cover_annotated_families_and_multiple_mouths',
        'test_fixed_world_mouth_reaches_one_outside_with_real_floor_steps',
    }), False),
    ('tests.test_native_occluded_corner097', 'NativeOccludedCorner097Tests', 'test121-related-NativeOccludedCorner097Tests', frozenset({
        'test_elbow_requires_each_observed_turn_wall_floor_and_unknown_direct_outside',
        'test_left_elbow_uses_diagonal_outside_floor_without_inventing_direct_outside_floor',
    }), False),
    ('tests.test_native_navigation116', 'NativeCappedNeck116Tests', 'test121-related-NativeCappedNeck116Tests', frozenset({
        'test_capped_observed_necks_keep_the_existing_world_bits_in_both_axes',
    }), False),
    ('tests.test_native_navigation117', 'NativeOpaqueFringe117Tests', 'test121-related-NativeOpaqueFringe117Tests', frozenset({
        'test_observed_floor_bend_adds_only_its_fixed_left_mouth',
    }), False),
    ('tests.test_native_goods_coverage121', 'NativeGoodsCoverage121Tests', 'test121-native-NativeGoodsCoverage121Tests', frozenset({
        'test_complete_single_shop_uses_relative_glyph_without_a_merchant_identity',
        'test_every_numeric_alias_keeps_five_cell_target_candidate_priority',
        'test_group_ownership_and_diagonal_floor_cannot_discard_other_boards_or_support',
        'test_new_numeric_tags_caps_and_auth_fields_are_independently_rechecked',
        'test_normal_new_producer_reaches_public_C_durable_restart_and_next_floor',
        'test_relative_glyph_needs_complete_ink_sign_support_and_exact_offer_scene',
        'test_three_owned_components_and_one_diagonal_floor_prove_complete_grouped_offer',
    }), True),
    ('tests.test_native_single_sign_shop103', 'NativeSingleSignShop103Tests', 'test121-related-NativeSingleSignShop103Tests', frozenset({
        'test_numeric_certificate_rejects_missing_face_fake_merchant_and_old_binary_mutations',
        'test_one_real_full_face_and_strong_merchant_certify_only_complete_strip',
        'test_raw_endcaps_prices_extra_groups_and_missing_items_are_held',
        'test_target_full_strip_and_strong_name_keep_positive_priority',
    }), False),
    ('tests.test_native_shop_coverage102', 'NativeShopCoverage102Tests', 'test121-related-NativeShopCoverage102Tests', frozenset({
        'test_bottom_alignment_selects_one_canonical_row_without_deleting_evidence',
        'test_bottom_door_and_top_prefix_have_independent_complete_proof',
        'test_certificate6_rechecks_every_existing_numeric_and_binary_guard',
        'test_target_icon_and_strong_word_keep_positive_priority',
    }), False),
    ('tests.test_native_offer_witness109', 'NativeOfferWitness109Tests', 'test121-related-NativeOfferWitness109Tests', frozenset({
        'test_both_independent_causes_are_fixed_in_one_normal_producer_result',
        'test_existing_numeric_certificate_rejects_missing_positive_evidence',
    }), False),
    ('tests.test_native_offer_witness109', 'NativeOfferWitnessController109Tests', 'test121-related-NativeOfferWitnessController109Tests', frozenset({
        'test_normal_negative_requires_pause_durable_intent_restart_ack_and_new_floor',
    }), False),
    ('tests.test_native_price_fragments118', 'NativePriceFragments118Tests', 'test121-related-NativePriceFragments118Tests', frozenset({
        'test_lower_entry_uses_existing_eighteen_ink_rule_for_small_nonprice_fragments',
    }), False),
    ('tests.test_native_offer_coverage104', 'NativeOfferCoverage104Tests', 'test121-related-NativeOfferCoverage104Tests', frozenset({
        'test_all_strip_templates_and_strong_name_keep_target_priority',
        'test_numeric_certificate_keeps_mapping_finite_score_box_and_absence_guards',
    }), False),
    ('tests.test_native_cycle094', 'NativeCycle094Tests', 'test121-related-NativeCycle094Tests', frozenset({
        'test_deadline_and_cancelled_worker_results_are_inert',
        'test_negative_authority_needs_durable_checkpoint_and_new_pause_source',
    }), False),
    ('patches.loopctrl.test_device_ci121', 'DeviceImplementationCapability121Tests', 'test121-capability', frozenset({
        'test_121_cannot_bypass_the_existing_120_package_binding',
        'test_current_patch_adds_121_without_replacing_118_119_or_120',
        'test_historical_120_manifest_gets_no_unrequested_121_field',
        'test_package_has_separate_121_field_and_unchanged_prior_API_and_profile',
        'test_resealed_mismatched_121_metadata_patch_or_rpc_is_rejected',
        'test_sealing_requires_one_real_uncommented_121_array_entry',
    }), True),
    ('patches.loopctrl.test_apply_ngg2', 'NGG2ApplyTests', 'test121-package-related', frozenset({
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
    'tests.test_native_closed_door_palette121',
    'tests.test_native_closed_floor113',
    'tests.test_native_closed_offer105',
    'tests.test_native_closed_price106',
    'tests.test_native_closed_refresh081',
    'tests.test_native_controller',
    'tests.test_native_corner_vantage086',
    'tests.test_native_cycle094',
    'tests.test_native_device066',
    'tests.test_native_goods_coverage121',
    'tests.test_native_irregular110',
    'tests.test_native_lower_fringe100',
    'tests.test_native_navigation',
    'tests.test_native_navigation116',
    'tests.test_native_navigation117',
    'tests.test_native_navigation120',
    'tests.test_native_navigation121',
    'tests.test_native_observation072',
    'tests.test_native_occluded_corner097',
    'tests.test_native_offer_coverage104',
    'tests.test_native_offer_witness109',
    'tests.test_native_opened_entry093',
    'tests.test_native_passage072',
    'tests.test_native_passage_navigation072',
    'tests.test_native_passage_unsent076',
    'tests.test_native_perception',
    'tests.test_native_price_fragments118',
    'tests.test_native_recovery',
    'tests.test_native_ring094',
    'tests.test_native_ring117',
    'tests.test_native_ring_bank094',
    'tests.test_native_route_observation120',
    'tests.test_native_shadow_passage094',
    'tests.test_native_shop_coverage102',
    'tests.test_native_shop_geometry101',
    'tests.test_native_side_shop100',
    'tests.test_native_single_offer108',
    'tests.test_native_single_sign_shop103',
    'tests.test_native_solid_corner098',
    'tests.test_native_split_shadow095',
    'tests.test_native_stationary_wait076',
    'tests.test_native_structural_shop096',
    'tests.test_native_supported_mouth084',
    'tests.test_target_assessment087',
)
# TEST120 recorded the unchanged pre117 SCREEN assertion failing on119/120.
# Keep that historical exclusion; this121 scope selects its own direct methods.
EXCLUDED_LEGACY_METHODS = {
    'tests.test_native_stationary_wait076.NativeStationaryWait076Tests.test_ready_or_issued_unknown_does_not_reopen_the_same_wait':
        'Prior TEST120 evidence records the pre117 SCREEN expectation failing on119/120; its assertion remains unchanged and is not replayed in this121 scope.',
}
FILE_CORE_SOURCES = {'tests.test_native_goods_coverage121': 'NG2Ring.c'}
MAC_CASE_GROUPS = ()
PRODUCT_PATHS = (*shared.PRODUCT_PATHS, 'necroprobe/test118.py', 'test_118.sh',
    'necroprobe/test119.py', 'test_119.sh', 'necroprobe/test120.py', 'test_120.sh',
    'necroprobe/test121.py', 'test_121.sh')
PRESERVED_PATHS = (*shared.UNCHANGED_CONTINUATION_PATHS,
    'patches/loopctrl/ngg2/NG2Runtime.swift', 'patches/loopctrl/ngg2/NG2Ticket.swift',
    'patches/loopctrl/ngg2/NG2Raster.swift', 'patches/loopctrl/ngg1.patch',
    'patches/loopctrl/source-manifest.json', 'patches/loopctrl/apply_patch.py',
    'patches/loopctrl/ngg2/NG2Perception.c',
    'patches/loopctrl/run_test119_host.py', 'patches/loopctrl/run_test119_python39.py',
    'patches/loopctrl/run_test120_host.py', 'patches/loopctrl/run_test120_python39.py')
EXPECTED_API = dict(shared.EXPECTED_API,
    device_fixes_capability='necrogold_native_device_fixes118_v1',
    device_fixes119_capability='necrogold_native_device_fixes119_v1',
    device_fixes120_capability='necrogold_native_device_fixes120_v1',
    device_fixes121_capability='necrogold_native_device_fixes121_v1')


def reject_fixture_overrides():
    if any(name == 'BASELINE_NAV' or name.startswith('NECRO_TEST')
            or re.match(r'^NECRO[0-9]+_', name) for name in os.environ):
        raise ValueError('TEST121 sealed fixture overrides are forbidden')


def ensure_scope():
    if not SCOPE_FINALIZED or not MAC_SCOPE_FINALIZED:
        raise ValueError('TEST121 author scopes are pending; no tests may execute')
    if not all((EXPECTED_NATIVE_CHANGES, EXPECTED_REPOSITORY_CHANGES, NEW_PATHS, CASES, CORE_MODULES)):
        raise ValueError('TEST121 source/method inventory is empty')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or any(not row[3] for row in CASES):
        raise ValueError('TEST121 empty or duplicate selected native scope')
    if MAC_CASE_GROUPS != ():
        raise ValueError('TEST121 declares no new Runtime/Mac boundary cases')


def native_inventory(old, current):
    """Check the complete sealed inventory before any selected C tests run."""
    changed = {name for name in set(old)&set(current) if old[name] != current[name]}
    added = set(current)-set(old)
    if (set(old)-set(current) or len(old) != 37 or len(current) != 37+len(EXPECTED_NATIVE_ADDITIONS)
            or changed != set(EXPECTED_NATIVE_CHANGES) or added != set(EXPECTED_NATIVE_ADDITIONS)):
        raise ValueError('TEST121 exact native changed/added inventory differs')
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
        raise ValueError('TEST121 installed source/API/capability identity differs')
    pinned_bytes(driver, 'patches/loopctrl/apply_ngg2.py', code)
    spec = importlib.util.spec_from_file_location('test121_addition_roots', driver/'patches/loopctrl/apply_ngg2.py')
    applier = importlib.util.module_from_spec(spec); spec.loader.exec_module(applier)
    compile_binding = {}
    for name, row in manifest['additions'].items():
        source = applier.addition_source(driver/'patches/loopctrl/ngg2', name, row)
        logical = source.relative_to(driver).as_posix(); digest = sha(pinned_bytes(driver, logical, code))
        if digest != current[name] or sha((upstream/name).read_bytes()) != digest:
            raise ValueError('TEST121 driver compile addition differs from sealed source: '+logical)
        compile_binding[logical] = dict(native_path=name, driver_sha256=digest, sealed_sha256=digest)
    baseline = {p.decode() for p in git(driver, 'ls-tree', '-r', '--name-only', '-z', NATIVE_BASELINE).split(b'\0') if p}
    differences = {p.decode() for p in git(driver, 'diff', '--no-renames', '--name-only', '-z', NATIVE_BASELINE, code, '--').split(b'\0') if p}
    existing = {p for p in differences&baseline if not p.startswith('docs/')}
    new = {p for p in differences-baseline if not p.startswith('docs/')}
    if existing != set(EXPECTED_REPOSITORY_CHANGES) or new != set(NEW_PATHS):
        raise ValueError('TEST121 exact repository changed/new source paths differ')
    if git(driver, 'diff', '--no-ext-diff', '--name-only', code, '--', 'tests', 'necroprobe',
            'tools/ring_native', 'legacy/r12', 'patches/loopctrl', '.github/workflows/loopctrl-geometry.yml',
            'test_116.sh', 'test_117.sh', 'test_118.sh', 'test_119.sh', 'test_120.sh', 'test_121.sh').strip():
        raise ValueError('TEST121 working source differs from pinned CODE')
    ring_path = 'necroprobe/ring_native_manifest.json'; ring_raw = pinned_bytes(driver, ring_path, code)
    if ring_raw != git(driver, 'show', NATIVE_BASELINE+':'+ring_path):
        raise ValueError('TEST121 canonical Ring manifest changed')
    ring = json.loads(ring_raw); r12 = sorted(p for p in baseline if p.startswith('legacy/r12/'))
    if len(ring['sources']) != 15 or len(r12) != 40:
        raise ValueError('TEST121 canonical/R12 source inventory differs')
    preserved = {}
    for name in (*ring['sources'], *r12, *PRESERVED_PATHS):
        data = pinned_bytes(driver, name, code)
        if data != git(driver, 'show', NATIVE_BASELINE+':'+name):
            raise ValueError('TEST121 preserved source changed: '+name)
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
    return suites


def run_scope(name, cases, output, evidence, *, receipt_name='test121-host-scope.json'):
    if type(receipt_name) is not str or receipt_name not in ('test121-host-scope.json', 'test121-python39-scope.json'):
        raise ValueError('TEST121 scope receipt name is not permitted')
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
        raise ValueError('TEST121 existing public POD ABI changed')
    output.mkdir(parents=True, exist_ok=True)
    evidence = dict(scope='TEST121 selected native/client boundary contracts', source_identity=sealed,
        production_source_binding=binding, abi_bytes=abi, device_test='not_run',
        excluded_legacy_methods=EXCLUDED_LEGACY_METHODS,
        not_run=['old Runtime/fault/world collections: not replayed; no new Runtime boundary changed',
            'iPhone reach rate, precision and speed acceptance'])
    for label, cases in suites:
        run_scope(label, cases, output, evidence)
    selector = importlib.import_module('test_device_ci121')
    run_scope('test121-selector', unittest.defaultTestLoader.loadTestsFromTestCase(selector.DeviceHostSelection121Tests), output, evidence)
    if verifier.inspect_native_sources(upstream, driver) != sealed or source_identity(driver, sealed, upstream) != binding:
        raise ValueError('TEST121 tests changed sealed source')
    reject_fixture_overrides(); evidence['sealed_sources_unchanged_after_tests'] = True
    (output/'test121-host-scope.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS TEST121 selected source-bound contracts; iPhone acceptance is separate')


if __name__ == '__main__':
    main()
