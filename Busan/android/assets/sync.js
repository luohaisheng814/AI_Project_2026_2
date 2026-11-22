/* 釜山 AI 旅行助手 · v3.1 内容与版本同步
 * 1) 启动时先把上一次从后台拉到的内容合进本地库（断网也有最新内容）
 * 2) 每 25 秒 / 回到前台时轮询 /api/state：rev 变了 → 顶部横幅提示刷新
 * 3) state.version.code 大于本包 BUILD.code → 弹更新层，给安装包下载
 * 4) 后台地址：设置里手填 > assets/admin_base.js 注入 > GitHub Pages 静态兜底
 */
(function () {
  "use strict";
  var BUILD = window.BUSAN_BUILD || { code: 24, name: "3.1" };
  var PAGES = "https://luohaisheng814.github.io/AI_Project_2026_2";
  var KEY = {
    base: "busan_admin_base",
    rev: "busan_sync_rev",
    content: "busan_admin_content",
    skip: "busan_upd_skip",
    at: "busan_sync_at"
  };
  var POLL_MS = 25000;
  var state = { rev: 0, version: null, base: "", ok: false, err: "", count: 0 };

  function ls(k, v) {
    try {
      if (v === undefined) return localStorage.getItem(k);
      localStorage.setItem(k, v);
    } catch (e) { return null; }
    return v;
  }
  function lsDel(k) { try { localStorage.removeItem(k); } catch (e) {} }
  function lang() {
    try { return localStorage.getItem("busan_lang") || "zh"; } catch (e) { return "zh"; }
  }
  function T(zh, ko, en) { var l = lang(); return l === "ko" ? ko : l === "en" ? en : zh; }
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  /* ---------- 纯函数，便于单测 ---------- */
  function parseState(txt) {
    try {
      var j = typeof txt === "string" ? JSON.parse(txt) : txt;
      if (!j || typeof j !== "object") return null;
      var rev = Number(j.rev);
      if (!isFinite(rev)) rev = 0;
      var v = j.version || null;
      if (v && !isFinite(Number(v.code))) v.code = 0;
      return { rev: rev, version: v ? { code: Number(v.code), name: String(v.name || ""), notes: String(v.notes || ""), download: String(v.download || "") } : null };
    } catch (e) { return null; }
  }
  function versionNewer(v, build) {
    if (!v) return false;
    return Number(v.code) > Number((build || BUILD).code || 0);
  }
  function mergeSpots(base, incoming, softDelete) {
    var out = [], seen = {}, byId = {};
    (base || []).forEach(function (s) { if (s && s.id) byId[s.id] = s; });
    (incoming || []).forEach(function (s) {
      if (!s || !s.id || seen[s.id]) return;
      seen[s.id] = 1;
      var old = byId[s.id];
      if (!old) { out.push(s); return; }
      Object.keys(s).forEach(function (k) {
        if (s[k] !== undefined && s[k] !== null) old[k] = s[k];
      });
      out.push(old);
    });
    if (softDelete === false) return out;
    return out;
  }
  function contentPayload(j) {
    if (!j) return null;
    var spots = j.spots || (j.content && j.content.spots) || [];
    if (!spots.length) return null;
    return { rev: Number(j.rev || 0), spots: spots };
  }

  /* ---------- 应用内容到本地库 ---------- */
  function applySpots(spots) {
    if (!spots || !spots.length) return 0;
    var D = window.BUSAN_DATA;
    if (D) {
      D.spots = mergeSpots(D.spots || [], spots);
      try {
        D.counts = D.counts || {};
        D.counts.spots = D.spots.length;
      } catch (e) {}
    }
    var C = window.BusanCloud;
    if (C && typeof C.getDb === "function") {
      var db = C.getDb();
      if (db && db.spots) {
        db.spots = mergeSpots(db.spots, spots);
        if (typeof C.setDb === "function") { try { C.setDb(db); } catch (e) {} }
      }
    }
    return spots.length;
  }
  function applyLocalContent() {
    var raw = ls(KEY.content);
    if (!raw) return 0;
    try {
      var j = JSON.parse(raw);
      var n = applySpots(j.spots || []);
      state.rev = Number(j.rev || 0);
      return n;
    } catch (e) { return 0; }
  }

  /* ---------- 地址候选 ---------- */
  function baseList() {
    var manual = (ls(KEY.base) || "").replace(/\/+$/, "");
    var injected = String(window.BUSAN_ADMIN_BASE || "").replace(/\/+$/, "");
    var list = [];
    if (manual) list.push(manual);
    if (injected && injected !== manual) list.push(injected);
    list.push(PAGES);
    return list;
  }
  function withTimeout(url, ms) {
    if (typeof AbortController !== "function") return fetch(url, { cache: "no-store" });
    var ctl = new AbortController();
    var t = setTimeout(function () { ctl.abort(); }, ms || 7000);
    return fetch(url, { cache: "no-store", signal: ctl.signal }).then(function (r) {
      clearTimeout(t); return r;
    }, function (e) { clearTimeout(t); throw e; });
  }
  function getJson(base, path) {
    return withTimeout(base + path).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }

  /* ---------- 轮询 ---------- */
  function pollOnce(manual) {
    if (navigator.onLine === false) { paintStatus(); return Promise.resolve(state); }
    var bases = baseList();
    var i = 0;
    function next() {
      if (i >= bases.length) {
        state.ok = false; state.err = T("未连接到后台", "백엔드에 연결되지 않음", "Backend offline");
        paintStatus(); return state;
      }
      var b = bases[i++];
      return getJson(b, "/api/state.json").catch(function () {
        return getJson(b, "/api/state");
      }).then(function (j) {
        var s = parseState(j);
        if (!s) throw new Error("bad state");
        state.base = b; state.ok = true; state.err = ""; state.count++;
        ls(KEY.at, String(Date.now()));
        onState(s, manual);
        paintStatus();
        return state;
      }).catch(function (e) {
        if (manual) state.err = e.message || String(e);
        return next();
      });
    }
    return next();
  }

  function onState(s, manual) {
    var prev = Number(ls(KEY.rev) || 0);
    state.version = s.version;
    if (prev && s.rev > prev) {
      showBanner(s.rev);
      return;
    }
    if (!prev) ls(KEY.rev, String(s.rev));
    checkVersion(s.version);
    state.rev = s.rev;
  }

  /* ---------- 内容更新横幅 ---------- */
  function showBanner(rev) {
    var bar = document.getElementById("syncBar");
    if (!bar) return;
    bar.hidden = false;
    document.getElementById("syncBarText").textContent =
      T("后台内容已更新（rev " + rev + "）", "콘텐츠가 업데이트되었습니다 (rev " + rev + ")",
        "Content updated (rev " + rev + ")");
  }
  function applyUpdate(rev) {
    var base = state.base || baseList()[0];
    var done = function () { ls(KEY.rev, String(rev || state.rev)); location.reload(); };
    getJson(base, "/api/content.json").catch(function () { return getJson(base, "/api/content"); })
      .then(function (j) {
        var p = contentPayload(j);
        if (!p) throw new Error("empty");
        ls(KEY.content, JSON.stringify(p));
        applySpots(p.spots);
        done();
      }).catch(function () {
        // 静态兜底：Pages 上只有 content.json
        getJson(PAGES, "/api/content.json").then(function (j) {
          var p = contentPayload(j);
          if (!p) throw new Error("empty");
          ls(KEY.content, JSON.stringify(p));
          applySpots(p.spots);
          done();
        }).catch(function () { toast(T("拉取内容失败", "콘텐츠를 가져오지 못했습니다", "Failed to fetch content")); });
      });
  }

  /* ---------- 版本更新 ---------- */
  function downloadUrl(v) {
    if (!v) return "";
    if (state.base && state.ok) return state.base + "/api/download";
    if (v.download) return v.download;
    return PAGES + "/Busan.apk";
  }
  function checkVersion(v) {
    if (!versionNewer(v)) return;
    if (String(ls(KEY.skip) || "") === String(v.code)) return;
    var box = document.getElementById("updModal");
    if (!box) return;
    if (!box.hidden) return;
    document.getElementById("updV").textContent = v.name + " · code " + v.code;
    document.getElementById("updNotes").textContent = v.notes || T("有新版本可用", "새 버전이 있습니다", "A new version is available");
    var dl = document.getElementById("updGo");
    dl.href = downloadUrl(v);
    box.hidden = false;
    document.getElementById("updSkip").onclick = function () {
      ls(KEY.skip, String(v.code)); box.hidden = true;
    };
  }
  function toast(msg) {
    var t = document.getElementById("syncToast");
    if (!t) return;
    t.textContent = msg; t.hidden = false;
    setTimeout(function () { t.hidden = true; }, 2200);
  }

  /* ---------- 设置面板 ---------- */
  function paintStatus() {
    var box = document.getElementById("syncStatus");
    if (!box) return;
    var at = Number(ls(KEY.at) || 0);
    if (state.ok) {
      box.textContent = T("已连接 · rev " + state.rev + " · 当前内容由后台下发",
        "연결됨 · rev " + state.rev, "Connected · rev " + state.rev);
      box.className = "sync-status ok";
    } else {
      box.textContent = T("未连接后台，使用包内离线数据" + (at ? "（上次同步 " + new Date(at).toLocaleString() + "）" : ""),
        "백엔드 미연결 · 내장 데이터 사용", "Not connected · using bundled data");
      box.className = "sync-status";
    }
  }
  function initSettings() {
    var inp = document.getElementById("syncBase");
    if (!inp) return;
    inp.value = ls(KEY.base) || "";
    inp.placeholder = PAGES;
    var save = document.getElementById("syncSave");
    if (save) save.onclick = function () {
      var v = inp.value.trim().replace(/\/+$/, "");
      if (v) { try { new URL(v); } catch (e) { toast(T("地址格式不对", "주소 형식 오류", "Bad URL")); return; } ls(KEY.base, v); }
      else lsDel(KEY.base);
      toast(T("已保存，正在检查…", "저장됨, 확인 중…", "Saved, checking…"));
      pollOnce(true);
    };
    var now = document.getElementById("syncNow");
    if (now) now.onclick = function () { pollOnce(true).then(paintStatus); };
    paintStatus();
  }

  /* ---------- 一次性注入 UI ---------- */
  function inject() {
    var st = document.createElement("style");
    st.textContent =
      "#syncBar{position:fixed;left:10px;right:10px;bottom:calc(74px + env(safe-area-inset-bottom));z-index:60;" +
      "background:#0f6e8c;color:#fff;border-radius:12px;padding:8px 10px;display:flex;align-items:center;gap:8px;" +
      "box-shadow:0 8px 24px rgba(6,40,52,.35);font-size:12.5px}" +
      "#syncBar[hidden]{display:none}" +
      "#syncBarText{flex:1 1 auto;min-width:0}" +
      "#syncBar button{border:0;border-radius:9px;padding:6px 10px;font-size:12px;background:#fff;color:#0f6e8c;font-weight:600}" +
      "#syncBar .x{background:transparent;color:#d7f2fa;padding:4px 6px;font-size:15px}" +
      ".sync-status{font-size:12px;color:var(--muted);margin-top:6px}" +
      ".sync-status.ok{color:#1f8a63}" +
      "body.night .sync-status.ok{color:#6ee0b4}" +
      "#updModal{position:fixed;inset:0;z-index:1200;background:rgba(5,16,22,.72);display:flex;" +
      "align-items:center;justify-content:center;padding:18px}" +
      "#updModal[hidden]{display:none}" +
      "#updModal .box{width:100%;max-width:340px;background:#fff;color:#16232c;border-radius:16px;padding:18px}" +
      "body.night #updModal .box{background:#18212a;color:#e8eff4}" +
      "#updModal h3{margin:0 0 8px;font-size:16px}" +
      "#updModal .n{font-size:12.5px;line-height:1.6;color:#5a6b78;white-space:pre-wrap}" +
      "body.night #updModal .n{color:#9fb2bf}" +
      "#updModal .acts{display:flex;gap:8px;margin-top:14px}" +
      "#updModal a,#updModal button{flex:1;text-align:center;border-radius:10px;padding:10px;font-size:13px;" +
      "text-decoration:none;border:0;font-weight:600}" +
      "#updGo{background:#0f6e8c;color:#fff}" +
      "#updLater,#updSkip{background:#eef3f6;color:#33414f}" +
      "body.night #updLater,body.night #updSkip{background:#22303b;color:#cfe0ea}" +
      "#syncToast{position:fixed;left:50%;transform:translateX(-50%);bottom:calc(120px + env(safe-area-inset-bottom));" +
      "background:rgba(12,28,36,.9);color:#fff;font-size:12px;padding:8px 14px;border-radius:999px;z-index:1201}" +
      "#syncToast[hidden]{display:none}";
    document.head.appendChild(st);

    var bar = document.createElement("div");
    bar.id = "syncBar"; bar.hidden = true;
    bar.innerHTML = '<span id="syncBarText"></span>' +
      '<button type="button" id="syncApply"></button><button type="button" class="x" id="syncX" aria-label="关闭">×</button>';
    document.body.appendChild(bar);
    document.getElementById("syncApply").textContent = T("刷新", "새로고침", "Refresh");
    document.getElementById("syncApply").onclick = function () { applyUpdate(); };
    document.getElementById("syncX").onclick = function () {
      bar.hidden = true; ls(KEY.rev, String(state.rev));
    };

    var upd = document.createElement("div");
    upd.id = "updModal"; upd.hidden = true;
    upd.innerHTML = '<div class="box"><h3 id="updTitle"></h3><div class="n" id="updNotes"></div>' +
      '<div class="acts"><a id="updGo" href="#" target="_blank" rel="noopener"></a>' +
      '<button type="button" id="updLater"></button></div>' +
      '<div class="acts" style="margin-top:8px"><button type="button" id="updSkip"></button></div></div>';
    document.body.appendChild(upd);
    document.getElementById("updTitle").textContent = T("发现新版本", "새 버전 발견", "New version available");
    document.getElementById("updGo").textContent = T("下载安装包", "설치 파일 다운로드", "Download APK");
    document.getElementById("updLater").textContent = T("稍后", "나중에", "Later");
    document.getElementById("updSkip").textContent = T("跳过这个版本", "이 버전 건너뛰기", "Skip this version");
    document.getElementById("updLater").onclick = function () { upd.hidden = true; };
    document.getElementById("updSkip").onclick = function () { ls(KEY.skip, String((state.version || {}).code || 0)); upd.hidden = true; };

    var tt = document.createElement("div");
    tt.id = "syncToast"; tt.hidden = true;
    document.body.appendChild(tt);
  }

  /* ---------- 启动 ---------- */
  function start() {
    applyLocalContent();
    inject();
    initSettings();
    setTimeout(function () { pollOnce(false); }, 3000);
    setInterval(function () { pollOnce(false); }, POLL_MS);
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) pollOnce(false);
    });
    window.addEventListener("online", function () { pollOnce(false); });
  }

  window.BusanSync = {
    pollOnce: pollOnce, applySpots: applySpots, applyLocalContent: applyLocalContent,
    parseState: parseState, versionNewer: versionNewer, mergeSpots: mergeSpots,
    contentPayload: contentPayload, state: state, BUILD: BUILD, _keys: KEY
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
