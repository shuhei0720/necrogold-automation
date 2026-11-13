"""TEST094 focused native-cycle units, sealed-source binding and explicit scope.

Procedural units test software contracts. Actual Swift callbacks/filesystem and
IPA compiler checks run in the Mac device lane; none proves iPhone acceptance.
"""
import argparse
import ctypes
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

NATIVE_BASELINE = '3e79c460840bf05fef0f49f5a10f39e09f2815cd'
SCOPE_FINALIZED = True
# Freeze this exact set after the final author inventories and seal are ready.
EXPECTED_NATIVE_CHANGES = frozenset({
    'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Controller.h',
    'LoopCtrlUITests/NG2Navigation.c', 'LoopCtrlUITests/NG2Runtime.swift',
    'LoopCtrlKit/RPCMethod.swift', 'LoopCtrlKit/JSONRPCServer.swift', 'project.yml',
    'LoopCtrlUITests/NG2Ring.c', 'LoopCtrlUITests/NG2Ring.h',
    'LoopCtrlUITests/NG2RingBank.h', 'LoopCtrlUITests/NG2RingCoverage.h',
    'LoopCtrlUITests/NG2CycleSpool.swift', 'LoopCtrlUITests/NG2CycleWire.swift',
    'LoopCtrlUITests/NG2CycleExport.swift',
    *('LoopCtrlUITests/NG2RingKernel/' + name for name in
      ('ring.h', 'features.h', 'word_features.h', 'feature_sha.h', 'observe.c', 'icon.c', 'word.c'))})
