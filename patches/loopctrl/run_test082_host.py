"""Run TEST082 material, passage-motion and wait-diagnostic units with exact related regressions.

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
    ('tests.test_native_materials082', 'NativeMaterials082Tests', 'test082-materials', frozenset({
        'test_bright_disjoint_floor_survives_integer_boundary',
        'test_bright_requires_disjoint_texture_and_bounded_colour',
        'test_old_materials_gold_gate_hud_and_invalid_alpha_remain_guarded',
        'test_partial_observed_mouth_becomes_candidate_without_unknown_entry',
        'test_partial_requires_current_observed_floor_not_darkness_or_wall',
        'test_stone_disjoint_brick_texture_survives_integer_boundary',
        'test_stone_requires_disjoint_witnesses_and_original_red_green_guards',
    }), True),
    ('tests.test_native_passage_motion082', 'NativePassageMotion082Tests', 'test082-passage-motion', frozenset({
        'test_all_old_terrain_and_unique_nine_reject_lost_changed_or_ambiguous_anchors',
        'test_blur_actual_dependencies_fixed52_support95_bands_and_all73_15pp',
        'test_corner_planes_keep_scope_quality_phase_and_all73_discrimination_separate',
        'test_known_primary_and_legacy_results_zero_tween_reverse_and_two_cells_are_preserved',
        'test_public_four_direction_terrain_blur_unit_keeps_next_navigation_unentered',
        'test_public_unique_corner_uses_blur_quality_and_separate_sharp_discrimination',
        'test_raw_and_both_independent_phase_require_finite_same_unit_and_original_gap',
        'test_scope_requires_clear_floor_no_gold_items_protection_and_old_endpoints',
    }), True),
    ('tests.test_native_wait_diagnostics082', 'NativeWaitDiagnostics082Tests', 'test082-wait-diagnostics', frozenset({
        'test_mask_zero_metadata_issued_clock_and_goods_do_not_create_false_trace',
        'test_ready_unknown_motion_records_only_real_nonzero_scene_diff',
        'test_rejected_independent_route_retains_true_source_diff_without_authority_change',
    }), True),
    ('tests.test_native_motion074', 'NativeMotion074Tests', 'test082-related-motion074', frozenset({
        'test_arrival_proof_does_not_authorize_or_require_a_future_step',
        'test_passage_move_requires_all_stones_and_a_noncollinear_dirt_anchor',
    }), False),
    ('tests.test_native_motion075', 'NativeMotion075Tests', 'test082-related-motion075', frozenset({
        'test_full_kernel_rejects_hidden_changed_or_ui_dependencies',
        'test_independent_bands_weak_support_and_aliases_are_required',
    }), False),
    ('tests.test_native_revealed_gate079', 'NativeRevealedGate079Tests', 'test082-related-revealed079', frozenset({
        'test_raw_normal_side_unit_gap_and_known_output_boundaries',
    }), False),
    ('tests.test_native_sparse_gate080', 'NativeSparseGate080Tests', 'test082-related-sparse080', frozenset({
        'test_only_all_positive_infinite_legacy_and_unknown_output_may_use_proof',
    }), False),
    ('tests.test_native_side_gate081', 'NativeSideGate081Tests', 'test082-related-side081', frozenset({
        'test_public_four_direction_side_gate_unit_keeps_next_navigation_unentered',
    }), False),
    ('tests.test_native_stationary_wait076', 'NativeStationaryWait076Tests', 'test082-related-stationary076', frozenset({
        'test_proof_requires_independent_current_prefix_and_increasing_capture',
        'test_ready_or_issued_unknown_does_not_reopen_the_same_wait',
        'test_wait_deadline_is_fixed_and_unknown_frames_do_not_extend_it',
    }), False),
    ('tests.test_native_controller', 'NativeControllerTests', 'test082-related-controller', frozenset({
        'test_continuous_run_limit_eight_and_first_latest_diagnostics',
        'test_scene_detail_query_is_bounded_and_leaves_existing_abi_unchanged',
    }), False),
    ('tests.test_native_perception', 'NativePerceptionTests', 'test082-related-palette', frozenset({
        'test_floor_quantization_integer_band_boundaries',
        'test_synthetic_goods_unknown_partial_and_exact_counts',
        'test_synthetic_tile_integer_thresholds',
    }), False),
    ('tests.test_native_fringe068', 'NativeFringe068Tests', 'test082-related-fringe', frozenset({
        'test_masked_in_grid_pair_restores_only_the_real_two_coordinates',
        'test_partial_visible_goods_and_existing_gold_keep_their_original_authority',
    }), False),
    ('tests.test_native_icon066', 'NativeIcon066Tests', 'test082-related-icon', frozenset({
        'test_fragmented_icon_does_not_replace_other_hud_or_menu_guards',
    }), False),
)

CLIENT_CASES = (
    ('tests.test_native_paged_results', 'PagedResultsTests', 'test082-report-details', frozenset({
        'test_scene_change_details_survive_encrypted_manifest_and_reload_with_closed_projection',
    }), False),
    ('tests.test_native_results', 'NativeResultsTests', 'test082-report-mask', frozenset({
        'test_bad_scene_change_required_values_are_rejected',
    }), False),
    ('tests.test_native_collection069', 'NativeCollection069Tests', 'test082-collection', frozenset({
        'test_interrupted_export_recovers_same_uuid_export_and_cursor_with_no_keepalive',
    }), False),
    ('tests.test_native_publication069', 'Publication069Tests', 'test082-publication', frozenset({
        'test_missing_png_or_incomplete_cursor_cannot_be_published_or_start_fresh',
    }), False),
)

PACKAGE_CASES = ()

CORE_MODULES = ('tests.test_native_controller', 'tests.test_native_recovery', 'tests.test_native_beat', 'tests.test_native_perception', 'tests.test_native_motion067', 'tests.test_native_blocked067', 'tests.test_native_observation072', 'tests.test_native_ui073', 'tests.test_native_passage_unsent076', 'test_native_perception', 'tests.test_native_passage072', 'tests.test_native_stationary_wait076', 'tests.test_native_navigation', 'tests.test_native_motion074', 'tests.test_native_motion075', 'tests.test_native_revealed_gate079', 'tests.test_native_sparse_gate080', 'tests.test_native_side_gate081', 'tests.test_native_fringe068', 'tests.test_native_icon066')
NATIVE_BASELINE = '7d4f8f435ad54daca79a1ec89b04dfdc6d30e625'
RETAINED_RUNTIME_SHA256 = '048a462811edabbef4544b2b83ffaadcedbdc654d8675fad4143a6432bc299da'
EXPECTED_NATIVE_CHANGES = {'LoopCtrlUITests/NG2Perception.c', 'LoopCtrlUITests/NG2Navigation.c', 'LoopCtrlUITests/NG2Controller.c'}
CORE_CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.validation', 'necroprobe.protocol')
CLIENT_SOURCE_MODULES = ('necroprobe.native_walk', 'necroprobe.test069', 'necroprobe.test082', 'necroprobe.validation', 'necroprobe.protocol')
FIXTURE_OVERRIDE_PREFIXES = ('NECRO_TEST063_BASELINE_', 'NECRO_TEST071_BASELINE_', 'NECRO_TEST072_BASELINE_', 'NECRO_TEST074_BASELINE_', 'NECRO_TEST075_BASELINE_', 'NECRO_TEST076_BASELINE_', 'NECRO_TEST077_BASELINE_', 'NECRO_TEST078_BASELINE_', 'NECRO_TEST079_BASELINE_', 'NECRO_TEST080_BASELINE_', 'NECRO_TEST081_BASELINE_', 'NECRO_TEST082_BASELINE_')

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
        if name != 'necroprobe.test082' and raw != subprocess.check_output(
                ['git', 'show', NATIVE_BASELINE+':'+relative], cwd=driver):
            raise ValueError('unchanged TEST082 client source differs from the baseline: '+name)
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
    entry = importlib.import_module('necroprobe.test082')
    if publication.native is not native:
        raise ValueError('production publication wrapper is not bound to the actual driver client')
    if entry.device_main is not publication.main:
        raise ValueError('TEST082 entry is not bound to the actual driver publication wrapper')
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
    (output/'test082-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
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
        raise ValueError('TEST082 sealed source identity is not installed')
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', NATIVE_BASELINE+':patches/loopctrl/ngg2-manifest.json'], cwd=driver, text=True))
    baseline_sources = {name: row['patched_sha256'] for name, row in baseline['files'].items()}
    baseline_sources.update({name: row['sha256'] for name, row in baseline['additions'].items()})
    current_sources = before['native_source_sha256']
    changed = {name for name in current_sources if current_sources[name] != baseline_sources.get(name)}
    if set(current_sources) != set(baseline_sources) or changed != EXPECTED_NATIVE_CHANGES:
        raise ValueError('TEST082 native change scope differs')
    native_change_scope = {'baseline': NATIVE_BASELINE, 'changed_sources': sorted(changed),
                           'unchanged_sources': len(current_sources)-len(changed)}
    if current_sources['LoopCtrlUITests/NG2Runtime.swift'] != RETAINED_RUNTIME_SHA256:
        raise ValueError('TEST082 retained Runtime source changed')
    client_before = client_source_identity(driver)
    suites = native_suites(upstream) + client_suites() + package_suites()
    selected_cases(case for _label, cases in suites for case in cases)
    fixture = importlib.import_module('tests.test_native_controller')
    abi = {name: ctypes.sizeof(getattr(fixture, name))
           for name in ('Scene', 'Status', 'Event', 'MotionWait', 'RecoveryStatus')}
    if abi != {'Scene': 23864, 'Status': 192, 'Event': 128, 'MotionWait': 48, 'RecoveryStatus': 456}:
        raise ValueError('native ABI layout changed')
    record = {'scope': 'TEST082 material boundaries, no-gold passage unit proof and stationary rejection evidence; device feedback first',
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
              'selection_reasons': {'test082-materials': 'additional original-pixel witnesses apply only after the old DIRT classifier and preserve later goods protection', 'test082-passage-motion': 'all old motion proofs UNKNOWN; independent terrain, raw unit and both world-blur phase bands must agree', 'test082-wait-diagnostics': 'only valid unsent stationary SCREEN rejection may append honest nonzero-mask diagnostics without new authority', 'test082-report-details': 'existing detailed diagnostic schema survives encrypted paged results and journal reload', 'test082-report-mask': 'zero masks, malformed types and excess diagnostic rows stay invalid', 'test082-collection': 'interrupted terminal evidence keeps the original UUID, export and cursor without input renewal', 'test082-publication': 'incomplete or missing evidence cannot publish a ZIP or start a fresh run', 'test082-related-motion074': 'all old STONE anchors and the noncollinear DIRT anchor remain necessary; past displacement proof does not grant a future input', 'test082-related-motion075': 'all21 original blur dependencies stay observed and protected from UI/hidden changes; independent old phase bands, support and alias bounds remain unchanged', 'test082-related-revealed079': 'old known motion outputs and raw unit gap bounds retain priority', 'test082-related-sparse080': 'the old positive-INF-only branch is not broadened', 'test082-related-side081': 'the preceding gold side-gate proof still gives no entry credit', 'test082-related-stationary076': 'prefix/stability/identity/overlap failures do not gain synthetic diagnostic authority; READY/ISSUED and UNKNOWN do not reopen expired or new-source waits; original wait deadlines and unknown-frame budgets remain fixed', 'test082-related-controller': 'existing bounded scene/detail ABI queries and omitted-cell counts remain intact; existing first1/latest2 diagnostics and chain/session limits remain intact', 'test082-related-palette': 'old palette, flat pixel and prior GOLD quantization remain unchanged; old wood, UNKNOWN and gold integer thresholds remain unchanged; goods visibility, exact counts and protected cells retain authority', 'test082-related-fringe': 'lower-edge gold restores only its original observed coordinates; partial goods and existing gold keep original authority', 'test082-related-icon': 'non-FLOOR HUD or menu guards cannot be replaced by a fragmented icon'}}
    for label, cases in suites:
        run_scope(label, cases, output, record)
    # Workflow and selection changes have their own small unit set, without
    # automatically discovering the historical package/Swift fixture suite.
    for module_name, classes in (('test_device_ci082', ('DeviceHostSelection082Tests',)),):
        module = importlib.import_module(module_name)
        cases = [case for name in classes for case in
                 unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module, name))]
        run_scope('test082-'+module_name, cases, output, record)
    if verifier.inspect_native_sources(upstream, driver) != before:
        raise ValueError('selected tests changed sealed production source')
    reject_fixture_overrides()
    if client_source_identity(driver) != client_before:
        raise ValueError('selected tests changed the pinned production client')
    record['sealed_sources_unchanged_after_tests'] = True
    record['client_source_unchanged_after_tests'] = True
    record['manifest_sha256'] = hashlib.sha256((driver/'patches/loopctrl/ngg2-manifest.json').read_bytes()).hexdigest()
    (output/'test082-host-scope.json').write_text(json.dumps(record, indent=2)+'\n')
    print('PASS TEST082 changed units and related regressions against exact IPA sources')


if __name__ == '__main__':
    main()
