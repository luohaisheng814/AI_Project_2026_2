/* planner.js —— 核心词识别、约束提取与行程推演
 *
 * 三层结构：
 *   1) 从一句话里抽核心词 / 时间 / 节奏 / 预算 / 同行 / 兴趣；
 *   2) 用云端库的 core / vibes / plan 元数据打分、按距离排序、按时间预算裁行程；
 *   3) 配了大模型时，把「候选点 + 已知事实 + 约束」交给模型重排，只允许它使用候选点；
 *      模型失败或没配置时，完整退回本地规则，不编造距离、票价和营业状态。
 */
(function () {
  var C = window.BusanCloud;

  function lang() { return (window.BusanUI && BusanUI.getLang()) || "zh"; }
  function P(zh, ko, en) { return lang() === "zh" ? zh : lang() === "ko" ? ko : en; }
  function norm(s) {
    return String(s == null ? "" : s).toLowerCase()
      .replace(/[\s\u3000·,，。.!?！？、/\\()（）【】\[\]<>《》"'“”‘’\-_+~:：;；]+/g, "");
  }
  function tidy(s) { return String(s == null ? "" : s).replace(/\r/g, "").trim(); }
  function firstLine(s) {
    return tidy(s).split("\n").map(tidy).filter(function (x) { return x; })[0] || "";
  }
  function field(s, name) { return C.field ? C.field(s, name) : ""; }
  function label(s) { return C.spotTitle(s); }
  function allSpots() { return (C.allSpots && C.allSpots()) || []; }
  function meta(s) {
    return s.plan || { duration_min: 60, duration_max: 90, best_time: "any", walk_level: 2, photo_score: 3, family_score: 3, indoor: 0, note: "" };
  }

  var TIMES = {
    "一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    "十一": 11, "十二": 12, "半": 0.5
  };

  function numText(s) {
    if (!s) return null;
    if (/^\d/.test(s)) return parseFloat(s);
    if (TIMES[s] != null) return TIMES[s];
    if (s.length === 2 && s[0] === "十" && TIMES[s[1]]) return 10 + TIMES[s[1]];
    return null;
  }

  function timeInfo(text) {
    var t = String(text || "");
    var out = { minutes: 0, start: null, label: "", evening: false, morning: false };
    if (/半天|반나절|half\s*day/i.test(t)) { out.minutes = 240; out.label = P("半天", "반나절", "half day"); }
    else if (/一天|一日|全天|하루|full\s*day|one\s*day/i.test(t)) { out.minutes = 480; out.label = P("一天", "하루", "full day"); }
    else {
      var m = t.match(/([0-9]+(?:\.[0-9]+)?|[一二两三四五六七八九十半]+)\s*(?:个)?\s*(?:小时|시간|hours?|hrs?)/i);
      if (m) {
        var n = numText(m[1]);
        if (n) { out.minutes = Math.round(n * 60); out.label = n + P(" 小时", "시간", " h"); }
      }
    }
    if (/上午|早上|清晨|아침|morning/i.test(t)) { out.start = 9 * 60; out.morning = true; }
    if (/中午|점심|noon/i.test(t)) out.start = 12 * 60;
    if (/下午|오후|afternoon/i.test(t)) out.start = 13.5 * 60;
    if (/傍晚|日落|夕阳|일몰|노을|sunset/i.test(t)) { out.start = 16.5 * 60; out.evening = true; }
    if (/晚上|夜景|夜间|야경|밤|night/i.test(t)) { out.start = 18 * 60; out.evening = true; }
    return out;
  }

  function paceOf(text, prof) {
    var t = String(text || "");
    if (/轻松|慢慢|慢逛|不赶|悠闲|少走|편한|천천히|relaxed|easy|slow/i.test(t)) return "relaxed";
    if (/紧凑|多逛|赶时间|多去|빠르게|packed|busy/i.test(t)) return "packed";
    return (prof && prof.pace) || "balanced";
  }

  function mobilityOf(text, prof) {
    var t = String(text || "");
    if (/轮椅|wheelchair|휠체어/i.test(t)) return "wheelchair";
    if (/婴儿车|유모차|stroller/i.test(t)) return "stroller";
    if (/少走路|腿脚|老人|长辈|걷기|어르신|less\s*walk/i.test(t)) return "lesswalk";
    return (prof && prof.mobility) || "normal";
  }

  function budgetOf(text, prof) {
    var t = String(text || "");
    if (/免费|不花钱|무료|free/i.test(t)) return "free";
    if (/省钱|便宜|预算紧|저렴|cheap|low\s*budget/i.test(t)) return "low";
    return (prof && prof.budget) || "medium";
  }

  function partyOf(text, opts, prof) {
    if (opts && opts.party) {
      if (/solo_/.test(opts.party)) return "solo";
      if (/two_/.test(opts.party)) return "two";
      if (/group_/.test(opts.party)) return "group";
    }
    var t = String(text || "");
    if (/孩子|亲子|아이|kids|child/i.test(t)) return "kids";
    if (/老人|父母|长辈|어르신|elder/i.test(t)) return "family";
    if (/情侣|两人|2人|두\s*명|couple/i.test(t)) return "two";
    if (/朋友|친구|friends/i.test(t)) return "friends";
    if (/一人|独自|혼자|solo/i.test(t)) return "solo";
    return (prof && prof.mobility === "stroller") ? "kids" : "solo";
  }

  function interestsOf(text, prof) {
    var lex = (C.lexicon ? C.lexicon() : {}) || {};
    var map = lex.interest_map || {};
    var out = [], seen = {};
    var t = String(text || "");
    Object.keys(map).forEach(function (zhKey) {
      var words = [zhKey].concat(map[zhKey] || []);
      for (var i = 0; i < words.length; i++) {
        var w = String(words[i] || "");
        if (!w) continue;
        if (norm(t).indexOf(norm(w)) >= 0) {
          // 用该兴趣的首个规范标签（photo / sunset / wetland…），避免“拍照”把艺术、渔港全拉进来
          var tags = map[zhKey] || [];
          var tag = norm(tags.length ? tags[0] : zhKey);
          if (tag && !seen[tag]) { seen[tag] = 1; out.push(tag); }
          break;
        }
      }
    });
    (prof && prof.interests || []).forEach(function (x) {
      var tag = norm(x);
      if (tag && !seen[tag]) { seen[tag] = 1; out.push(tag); }
    });
    return out;
  }

  function coreWordsOf(text) {
    var t = String(text || ""), found = [], seen = {};
    var list = allSpots();
    var lex = (C.lexicon ? C.lexicon() : {}) || {};
    var push = function (w) {
      var k = norm(w);
      if (!k || seen[k]) return;
      if (t.indexOf(k) >= 0 || norm(t).indexOf(k) >= 0) { seen[k] = 1; found.push(w); }
    };
    list.forEach(function (s) {
      (s.core || []).forEach(function (w) {
        var k = norm(w);
        if (k && (t.indexOf(w) >= 0 || norm(t).indexOf(k) >= 0)) push(w);
      });
    });
    var cons = lex.constraints || {};
    Object.keys(cons).forEach(function (kind) {
      (cons[kind] || []).forEach(function (w) {
        var k = norm(w);
        if (k && (t.indexOf(w) >= 0 || norm(t).indexOf(k) >= 0)) push(w);
      });
    });
    return found.slice(0, 8);
  }

  function themeOf(opts, text, matched) {
    if (opts && opts.theme) return opts.theme;
    var lex = (C.lexicon ? C.lexicon() : {}) || {};
    var themes = lex.themes || {};
    var t = String(text || "");
    var best = "", bestN = 0;
    Object.keys(themes).forEach(function (k) {
      var keys = (themes[k] && themes[k].keywords) || [];
      var n = 0;
      keys.forEach(function (w) {
        if (w && t.indexOf(w) >= 0) n++;
      });
      if (n > bestN) { bestN = n; best = k; }
    });
    if (best && bestN >= 2) return best;
    if (matched && matched.length) return matched[0].spot.category;
    return "";
  }

  function distanceFrom(origin, s) {
    if (!origin || s.lat == null || s.lng == null) return null;
    return C.haversine(origin.lat, origin.lng, s.lat, s.lng);
  }

  function scoreSpot(s, ctx) {
    var m = meta(s), vibe = s.vibes || [];
    var score = 40;
    if (ctx.theme && s.category === ctx.theme) score += 55;
    if (ctx.interests && ctx.interests.length) {
      ctx.interests.forEach(function (tag) {
        if (vibe.indexOf(tag) >= 0) score += 14;
      });
    }
    var hit = 0;
    (ctx.matched || []).forEach(function (r) {
      if (r.spot.id === s.id) {
        hit = 1;
        score += r.direct ? 36 : 10;
        score += Math.min(30, (r.hits || []).length * 8);
      }
    });
    if (ctx.pace === "relaxed") score -= (m.walk_level || 2) * 8;
    if (ctx.pace === "packed") score += (m.photo_score || 3) * 2;
    if (ctx.mobility === "lesswalk" || ctx.mobility === "stroller") {
      score -= (m.walk_level || 2) * 10;
      if ((m.walk_level || 2) <= 2) score += 14;
    }
    if (ctx.mobility === "wheelchair") {
      score -= (m.walk_level || 2) * 16;
      if ((m.walk_level || 2) >= 4) score -= 40;
    }
    if (ctx.party === "kids") score += (m.family_score || 3) * 7;
    if (ctx.budget === "free") {
      if (vibe.indexOf("free") >= 0 || /免费|무료|free/i.test(field(s, "ticket"))) score += 24;
      else if (/[₩원]|收费|paid/i.test(field(s, "ticket"))) score -= 12;
    }
    if (ctx.evening && (m.best_time === "sunset" || m.best_time === "evening")) score += 24;
    if (ctx.morning && m.best_time === "morning") score += 18;
    if (ctx.origin) {
      var km = distanceFrom(ctx.origin, s);
      if (km != null) score -= Math.min(30, km * 2.2);
    }
    if (!hit && ctx.onlyMatched) score -= 80;
    return score;
  }

  function preferredDuration(s, pace) {
    var m = meta(s);
    var lo = m.duration_min || 60, hi = m.duration_max || lo + 30;
    if (pace === "relaxed") return Math.round((3 * lo + hi) / 4);
    if (pace === "packed") return Math.round(lo);
    return Math.round((lo + hi) / 2);
  }

  function travelMinutes(a, b) {
    if (!a || !b || a.lat == null || b.lat == null) return 12;
    var km = C.haversine(a.lat, a.lng, b.lat, b.lng);
    return Math.min(32, Math.round(km * 3.2 + 6));
  }

  function orderRoute(list, origin) {
    var out = [], pool = list.slice();
    var cur = null;
    if (origin) {
      var best = 0, bestD = Infinity;
      for (var i = 0; i < pool.length; i++) {
        var d = distanceFrom(origin, pool[i]);
        if (d != null && d < bestD) { bestD = d; best = i; }
      }
      cur = pool[best];
      out.push(cur);
      pool.splice(best, 1);
    }
    while (pool.length) {
      if (!cur) { cur = pool.shift(); out.push(cur); continue; }
      var bi = 0, bd = Infinity;
      for (var j = 0; j < pool.length; j++) {
        var k = distanceFrom(cur, pool[j]);
        if (k != null && k < bd) { bd = k; bi = j; }
      }
      cur = pool[bi];
      out.push(cur);
      pool.splice(bi, 1);
    }
    return out;
  }

  function pickSpots(ctx) {
    var budget = ctx.minutes || 240;
    var scored = allSpots().map(function (s) {
      return { spot: s, score: scoreSpot(s, ctx) };
    }).sort(function (a, b) { return b.score - a.score; });

    var maxCount = budget <= 100 ? 1 : budget <= 180 ? 2 : budget <= 300 ? 3 : 4;
    var chosen = [], total = 0, last = ctx.origin;
    for (var i = 0; i < scored.length && chosen.length < maxCount; i++) {
      var s = scored[i].spot;
      var m = meta(s);
      if (!ctx.evening && ctx.start < 15 * 60 && m.best_time === "evening") continue;
      if (!ctx.evening && ctx.start < 15 * 60 && m.best_time === "sunset" && budget <= 300) continue;
      var dur = preferredDuration(s, ctx.pace);
      var travel = chosen.length ? travelMinutes(last, s) : (ctx.origin ? travelMinutes(ctx.origin, s) : 0);
      if (chosen.length && total + travel + dur > budget) continue;
      chosen.push(s);
      total += travel + dur;
      last = s;
    }
    if (!chosen.length && scored.length) chosen.push(scored[0].spot);
    return { list: orderRoute(chosen, ctx.origin), total: total };
  }

  function startMinutes(ctx) {
    if (ctx.start != null) return ctx.start;
    var d = new Date();
    var m = d.getHours() * 60 + d.getMinutes() + 30;
    if (m >= 15 * 60) { ctx.nextDay = true; return 9 * 60 + 30; }
    if (m < 9 * 60 + 30) return 9 * 60 + 30;
    return Math.round(m / 15) * 15;
  }

  function fmtTime(mins) {
    var m = Math.round(mins);
    var h = Math.floor(m / 60) % 24, mm = m % 60;
    return (h < 10 ? "0" : "") + h + ":" + (mm < 10 ? "0" : "") + mm;
  }

  function fmtDur(mins) {
    var h = Math.floor(mins / 60), m = Math.round(mins % 60);
    if (lang() === "zh") return h ? (h + " 小时" + (m ? " " + m + " 分" : "")) : (m + " 分");
    if (lang() === "ko") return h ? (h + "시간" + (m ? " " + m + "분" : "")) : (m + "분");
    return h ? (h + " h" + (m ? " " + m + " m" : "")) : (m + " m");
  }

  function timeWord(ctx) {
    if (ctx.timeLabel) return ctx.timeLabel;
    if (ctx.minutes <= 120) return P("约 2 小时", "약 2시간", "~2 hours");
    if (ctx.minutes <= 240) return P("约半天", "약 반나절", "~half day");
    return P("约一天", "약 하루", "~full day");
  }

  function paceWord(p) {
    return p === "relaxed" ? P("轻松", "여유", "relaxed") : p === "packed" ? P("紧凑", "알찬", "packed") : P("均衡", "균형", "balanced");
  }
  function budgetWord(b) {
    return b === "free" ? P("尽量免费", "무료 위주", "free-first") : b === "low" ? P("省一点", "가성비", "low budget") : P("正常", "보통", "normal");
  }
  function mobilityWord(m) {
    return m === "wheelchair" ? P("轮椅", "휠체어", "wheelchair") : m === "stroller" ? P("婴儿车", "유모차", "stroller") : m === "lesswalk" ? P("少走路", "덜 걷기", "less walking") : P("无特殊限制", "제한 없음", "no limit");
  }
  function partyWord(p) {
    return p === "kids" ? P("带孩子", "아이 동반", "with kids") : p === "family" ? P("陪长辈", "어르신 동반", "with elders") : p === "two" ? P("两人", "2인", "two") : p === "friends" ? P("朋友", "친구", "friends") : p === "group" ? P("三人以上", "3인 이상", "3+") : P("一人", "1인", "solo");
  }

  function themeLabel(cat) {
    var lex = (C.lexicon ? C.lexicon() : {}) || {};
    var t = (lex.themes || {})[cat];
    if (t && t.label) return t.label[lang()] || t.label.zh;
    return C.catLabel(cat);
  }

  function buildContext(text, opts) {
    var prof = (window.BusanSession && BusanSession.profile()) || {};
    var t = String(text || "");
    var time = timeInfo(t);
    var matched = C.matchSpots ? C.matchSpots(t, 8) : [];
    var ctx = {
      matched: matched,
      theme: themeOf(opts, t, matched),
      interests: interestsOf(t, prof),
      pace: paceOf(t, prof),
      mobility: mobilityOf(t, prof),
      budget: budgetOf(t, prof),
      party: partyOf(t, opts, prof),
      minutes: time.minutes || (prof.pace === "relaxed" ? 180 : prof.pace === "packed" ? 330 : 240),
      start: time.start,
      timeLabel: time.label,
      evening: time.evening,
      morning: time.morning,
      origin: (window.BusanLive && BusanLive.position()) || null,
      onlyMatched: false,
      text: t
    };
    if (!ctx.theme && matched.length) ctx.theme = matched[0].spot.category;
    return ctx;
  }

  /** 行程类回答也固定给 3 个可选点，点开即可继续追问。 */
  function planChoices(list, ctx) {
    var out = [], used = {}, pool = list.concat(allSpots());
    var tags = [P("首选", "첫 번째", "Main"), P("更省力", "덜 걷기", "Easier"), P("换主题", "다른 테마", "Theme")];
    for (var i = 0; i < pool.length && out.length < 3; i++) {
      var s = pool[i];
      if (!s || used[s.id]) continue;
      used[s.id] = 1;
      var m = meta(s);
      out.push({
        spotId: s.id,
        name: label(s),
        tag: tags[out.length],
        reason: (themeLabel(s.category) || "") + " · " + (m.note || firstLine(field(s, "highlights")) || P("顺路可选", "경로상 선택", "On the way")),
        query: label(s)
      });
    }
    return out;
  }

  function buildLocal(text, opts) {    var ctx = buildContext(text, opts);
    var start = startMinutes(ctx);
    ctx.start = start;
    var picked = pickSpots(ctx);
    var list = picked.list;

    var names = list.map(function (s) { return label(s); });
    var title;
    if (list.length === 1) title = P("单点慢逛", "한 곳 천천히", "One spot, unhurried") + " · " + label(list[0]);
    else {
      var cats = [];
      list.forEach(function (s) { if (cats.indexOf(s.category) < 0) cats.push(s.category); });
      title = cats.slice(0, 2).map(themeLabel).join(" + ") + " · " + timeWord(ctx);
    }

    var core = coreWordsOf(text);
    var analysis = [];
    analysis.push(P("核心词：", "핵심어: ", "Core words: ") + (core.length ? core.join("、") : (names.join("、") || themeLabel(ctx.theme))));
    analysis.push(P("条件：", "조건: ", "Conditions: ") + timeWord(ctx) + " · " + paceWord(ctx.pace) + " · " + budgetWord(ctx.budget) + " · " + partyWord(ctx.party) + " · " + mobilityWord(ctx.mobility));
    if (ctx.origin) {
      var d0 = distanceFrom(ctx.origin, list[0]);
      analysis.push(P("起点：当前定位，最近入选点约 ", "출발: 현재 위치, 가장 가까운 지점 약 ", "Start: current location, nearest stop ~") +
        (d0 == null ? "?" : d0.toFixed(1)) + " km");
    } else {
      analysis.push(P("起点：未开启实时定位，按景点之间的相对位置排序。", "출발: 실시간 위치 꺼짐. 지점 간 상대 위치로 정렬했습니다.", "Start: live location off — ordered by relative positions."));
    }
    if (ctx.interests.length) {
      analysis.push(P("兴趣标签：", "관심 태그: ", "Interest tags: ") + ctx.interests.join("、"));
    }

    var lines = ["**" + title + "**", "", "**" + P("分析", "분석", "Analysis") + "**"];
    analysis.forEach(function (x) { lines.push("- " + x); });
    lines.push("", "**" + P("行程", "일정", "Itinerary") + "**");

    var clock = start;
    var prev = ctx.origin;
    list.forEach(function (s, i) {
      var dur = preferredDuration(s, ctx.pace);
      var travel = i === 0 ? (ctx.origin ? travelMinutes(ctx.origin, s) : 0) : travelMinutes(prev, s);
      if (i > 0) clock += travel;
      var from = clock, to = clock + dur;
      var km = i === 0 ? distanceFrom(ctx.origin, s) : distanceFrom(prev, s);
      var m = meta(s);
      if (m.best_time === "sunset" && clock < 16 * 60 && ctx.minutes > 300) clock = 16 * 60;
      if (m.best_time === "evening" && clock < 17 * 60) clock = 17 * 60;
      var why = firstLine(field(s, "highlights")) || m.note || "";
      var row = "- **" + fmtTime(from) + "–" + fmtTime(to) + "｜" + label(s) + "**（" +
        fmtDur(dur) +
        (km != null ? " · " + km.toFixed(1) + " km" : "") + "）";
      lines.push(row);
      if (why) lines.push("  - " + why);
      if (m.note && m.note !== why) lines.push("  - " + m.note);
      var ticket = firstLine(field(s, "ticket"));
      if (ticket && ctx.budget !== "medium") lines.push("  - " + P("门票：", "입장료: ", "Ticket: ") + ticket);
      clock = to;
      prev = s;
    });

    lines.push("", "**" + P("提示", "팁", "Tips") + "**");
    lines.push("- " + P("时间按“到达—离开”估算，景点之间的移动已留出余量；实际交通以 NAVER 地图为准。",
      "시간은 도착·출발 기준이며 이동 여유를 포함했습니다. 실제 교통은 NAVER 지도 기준입니다.",
      "Times are arrive-to-leave estimates with travel buffer; check NAVER Map for real transit."));
    if (ctx.nextDay) {
      lines.push("- " + P("现在已过 15:00，白天型景点按次日 09:30 起算；若只想看日落，可在输入框写“傍晚出发”。",
        "지금은 15:00가 넘어 주간 명소는 다음 날 09:30부터 계산했습니다. 일몰만 보려면 ‘저녁 출발’을 입력하세요.",
        "It is past 15:00, so daytime stops start next day at 09:30; for sunset only, type “evening start”."));
    }
    if (ctx.mobility !== "normal") {
      lines.push("- " + P("已按“" + mobilityWord(ctx.mobility) + "”降低坡道/阶梯多的点权重。",
        "‘" + mobilityWord(ctx.mobility) + "’ 조건에 따라 경사·계단이 많은 지점 가중치를 낮췄습니다.",
        "Spots with steep slopes or stairs were down-weighted for “" + mobilityWord(ctx.mobility) + "”."));
    }
    if (ctx.budget === "free") {
      lines.push("- " + P("优先免费点；门票与营业状态出发前仍要看官网。", "무료 지점 우선. 입장료·운영 상태는 출발 전 공식 사이트 확인.", "Free spots first; check official sites for tickets and hours before leaving."));
    }
    if (window.BusanSession && !BusanSession.currentUser()) {
      lines.push("- " + P("登录后可把这次节奏、预算与兴趣存到账户，下次直接沿用。", "로그인하면 이번 속도·예산·취향을 저장해 다음에 이어서 쓸 수 있습니다.", "Sign in to save this pace, budget and interests for next time."));
    }

    var sources = [
      (window.BusanUI && BusanUI.online() ? P("云端库 ", "클라우드 DB ", "Cloud DB ") : P("包内快照 ", "내장 스냅숏 ", "Bundled snapshot ")) +
      (C.updatedAt ? C.updatedAt() : ""),
      P("核心词库", "핵심어 사전", "Core-word lexicon"),
      ctx.origin ? P("实时定位", "실시간 위치", "Live location") : P("景点坐标", "명소 좌표", "Spot coordinates")
    ];

    var followups = [
      P("换成更轻松的路线", "더 여유로운 코스로", "Make it more relaxed"),
      P("只想看日落和夜景", "일몰·야경만 보고 싶어", "Only sunset and night views"),
      P("加一个免费景点", "무료 명소 하나 추가", "Add a free spot"),
      P("从甘川文化村出发", "감천문화마을에서 출발", "Start from Gamcheon")
    ];

    var plan = {
      title: title,
      summary: names.join(" → "),
      at: new Date().toLocaleDateString(),
      constraints: {
        minutes: ctx.minutes, pace: ctx.pace, budget: ctx.budget,
        party: ctx.party, mobility: ctx.mobility, theme: ctx.theme, interests: ctx.interests
      },
      spotIds: list.map(function (s) { return s.id; })
    };

    return {
      text: lines.join("\n"),
      sources: sources,
      sourceUrl: (list.length && C.sourceUrl) ? C.sourceUrl(list[0]) : "",
      followups: followups,
      choices: planChoices(list, ctx),
      tag: P("自主分析 · 本地推演", "자체 분석 · 로컬 추론", "Self-analysis · local reasoning"),
      plan: plan,
      ctx: ctx,
      llm: false
    };
  }

  /* ---------------- 大模型增强（可选） ---------------- */
  function candidatePayload(ctx, list) {
    return list.slice(0, 6).map(function (s) {
      var m = meta(s);
      return {
        name: label(s),
        category: themeLabel(s.category),
        duration_min: m.duration_min,
        duration_max: m.duration_max,
        best_time: m.best_time,
        walk_level: m.walk_level,
        family_score: m.family_score,
        distance_km: ctx.origin ? (function () {
          var d = distanceFrom(ctx.origin, s);
          return d == null ? null : Math.round(d * 10) / 10;
        })() : null,
        highlights: (field(s, "highlights") || "").split("\n").map(tidy).filter(Boolean).slice(0, 2),
        ticket: (field(s, "ticket") || "").split("\n").map(tidy).filter(Boolean).slice(0, 1),
        note: m.note
      };
    });
  }

  function llmMessages(ctx, list) {
    var langName = lang() === "zh" ? "中文" : lang() === "ko" ? "한국어" : "English";
    var system = "You are a travel planner for Saha-gu, Busan. Use ONLY the candidate spots and facts provided. " +
      "Never invent distances, durations, prices, opening hours, crowding or weather. " +
      "Respect the time budget, mobility, budget, party and interests. " +
      "Choose 2-4 stops (or 1 if the budget is under 100 minutes), order them sensibly, and answer in " + langName + ". " +
      "Return STRICT JSON only: {\"title\":\"\",\"analysis\":[\"\"],\"stops\":[{\"name\":\"\",\"start\":\"HH:MM\",\"duration_min\":120,\"why\":\"\"}],\"tips\":[\"\"]}. " +
      "Every stop name must exactly match one candidate name.";
    var user = JSON.stringify({
      request: ctx.text || P("按当前选择规划", "현재 조건으로 일정", "Plan with current choices"),
      constraints: {
        time_budget_minutes: ctx.minutes,
        pace: ctx.pace,
        budget: ctx.budget,
        party: ctx.party,
        mobility: ctx.mobility,
        interests: ctx.interests,
        start_time_hint: ctx.start == null ? null : fmtTime(ctx.start),
        theme: themeLabel(ctx.theme)
      },
      profile: (window.BusanSession && BusanSession.profile()) || {},
      candidates: candidatePayload(ctx, list)
    });
    return [{ role: "system", content: system }, { role: "user", content: user }];
  }

  function parseJson(text) {
    var t = String(text || "").trim();
    t = t.replace(/^```(?:json)?/i, "").replace(/```$/, "").trim();
    var i = t.indexOf("{"), j = t.lastIndexOf("}");
    if (i >= 0 && j > i) t = t.slice(i, j + 1);
    try { return JSON.parse(t); } catch (e) { return null; }
  }

  function findByName(name, list) {
    var k = norm(name);
    for (var i = 0; i < list.length; i++) {
      var s = list[i], names = [s.name, s.name_ko, s.name_en].concat(s.aliases || []);
      for (var j = 0; j < names.length; j++) if (norm(names[j]) === k) return s;
    }
    return null;
  }

  function fromLlm(data, local, ctx, list) {
    if (!data || !Array.isArray(data.stops) || !data.stops.length) return null;
    var stops = [], total = 0;
    for (var i = 0; i < data.stops.length && i < 5; i++) {
      var x = data.stops[i] || {};
      var s = findByName(x.name, list);
      if (!s) return null;
      var dur = Number(x.duration_min);
      if (!isFinite(dur) || dur < 20 || dur > 300) dur = preferredDuration(s, ctx.pace);
      total += dur;
      stops.push({ spot: s, start: String(x.start || ""), dur: dur, why: tidy(x.why || "") });
    }
    if (!stops.length) return null;
    if (total > ctx.minutes + 60) return null;

    var title = tidy(data.title || local.plan.title);
    var analysis = Array.isArray(data.analysis) ? data.analysis : [String(data.analysis || "")];
    var lines = ["**" + title + "**", "", "**" + P("分析", "분석", "Analysis") + "**"];
    analysis.filter(Boolean).slice(0, 5).forEach(function (x) { lines.push("- " + tidy(x)); });
    lines.push("", "**" + P("行程", "일정", "Itinerary") + "**");

    var clock = startMinutes(ctx);
    for (var j = 0; j < stops.length; j++) {
      var st = stops[j];
      var startMin = null;
      var mt = st.start.match(/^(\d{1,2}):(\d{2})$/);
      if (mt) startMin = parseInt(mt[1], 10) * 60 + parseInt(mt[2], 10);
      if (startMin == null) startMin = clock;
      var to = startMin + st.dur;
      var km = j === 0 ? distanceFrom(ctx.origin, st.spot) : distanceFrom(stops[j - 1].spot, st.spot);
      lines.push("- **" + fmtTime(startMin) + "–" + fmtTime(to) + "｜" + label(st.spot) + "**（" +
        fmtDur(st.dur) +
        (km != null ? " · " + km.toFixed(1) + " km" : "") + "）");
      var why = st.why || firstLine(field(st.spot, "highlights")) || meta(st.spot).note;
      if (why) lines.push("  - " + why);
      clock = to;
    }
    if (Array.isArray(data.tips) && data.tips.length) {
      lines.push("", "**" + P("提示", "팁", "Tips") + "**");
      data.tips.filter(Boolean).slice(0, 4).forEach(function (x) { lines.push("- " + tidy(x)); });
    }
    lines.push("", "- " + P("大模型只重排了候选点与时间；距离、票价、营业状态仍取自景点库。",
      "LLM은 후보 지점과 시간만 재배치했습니다. 거리·요금·운영 상태는 명소 DB 기준입니다.",
      "The model only reordered candidates and timing; distance, tickets and hours still come from the spot DB."));

    return {
      text: lines.join("\n"),
      tag: P("自主分析 · 大模型", "자체 분석 · LLM", "Self-analysis · LLM"),
      sources: local.sources.concat([P("大模型重排（仅用候选点）", "LLM 재배치(후보 지점만)", "LLM reorder (candidates only)")]),
      sourceUrl: local.sourceUrl,
      followups: local.followups,
      choices: planChoices(stops.map(function (x) { return x.spot; }), ctx),
      plan: {
        title: title,
        summary: stops.map(function (x) { return label(x.spot); }).join(" → "),
        at: new Date().toLocaleDateString(),
        constraints: local.plan.constraints,
        spotIds: stops.map(function (x) { return x.spot.id; })
      },
      ctx: ctx,
      llm: true
    };
  }

  /* ---------------- 对外入口 ---------------- */
  function enrichWithLlm(local, msg) {
    if (!window.BusanLLM || !BusanLLM.configured()) return;
    if (!window.BusanUI || !BusanUI.online()) return;
    // 给模型一个受限候选池：按本地打分排序的前 8 个景点，它只能从中选
    var list = allSpots().slice().sort(function (a, b) {
      return scoreSpot(b, local.ctx) - scoreSpot(a, local.ctx);
    }).slice(0, 8);
    if (!list.length) return;
    BusanLLM.chat(llmMessages(local.ctx, list), function (code, content) {
      if (code !== 0) return;
      var data = parseJson(content);
      var out = fromLlm(data, local, local.ctx, list);
      if (!out) return;
      if (msg && BusanUI.updateBubble) BusanUI.updateBubble(msg, out);
      BusanUI.renderFollowups(out);
      BusanUI.setLastPlan(out.plan);
      if (window.BusanSession) BusanSession.saveSoon();
    });
  }

  function run(text, opts) {
    if (!C || !C.getDb()) return;
    opts = opts || {};
    var clean = tidy(text);
    if (!clean) clean = P("按当前选择规划", "현재 조건으로 일정", "Plan with current choices");
    if (window.BusanUI && BusanUI.noteUser) BusanUI.noteUser(clean);
    else if (window.BusanUI && BusanUI.addUser) BusanUI.addUser(clean);

    var res = buildLocal(clean, opts);
    var msg = window.BusanUI ? BusanUI.addBot(res) : null;
    if (window.BusanUI) {
      BusanUI.setLastPlan(res.plan);
      if (BusanUI.renderFollowups) BusanUI.renderFollowups(res);
    }
    if (window.BusanLive && res.plan.spotIds && res.plan.spotIds.length) {
      BusanLive.setTarget(res.plan.spotIds[0]);
    }
    if (window.BusanSession) BusanSession.saveSoon();
    enrichWithLlm(res, msg);
    return res;
  }

  function replay(text) {
    try { return buildLocal(text, {}); } catch (e) { return null; }
  }

  function intercept(text) {
    var t = String(text || "");
    var spot = C.findSpot(t);
    // 明确问“有几条路/怎么去/从当前位置出发”时，先交给路线权限与实时路线流程，
    // 不能因为出现“路线”二字就被当成行程规划。
    if (spot && /几条(路|线)|有哪几条|哪几条|怎么去|怎么走|怎么到|如何到|从.{0,8}当前位置|从我(这里|当前位置)?|当前位置.{0,8}(去|到)|路线可|交通方式/.test(t) &&
        !/规划|安排|行程|一日游|半日|半天|怎么玩|玩什么|带.{0,6}(逛|玩)| itinerary|plan a trip/i.test(t)) {
      return false;
    }
    var strong = /规划|安排|行程|路线|怎么玩|玩什么|一日游|半日|半天|一天|带我|推荐路线|计划去|想去|想看|想拍|去哪儿看|去哪看|看日落|看夜景|일정|코스|반나절|하루|plan|itinerary|route|schedule/i;
    if (!strong.test(t)) return false;
    var intent = C.intentOf(t);
    if (spot && intent !== "overview" && !/规划|安排|行程|路线|怎么玩|一日游|半日|半天|一天|带|일정|코스|plan|itinerary|route/i.test(t)) {
      return false;
    }
    return true;
  }

  function planFromSelection() {
    var opts = {
      theme: window.BusanUI && BusanUI.isAutoCat() ? "" : BusanUI.getCat(),
      party: window.BusanUI && BusanUI.isAutoGrp() ? "" : BusanUI.getGrp()
    };
    run("", opts);
  }

  window.BusanPlanner = {
    intercept: intercept,
    run: run,
    replay: replay,
    planFromSelection: planFromSelection,
    buildLocal: buildLocal,
    extract: function (text) {
      var c = buildContext(text, {});
      return {
        coreWords: coreWordsOf(text),
        matched: c.matched.map(function (r) { return { name: label(r.spot), direct: r.direct, score: r.score, hits: r.hits }; }),
        constraints: {
          minutes: c.minutes, pace: c.pace, budget: c.budget,
          party: c.party, mobility: c.mobility, interests: c.interests, theme: c.theme
        }
      };
    }
  };
})();
