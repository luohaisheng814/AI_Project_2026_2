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
      localNote: "以上来自包内数据（离线）",
      choicesLabel: "3 个可选方案",
      choiceOpen: "看这个",
      choiceMain: "首选",
      choiceEasy: "省力",
      choiceTheme: "换口味"
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
      localNote: "내장 데이터 기준입니다(오프라인)",
      choicesLabel: "3가지 선택안",
      choiceOpen: "이 안 보기",
      choiceMain: "첫 번째",
      choiceEasy: "덜 걷기",
      choiceTheme: "다른 테마"
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
      localNote: "From bundled data (offline)",
      choicesLabel: "3 options",
      choiceOpen: "Open this",
      choiceMain: "Main",
      choiceEasy: "Easier",
      choiceTheme: "Theme"
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
  function P(zh, ko, en) { return st.lang === "zh" ? zh : st.lang === "ko" ? ko : en; }
  function tidy(s) { return String(s == null ? "" : s).replace(/\r/g, "").trim(); }
  function key(s) {
    return tidy(s).toLowerCase()
      .replace(/[\s\u3000·,，。.!?！？、/\\()（）【】\[\]<>《》"'“”‘’\-_+~:：;；]+/g, "");
  }

  /** 一个景点可用于检索的全部词：三语名称、别名、核心词。 */
  function keywordsOf(s) {
    var out = [s.name, s.name_ko, s.name_en].concat(s.aliases || [], s.core || []);
    var seen = {}, list = [];
    for (var i = 0; i < out.length; i++) {
      var k = key(out[i]);
      if (k && !seen[k]) { seen[k] = 1; list.push(k); }
    }
    return list;
  }

  /** 某核心词覆盖了几个景点；唯一命中给额外权重。 */
  function keywordSpread(list, kw) {
    var n = 0;
    for (var i = 0; i < list.length; i++) {
      var words = keywordsOf(list[i]);
      for (var j = 0; j < words.length; j++) {
        if (words[j] === kw) { n++; break; }
      }
    }
    return n;
  }

  /**
   * 多景点打分：名称 / 别名优先，其次核心词。
   * 返回 [{spot, score, hits}]，planner 用它做多约束筛选。
   */
  function matchSpots(q, limit) {
    var k = key(q), list = spots(), rows = [];
    if (!k) return [];
    for (var i = 0; i < list.length; i++) {
      var s = list[i], score = 0, hits = [], direct = false;
      var names = [s.name, s.name_ko, s.name_en].concat(s.aliases || []);
      for (var j = 0; j < names.length; j++) {
        var nk = key(names[j]);
        if (!nk) continue;
        if (k === nk) { score = Math.max(score, 1000); direct = true; }
        else if (k.indexOf(nk) >= 0) { score = Math.max(score, 620 + nk.length); direct = true; }
        else if (nk.indexOf(k) >= 0 && k.length >= 2) { score = Math.max(score, 500 + k.length); direct = true; }
      }
      var cores = s.core || [];
      for (var c = 0; c < cores.length; c++) {
        var ck = key(cores[c]);
        if (!ck || ck.length < 2) continue;
        if (k.indexOf(ck) >= 0) {
          var spread = keywordSpread(list, ck);
          var sc = 120 + ck.length * 4 + (ck.length >= 4 ? 60 : 0) + (spread === 1 ? 80 : 0);
          if (sc > score) score = sc;
          hits.push(cores[c]);
        } else if (ck.indexOf(k) >= 0 && k.length >= 2 && score < 90) {
          score = Math.max(score, 90);
        }
      }
      if (score > 0) rows.push({ spot: s, score: score, hits: hits, direct: direct });
    }
    rows.sort(function (a, b) { return b.score - a.score; });
    return rows.slice(0, limit || rows.length);
  }

  function findSpot(q) {
    var rows = matchSpots(q, 1);
    if (!rows.length) return null;
    // 只命中一个泛化核心词（如「拍照」「海边」）时不当成具体景点，交给 planner 多选
    if (!rows[0].direct && rows[0].score < 180) return null;
    return rows[0].spot;
  }

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

  function firstLine(text) { return firstLines(text, 1)[0] || ""; }

  /** 从一句问题里抽“人”的条件：同行、行动限制、兴趣、预算与时段。 */
  function contextOf(q) {
    var t = String(q || "");
    var c = {
      kids: /孩子|亲子|小孩|儿童|宝宝|아이|어린이|유아|kid|child|toddler/i.test(t),
      stroller: /婴儿车|推车|유모차|stroller|pushchair/i.test(t),
      wheelchair: /轮椅|휠체어|wheelchair/i.test(t),
      lesswalk: /少走|腿脚|老人|长辈|父母|不方便|걷기\s*(힘|싫)|어르신|노인|less\s*walk|mobility/i.test(t),
      photo: /拍照|机位|打卡|摄影|사진|포토|photo|camera|instagram/i.test(t),
      sunset: /日落|夕阳|傍晚|일몰|노을|저녁|sunset|dusk/i.test(t),
      morning: /上午|早上|清晨|아침|morning/i.test(t),
      free: /免费|不花钱|무료|free/i.test(t),
      quiet: /安静|人少|不挤|한적|조용|quiet|less\s*crowd/i.test(t),
      cafe: /咖啡|카페|coffee|cafe/i.test(t),
      art: /艺术|文化|壁画|예술|문화|art|culture|mural/i.test(t),
      wetland: /湿地|候鸟|观鸟|습지|철새|wetland|bird/i.test(t),
      halfday: /半天|반나절|half\s*day/i.test(t)
    };
    c.any = c.kids || c.stroller || c.wheelchair || c.lesswalk || c.photo || c.sunset ||
            c.morning || c.free || c.quiet || c.cafe || c.art || c.wetland || c.halfday;
    return c;
  }

  function walkWord(n) {
    return n >= 4 ? P("坡道/阶梯多", "경사·계단 많음", "steep or many stairs") :
           n >= 3 ? P("有一定步行量", "보통 수준의 도보", "moderate walking") :
           P("步行轻松", "걷기 편함", "easy walking");
  }

  /** 把景点的时长、体力、亲子、拍照、时段、票价和当前位置拼成“针对这个人”的判断。 */
  function fitLines(s, c) {
    var m = s.plan || {};
    var lines = [];
    var add = function (x) { if (x && lines.length < 3 && lines.indexOf(x) < 0) lines.push(x); };
    var walk = m.walk_level || 2, fam = m.family_score || 3, photo = m.photo_score || 3;

    if (c.wheelchair || c.stroller || c.lesswalk) {
      var mode = c.wheelchair ? P("轮椅", "휠체어", "wheelchair") :
                 c.stroller ? P("婴儿车", "유모차", "stroller") : P("少走路", "덜 걷기", "less walking");
      if (walk >= 4) {
        add(P("步行强度 " + walk + "/5，" + walkWord(walk) + "；" + mode + "不建议把这里当主行程。",
          "도보 강도 " + walk + "/5, " + walkWord(walk) + "; " + mode + " 사용 시 대표 코스로는 비추천.",
          "Walk level " + walk + "/5 (" + walkWord(walk) + "); not ideal as the main stop for " + mode + "."));
      } else if (walk >= 3) {
        add(P("步行强度 " + walk + "/5，有坡道；" + mode + "建议只走主路线并留休息。",
          "도보 강도 " + walk + "/5, 경사가 있습니다. " + mode + " 이용 시 주 코스만 걷고 휴식을 두세요.",
          "Walk level " + walk + "/5 with slopes; for " + mode + ", keep to the main route and rest."));
      } else {
        add(P("步行强度 " + walk + "/5，对" + mode + "相对友好。",
          "도보 강도 " + walk + "/5, " + mode + " 이용에 비교적 편합니다.",
          "Walk level " + walk + "/5 — relatively friendly for " + mode + "."));
      }
      var tip = firstLine(pickField(s, "tips"));
      if (tip && /轮椅|婴儿车|阶梯|台阶|坡|계단|경사|유모차|휠체어|stairs|slope|stroller|wheelchair/i.test(tip)) {
        add(P("现场提示：" + tip, "현장 안내: " + tip, "On-site note: " + tip));
      }
    }

    if (c.kids) {
      if (fam >= 4) add(P("家庭评分 " + fam + "/5，适合带孩子；仍要避开台阶多的支路。",
        "가족 적합도 " + fam + "/5, 아이와 함께하기 좋습니다. 계단 많은 샛길은 피하세요.",
        "Family score " + fam + "/5 — good with kids; still avoid stair-heavy side paths."));
      else add(P("家庭评分 " + fam + "/5，带小孩建议缩短停留，优先走平坦主路。",
        "가족 적합도 " + fam + "/5, 아이와 함께라면 체류를 줄이고 평탄한 주로를 이용하세요.",
        "Family score " + fam + "/5 — with kids, shorten the stay and stick to flat main paths."));
    }

    if (c.photo) {
      add(photo >= 4 ? P("拍照评分 " + photo + "/5，是这一片的主力机位。",
        "사진 적합도 " + photo + "/5, 이 지역의 대표 촬영 포인트입니다.",
        "Photo score " + photo + "/5 — a main photo spot in this area.")
        : P("拍照评分 " + photo + "/5，拍照不是它的强项，别把行程全押在这里。",
        "사진 적합도 " + photo + "/5, 촬영은 주력이 아니므로 일정을 여기에만 맞추지 마세요.",
        "Photo score " + photo + "/5 — photography is not its strength; do not build the whole plan around it."));
    }

    if (c.sunset || c.morning) {
      var best = m.best_time || "any";
      if (c.sunset) {
        if (best === "sunset" || best === "evening") {
          add(P("最佳时段正是日落/傍晚，按日落前 1 小时到场。",
            "최적 시간대가 일몰·저녁입니다. 일몰 1시간 전 도착을 권장합니다.",
            "Best time is sunset/evening — arrive one hour before sunset."));
        } else {
          add(P("这里不是日落主场景；想看海边日落，改去多大浦海水浴场或峨嵋山观景台。",
            "이곳은 일몰 주 무대가 아닙니다. 바다 일몰은 다대포해수욕장이나 아미산 전망대를 권장합니다.",
            "This is not a sunset spot; for a sea sunset, go to Dadaepo Beach or Amisan Observatory."));
        }
      } else if (best === "morning") {
        add(P("最佳时段是上午，建议 09:30 前后到，避开排队和顶光。",
          "최적 시간대는 오전입니다. 09:30 전후 도착해 대기와 역광을 피하세요.",
          "Best time is morning — arrive around 09:30 to avoid queues and harsh light."));
      }
    }

    if (c.free) {
      var ticket = firstLine(pickField(s, "ticket"));
      if (/免费|무료|free/i.test(ticket)) add(P("门票：" + ticket + "，符合“尽量免费”。",
        "입장료: " + ticket + " — '무료 우선' 조건에 맞습니다.",
        "Ticket: " + ticket + " — fits the free-first constraint."));
      else if (ticket) add(P("门票不是免费：" + ticket,
        "입장료가 무료가 아닙니다: " + ticket,
        "Not free: " + ticket));
    }

    if (c.quiet && /04_|湿地|生态|渔港/.test(s.category || "")) {
      add(P("这类点位相对不挤，适合避开人群；周末仍建议早到。",
        "이 유형은 비교적 한적합니다. 주말에도 일찍 도착하는 편이 좋습니다.",
        "This type is relatively uncrowded; still arrive early on weekends."));
    }

    if (c.cafe && (s.vibes || []).indexOf("cafe") >= 0) {
      add(P("点位内有咖啡/休息点，拍照和歇脚可以放在同一段。",
        "카페·휴식 지점이 있어 촬영과 휴식을 한 구간에 묶을 수 있습니다.",
        "Cafe/rest points on site — combine photos and a break in one block."));
    }

    if (c.wetland && ((s.vibes || []).indexOf("wetland") >= 0 || /湿地|候鸟|生态/.test(s.category || ""))) {
      add(P("湿地/候鸟类点位，清晨或黄昏观鸟更稳；带望远镜。",
        "습지·철새 유형은 새벽·황혼 관찰이 안정적입니다. 망원경을 챙기세요.",
        "Wetland/bird spot — dawn or dusk is more reliable; bring binoculars."));
    }

    var pos = (window.BusanLive && BusanLive.position && BusanLive.position()) || null;
    if (pos && s.lat != null && s.lng != null) {
      var km = haversine(pos.lat, pos.lng, s.lat, s.lng);
      add(P("从当前位置直线约 " + km.toFixed(1) + " km；这是直线距离，步行/公交以 NAVER 地图为准。",
        "현재 위치에서 직선 약 " + km.toFixed(1) + " km; 직선 거리이며 도보·대중교통은 NAVER 지도 기준입니다.",
        "About " + km.toFixed(1) + " km straight-line from you; walking/transit per NAVER Map."));
    }

    return lines;
  }

  /** 条件明显不匹配时，只补一个更贴合的点，并说明为什么。 */
  function alternativeFor(s, c) {
    var needMove = c.wheelchair || c.stroller || c.lesswalk;
    var needKid = c.kids;
    var needSun = c.sunset;
    if (!needMove && !needKid && !needSun) return null;
    var cur = s.plan || {};
    if ((!needMove || (cur.walk_level || 2) < 4) &&
        (!needKid || (cur.family_score || 3) >= 4) &&
        (!needSun || cur.best_time === "sunset" || cur.best_time === "evening")) return null;

    var best = null, bestScore = -1e9;
    spots().forEach(function (x) {
      if (x.id === s.id) return;
      var m = x.plan || {};
      var score = 0;
      if (needMove) score += (5 - (m.walk_level || 2)) * 3 - ((m.walk_level || 2) >= 4 ? 12 : 0);
      if (needKid) score += (m.family_score || 3) * 4;
      if (needSun) score += (m.best_time === "sunset" || m.best_time === "evening") ? 14 : -8;
      if (score > bestScore) { bestScore = score; best = x; }
    });
    return best;
  }

  function sourceUrlFor(s) {
    var u = (s && s.official && s.official.url) || "";
    if (!u) {
      var m = String(pickField(s, "source") || "").match(/https?:\/\/[^\s"'<>]+/);
      u = m ? m[0] : "https://www.saha.go.kr/tour/";
    }
    return u;
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

  function sourcesFor(s) {
    var out = [];
    if (st.mode === "online") {
      var open = st.lang === "zh" ? "（" : " (", close = st.lang === "zh" ? "）" : ")";
      out.push((st.lang === "zh" ? "云端数据库 " : st.lang === "ko" ? "클라우드 DB " : "Cloud DB ")
        + "spots.json" + open + (st.db.updated_at || "") + close);
      out.push((st.lang === "zh" ? "官网 " : st.lang === "ko" ? "공식 사이트 " : "Official site ")
        + ((s.official && s.official.host) || ""));
    } else {
      out.push((st.lang === "zh" ? "包内数据 " : st.lang === "ko" ? "내장 데이터 " : "Bundled data ")
        + "cloud_snapshot.json" + (st.lang === "zh" ? "（离线）" : st.lang === "ko" ? " (오프라인)" : " (offline)"));
    }
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

  /** 每条具体回答固定给 3 个可选方案：主方案 + 更省力 + 换主题。 */
  function choiceOf(x, tag, reason) {
    return {
      spotId: x.id,
      name: spotTitle(x),
      tag: tag,
      reason: reason,
      query: spotTitle(x)
    };
  }

  function choicesFor(s, ctx) {
    var out = [];
    var used = {};
    used[s.id] = 1;
    out.push(choiceOf(s, t("choiceMain"),
      P("经典走法 · 约 " + Math.round((s.plan || {}).duration_min || 120) / 60 + " 小时，" + reasonOf(s),
        "기본 코스 · 약 " + Math.round((s.plan || {}).duration_min || 120) / 60 + "시간, " + reasonOf(s),
        "Classic · about " + Math.round((s.plan || {}).duration_min || 120) / 60 + " h, " + reasonOf(s))));

    var list = spots().filter(function (x) { return x.id !== s.id; });
    var low = list.slice().sort(function (a, b) {
      var wa = (a.plan || {}).walk_level || 2, wb = (b.plan || {}).walk_level || 2;
      if (wa !== wb) return wa - wb;
      return ((b.plan || {}).family_score || 3) - ((a.plan || {}).family_score || 3);
    });
    var easy = low.filter(function (x) { return !used[x.id]; })[0];
    if (easy) {
      used[easy.id] = 1;
      var m = easy.plan || {};
      out.push(choiceOf(easy, t("choiceEasy"),
        P("步行强度 " + (m.walk_level || 2) + "/5 · 亲子 " + (m.family_score || 3) + "/5，" + reasonOf(easy),
          "도보 " + (m.walk_level || 2) + "/5 · 가족 " + (m.family_score || 3) + "/5, " + reasonOf(easy),
          "Walk " + (m.walk_level || 2) + "/5 · family " + (m.family_score || 3) + "/5, " + reasonOf(easy))));
    }

    var themes = supplements(s, 4).filter(function (x) { return !used[x.id]; });
    if (!themes.length) themes = low.filter(function (x) { return !used[x.id]; });
    var theme = themes[0];
    if (theme) {
      out.push(choiceOf(theme, t("choiceTheme"), (catLabel(theme.category) || "") + " · " + reasonOf(theme)));
    }

    // 数据异常时也保证三条
    for (var i = 0; out.length < 3 && i < list.length; i++) {
      if (!used[list[i].id]) {
        used[list[i].id] = 1;
        out.push(choiceOf(list[i], t("choiceTheme"), reasonOf(list[i])));
      }
    }
    return out.slice(0, 3);
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
      var max = concise ? 2 : (intent === "overview" ? 3 : (intent === "transport" || intent === "hours" ? 5 : 4));
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
    }
    if (intent === "overview" && !concise) {
      var m = s.plan || {};
      if (m.duration_min) {
        var best = m.best_time === "morning" ? P("上午", "오전", "morning") :
          (m.best_time === "sunset" || m.best_time === "evening") ? P("日落/傍晚", "일몰·저녁", "sunset/evening") : P("全天", "종일", "any time");
        lines.push("", "**" + P("怎么安排", "일정 판단", "How to plan") + "**");
        lines.push("- " + P("建议停留 " + Math.round(m.duration_min / 60 * 10) / 10 + "–" + Math.round((m.duration_max || m.duration_min) / 60 * 10) / 10 +
          " 小时 · 步行强度 " + (m.walk_level || 2) + "/5 · 最佳时段：" + best,
          "권장 체류 " + Math.round(m.duration_min / 60 * 10) / 10 + "~" + Math.round((m.duration_max || m.duration_min) / 60 * 10) / 10 +
          "시간 · 도보 강도 " + (m.walk_level || 2) + "/5 · 최적 시간: " + best,
          "Stay " + Math.round(m.duration_min / 60 * 10) / 10 + "–" + Math.round((m.duration_max || m.duration_min) / 60 * 10) / 10 +
          " h · walk " + (m.walk_level || 2) + "/5 · best: " + best));
        lines.push("- " + P("拍照 " + (m.photo_score || 3) + "/5 · 亲子 " + (m.family_score || 3) + "/5 · " + (m.indoor ? "室内为主" : "户外为主"),
          "사진 " + (m.photo_score || 3) + "/5 · 가족 " + (m.family_score || 3) + "/5 · " + (m.indoor ? "실내 위주" : "야외 위주"),
          "Photo " + (m.photo_score || 3) + "/5 · family " + (m.family_score || 3) + "/5 · " + (m.indoor ? "mostly indoor" : "mostly outdoor")));
        if (m.note && st.lang === "zh") lines.push("- " + m.note);
      }
    }

    var ctx = contextOf(opts && opts.text);
    var fit = (!concise && ctx.any) ? fitLines(s, ctx) : [];
    if (fit.length) {
      lines.push("", "**" + P("针对你的情况", "요청에 맞춘 판단", "For your case") + "**");
      fit.forEach(function (x) { lines.push("- " + x); });
      var alt = alternativeFor(s, ctx);
      if (alt) {
        var why = [];
        if (ctx.wheelchair || ctx.stroller || ctx.lesswalk) why.push(P("步行强度 " + ((alt.plan || {}).walk_level || 2) + "/5",
          "도보 강도 " + ((alt.plan || {}).walk_level || 2) + "/5", "walk " + ((alt.plan || {}).walk_level || 2) + "/5"));
        if (ctx.kids) why.push(P("家庭评分 " + ((alt.plan || {}).family_score || 3) + "/5",
          "가족 적합도 " + ((alt.plan || {}).family_score || 3) + "/5", "family " + ((alt.plan || {}).family_score || 3) + "/5"));
        if (ctx.sunset) why.push(P("最佳时段 " + (((alt.plan || {}).best_time === "evening" || (alt.plan || {}).best_time === "sunset") ? "日落/傍晚" : ((alt.plan || {}).best_time || "any")),
          "최적 시간 " + (((alt.plan || {}).best_time === "evening" || (alt.plan || {}).best_time === "sunset") ? "일몰·저녁" : ((alt.plan || {}).best_time || "any")),
          "best " + ((alt.plan || {}).best_time || "any")));
        lines.push("- " + P("更贴合你的替代点：", "더 맞는 대안: ", "Better fit: ") + "**" + spotTitle(alt) + "**" +
          (why.length ? (st.lang === "zh" ? "（" + why.join(" · ") + "）" : " (" + why.join(" · ") + ")") : ""));
      }
    }

    if (intent === "overview") {
      lines.push("", st.lang === "zh" ? "想看交通、门票或开放时间，点下面的追问。" :
        st.lang === "ko" ? "교통·입장료·운영시간이 궁금하면 아래 질문을 눌러 주세요." :
        "Tap a follow-up below for transport, tickets or hours.");
    }

    if (concise) lines.push("", t("conciseHint"));
    var pickedChoices = choicesFor(s, ctx);
    return {
      text: lines.join("\n"),
      sources: [],
      sourceUrl: sourceUrlFor(s),
      followups: followupsFor(s),
      spotId: s.id,
      intent: intent,
      choices: pickedChoices,
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
    return compose(s, onlyName ? "overview" : intent, { concise: onlyName || opts.concise, text: q });
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

  function mergeLocalLexicon(db) {
    if (!db || !db.spots) return db;
    if (!SNAP || !SNAP.spots) return db;
    var byId = {};
    SNAP.spots.forEach(function (s) { byId[s.id] = s; });
    db.spots.forEach(function (s) {
      var local = byId[s.id];
      if (!local) return;
      if (!s.core || !s.core.length) s.core = local.core || [];
      if (!s.vibes || !s.vibes.length) s.vibes = local.vibes || [];
      if (!s.plan) s.plan = local.plan || {};
    });
    if (!db.lexicon || !db.lexicon.themes) db.lexicon = SNAP.lexicon || db.lexicon;
    if (!db.schema || db.schema < 3) db.schema = 3;
    return db;
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
          db = mergeLocalLexicon(db);
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
    if (idx > 0) {
      var gt = h.indexOf(">", idx);
      h = h.slice(gt >= 0 ? gt + 1 : idx, (gt >= 0 ? gt + 1 : idx) + 6000);
    }
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
    matchSpots: matchSpots,
    keywordsOf: keywordsOf,
    allSpots: function () { return spots(); },
    lexicon: function () { return (st.db && st.db.lexicon) || {}; },
    updatedAt: function () { return (st.db && st.db.updated_at) || ""; },
    field: pickField,
    nearby: nearby,
    mapLinks: mapLinks,
    sourceUrl: sourceUrlFor,
    fetchOfficial: fetchOfficial,
    officialNote: function (id) { return st.official[id]; },
    spotTitle: spotTitle,
    catLabel: catLabel,
    reasonOf: reasonOf,
    haversine: haversine
  };
})();