CASES = (('tests.test_native_ring094',
  'NativeRing094Tests',
  'test094-ring',
  frozenset({'test_direct_opaque_rgba_same_slot_target_and_raw_word_all_slots',
             'test_fast_upper_bounds_preserve_positive_and_explicitly_qualify_pruned_scores',
             'test_more_than_twelve_observed_sign_hypotheses_fail_instead_of_dropping_candidates',
             'test_negative_finalizer_rejects_missing_identity_foreign_row_and_any_candidate',
             'test_no_match_and_three_rows_never_prove_negative',
             'test_only_completed_observed_partial_without_a_positive_may_continue',
             'test_partial_icon_above_hud_is_retained_when_only_price_overlaps_hud',
             'test_partial_pixels_keep_single_icon_name_even_without_a_complete_row',
             'test_partial_visible_target_and_candidate_survive_missing_three_column_row',
             'test_partial_visible_target_is_retained_when_price_ink_is_occluded',
             'test_pixel_failure_cancellation_and_deadline_never_become_completed_unknown',
             'test_raw_aggregation_cannot_retain_stale_identity_or_coverage_witnesses',
             'test_round9_matches_python_at_binary64_thresholds_and_decimal_ties',
             'test_same_slot_icon_and_name_precedes_a_stronger_unpaired_icon'}),
  True),
 ('tests.test_native_ring_bank094',
  'NativeRingBank094Tests',
  'test094-bank',
  frozenset({'test_broken_frame_wrong_spacing_or_clipped_board_cannot_complete_coverage',
             'test_complete_container_shop_certifies_exposed_scope_without_judging_contents',
             'test_complete_coverage_certificate_joins_the_selected_row',
             'test_confirmed_closed_containers_are_distinct_ignored_evidence',
             'test_different_known_ring_requires_its_own_name_and_does_not_prove_target',
             'test_different_merchant_colours_and_hud_overlap_do_not_authenticate_layout',
             'test_extra_authenticated_shop_board_blocks_complete_coverage',
             'test_gold_continuation_outside_board_roi_is_not_a_closed_frame',
             'test_gold_frame_defines_the_board_when_lower_yellow_pixels_are_gold',
             'test_known_bank_identities_require_independent_same_slot_names_and_icons',
             'test_local_disconnected_foreground_23_is_allowed_and_24_is_held',
             'test_long_product_name_occluding_a_board_edge_keeps_coverage_incomplete',
             'test_missing_or_wrong_slot_name_uncatalogued_object_and_unseen_end_hold',
             'test_nameless_blob_or_damaged_container_shape_is_not_ignored',
             'test_off_row_partial_target_or_candidate_vetoes_complete_main_shop',
             'test_separated_small_foreground_specks_do_not_create_a_fourth_item',
             'test_target_template_and_ringlike_icon_keep_target_or_candidate',
             'test_torch_word_inside_a_longer_name_cannot_identify_the_torch',
             'test_two_complete_named_shop_sets_are_negative',
             'test_two_matching_bank_ids_are_unknown_instead_of_first_id_winning'}),
  True),
 ('tests.test_native_cycle094',
  'NativeCycle094Tests',
  'test094-cycle',
  frozenset({'test_ack_and_real_changed_floor_wait_for_linked_outcome_durability',
             'test_actual_closed_container_footprints_fit_only_the_ignored_policy_strip',
             'test_container_extension_rejects_one_pixel_overflow_cross_slot_and_unknown',
             'test_deadline_and_cancelled_worker_results_are_inert',
             'test_goods_hold_keeps_cycle_open_after_real_pause_observation',
             'test_ignored_closed_container_is_explicit_policy_witness',
             'test_inflight_goods_credit_real_move_once_and_keep_unknown_motion_held',
             'test_late_old_level_writer_failure_cannot_change_new_search',
             'test_negative_authority_needs_durable_checkpoint_and_new_pause_source',
             'test_negative_missing_or_conflicting_witness_is_held',
             'test_negative_restart_begin_rechecks_cumulative_walk_deadline_after_writer_wait',
             'test_partial_candidate_survives_queued_full_goods_unknown_or_negative',
             'test_partial_credit_unproven_change_retires_new_move_and_holds',
             'test_partial_observe_more_uses_one_new_safe_move_without_reviving_old_ticket',
             'test_partial_safe_flag_without_observed_slot_is_not_continuation_authority',
             'test_queued_full_frame_becomes_a_fresh_serial_job_after_safe_partial',
             'test_recorded_named_full_sprite_poses_use_finite_bank_search_not_presence_window',
             'test_restart_begin_requires_exact_durable_intent_and_fresh_pause',
             'test_restart_changed_floor_with_partial_goods_starts_new_bound_hold_after_outcome',
             'test_restart_changed_floor_with_visible_goods_starts_new_bound_hold_after_outcome',
             'test_search_restart_crossed_first_goods_waits_for_current_stable_prefix',
             'test_search_restart_first_partial_goods_drains_and_binds_new_level',
             'test_search_restart_first_visible_goods_drains_and_binds_new_level',
             'test_search_restart_unchanged_goods_holds_without_new_level_or_retry',
             'test_storage_failure_pauses_then_stops_without_fabricating_durability',
             'test_storage_failure_revokes_an_already_reserved_restart_before_begin',
             'test_target_candidate_and_unknown_keep_pause_without_restart',
             'test_two_shops_continue_and_fourth_shop_holds_with_cumulative_budget',
             'test_unknown_synth_freeze_survives_late_classifier_and_writer'}),
  True),
 ('tests.test_native_shadow_passage094',
  'NativeShadowPassage094Tests',
  'test094-shadow',
  frozenset({'test_black_gaps_other_sides_goods_gold_protection_and_invalid_scenes_fail_closed',
             'test_fixed_world_mouth_moves_only_on_observed_floor_then_holds',
             'test_four_dark_cells_and_observed_short_floor_vantage_are_required',
             'test_marked_shadow_shape_keeps_unknown_and_adds_only_fixed_upper_left_mouth',
             'test_original_ten_mouths_supported_mouths_and_corner_masks_remain_unchanged',
             'test_tall_brown_column_and_opposite_roof_wall_are_required'}),
  True),
 ('tests.test_native_cycle_client094',
  'CycleClient094Tests',
  'test094-client',
  frozenset({'test_ack_failure_retains_same_archive_and_retries_no_game_start',
             'test_authenticated_definitive_not_started_is_distinct_from_unknown_start',
             'test_cancel_after_durable_start_intent_never_posts_start',
             'test_changed_completed_archive_blocks_ack_and_preserves_destination',
             'test_changed_png_blocks_ack',
             'test_collection_recovers_all_records_and_batched_png_without_pixel_classifier',
             'test_durable_per_run_journal_survives_interruption_before_active_mirror',
             'test_envelope_requires_exact_schema_mode_profile_and_run',
             'test_fresh_session_starts_once_after_ready_and_keeps_heartbeat_before_terminal',
             'test_gameworker_drain_is_required_before_manifest',
             'test_interrupted_diagnostic_is_saved_but_never_claimed_normal_completion',
             'test_later_explicit_invocation_starts_new_id_only_after_prior_receipt_and_zip_verify',
             'test_malformed_not_started_error_cannot_clear_uncertain_input_intent',
             'test_late_terminal_assessment_is_reported_as_unadopted_not_unexecuted_or_negative',
             'test_manifest_hash_is_of_exact_utf8_not_python_reserialization',
             'test_manifest_registry_rejects_extra_fields_duplicate_ids_and_bool_lengths',
             'test_method_admission_rejects_oldprofile_unknownfields_and_arbitrary_input',
             'test_missing_frame_metadata_never_resolves_or_publishes',
             'test_missing_header_is_publishable_only_as_explicit_interrupted_diagnostic',
             'test_native_pending_deadline_and_cancellation_do_not_reissue_after_expiry',
             'test_native_unpublished_id_is_recovered_without_new_start',
             'test_new_profile_has_an_explicit_admitted_client_not_old_profile_fallback',
             'test_notification_preflight_failure_can_start_on_next_explicit_invocation',
             'test_only_authenticated_dedicated_pending_code_is_automatically_polled',
             'test_permission_denied_never_sends_start',
             'test_png_all_chunks_crc_and_rgba_geometry_are_verified',
             'test_published_ack_occurs_only_after_full_crc_sha_zip_and_destination_copy',
             'test_real_encrypted_pending_reply_is_polled_but_bad_mac_is_not',
             'test_return_zip_deflates_stored_recovery_png_and_preserves_all_bytes',
             'test_same_offset_retry_preserves_and_compares_uncheckpointed_suffix',
             'test_schema_requires_current_api_new_capability_and_integer_protocol',
             'test_start_admission_guard_runs_after_crypto_before_transport',
             'test_started_unknown_frozen_terminal_remains_exportable_without_new_input',
             'test_uncertain_start_is_sent_once_and_next_invocation_only_recovers_same_id'}),
  True),
 ('tests.test_native_supported_mouth084',
  'NativeSupportedMouth084Tests',
  'test094-related-nav084',
  frozenset({'test_gold_goods_invalid_scenes_and_ordinary_right_down_exits_stay_out',
             'test_missing_flank_needs_outside_floor_and_three_current_walls',
             'test_observed_outside_floor_with_one_unknown_flank_selects_fixed_upper_left_mouths',
             'test_old_two_wall_and_shadowed_mouth_masks_and_source_bytes_are_preserved',
             'test_only_current_safe_floor_paths_authorize_approach'}),
  True),
 ('tests.test_native_corner_vantage086',
  'NativeCornerVantage086Tests',
  'test094-related-nav086',
  frozenset({'test_fixed_world_mouth_approaches_only_floor_and_holds_until_a_new_observed_route',
             'test_observed_mouth_outside_two_walls_and_unknown_inboard_are_all_required',
             'test_only_four_fixed_upper_left_corners_gain_the_new_hypothesis',
             'test_scene_guards_and_all_original_ten_mouth_branches_stay_unchanged',
             'test_unknown_inboard_keeps_observed_corner_candidate_for_safe_vantage',
             'test_vantage_requires_observed_shortest_three_step_route_and_clear_crosses'}),
  True),
 ('tests.test_native_passage_navigation072',
  'NativePassageNavigation072Tests',
  'test094-related-nav072',
  frozenset({'test_candidate_bits_cover_annotated_families_and_multiple_mouths',
             'test_chooser_rejects_unsafe_steps_invalid_world_targets_and_unreachable_floor',
             'test_fixed_second_mouth_remains_reachable_across_the_initial_room',
             'test_fixed_world_mouth_reaches_one_outside_with_real_floor_steps',
             'test_invalid_start_gold_goods_ordinary_exits_and_protection_do_not_explore',
             'test_shadowed_mouth_requires_outside_floor_and_wall_line_support',
             'test_shop_chooser_stays_separate_and_null_outputs_fail_closed',
             'test_unknown_outside_uses_a_monotone_observed_vantage_then_new_view'}),
  True),
 ('tests.test_native_opened_entry093',
  'NativeOpenedEntry093Tests',
  'test094-related-opened-entry',
  frozenset({'test_expired_partial_entry_reacquires_independent_future_permission',
             'test_goods_cancel_unknown_ack_prefix_and_original_budgets_stay_authoritative',
             'test_observed_inner_floor_after_opening_revalidates_in_four_directions',
             'test_original_ticket_windows_epochs_and_actual_begin_boundaries_are_frozen',
             'test_projected_top_goods_growth_and_shrink_use_latest_separate_ticket',
             'test_projection_surface_gold_and_motion_counterexamples_reject_revalidation'}),
  True),
 ('tests.test_native_clipped_entry081',
  'NativeClippedEntry081Tests',
  'test094-related-clipped081',
  frozenset({'test_clipped_partial_goods_preserve_original_up_entry_then_real_move_and_goods_hold',
             'test_new_protection_nonedge_items_gold_or_near_changes_cannot_use_quarantine',
             'test_source_mask_and_top_gold_quarantine_survive_mask_zero_return'}),
  False),
 ('tests.test_native_shop071',
  'NativeShop071Tests',
  'test094-related-shop071',
  frozenset({'test_exception_does_not_allow_other_local_cells_materials_or_missing_open_ack',
             'test_verified_open_entry_keeps_original_ticket_for_shielded_floor_dirt_flicker'}),
  False),
 ('tests.test_native_open_entry077',
  'NativeOpenEntry077Tests',
  'test094-related-open077',
  frozenset({'test_accepted_new_gold_cannot_disappear_or_shift_within_same_ticket',
             'test_opened_entry_reveal_preserves_ticket_then_enters_on_original_beat'}),
  False),
 ('tests.test_native_device065',
  'NativeDevice065Tests',
  'test094-related-expiry065',
  frozenset({'test_pending_same_and_fresh_expiry_reacquire_without_rewriting_retired_ticket'}),
  False),
 ('tests.test_ring_backend089',
  'RingBackend089Tests',
  'test094-related-ring089',
  frozenset({'test_observed_icon_and_name_keep_the_result_without_python_pixel_loops',
             'test_visible_ring_with_clipped_name_stays_candidate'}),
  False),
 ('tests.test_ring_accuracy089',
  'RingAccuracy089Tests',
  'test094-related-ring-accuracy089',
  frozenset({'test_readable_translated_dimmed_same_slot_targets_and_partial_name_candidate'}),
  True))

