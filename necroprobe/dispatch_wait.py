"""最後の短い区間だけclockを読む、ホスト側の予定時刻待機。

予定時刻でのゲーム受付を保証しない。送信の可否は呼出し側が待機後に
取消・観測・位相・前面・10ms遅れ等をもう一度検証して決める。
"""

SPIN_NS=25_000_000


def spin_until(until,clock):
    """呼出し側が残り25ms以下と確認した末尾だけ、sleepせず待つ。"""
    while clock()<until:
        pass


def wait_until(until,clock,sleeper,check,spin_wait=None):
    """長い区間は最大50msずつsleepし、最後の最大25msは短くspinする。

    checkは取消/期限を検証し、残り秒か(残り秒,検証時刻)を返す。
    末尾spinの前後にも呼び、最後の検証結果を返す。呼出し側で同じ
    検証を重ね、送信直前の余裕を消費しないため。
    spin_waitは仮想時計等で末尾の時間進行を差し替えるための依存注入。
    """
    while True:
        result=check()
        remaining=result[0] if type(result) is tuple else result
        # followupのvalidateは最終検査時刻も返す。その時刻から残時間を
        # 求め、直後の追加clockだけが進んだ古い認可を返さない。
        checked=result[1] if type(result) is tuple else clock()
        left=until-checked
        if left<=0:return result
        if left<=SPIN_NS:
            if spin_wait is None:spin_until(until,clock)
            else:spin_wait(until)
            return check()
        sleeper(min(.05,remaining,(left-SPIN_NS)/1e9))
