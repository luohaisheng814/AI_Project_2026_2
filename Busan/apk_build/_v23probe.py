# -*- coding: utf-8 -*-
import base64, json, os, subprocess, time, urllib.request
import websocket

CHROME = r"C:\Users\43763\AppData\Local\Google\Chrome\Application\chrome.exe"
PAGE = "file:///D:/AI_Project_2026_2/Busan/android/assets/index.html"
PORT = 9225
BASE = os.path.dirname(__file__)
proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
    "--remote-allow-origins=*", f"--remote-debugging-port={PORT}",
    rf"--user-data-dir={BASE}\_chrome_probe_v23", "--window-size=500,1400", PAGE],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def connect():
    for _ in range(40):
        try:
            for t in json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json")):
                if t.get("type") == "page":
                    return websocket.create_connection(t["webSocketDebuggerUrl"], timeout=40)
        except Exception:
            pass
        time.sleep(0.5)
    return None


try:
    ws = connect()
    assert ws, "CDP not connected"
    mid = [0]
    def cmd(m, p=None):
        mid[0] += 1
        ws.send(json.dumps({"id": mid[0], "method": m, "params": p or {}}))
        while True:
            r = json.loads(ws.recv())
            if r.get("id") == mid[0]:
                return r.get("result", {})
    def ev(expr):
        r = cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
        return r.get("result", {}).get("value")
    def shot(name):
        s = cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        open(os.path.join(BASE, name), "wb").write(base64.b64decode(s["data"]))
    cmd("Emulation.setDeviceMetricsOverride", {"width": 500, "height": 1400, "deviceScaleFactor": 1, "mobile": True})
    cmd("Page.navigate", {"url": PAGE})
    time.sleep(2)
    ev("BusanCloud.setDb(window.BUSAN_CLOUD_SNAPSHOT); BusanCloud.init('zh'); if(window.BusanLLM){BusanLLM.configured=function(){return false;};} if(window.BusanLive){BusanLive.stop();}")
    print("PHOTOS_READY", ev("JSON.stringify({spots:Object.keys(window.BUSAN_PHOTOS||{}).length,photos:Object.values(window.BUSAN_PHOTOS||{}).reduce((n,v)=>n+v.length,0)})"))
    print("NO_POS", ev("JSON.stringify({perm:!!document.querySelector('.permact'),route:/3 条可选走法/.test(document.querySelector('.msg.bot:last-child .bubble').innerText)})"))
    ev("document.getElementById('q').value='去甘村文化村的路线有几条可以推荐的';document.getElementById('send').click();")
    time.sleep(1.2)
    last = "document.querySelector('.msg.bot:last-child .bubble')"
    print("NO_POS_CARD", ev("JSON.stringify({perm:!!document.querySelector('.permact'),route:/3 条可选走法/.test(" + last + ".innerText),text:" + last + ".innerText.slice(0,70)})"))
    shot("v23_permission.png")

    ev("window.__busanLocUpdate(35.10,129.03,38,'gps',Date.now());")
    ev("document.getElementById('q').value='去甘村文化村的路线有几条可以推荐的';document.getElementById('send').click();")
    time.sleep(1.5)
    print("ROUTE", ev("(function(){var bots=document.querySelectorAll('.msg.bot');var b=bots[bots.length-1].querySelector('.bubble');var rh=b.querySelector('.routes-h');var imgs=b.querySelectorAll('.photos img');var ems=b.querySelectorAll('.routeopt em');return JSON.stringify({route:/3 条可选走法/.test(b.innerText),best:/最优建议/.test(b.innerText),km:/4\\.8 km/.test(b.innerText),acc:/±38 m/.test(b.innerText),photos:imgs.length,loaded:Array.from(imgs).every(function(i){return i.naturalWidth>0}),navH:rh?/NAVER 地图/.test(rh.innerText):false,navBtn:Array.from(ems).every(function(e){return /NAVER 地图/.test(e.innerText)})})})()"))
    shot("v23_route.png")

    ev("document.getElementById('q').value='甘川文化村';document.getElementById('send').click();")
    time.sleep(1.5)
    print("SPOT_PHOTOS", ev("JSON.stringify({photos:document.querySelectorAll('.msg.bot:last-child .photos img').length,loaded:Array.from(document.querySelectorAll('.msg.bot:last-child .photos img')).every(i=>i.naturalWidth>0),credit:document.querySelector('.msg.bot:last-child .photocredit').innerText,title:document.querySelector('.msg.bot:last-child .bubble').innerText.slice(0,30)})"))
    shot("v23_spot_photos.png")

    ev("BusanUI.addBot({text:'地图按钮归属测试',cards:[{name:'甘川文化村',km:4.8,reason:'测试',map:BusanCloud.mapLinks(BusanCloud.findSpot('甘川'))}]});")
    time.sleep(0.4)
    print("MAP_LABELS", ev("JSON.stringify({labels:Array.from(document.querySelectorAll('.msg.bot:last-child .cb a')).map(a=>a.innerText),naver:Array.from(document.querySelectorAll('.msg.bot:last-child .cb a')).filter(a=>/NAVER/.test(a.innerText)).length,google:Array.from(document.querySelectorAll('.msg.bot:last-child .cb a')).filter(a=>/Google/.test(a.innerText)).length})"))
    shot("v23_map_labels.png")

    ev("document.querySelector('[data-lang=\"en\"]').click();")
    time.sleep(0.8)
    print("LANG_EN", ev("JSON.stringify({title:document.getElementById('title').innerText,btn:document.getElementById('send').innerText,on:document.querySelector('[data-lang=\"en\"]').className})"))
    shot("v23_lang_en.png")
    ev("document.querySelector('[data-lang=\"zh\"]').click();")
    print("LANG_ZH", ev("JSON.stringify({title:document.getElementById('title').innerText,on:document.querySelector('[data-lang=\"zh\"]').className})"))
    print("SPOTS", ev("BusanCloud.allSpots().length"))
    ws.close()
finally:
    proc.terminate()
