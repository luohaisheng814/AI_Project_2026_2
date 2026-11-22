# -*- coding: utf-8 -*-
"""v2.8 探针：先权限 → 定位 → 天气 → 结合手机本地时间的综合推荐（真浏览器 390×844）。

检查项：
  1. mix.js 是否加载、index.html 无 JS 报错
  2. 点右上角天气按钮：无权限时先出权限卡（写明坐标/天气/时间三步）
  3. 模拟授权（注入坐标）后点“允许定位并继续”：走完 mixFlow，出综合结论
     - 三枚胶囊（时间/天气/距离）
     - 3 个可点选项
     - 气泡第二行有 “几点 · 时段 · 最近景点”
  4. 点“附近”：同样走综合链路，标签换成「附近 · 综合推荐」
  5. 换一个钟点重排：21 点 vs 10 点，首选顺序应不同（时间真的参与了打分）
  6. 夜间模式下胶囊/结论仍可读（配色不是白底）
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
PORT = 9230
HTTP_PORT = 8793
PAGE = "http://127.0.0.1:%d/index.html" % HTTP_PORT
POS = "35.1000,129.0350"          # 南浦洞一带（札嘎其走路约 0.5 km）
LAT, LNG = 35.1000, 129.0350


def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(HTTP_PORT),
                            "--bind", "127.0.0.1", "--directory", ASSETS],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    profile = os.path.join(HERE, "_chrome_probe28")
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

        print("BOOT:", js("JSON.stringify({mix:typeof BusanMix,"
                          "fab:!!document.getElementById('wxFab'),"
                          "pillCtx:!!document.getElementById('wxCtx'),"
                          "native:typeof BusanMix!=='undefined'&&typeof BusanMix.ranked==='function',"
                          "hour:new Date().getHours(),night:BusanUI.isNight(),"
                          "fabText:document.getElementById('wxFab').textContent.trim()})"))
        print("PILL CTX:", js("document.getElementById('wxCtx').textContent"))
        shot("v28_home_day.png")

        # 1) 无权限点天气按钮 → 先出权限卡
        js("document.getElementById('wxFab').click();")
        time.sleep(1.2)
        print("PERM CARD:", js("(function(){var b=document.querySelector('#chat .msg.bot:last-child .bubble');"
                               "return JSON.stringify({permacts:document.querySelectorAll('#chat .permact').length,"
                               "grant:!!document.querySelector('.act-grant'),"
                               "tag:(b.querySelector('.badge')||{}).textContent,"
                               "hasThreeSteps:/坐标/.test(b.textContent)&&/天气/.test(b.textContent)&&/时间/.test(b.textContent),"
                               "pillHidden:document.getElementById('wxPill').hidden});})()"))
        shot("v28_wx_permission.png")

        # 2) 模拟系统授权成功：注入坐标，再点“允许定位并继续”
        js("window.__busanLocUpdate(%s, 12, 'probe', Date.now());" % POS)
        time.sleep(0.4)
        print("PERM STATE:", js("BusanUI.weatherPermission()"))
        js("document.querySelector('.act-grant').click();")
        time.sleep(6.0)
        print("MIX WEATHER:", js("(function(){var b=document.querySelector('#chat .msg.bot:last-child .bubble');"
                                 "return JSON.stringify({tag:(b.querySelector('.badge')||{}).textContent,"
                                 "chips:b.querySelectorAll('.mixchip').length,"
                                 "chipTexts:Array.from(b.querySelectorAll('.mixchip')).map(function(x){return x.textContent;}),"
                                 "choices:b.querySelectorAll('.choice').length,"
                                 "hasAdvice:/一句话建议/.test(b.textContent),"
                                 "hasTime:/\\d\\d:\\d\\d/.test((b.querySelector('.mixchip')||{}).textContent||''),"
                                 "pillHidden:document.getElementById('wxPill').hidden});})()"))
        shot("v28_mix_result.png")

        # 2b) 滚到最后一条结论的顶部，单独留一张「三枚胶囊 + 时间上下文」的证据
        js("(function(){var c=document.getElementById('chat');var b=document.querySelectorAll('#chat .msg.bot');"
           "var last=b[b.length-1];var r=last.getBoundingClientRect();"
           "c.scrollTop += (r.top - c.getBoundingClientRect().top + 2);})()")
        time.sleep(0.6)
        print("CHIPS RECTS:", js("(function(){var r=Array.from(document.querySelectorAll('#chat .mixrow .mixchip'));"
                                 "return JSON.stringify(r.map(function(x){var b=x.getBoundingClientRect();"
                                 "return {t:x.textContent,w:Math.round(b.width),h:Math.round(b.height)};}));})()"))
        shot("v28_mix_chips.png")

        # 3) 点“附近”：同样先定位再综合
        js("document.getElementById('gps').click();")
        time.sleep(6.0)
        print("MIX NEARBY:", js("(function(){var b=document.querySelector('#chat .msg.bot:last-child .bubble');"
                                "return JSON.stringify({tag:(b.querySelector('.badge')||{}).textContent,"
                                "chips:b.querySelectorAll('.mixchip').length,"
                                "choices:b.querySelectorAll('.choice').length,"
                                "first:(b.querySelector('.choice .cname')||{}).textContent});})()"))
        shot("v28_nearby_result.png")

        # 4) 时间真的参与打分：同一位置同一天气，21 点 vs 10 点
        print("TIME SHIFT:", js("(function(){var pos={lat:%f,lng:%f};var w={cls:'rain',temp:14,wind:3,precipProb:85};"
                                "var a=BusanMix.ranked(BusanMix.ctxOf({pos:pos,w:w,hour:21}),3).map(function(r){return r.id;});"
                                "var b=BusanMix.ranked(BusanMix.ctxOf({pos:pos,w:w,hour:10}),3).map(function(r){return r.id;});"
                                "return JSON.stringify({night:a,day:b,changed:JSON.stringify(a)!==JSON.stringify(b)});})()" % (LAT, LNG)))

        # 5) 夜间可读性
        js("BusanUI.setThemeMode('night');")
        time.sleep(1.2)
        print("NIGHT MIX:", js("(function(){var c=document.querySelector('#chat .mixchip');"
                               "return JSON.stringify({night:BusanUI.isNight(),"
                               "chipBg:c?getComputedStyle(c).backgroundColor:'',"
                               "chipColor:c?getComputedStyle(c).color:'',"
                               "theme:document.querySelector('meta[name=theme-color]').content});})()"))
        shot("v28_night_mix.png")

        js("BusanUI.setThemeMode('day');")
        time.sleep(0.8)
        print("BACK DAY:", js("JSON.stringify({night:BusanUI.isNight(),theme:document.querySelector('meta[name=theme-color]').content})"))
        shot("v28_day_after.png")

        # 6) 综合结论里的选项能点开（走原有问答链路）
        print("CHOICE CLICK:", js("(function(){var b=document.querySelector('#chat .msg.bot:last-child .choice');"
                                  "if(!b) return 'no-choice';var q=b.getAttribute('data-q');b.click();return q;})()"))
        time.sleep(2.2)
        print("AFTER CHOICE:", js("JSON.stringify({bots:document.querySelectorAll('#chat .msg.bot').length,"
                                  "errors:(window.__errs||[]).length})"))

        print("ERRORS:", js("JSON.stringify(window.__errs||[])"))
        ws.close()
    finally:
        proc.terminate()
        srv.terminate()


if __name__ == "__main__":
    main()
