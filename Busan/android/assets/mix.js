/* mix.js —— v2.8 综合推荐：把「当前位置 + 当地天气 + 手机本地时间」揉成一次排序
 *
 * 设计约束（与 v2.5/v2.7 一致，别越界）：
 * 1. 只用本机已有的三类输入：BusanLive 的坐标、BusanWeather 的实时天气、手机本地小时。
 * 2. 排序结果不是官方评分，只是"这个点、这个天，先去哪个"；不推断实时营业/客流。
 * 3. 距离用直线距离，和 live.js 同口径，不编造车程。
 * 纯计算模块：不碰 DOM，便于静态断言与离线复用。
 * 发布重试标记：v2.8.1
 */
(function (global) {
  var LANG = "zh";

  function setLang(l) { if (/^(zh|ko|en)$/.test(l || "")) LANG = l; }
  function P(zh, ko, en) { return LANG === "zh" ? zh : LANG === "ko" ? ko : en; }
  function num(v, d) { var n = Number(v); return isFinite(n) ? n : d; }

  /* ---------- 时间轴 ---------- */
  function hourNow(d) { d = d || new Date(); return d.getHours(); }

  /** 夜间口径与 index.html 的 computeNight 一致：19:00–05:59 算夜。 */
  function nightOf(hour) {
    hour = num(hour, hourNow());
    return hour >= 19 || hour < 6;
  }

  function bandOf(hour) {
    hour = num(hour, hourNow());
    if (hour >= 19 || hour < 4) return "night";   // 与 nightOf 同口径，0–3 点算夜里
    if (hour < 6) return "dawn";
    if (hour < 11) return "morning";
    if (hour < 14) return "noon";
    if (hour < 17) return "afternoon";
    if (hour < 19) return "dusk";
    return "night";
  }

  function bandName(band) {
    return {
      dawn: P("凌晨", "새벽", "early morning"),
      morning: P("上午", "오전", "morning"),
      noon: P("午间", "한낮", "midday"),
      afternoon: P("午后", "오후", "afternoon"),
      dusk: P("傍晚", "저녁", "dusk"),
      night: P("夜间", "밤", "night")
    }[band] || "";
  }

  function hhmm(d) {
    d = d || new Date();
    return ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2);
  }

  /* ---------- 三个分项打分 ---------- */
  /** 距离分：走路能到的权重最高，超过 6 km 开始明显减分。 */
  function distScore(km) {
    if (km == null || !isFinite(km)) return 0;
    if (km <= 0.5) return 22;
    return Math.max(-12, 22 - km * 4.4);
  }

  /** 时间分：用景点自带的 plan.best_time 与 vibes，不猜营业时间。 */
  function timeScore(spot, band) {
    var plan = spot.plan || {}, vibes = spot.vibes || [];
    var best = String(plan.best_time || "").toLowerCase();
    var indoor = !!num(plan.indoor, 0);
    var has = function (v) { return vibes.indexOf(v) >= 0; };
    var s = 0;
    if (band === "night") {
      if (best === "evening") s += 10;
      if (has("night")) s += 8;
      if (indoor) s += 9;
      if (!indoor && (has("coast") || has("nature") || has("walk"))) s -= 8;
      if (best === "morning") s -= 4;
    } else if (band === "dusk") {
      if (best === "sunset") s += 12;
      else if (best === "evening") s += 9;
      if (has("sunset")) s += 6;
      if (has("photo")) s += 3;
    } else if (band === "afternoon") {
      if (best === "afternoon") s += 10;
      if (best === "sunset") s += 6;
      if (has("photo")) s += 3;
    } else if (band === "morning") {
      if (best === "morning") s += 11;
      if (has("photo")) s += 4;
      if (has("night")) s -= 7;
      if (has("market") || has("food")) s -= 4;
    } else if (band === "noon") {
      if (indoor) s += 7;
      if (has("market") || has("food")) s += 5;
      if (has("coast")) s -= 3;
      if (best === "sunset" || best === "evening") s -= 5;
    } else {
      if (best === "morning") s += 6;
      if (has("photo")) s += 2;
    }
    return s;
  }

  /** 天气分：直接复用 weather.js 的 fitOf（0–100），再压到 ±26 的区间。 */
  function weatherScore(spot, w) {
    if (!w) return 0;
    var WX = global.BusanWeather;
    if (!WX || typeof WX.fitOf !== "function") return 0;
    var fit = num(WX.fitOf(spot.id, w), 62);
    return Math.max(-26, Math.min(28, (fit - 62) * 0.8));
  }

  /** 大家打过的分也是输入之一，权重刻意压低，不让它盖过时间/天气。 */
  function rateScore(spot) {
    var RT = global.BusanRating;
    if (!RT || typeof RT.of !== "function") return 0;
    var r = null;
    try { r = RT.of(spot.id); } catch (e) { r = null; }
    if (!r || r.score == null) return 0;
    return Math.max(-4, Math.min(5, (num(r.score, 3) - 3) * 2));
  }

  /* ---------- 理由（一句话一条，最多三条） ---------- */
  function kmText(km) {
    if (km == null || !isFinite(km)) return "";
    return P("距你 " + km.toFixed(1) + " km", "여기서 " + km.toFixed(1) + " km", km.toFixed(1) + " km away");
  }

  function timeWhy(spot, band) {
    var plan = spot.plan || {}, best = String(plan.best_time || "").toLowerCase();
    var indoor = !!num(plan.indoor, 0);
    var map = { morning: P("上午", "오전", "morning"), afternoon: P("午后", "오후", "afternoon"),
      sunset: P("日落时分", "일몰 무렵", "sunset"), evening: P("傍晚以后", "저녁 이후", "evening") };
    if (best && map[best]) {
      if (band === "night" && best === "evening") return P("资料里标的最佳时段正是晚间", "자료상 최적 시간대가 저녁", "its listed best time is evening");
      if (band === "dusk" && best === "sunset") return P("资料里标的最佳时段正是日落", "자료상 최적 시간대가 일몰", "its listed best time is sunset");
      if (band === "afternoon" && best === "afternoon") return P("资料里标的最佳时段正是午后", "자료상 최적 시간대가 오후", "its listed best time is afternoon");
      if (band === "morning" && best === "morning") return P("资料里标的最佳时段正是上午", "자료상 최적 시간대가 오전", "its listed best time is morning");
    }
    if (band === "night" && indoor) return P("室内为主，天黑后不受影响", "실내 위주라 어두워져도 무관", "mostly indoor, unaffected after dark");
    if (band === "night") return P("夜间主要靠灯光和夜景", "밤에는 조명·야경 위주", "night means lights and night views");
    if (band === "dusk") return P("天色渐暗，正好赶日落前后", "해 질 무렵과 겹침", "lines up with the sunset window");
    if (band === "noon" && indoor) return P("午间室内，避开最晒的时段", "한낮 실내라 햇빛을 피함", "indoor at midday, out of the sun");
    return "";
  }

  function whyClauses(spot, ctx) {
    var out = [];
    var km = ctx.kmOf ? ctx.kmOf(spot) : null;
    if (km != null && isFinite(km)) out.push(kmText(km));
    var WX = global.BusanWeather;
    if (ctx.w && WX && typeof WX.why === "function") {
      var ww = WX.why(spot.id, ctx.w);
      if (ww) out.push(ww);
    }
    var tw = timeWhy(spot, ctx.band);
    if (tw) out.push(tw);
    return out.slice(0, 3);
  }

  /* ---------- 主排序 ---------- */
  function spots() {
    var C = global.BusanCloud;
    if (C && typeof C.allSpots === "function") {
      var a = C.allSpots();
      if (a && a.length) return a;
    }
    if (global.BUSAN_DATA && global.BUSAN_DATA.spots) return global.BUSAN_DATA.spots;
    return [];
  }

  function titleOf(s) {
    var C = global.BusanCloud;
    if (C && typeof C.spotTitle === "function") return C.spotTitle(s);
    return s.name || s.id;
  }

  function haversine(a, b, c, d) {
    var C = global.BusanCloud;
    if (C && typeof C.haversine === "function") return C.haversine(a, b, c, d);
    var R = 6371, rad = Math.PI / 180;
    var dLat = (c - a) * rad, dLng = (d - b) * rad;
    var x = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(a * rad) * Math.cos(c * rad) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return 2 * R * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
  }

  function ctxOf(opts) {
    opts = opts || {};
    var hour = opts.hour != null ? num(opts.hour, hourNow()) : hourNow();
    return {
      pos: opts.pos || null,
      w: opts.w || null,
      hour: hour,
      band: bandOf(hour),
      night: nightOf(hour),
      at: opts.at || null
    };
  }

  function ranked(ctx, n) {
    ctx = ctx && ctx.band ? ctx : ctxOf(ctx);
    var hasPos = !!(ctx.pos && isFinite(ctx.pos.lat) && isFinite(ctx.pos.lng));
    var rows = spots().map(function (s) {
      var km = (hasPos && s.lat != null && s.lng != null)
        ? haversine(ctx.pos.lat, ctx.pos.lng, s.lat, s.lng) : null;
      var score = distScore(km) + weatherScore(s, ctx.w) + timeScore(s, ctx.band) + rateScore(s);
      return { id: s.id, spot: s, name: titleOf(s), km: km, score: Math.round(score) };
    });
    rows.sort(function (a, b) { return b.score - a.score; });
    var out = [];
    for (var i = 0; i < rows.length; i++) {
      if (out.length >= (n || 3)) break;
      out.push(rows[i]);
    }
    out.forEach(function (r) {
      r.reasons = whyClauses(r.spot, {
        w: ctx.w, band: ctx.band,
        kmOf: function () { return r.km; }
      });
    });
    return out;
  }

  /** 顶部一行上下文：几点、哪一段、什么天气。 */
  function contextLine(ctx) {
    ctx = ctx && ctx.band ? ctx : ctxOf(ctx);
    var parts = [hhmm(ctx.at || new Date()), bandName(ctx.band)];
    if (ctx.w) {
      var WX = global.BusanWeather;
      var icon = WX && WX.label ? (WX.label(ctx.w.cls) || {}).icon || "" : "";
      var name = WX && WX.clsName ? WX.clsName(ctx.w.cls) : "";
      var temp = ctx.w.temp != null ? Math.round(ctx.w.temp) + "°C" : "";
      parts.push((icon + " " + name + " " + temp).trim());
      if (ctx.w.manual) parts.push(P("手动天气", "수동 날씨", "manual"));
    } else {
      parts.push(P("天气未取到", "날씨 미확인", "weather unknown"));
    }
    return parts.join(" · ");
  }

  /** 一句总体建议：只根据时间+天气给方向，不点名具体景点。 */
  function advice(ctx) {
    ctx = ctx && ctx.band ? ctx : ctxOf(ctx);
    var w = ctx.w, cls = w ? w.cls : "", temp = w ? num(w.temp, 20) : null;
    var rainy = /^(rain|drizzle|storm|heavy)$/.test(cls);
    var snowy = cls === "snow", foggy = cls === "fog";
    if (ctx.night) {
      if (rainy) return P("夜里又在下雨，就近找室内或带屋檐的一条街，别跑远。", "밤에 비까지 오니 가까운 실내·처마 있는 거리로 한정하세요.", "Rain at night — keep it close, indoor or covered streets.");
      if (snowy) return P("夜里下雪，路滑，只建议走走路就能到的地方。", "밤에 눈이라 길이 미끄럽습니다. 걸어서 닿는 곳만 권합니다.", "Snow at night — only walkable distances.");
      if (foggy) return P("夜雾能见度低，夜景观景台先放一放。", "밤 안개로 시야가 나빠 전망대는 미루세요.", "Night fog — skip the lookouts.");
      return P("天黑了，优先灯光和夜市一带，近的先走。", "어두워졌으니 조명·야시장 쪽을 가까운 순서로.", "Dark now — go for lit streets and markets, nearest first.");
    }
    if (rainy) return P("白天下雨，室内和能躲雨的地方优先。", "낮에 비가 오니 실내·비 피할 곳 우선.", "Rainy daytime — indoor and covered first.");
    if (temp != null && temp >= 30) return P("高温，海边或有树荫的排在前面，正午少爬坡。", "폭염이니 해변·그늘 위주, 한낮 오르막은 자제.", "Hot — coast or shade first, skip climbs at midday.");
    if (snowy) return P("下雪天，台阶多的文化村放慢节奏。", "눈이라 계단 많은 마을은 천천히.", "Snow — go slow on stepped villages.");
    if (ctx.band === "dusk") return P("快到日落，能看海的一侧更值。", "해 질 무렵이라 바다 쪽이 좋습니다.", "Near sunset — the sea side wins.");
    if (cls === "clear") return P("天气好，海景和观景台可以排前面。", "날씨 좋으니 바다·전망대를 앞에.", "Clear — sea views and lookouts first.");
    return P("天气平稳，按距离就近安排最省力。", "무난한 날씨, 가까운 곳부터가 효율적.", "Steady weather — nearest first.");
  }

  global.BusanMix = {
    setLang: setLang,
    hourNow: hourNow,
    hhmm: hhmm,
    nightOf: nightOf,
    bandOf: bandOf,
    bandName: bandName,
    distScore: distScore,
    timeScore: timeScore,
    weatherScore: weatherScore,
    rateScore: rateScore,
    ctxOf: ctxOf,
    ranked: ranked,
    contextLine: contextLine,
    advice: advice,
    timeWhy: timeWhy
  };
})(window);