# Import every shared C fixture before rebinding its CORE, including direct-name
# aliases used by historical tests. Do not import an old selector's execution.
CORE_MODULES = (
    'tests.test_native_beat', 'tests.test_native_blocked067', 'tests.test_native_controller',
    'tests.test_native_navigation', 'tests.test_native_perception', 'tests.test_native_recovery',
    'tests.test_native_motion067', 'tests.test_native_passage_motion082',
    'tests.test_native_first_gold083', 'tests.test_native_single_gold086',
    'tests.test_native_stationary_texture085', 'tests.test_native_passage072')
RETAINED_PATHS = (
    'necroprobe/native_walk.py', 'necroprobe/test069.py', 'necroprobe/target_assessment.py',
    'necroprobe/ring_native.py', 'necroprobe/ring_early.py', 'necroprobe/ring_status.py',
    'necroprobe/protocol.py', 'necroprobe/validation.py', 'necroprobe/test093.py', 'test_093.sh')
NEW_PRODUCT_PATHS = (
    'necroprobe/native_cycle.py', 'necroprobe/cycle_publication.py', 'necroprobe/test094.py',
    'test_094.sh', 'necroprobe/non_target_features094.json', 'necroprobe/goldshop_auth_features094.json')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(driver, *args):
    return subprocess.check_output(['git', *args], cwd=driver)


