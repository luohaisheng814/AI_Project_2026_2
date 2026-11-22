# -*- coding: utf-8 -*-
"""线上 GitHub Pages 验证：https 下 manifest / service worker / 图标 / 首页可访问。"""
import base64
import json
import os
import subprocess
import time
import urllib.request

import websocket

CHROME = r"C:\Users\43763\AppData\Local\Google\Chrome\Application\chrome.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = "https://luohaisheng814.github.io/AI_Project_2026_2/"
PORT = 9227


def main():
    profile = os.path.join(HERE, "_chrome_probe_live26")
    proc = subprocess.Popen([
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--remote-allow-origins=*",
        "--remote-debugging-port=%d" % PORT, "--user-data-dir=" + profile,
        "--window-size=390,844", PAGE,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ws_url = None
        for _ in range(40):
            try:
                data = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json" % PORT))
                for t in data:
                    if t.get("type") == "page":
                        ws_url = t["webSocketDebuggerUrl"]
                        break
                if ws_url:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        if not ws_url:
            raise SystemExit("Chrome CDP 未就绪")

        ws = websocket.create_connection(ws_url, timeout=30)
        mid = [0]

        def cmd(method, params=None):
            mid[0] += 1
            ws.send(json.dumps({"id": mid[0], "method": method, "params": params or {}}))
            while True:
                msg = json.loads(ws.recv())
                if msg.get("id") == mid[0]:
                    return msg.get("result", {})

        def js(expr):
            r = cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
            return r.get("result", {}).get("value")

        cmd("Page.enable")
        cmd("Runtime.enable")
        cmd("Page.addScriptToEvaluateOnNewDocument", {"source":
            "window.__errs=[];window.onerror=function(m,s,l,c,e){window.__errs.push(String(m)+' @'+l);};"})
        cmd("Emulation.setDeviceMetricsOverride",
            {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True})
        cmd("Page.navigate", {"url": PAGE})
        time.sleep(5.0)

        print("URL:", js("location.href"))
        print("TITLE:", js("document.title"))
        print("SECURE:", js("isSecureContext"))
        print("MANIFEST:", js("fetch('manifest.webmanifest').then(r=>r.status+' '+r.headers.get('content-type'))"
                              ".catch(e=>'ERR:'+e)"))
        print("MANIFEST BODY:", js("fetch('manifest.webmanifest').then(r=>r.json())"
                                   ".then(j=>JSON.stringify({name:j.name,display:j.display,start:j.start_url,"
                                   "icons:(j.icons||[]).length}))"))
        print("SW:", js("navigator.serviceWorker.getRegistration().then(r=>r?'registered '+r.scope:'none')"
                        ".catch(e=>'ERR:'+e)"))
        print("CACHE:", js("caches.keys().then(k=>JSON.stringify(k)).catch(e=>'ERR:'+e)"))
        print("CACHE HIT:", js("caches.match('./index.html').then(r=>r?'index cached':'MISSING')"
                               ".catch(e=>'ERR:'+e)"))
        print("ICONS:", js("Promise.all(['icon-180.png','icon-192.png','icon-512.png']"
                           ".map(f=>fetch(f).then(r=>f+':'+r.status))).then(a=>a.join(' | '))"))
        print("QUICK:", js("document.querySelectorAll('.quick .pick').length"))
        print("WXBAR:", js("document.getElementById('wxText').textContent"))

        data = cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        path = os.path.join(HERE, "v26_online_pages.png")
        with open(path, "wb") as f:
            f.write(base64.b64decode(data["data"]))
        print("screenshot:", path, os.path.getsize(path) // 1024, "KB")
        print("ERRORS:", js("JSON.stringify(window.__errs||[])"))
        ws.close()
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
