# -*- coding: utf-8 -*-
"""v3.0 探针：页头昼夜切换按钮（真浏览器 390×844，另测 360×740 不溢出）。

检查项：
  1. 启动为「自动」：🌓、data-mode=auto、配色按当前钟点
  2. 点 1 次 → 白天：☀️、body 去 night、theme-color #0a4e63、提示出现
  3. 点 2 次 → 夜间：🌙、body.night、theme-color #072e3c、按钮深色
  4. 点 3 次 → 回到自动：🌓、按钟点、提示文案正确
  5. 提示 1.8 秒后自动消失
  6. 手动选择持久化：刷新后仍是夜间（即使白天）
  7. 切韩语：aria-label/tooltip 跟着变，状态不丢
  8. 布局：按钮在天气按钮左侧、不重叠；360 宽无横向溢出
  9. 不回退：天气按钮仍出权限卡、推荐条仍可展开
"""
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
PORT = 9234
HTTP_PORT = 8795
PAGE = "http://127.0.0.1:%d/index.html" % HTTP_PORT
LAT, LNG = 35.1000, 129.0350


def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(HTTP_PORT),
                            "--bind", "127.0.0.1", "--directory", ASSETS],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    profile = os.path.join(HERE, "_chrome_probe30")
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
        time.sleep(3.5)
        js("localStorage.removeItem('busan_theme'); localStorage.removeItem('busan_qrec');")
        cmd("Page.navigate", {"url": PAGE})
        time.sleep(3.0)

        def state():
            return js("(function(){var b=document.getElementById('themeBtn');"
                      "var t=document.getElementById('themeToast');"
                      "return JSON.stringify({mode:BusanUI.themeMode(),dataMode:b.getAttribute('data-mode'),"
                      "icon:document.getElementById('themeIcon').textContent,"
                      "pressed:b.getAttribute('aria-pressed'),"
                      "night:BusanUI.isNight(),"
                      "theme:document.querySelector('meta[name=theme-color]').content,"
                      "bg:getComputedStyle(b).backgroundColor,"
                      "toastHidden:t.hidden,toastShown:t.classList.contains('show'),toastText:t.textContent,"
                      "hour:new Date().getHours()});})()")

        print("BOOT:", state())
        shot("v30_theme_auto.png")

        # 1) 点一次 → 白天
        js("document.getElementById('themeBtn').click();")
        time.sleep(1.0)
        print("TAP1(day):", state())
        shot("v30_theme_day.png")

        # 2) 再点 → 夜间
        js("document.getElementById('themeBtn').click();")
        time.sleep(0.8)
        print("TAP2(night):", state())
        shot("v30_theme_night.png")

        # 3) 提示 1.8 秒后消失
        time.sleep(2.4)
        print("TOAST AFTER 2.4s:", js("(function(){var t=document.getElementById('themeToast');"
                                      "return JSON.stringify({hidden:t.hidden,shown:t.classList.contains('show')});})()"))

        # 4) 持久化：夜间状态下刷新（当前是白天钟点）
        cmd("Page.navigate", {"url": PAGE})
        time.sleep(3.0)
        print("RELOAD(manual night):", state())

        # 5) 再点一次 → 回到自动
        js("document.getElementById('themeBtn').click();")
        time.sleep(0.9)
        print("TAP3(auto):", state())

        # 6) 韩语文案
        js("document.querySelector('.langs button[data-lang=\"ko\"]').click();")
        time.sleep(1.6)
        print("KO:", js("(function(){var b=document.getElementById('themeBtn');"
                        "return JSON.stringify({mode:BusanUI.themeMode(),title:b.title,"
                        "aria:b.getAttribute('aria-label'),icon:document.getElementById('themeIcon').textContent,"
                        "dataMode:b.getAttribute('data-mode')});})()"))
        shot("v30_theme_ko.png")
        js("document.querySelector('.langs button[data-lang=\"zh\"]').click();")
        time.sleep(1.4)

        # 7) 布局：与天气按钮同行不重叠
        print("LAYOUT:", js("(function(){var t=document.getElementById('themeBtn').getBoundingClientRect();"
                            "var w=document.getElementById('wxFab').getBoundingClientRect();"
                            "return JSON.stringify({theme:{x:Math.round(t.x),y:Math.round(t.y),w:Math.round(t.width),h:Math.round(t.height)},"
                            "fab:{x:Math.round(w.x),y:Math.round(w.y)},"
                            "noOverlap:t.right<=w.left+1,"
                            "headerH:Math.round(document.querySelector('header').getBoundingClientRect().height),"
                            "overflow:document.documentElement.scrollWidth>window.innerWidth});})()"))

        # 8) 360 宽不溢出
        cmd("Emulation.setDeviceMetricsOverride",
            {"width": 360, "height": 740, "deviceScaleFactor": 2, "mobile": True})
        time.sleep(1.2)
        print("NARROW 360:", js("(function(){var t=document.getElementById('themeBtn').getBoundingClientRect();"
                                "var w=document.getElementById('wxFab').getBoundingClientRect();"
                                "return JSON.stringify({innerW:window.innerWidth,scrollW:document.documentElement.scrollWidth,"
                                "noOverlap:t.right<=w.left+1,"
                                "titleW:Math.round(document.getElementById('title').getBoundingClientRect().width)});})()"))
        shot("v30_theme_360.png")
        cmd("Emulation.setDeviceMetricsOverride",
            {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True})
        time.sleep(0.6)

        # 9) 不回退：天气仍先权限卡；推荐条仍能展开
        js("document.getElementById('wxFab').click();")
        time.sleep(1.3)
        print("WX PERM:", js("(function(){var b=document.querySelector('#chat .msg.bot:last-child .bubble');"
                             "return JSON.stringify({grant:!!document.querySelector('.act-grant'),"
                             "tag:(b.querySelector('.badge')||{}).textContent});})()"))
        js("document.getElementById('qrecToggle').click();")
        time.sleep(0.8)
        print("QREC:", js("(function(){var row=document.querySelector('.qrec-body .quick');"
                          "return JSON.stringify({open:document.getElementById('qrec').classList.contains('open'),"
                          "chips:row.querySelectorAll('.pick').length,scrollable:row.scrollWidth>row.clientWidth+1});})()"))

        # 10) 手动锁夜间后，回到前台触发的复判不应把它改回白天
        js("BusanUI.setThemeMode('night');")
        print("LOCK NIGHT:", js("JSON.stringify({mode:BusanUI.themeMode(),night:BusanUI.isNight()})"))
        js("document.dispatchEvent(new Event('visibilitychange'));")
        time.sleep(1.0)
        print("AFTER VISIBILITY:", js("JSON.stringify({mode:BusanUI.themeMode(),night:BusanUI.isNight(),"
                                       "theme:document.querySelector('meta[name=theme-color]').content,"
                                       "icon:document.getElementById('themeIcon').textContent})"))

        print("ERRORS:", js("JSON.stringify(window.__errs||[])"))
        ws.close()
    finally:
        proc.terminate()
        srv.terminate()


if __name__ == "__main__":
    main()
