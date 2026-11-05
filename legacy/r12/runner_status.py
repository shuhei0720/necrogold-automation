"""Parent-side worker exit reporting. Never restarts or sends game inputs."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import diagnostics


class Worker:
    def __init__(self, log, stage, receipt):
        self.log, self.stage, self.receipt = map(Path,(log,stage,receipt))
        self.process = None
        self.message = ""
        self.stop_requested = False
        self.timeout_reason = ""
        self.term_at = None
        old = diagnostics.read_record(self.receipt)
        if old.get("state") == "running":
            last = diagnostics.read_record(self.stage).get("phase","起動中")
            self.message = "前回は完了記録なしに中断しました。最後の処理: " + last
            self._append(self.message)
            self._record("interrupted",self.message)
        elif old.get("state") in ("error","interrupted","stopped"):
            self.message = str(old.get("message",""))

    def _append(self, text):
        try:
            with self.log.open("a",encoding="utf-8") as stream:
                stream.write("\n"+text+"\n")
        except OSError:
            pass

    def _record(self, state, message):
        try:
            diagnostics.write_record(self.receipt,dict(state=state,message=message,time=time.time()))
        except OSError:
            pass

    @property
    def active(self):
        return self.process is not None and self.process.poll() is None

    def start(self, script, mode):
        self.poll()
        if self.active:
            return False
        # Preserve the complete previous log, including a fatal traceback.
        if self.log.exists():
            self.log.replace(self.log.with_name(self.log.stem+"-previous.log"))
        self.message = ""
        self.stop_requested = False
        self.timeout_reason = ""
        self.term_at = None
        env = dict(os.environ,NECRO_STAGE_FILE=str(self.stage))
        diagnostics.write_record(self.stage,dict(pid=0,phase="Python起動中",since=time.monotonic(),limit=45,state="running"))
        self._record("running","")
        try:
            with self.log.open("w",encoding="utf-8") as out:
                self.process = subprocess.Popen([sys.executable,"-u","-X","faulthandler",str(script),mode],
                                                cwd=str(Path(script).parent),env=env,stdout=out,stderr=out)
        except OSError as exc:
            self.message="起動失敗: "+str(exc)
            self._append(self.message)
            self._record("error",self.message)
            raise
        return True

    def stop(self):
        if self.active:
            self.stop_requested=True
            self.term_at=time.monotonic()
            self.process.terminate()

    def poll(self):
        if self.process is None:
            return
        code=self.process.poll()
        last=diagnostics.read_record(self.stage)
        phase=str(last.get("phase","起動中"))
        if code is None:
            now=time.monotonic()
            if self.term_at is not None:
                if now-self.term_at>3:
                    self.process.kill()
                return
            # A single blocked operation is bounded. No background retry can
            # accidentally re-send a tap whose acknowledgement was lost.
            if (last.get("state")=="running" and isinstance(last.get("since"),(int,float))
                    and now-last["since"]>max(15,float(last.get("limit",30)))):
                self.timeout_reason=f"処理が進まないため停止しました。最後の処理: {phase}"
                self._append(self.timeout_reason)
                self.term_at=now
                self.process.terminate()
            return
        self.process=None
        if self.stop_requested:
            state="stopped";self.message="停止操作で終了しました。"
        elif self.timeout_reason:
            state="error";self.message=self.timeout_reason
        elif code==0:
            state="completed";self.message=""
        else:
            state="error"
            if code<0:
                try:name=signal.Signals(-code).name
                except ValueError:name=f"signal {-code}"
                reason=f"シグナル {name}"
            else:
                reason=f"終了コード {code}"
            self.message=f"処理終了（{reason}）。最後の処理: {phase}。下のログを確認してください。"
        if self.message:self._append(self.message)
        self._record(state,self.message)

    def close(self):
        self.stop()
        if self.process is not None:
            try:self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=3)
        self.poll()