def pinned_bytes(driver, path, code):
    raw = (driver / path).read_bytes()
    if raw != git(driver, 'show', code + ':' + path):
        raise ValueError('source differs from pinned commit: ' + path)
    return raw


def reject_fixture_overrides():
    present = sorted(name for name in os.environ if name == 'BASELINE_NAV'
                     or name.startswith(('NECRO_TEST', 'NECRO094_')))
    if present:
        raise ValueError('sealed fixture overrides are forbidden: ' + ', '.join(present))


def selected_cases(cases):
    cases = list(cases)
    if not cases or len({case.id() for case in cases}) != len(cases):
        raise ValueError('missing or duplicate device cases')
    return cases


def method_cases(case_type, methods, *, exact=False):
    available = set(unittest.defaultTestLoader.getTestCaseNames(case_type))
    if not methods or not methods <= available or (exact and available != set(methods)):
        raise ValueError('device method inventory changed: ' + case_type.__name__)
    return selected_cases(case_type(method) for method in sorted(methods))


def ensure_scope():
    if not SCOPE_FINALIZED or not CASES:
        raise ValueError('TEST094 author inventories are not frozen')
    labels = [row[2] for row in CASES]
    if len(labels) != len(set(labels)) or not all(row[3] for row in CASES):
        raise ValueError('TEST094 scope is empty or duplicated')
    if not any(row[0] == 'tests.test_native_cycle094' and row[4] for row in CASES):
        raise ValueError('TEST094 new cycle scope is missing')


