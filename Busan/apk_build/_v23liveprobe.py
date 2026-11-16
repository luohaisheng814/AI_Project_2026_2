# -*- coding: utf-8 -*-
"""验证：原生已授权时自动恢复实时定位；坐标回传后实时条显示到景点距离。"""
import base64, json, os, subprocess, time, urllib.request
import websocket

CHROME = r"C:\Users\43763\AppData\Local\Google\Chrome\Application\chrome.exe"
PAGE = "file:///D:/AI_Project_2026_2/Busan/android/assets/index.html"
PORT = 9226
BASE = os.path.dirname(__file__)
proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
    "--remote-allow-origins=*", f"--remote-debugging-port={PORT}",
    rf"--user-data-dir={BASE}\_chrome_probe_v23live", "--window-size=500,1400", "about:blank"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    ws = None
    for _ in range(40):
        try:
            for t in json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json")):
                if t.get("type") == "page":
                    ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=40)
                    break
        except Exception:
            pass
        if ws:
            break
        time.sleep(0.5)
    assert ws
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
    cmd("Page.addScriptToEvaluateOnNewDocument", {"source": """
window.BusanHost = {
  hasLocationPermission: function(){return true;},
  startLocationWatch: function(){return true;},
  stopLocationWatch: function(){},
  requestLocation: function(){window.__busanLocReady && window.__busanLocReady();},
  openAppSettings: function(){},
  netAllowed: function(){return false;}
};
"""})
    cmd("Emulation.setDeviceMetricsOverride", {"width": 500, "height": 1400, "deviceScaleFactor": 1, "mobile": True})
    cmd("Page.navigate", {"url": PAGE})
    time.sleep(2.2)
    print("HOST", ev("JSON.stringify({host:typeof BusanHost,perm:(window.BusanHost&&BusanHost.hasLocationPermission)?BusanHost.hasLocationPermission():'none',init:typeof BusanLive.init})"))
    ev("window.BusanHost={hasLocationPermission:function(){return true;},startLocationWatch:function(){return true;},stopLocationWatch:function(){},requestLocation:function(){window.__busanLocReady&&window.__busanLocReady();},openAppSettings:function(){},netAllowed:function(){return false;}};BusanLive.init();")
    time.sleep(1.2)
    print("AUTO_START", ev("JSON.stringify({watching:BusanLive.isWatching(),pos:!!BusanLive.position(),text:document.getElementById('liveText').innerText,btn:document.getElementById('liveBtn').innerText})"))
    ev("window.__busanLocUpdate(35.10,129.03,38,'gps',Date.now());")
    time.sleep(0.5)
    print("LOC_UPDATE", ev("JSON.stringify({watching:BusanLive.isWatching(),pos:!!BusanLive.position(),text:document.getElementById('liveText').innerText,dot:document.getElementById('liveDot').className})"))
    s = cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
    open(os.path.join(BASE, "v23_live_auto.png"), "wb").write(base64.b64decode(s["data"]))
    ws.close()
finally:
    proc.terminate()
