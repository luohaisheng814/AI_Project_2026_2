/* v2.5 天气模块
 * 数据源：Open-Meteo（免 API Key，按经纬度取实况 + 未来 24 小时）
 * 原则：只在成功解析到接口返回时才展示实况数字；无网络 / 无权限时明确降级，
 *       允许用户手动指定天气做推荐，绝不编造实时温度。
 */
(function (global) {
  var LANG = "zh";
  var W = null;              // 最近一次归一化后的天气
  var PREV_KEY = "busan_wx_prev";
  var BUSAN = { lat: 35.1796, lng: 129.0756, label: "Busan" };

  function setLang(l) { if (/^(zh|ko|en)$/.test(l || "")) LANG = l; }
  function P(zh, ko, en) { return LANG === "zh" ? zh : LANG === "ko" ? ko : en; }

  var LABEL = {
    clear:   { icon: "☀️", zh: "晴",   ko: "맑음",     en: "Clear" },
    cloudy:  { icon: "⛅", zh: "多云", ko: "구름 조금", en: "Partly cloudy" },
    drizzle: { icon: "🌦", zh: "小雨", ko: "약한 비",   en: "Drizzle" },
    rain:    { icon: "🌧", zh: "雨",   ko: "비",       en: "Rain" },
    snow:    { icon: "🌨", zh: "雪",   ko: "눈",       en: "Snow" },
    fog:     { icon: "🌫", zh: "雾",   ko: "안개",     en: "Fog" },
    storm:   { icon: "⛈", zh: "雷雨", ko: "뇌우",     en: "Thunderstorm" },
    unknown: { icon: "🌡", zh: "未知", ko: "알 수 없음", en: "Unknown" }
  };

  function classOf(code) {
    if (code == null || isNaN(code)) return "unknown";
    code = Number(code);
    if (code === 0) return "clear";
    if (code >= 1 && code <= 3) return "cloudy";
    if (code === 45 || code === 48) return "fog";
    if (code >= 51 && code <= 57) return "drizzle";
    if (code >= 61 && code <= 67) return "rain";
    if (code >= 71 && code <= 77) return "snow";
    if (code >= 80 && code <= 82) return "rain";
    if (code >= 85 && code <= 86) return "snow";
    if (code >= 95) return "storm";
    return "cloudy";
  }

  function label(cls) { return LABEL[cls] || LABEL.unknown; }
  function clsName(cls) { var l = label(cls); return LANG === "zh" ? l.zh : LANG === "ko" ? l.ko : l.en; }

  /* 景点天气画像：env 0=户外 1=半室内 2=室内；coast 海边；view 依赖能见度；
     stairs 台阶强度 0-2；shade 遮阴 0-2；rain 躲雨能力 0-1 */
  var TRAITS = {
    "甘川文化村":         { env: 0, coast: 0, view: 1, stairs: 2, shade: 1, rain: 0.15 },
    "多大浦梦之夕阳喷泉": { env: 0, coast: 1, view: 1, stairs: 0, shade: 0, rain: 0.05 },
    "多大浦海水浴场":     { env: 0, coast: 1, view: 1, stairs: 0, shade: 0, rain: 0.05 },
    "没云台":             { env: 0, coast: 1, view: 1, stairs: 1, shade: 1, rain: 0.25 },
    "乙淑岛候鸟公园":     { env: 0, coast: 0, view: 1, stairs: 0, shade: 1, rain: 0.35 },
    "峨嵋山观景台":       { env: 0, coast: 0, view: 1, stairs: 2, shade: 1, rain: 0.25 },
    "洛东江河口生态中心": { env: 2, coast: 0, view: 1, stairs: 0, shade: 2, rain: 1 },
    "长林浦口":           { env: 0, coast: 1, view: 1, stairs: 0, shade: 1, rain: 0.25 },
    "海云台海水浴场":     { env: 0, coast: 1, view: 1, stairs: 0, shade: 0, rain: 0.05 },
    "广安里海水浴场":     { env: 0, coast: 1, view: 1, stairs: 0, shade: 0, rain: 0.05 },
    "太宗台":             { env: 0, coast: 1, view: 1, stairs: 2, shade: 2, rain: 0.25 },
    "札嘎其市场":         { env: 1, coast: 1, view: 0, stairs: 0, shade: 1, rain: 0.8 },
    "南浦洞BIFF广场":     { env: 1, coast: 0, view: 0, stairs: 0, shade: 0, rain: 0.6 },
    "松岛海水浴场":       { env: 0, coast: 1, view: 1, stairs: 0, shade: 0, rain: 0.15 },
    "白浅滩文化村":       { env: 0, coast: 1, view: 1, stairs: 2, shade: 1, rain: 0.15 },
    "龙头山公园":         { env: 0, coast: 0, view: 1, stairs: 1, shade: 1, rain: 0.35 },
    "海东龙宫寺":         { env: 0, coast: 1, view: 1, stairs: 2, shade: 1, rain: 0.15 },
    "西面":               { env: 2, coast: 0, view: 0, stairs: 0, shade: 2, rain: 0.95 }
  };

  function isRainy(cls) { return cls === "rain" || cls === "drizzle" || cls === "heavy" || cls === "storm"; }

  /** 单景点天气适配分（0-100），只用于排序与解释，不当作官方评分。 */
  function fitOf(id, w) {
    var t = TRAITS[id];
    if (!t) return 60;
    if (!w) return 62;
    var s = 62, cls = w.cls || "cloudy", temp = Number(w.temp), wind = Number(w.wind), pp = Number(w.precipProb);

    if (cls === "clear") {
      if (t.env === 0) s += 10;
      if (t.coast) s += 7;
      if (t.view) s += 5;
      if (t.shade === 0 && temp >= 27) s -= 6;
    } else if (cls === "cloudy") {
      if (t.env === 0) s += 4;
      if (t.view) s += 3;
    } else if (isRainy(cls)) {
      s += (t.env === 2 ? 22 : t.env === 1 ? 9 : -14);
      s += t.rain * 12;
      if (t.coast) s -= 9;
      s -= t.stairs * 3;
      if (cls === "storm" || cls === "heavy") {
        s += (t.env === 2 ? 6 : -8);
        if (t.coast) s -= 10;
      }
    } else if (cls === "snow") {
      s += (t.env === 2 ? 16 : t.env === 1 ? 4 : -10);
      s -= t.stairs * 6;
      if (t.coast) s -= 9;
    } else if (cls === "fog") {
      if (t.env === 2) s += 14;
      if (t.view) s -= 16;
      if (t.coast) s -= 5;
    }

    if (temp >= 30) {
      if (t.coast) s += 10;
      if (t.shade >= 1) s += 6;
      if (t.shade === 2) s += 3;
      if (t.stairs === 2) s -= 7;
      if (t.env === 2) s += 6;
    }
    if (temp <= 2) {
      if (t.env === 2) s += 12;
      if (t.coast) s -= 12;
      if (t.env === 0) s -= 6;
      if (t.stairs === 2) s -= 4;
    }
    if (wind >= 9) {
      if (t.coast) s -= 15;
      if (t.view) s -= 6;
      if (t.env === 2) s += 8;
    }
    if (pp >= 60) {
      if (t.env === 0) s -= 8;
      if (t.rain >= 0.75) s += 6;
    }
    return Math.max(5, Math.min(100, Math.round(s)));
  }

  function why(id, w) {
    var t = TRAITS[id];
    if (!t || !w) return P("常规推荐", "일반 추천", "General pick");
    var cls = w.cls || "cloudy", temp = Number(w.temp), wind = Number(w.wind);
    if (isRainy(cls)) {
      if (t.env === 2) return P("室内为主，下雨也能逛", "실내 위주라 비 와도 관람 가능", "Mostly indoor — fine in rain");
      if (t.env === 1) return P("有店铺和屋檐可躲雨", "가게·처마로 비를 피할 수 있음", "Shops and awnings to shelter from rain");
      return P("户外为主，雨天体验打折", "야외 위주라 비 오면 아쉬움", "Mostly outdoor — rain hurts the visit");
    }
    if (cls === "snow") {
      if (t.env === 2) return P("室内避寒，雪天更稳", "실내라 눈에도 안정적", "Indoor — steady on snowy days");
      if (t.stairs === 2) return P("台阶多，雪天湿滑要小心", "계단이 많아 눈길에 미끄럼 주의", "Many steps — slippery in snow");
      return P("雪景好看但要注意保暖", "설경은 좋지만 방한 필요", "Snow looks great — dress warm");
    }
    if (cls === "fog") {
      if (t.view) return P("雾天能见度低，观景会打折", "안개로 전망이 아쉬움", "Fog cuts the view");
      return P("雾天影响不大", "안개 영향 적음", "Fog matters little");
    }
    if (temp >= 30) {
      if (t.coast) return P("海边有风，比市区凉快", "바닷바람으로 시내보다 시원함", "Sea breeze — cooler than downtown");
      if (t.shade === 2) return P("树荫多，正午也能待", "그늘이 많아 한낮에도 가능", "Plenty of shade even at noon");
      if (t.stairs === 2) return P("爬坡台阶多，高温时累", "오르막·계단이 많아 더움에 부담", "Steep steps — tiring in heat");
    }
    if (temp <= 2) {
      if (t.env === 2) return P("室内暖和，适合避寒", "실내라 따뜻함", "Indoor and warm");
      if (t.coast) return P("海边风大体感更冷", "바닷바람에 더 춥게 느껴짐", "Coastal wind feels colder");
    }
    if (wind >= 9) {
      if (t.coast) return P("海边风大，注意防风", "바다 바람이 강해 방풍 필요", "Strong coastal wind — bring a shell");
      if (t.env === 2) return P("室内不受大风影响", "실내라 강풍 영향 적음", "Indoor — wind hardly matters");
    }
    if (cls === "clear") {
      if (t.coast) return P("晴天海景和日落最好看", "맑은 날 바다·일몰이 가장 좋음", "Best sea view and sunset on a clear day");
      if (t.view) return P("能见度好，观景正好", "시야가 좋아 전망 최적", "Great visibility for views");
      return P("户外舒服，适合慢慢逛", "야외 활동하기 좋음", "Comfortable outdoors");
    }
    if (cls === "cloudy") {
      if (t.view) return P("云层不厚，观景仍可以", "구름이 많지 않아 전망 무난", "Thin cloud — views still fine");
      return P("多云不晒，走路舒服", "구름 많아 걷기 편함", "Cloudy and easy to walk");
    }
    return P("天气影响不大", "날씨 영향 적음", "Weather matters little");
  }

  function spotList() {
    if (global.BusanCloud && typeof global.BusanCloud.allSpots === "function") {
      var a = global.BusanCloud.allSpots();
      if (a && a.length) return a;
    }
    if (global.BUSAN_DATA && global.BUSAN_DATA.spots) return global.BUSAN_DATA.spots;
    return [];
  }

  function titleOf(s, lang) {
    if (!s) return "";
    if (global.BusanCloud && typeof global.BusanCloud.spotTitle === "function") return global.BusanCloud.spotTitle(s);
    lang = lang || LANG;
    return (lang === "zh" ? s.name : lang === "ko" ? (s.name_ko || s.name) : (s.name_en || s.name)) || s.id || "";
  }

  /** 按天气排序的可去景点（默认 3 个）。 */
  function recommend(w, n) {
    w = w || state();
    n = n || 3;
    var spots = spotList();
    var rows = spots.map(function (s) {
      return { id: s.id, name: titleOf(s, LANG), score: fitOf(s.id, w), reason: why(s.id, w), cat: s.category };
    });
    rows.sort(function (a, b) { return b.score - a.score; });
    return rows.slice(0, n);
  }

  function tips(w) {
    if (!w) return [];
    var out = [], cls = w.cls, temp = Number(w.temp), wind = Number(w.wind), pp = Number(w.precipProb);
    if (isRainy(cls)) {
      out.push(P("带伞或轻便雨衣", "우산이나 가벼운 우비", "Bring an umbrella or light raincoat"));
      out.push(P("石板路和台阶湿滑，鞋底要防滑", "돌길·계단이 미끄러우니 접지 좋은 신발", "Stone paths get slick — wear grippy shoes"));
    }
    if (cls === "storm") out.push(P("雷雨时避开海边、观景台和空旷高处", "뇌우 시 해변·전망대·노출된 고지대는 피하세요", "In thunderstorms avoid beaches, observatories and exposed heights"));
    if (cls === "snow") out.push(P("台阶多的文化村容易结冰，慢走", "계단 많은 마을은 결빙 주의", "Villages with many steps ice up — go slow"));
    if (temp >= 30) { out.push(P("防晒 + 补水，正午少爬坡", "자외선 차단·수분 보충, 한낮 오르막 자제", "Sun protection and water; skip climbs at noon")); }
    if (temp <= 2) out.push(P("海边体感更低，加一件防风外套", "바다가는 더 춥게 느껴져 방풍 자켓 필요", "The coast feels colder — add a windproof layer"));
    if (wind >= 9) out.push(P("风速较大，帽子和伞容易被吹翻", "바람이 강해 모자·우산이 뒤집힐 수 있음", "Strong wind — hats and umbrellas may flip"));
    if (pp >= 60 && !isRainy(cls)) out.push(P("降水概率偏高，出发前再看一次雷达", "강수 확률이 높으니 출발 전 레이더 확인", "High rain chance — check the radar before leaving"));
    if (!out.length) out.push(P("天气平稳，按平时节奏走就好", "날씨가 무난하니 평소대로 이동하세요", "Stable weather — keep your usual plan"));
    return out;
  }

  /* ---------- 状态与变化检测 ---------- */
  function sev(cls) {
    return cls === "clear" ? 1 : cls === "cloudy" ? 2 : cls === "fog" ? 3 :
      cls === "drizzle" ? 4 : cls === "rain" ? 5 : cls === "snow" ? 6 : cls === "storm" ? 7 : 3;
  }

  function diff(prev, cur) {
    var out = [];
    if (!prev || !cur) return out;
    if (prev.cls !== cur.cls) out.push({ type: "class", from: prev.cls, to: cur.cls, worse: sev(cur.cls) > sev(prev.cls) });
    if (prev.temp != null && cur.temp != null && Math.abs(cur.temp - prev.temp) >= 5) {
      out.push({ type: "temp", from: prev.temp, to: cur.temp, up: cur.temp > prev.temp });
    }
    if ((Number(prev.precipProb) || 0) < 60 && (Number(cur.precipProb) || 0) >= 60) {
      out.push({ type: "rain", p: cur.precipProb });
    }
    if ((Number(prev.wind) || 0) < 9 && (Number(cur.wind) || 0) >= 9) {
      out.push({ type: "wind", v: cur.wind });
    }
    return out;
  }

  function changeText(changes, w) {
    if (!changes || !changes.length) return "";
    var lines = [];
    lines.push("**" + P("天气有变化", "날씨가 바뀌었습니다", "Weather changed") + "**");
    changes.forEach(function (c) {
      if (c.type === "class") {
        lines.push("- " + label(c.from).icon + " " + clsName(c.from) + " → " + label(c.to).icon + " " + clsName(c.to) +
          (c.worse ? P("，体验会受影响", " · 관람에 영향", " — this affects the visit")
                   : P("，条件变好了", " · 조건이 좋아짐", " — conditions improved")));
      } else if (c.type === "temp") {
        lines.push("- " + P("气温 " + c.from.toFixed(0) + "°C → " + c.to.toFixed(0) + "°C", "기온 " + c.from.toFixed(0) + "°C → " + c.to.toFixed(0) + "°C", "Temperature " + c.from.toFixed(0) + "°C → " + c.to.toFixed(0) + "°C"));
      } else if (c.type === "rain") {
        lines.push("- " + P("降水概率升到 " + Math.round(c.p) + "%", "강수 확률 " + Math.round(c.p) + "%로 상승", "Rain chance up to " + Math.round(c.p) + "%"));
      } else if (c.type === "wind") {
        lines.push("- " + P("风速升到 " + c.v.toFixed(1) + " m/s", "풍속 " + c.v.toFixed(1) + " m/s로 상승", "Wind up to " + c.v.toFixed(1) + " m/s"));
      }
    });
    var rec = recommend(w, 3);
    if (rec.length) {
      lines.push("");
      lines.push("**" + P("现在更适合", "지금 더 적합한 곳", "Better right now") + "**");
      rec.forEach(function (r, i) { lines.push((i + 1) + ". " + r.name + " — " + r.reason); });
    }
    var tp = tips(w);
    lines.push("");
    lines.push("**" + P("提醒", "알림", "Heads-up") + "** · " + tp.slice(0, 2).join(" · "));
    return lines.join("\n");
  }

  function normalize(api) {
    if (!api || !api.current) return null;
    var cur = api.current;
    var code = cur.weather_code;
    var cls = classOf(code);
    var hourly = (api.hourly && api.hourly.time) ? api.hourly : null;
    var pp = 0;
    if (hourly) {
      var now = new Date().getTime();
      var best = 0, bestGap = 1e12;
      for (var i = 0; i < hourly.time.length; i++) {
        var t = new Date(hourly.time[i].replace(" ", "T")).getTime();
        if (isNaN(t)) continue;
        if (t >= now - 3600000) { var gap = Math.abs(t - now); if (gap < bestGap) { bestGap = gap; best = i; } }
      }
      var maxP = 0;
      for (var j = best; j < hourly.time.length && j <= best + 3; j++) {
        var v = Number(hourly.precipitation_probability && hourly.precipitation_probability[j]);
        if (!isNaN(v) && v > maxP) maxP = v;
      }
      pp = maxP;
    }
    var daily = api.daily || {};
    return {
      cls: cls, code: Number(code),
      temp: Number(cur.temperature_2m),
      feels: cur.apparent_temperature != null ? Number(cur.apparent_temperature) : null,
      humidity: cur.relative_humidity_2m != null ? Number(cur.relative_humidity_2m) : null,
      wind: cur.wind_speed_10m != null ? Number(cur.wind_speed_10m) : 0,
      precip: cur.precipitation != null ? Number(cur.precipitation) : 0,
      precipProb: pp,
      max: daily.temperature_2m_max ? Number(daily.temperature_2m_max[0]) : null,
      min: daily.temperature_2m_min ? Number(daily.temperature_2m_min[0]) : null,
      at: Date.now(),
      source: "open-meteo",
      lat: api.latitude, lng: api.longitude,
      timezone: api.timezone || "Asia/Seoul"
    };
  }

  function parse(body) {
    try {
      var j = typeof body === "string" ? JSON.parse(body) : body;
      return normalize(j);
    } catch (e) { return null; }
  }

  function loadPrev() {
    try {
      var raw = global.localStorage && global.localStorage.getItem(PREV_KEY);
      if (!raw) return null;
      var p = JSON.parse(raw);
      if (!p || !p.at || Date.now() - p.at > 6 * 3600 * 1000) return null;   // 超过 6 小时不比较
      return p;
    } catch (e) { return null; }
  }

  function savePrev(w) {
    try { if (global.localStorage) global.localStorage.setItem(PREV_KEY, JSON.stringify(w)); } catch (e) {}
  }

  /** 写入最新天气并返回变化列表；changes 为空表示没有值得打断用户的变化。 */
  function setState(w, opts) {
    if (!w) return [];
    var prev = (opts && opts.prev) || W || loadPrev();
    var changes = diff(prev, w);
    W = w;
    savePrev(w);
    if (global.BusanWeather && typeof global.BusanWeather.onChange === "function") {
      try { global.BusanWeather.onChange(changes, w); } catch (e) {}
    }
    return changes;
  }

  function state() { return W; }
  function clear() { W = null; }

  function manual(cls, temp) {
    var t = temp == null ? (cls === "clear" ? 24 : cls === "snow" ? -1 : cls === "rain" ? 18 : 21) : temp;
    var w = {
      cls: cls, code: cls === "clear" ? 0 : cls === "rain" ? 61 : cls === "snow" ? 71 : cls === "fog" ? 45 : cls === "storm" ? 95 : 2,
      temp: t, feels: t, wind: cls === "storm" ? 14 : cls === "rain" ? 6 : 3,
      precipProb: cls === "rain" || cls === "storm" ? 85 : cls === "snow" ? 70 : 10,
      source: "manual", at: Date.now(), manual: true
    };
    setState(w);
    return w;
  }

  function url(lat, lng) {
    return "https://api.open-meteo.com/v1/forecast?latitude=" + Number(lat).toFixed(4) +
      "&longitude=" + Number(lng).toFixed(4) +
      "&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m" +
      "&hourly=precipitation_probability,temperature_2m,weather_code" +
      "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max" +
      "&timezone=Asia%2FSeoul&forecast_days=2";
  }

  function httpGet(u, cb) {
    if (global.BusanHost && typeof global.BusanHost.fetchText === "function") {
      var id = "wx" + Math.random().toString(36).slice(2);
      global.__busanHttpCbs = global.__busanHttpCbs || {};
      global.__busanHttpCbs[id] = cb;
      try { global.BusanHost.fetchText(u, id); } catch (e) { cb(-1, ""); }
      return;
    }
    if (typeof global.fetch === "function") {
      global.fetch(u, { cache: "no-store" }).then(function (r) {
        return r.text().then(function (b) { cb(r.status, b); });
      }).catch(function () { cb(-1, ""); });
      return;
    }
    cb(-1, "");
  }

  /** 取当前位置（无权限则用釜山市区并标记 fallback），联网拉天气。 */
  function refresh(cb) {
    var pos = (global.BusanLive && typeof global.BusanLive.position === "function") ? global.BusanLive.position() : null;
    var fallback = !pos;
    if (!pos) pos = { lat: BUSAN.lat, lng: BUSAN.lng };
    httpGet(url(pos.lat, pos.lng), function (status, body) {
      if (status !== 200 && status !== 0) { cb && cb("offline", null, []); return; }
      var w = parse(body);
      if (!w) { cb && cb("offline", null, []); return; }
      w.fallback = fallback;
      var changes = setState(w);
      cb && cb(null, w, changes);
    });
  }

  function banner(w) {
    w = w || state();
    if (!w) return P("天气未获取", "날씨 미확인", "Weather not loaded");
    var l = label(w.cls);
    var temp = (w.temp != null && !isNaN(w.temp)) ? Math.round(w.temp) + "°C" : "";
    var pp = w.precipProb ? Math.round(w.precipProb) + "%" : "";
    var bits = [l.icon + " " + clsName(w.cls), temp, pp ? P("降水 " + pp, "강수 " + pp, "rain " + pp) : ""].filter(Boolean);
    if (w.manual) bits.push(P("手动", "수동", "manual"));
    if (w.fallback) bits.push(P("默认位置", "기본 위치", "default spot"));
    return bits.join(" · ");
  }

  global.BusanWeather = {
    setLang: setLang,
    getLang: function () { return LANG; },
    classOf: classOf,
    label: label,
    clsName: clsName,
    fitOf: fitOf,
    why: why,
    recommend: recommend,
    tips: tips,
    diff: diff,
    changeText: changeText,
    parse: parse,
    normalize: normalize,
    setState: setState,
    state: state,
    clear: clear,
    manual: manual,
    refresh: refresh,
    banner: banner,
    url: url,
    traits: TRAITS,
    defaultPos: BUSAN,
    onChange: null
  };
})(typeof window !== "undefined" ? window : this);