def native_suites(upstream):
    reject_fixture_overrides()
    names = tuple(dict.fromkeys((*CORE_MODULES, *(row[0] for row in CASES))))
    modules = {name: importlib.import_module(name) for name in names}
    for module in modules.values():
        module.CORE = upstream / 'LoopCtrlUITests'
    for name in names:
        alias = sys.modules.get(name.rsplit('.', 1)[-1])
        if alias is not None:
            alias.CORE = upstream / 'LoopCtrlUITests'
    reject_fixture_overrides()
    return [(label, method_cases(getattr(modules[name], klass), methods, exact=exact))
            for name, klass, label, methods, exact in CASES]


def addition_identity(driver, destination, spec):
    root = spec.get('source_root', 'ngg2')
    source = spec['source']
    if root not in ('ngg2', 'ring_native') or not isinstance(source, str):
        raise ValueError('addition source root')
    relative = Path(source)
    target = Path(destination)
    if relative.name != source or target.is_absolute() or '..' in target.parts:
        raise ValueError('addition source path')
    if root == 'ring_native':
        allowed = {'ring.h', 'features.h', 'word_features.h', 'feature_sha.h', 'observe.c', 'icon.c', 'word.c'}
        if source not in allowed or destination != 'LoopCtrlUITests/NG2RingKernel/' + source:
            raise ValueError('addition canonical destination')
        directory = driver / 'tools/ring_native'
    else:
        expected = ('Tests/LoopCtrlKitTests/NG2RPCContractsTests.swift' if source == 'NG2RPCContractsTests.swift'
                    else 'LoopCtrlUITests/' + source)
        if destination != expected:
            raise ValueError('addition native destination')
        if not source.startswith('NG2') or Path(source).suffix not in ('.swift', '.c', '.h', '.m'):
            raise ValueError('addition native name')
        directory = driver / 'patches/loopctrl/ngg2'
    if directory.is_symlink() or not directory.is_dir() or (directory / source).is_symlink():
        raise ValueError('addition symlink')
    digest = sha((directory / source).read_bytes())
    if digest != spec['sha256']:
        raise ValueError('addition hash: ' + destination)
    return digest


