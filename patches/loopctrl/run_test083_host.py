"""Run TEST083 first-gold motion and partial-shop framing with exact related regressions.

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
    ('tests.test_native_outer_floor083', 'NativeOuterFloor083Tests', 'test083-outer-floor', frozenset({
        'test_each_floor_band_needs_real_colour_and_texture',
        'test_fixed_same_tile_bands_hud_and_invalid_alpha_are_not_bypassed',
        'test_full_colour_bounds_keep_warm_walls_out',
        'test_old_types_gate_and_merchandise_protection_take_precedence',
        'test_two_disjoint_current_floor_bands_recover_occluded_floor',
    }), True),
    ('tests.test_native_shop_framing083', 'NativeShopFraming083Tests', 'test083-shop-framing', frozenset({
        'test_bottom_and_top_partial_items_choose_framing_floor_after_real_entry',
        'test_framing_ties_keep_short_routes_visits_lexical_and_immutable_inputs',
        'test_left_right_and_low_item_positions_follow_overflow_not_gold',
        'test_public_open_entry_partial_framing_then_visible_keeps_ticket_and_goods_priority',
        'test_unentered_invalid_unknown_visible_and_itemless_scenes_keep_old_contract',
        'test_unknown_blocked_item_or_protected_cells_never_form_a_framing_path',
    }), True),
    ('tests.test_native_first_gold083', 'NativeFirstGold083Tests', 'test083-first-gold', frozenset({
        'test_all_old_stones_noncollinear_dirt_and_unique_nine_remain_required',
        'test_first_gold_requires_clear_single_candidate_unknown_projection_and_safe_floor',
        'test_known_outputs_reverse_partial_stationary_and_two_cells_never_gain_unit_credit',
        'test_original_raw_finite_phase_and_strong_blur_limits_are_independent',
        'test_public_four_direction_first_gold_unit_keeps_opening_and_entry_uncredited',
    }), True),
    ('tests.test_native_motion074', 'NativeMotion074Tests', 'test083-related-motion074', frozenset({
        'test_passage_move_requires_all_stones_and_a_noncollinear_dirt_anchor',
    }), False),
    ('tests.test_native_motion075', 'NativeMotion075Tests', 'test083-related-motion075', frozenset({
        'test_full_kernel_rejects_hidden_changed_or_ui_dependencies',
        'test_independent_bands_weak_support_and_aliases_are_required',
    }), False),
    ('tests.test_native_passage_motion082', 'NativePassageMotion082Tests', 'test083-related-passage082', frozenset({
        'test_public_unique_corner_uses_blur_quality_and_separate_sharp_discrimination',
        'test_raw_and_both_independent_phase_require_finite_same_unit_and_original_gap',
        'test_scope_requires_clear_floor_no_gold_items_protection_and_old_endpoints',
    }), False),
    ('tests.test_native_side_gate081', 'NativeSideGate081Tests', 'test083-related-side081', frozenset({
        'test_public_four_direction_side_gate_unit_keeps_next_navigation_unentered',
    }), False),
    ('tests.test_native_navigation', 'NativeNavigationTests', 'test083-related-navigation', frozenset({
        'test_entrance_retains_gold_but_forbids_retreat',
    }), False),
    ('tests.test_native_shop071', 'NativeShop071Tests', 'test083-related-shop071', frozenset({
        'test_unknown_entry_synth_never_reuses_the_quiet_permission',
        'test_verified_open_entry_keeps_original_ticket_for_shielded_floor_dirt_flicker',
    }), False),
    ('tests.test_native_open_entry077', 'NativeOpenEntry077Tests', 'test083-related-entry077', frozenset({
        'test_geometry_old_gold_and_protected_material_changes_cannot_use_reveal',
        'test_interior_partial_reveals_continue_after_verified_entry_and_next_step',
        'test_original_deadline_prefix_goods_and_control_priority_remain',
    }), False),
    ('tests.test_native_controller', 'NativeControllerTests', 'test083-related-abi', frozenset({
        'test_scene_detail_query_is_bounded_and_leaves_existing_abi_unchanged',
    }), False),
    ('tests.test_native_materials082', 'NativeMaterials082Tests', 'test083-related-materials082', frozenset({
        'test_bright_requires_disjoint_texture_and_bounded_colour',
        'test_partial_requires_current_observed_floor_not_darkness_or_wall',
        'test_stone_requires_disjoint_witnesses_and_original_red_green_guards',
    }), False),
    ('tests.test_native_perception', 'NativePerceptionTests', 'test083-related-palette', frozenset({
        'test_floor_quantization_integer_band_boundaries',
        'test_synthetic_goods_unknown_partial_and_exact_counts',
    }), False),
    ('tests.test_native_icon066', 'NativeIcon066Tests', 'test083-related-hud', frozenset({
        'test_fragmented_icon_does_not_replace_other_hud_or_menu_guards',
    }), False),
)

CLIENT_CASES = (
    ('tests.test_native_publication069', 'Publication069Tests', 'test083-publication', frozenset({
        'test_missing_png_or_incomplete_cursor_cannot_be_published_or_start_fresh',
    }), False),
)

PACKAGE_CASES = ()

CORE_MODULES = ('tests.test_native_outer_floor083', 'tests.test_native_shop_framing083', 'tests.test_native_first_gold083', 'tests.test_native_motion074', 'tests.test_native_motion075', 'tests.test_native_passage_motion082', 'tests.test_native_side_gate081', 'tests.test_native_navigation', 'tests.test_native_shop071', 'tests.test_native_open_entry077', 'tests.test_native_controller', 'tests.test_native_materials082', 'tests.test_native_perception', 'tests.test_native_icon066', 'tests.test_native_recovery', 'tests.test_native_observation072', 'tests.test_native_motion067', 'tests.test_native_blocked067', 'test_native_perception', 'tests.test_native_beat', 'tests.test_beat_sync')
NATIVE_BASELINE = '3db9d9d244084f4fcc95637717f9cb073b57571d'
RETAINED_RUNTIME_SHA256 = '048a462811edabbef4544b2b83ffaadcedbdc654d8675fad4143a6432bc299da'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Perception.c', 'LoopCtrlUITests/NG2Navigation.c'}
CORE_CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.validation', 'necroprobe.protocol')
CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.test083', 'necroprobe.validation', 'necroprobe.protocol')
FIXTURE_OVERRIDE_PREFIXES = ('NECRO_TEST063_BASELINE_', 'NECRO_TEST071_BASELINE_', 'NECRO_TEST072_BASELINE_', 'NECRO_TEST074_BASELINE_', 'NECRO_TEST075_BASELINE_', 'NECRO_TEST076_BASELINE_', 'NECRO_TEST077_BASELINE_', 'NECRO_TEST078_BASELINE_', 'NECRO_TEST079_BASELINE_', 'NECRO_TEST080_BASELINE_', 'NECRO_TEST081_BASELINE_', 'NECRO_TEST082_BASELINE_', 'NECRO_TEST083_BASELINE_', 'NECRO_TEST083_FRAMING_BASELINE_')

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
        if name != 'necroprobe.test083' and raw != subprocess.check_output(
                ['git', 'show', NATIVE_BASELINE+':'+relative], cwd=driver):
            raise ValueError('unchanged TEST083 client source differs from the baseline: '+name)
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
    entry = importlib.import_module('necroprobe.test083')
    if publication.native is not native:
        raise ValueError('production publication wrapper is not bound to the actual driver client')
    if entry.device_main is not publication.main:
        raise ValueError('TEST083 entry is not bound to the actual driver publication wrapper')
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
    (output/'test083-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
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
        raise ValueError('TEST083 sealed source identity is not installed')
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'], cwd=driver, text=True))
    baseline_sources = {name: row['patched_sha256'] for name, row in baseline['files'].items()}
    baseline_sources.update({name: row['sha256'] for name, row in baseline['additions'].items()})
    current_sources = before['native_source_sha256']
    changed = {name for name in current_sources if current_sources[name] != baseline_sources.get(name)}
    if set(current_sources) != set(baseline_sources) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('TEST083 native change scope differs')
    native_change_scope = {'baseline': NATIVE_BASELINE, 'changed_sources': sorted(changed),
                           'unchanged_sources': len(current_sources)-len(changed)}
    if current_sources['LoopCtrlUITests/NG2Runtime.swift'] != RETAINED_RUNTIME_SHA256:
        raise ValueError('TEST083 retained Runtime source changed')
    client_before = client_source_identity(driver)
    suites = native_suites(upstream) + client_suites() + package_suites()
    selected_cases(case for _label, cases in suites for case in cases)
    fixture = importlib.import_module('tests.test_native_controller')
    abi = {name: ctypes.sizeof(getattr(fixture, name))
           for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    if abi != {'Scene': 23864, 'Status': 192, 'Event': 128, 'MotionWait': 48, 'RecoveryStatus': 456}:
        raise ValueError('native ABI layout changed')
    record = {'scope': 'TEST083 original-pixel floor, partial-shop framing and first-gold displacement; device feedback first',
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
              'selection_reasons': {'test083-outer-floor': 'independent original-pixel floor bands may restore only old DIRT, with all750 actual dependencies and old goods protection', 'test083-shop-framing': 'after verified entry, reachable observed floor may strictly reduce partial ITEM hull overflow without entry or goods credit', 'test083-first-gold': 'only an UNKNOWN old motion at the first clear-to-single-gold reveal may combine the existing independent finite proofs', 'test083-publication': 'the new entry inherits the unchanged complete-evidence ZIP gate; missing images or cursors cannot publish or start anew', 'test083-related-motion074': 'all old STONE anchors and noncollinear DIRT unique9 remain required', 'test083-related-motion075': 'all21 original kernel dependencies remain observed and outside UI; independent phase/support/alias bounds remain unchanged', 'test083-related-passage082': 'existing finite raw/phase gates are not broadened; existing both-CLEAR scope remains separate from new first-gold proof; B2 known corner result is retained', 'test083-related-side081': 'previous singleton reveal gives no entry credit', 'test083-related-navigation': '全4入口の既半平面/後退禁止・invalid入口を保持。A2はそのcopy後だけで動く。', 'test083-related-shop071': '4方向の既閉扉→開通→PARTIAL初進入を同ticket/元clockのまま保持。入口前framingを混入させない。; UNKNOWN synth state4後、新framing/hint観測でも再送・追加MOVE・cleanupを作らない。', 'test083-related-entry077': '実入店後の旧PARTIAL/GOLD-reveal継続。後方ITEMを元sourceでなく入口mask後から読むscopeも保つ。; 旧金消失/near/STONE/FLOOR/bracket/route/protected変化に新frame目的から権限を足さない。; 旧PARTIAL ticketの期限等号/+1、stable/prefix、VISIBLE/control優先、UNKNOWN motion拒否を保持。', 'test083-related-abi': '既Scene23864/Status192/Event128/SceneChange80/Detail144と診断getter境界を同codeで確認。', 'test083-related-materials082': 'old bright disjoint texture, colour and black-entry requirements remain unchanged; old partial proof never invents floor from unknown or darkness; old stone colour, red-green and texture guards remain intact', 'test083-related-palette': 'old palette, flat, gold-first and HUD quantization boundaries remain intact; original visible/partial goods and protection authority remains unchanged', 'test083-related-hud': 'new floor pixels never replace non-FLOOR, menu or fragmented HUD guards'}}
    for label, cases in suites:
        run_scope(label, cases, output, record)
    # Workflow and selection changes have their own small unit set, without
    # automatically discovering the historical package/Swift fixture suite.
    for module_name, classes in (('test_device_ci083', ('DeviceHostSelection083Tests',)),):
        module = importlib.import_module(module_name)
        cases = [case for name in classes for case in
                 unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module, name))]
        run_scope('test083-'+module_name, cases, output, record)
    if verifier.inspect_native_sources(upstream, driver) != before:
        raise ValueError('selected tests changed sealed production source')
    reject_fixture_overrides()
    if client_source_identity(driver) != client_before:
        raise ValueError('selected tests changed the pinned production client')
    record['sealed_sources_unchanged_after_tests'] = True
    record['client_source_unchanged_after_tests'] = True
    record['manifest_sha256'] = hashlib.sha256((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes()).hexdigest()
    (output/'test083-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
    print('PASS TEST083 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
