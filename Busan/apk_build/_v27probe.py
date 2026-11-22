# -*- coding: utf-8 -*-
"""v2.7 探针：右上角天气按钮 / 权限询问 / 10 秒气泡 / 滚开收起 / 按时间昼夜。"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

import websocket

CHROME = r"C:\Users\43763\AppData\Local\Google\Chrome\Application\chrome.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "android", "assets")
PORT = 9228
HTTP_PORT = 8792
PAGE = "http://127.0.0.1:%d/index.html" % HTTP_PORT


def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(HTTP_PORT),
                            "--bind", "127.0.0.1", "--directory", ASSETS],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    profile = os.path.join(HERE, "_chrome_probe27")
    proc = subprocess.Popen([
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--remote-allow-origins=*",
        "--remote-debugging-port=%d" % PORT, "--user-data-dir=" + profile,
        "--window-size=390,844", PAGE,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(1.0)
        for _ in range(20):
            try:
                urllib.request.urlopen(PAGE, timeout=1).read()
                break
            except Exception:
                time.sleep(0.3)

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
        time.sleep(3.5)

        print("BOOT:", js("JSON.stringify({fab:!!document.getElementById('wxFab'),"
                          "pill:!!document.getElementById('wxPill'),"
                          "oldStrip:!!document.getElementById('wxStrip'),"
                          "fabText:document.getElementById('wxFab').textContent.trim(),"
                          "night:document.body.classList.contains('night'),"
                          "theme:document.querySelector('meta[name=theme-color]').content})"))

        print("FAB RECT:", js("(function(){var r=document.getElementById('wxFab').getBoundingClientRect();"
                              "var h=document.querySelector('header').getBoundingClientRect();"
                              "return JSON.stringify({fab:[Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)],"
                              "header:[Math.round(h.left),Math.round(h.top),Math.round(h.right),Math.round(h.bottom)],"
                              "vw:innerWidth,fabH:Math.round(r.height)});})()"))
        print("PILL HIDDEN:", js("document.getElementById('wxPill').hidden"))
        shot("v27_home_day.png")

        # 1) 点按钮：没有权限 → 先问，再申请
        js("document.getElementById('wxFab').click();")
        time.sleep(1.4)
        print("PERM CARD:", js("JSON.stringify({permacts:document.querySelectorAll('#chat .permact').length,"
                               "grant:!!document.querySelector('.act-grant'),"
                               "head:(document.querySelector('#chat .msg.bot:last-child .bubble')||{}).textContent.slice(0,90),"
                               "pillHidden:document.getElementById('wxPill').hidden})"))
        shot("v27_wx_permission.png")

        # 2) 模拟授权成功 + 已有天气：再点只露气泡
        js("BusanUI.setWeather('rain', 14); document.getElementById('wxFab').click();")
        time.sleep(0.8)
        print("PILL SHOWN:", js("JSON.stringify({hidden:document.getElementById('wxPill').hidden,"
                                "text:document.getElementById('wxText').textContent,"
                                "fab:document.getElementById('wxFab').textContent.trim(),"
                                "on:document.getElementById('wxFab').classList.contains('on'),"
                                "expanded:document.getElementById('wxFab').getAttribute('aria-expanded')})"))
        shot("v27_wx_pill.png")

        # 3) 短暂显示后自动收起
        js("BusanUI.showWeatherPill(1200);")
        time.sleep(1.5)
        print("AUTO HIDE:", js("JSON.stringify({hidden:document.getElementById('wxPill').hidden,"
                               "expanded:document.getElementById('wxFab').getAttribute('aria-expanded')})"))

        # 4) 往上翻（离开首页）自动收起
        js("BusanUI.ask('甘川文化村 门票');")
        time.sleep(2.6)
        js("BusanUI.showWeatherPill(60000);")
        time.sleep(0.4)
        before = js("document.getElementById('wxPill').hidden")
        js("(function(){var c=document.getElementById('chat'); c.scrollTop=0; c.dispatchEvent(new Event('scroll'));})()")
        time.sleep(0.5)
        print("SCROLL AWAY:", js("JSON.stringify({beforeScroll:" + ("false" if before is False else "true") +
                                 ",hiddenAfter:document.getElementById('wxPill').hidden})"))

        # 5) 夜间模式
        js("BusanUI.setThemeMode('night');")
        time.sleep(1.2)
        print("NIGHT:", js("JSON.stringify({night:document.body.classList.contains('night'),"
                           "theme:document.querySelector('meta[name=theme-color]').content,"
                           "bodyBg:getComputedStyle(document.body).backgroundColor,"
                           "headerBg:getComputedStyle(document.querySelector('header')).backgroundImage,"
                           "bubble:getComputedStyle(document.querySelector('#chat .msg.bot:last-child .bubble')).backgroundColor,"
                           "ink:getComputedStyle(document.body).color})"))
        shot("v27_night.png")

        # 6) 白天模式
        js("BusanUI.setThemeMode('day');")
        time.sleep(1.0)
        print("DAY:", js("JSON.stringify({night:document.body.classList.contains('night'),"
                         "theme:document.querySelector('meta[name=theme-color]').content,"
                         "bodyBg:getComputedStyle(document.body).backgroundColor})"))
        shot("v27_day_after.png")

        # 7) 自动模式（按当前钟点）
        print("AUTO:", js("JSON.stringify({mode:BusanUI.setThemeMode('auto'),"
                          "hour:new Date().getHours(),night:BusanUI.isNight()})"))

        print("LIVE FETCH:", js("fetch(BusanWeather.url(35.1796,129.0756)).then(r=>r.text())"
                               ".then(t=>{var j=JSON.parse(t);return JSON.stringify(j.current);})"
                               ".catch(e=>'ERR:'+e)"))
        print("ERRORS:", js("JSON.stringify(window.__errs||[])"))
        ws.close()
    finally:
        proc.terminate()
        srv.terminate()


if __name__ == "__main__":
    main()