def retained_identity(raw, baseline, digest=None):
    if raw != baseline or (digest is not None and sha(raw) != digest):
        raise ValueError('retained source bytes changed')
    return sha(raw)


def source_identity(driver, sealed):
    code = git(driver, 'rev-parse', 'HEAD').decode().strip()
    retained = {}
    for path in RETAINED_PATHS:
        raw = pinned_bytes(driver, path, code)
        retained[path] = retained_identity(raw, git(driver, 'show', NATIVE_BASELINE + ':' + path))
    manifest = json.loads(pinned_bytes(driver, 'patches/loopctrl/ngg2-manifest.json', code))
    before = json.loads(git(driver, 'show', NATIVE_BASELINE + ':patches/loopctrl/ngg2-manifest.json'))
    old = {name: row['patched_sha256'] for name, row in before['files'].items()}
    old.update({name: row['sha256'] for name, row in before['additions'].items()})
    current = sealed['native_source_sha256']
    changed = {name for name in current if current[name] != old.get(name)}
    if set(old) - set(current) or changed != set(EXPECTED_NATIVE_CHANGES):
        raise ValueError('unexpected TEST094 native change scope: ' + repr(sorted(changed)))
    if (sealed['api_version'], sealed['client_capability']) != ('1.98.16-ngg2', 'necrogold_native_v15'):
        raise ValueError('legacy global API or capability changed')
    repository = {}
    for name, spec in manifest['additions'].items():
        digest = addition_identity(driver, name, spec)
        directory = 'tools/ring_native/' if spec.get('source_root') == 'ring_native' else 'patches/loopctrl/ngg2/'
        pinned_bytes(driver, directory + spec['source'], code)
        if current[name] != digest:
            raise ValueError('repository addition differs from IPA source: ' + name)
        repository[name] = digest
    old_ring = json.loads(git(driver, 'show', NATIVE_BASELINE + ':necroprobe/ring_native_manifest.json'))
    ring = json.loads(pinned_bytes(driver, 'necroprobe/ring_native_manifest.json', code))
    if ring != old_ring or len(ring['sources']) != 15:
        raise ValueError('canonical ring manifest changed')
    for path, digest in ring['sources'].items():
        raw = pinned_bytes(driver, path, code)
        retained_identity(raw, git(driver, 'show', NATIVE_BASELINE + ':' + path), digest)
    engine = pinned_bytes(driver, 'necroprobe/bin/ring-i386', code)
    if (len(engine) != 56088 or len(engine) != ring['binary_bytes'] or sha(engine) != ring['binary_sha256']
            or engine != git(driver, 'show', NATIVE_BASELINE + ':necroprobe/bin/ring-i386')):
        raise ValueError('canonical i386 engine changed')
    native = importlib.import_module('necroprobe.native_walk')
    if (native.REVISION, native.API_VERSION, native.CAPABILITY, native.PROFILE) != (
            'native-walk-v16', '1.98.16-ngg2', 'necrogold_native_v15', 'normal-1-1-evidence-v2'):
        raise ValueError('legacy client profile identity changed')
    patch = pinned_bytes(driver, 'patches/loopctrl/ngg2.patch', code).decode()
    if patch.count('"necrogold_native_cycle_v1"') != 1 or patch.count('RPCMethodDef(name: "necro_native_cycle"') != 1:
        raise ValueError('independent cycle capability or RPC registration missing')
    runtime = pinned_bytes(driver, 'patches/loopctrl/ngg2/NG2Runtime.swift', code).decode()
    if 'normal-1-1-cycle-v1' not in runtime or 'necro_native_cycle' not in runtime:
        raise ValueError('native cycle profile or method missing')
    products = {path: sha(pinned_bytes(driver, path, code)) for path in NEW_PRODUCT_PATHS}
    for module_name in ('necroprobe.native_cycle', 'necroprobe.cycle_publication', 'necroprobe.test094'):
        module = importlib.import_module(module_name)
        if Path(module.__file__).resolve() != driver / (module_name.replace('.', '/') + '.py'):
            raise ValueError('client import escaped pinned driver: ' + module_name)
    return dict(driver_commit=code, native_baseline=NATIVE_BASELINE, retained_source_sha256=retained,
                changed_native_sources=sorted(changed), repository_native_source_sha256=repository,
                ring_manifest=ring, new_product_sha256=products,
                direct_ring_compiler_binding='driver NG2Ring and canonical kernels; every source equals installed sealed bytes')


