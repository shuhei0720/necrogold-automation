"""Console wording only; result evidence and absence semantics stay unchanged."""


def assessment_label(outcome, *, has_sources):
    labels = {
        'target': 'のろいのゆびわ（アイコンと名前が一致）',
        'candidate': '指輪候補（保持して目視確認してください）',
        'unknown': 'のろいのゆびわとの一致は未確認（対象なしとは未確定）',
    }
    label = labels[outcome]
    if not has_sources:
        return '未実施（判定できる商品画像がありません）'
    return '実施済み・'+label
