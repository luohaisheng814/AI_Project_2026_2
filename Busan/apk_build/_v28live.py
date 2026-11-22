# -*- coding: utf-8 -*-
"""v2.8 线上验证：https 下 mix.js 是否上线、缓存名、点按钮的权限卡、注入坐标后的综合结论。"""
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
PORT = 9231


def main():
    profile = os.path.join(HERE, "_chrome_probe_live28")
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
            return r.get("result", {}).get("value")

        cmd("Page.enable")
        cmd("Runtime.enable")
        cmd("Page.addScriptToEvaluateOnNewDocument", {"source":
            "window.__errs=[];window.onerror=function(m,s,l,c,e){window.__errs.push(String(m)+' @'+l);};"
            "window.addEventListener('unhandledrejection',function(e){window.__errs.push('rej:'+String(e.reason));});"})
        cmd("Emulation.setDeviceMetricsOverride",
            {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True})
        cmd("Page.navigate", {"url": PAGE})
        time.sleep(5.0)

        print("URL:", js("location.href"))
        print("SECURE:", js("isSecureContext"))
        print("V28:", js("JSON.stringify({mix:typeof BusanMix,"
                          "mixFn:typeof BusanMix==='object'&&typeof BusanMix.ranked==='function',"
                          "fab:!!document.getElementById('wxFab'),"
                          "pillCtx:!!document.getElementById('wxCtx'),"
                          "pillCtxText:document.getElementById('wxCtx').textContent,"
                          "oldStrip:!!document.getElementById('wxStrip'),"
                          "night:document.body.classList.contains('night'),"
                          "hour:new Date().getHours(),"
                          "theme:document.querySelector('meta[name=theme-color]').content})"))
        print("MIXJS HTTP:", js("fetch('mix.js').then(r=>r.status+' '+r.headers.get('content-length'))"
                                ".catch(e=>'ERR:'+e)"))
        print("MANIFEST:", js("fetch('manifest.webmanifest').then(r=>r.status+' '+r.headers.get('content-type'))"
                              ".catch(e=>'ERR:'+e)"))
        print("SW:", js("navigator.serviceWorker.getRegistration().then(r=>r?'registered '+r.scope:'none')"
                        ".catch(e=>'ERR:'+e)"))
        print("CACHE:", js("caches.keys().then(k=>JSON.stringify(k)).catch(e=>'ERR:'+e)"))

        print("PERM FLOW:", js("(function(){document.getElementById('wxFab').click();return 'clicked';})()"))
        time.sleep(1.4)
        print("PERM CARD:", js("JSON.stringify({permacts:document.querySelectorAll('#chat .permact').length,"
                              "grant:!!document.querySelector('.act-grant'),"
                              "tag:(document.querySelector('#chat .msg.bot:last-child .badge')||{}).textContent,"
                              "pillHidden:document.getElementById('wxPill').hidden})"))

        # 线上安全上下文里注入坐标，点“允许”→ 真跑一次综合推荐（会联网取 Open-Meteo）
        js("window.__busanLocUpdate(35.1000, 129.0350, 15, 'probe', Date.now());")
        time.sleep(0.4)
        js("document.querySelector('.act-grant').click();")
        time.sleep(7.0)
        print("ONLINE MIX:", js("(function(){var b=document.querySelector('#chat .msg.bot:last-child .bubble');"
                                "return JSON.stringify({tag:(b.querySelector('.badge')||{}).textContent,"
                                "chips:b.querySelectorAll('.mixchip').length,"
                                "chipTexts:Array.from(b.querySelectorAll('.mixchip')).map(function(x){return x.textContent;}),"
                                "choices:b.querySelectorAll('.choice').length,"
                                "first:(b.querySelector('.choice .cname')||{}).textContent,"
                                "hasRule:/06:00–18:59/.test(b.textContent)});})()"))

        data = cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        p = os.path.join(HERE, "v28_online_pages.png")
        with open(p, "wb") as f:
            f.write(base64.b64decode(data["data"]))
        print("screenshot:", p, os.path.getsize(p) // 1024, "KB")
        print("NIGHT CSS:", js("[].some.call(document.styleSheets,function(s){try{return [].some.call(s.cssRules,"
                               "function(r){return (r.cssText||'').indexOf('body.night')>-1;});}catch(e){return false;}})"))
        print("ERRORS:", js("JSON.stringify(window.__errs||[])"))
        ws.close()
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