def run_scope(name, cases, output, evidence):
    cases = selected_cases(cases)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(cases))
    log = stream.getvalue()
    (output / (name + '.txt')).write_text(log)
    print(log, end='', flush=True)
    evidence[name] = dict(selected=[case.id() for case in cases], tests_run=result.testsRun,
                          failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
                          expected_failures=len(result.expectedFailures))
    (output / 'test094-host-scope.json').write_text(json.dumps(evidence, indent=2) + '\n')
    if result.testsRun != len(cases) or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise RuntimeError(name + ': every selected method must execute Green')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('driver', 'upstream', 'output'): parser.add_argument(name, type=Path)
    args = parser.parse_args()
    driver, upstream, output = (getattr(args, name).resolve() for name in ('driver', 'upstream', 'output'))
    ensure_scope(); output.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(driver), str(driver / 'tests'), str(driver / 'patches/loopctrl')]
    verifier = importlib.import_module('verify_package')
    before = verifier.inspect_native_sources(upstream, driver)
    source_before = source_identity(driver, before)
    suites = native_suites(upstream)
    selected_cases(case for _name, cases in suites for case in cases)
    fixture = importlib.import_module('tests.test_native_controller')
    abi = {name: ctypes.sizeof(getattr(fixture, name)) for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    if abi != dict(Scene=23864, Status=192, Event=128, MotionWait=48, RecoveryStatus=456):
        raise ValueError('legacy public native ABI changed')
    evidence = dict(scope='TEST094 native ring/cycle/client and related route/goods contracts',
                    source_identity=before, production_source_binding=source_before, abi_bytes=abi,
                    device_test='not_run',
                    not_run=['full historical Runtime/world/fault suites', 'private device replay corpus',
                             'iPhone reach rate, rare-target precision and human speed acceptance'])
    for name, cases in suites: run_scope(name, cases, output, evidence)
    selector = importlib.import_module('test_device_ci094')
    run_scope('test094-selector', unittest.defaultTestLoader.loadTestsFromTestCase(
        selector.DeviceHostSelection094Tests), output, evidence)
    if verifier.inspect_native_sources(upstream, driver) != before or source_identity(driver, before) != source_before:
        raise ValueError('selected tests changed production source')
    reject_fixture_overrides()
    evidence['sealed_sources_unchanged_after_tests'] = True
    evidence['manifest_sha256'] = sha((driver / 'patches/loopctrl/ngg2-manifest.json').read_bytes())
    (output / 'test094-host-scope.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print('PASS TEST094 selected contracts against exact sealed IPA sources')


if __name__ == '__main__': main()
