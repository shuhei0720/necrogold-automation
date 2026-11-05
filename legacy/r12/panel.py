"""Local control panel. The game driver is a single child process; GET never triggers taps."""
import html
import os
from pathlib import Path
import secrets
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
from threading import Timer
from datetime import datetime

from phone import ROOT, HOST, VERSION, rpc
import loopctrl_rpc
from runner_status import Worker

PORT=8766
BASE=f"http://127.0.0.1:{PORT}"
TOKEN=Path.home()/".necro-panel-key"
LOG=Path.home()/".necro-latest.log"


def serve():
    # Acquire the port before starting other operations, including pairing.
    key=TOKEN.read_text().strip() if TOKEN.exists() else secrets.token_urlsafe(20)
    if not TOKEN.exists():
        fd=os.open(TOKEN,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"w") as out:out.write(key)
    path="/"+key
    worker=Worker(LOG,LOG.with_suffix(".stage.json"),LOG.with_suffix(".status.json"))
    class Panel(BaseHTTPRequestHandler):
        def reply(self,status,body):
            data=body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type","text/html; charset=UTF-8")
            self.send_header("Content-Length",str(len(data)))
            self.send_header("Cache-Control","no-store")
            self.send_header("Referrer-Policy","same-origin")
            self.send_header("X-Frame-Options","DENY")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path not in (path,path+"/log") or self.headers.get("Host")!=f"127.0.0.1:{PORT}":
                return self.reply(404,"Not found")
            worker.poll()
            active=worker.active
            if self.path==path+"/log":
                data=(f"検証版 {VERSION}\n"+worker.message+"\n").encode("utf-8")
                for name in (LOG.with_name(LOG.stem+"-previous.log"),LOG):
                    try:
                        with name.open("rb") as stream:
                            stream.seek(max(0,stream.seek(0,2)-1024*1024))
                            data+=("\n--- "+name.name+" ---\n").encode()+stream.read()
                    except FileNotFoundError:pass
                self.send_response(200)
                self.send_header("Content-Type","text/plain; charset=utf-8")
                self.send_header("Content-Disposition",f'attachment; filename="necro-{VERSION}-log.txt"')
                self.send_header("Content-Length",str(len(data)))
                self.send_header("Cache-Control","no-store")
                self.end_headers();self.wfile.write(data)
                return
            try:
                with LOG.open("rb") as f:
                    f.seek(max(0,f.seek(0,2)-2600))
                    last=f.read().decode("utf-8",errors="replace").strip().splitlines()[-12:]
                    updated=datetime.fromtimestamp(os.fstat(f.fileno()).st_mtime).strftime("%H:%M:%S")
            except FileNotFoundError:last=[]
            message="運転中" if active else "待機中"
            page="""<!DOCTYPE html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
            <title>金壁リセマラ</title><style>body{font:17px/1.55 system-ui;background:#14131c;color:#faf9ff;max-width:34rem;margin:2rem auto;padding:0 1rem}button{width:100%;padding:.9rem;margin:.35rem 0;border:0;border-radius:.6rem;font:inherit;font-weight:bold}button.primary{background:#fbd96b}pre{white-space:pre-wrap;font:14px/1.5 system-ui}small{color:#c9c7d6}</style><h1>金壁リセマラ</h1>"""
            page+="<script>document.addEventListener('visibilitychange',()=>{if(!document.hidden)location.reload()})</script>"
            page+=f"<p>{message}　<small>検証版 {VERSION}</small></p>"
            if worker.message:page+="<p role='status'>"+html.escape(worker.message)+"</p>"
            page+="<form method='post'>"
            for value,title in (("hold","開始　未判定は手元で確認"),("run","開始　未判定回も飛ばす"),("check","画面判定だけ試す"),("test-notify","通知をテスト"),("stop","自動操作を停止")):
                disabled=(active and value!="stop") or (not active and value=="stop")
                page+=f"<button name='mode' value='{value}' class='{ 'primary' if value=='hold' else ''}' {'disabled' if disabled else ''}>{title}</button>"
            page+="</form><small>開始するとゲームが開きます。通常オールゾーン1-1から使ってください。ホームに戻ると次の前面確認で操作を止めます。</small>"
            if last:page+=f"<p><small>直近の実行ログ　{updated}</small></p><pre>"+html.escape("\n".join(last))+"</pre>"
            page+=f"<p><a style='color:#79b7ff' href='{path}/log'>実行ログを保存</a></p>"
            self.reply(200,page)

        def do_POST(self):
            if self.path!=path or self.headers.get("Origin")!=BASE or self.headers.get("Host")!=f"127.0.0.1:{PORT}":
                return self.reply(403,"Forbidden")
            try:length=int(self.headers.get("Content-Length","0"))
            except ValueError:length=0
            if not 0<length<256:return self.reply(400,"Bad request")
            mode=parse_qs(self.rfile.read(length).decode()).get("mode",[""])[0]
            if mode not in ("run","hold","check","test-notify","stop"):return self.reply(400,"Bad request")
            if mode=="stop":
                worker.stop()
            elif not worker.active:
                worker.start(ROOT/"phone.py",mode)
            self.send_response(303);self.send_header("Location",path);self.end_headers()
        def log_message(self,*args):pass

    class WatchedServer(HTTPServer):
        def service_actions(self):
            worker.poll()

    with WatchedServer(("127.0.0.1",PORT),Panel) as server:
        if not Path(loopctrl_rpc.STORE).exists():
            subprocess.run([sys.executable,str(ROOT/"loopctrl_rpc.py"),"--host",HOST,"pair","--name","NecroGold"],check=True)
        url=BASE+path
        print("Safariに表示したページはホーム画面に追加できます。\n"+url,flush=True)
        def open_panel():
            try:rpc("open_url",{"url":url})
            except (Exception,SystemExit):print("自動で開けなければ、上のURLをSafariで開いてください。",flush=True)
        # Serve before opening Safari. The runner may wait for Safari to settle.
        timer=Timer(.2,open_panel);timer.daemon=True;timer.start()
        try:server.serve_forever()
        finally:
            worker.close()


if __name__=="__main__":
    try:serve()
    except KeyboardInterrupt:pass
    except OSError as exc:
        if exc.errno == 98:
            raise SystemExit("旧パネルが起動中です。iSHをアプリ切替画面で終了して開き直し、新しいフォルダで起動してください。")
        raise
