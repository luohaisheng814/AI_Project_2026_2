/* cloud.js —— 手机端「云端模式」引擎
 *
 * 定位：APK 不再依赖电脑上的 Python 服务。
 *   · 联网：从云端数据库（GitHub raw 上的 Busan/mobile/cloud/spots.json）取景点档案，
 *           再用原生 HTTP 桥实时抓景点官网正文核对；
 *   · 离线：云端库不可达时，退回包内最近一次快照 / 原始 data.js。
 * 这里的回答是「资料组装」，不做自由生成：只引用数据库与官网里真实存在的字段。
 */
(function () {
  var STR = {
    zh: {
      online: "联网 · 云端库", offline: "离线 · 包内数据", blocked: "离线 · 手机未允许联网",
      retry: "重试", loading: "正在读取云端数据库…", loadingOfficial: "正在核对景点官网…",
      welcomeTitle: "沙下区现场旅行助手",
      welcome: "问景点、交通、门票、开放时间都行。\n联网时用云端数据库 + 景点官网回答，不经过电脑；断网后自动切到包内数据。",
      noNet: "手机当前没有可用网络，已切到包内数据。",
      cloudFail: "云端数据库暂时取不到，已切到包内最近快照。",
      notFound: "库里没有这个地点。沙下区目前收录：" ,
      sourcesLabel: "资料来源", officialLabel: "官网核对", officialFail: "官网没取到内容（可能被拦截或无网络）",
      officialFrom: "官网原文（韩文）", fetchedAt: "抓取时间",
      km: "公里", nearbyTitle: "附近景点", nearbyNone: "附近 15 公里内没有收录景点。",
      rec: "推荐", rest: "其余", more: "个（点开看）",
      askTransport: "交通", askTicket: "门票", askHours: "开放时间", askPhoto: "拍照点",      youMayAsk: "你可能还想问", jump: "导航", place: "地点", webmap: "网页地图", google: "Google",
      conciseHint: "想看交通、门票或开放时间，直接问我就行。",
      catArt: "艺术村落，适合慢慢逛、拍照",
      catSunset: "海岸日落，傍晚最值",
      catWet: "湿地生态，看候鸟与开阔水面",
      catPort: "小众渔港，适合拍照",
      locating: "正在定位…", originTitle: "没有拿到位置，先用一个已收录地点当起点：",
      nearbyDenied: "定位权限被拒绝，已改为按已收录景点推荐。",
      nearbyTimeout: "定位超时，已改为按已收录景点推荐。",
      officialLive: "官网实时",
      localNote: "以上来自包内数据（离线）"
    },
    ko: {
      online: "온라인 · 클라우드", offline: "오프라인 · 내장 데이터", blocked: "오프라인 · 네트워크 차단",
      retry: "다시 시도", loading: "클라우드 데이터를 불러오는 중…", loadingOfficial: "공식 사이트를 확인하는 중…",
      welcomeTitle: "사하구 현장 여행 도우미",
      welcome: "명소, 교통, 입장료, 운영시간 모두 질문할 수 있습니다.\n온라인일 때는 클라우드 데이터와 공식 사이트로 답하며 PC를 거치지 않습니다. 네트워크가 끊기면 내장 데이터로 전환됩니다.",
      noNet: "현재 사용 가능한 네트워크가 없어 내장 데이터로 전환했습니다.",
      cloudFail: "클라우드 데이터를 가져오지 못해 최근 스냅숏으로 전환했습니다.",
      notFound: "해당 장소가 데이터에 없습니다. 현재 사하구 수록 지점:",
      sourcesLabel: "자료 출처", officialLabel: "공식 사이트 확인", officialFail: "공식 사이트 내용을 가져오지 못했습니다(차단 또는 네트워크 없음)",
      officialFrom: "공식 사이트 원문(한국어)", fetchedAt: "가져온 시각",
      km: "km", nearbyTitle: "주변 명소", nearbyNone: "주변 15km 내에 수록된 명소가 없습니다.",
      rec: "추천", rest: "나머지", more: "곳(펼쳐 보기)",
      askTransport: "교통", askTicket: "입장료", askHours: "운영시간", askPhoto: "사진 명소",
      youMayAsk: "이런 질문도 가능", jump: "길찾기", place: "장소", webmap: "웹 지도", google: "Google",
      conciseHint: "교통·입장료·운영시간이 궁금하면 바로 물어보세요.",
      catArt: "예술마을, 천천히 걷고 사진 찍기 좋음",
      catSunset: "해안 일몰, 저녁이 가장 좋음",
      catWet: "습지 생태, 철새와 탁 트인 수면",
      catPort: "작은 어항, 사진 찍기 좋음",
      locating: "위치를 확인하는 중…", originTitle: "위치를 못 받았습니다. 수록된 지점을 출발지로 선택하세요:",
      nearbyDenied: "위치 권한이 거부되어 수록 지점 기준으로 추천합니다.",
      nearbyTimeout: "위치 확인 시간이 초과되어 수록 지점 기준으로 추천합니다.",
      officialLive: "공식 사이트 실시간",
      localNote: "내장 데이터 기준입니다(오프라인)"
    },
    en: {
      online: "Online · Cloud DB", offline: "Offline · Bundled data", blocked: "Offline · Network blocked",
      retry: "Retry", loading: "Loading cloud database…", loadingOfficial: "Checking official site…",
      welcomeTitle: "Saha-gu Field Travel Assistant",
      welcome: "Ask about spots, transport, tickets or hours.\nOnline answers come from the cloud database plus official sites — no PC involved. Without network it falls back to bundled data.",
      noNet: "No usable network right now — switched to bundled data.",
      cloudFail: "Cloud database is unreachable — using the latest bundled snapshot.",
      notFound: "That place is not in the database. Covered spots in Saha-gu:",
      sourcesLabel: "Sources", officialLabel: "Official site check", officialFail: "Official site returned nothing (blocked or no network)",
      officialFrom: "Official text (Korean)", fetchedAt: "Fetched at",
      km: "km", nearbyTitle: "Nearby spots", nearbyNone: "No covered spot within 15 km.",
      rec: "Pick", rest: "Other", more: "more (tap to open)",
      askTransport: "Transport", askTicket: "Tickets", askHours: "Hours", askPhoto: "Photo spots",
      youMayAsk: "You may also ask", jump: "Directions", place: "Place", webmap: "Web map", google: "Google",
      conciseHint: "Ask me about transport, tickets or hours anytime.",
      catArt: "Art village — slow walks and photos",
      catSunset: "Coastal sunset — best in the evening",
      catWet: "Wetland ecology — birds and open water",
      catPort: "Small fishing port — good for photos",
      locating: "Locating…", originTitle: "No position available — pick a covered spot as your start:",
      nearbyDenied: "Location permission denied — recommending from covered spots instead.",
      nearbyTimeout: "Location timed out — recommending from covered spots instead.",
      officialLive: "official site live",
      localNote: "From bundled data (offline)"
    }
  };

  var st = { lang: "zh", db: null, mode: "offline", reason: "", fetchedAt: "", official: {}, snapshot: false };
  // 包内最近一份云端快照：离线时也能算附近、拼地图深链，避免「有数据但按钮点不了」
  var SNAP = window.BUSAN_CLOUD_SNAPSHOT || null;
  var CAT_REASON = {
    "01_艺术村落_文化街区": "catArt",
    "02_海岸休闲_日落夜景": "catSunset",
    "03_湿地生态_自然观景": "catWet",
    "04_小众渔港_文艺拍照": "catPort"
  };

  function t(key) { return (STR[st.lang] || STR.zh)[key]; }
  function tidy(s) { return String(s == null ? "" : s).replace(/\r/g, "").trim(); }
  function key(s) { return tidy(s).toLowerCase().replace(/[\s\u3000]+/g, ""); }

  function haversine(a, b, c, d) {
    var R = 6371, rad = Math.PI / 180;
    var dLat = (c - a) * rad, dLng = (d - b) * rad;
    var x = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(a * rad) * Math.cos(c * rad) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return 2 * R * Math.asin(Math.sqrt(x));
  }

  function spots() { return (st.db && st.db.spots) || []; }

  function findSpot(q) {
    var k = key(q);
    if (!k) return null;
    var list = spots(), best = null, bestScore = 0;
    for (var i = 0; i < list.length; i++) {
      var s = list[i], names = [s.name, s.name_ko, s.name_en].concat(s.aliases || []);
      for (var j = 0; j < names.length; j++) {
        var nk = key(names[j]);
        if (!nk) continue;
        var score = 0;
        if (k === nk) score = 1000;
        else if (k.indexOf(nk) >= 0) score = 600 + nk.length;
        else if (nk.indexOf(k) >= 0 && k.length >= 2) score = 500 + k.length;
        if (score > bestScore) { bestScore = score; best = s; }
      }
    }
    return best;
  }

  var INTENTS = [
    ["transport", ["交通", "怎么去", "怎样去", "路线", "地铁", "公交", "打车", "停车", "교통", "가는", "지하철", "버스", "주차", "transport", "how to get", "subway", "bus", "parking"]],
    ["ticket", ["门票", "费用", "多少钱", "票价", "入场", "입장료", "요금", "얼마", "무료", "ticket", "fee", "price", "admission"]],
    ["hours", ["开放", "时间", "几点", "营业", "运营", "休馆", "闭馆", "운영", "개방", "시간", "휴관", "몇시", "hours", "open", "close", "opening"]],
    ["photo", ["拍照", "机位", "打卡", "摄影", "사진", "포토", "photo", "camera", "instagram"]],
    ["highlights", ["亮点", "看什么", "玩什么", "볼거리", "명소", "highlight", "see", "must"]],
    ["tips", ["注意", "주의", "팁", "tips", "caution", "warning"]],
    ["around", ["周边", "附近", "주변", "근처", "nearby", "around"]]
  ];

  function intentOf(q) {
    var k = key(q);
    for (var i = 0; i < INTENTS.length; i++) {
      var words = INTENTS[i][1];
      for (var j = 0; j < words.length; j++) {
        if (k.indexOf(key(words[j])) >= 0) return INTENTS[i][0];
      }
    }
    return "overview";
  }

  function pickField(s, field) {
    var block = (s.fields && (s.fields[st.lang] || s.fields.zh)) || {};
    return tidy(block[field] || "");
  }

  function firstLines(text, n) {
    var arr = tidy(text).split("\n").map(tidy).filter(function (x) { return x; });
    return arr.slice(0, n);
  }

  function catLabel(cat) {
    var c = (st.db && st.db.strings && st.db.strings.categories && st.db.strings.categories[cat]) || null;
    var s = c ? (c[st.lang] || c.zh) : "";
    return String(s).replace(/^\d+[_\s.、-]*/, "");
  }

  function reasonOf(s) { return t(CAT_REASON[s.category] || "catArt"); }

  function spotTitle(s) {
    if (st.lang === "ko" && s.name_ko) return s.name_ko;
    if (st.lang === "en" && s.name_en) return s.name_en;
    return s.name;
  }

  function sourcesFor(s, officialNote) {
    var out = [];
    out.push((st.mode === "online" ? "云端数据库 spots.json（" + (st.db.updated_at || "") + "）"
      : "包内数据 cloud_snapshot.json（离线）"));
    if (officialNote && officialNote.ok) out.push("官网 " + officialNote.url);
    else if (officialNote) out.push("官网 " + officialNote.url + "（未取到正文）");
    else if (s.official && s.official.url) out.push("官网 " + s.official.url);
    return out;
  }

  function followupsFor(s) {
    var title = spotTitle(s);
    return [title + " " + t("askTransport"), title + " " + t("askTicket"),
            title + " " + t("askHours"), title + " " + t("askPhoto")];
  }

  /** 其它玩法的补充推荐：只换不同类别、最多 2 个，排在主回答之后。 */
  function supplements(s, limit) {
    var out = [], seen = {}, list = spots();
    for (var i = 0; i < list.length && out.length < limit; i++) {
      var x = list[i];
      if (x.id === s.id || x.category === s.category || seen[x.category]) continue;
      seen[x.category] = 1;
      out.push(x);
    }
    return out;
  }

  function compose(s, intent, opts) {
    var concise = !!(opts && opts.concise);
    var lines = [];
    var field = intent === "overview" ? "overview" : intent;
    var body = pickField(s, field);
    var title = spotTitle(s);
    lines.push("**" + title + "**" + (catLabel(s.category) ? " · " + catLabel(s.category) : ""));
    if (!body && intent !== "overview") body = pickField(s, "overview");
    if (body) {
      var max = concise ? 2 : (intent === "transport" || intent === "hours" ? 5 : 4);
      var rows = firstLines(body, max);
      rows.forEach(function (r) { lines.push("- " + r); });
    } else {
      lines.push("- " + t("localNote"));
    }
    if (intent === "overview" || concise) {
      var hl = pickField(s, "highlights");
      if (hl) {
        var h = firstLines(hl, 2);
        if (h.length) lines.push("", "**" + (st.lang === "zh" ? "看点" : st.lang === "ko" ? "볼거리" : "Highlights") + "**");
        h.forEach(function (x) { lines.push("- " + x); });
      }
      var sup = supplements(s, 2);
      if (sup.length) {
        lines.push("", "**" + (st.lang === "zh" ? "其它玩法补充推荐" : st.lang === "ko" ? "다른 테마 추천" : "Other themes") + "**");
        sup.forEach(function (x) {
          lines.push("- **" + spotTitle(x) + "**（" + (catLabel(x.category) || "") + "）：" + reasonOf(x));
        });
      }
    }
    if (concise) lines.push("", t("conciseHint"));
    return {
      text: lines.join("\n"),
      sources: sourcesFor(s),
      followups: followupsFor(s),
      spotId: s.id,
      intent: intent,
      concrete: true
    };
  }

  function answer(q, opts) {
    opts = opts || {};
    var s = findSpot(q);
    var intent = intentOf(q);
    if (!s) {
      // 「附近 / 推荐」交给 nearby；这里只处理纯文本匹配不到的情况
      var names = spots().map(function (x) { return "**" + spotTitle(x) + "**"; });
      return {
        text: t("notFound") + "\n\n" + names.join(" · "),
        sources: [], followups: names.slice(0, 4).map(function (x) { return x.replace(/\*\*/g, ""); }),
        concrete: false
      };
    }
    var onlyName = key(q) === key(s.name) || key(q) === key(s.name_ko || "") || key(q) === key(s.name_en || "");
    return compose(s, onlyName ? "overview" : intent, { concise: onlyName || opts.concise });
  }

  function nearby(lat, lng, n) {
    var list = spots().filter(function (s) { return s.lat != null && s.lng != null; });
    var rows = list.map(function (s) {
      return { spot: s, km: haversine(lat, lng, s.lat, s.lng) };
    }).sort(function (a, b) { return a.km - b.km; });
    var near = rows.filter(function (r) { return r.km <= 15; });
    if (!near.length) near = rows.slice(0, 3);
    return near.slice(0, n || 3);
  }

  function mapLinks(s) {
    var name = s.name_ko || s.name;
    var dlat = s.lat, dlng = s.lng;
    if (dlat == null || dlng == null) {
      return {
        nav: "nmap://search?query=" + encodeURIComponent(name) + "&appname=com.busan.tour",
        place: "nmap://search?query=" + encodeURIComponent(name) + "&appname=com.busan.tour",
        web: "https://map.naver.com/p/search/" + encodeURIComponent(name),
        google: "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(name)
      };
    }
    return {
      nav: "nmap://route/public?slat=&slng=&sname=%ED%98%84%EC%9C%84%EC%B9%98&dlat=" + dlat + "&dlng=" + dlng +
        "&dname=" + encodeURIComponent(name) + "&appname=com.busan.tour",
      place: "nmap://place?lat=" + dlat + "&lng=" + dlng + "&name=" + encodeURIComponent(name) + "&appname=com.busan.tour",
      web: "https://map.naver.com/p/search/" + encodeURIComponent(name),
      google: "https://www.google.com/maps/dir/?api=1&destination=" + dlat + "," + dlng
    };
  }

  /* ---- 云端库加载 ---- */
  var ENDPOINTS = [
    "https://raw.githubusercontent.com/luohaisheng814/AI_Project_2026_2/main/Busan/mobile/cloud/spots.json",
    "https://cdn.jsdelivr.net/gh/luohaisheng814/AI_Project_2026_2@main/Busan/mobile/cloud/spots.json"
  ];
  var CACHE_KEY = "busan_cloud_snapshot";

  function httpGet(url, cb) {
    if (window.BusanHost && typeof window.BusanHost.fetchText === "function") {
      var id = "cb" + Math.random().toString(36).slice(2);
      window.__busanHttpCbs = window.__busanHttpCbs || {};
      window.__busanHttpCbs[id] = cb;
      try { window.BusanHost.fetchText(url, id); } catch (e) { cb(-1, ""); }
      return;
    }
    if (typeof fetch === "function") {
      fetch(url, { cache: "no-store" }).then(function (r) {
        return r.text().then(function (t) { cb(r.status, t); });
      }).catch(function () { cb(-1, ""); });
      return;
    }
    cb(-1, "");
  }

  window.__busanHttpDone = function (id, status, body) {
    var f = window.__busanHttpCbs && window.__busanHttpCbs[id];
    if (f) { delete window.__busanHttpCbs[id]; f(status, body || ""); }
  };

  function parse(payload) {
    try {
      var data = typeof payload === "string" ? JSON.parse(payload) : payload;
      if (!data || !data.spots) return null;
      return data;
    } catch (e) { return null; }
  }

  function loadCloud(cb) {
    var i = 0;
    var blocked = window.BusanHost && typeof window.BusanHost.netAllowed === "function" && !window.BusanHost.netAllowed();
    if (blocked) {
      useSnapshot();
      st.mode = "offline"; st.reason = "blocked";
      return cb(st);
    }
    function next() {
      if (i >= ENDPOINTS.length) {
        useSnapshot();
        st.mode = "offline"; st.reason = "cloudFail";
        return cb(st);
      }
      var url = ENDPOINTS[i++];
      httpGet(url, function (status, body) {
        var db = (status === 200 || status === 0) ? parse(body) : null;
        if (db && db.spots && db.spots.length) {
          st.db = db; st.mode = "online"; st.reason = "";
          st.snapshot = false;
          st.fetchedAt = new Date().toTimeString().slice(0, 5);
          return cb(st);
        }
        next();
      });
    }
    next();
  }

  function useSnapshot() {
    if (!st.db && SNAP && SNAP.spots) {
      st.db = SNAP;
      st.snapshot = true;
    }
  }

  /* ---- 官网正文核对 ---- */
  function textOfHtml(html) {
    var h = String(html || "");
    var idx = h.indexOf('id="conts"');
    if (idx > 0) h = h.slice(idx, idx + 6000);
    h = h.replace(/<script[\s\S]*?<\/script>/gi, " ")
      .replace(/<style[\s\S]*?<\/style>/gi, " ")
      .replace(/<[^>]+>/g, "\n");
    h = h.replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"');
    return h.split("\n").map(tidy).filter(function (x) { return x && x.length > 3; });
  }

  function fetchOfficial(s, cb) {
    if (!s.official || !s.official.url) return cb(null);
    if (st.official[s.id]) return cb(st.official[s.id]);
    var url = s.official.url;
    httpGet(url, function (status, body) {
      var lines = textOfHtml(body).filter(function (x) { return !/^[|/\-=]+$/.test(x); });
      var ok = (status === 200 || status === 0) && lines.length > 0;
      var note = { ok: ok, url: url, lines: lines.slice(0, 12), at: new Date().toTimeString().slice(0, 5) };
      st.official[s.id] = note;
      cb(note);
    });
  }

  window.BusanCloud = {
    init: function (lang) { if (lang) st.lang = lang; return st; },
    load: loadCloud,
    setLang: function (l) { st.lang = l; },
    getLang: function () { return st.lang; },
    getMode: function () { return st.mode; },
    getReason: function () { return st.reason; },
    getDb: function () { return st.db; },
    setDb: function (db) { st.db = db; },
    isSnapshot: function () { return (st.mode !== "online") && !!st.db; },
    strings: function () { return STR[st.lang] || STR.zh; },
    answer: answer,
    intentOf: intentOf,
    findSpot: findSpot,
    nearby: nearby,
    mapLinks: mapLinks,
    fetchOfficial: fetchOfficial,
    officialNote: function (id) { return st.official[id]; },
    spotTitle: spotTitle,
    catLabel: catLabel,
    reasonOf: reasonOf,
    haversine: haversine
  };
})();
