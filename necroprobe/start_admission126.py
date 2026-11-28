"""Closed, display-only reasons from authenticated native start refusals."""
import re


_MESSAGES = {
    'Owner paused native control before campaign admission.': 'owner_paused',
    'Campaign storage quota is unavailable.': 'storage_unavailable',
    'Native cycle evidence must be recovered and publication acknowledged before a new start.': 'evidence_unpublished',
    'Prepare native cycle notifications before starting gameplay.': 'notification_permission',
    'Previous native cycle publication is not acknowledged.': 'publication_pending',
    'Unknown native input prevents campaign admission.': 'input_unknown',
    'Previous native run is still draining before campaign admission.': 'run_draining',
    'Previous native campaign is still draining.': 'campaign_draining',
    'Previous native export prevents campaign admission.': 'export_pending',
    'Previous capture prevents campaign admission.': 'capture_pending',
    'Run identity or process limit prevents campaign admission.': 'identity_limit',
}
REASONS = frozenset('cycle_start_'+value for value in _MESSAGES.values())
EXPLANATIONS = {
    'cycle_start_owner_paused': 'LoopCtrlの遠隔操作が一時停止中のため、開始が拒否されました。',
    'cycle_start_storage_unavailable': '保存領域の予約ができません。保存件数・空き容量・保存記録の検証などが開始条件を満たしていません。どの条件かは追加確認が必要です。',
    'cycle_start_evidence_unpublished': '保存記録の確認、または前回記録の回収・照合が完了していないため、開始が拒否されました。',
    'cycle_start_notification_permission': 'LoopCtrlが開始時に通知の許可を確認できなかったため、開始が拒否されました。',
    'cycle_start_publication_pending': '前回の記録の回収・照合が完了していないため、開始が拒否されました。',
    'cycle_start_input_unknown': '前回の入力結果が未確定のため、開始が拒否されました。',
    'cycle_start_run_draining': '前回の実行処理がまだ終了していないため、開始が拒否されました。',
    'cycle_start_campaign_draining': '前回の周回処理がまだ終了していないため、開始が拒否されました。',
    'cycle_start_export_pending': '前回の記録の書き出し処理が残っているため、開始が拒否されました。',
    'cycle_start_capture_pending': '前回の画面取得処理が残っているため、開始が拒否されました。',
    'cycle_start_identity_limit': '同じ実行IDの消費済み、またはLoopCtrl起動中の実行数上限により、開始が拒否されました。',
    'cycle_start_not_admitted': '開始要求は拒否されましたが、具体的な原因はまだ特定できません。',
}


def classify(method, params, code, message):
    # The caller has already authenticated the response and checked its ID
    # and error shape. No native message/data is retained or interpreted as
    # authority to start, retry, cancel, or remove evidence.
    if (method != 'necro_native_start' or code != -32095 or type(params) is not dict
            or set(params) != {'run_id', 'profile', 'continuous_campaign', 'initial_restart'}
            or type(params['run_id']) is not str
            or re.fullmatch('[0-9a-f]{32}', params['run_id']) is None
            or params['profile'] != 'normal-1-1-irregular-v1'
            or params['continuous_campaign'] is not True or params['initial_restart'] is not True):
        return None
    reason = _MESSAGES.get(message)
    return 'cycle_start_'+reason if reason is not None else None
