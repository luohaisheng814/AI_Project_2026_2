/* session.js —— 账户、会话、偏好、网络提示与大模型通道
 *
 * 账户密码只在原生壳里做 PBKDF2 哈希并写入应用私有目录；网页只拿会话结果。
 * 未登录：不写任何账户状态，启动时由 BusanUI.resetGuest() 清成全新界面。
 * 已登录：语言 / 玩法 / 出行 / 最近问题 / 偏好 / 上次推演按用户保存。
 */
(function () {
  var HOST = window.BusanHost || null;
  var DEMO_AUTH = "busan_demo_auth";
  var DEMO_SESSION = "busan_demo_session";

  var user = null;
  var profile = { pace: "balanced", budget: "medium", mobility: "normal", interests: [], notes: "" };
  var saveTimer = null;
  var toastTimer = null;
  var authBusy = false;
  var llmCfg = { endpoint: "", model: "", hasKey: false, keyTail: "" };

  function lang() { return (window.BusanUI && BusanUI.getLang()) || "zh"; }
  function L(zh, ko, en) { return lang() === "zh" ? zh : lang() === "ko" ? ko : en; }

  function hasHost(name) {
    return !!(HOST && typeof HOST[name] === "function");
  }

  function demoUsers() {
    try { return JSON.parse(localStorage.getItem(DEMO_AUTH) || "{}"); } catch (e) { return {}; }
  }
  function demoHash(s) {
    var h = 5381;
    for (var i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) >>> 0;
    return "d" + h.toString(16);
  }
  function demoSession() {
    try { return JSON.parse(localStorage.getItem(DEMO_SESSION) || "null"); } catch (e) { return null; }
  }
  function demoCall(name, a, b, c) {
    var users = demoUsers();
    if (name === "authRegister") {
      var key = String(a || "").trim().toLowerCase();
      if (key.length < 2) return { ok: false, error: "username_length" };
      if (String(b || "").length < 6) return { ok: false, error: "password_length" };
      if (users[key]) return { ok: false, error: "user_exists" };
      users[key] = {
        username: String(a).trim(),
        displayName: String(c || a).trim(),
        hash: demoHash(key + "|" + b),
        createdAt: Date.now(),
        lastActive: Date.now()
      };
      localStorage.setItem(DEMO_AUTH, JSON.stringify(users));
      localStorage.setItem(DEMO_SESSION, JSON.stringify({ key: key, token: "demo", at: Date.now() }));
      return { ok: true, user: pub(users[key]) };
    }
    if (name === "authLogin") {
      var k = String(a || "").trim().toLowerCase();
      var rec = users[k];
      if (!rec || rec.hash !== demoHash(k + "|" + b)) return { ok: false, error: "invalid_credentials" };
      rec.lastActive = Date.now();
      localStorage.setItem(DEMO_AUTH, JSON.stringify(users));
      localStorage.setItem(DEMO_SESSION, JSON.stringify({ key: k, token: "demo", at: Date.now() }));
      return { ok: true, user: pub(rec) };
    }
    if (name === "authCurrent") {
      var s = demoSession();
      if (!s) return { ok: false, error: "none" };
      var r = users[s.key];
      if (!r) return { ok: false, error: "none" };
      if (Date.now() - (r.lastActive || 0) > 30 * 24 * 3600 * 1000) {
        localStorage.removeItem(DEMO_SESSION);
        return { ok: false, error: "expired" };
      }
      r.lastActive = Date.now();
      localStorage.setItem(DEMO_AUTH, JSON.stringify(users));
      return { ok: true, user: pub(r) };
    }
    if (name === "authLogout") { localStorage.removeItem(DEMO_SESSION); return { ok: true }; }
    if (name === "saveUserState") {
      var ss = demoSession();
      if (!ss) return { ok: false, error: "auth" };
      localStorage.setItem("busan_state_" + ss.key, String(a || "{}"));
      return { ok: true };
    }
    if (name === "loadUserState") {
      var s2 = demoSession();
      if (!s2) return "{}";
      return localStorage.getItem("busan_state_" + s2.key) || "{}";
    }
    return { ok: false, error: "demo_unsupported" };
  }
  function pub(rec) {
    return {
      username: rec.username,
      displayName: rec.displayName || rec.username,
      createdAt: rec.createdAt,
      lastLogin: rec.lastLogin || 0,
      lastActive: rec.lastActive || 0
    };
  }

  function call(name, a, b, c) {
    if (hasHost(name)) {
      try {
        var r = HOST[name](a, b, c);
        if (typeof r === "string") {
          try { return JSON.parse(r); } catch (e) { return { ok: false, error: "bad_payload" }; }
        }
        return r;
      } catch (e) {
        return { ok: false, error: "bridge_error" };
      }
    }
    return demoCall(name, a, b, c);
  }

  function stateText(name, a, b, c) {
    if (hasHost(name)) {
      try { return HOST[name](a, b, c); } catch (e) { return "{}"; }
    }
    return demoCall(name, a, b, c);
  }

  /* ---------------- 错误文案 ---------------- */
  function errText(res) {
    var code = (res && res.error) || "unknown";
    var map = {
      username_length: L("用户名需为 2–24 个字符", "사용자 이름은 2~24자여야 합니다", "Username must be 2–24 characters"),
      password_length: L("密码至少 6 位", "비밀번호는 6자 이상이어야 합니다", "Password must be at least 6 characters"),
      user_exists: L("这个用户名已经注册", "이미 사용 중인 사용자 이름입니다", "That username is already registered"),
      invalid_credentials: L("用户名或密码不正确", "사용자 이름 또는 비밀번호가 맞지 않습니다", "Username or password is incorrect"),
      empty: L("请输入用户名和密码", "사용자 이름과 비밀번호를 입력하세요", "Enter both username and password"),
      expired: L("超过 30 天未使用，登录已自动退出", "30일 이상 미사용으로 자동 로그아웃되었습니다", "Signed out automatically after 30 days unused"),
      auth: L("登录状态已失效，请重新登录", "로그인 상태가 만료되었습니다", "Session expired — please sign in again"),
      endpoint_scheme: L("接口地址需以 http:// 或 https:// 开头", "API 주소는 http:// 또는 https://로 시작해야 합니다", "Endpoint must start with http:// or https://"),
      bad_payload: L("本机返回数据异常", "기기 응답이 올바르지 않습니다", "Bad response from device"),
      bridge_error: L("本机账户服务不可用", "기기 계정 서비스를 사용할 수 없습니다", "Local account service unavailable"),
      unknown: L("操作失败，请重试", "작업 실패, 다시 시도하세요", "Something went wrong — try again")
    };
    return map[code] || (res && res.message) || map.unknown;
  }

  /* ---------------- 顶部账户按钮与弹层文案 ---------------- */
  function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
  }
  function setPh(id, text) {
    var el = document.getElementById(id);
    if (el) el.setAttribute("placeholder", text);
  }
  function setLabel(forId, text) {
    var el = document.querySelector('label[for="' + forId + '"]');
    if (el) el.textContent = text;
  }

  function paintAuthText() {
    if (!document.getElementById("authModal")) return;
    setText("authTitle", L("登录 / 注册", "로그인 / 회원가입", "Sign in / Register"));
    setText("authDesc", L("登录后保留玩法、偏好与上次推演；不登录则每次打开都是全新界面。",
      "로그인하면 테마·취향·최근 일정이 저장됩니다. 비로그인 상태에서는 매번 새 화면으로 시작합니다.",
      "Sign in to keep themes, preferences and your last plan; without it every launch starts fresh."));
    setText("tabLogin", L("登录", "로그인", "Sign in"));
    setText("tabRegister", L("注册", "회원가입", "Register"));
    setLabel("loginUser", L("用户名", "사용자 이름", "Username"));
    setPh("loginUser", L("2–24 个字符", "2~24자", "2–24 characters"));
    setLabel("loginPass", L("密码", "비밀번호", "Password"));
    setPh("loginPass", L("至少 6 位", "6자 이상", "At least 6 characters"));
    setText("loginGo", L("登录", "로그인", "Sign in"));
    setLabel("regName", L("用户名", "사용자 이름", "Username"));
    setPh("regName", L("2–24 个字符", "2~24자", "2–24 characters"));
    setLabel("regDisplay", L("显示名（可选）", "표시 이름(선택)", "Display name (optional)"));
    setPh("regDisplay", L("例如：小李", "예: 민수", "e.g. Min-su"));
    setLabel("regPass", L("密码", "비밀번호", "Password"));
    setPh("regPass", L("至少 6 位", "6자 이상", "At least 6 characters"));
    setLabel("regPass2", L("确认密码", "비밀번호 확인", "Confirm password"));
    setPh("regPass2", L("再输一次", "다시 입력", "Type it again"));
    setText("registerGo", L("注册并登录", "가입 후 로그인", "Register & sign in"));
    setText("guestClose", L("先以游客身份使用", "비로그인으로 사용", "Continue as guest"));
    setText("authFine", L("账户与密码只保存在这台手机的应用私有目录；卸载重装会清空账户。登录后 30 天不打开会自动退出。",
      "계정과 비밀번호는 이 기기의 앱 전용 저장소에만 보관됩니다. 앱을 삭제하면 계정도 삭제됩니다. 로그인 후 30일간 열지 않으면 자동 로그아웃됩니다.",
      "Account and password stay in this phone's private app storage. Uninstalling clears the account. Sign-in expires after 30 days unused."));

    var panelTitle = document.querySelector("#acctPanel h2");
    if (panelTitle) panelTitle.textContent = L("账户与偏好", "계정과 취향", "Account & preferences");
    var panelDesc = document.querySelector("#acctPanel > .desc");
    if (panelDesc) panelDesc.textContent = L("偏好会参与下一次行程推演；点“保存偏好”后写入本机账户。",
      "취향은 다음 일정 추천에 반영됩니다. ‘취향 저장’을 누르면 이 기기 계정에 저장됩니다.",
      "Preferences feed the next plan; tap “Save preferences” to store them on this device.");
    setText("prefSave", L("保存偏好", "취향 저장", "Save preferences"));
    setText("llmSave", L("保存设置", "설정 저장", "Save settings"));
    setText("llmTest", L("测试连接", "연결 테스트", "Test connection"));
    setText("logoutBtn", L("退出登录", "로그아웃", "Sign out"));
  }

  function paintAccount() {
    var btn = document.getElementById("acctBtn");
    paintAuthText();
    if (!btn) return;
    if (user) {
      btn.textContent = user.displayName || user.username;
      btn.classList.remove("guest");
      btn.title = user.username;
    } else {
      btn.textContent = L("登录", "로그인", "Sign in");
      btn.classList.add("guest");
      btn.title = "";
    }
  }

  function applyLoadedState() {
    if (!user) return;
    var raw = stateText("loadUserState");
    var st = {};
    try { st = JSON.parse(raw || "{}"); } catch (e) { st = {}; }
    if (st.profile) {
      profile.pace = st.profile.pace || profile.pace;
      profile.budget = st.profile.budget || profile.budget;
      profile.mobility = st.profile.mobility || profile.mobility;
      profile.interests = Array.isArray(st.profile.interests) ? st.profile.interests : [];
      profile.notes = st.profile.notes || "";
    }
    if (window.BusanUI) {
      BusanUI.setWelcome(user.displayName || user.username);
      BusanUI.applyState(st);
    }
  }

  function collectState() {
    var s = (window.BusanUI && BusanUI.snapshot()) || {};
    s.profile = profile;
    s.user = user ? { username: user.username, displayName: user.displayName } : null;
    return s;
  }

  function saveNow() {
    if (!user) return;
    var s = collectState();
    s.profile = profile;
    if (window.BusanUI) BusanUI.setLastPlan(s.lastPlan);
    var res = call("saveUserState", JSON.stringify(s));
    if (res && res.ok === false && res.error === "auth") {
      user = null;
      paintAccount();
      if (window.BusanToast) BusanToast.show(L("登录状态已失效", "로그인이 만료되었습니다", "Session expired"), errText(res));
      if (window.BusanUI) BusanUI.resetGuest();
    }
  }

  function saveSoon() {
    if (!user) return;
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveNow, 650);
  }

  /* ---------------- 弹层 ---------------- */
  function openModal(tab) {
    var modal = document.getElementById("authModal");
    if (!modal) return;
    modal.hidden = false;
    if (user) {
      document.getElementById("authGuest").hidden = true;
      document.getElementById("acctPanel").hidden = false;
      fillAccountPanel();
    } else {
      document.getElementById("authGuest").hidden = false;
      document.getElementById("acctPanel").hidden = true;
      switchTab(tab || "login");
      setTimeout(function () {
        var i = document.getElementById(tab === "register" ? "regName" : "loginUser");
        if (i) try { i.focus(); } catch (e) {}
      }, 120);
    }
  }

  function closeModal() {
    var modal = document.getElementById("authModal");
    if (modal) modal.hidden = true;
  }

  function switchTab(tab) {
    var login = document.getElementById("loginForm");
    var reg = document.getElementById("registerForm");
    var tl = document.getElementById("tabLogin");
    var tr = document.getElementById("tabRegister");
    var isLogin = tab === "login";
    login.hidden = !isLogin;
    reg.hidden = isLogin;
    tl.classList.toggle("on", isLogin);
    tr.classList.toggle("on", !isLogin);
    document.getElementById("loginErr").textContent = "";
    document.getElementById("regErr").textContent = "";
  }

  function setBusy(b, which) {
    authBusy = b;
    ["loginGo", "registerGo"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.disabled = b;
    });
    if (which) {
      var btn = document.getElementById(which);
      if (btn) btn.textContent = b
        ? L("请稍候…", "잠시만…", "Working…")
        : (which === "loginGo" ? L("登录", "로그인", "Sign in") : L("注册并登录", "가입 후 로그인", "Register & sign in"));
    }
  }

  function onAuthSuccess(res) {
    user = res.user;
    profile = { pace: "balanced", budget: "medium", mobility: "normal", interests: [], notes: "" };
    paintAccount();
    closeModal();
    applyLoadedState();
    paintAccount();
    var hasState = false;
    try {
      var raw = stateText("loadUserState");
      var st = JSON.parse(raw || "{}");
      hasState = !!(st && st.history && st.history.length);
    } catch (e) {}
    if (!hasState && window.BusanToast) {
      BusanToast.show(
        L("已登录", "로그인되었습니다", "Signed in"),
        L("之后的玩法、偏好与推演会保存在这台手机上。", "이제 테마·취향·일정이 이 기기에 저장됩니다.", "Themes, preferences and plans will persist on this phone."));
    }
    saveSoon();
  }

  function doLogin(e) {
    if (e) e.preventDefault();
    if (authBusy) return;
    var u = document.getElementById("loginUser").value.trim();
    var p = document.getElementById("loginPass").value;
    var err = document.getElementById("loginErr");
    err.textContent = "";
    setBusy(true, "loginGo");
    setTimeout(function () {
      var res = call("authLogin", u, p);
      setBusy(false, "loginGo");
      if (!res || !res.ok) { err.textContent = errText(res); return; }
      document.getElementById("loginPass").value = "";
      onAuthSuccess(res);
    }, 30);
  }

  function doRegister(e) {
    if (e) e.preventDefault();
    if (authBusy) return;
    var u = document.getElementById("regName").value.trim();
    var d = document.getElementById("regDisplay").value.trim();
    var p = document.getElementById("regPass").value;
    var p2 = document.getElementById("regPass2").value;
    var err = document.getElementById("regErr");
    err.textContent = "";
    if (p !== p2) { err.textContent = L("两次密码不一致", "비밀번호가 일치하지 않습니다", "Passwords do not match"); return; }
    setBusy(true, "registerGo");
    setTimeout(function () {
      var res = call("authRegister", u, p, d);
      setBusy(false, "registerGo");
      if (!res || !res.ok) { err.textContent = errText(res); return; }
      document.getElementById("regPass").value = "";
      document.getElementById("regPass2").value = "";
      onAuthSuccess(res);
    }, 30);
  }

  function logout() {
    call("authLogout");
    user = null;
    clearTimeout(saveTimer);
    profile = { pace: "balanced", budget: "medium", mobility: "normal", interests: [], notes: "" };
    paintAccount();
    closeModal();
    if (window.BusanUI) BusanUI.resetGuest();
    if (window.BusanToast) BusanToast.show(
      L("已退出登录", "로그아웃되었습니다", "Signed out"),
      L("现在每次打开都是全新界面。", "이제 앱을 열 때마다 새 화면으로 시작합니다.", "Each launch now starts fresh."));
  }

  /* ---------------- 偏好面板 ---------------- */
  function fillAccountPanel() {
    if (!user) return;
    document.getElementById("acctAvatar").textContent = (user.displayName || user.username || "U").slice(0, 1).toUpperCase();
    document.getElementById("acctName").textContent = user.displayName || user.username;
    var when = user.lastLogin ? new Date(user.lastLogin).toLocaleDateString() : "";
    document.getElementById("acctMeta").textContent = "@" + user.username + (when ? " · " + L("上次登录 ", "최근 로그인 ", "last login ") + when : "");

    document.getElementById("prefPace").value = profile.pace;
    document.getElementById("prefBudget").value = profile.budget;
    document.getElementById("prefMobility").value = profile.mobility;
    document.getElementById("prefNotes").value = profile.notes || "";
    var checks = document.querySelectorAll("#prefChecks input");
    checks.forEach(function (c) {
      c.checked = profile.interests.indexOf(c.value) >= 0;
      c.parentNode.classList.toggle("on", c.checked);
    });

    var lp = window.BusanUI && BusanUI.lastPlan();
    var box = document.getElementById("lastPlanBox");
    var txt = document.getElementById("lastPlanText");
    if (lp && lp.title) {
      box.hidden = false;
      txt.textContent = lp.title + (lp.summary ? " · " + lp.summary : "") + (lp.at ? "（" + lp.at + "）" : "");
    } else {
      box.hidden = true;
    }

    loadLlmIntoForm();
  }

  function saveProfile() {
    profile.pace = document.getElementById("prefPace").value;
    profile.budget = document.getElementById("prefBudget").value;
    profile.mobility = document.getElementById("prefMobility").value;
    profile.notes = document.getElementById("prefNotes").value.trim();
    profile.interests = [];
    document.querySelectorAll("#prefChecks input").forEach(function (c) {
      if (c.checked) profile.interests.push(c.value);
    });
    saveNow();
    if (window.BusanToast) BusanToast.show(
      L("偏好已保存", "취향이 저장되었습니다", "Preferences saved"),
      L("下一次推演会把节奏、预算、同行与兴趣算进去。", "다음 일정에 속도·예산·동행·관심사를 반영합니다.", "The next plan will use pace, budget, mobility and interests."));
  }

  /* ---------------- 大模型 ---------------- */
  function loadLlmConfig() {
    if (hasHost("getLlmConfig")) {
      try {
        var raw = HOST.getLlmConfig();
        llmCfg = typeof raw === "string" ? JSON.parse(raw) : raw;
      } catch (e) { llmCfg = { endpoint: "", model: "", hasKey: false }; }
    } else {
      try { llmCfg = JSON.parse(localStorage.getItem("busan_llm_demo") || "{}"); } catch (e) { llmCfg = {}; }
    }
  }

  function loadLlmIntoForm() {
    loadLlmConfig();
    document.getElementById("llmEndpoint").value = llmCfg.endpoint || "";
    document.getElementById("llmModel").value = llmCfg.model || "";
    document.getElementById("llmKey").value = "";
    var status = document.getElementById("llmStatus");
    if (llmCfg.hasKey) {
      status.className = "llmstatus ok";
      status.textContent = L("已保存 Key（尾号 " + (llmCfg.keyTail || "") + "）；推演时会优先调用大模型。",
        "Key 저장됨(끝 " + (llmCfg.keyTail || "") + "). 일정 생성 시 LLM을 우선 호출합니다.",
        "Key saved (tail " + (llmCfg.keyTail || "") + "); plans will try the model first.");
    } else {
      status.className = "llmstatus";
      status.textContent = L("未配置大模型：当前使用本地核心词与规则推演。", "LLM 미설정: 로컬 핵심어·규칙으로 생성합니다.", "No model configured — using local core-word rules.");
    }
  }

  function saveLlm() {
    var endpoint = document.getElementById("llmEndpoint").value.trim();
    var model = document.getElementById("llmModel").value.trim();
    var key = document.getElementById("llmKey").value.trim();
    var status = document.getElementById("llmStatus");
    if (hasHost("saveLlmConfig")) {
      var res = call("saveLlmConfig", endpoint, key, model);
      if (!res || !res.ok) { status.className = "llmstatus err"; status.textContent = errText(res); return; }
    } else {
      var cfg = { endpoint: endpoint, model: model, hasKey: !!key, apiKey: key || (llmCfg.apiKey || "") };
      localStorage.setItem("busan_llm_demo", JSON.stringify(cfg));
    }
    document.getElementById("llmKey").value = "";
    loadLlmIntoForm();
    status.className = "llmstatus ok";
    status.textContent = L("设置已保存。", "설정이 저장되었습니다.", "Settings saved.");
  }

  function extractContent(body) {
    try {
      var data = typeof body === "string" ? JSON.parse(body) : body;
      if (data && data.error) return { error: data.error.message || String(data.error) };
      var c = ((data.choices || [])[0] || {}).message || {};
      var content = c.content;
      if (Array.isArray(content)) {
        content = content.map(function (p) { return typeof p === "string" ? p : (p.text || ""); }).join("");
      }
      return { content: String(content || "") };
    } catch (e) { return { error: "bad_response" }; }
  }

  var pending = {};

  window.__busanLlmDone = function (id, status, body) {
    var cb = pending[id];
    if (!cb) return;
    delete pending[id];
    if (status < 0) { cb(-1, "network", body); return; }
    if (status < 200 || status >= 300) {
      var e = extractContent(body);
      cb(status, e.error || "http_" + status, body);
      return;
    }
    var r = extractContent(body);
    if (r.content) cb(0, r.content, body);
    else cb(1, r.error || "empty", body);
  };

  function llmChat(messages, cb) {
    if (!llmConfigured()) { cb(-2, "not_configured", ""); return; }
    if (hasHost("llmChat")) {
      var id = "llm" + Math.random().toString(36).slice(2);
      pending[id] = cb;
      try {
        HOST.llmChat(JSON.stringify(messages), id);
      } catch (e) {
        delete pending[id];
        cb(-1, "bridge_error", "");
      }
      return;
    }
    loadLlmConfig();
    var endpoint = (llmCfg.endpoint || "").replace(/\/+$/, "");
    if (!/\/chat\/completions$/.test(endpoint)) endpoint += "/chat/completions";
    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": "Bearer " + (llmCfg.apiKey || "") },
      body: JSON.stringify({ model: llmCfg.model || "gpt-4o-mini", messages: messages, temperature: 0.25, max_tokens: 900 })
    }).then(function (r) { return r.text().then(function (t) { return { s: r.status, t: t }; }); })
      .then(function (x) {
        if (x.s < 200 || x.s >= 300) { cb(x.s, extractContent(x.t).error || "http_" + x.s, x.t); return; }
        var r = extractContent(x.t);
        cb(r.content ? 0 : 1, r.content || r.error || "empty", x.t);
      }).catch(function () { cb(-1, "network", ""); });
  }

  function llmConfigured() {
    loadLlmConfig();
    return !!(llmCfg && llmCfg.endpoint && llmCfg.hasKey);
  }

  function testLlm() {
    var status = document.getElementById("llmStatus");
    saveLlm();
    if (!llmConfigured()) {
      status.className = "llmstatus err";
      status.textContent = L("请先填写接口地址和 API Key。", "API 주소와 Key를 먼저 입력하세요.", "Fill in the endpoint and API key first.");
      return;
    }
    status.className = "llmstatus";
    status.textContent = L("正在测试…", "테스트 중…", "Testing…");
    llmChat([{ role: "user", content: "Reply with the single word OK." }], function (code, out) {
      if (code === 0) {
        status.className = "llmstatus ok";
        status.textContent = L("连接成功：" + String(out).slice(0, 40), "연결 성공: " + String(out).slice(0, 40), "Connected: " + String(out).slice(0, 40));
      } else {
        status.className = "llmstatus err";
        status.textContent = L("连接失败：" + out, "연결 실패: " + out, "Failed: " + out);
      }
    });
  }

  /* ---------------- 网络提示 ---------------- */
  function showToast(title, desc, ms) {
    var el = document.getElementById("netToast");
    if (!el) return;
    document.getElementById("netToastTitle").textContent = title;
    document.getElementById("netToastDesc").textContent = desc || "";
    el.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.classList.remove("show"); }, ms || 4000);
  }

  function startupNetToast() {
    if (!window.BusanUI) return;
    if (!BusanUI.cloudReady()) { setTimeout(startupNetToast, 700); return; }
    if (BusanUI.online()) {
      showToast(L("当前已联网", "온라인 상태입니다", "You are online"),
        L("正在使用云端库与官网核对，手机可独立回答。", "클라우드 데이터와 공식 사이트를 사용합니다.", "Using the cloud DB and official sites — no PC needed."), 3800);
    } else {
      showToast(L("当前未联网", "오프라인 상태입니다", "You are offline"),
        L("已使用包内数据；恢复网络后会自动切回云端库。", "내장 데이터를 사용 중입니다. 연결되면 자동 전환됩니다.", "Using bundled data; it will switch back when network returns."), 3800);
    }
  }

  /* ---------------- 启动 ---------------- */
  function init() {
    paintAccount();
    loadLlmConfig();

    var res = call("authCurrent");
    if (res && res.ok && res.user) {
      user = res.user;
      paintAccount();
      applyLoadedState();
      saveSoon();
    } else {
      if (res && res.error === "expired" && window.BusanToast) {
        showToast(L("登录已自动退出", "자동 로그아웃", "Signed out"), errText(res));
      }
      user = null;
      paintAccount();
      if (window.BusanUI) BusanUI.resetGuest();
    }

    var btn = document.getElementById("acctBtn");
    if (btn) btn.onclick = function () { openModal("login"); };
    var close = document.getElementById("authClose");
    if (close) close.onclick = closeModal;
    var guest = document.getElementById("guestClose");
    if (guest) guest.onclick = closeModal;
    var modal = document.getElementById("authModal");
    if (modal) modal.addEventListener("click", function (e) { if (e.target === modal) closeModal(); });

    var tl = document.getElementById("tabLogin");
    var tr = document.getElementById("tabRegister");
    if (tl) tl.onclick = function () { switchTab("login"); };
    if (tr) tr.onclick = function () { switchTab("register"); };
    var lf = document.getElementById("loginForm");
    var rf = document.getElementById("registerForm");
    if (lf) lf.addEventListener("submit", doLogin);
    if (rf) rf.addEventListener("submit", doRegister);

    var lo = document.getElementById("logoutBtn");
    if (lo) lo.onclick = logout;

    var ps = document.getElementById("prefSave");
    if (ps) ps.onclick = saveProfile;
    document.querySelectorAll("#prefChecks input").forEach(function (c) {
      c.addEventListener("change", function () {
        c.parentNode.classList.toggle("on", c.checked);
      });
    });

    var ls = document.getElementById("llmSave");
    if (ls) ls.onclick = saveLlm;
    var lt = document.getElementById("llmTest");
    if (lt) lt.onclick = testLlm;

    setTimeout(startupNetToast, 900);

    // 从后台回到前台：重新验证会话是否已超过 30 天
    document.addEventListener("visibilitychange", function () {
      if (document.hidden || !user) return;
      var check = call("authCurrent");
      if (!check || !check.ok) {
        user = null;
        paintAccount();
        if (window.BusanUI) BusanUI.resetGuest();
      }
    });
  }

  window.BusanToast = { show: showToast };

  window.BusanSession = {
    init: init,
    currentUser: function () { return user; },
    profile: function () { return profile; },
    saveNow: saveNow,
    saveSoon: saveSoon,
    refresh: function () { paintAccount(); },
    openAccount: function () { openModal("login"); }
  };
  window.BusanAuth = window.BusanSession;

  window.BusanLLM = {
    configured: llmConfigured,
    chat: llmChat,
    config: function () { loadLlmConfig(); return llmCfg; }
  };
})();
