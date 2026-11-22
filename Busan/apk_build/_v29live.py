# -*- coding: utf-8 -*-
"""v2.9 线上 Pages 探针：确认部署后的个性化推荐条与本地一致（真浏览器 390×844）。"""
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
PORT = 9233


def main():
    profile = os.path.join(HERE, "_chrome_probe_live29")
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

        ws = websocket.create_connection(ws_url, timeout=40)
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
            res = r.get("result", {})
            if res.get("subtype") == "error":
                print("JS ERROR:", res.get("description"))
            return res.get("value")

        def shot(name):
            data = cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
            p = os.path.join(HERE, name)
            with open(p, "wb") as f:
                f.write(base64.b64decode(data["data"]))
            print("screenshot:", p, os.path.getsize(p) // 1024, "KB")

        cmd("Page.enable")
        cmd("Runtime.enable")
        cmd("Page.addScriptToEvaluateOnNewDocument", {"source":
            "window.__errs=[];window.onerror=function(m,s,l,c,e){window.__errs.push(String(m)+' @'+l);};"
            "window.addEventListener('unhandledrejection',function(e){window.__errs.push('rej:'+String(e.reason));});"})
        cmd("Emulation.setDeviceMetricsOverride",
            {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True})
        cmd("Page.navigate", {"url": PAGE})
        time.sleep(5.0)
        js("localStorage.removeItem('busan_qrec');")
        cmd("Page.navigate", {"url": PAGE})
        time.sleep(5.0)

        print("URL:", js("location.href"), "SECURE:", js("isSecureContext"))
        print("V29:", js("(function(){var q=document.getElementById('qrec');"
                        "return JSON.stringify({qrec:!!q,open:q.classList.contains('open'),"
                        "bodyH:Math.round(document.getElementById('qrecBody').getBoundingClientRect().height),"
                        "title:document.querySelector('.qrec-title').textContent,"
                        "act:document.getElementById('qrecAct').textContent,"
                        "mix:typeof BusanMix});})()"))
        print("SW CACHE:", js("caches.keys().then(function(k){return JSON.stringify(k);})"))
        shot("v29_online_collapsed.png")

        js("document.getElementById('qrecToggle').click();")
        time.sleep(0.9)
        print("OPEN:", js("(function(){var row=document.querySelector('.qrec-body .quick');"
                          "var cs=Array.from(row.querySelectorAll('.pick'));"
                          "return JSON.stringify({open:document.getElementById('qrec').classList.contains('open'),"
                          "chips:cs.length,"
                          "oneRow:cs.every(function(c){return Math.round(c.getBoundingClientRect().top)===Math.round(cs[0].getBoundingClientRect().top);}),"
                          "scrollable:row.scrollWidth>row.clientWidth+1,"
                          "scrollW:row.scrollWidth,clientW:row.clientWidth});})()"))
        shot("v29_online_open.png")

        print("ERRORS:", js("JSON.stringify(window.__errs||[])"))
        ws.close()
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
