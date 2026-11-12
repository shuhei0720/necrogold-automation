"""Run TEST084 mouth/floor/icon changes and non-FLOOR diagnostics with exact related regressions.

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
    ('tests.test_native_shadow_floor084', 'NativeShadowFloor084Tests', 'test084-shadow-floor', frozenset({
        'test_black_entry_and_full_rgb_bounds_are_required',
        'test_black_entry_partial_floor_becomes_observed_mouth',
        'test_existing_materials_gate_goods_and_hud_keep_priority',
        'test_fixed_halves_require_95percent_black_and_90percent_visible_floor',
        'test_observed_floor_requires_original_colour_texture_and_median_r16',
    }), True),
    ('tests.test_native_supported_mouth084', 'NativeSupportedMouth084Tests', 'test084-supported-mouth', frozenset({
        'test_gold_goods_invalid_scenes_and_ordinary_right_down_exits_stay_out',
        'test_missing_flank_needs_outside_floor_and_three_current_walls',
        'test_observed_outside_floor_with_one_unknown_flank_selects_fixed_upper_left_mouths',
        'test_old_two_wall_and_shadowed_mouth_masks_and_source_bytes_are_preserved',
        'test_only_current_safe_floor_paths_authorize_approach',
    }), True),
    ('tests.test_native_icon084', 'NativeIcon084Tests', 'test084-nine-pixel-icon', frozenset({
        'test_nine_pixel_bar_fragments_retain_full_reference_floor',
        'test_nine_pixel_path_keeps_hud_menu_and_buffer_guards',
        'test_nine_pixel_path_keeps_intensity_neutrality_and_fixed_roi',
        'test_nine_pixel_path_rejects_missing_bars_white_and_short_glyphs',
        'test_public_rgba_goods_after_move_ack_latches_and_confirms_pause',
    }), True),
    ('tests.test_native_nonfloor_diagnostics084', 'NativeNonfloorDiagnostics084Tests', 'test084-nonfloor-diagnostics', frozenset({
        'test_ack_nonfloor_rejection_records_state_diff_without_motion_assessment',
        'test_nonfloor_trace_requires_current_acked_move_and_original_capture_bounds',
        'test_state_trace_preserves_deadlines_goods_priority_and_existing_cleanup',
    }), True),
    ('tests.test_native_materials082', 'NativeMaterials082Tests', 'test084-related-materials082', frozenset({
        'test_partial_observed_mouth_becomes_candidate_without_unknown_entry',
        'test_partial_requires_current_observed_floor_not_darkness_or_wall',
    }), False),
    ('tests.test_native_outer_floor083', 'NativeOuterFloor083Tests', 'test084-related-outer083', frozenset({
        'test_fixed_same_tile_bands_hud_and_invalid_alpha_are_not_bypassed',
        'test_old_types_gate_and_merchandise_protection_take_precedence',
    }), False),
    ('tests.test_native_passage_navigation072', 'NativePassageNavigation072Tests', 'test084-related-passage072', frozenset({
        'test_candidate_bits_cover_annotated_families_and_multiple_mouths',
        'test_shadowed_mouth_requires_outside_floor_and_wall_line_support',
    }), False),
    ('tests.test_native_icon066', 'NativeIcon066Tests', 'test084-related-icon066', frozenset({
        'test_fragmented_icon_does_not_replace_other_hud_or_menu_guards',
        'test_original_bright_bars_and_long_opening_path_still_classify_floor',
    }), False),
    ('tests.test_native_controller', 'NativeControllerTests', 'test084-related-controller', frozenset({
        'test_continuous_run_limit_eight_and_first_latest_diagnostics',
        'test_goods_crossing_latches_before_motion_but_needs_stable_pause_source',
        'test_goods_frame_unknown_motion_is_recorded_once_without_waiting',
        'test_motion_wait_diagnostic_retains_each_eligible_capture_and_fixed_deadline',
        'test_scene_detail_query_is_bounded_and_leaves_existing_abi_unchanged',
        'test_unknown_synth_and_started_cancel_freeze_even_pause',
    }), False),
    ('tests.test_native_recovery', 'NativeRecoveryTests', 'test084-related-recovery', frozenset({
        'test_goods_after_visual_deadline_are_held_without_move_credit',
    }), False),
)

CLIENT_CASES = (
    ('tests.test_native_results', 'NativeResultsTests', 'test084-related-journal', frozenset({
        'test_scene_changes_are_projected_and_survive_journal_roundtrip',
    }), False),
    ('tests.test_native_publication069', 'Publication069Tests', 'test084-publication', frozenset({
        'test_missing_png_or_incomplete_cursor_cannot_be_published_or_start_fresh',
    }), False),
)

PACKAGE_CASES = ()

CORE_MODULES = ('tests.test_native_shadow_floor084', 'tests.test_native_supported_mouth084', 'tests.test_native_icon084', 'tests.test_native_nonfloor_diagnostics084', 'tests.test_native_materials082', 'tests.test_native_outer_floor083', 'tests.test_native_passage_navigation072', 'tests.test_native_icon066', 'tests.test_native_controller', 'tests.test_native_recovery', 'tests.test_native_perception', 'tests.test_native_beat')
NATIVE_BASELINE = '87cd98b6046154b8a6eb8da39ada31b31afb595f'
RETAINED_RUNTIME_SHA256 = '048a462811edabbef4544b2b83ffaadcedbdc654d8675fad4143a6432bc299da'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Perception.c', 'LoopCtrlUITests/NG2Navigation.c', 'LoopCtrlUITests/NG2Controller.c'}
CORE_CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.validation', 'necroprobe.protocol')
CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.test084', 'necroprobe.validation', 'necroprobe.protocol')
FIXTURE_OVERRIDE_PREFIXES = ('NECRO_TEST063_BASELINE_', 'NECRO_TEST071_BASELINE_', 'NECRO_TEST072_BASELINE_', 'NECRO_TEST074_BASELINE_', 'NECRO_TEST075_BASELINE_', 'NECRO_TEST076_BASELINE_', 'NECRO_TEST077_BASELINE_', 'NECRO_TEST078_BASELINE_', 'NECRO_TEST079_BASELINE_', 'NECRO_TEST080_BASELINE_', 'NECRO_TEST081_BASELINE_', 'NECRO_TEST082_BASELINE_', 'NECRO_TEST083_BASELINE_', 'NECRO_TEST083_FRAMING_BASELINE_', 'NECRO_TEST084_BASELINE_', 'NECRO_TEST084_NONFLOOR_')

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
        if name != 'necroprobe.test084' and raw != subprocess.check_output(
                ['git', 'show', NATIVE_BASELINE+':'+relative], cwd=driver):
            raise ValueError('unchanged TEST084 client source differs from the baseline: '+name)
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
    entry = importlib.import_module('necroprobe.test084')
    if publication.native is not native:
        raise ValueError('production publication wrapper is not bound to the actual driver client')
    if entry.device_main is not publication.main:
        raise ValueError('TEST084 entry is not bound to the actual driver publication wrapper')
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
    (output/'test084-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
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
        raise ValueError('TEST084 sealed source identity is not installed')
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'], cwd=driver, text=True))
    baseline_sources = {name: row['patched_sha256'] for name, row in baseline['files'].items()}
    baseline_sources.update({name: row['sha256'] for name, row in baseline['additions'].items()})
    current_sources = before['native_source_sha256']
    changed = {name for name in current_sources if current_sources[name] != baseline_sources.get(name)}
    if set(current_sources) != set(baseline_sources) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('TEST084 native change scope differs')
    native_change_scope = {'baseline': NATIVE_BASELINE, 'changed_sources': sorted(changed),
                           'unchanged_sources': len(current_sources)-len(changed)}
    if current_sources['LoopCtrlUITests/NG2Runtime.swift'] != RETAINED_RUNTIME_SHA256:
        raise ValueError('TEST084 retained Runtime source changed')
    client_before = client_source_identity(driver)
    suites = native_suites(upstream) + client_suites() + package_suites()
    selected_cases(case for _label, cases in suites for case in cases)
    fixture = importlib.import_module('tests.test_native_controller')
    abi = {name: ctypes.sizeof(getattr(fixture, name))
           for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    if abi != {'Scene': 23864, 'Status': 192, 'Event': 128, 'MotionWait': 48, 'RecoveryStatus': 456}:
        raise ValueError('native ABI layout changed')
    record = {'scope': 'TEST084 black-entry floor, supported mouth, nine-pixel icon and ACK non-FLOOR diagnostics; device feedback first',
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
              'selection_reasons': {'test084-shadow-floor': 'only the fixed black upper half plus independently observed coloured/textured lower floor may recover an original UNKNOWN mouth; all full-tile and old material guards remain', 'test084-supported-mouth': 'an already observed FLOOR mouth needs outside FLOOR, exactly one observed wall and three current wall-line cells; only observed safe-floor approach remains authorized', 'test084-nine-pixel-icon': 'original full ROI, neutral reference IoU and independent HUD/menu gates remain while a nine-pixel bar opening recovers FLOOR; public RGBA then ACKed Controller goods require confirmed PAUSE', 'test084-nonfloor-diagnostics': 'only a current stable ACKed MOVE may retain a real source-to-non-FLOOR STATE diff; no motion assessment, attempt, command credit or recovery is introduced', 'test084-related-materials082': 'the old observed partial mouth candidate and original colour/texture/darkness rejection stay distinct from the new black-entry proof', 'test084-related-outer083': 'the prior fixed bands retain all original pixel/HUD/alpha dependencies and old material/gate/merchandise authority', 'test084-related-passage072': 'the original two-wall ten-bit candidate families and UNKNOWN-mouth wall-line/outside-floor requirements remain unchanged', 'test084-related-icon066': 'old raw/long openings still classify FLOOR and no fragmented icon replaces independent HUD/menu guards', 'test084-related-controller': 'goods after UNKNOWN motion are latched without invented movement; pause requires a stable prefix; UNKNOWN synth/cancel never retries; real MotionWait captures keep the original deadline; public ABI/query capacity and existing first/latest diagnostics remain bounded', 'test084-related-recovery': 'goods after the visual deadline are retained without MOVE credit or deadline extension', 'test084-related-journal': 'existing SceneChange projection and journal roundtrip preserve the old report schema without private fields', 'test084-publication': 'the new entry inherits complete-evidence ZIP publication; missing PNGs or incomplete cursors cannot publish or start a new run'}}
    for label, cases in suites:
        run_scope(label, cases, output, record)
    # Workflow and selection changes have their own small unit set, without
    # automatically discovering the historical package/Swift fixture suite.
    for module_name, classes in (('test_device_ci084', ('DeviceHostSelection084Tests',)),):
        module = importlib.import_module(module_name)
        cases = [case for name in classes for case in
                 unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module, name))]
        run_scope('test084-'+module_name, cases, output, record)
    if verifier.inspect_native_sources(upstream, driver) != before:
        raise ValueError('selected tests changed sealed production source')
    reject_fixture_overrides()
    if client_source_identity(driver) != client_before:
        raise ValueError('selected tests changed the pinned production client')
    record['sealed_sources_unchanged_after_tests'] = True
    record['client_source_unchanged_after_tests'] = True
    record['manifest_sha256'] = hashlib.sha256((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes()).hexdigest()
    (output/'test084-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
    print('PASS TEST084 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
