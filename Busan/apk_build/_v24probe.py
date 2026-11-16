# -*- coding: utf-8 -*-
"""v2.4 图片大图查看探针：点缩略图打开、放大、切换、关闭。"""
import base64, json, os, subprocess, time, urllib.request
import websocket

CHROME = r"C:\Users\43763\AppData\Local\Google\Chrome\Application\chrome.exe"
PAGE = "file:///D:/AI_Project_2026_2/Busan/android/assets/index.html"
PORT = 9227
BASE = os.path.dirname(__file__)
proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
    "--remote-allow-origins=*", f"--remote-debugging-port={PORT}",
    rf"--user-data-dir={BASE}\_chrome_probe_v24", "--window-size=500,1400", PAGE],
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
    ev("document.getElementById('q').value='甘川文化村';document.getElementById('send').click();")
    time.sleep(1.8)

    print("THUMBS", ev("JSON.stringify({count:document.querySelectorAll('.msg.bot:last-child .photostrip img').length,loaded:Array.from(document.querySelectorAll('.msg.bot:last-child .photostrip img')).every(i=>i.naturalWidth>0)})"))
    ev("document.querySelector('.msg.bot:last-child .photostrip img').click();")
    time.sleep(0.8)
    print("OPEN", ev("JSON.stringify({open:BusanLightbox.state().open,index:BusanLightbox.state().index,count:BusanLightbox.state().count,scale:BusanLightbox.state().scale,imgLoaded:document.getElementById('lbImg').naturalWidth>0,counter:document.getElementById('lbCount').innerText,cap:document.getElementById('lbCap').innerText.slice(0,50),bodyLock:document.body.classList.contains('lb-open')})"))
    shot("v24_lightbox.png")

    ev("BusanLightbox.zoom(250,500);")
    time.sleep(0.5)
    print("ZOOM", ev("JSON.stringify({scale:BusanLightbox.state().scale,x:BusanLightbox.state().x,y:BusanLightbox.state().y,transform:document.getElementById('lbCanvas').style.transform})"))
    shot("v24_lightbox_zoom.png")

    ev("document.getElementById('lbNext').click();")
    time.sleep(0.6)
    print("NEXT", ev("JSON.stringify({index:BusanLightbox.state().index,counter:document.getElementById('lbCount').innerText,scale:BusanLightbox.state().scale,loaded:document.getElementById('lbImg').naturalWidth>0})"))
    cmd("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 180, "y": 700, "id": 1}, {"x": 320, "y": 700, "id": 2}]})
    time.sleep(0.15)
    cmd("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": 130, "y": 700, "id": 1}, {"x": 370, "y": 700, "id": 2}]})
    time.sleep(0.25)
    cmd("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    time.sleep(0.3)
    print("PINCH", ev("JSON.stringify({scale:BusanLightbox.state().scale,x:BusanLightbox.state().x,y:BusanLightbox.state().y})"))
    cmd("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 250, "y": 700, "id": 3}]})
    time.sleep(0.1)
    cmd("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": 310, "y": 760, "id": 3}]})
    time.sleep(0.2)
    cmd("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    time.sleep(0.2)
    print("PAN", ev("JSON.stringify({scale:BusanLightbox.state().scale,x:BusanLightbox.state().x,y:BusanLightbox.state().y})"))
    ev("document.getElementById('lbPrev').click();")
    time.sleep(0.3)
    print("PREV", ev("JSON.stringify({index:BusanLightbox.state().index,counter:document.getElementById('lbCount').innerText})"))

    ev("document.getElementById('lbClose').click();")
    time.sleep(0.3)
    print("CLOSE", ev("JSON.stringify({open:BusanLightbox.state().open,href:document.getElementById('lbImg').getAttribute('src'),bodyLock:document.body.classList.contains('lb-open')})"))
    ws.close()
finally:
    proc.terminate()
