# -*- coding: utf-8 -*-
"""v2.5 UI 探针：天气条 / 天气卡 / 星级评分 / 手动切天气，并截图。"""
import base64
import json
import os
import subprocess
import time
import urllib.request

import websocket

CHROME = r"C:\Users\43763\AppData\Local\Google\Chrome\Application\chrome.exe"
PAGE = "file:///D:/AI_Project_2026_2/Busan/android/assets/index.html"
HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 9225


def main():
    profile = os.path.join(HERE, "_chrome_probe")
    proc = subprocess.Popen([
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--remote-allow-origins=*",
        "--remote-debugging-port=%d" % PORT, "--user-data-dir=" + profile,
        "--window-size=500,1500", PAGE,
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

        def shot(name):
            data = cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
            path = os.path.join(HERE, name)
            with open(path, "wb") as f:
                f.write(base64.b64decode(data["data"]))
            print("screenshot:", path,
                  os.path.getsize(path) // 1024, "KB")

        cmd("Page.enable")
        cmd("Runtime.enable")
        cmd("Page.addScriptToEvaluateOnNewDocument", {"source":
            "window.__errs=[];window.onerror=function(m,s,l,c,e){window.__errs.push(String(m)+' @'+l);};"
            "window.addEventListener('unhandledrejection',function(e){window.__errs.push('rej:'+String(e.reason));});"})
        cmd("Emulation.setDeviceMetricsOverride",
            {"width": 500, "height": 1500, "deviceScaleFactor": 1, "mobile": True})
        cmd("Page.navigate", {"url": PAGE})
        time.sleep(3.0)

        print("MODULES:", js("JSON.stringify({ui:!!window.BusanUI,wx:!!window.BusanWeather,rt:!!window.BusanRating,"
                             "wxText:(document.getElementById('wxText')||{}).textContent,"
                             "wxBtn:!!document.getElementById('wxBtn')})"))
        print("RATING:", js("JSON.stringify(BusanRating.of('甘川文化村'))"))
        print("REC RAIN:", js("JSON.stringify(BusanWeather.recommend(BusanWeather.manual('rain'),3).map(r=>r.name+':'+r.score))"))
        print("WXBAR:", js("document.getElementById('wxText').textContent"))

        # 1) 打开天气卡（手动雨）
        js("document.getElementById('wxBtn').click();")
        time.sleep(1.2)
        print("WXCARD:", js("JSON.stringify({chips:document.querySelectorAll('.wxchip').length,"
                           "choices:document.querySelectorAll('#chat .msg.bot:last-child .choice').length,"
                           "hasRating:!!document.querySelector('#chat .msg.bot:last-child .rating'),"
                           "head:(document.querySelector('#chat .msg.bot:last-child .bubble')||{}).textContent.slice(0,120)})"))
        shot("v25_weather_rain.png")

        # 2) 手动切到晴天，卡片应重排
        js("document.querySelector('.wxchip[data-k=\"clear\"]').click();")
        time.sleep(1.0)
        print("WXCLEAR:", js("JSON.stringify({bar:document.getElementById('wxText').textContent,"
                            "first:(document.querySelector('#chat .msg.bot:last-child .choice .cname')||{}).textContent})"))
        shot("v25_weather_clear.png")

        # 3) 具体景点回答 → 星级块 + 用户自评
        js("document.getElementById('q').value='甘川文化村 门票';document.getElementById('send').click();")
        time.sleep(2.5)
        print("SPOT:", js("JSON.stringify({rating:!!(document.querySelector('#chat .msg.bot:last-child .rating')),"
                          "stars:(document.querySelector('#chat .msg.bot:last-child .rtop')||{}).textContent,"
                          "buttons:document.querySelectorAll('#chat .msg.bot:last-child .ratebtn').length,"
                          "summary:(document.querySelector('#chat .msg.bot:last-child .rsub')||{}).textContent})"))
        js("localStorage.removeItem('busan_rating_user');"
           "document.querySelector('#chat .msg.bot:last-child .ratebtn[data-n=\"5\"]').click();")
        time.sleep(0.6)
        print("RATED:", js("JSON.stringify({saved:BusanRating.userOf('甘川文化村'),"
                          "ls:localStorage.getItem('busan_rating_user'),"
                          "on:document.querySelectorAll('#chat .msg.bot:last-child .ratebtn.on').length})"))
        shot("v25_rating.png")

        # 4) 推荐类回答应带天气提示行
        js("document.getElementById('q').value='一个人女性推荐';document.getElementById('send').click();")
        time.sleep(2.5)
        print("WXNOTE:", js("JSON.stringify({note:(document.querySelector('#chat .msg.bot:last-child .wxnote')||{}).textContent,"
                           "choices:document.querySelectorAll('#chat .msg.bot:last-child .choice').length})"))
        shot("v25_recommend.png")

        print("LIVE FETCH:", js("fetch(BusanWeather.url(35.1796,129.0756)).then(r=>r.text())"
                               ".then(t=>{var j=JSON.parse(t);return JSON.stringify(j.current);})"
                               ".catch(e=>'ERR:'+e)"))
        print("ERRORS:", js("JSON.stringify(window.__errs||[])"))
        ws.close()
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
