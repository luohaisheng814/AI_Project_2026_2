# -*- coding: utf-8 -*-
"""无头 Chrome 冒烟测试：打开 index.html，问一个问题，截图并打印气泡 HTML。"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

import websocket

CHROME = r"C:\Users\43763\AppData\Local\Google\Chrome\Application\chrome.exe"
PAGE = "file:///D:/AI_Project_2026_2/Busan/android/assets/index.html"
OUT = r"D:\AI_Project_2026_2\Busan\apk_build\v18_probe_choices.png"
PORT = 9223


def main():
    profile = os.path.join(os.path.dirname(__file__), "_chrome_probe")
    proc = subprocess.Popen([
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--remote-allow-origins=*",
        f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
        "--window-size=500,1400", PAGE,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ws_url = None
        for _ in range(30):
            try:
                data = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
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

        cmd("Page.enable")
        cmd("Emulation.setDeviceMetricsOverride", {"width": 500, "height": 1400, "deviceScaleFactor": 1, "mobile": True})
        cmd("Page.navigate", {"url": PAGE})
        time.sleep(2.5)
        home = cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        home_path = os.path.join(os.path.dirname(__file__), "v18_probe_home.png")
        with open(home_path, "wb") as f:
            f.write(base64.b64decode(home["data"]))
        cfg = cmd("Runtime.evaluate", {"expression": "JSON.stringify({modelStrip: !!document.getElementById('modelStrip'), llm: window.BusanLLM && BusanLLM.config(), provider: document.getElementById('llmProvider') ? document.getElementById('llmProvider').textContent : ''})", "returnByValue": True})
        print("CONFIG:" + cfg.get("result", {}).get("value", ""))
        print("screenshot:", home_path)
        cmd("Runtime.evaluate", {"expression": """
            document.getElementById('q').value='甘川文化村 轮椅 怎么去';
            document.getElementById('send').click();
        """})
        time.sleep(2.0)
        html = cmd("Runtime.evaluate", {"expression": "document.getElementById('chat').lastElementChild ? document.getElementById('chat').lastElementChild.outerHTML : 'none'", "returnByValue": True})
        print(html.get("result", {}).get("value", ""))
        shot = cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        with open(OUT, "wb") as f:
            f.write(base64.b64decode(shot["data"]))
        print("screenshot:", OUT)

        # 行程推演也应有 3 个可选点
        cmd("Runtime.evaluate", {"expression": "document.getElementById('planBtn').click();"})
        time.sleep(2.0)
        plan_html = cmd("Runtime.evaluate", {"expression": "document.getElementById('chat').lastElementChild.outerHTML", "returnByValue": True})
        print("\nPLAN:" + plan_html.get("result", {}).get("value", ""))
        shot2 = cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        plan_out = OUT.replace("choices", "plan")
        with open(plan_out, "wb") as f:
            f.write(base64.b64decode(shot2["data"]))
        print("screenshot:", plan_out)

        # 账户面板：注入一个本机演示账户，重载后打开面板，核对云端卡片
        cmd("Runtime.evaluate", {"expression": """
            localStorage.setItem('busan_demo_auth', JSON.stringify({u1:{username:'u1',displayName:'测试用户',hash:'demo',createdAt:Date.now(),lastActive:Date.now()}}));
            localStorage.setItem('busan_demo_session', JSON.stringify({key:'u1',token:'demo',at:Date.now()}));
            location.reload();
        """})
        time.sleep(2.2)
        cmd("Runtime.evaluate", {"expression": "document.getElementById('acctBtn').click();"})
        time.sleep(0.8)
        acct_html = cmd("Runtime.evaluate", {"expression": "document.getElementById('acctPanel') ? document.getElementById('acctPanel').outerHTML : 'none'", "returnByValue": True})
        acct_text = acct_html.get("result", {}).get("value", "")
        print("ACCT:" + acct_text[:3000])
        shot3 = cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        acct_out = os.path.join(os.path.dirname(__file__), "v18_probe_account.png")
        with open(acct_out, "wb") as f:
            f.write(base64.b64decode(shot3["data"]))
        print("screenshot:", acct_out)
        ws.close()
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
