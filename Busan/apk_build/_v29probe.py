# -*- coding: utf-8 -*-
"""v2.9 探针：个性化推荐条的收起/展开 + 单行横向滚动（真浏览器 390×844）。

检查项：
  1. 启动即收起：只有一行标题，正文高度为 0
  2. 点「展开」：正文展开，5 个点子排在同一行（top 全等），可横向滚动（scrollWidth > clientWidth）
  3. 真的能滑：把 scrollLeft 推到尾部，读数 > 0
  4. 点任一点子：自动收起 + 正常进入原有问答
  5. 刷新后保持上次的收起状态（localStorage busan_qrec）
  6. 切韩语：标题/按钮文案跟着变，展开状态不丢
  7. 夜间：推荐条与点子有深色配色
  8. 不回退：点天气按钮仍先出权限卡；综合推荐三枚胶囊也是一行（top 全等）
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
PORT = 9232
HTTP_PORT = 8794
PAGE = "http://127.0.0.1:%d/index.html" % HTTP_PORT
LAT, LNG = 35.1000, 129.0350


def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(HTTP_PORT),
                            "--bind", "127.0.0.1", "--directory", ASSETS],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    profile = os.path.join(HERE, "_chrome_probe29")
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
        # 清掉上一轮残留的折叠状态，保证每次从“默认收起”开始
        js("localStorage.removeItem('busan_qrec'); localStorage.removeItem('busan_lang');")
        cmd("Page.navigate", {"url": PAGE})
        time.sleep(3.0)

        # ---------------- 1. 启动即收起 ----------------
        print("BOOT:", js("(function(){var q=document.getElementById('qrec');"
                          "var b=document.getElementById('qrecBody');"
                          "var h=document.getElementById('qrecToggle');"
                          "return JSON.stringify({qrec:!!q,open:q?q.classList.contains('open'):null,"
                          "aria:h?h.getAttribute('aria-expanded'):null,"
                          "bodyH:b?Math.round(b.getBoundingClientRect().height):null,"
                          "boxH:q?Math.round(q.getBoundingClientRect().height):null,"
                          "title:document.querySelector('.qrec-title').textContent,"
                          "sum:document.getElementById('qrecSum').textContent,"
                          "act:document.getElementById('qrecAct').textContent,"
                          "headH:h?Math.round(h.getBoundingClientRect().height):null,"
                          "local:localStorage.getItem('busan_qrec')});})()"))
        shot("v29_home_collapsed.png")

        # ---------------- 2. 展开：一行 + 可滑动 ----------------
        js("document.getElementById('qrecToggle').click();")
        time.sleep(0.9)
        print("OPEN:", js("(function(){var q=document.getElementById('qrec');"
                          "var b=document.getElementById('qrecBody');"
                          "var row=document.querySelector('.qrec-body .quick');"
                          "var chips=Array.from(row.querySelectorAll('.pick'));"
                          "return JSON.stringify({open:q.classList.contains('open'),"
                          "aria:document.getElementById('qrecToggle').getAttribute('aria-expanded'),"
                          "act:document.getElementById('qrecAct').textContent,"
                          "sum:document.getElementById('qrecSum').textContent,"
                          "bodyH:Math.round(b.getBoundingClientRect().height),"
                          "boxH:Math.round(q.getBoundingClientRect().height),"
                          "chips:chips.length,"
                          "tops:chips.map(function(c){return Math.round(c.getBoundingClientRect().top);}),"
                          "oneRow:chips.every(function(c){return Math.round(c.getBoundingClientRect().top)===Math.round(chips[0].getBoundingClientRect().top);}),"
                          "rowClientW:row.clientWidth,rowScrollW:row.scrollWidth,"
                          "scrollable:row.scrollWidth>row.clientWidth+1,"
                          "maxChipW:Math.max.apply(null,chips.map(function(c){return Math.round(c.getBoundingClientRect().width);}))});})()"))
        shot("v29_qrec_open.png")

        # ---------------- 3. 真的能横向滑 ----------------
        print("SCROLL:", js("(function(){var r=document.querySelector('.qrec-body .quick');"
                            "var m=Math.max(0, r.scrollWidth - r.clientWidth);"
                            "r.scrollLeft=m;"
                            "return JSON.stringify({maxW:r.scrollWidth, clientW:r.clientWidth, after:Math.round(r.scrollLeft)});})()"))
        time.sleep(0.5)
        shot("v29_qrec_scrolled.png")

        # ---------------- 4. 点点子自动收起 + 进问答 ----------------
        print("PICK:", js("(function(){var row=document.querySelector('.qrec-body .quick');"
                          "var cs=Array.from(row.querySelectorAll('.pick'));"
                          "var t=cs[1].getAttribute('data-q');cs[1].click();"
                          "return t;})()"))
        time.sleep(2.4)
        print("AFTER PICK:", js("(function(){var q=document.getElementById('qrec');"
                                "return JSON.stringify({open:q?q.classList.contains('open'):null,"
                                "bots:document.querySelectorAll('#chat .msg.bot').length,"
                                "users:document.querySelectorAll('#chat .msg.user').length,"
                                "local:localStorage.getItem('busan_qrec')});})()"))

        # ---------------- 5. 刷新后保持收起 ----------------
        cmd("Page.navigate", {"url": PAGE})
        time.sleep(3.0)
        print("RELOAD:", js("(function(){var q=document.getElementById('qrec');var b=document.getElementById('qrecBody');"
                            "return JSON.stringify({open:q.classList.contains('open'),"
                            "aria:document.getElementById('qrecToggle').getAttribute('aria-expanded'),"
                            "bodyH:Math.round(b.getBoundingClientRect().height),"
                            "act:document.getElementById('qrecAct').textContent,"
                            "local:localStorage.getItem('busan_qrec')});})()"))

        # ---------------- 6. 韩语文案 + 状态不丢 ----------------
        js("document.getElementById('qrecToggle').click();")
        time.sleep(0.6)
        js("document.querySelector('.langs button[data-lang=\"ko\"]').click();")
        time.sleep(1.6)
        print("KO:", js("(function(){var q=document.getElementById('qrec');"
                        "return JSON.stringify({open:q.classList.contains('open'),"
                        "title:document.querySelector('.qrec-title').textContent,"
                        "act:document.getElementById('qrecAct').textContent,"
                        "sum:document.getElementById('qrecSum').textContent,"
                        "chips:document.querySelectorAll('.qrec-body .pick').length});})()"))
        shot("v29_qrec_ko.png")
        js("document.querySelector('.langs button[data-lang=\"zh\"]').click();")
        time.sleep(1.4)

        # ---------------- 7. 夜间配色 ----------------
        js("BusanUI.setThemeMode('night');")
        time.sleep(1.2)
        print("NIGHT:", js("(function(){var q=document.querySelector('.qrec');var p=document.querySelector('.qrec .pick');"
                           "return JSON.stringify({night:BusanUI.isNight(),"
                           "boxBg:getComputedStyle(q).backgroundColor,"
                           "chipBg:p?getComputedStyle(p).backgroundColor:'',"
                           "chipColor:p?getComputedStyle(p).color:'',"
                           "theme:document.querySelector('meta[name=theme-color]').content});})()"))
        shot("v29_night_qrec.png")
        js("BusanUI.setThemeMode('day');")
        time.sleep(0.8)

        # ---------------- 8. 不回退：天气仍先权限卡 + 胶囊一行 ----------------
        js("document.getElementById('wxFab').click();")
        time.sleep(1.3)
        print("WX PERM:", js("(function(){var b=document.querySelector('#chat .msg.bot:last-child .bubble');"
                             "return JSON.stringify({grant:!!document.querySelector('.act-grant'),"
                             "tag:(b.querySelector('.badge')||{}).textContent,"
                             "qrecOpen:document.getElementById('qrec').classList.contains('open')});})()"))
        js("window.__busanLocUpdate(%f,%f,12,'probe',Date.now());" % (LAT, LNG))
        time.sleep(0.4)
        js("document.querySelector('.act-grant').click();")
        time.sleep(6.0)
        print("MIX ROW:", js("(function(){var b=document.querySelector('#chat .msg.bot:last-child .bubble');"
                            "var cs=Array.from(b.querySelectorAll('.mixchip'));"
                            "return JSON.stringify({chips:cs.length,"
                            "tops:cs.map(function(c){return Math.round(c.getBoundingClientRect().top);}),"
                            "oneRow:cs.every(function(c){return Math.round(c.getBoundingClientRect().top)===Math.round(cs[0].getBoundingClientRect().top);}),"
                            "choices:b.querySelectorAll('.choice').length,"
                            "tag:(b.querySelector('.badge')||{}).textContent});})()"))
        shot("v29_mix_row.png")

        print("ERRORS:", js("JSON.stringify(window.__errs||[])"))
        ws.close()
    finally:
        proc.terminate()
        srv.terminate()


if __name__ == "__main__":
    main()
