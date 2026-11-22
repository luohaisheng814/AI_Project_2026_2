# -*- coding: utf-8 -*-
"""v2.6 UI + PWA 探针。

与 v2.5 的区别：用本地 http 服务打开页面（file:// 下 service worker 不注册），
因此能真实检验 manifest / sw.js / 离线缓存，同时截 iPhone 尺寸、深色模式、
平板宽屏、360px 窄屏四组图。
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
PORT = 9226
HTTP_PORT = 8791
PAGE = "http://127.0.0.1:%d/index.html" % HTTP_PORT


def main():
    py = sys.executable
    srv = subprocess.Popen([py, "-m", "http.server", str(HTTP_PORT), "--bind", "127.0.0.1",
                            "--directory", ASSETS],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    profile = os.path.join(HERE, "_chrome_probe26")
    proc = subprocess.Popen([
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--remote-allow-origins=*",
        "--remote-debugging-port=%d" % PORT, "--user-data-dir=" + profile,
        "--window-size=390,844", PAGE,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(1.0)
        # 等 http 服务起来
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
            res = r.get("result", {})
            if res.get("subtype") == "error":
                return "EVALERR:" + str(res.get("description"))
            return res.get("value")

        def shot(name):
            data = cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
            path = os.path.join(HERE, name)
            with open(path, "wb") as f:
                f.write(base64.b64decode(data["data"]))
            print("screenshot:", path, os.path.getsize(path) // 1024, "KB")

        def metrics(w, h):
            cmd("Emulation.setDeviceMetricsOverride",
                {"width": w, "height": h, "deviceScaleFactor": 2 if w < 500 else 1, "mobile": True})
            time.sleep(0.6)

        cmd("Page.enable")
        cmd("Runtime.enable")
        cmd("Page.addScriptToEvaluateOnNewDocument", {"source":
            "window.__errs=[];window.onerror=function(m,s,l,c,e){window.__errs.push(String(m)+' @'+l);};"
            "window.addEventListener('unhandledrejection',function(e){window.__errs.push('rej:'+String(e.reason));});"})
        metrics(390, 844)
        cmd("Page.navigate", {"url": PAGE})
        time.sleep(3.5)

        print("MODULES:", js("JSON.stringify({ui:!!window.BusanUI,wx:!!window.BusanWeather,rt:!!window.BusanRating,"
                             "live:!!window.BusanLive,wxText:(document.getElementById('wxText')||{}).textContent,"
                             "quick:document.querySelectorAll('.quick .pick').length})"))

        # 1) PWA 安装条件
        print("MANIFEST:", js("fetch('manifest.webmanifest').then(r=>r.status+' '+r.headers.get('content-type'))"
                              ".catch(e=>'ERR:'+e)"))
        print("MANIFEST BODY:", js("fetch('manifest.webmanifest').then(r=>r.json())"
                                   ".then(j=>JSON.stringify({name:j.name,short:j.short_name,display:j.display,"
                                   "start:j.start_url,icons:(j.icons||[]).length,theme:j.theme_color}))"
                                   ".catch(e=>'ERR:'+e)"))
        print("SW:", js("navigator.serviceWorker.getRegistration().then(r=>r?'registered scoped '+r.scope:'none')"
                        ".catch(e=>'ERR:'+e)"))
        print("CACHE:", js("caches.keys().then(k=>'keys='+JSON.stringify(k)).catch(e=>'ERR:'+e)"))
        print("CACHE HIT:", js("caches.match('./index.html').then(r=>r?'index cached':'index MISSING')"
                               ".catch(e=>'ERR:'+e)"))
        print("ICONS:", js("Promise.all(['icon-180.png','icon-192.png','icon-512.png']"
                           ".map(f=>fetch(f).then(r=>f+':'+r.status))).then(a=>a.join(' | '))"))
        print("HEAD META:", js("JSON.stringify({theme:(document.querySelector('meta[name=theme-color]')||{}).content,"
                               "capable:(document.querySelector('meta[name=apple-mobile-web-app-capable]')||{}).content,"
                               "status:(document.querySelector('meta[name=apple-mobile-web-app-status-bar-style]')||{}).content,"
                               "icon:(document.querySelector('link[rel=apple-touch-icon]')||{}).getAttribute,"
                               "manifest:!!document.querySelector('link[rel=manifest]')})"))
        shot("v26_home_iphone.png")

        # 2) 欢迎语的“今天天气适合去哪”入口
        print("WXCHIP:", js("(function(){var b=document.querySelector('.quick .pick[data-wx]');"
                            "if(!b)return 'NO CHIP';b.click();return 'clicked '+b.textContent;})()"))
        time.sleep(1.3)
        print("WXCARD:", js("JSON.stringify({chips:document.querySelectorAll('.wxchip').length,"
                            "choices:document.querySelectorAll('#chat .msg.bot:last-child .choice').length,"
                            "hasRating:!!document.querySelector('#chat .msg.bot:last-child .rating')})"))
        print("WXBAR:", js("document.getElementById('wxText').textContent"))
        shot("v26_wx_from_chip.png")

        # 2b) 手动给一个天气，渲染完整天气卡（离线/无定位时的可用路径）
        print("WXMANUAL:", js("JSON.stringify(BusanWeather.manual('rain', 14)||null)"))
        js("document.getElementById('wxBtn').click();")
        time.sleep(1.2)
        print("WXCARD2:", js("JSON.stringify({chips:document.querySelectorAll('.wxchip').length,"
                             "choices:document.querySelectorAll('#chat .msg.bot:last-child .choice').length,"
                             "bar:document.getElementById('wxText').textContent})"))
        shot("v26_weather_card.png")

        # 3) 景点回答 + 星级
        js("document.getElementById('q').value='甘川文化村 门票';document.getElementById('send').click();")
        time.sleep(2.5)
        print("SPOT:", js("JSON.stringify({rating:!!document.querySelector('#chat .msg.bot:last-child .rating'),"
                          "stars:(document.querySelector('#chat .msg.bot:last-child .rtop')||{}).textContent})"))
        print("GEOM:", js("(function(){var b=document.querySelector('#chat .msg.bot:last-child .bubble');"
                          "var c=b.querySelector('.choice');var g=b.querySelector('.cgo');"
                          "var rb=b.getBoundingClientRect();var rc=c?c.getBoundingClientRect():null;"
                          "var rg=g?g.getBoundingClientRect():null;"
                          "return JSON.stringify({bubble:[Math.round(rb.left),Math.round(rb.right)],"
                          "choice:rc?[Math.round(rc.left),Math.round(rc.right)]:null,"
                          "cgo:rg?[Math.round(rg.left),Math.round(rg.right)]:null,"
                          "scrollW:document.documentElement.scrollWidth,clientW:document.documentElement.clientWidth,"
                          "scrollX:window.scrollX});})()"))

        # 4) 深色模式
        cmd("Emulation.setEmulatedMedia",
            {"features": [{"name": "prefers-color-scheme", "value": "dark"}]})
        time.sleep(1.0)
        print("DARK:", js("JSON.stringify({bg:getComputedStyle(document.querySelector('.bubble')).backgroundColor,"
                          "ink:getComputedStyle(document.body).color,"
                          "bar:getComputedStyle(document.getElementById('wxText')).color,"
                          "input:getComputedStyle(document.getElementById('q')).backgroundColor,"
                          "qfont:getComputedStyle(document.getElementById('q')).fontSize})"))
        shot("v26_dark.png")
        cmd("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-color-scheme", "value": "light"}]})

        # 5) 平板宽屏（单列居中）
        metrics(820, 1180)
        print("WIDE:", js("JSON.stringify({bodyW:document.body.getBoundingClientRect().width,"
                          "screenW:innerWidth,"
                          "bodyLeft:Math.round(document.body.getBoundingClientRect().left),"
                          "bubbleW:Math.round(document.querySelector('#chat .msg.bot:last-child .bubble').getBoundingClientRect().width)})"))
        shot("v26_wide_tablet.png")

        # 6) 360px 窄屏
        metrics(360, 740)
        print("NARROW:", js("JSON.stringify({screenW:innerWidth,"
                            "scrollW:document.documentElement.scrollWidth,"
                            "chatPad:getComputedStyle(document.getElementById('chat')).paddingLeft,"
                            "bubbleW:Math.round(document.querySelector('#chat .msg.bot:last-child .bubble').getBoundingClientRect().width),"
                            "choiceH:Math.round((document.querySelector('.choice')||{getBoundingClientRect:()=>({height:0})}).getBoundingClientRect().height),"
                            "sendH:Math.round(document.getElementById('send').getBoundingClientRect().height)})"))
        shot("v26_narrow_360.png")

        # 7) 触控尺寸统计（390 视口）
        metrics(390, 844)
        print("TOUCH:", js("JSON.stringify({"
                           "send:Math.round(document.getElementById('send').getBoundingClientRect().height),"
                           "chip:Math.round(document.querySelector('.chip').getBoundingClientRect().height),"
                           "pick:Math.round(document.querySelector('.pick').getBoundingClientRect().height),"
                           "liveBtn:Math.round(document.getElementById('liveBtn').getBoundingClientRect().height),"
                           "wxBtn:Math.round(document.getElementById('wxBtn').getBoundingClientRect().height)})"))

        # 8) 真实天气接口（网络）
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
