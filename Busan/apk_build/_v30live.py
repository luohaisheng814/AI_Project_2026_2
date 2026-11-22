# -*- coding: utf-8 -*-
"""v3.0 线上 Pages 探针：确认部署后的昼夜按钮与本地一致（390×844）。"""
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
PORT = 9235


def main():
    profile = os.path.join(HERE, "_chrome_probe_live30")
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
        js("localStorage.removeItem('busan_theme');")
        cmd("Page.navigate", {"url": PAGE})
        time.sleep(5.0)

        print("URL:", js("location.href"), "SECURE:", js("isSecureContext"))
        print("V30:", js("(function(){var b=document.getElementById('themeBtn');"
                        "return JSON.stringify({btn:!!b,mode:BusanUI.themeMode(),dataMode:b?b.getAttribute('data-mode'):'',"
                        "icon:document.getElementById('themeIcon').textContent,night:BusanUI.isNight(),"
                        "theme:document.querySelector('meta[name=theme-color]').content,"
                        "cycle:typeof BusanUI.cycleTheme});})()"))
        print("SW CACHE:", js("caches.keys().then(function(k){return JSON.stringify(k);})"))
        shot("v30_online_auto.png")

        js("document.getElementById('themeBtn').click();")
        time.sleep(0.9)
        print("TAP1:", js("JSON.stringify({mode:BusanUI.themeMode(),night:BusanUI.isNight(),"
                          "icon:document.getElementById('themeIcon').textContent,"
                          "toast:document.getElementById('themeToast').textContent})"))
        js("document.getElementById('themeBtn').click();")
        time.sleep(0.8)
        print("TAP2:", js("JSON.stringify({mode:BusanUI.themeMode(),night:BusanUI.isNight(),"
                          "icon:document.getElementById('themeIcon').textContent,"
                          "theme:document.querySelector('meta[name=theme-color]').content})"))
        shot("v30_online_night.png")

        print("ERRORS:", js("JSON.stringify(window.__errs||[])"))
        ws.close()
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
