# -*- coding: utf-8 -*-
"""v2.7 线上验证：https 下 manifest / sw(2.7) / 右上角天气按钮 / 昼夜 class。"""
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
PORT = 9229


def main():
    profile = os.path.join(HERE, "_chrome_probe_live27")
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
        print("SECURE:", js("isSecureContext"))
        print("V27:", js("JSON.stringify({fab:!!document.getElementById('wxFab'),"
                          "pillHidden:document.getElementById('wxPill').hidden,"
                          "fabText:document.getElementById('wxFab').textContent.trim().replace(/\\s+/g,' '),"
                          "oldStrip:!!document.getElementById('wxStrip'),"
                          "night:document.body.classList.contains('night'),"
                          "hour:new Date().getHours(),"
                          "theme:document.querySelector('meta[name=theme-color]').content})"))
        print("MANIFEST:", js("fetch('manifest.webmanifest').then(r=>r.status+' '+r.headers.get('content-type'))"
                              ".catch(e=>'ERR:'+e)"))
        print("SW:", js("navigator.serviceWorker.getRegistration().then(r=>r?'registered '+r.scope:'none')"
                        ".catch(e=>'ERR:'+e)"))
        print("CACHE:", js("caches.keys().then(k=>JSON.stringify(k)).catch(e=>'ERR:'+e)"))
        print("PERM FLOW:", js("(function(){document.getElementById('wxFab').click();"
                              "return 'clicked';})()"))
        time.sleep(1.4)
        print("PERM CARD:", js("JSON.stringify({permacts:document.querySelectorAll('#chat .permact').length,"
                              "grant:!!document.querySelector('.act-grant'),"
                              "pillHidden:document.getElementById('wxPill').hidden})"))
        print("NIGHT CSS:", js("[].some.call(document.styleSheets,function(s){try{return [].some.call(s.cssRules,"
                               "function(r){return (r.cssText||'').indexOf('body.night')>-1;});}catch(e){return false;}})"))
        print("LIVE:", js("fetch(BusanWeather.url(35.1796,129.0756)).then(r=>r.text())"
                          ".then(t=>{var j=JSON.parse(t);return JSON.stringify(j.current);})"
                          ".catch(e=>'ERR:'+e)"))

        data = cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        p = os.path.join(HERE, "v27_online_pages.png")
        with open(p, "wb") as f:
            f.write(base64.b64decode(data["data"]))
        print("screenshot:", p, os.path.getsize(p) // 1024, "KB")
        print("ERRORS:", js("JSON.stringify(window.__errs||[])"))
        ws.close()
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
