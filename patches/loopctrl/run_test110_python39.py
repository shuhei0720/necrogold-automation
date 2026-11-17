"""Actual Python 3.9 client/publication contracts for the TEST110 device lane.

This is a separate interpreter execution from the native C host selector.
It sends no device traffic and does not claim phone acceptance.
"""
import argparse
import hashlib
import importlib
import importlib.util
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
SCOPE_FINALIZED = True  # Final author actual-Python3.9 inventory: 34 new + 74 retained.
CASES = (
    ('tests.test_native_irregular_client110', 'IrregularClient110Tests', 'test110-irregular_client110', frozenset({
        'test_api16_schema_requires_both_caps_and_keeps_unrelated_tags',
        'test_checkpoint_without_completed_restart_stays_pending',
        'test_explicit_irregular_client_admits_only_its_profile_and_query',
        'test_fixture_uses_c_restart_level_move_only_inputs_and_unknown_event_identity',
        'test_intent_state_command_ids_bind_exact_action',
        'test_kind5_is_not_move_credit_and_is_refused_by_old_snapshot_parser',
        'test_limit_episode_thirteen_is_exportable_diagnostic_without_extra_retry_authority',
        'test_observation_fields_and_positive_geometry_are_closed',
        'test_old_and_new_admission_do_not_follow_reply_selected_profiles',
        'test_old_eight_and_new_nine_payloads_are_closed',
        'test_only_durable_unreserved_stalled_episode_can_upgrade_to_fresh_death',
        'test_outcome_state_command_and_capture_ids_bind_exact_action_and_role',
        'test_physical_count_bounds_reject_impossible_positive_and_none_observations',
        'test_proof_ids_and_clocks_are_typed_and_none_enemy_is_not_positive',
        'test_records_preserve_same_capture_roles_but_refuse_mismatched_hash',
        'test_sequence_refuses_wrong_epoch_prefix_ack_order_and_raw_binding',
        'test_stalled_checkpoint_preserves_both_observations_and_source_identity',
        'test_trial_preflight_uses_only_selected_sibling_query',
    }), True),
    ('tests.test_native_irregular_client110', 'IrregularPublication110Tests', 'test110-irregular_client110', frozenset({
        'test_archive_snapshot_cannot_disguise_its_selected_profile_or_revision',
        'test_cross_profile_journal_read_and_client_spec_are_refused_before_network',
        'test_every_irregular_referenced_png_is_required_before_publication',
        'test_hash_valid_cross_profile_session_and_old_kind5_records_are_rejected',
        'test_hint_cannot_bind_other_capture_prefix_or_untyped_job',
        'test_irregular_positive_hint_is_unadopted_candidate_and_never_shop_credit',
        'test_manifest_session_provenance_and_raw_hash_mismatch_refuse_authority',
        'test_missing_capability_starts_zero_and_no_game_identity_is_replaced',
        'test_missing_irregular_png_preserves_original_run_without_publication_or_restart',
        'test_new_notice_distinguishes_unknown_negative_target_and_retry_hold',
        'test_new_profile_keeps_proved_normal_negative_campaign_handoff_until_target',
        'test_old_diagnostic_manifest_may_omit_png_without_new_irregular_requirement',
        'test_test110_entry_selects_new_protocol_and_old_entry_stays_default',
        'test_unknown_ack_and_dangling_intent_do_not_authorize_campaign_next_start',
        'test_unknown_start_and_export_failure_recover_same_uuid_without_resend',
        'test_whole_native_kind5_evidence_survives_journal_and_archive_unchanged',
    }), True),
    ('tests.test_native_cycle_client094', 'CycleClient094Tests', 'test094-cycle_client094', frozenset({
        'test_ack_failure_retains_same_archive_and_retries_no_game_start',
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
        'test_late_terminal_assessment_is_reported_as_unadopted_not_unexecuted_or_negative',
        'test_later_explicit_invocation_starts_new_id_only_after_prior_receipt_and_zip_verify',
        'test_malformed_not_started_error_cannot_clear_uncertain_input_intent',
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
        'test_uncertain_start_is_sent_once_and_next_invocation_only_recovers_same_id',
    }), True),
    ('tests.test_native_cycle_client095', 'CycleClient095Tests', 'test095-cycle_client095', frozenset({
        'test_095_launcher_uses_separate_spool_and_truthful_not_started_message',
        'test_095_zip_prefix_filename_receipt_and_all_registered_bytes',
        'test_existing_094_and_generic_spools_preserve_original_zip_label',
    }), True),
    ('tests.test_campaign099', 'Campaign099Tests', 'test099-campaign099', frozenset({
        'test_cancel_after_publication_keeps_last_zip_and_issues_no_next_start',
        'test_clean_search_after_earlier_resolved_negative_uses_current_handoff',
        'test_clean_search_limit_default_unknown_is_distinct_from_unknown_assessment',
        'test_collection_interruption_recovers_same_uuid_without_new_start',
        'test_completed_run_before_index_crash_is_reconciled_before_next_start',
        'test_controller_fault_or_unadopted_negative_does_not_restart_campaign',
        'test_handoff_denies_pause_command_source_from_other_generation',
        'test_handoff_denies_referenced_frame_without_manifest_image',
        'test_handoff_requires_matching_registered_stable_source_and_pause_prefix',
        'test_indexed_published_run_clears_pending_markers_after_recovery',
        'test_missing_malformed_or_denied_handoff_does_not_repeat_limit',
        'test_negative_handoff_publishes_before_new_uuid_and_stops_at_target',
        'test_next_intent_crash_never_skips_or_restarts_the_previous_uuid',
        'test_prepared_next_journal_cannot_skip_revalidation_of_prior_proof',
        'test_publication_ack_failure_returns_incomplete_fault_bundle_and_same_id_recovery',
        'test_recovery_only_restores_last_bundle_without_start_or_new_campaign',
        'test_single_mode_returns_a_checked_index_and_last_full_run_zip',
        'test_target_candidate_and_real_unknown_never_start_another_run',
        'test_trial_client_reads_feature_every_preflight_and_rejects_old_or_malformed',
        'test_trial_run_limit_stops_before_an_additional_native_start',
        'test_uncertain_start_response_is_only_recovered_under_original_uuid',
        'test_unsupported_trial_feature_stops_before_any_native_start',
    }), True),
    ('tests.test_cycle_http098', 'CycleHTTP098Tests', 'test098-cycle_http098', frozenset({
        'test_bulk_allowance_does_not_bypass_response_mac',
        'test_explicit_recovery_entry_keeps_098_spool_and_forwards_no_start_mode',
        'test_oversized_bulk_and_unchanged_single_status_limits_reject_at_headers',
        'test_valid_slash_heavy_four_chunk_png_passes_authenticated_http_and_full_recovery',
    }), True),
    ('tests.test_cycle_recovery_only098', 'CycleRecoveryOnly098Tests', 'test098-cycle_recovery_only098', frozenset({
        'test_missing_journal_rejects_without_rpc_or_fresh_uuid',
        'test_published_journal_without_original_receipt_still_rejects',
        'test_published_run_recreates_same_zip_at_new_mount_without_rpc_or_new_uuid',
        'test_unfinished_run_collects_and_publishes_same_uuid_without_keepalive',
        'test_unstarted_journal_rejects_without_rpc_and_preserves_original_bytes',
    }), True),
    ('tests.test_client100', 'Client100Tests', 'test100-client100', frozenset({
        'test_default_test099_labels_and_recovery_stay_unchanged',
        'test_test100_archive_index_and_nested_run_use_separate_label',
        'test_test100_entry_routes_own_spool_and_preserves_closed_test_number',
        'test_test100_interrupted_collection_recovers_same_uuid_and_label',
    }), True),
    ('tests.test_client101', 'Client101Tests', 'test101-client101', frozenset({
        'test_entry101_isolates_labels_and_recovers_same_uuid_without_continuing',
        'test_shell101_checks_own_module_and_rejects_conflicting_modes_before_start',
    }), True),
)
PRODUCT_PATHS = (
    'necroprobe/native_cycle.py', 'necroprobe/irregular.py',
    'necroprobe/cycle_publication.py', 'necroprobe/campaign099.py',
    'necroprobe/trial_evidence099.py', 'necroprobe/test099.py',
    'necroprobe/test110.py', 'test_110.sh',
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_suite(driver):
    if not SCOPE_FINALIZED or not CASES:
        raise ValueError('TEST110 Python 3.9 author scope is pending')
    spec = importlib.util.spec_from_file_location('test110_host_source_utils', HERE / 'run_test110_host.py')
    host = importlib.util.module_from_spec(spec); spec.loader.exec_module(host)
    host.reject_fixture_overrides()
    selected = []
    for module_name, klass, _label, methods, exact in CASES:
        module = importlib.import_module(module_name)
        if Path(module.__file__).resolve() != driver / (module_name.replace('.', '/') + '.py'):
            raise ValueError('Python 3.9 fixture import escaped pinned driver')
        selected.extend(host.method_cases(getattr(module, klass), methods, exact=exact))
    return host.selected_cases(selected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('driver', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args(); driver = args.driver.resolve(); output = args.output.resolve()
    if sys.version_info[:2] != (3, 9) or hasattr(0, 'bit_count'):
        raise SystemExit('Actual Python 3.9 is required; another interpreter is not compatibility proof')
    output.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(driver), str(driver / 'tests'), str(HERE)]
    selected = selected_suite(driver)
    paths = (*PRODUCT_PATHS, 'patches/loopctrl/run_test110_python39.py',
        'patches/loopctrl/run_test110_host.py',
        *(row[0].replace('.', '/') + '.py' for row in CASES))
    before = {name: sha(driver / name) for name in dict.fromkeys(paths)}
    code = subprocess.check_output(['git', '-C', str(driver), 'rev-parse', 'HEAD'], text=True).strip()
    for name, digest in before.items():
        pinned = subprocess.check_output(['git', '-C', str(driver), 'show', code + ':' + name])
        if hashlib.sha256(pinned).hexdigest() != digest:
            raise ValueError('Python 3.9 source differs from pinned CODE: ' + name)
    syntax = subprocess.run(['sh', '-n', str(driver / 'test_110.sh')], capture_output=True, text=True)
    check = subprocess.run([sys.executable, '-m', 'necroprobe.test110', '--check'], cwd=driver,
        capture_output=True, text=True)
    entry_ok = syntax.returncode == 0 and check.returncode == 0 and check.stdout.strip() == (
        'native-irregular-trial-v1 / 1.98.16-ngg2')
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(selected))
    log = stream.getvalue(); (output / 'test110-python39.txt').write_text(log)
    print(sys.version); print(log, end='', flush=True)
    after = {name: sha(driver / name) for name in before}
    success = entry_ok and before == after and result.testsRun == len(selected) and (
        result.wasSuccessful() and not result.skipped and not result.expectedFailures)
    evidence = dict(driver_commit=code, scope='actual Python 3.9 selected client/publication contracts',
        interpreter_version=sys.version, interpreter=platform.python_implementation(),
        interpreter_executable_sha256=sha(Path(sys.executable).resolve()),
        python_version=list(sys.version_info[:3]), selected=[case.id() for case in selected],
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        skipped=len(result.skipped), expected_failures=len(result.expectedFailures),
        source_sha256=before, sources_unchanged=before == after, product_pass=success,
        shell_syntax=dict(returncode=syntax.returncode, stdout=syntax.stdout, stderr=syntax.stderr),
        entry_check=dict(returncode=check.returncode, stdout=check.stdout, stderr=check.stderr),
        device_test='not_run')
    (output / 'test110-python39-scope.json').write_text(json.dumps(evidence, indent=2) + '\n')
    if not success:
        raise SystemExit('TEST110 Python 3.9 selected methods/entry must all execute Green')


if __name__ == '__main__':
    main()
