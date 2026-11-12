"""Run TEST086 corner-vantage and single-gold unit proofs with exact related regressions.

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


NATIVE_CASES = (('tests.test_native_corner_vantage086', 'NativeCornerVantage086Tests', 'test086-corner-vantage', frozenset({'test_scene_guards_and_all_original_ten_mouth_branches_stay_unchanged', 'test_vantage_requires_observed_shortest_three_step_route_and_clear_crosses', 'test_only_four_fixed_upper_left_corners_gain_the_new_hypothesis', 'test_observed_mouth_outside_two_walls_and_unknown_inboard_are_all_required', 'test_fixed_world_mouth_approaches_only_floor_and_holds_until_a_new_observed_route', 'test_unknown_inboard_keeps_observed_corner_candidate_for_safe_vantage'}), True), ('tests.test_native_single_gold086', 'NativeSingleGold086Tests', 'test086-single-gold-unit', frozenset({'test_public_controller_credits_only_one_qualified_post_ack_unit_and_goods_has_priority', 'test_raw_all73_phase_unit_and_both_strong_planes_keep_their_original_boundaries', 'test_complete_old_stones_dirt_support_noncollinearity_and_unique_nine_are_required', 'test_scope_gold_projection_endpoints_global_materials_and_known_results_remain_separate', 'test_axis_independence_all73_competition_and_blur_dependency_closure_are_required', 'test_public_four_directions_retained_single_gold_unit_requires_independent_old15_unknown_proof'}), True), ('tests.test_native_supported_mouth084', 'NativeSupportedMouth084Tests', 'test086-related-mouth084', frozenset({'test_old_two_wall_and_shadowed_mouth_masks_and_source_bytes_are_preserved', 'test_missing_flank_needs_outside_floor_and_three_current_walls', 'test_observed_outside_floor_with_one_unknown_flank_selects_fixed_upper_left_mouths', 'test_only_current_safe_floor_paths_authorize_approach', 'test_gold_goods_invalid_scenes_and_ordinary_right_down_exits_stay_out'}), False), ('tests.test_native_passage_navigation072', 'NativePassageNavigation072Tests', 'test086-related-navigation072', frozenset({'test_candidate_bits_cover_annotated_families_and_multiple_mouths', 'test_shadowed_mouth_requires_outside_floor_and_wall_line_support', 'test_unknown_outside_uses_a_monotone_observed_vantage_then_new_view', 'test_chooser_rejects_unsafe_steps_invalid_world_targets_and_unreachable_floor'}), False), ('tests.test_native_passage072', 'NativePassage072Tests', 'test086-related-passage072', frozenset({'test_restart_never_extends_original_walk_equality_deadline', 'test_shadowed_outer_goal_waits_for_observed_floor_and_never_steps_unknown', 'test_gold_clear_passage_moves_on_observed_floor_instead_of_restarting', 'test_acknowledged_unknown_visual_motion_never_becomes_another_exploration_step'}), False), ('tests.test_native_first_gold083', 'NativeFirstGold083Tests', 'test086-related-gold083', frozenset({'test_public_four_direction_first_gold_unit_keeps_opening_and_entry_uncredited', 'test_known_outputs_reverse_partial_stationary_and_two_cells_never_gain_unit_credit'}), False), ('tests.test_native_passage_motion082', 'NativePassageMotion082Tests', 'test086-related-motion082', frozenset({'test_public_four_direction_terrain_blur_unit_keeps_next_navigation_unentered'}), False), ('tests.test_native_stationary_texture085', 'NativeStationaryTexture085Tests', 'test086-related-stationary085', frozenset({'test_public_clear_floor_zero_requires_independent_stationary_evidence', 'test_old_unit_tween_reverse_and_opening_outputs_are_never_overwritten'}), False), ('tests.test_native_controller', 'NativeControllerTests', 'test086-related-controller', frozenset({'test_scene_detail_query_is_bounded_and_leaves_existing_abi_unchanged', 'test_goods_during_unknown_visual_wait_hold_without_direction_retry', 'test_fresh_ack_earliest_attempts_and_opening_are_not_displacement'}), False))

CLIENT_CASES = (('tests.test_native_publication069', 'Publication069Tests', 'test086-publication', frozenset({'test_missing_png_or_incomplete_cursor_cannot_be_published_or_start_fresh'}), False),)

PACKAGE_CASES = ()

CORE_MODULES = ('tests.test_native_beat', 'tests.test_native_blocked067', 'tests.test_native_controller', 'tests.test_native_corner_vantage086', 'tests.test_native_first_gold083', 'tests.test_native_motion067', 'tests.test_native_navigation', 'tests.test_native_passage072', 'tests.test_native_passage_motion082', 'tests.test_native_passage_navigation072', 'tests.test_native_passage_unsent076', 'tests.test_native_perception', 'tests.test_native_recovery', 'tests.test_native_single_gold086', 'tests.test_native_stationary_texture085', 'tests.test_native_supported_mouth084')
NATIVE_BASELINE = '843d401ecaff22607063bd4fad744aefc8ec51f5'
RETAINED_RUNTIME_SHA256 = '048a462811edabbef4544b2b83ffaadcedbdc654d8675fad4143a6432bc299da'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Navigation.c'}
CORE_CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.validation', 'necroprobe.protocol')
CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.test086', 'necroprobe.validation', 'necroprobe.protocol')
FIXTURE_OVERRIDE_PREFIXES = ('NECRO_TEST063_BASELINE_', 'NECRO_TEST071_BASELINE_', 'NECRO_TEST072_BASELINE_', 'NECRO_TEST074_BASELINE_', 'NECRO_TEST075_BASELINE_', 'NECRO_TEST076_BASELINE_', 'NECRO_TEST077_BASELINE_', 'NECRO_TEST078_BASELINE_', 'NECRO_TEST079_BASELINE_', 'NECRO_TEST080_BASELINE_', 'NECRO_TEST081_BASELINE_', 'NECRO_TEST082_BASELINE_', 'NECRO_TEST083_BASELINE_', 'NECRO_TEST083_FRAMING_BASELINE_', 'NECRO_TEST084_BASELINE_', 'NECRO_TEST084_NONFLOOR_', 'NECRO_TEST085_PROOF_', 'NECRO_TEST085_STATIONARY_', 'NECRO_TEST086_')

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
        if name != 'necroprobe.test086' and raw != subprocess.check_output(
                ['git', 'show', NATIVE_BASELINE+':'+relative], cwd=driver):
            raise ValueError('unchanged TEST086 client source differs from the baseline: '+name)
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
    entry = importlib.import_module('necroprobe.test086')
    if publication.native is not native:
        raise ValueError('production publication wrapper is not bound to the actual driver client')
    if entry.device_main is not publication.main:
        raise ValueError('TEST086 entry is not bound to the actual driver publication wrapper')
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
    (output/'test086-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
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
        raise ValueError('TEST086 sealed source identity is not installed')
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'], cwd=driver, text=True))
    baseline_sources = {name: row['patched_sha256'] for name, row in baseline['files'].items()}
    baseline_sources.update({name: row['sha256'] for name, row in baseline['additions'].items()})
    current_sources = before['native_source_sha256']
    changed = {name for name in current_sources if current_sources[name] != baseline_sources.get(name)}
    if set(current_sources) != set(baseline_sources) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('TEST086 native change scope differs')
    native_change_scope = {'baseline': NATIVE_BASELINE, 'changed_sources': sorted(changed),
                           'unchanged_sources': len(current_sources)-len(changed)}
    if current_sources['LoopCtrlUITests/NG2Runtime.swift'] != RETAINED_RUNTIME_SHA256:
        raise ValueError('TEST086 retained Runtime source changed')
    client_before = client_source_identity(driver)
    suites = native_suites(upstream) + client_suites() + package_suites()
    selected_cases(case for _label, cases in suites for case in cases)
    fixture = importlib.import_module('tests.test_native_controller')
    abi = {name: ctypes.sizeof(getattr(fixture, name))
           for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    if abi != {'Scene': 23864, 'Status': 192, 'Event': 128, 'MotionWait': 48, 'RecoveryStatus': 456}:
        raise ValueError('native ABI layout changed')
    record = {'scope': 'TEST086 observed corner vantage and independently proven retained-single-gold unit; device feedback first',
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
              'selection_reasons': {'test086-corner-vantage': 'only four observed fixed corner mouths with unknown inboard gain a shortest three-step observed-FLOOR vantage; UNKNOWN and original candidate branches stay unchanged', 'test086-single-gold-unit': 'a separate final unit proof preserves exactly one visible GOLD and requires original finite raw73, phase, all old terrain, independent world/axis support bands and all73 competition; original15 stages remain first', 'test086-related-mouth084': 'previous one-unknown-flank fixed mouths, wall support, observed safe routes and gold/goods/ordinary-exit guards remain unchanged', 'test086-related-navigation072': 'original ten-bit families, shadowed mouth wall support, monotone observed vantage and unsafe or unreachable route rejection remain unchanged', 'test086-related-passage072': 'public Controller continues observed passage motion and waits at shadowed UNKNOWN; acknowledged unknown never retries and restart cannot extend original walk budget', 'test086-related-gold083': 'old first-gold public unit proof and known reverse/partial/stationary/two-cell outputs stay prior and independent', 'test086-related-motion082': 'old no-gold terrain blur public unit proof remains separate and does not credit gate entry', 'test086-related-stationary085': 'old zero-only independent proof and old known unit/tween/reverse/opening results remain unchanged', 'test086-related-controller': 'original post-ACK earliest/attempt/opening rules, goods priority without direction retry, and bounded direct ABI/query remain authoritative', 'test086-publication': 'new entry reuses full-evidence ZIP publication; incomplete PNG/cursor data cannot publish or start fresh'}}
    for label, cases in suites:
        run_scope(label, cases, output, record)
    # Workflow and selection changes have their own small unit set, without
    # automatically discovering the historical package/Swift fixture suite.
    for module_name, classes in (('test_device_ci086', ('DeviceHostSelection086Tests',)),):
        module = importlib.import_module(module_name)
        cases = [case for name in classes for case in
                 unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module, name))]
        run_scope('test086-'+module_name, cases, output, record)
    if verifier.inspect_native_sources(upstream, driver) != before:
        raise ValueError('selected tests changed sealed production source')
    reject_fixture_overrides()
    if client_source_identity(driver) != client_before:
        raise ValueError('selected tests changed the pinned production client')
    record['sealed_sources_unchanged_after_tests'] = True
    record['client_source_unchanged_after_tests'] = True
    record['manifest_sha256'] = hashlib.sha256((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes()).hexdigest()
    (output/'test086-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
    print('PASS TEST086 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
