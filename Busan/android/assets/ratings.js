/* v2.5 星级评级模块
 * 玩法 / 景观 / 便利 / 性价比 四项打分（1-5），综合分按权重折算成 5 星制；
 * 同时支持用户自己给景点打 1-5 星（本机保存），不改官方基线分。
 */
(function (global) {
  var LANG = "zh";
  var STORE = "busan_rating_user";
  function setLang(l) { if (/^(zh|ko|en)$/.test(l || "")) LANG = l; }
  function P(zh, ko, en) { return LANG === "zh" ? zh : LANG === "ko" ? ko : en; }

  /* play 玩法性 / view 景观 / ease 便利（体力·交通）/ value 性价比 */
  var BASE = {
    "甘川文化村":         { play: 4.7, view: 4.6, ease: 3.1, value: 4.4 },
    "多大浦梦之夕阳喷泉": { play: 4.5, view: 4.6, ease: 4.4, value: 4.7 },
    "多大浦海水浴场":     { play: 4.2, view: 4.3, ease: 4.5, value: 4.6 },
    "没云台":             { play: 4.0, view: 4.4, ease: 3.9, value: 4.5 },
    "乙淑岛候鸟公园":     { play: 4.3, view: 4.5, ease: 3.8, value: 4.6 },
    "峨嵋山观景台":       { play: 4.1, view: 4.7, ease: 3.2, value: 4.4 },
    "洛东江河口生态中心": { play: 3.9, view: 4.2, ease: 4.6, value: 4.8 },
    "长林浦口":           { play: 3.8, view: 4.3, ease: 4.2, value: 4.4 },
    "海云台海水浴场":     { play: 4.6, view: 4.7, ease: 4.7, value: 4.2 },
    "广安里海水浴场":     { play: 4.5, view: 4.6, ease: 4.7, value: 4.4 },
    "太宗台":             { play: 4.6, view: 4.7, ease: 3.4, value: 4.3 },
    "札嘎其市场":         { play: 4.4, view: 3.8, ease: 4.2, value: 4.0 },
    "南浦洞BIFF广场":     { play: 4.3, view: 3.9, ease: 4.8, value: 4.5 },
    "松岛海水浴场":       { play: 4.3, view: 4.5, ease: 4.3, value: 4.4 },
    "白浅滩文化村":       { play: 4.4, view: 4.6, ease: 3.3, value: 4.3 },
    "龙头山公园":         { play: 4.1, view: 4.4, ease: 4.3, value: 4.4 },
    "海东龙宫寺":         { play: 4.5, view: 4.6, ease: 3.4, value: 4.2 },
    "西面":               { play: 4.2, view: 3.6, ease: 4.9, value: 4.3 }
  };

  /* 权重：玩法 35 / 景观 30 / 便利 20 / 性价比 15 */
  function score(r) {
    if (!r) return 0;
    return Math.round((r.play * 0.35 + r.view * 0.30 + r.ease * 0.20 + r.value * 0.15) * 10) / 10;
  }

  function of(id) {
    var r = BASE[id];
    if (!r) return null;
    return { play: r.play, view: r.view, ease: r.ease, value: r.value, score: score(r) };
  }

  function starsText(n) {
    var full = Math.max(0, Math.min(5, Math.floor(Number(n) || 0)));
    return "★★★★★".slice(0, full) + "☆☆☆☆☆".slice(0, 5 - full);
  }

  function starsHtml(n, cls) {
    n = Math.max(0, Math.min(5, Number(n) || 0));
    var pct = Math.round(n / 5 * 1000) / 10;
    return '<span class="stars' + (cls ? " " + cls : "") + '" role="img" aria-label="' + n.toFixed(1) + ' / 5">' +
      '<span class="sbg">★★★★★</span>' +
      '<span class="sfg" style="width:' + pct + '%">★★★★★</span></span>';
  }

  function grade(n) {
    if (n == null) return "";
    if (n >= 4.6) return P("强烈推荐", "강력 추천", "Highly recommended");
    if (n >= 4.2) return P("值得一去", "추천", "Worth a visit");
    if (n >= 3.6) return P("可以一看", "볼 만함", "Decent");
    if (n >= 3.0) return P("看时间安排", "시간 되면", "If time allows");
    return P("可以跳过", "생략 가능", "Can skip");
  }

  function summary(id) {
    var r = of(id);
    if (!r) return "";
    return P("玩法 ", "플레이 ", "Things to do ") + r.play.toFixed(1) +
      " · " + P("景观 ", "경관 ", "Scenery ") + r.view.toFixed(1) +
      " · " + P("便利 ", "편의 ", "Ease ") + r.ease.toFixed(1) +
      " · " + P("性价比 ", "가성비 ", "Value ") + r.value.toFixed(1);
  }

  function catLabel(cat) {
    if (global.BusanCloud && typeof global.BusanCloud.catLabel === "function") return global.BusanCloud.catLabel(cat);
    return String(cat || "").replace(/^\d+[_\s.、-]*/, "");
  }

  function catAvg(cat) {
    var spots = listSpots().filter(function (s) { return s.category === cat; });
    if (!spots.length) return null;
    var sum = 0;
    spots.forEach(function (s) { sum += (of(s.id) || {}).score || 0; });
    return Math.round(sum / spots.length * 10) / 10;
  }

  function listSpots() {
    if (global.BusanCloud && typeof global.BusanCloud.allSpots === "function") {
      var a = global.BusanCloud.allSpots();
      if (a && a.length) return a;
    }
    if (global.BUSAN_DATA && global.BUSAN_DATA.spots) return global.BUSAN_DATA.spots;
    return [];
  }

  function categorySummary() {
    var spots = listSpots();
    var seen = {};
    var rows = [];
    spots.forEach(function (s) {
      var c = s.category;
      if (!c || seen[c]) return;
      seen[c] = 1;
      var avg = catAvg(c);
      if (avg == null) return;
      rows.push({ category: c, label: catLabel(c), stars: avg });
    });
    rows.sort(function (a, b) { return b.stars - a.stars; });
    return rows;
  }

  /* ---- 用户自评（1-5 星，仅本机） ---- */
  function userAll() {
    try {
      var raw = global.localStorage && global.localStorage.getItem(STORE);
      var j = raw ? JSON.parse(raw) : {};
      return (j && typeof j === "object") ? j : {};
    } catch (e) { return {}; }
  }
  function userOf(id) {
    var v = userAll()[id];
    return (v >= 1 && v <= 5) ? Number(v) : 0;
  }
  function setUser(id, n) {
    n = Math.round(Number(n) || 0);
    if (n < 1 || n > 5) n = 0;
    var all = userAll();
    if (n) all[id] = n; else delete all[id];
    try { if (global.localStorage) global.localStorage.setItem(STORE, JSON.stringify(all)); } catch (e) {}
    return n;
  }

  global.BusanRating = {
    setLang: setLang,
    of: of,
    score: score,
    starsText: starsText,
    starsHtml: starsHtml,
    grade: grade,
    summary: summary,
    catAvg: catAvg,
    categorySummary: categorySummary,
    userOf: userOf,
    setUser: setUser,
    base: BASE
  };
})(typeof window !== "undefined" ? window : this);
