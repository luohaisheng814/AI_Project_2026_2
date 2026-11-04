/* Busan 离线问答引擎 + 界面逻辑
 * 供 Android 安装包 WebView 使用：数据来自 data.js（window.BUSAN_DATA），
 * 不联网、不请求电脑端服务，问答全部在本地完成。
 * 末尾导出 BusanEngine，便于用 Node 做回归测试。
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.BusanEngine = api;
})(typeof window !== "undefined" ? window : null, function () {
  "use strict";

  var LANGS = ["zh", "ko", "en"];

  var FIELD_ORDER = ["overview", "highlights", "hours", "ticket", "course", "transport",
                     "photo", "food", "audience", "tips", "stay", "around", "history", "source"];

  function fieldOrder() {
    return (data && data.strings && data.strings.field_order) || FIELD_ORDER;
  }

  /* ---------------- 意图规则（与 intent_parser.py 同序同位） ---------------- */
  var INTENT_RULES = [
    ["source", ["来源网址", "来源", "出处", "网址", "官网", "链接", "공식홈페이지", "출처", "공식사이트", "공식 사이트",
                "source", "website", "official site", "official", "link", "url"]],
    ["transport", ["怎么去", "怎么走", "如何去", "怎么到达", "怎么过去", "坐地铁", "地铁", "公交", "巴士",
                   "公交巴士", "打车", "停车", "地铁几号线", "哪个出口", "几号口", "怎么坐车", "怎么坐",
                   "교통", "가는법", "가는 법", "지하철", "버스", "어떻게 가요", "몇 호선", "몇 번 출구",
                   "transportation", "transport", "how to get", "how do i get", "how do i go",
                   "get to", "go to", "getting there", "subway", "bus", "which exit", "which line",
                   "access", "direction", "directions"]],
    ["hours", ["开放时间", "开放信息", "营业时间", "运营时间", "几点开门", "几点关门", "几点闭馆", "几点",
               "开放", "开门", "关门", "开吗", "今天开吗", "现在开吗", "休馆", "休演", "휴관", "휴일",
               "개방시간", "운영시간", "개방", "운영 시간", "몇 시", "언제 열어요", "언제 닫아요",
               "opening hours", "when does", "opening", "hours", "open time", "open", "open today", "closed"]],
    ["ticket", ["多少钱", "门票", "票价", "收费", "免费吗", "要钱吗", "费用", "门票多少", "要不要钱",
                "입장료", "요금", "무료", "얼마예요",
                "ticket", "price", "fee", "cost", "admission", "free", "how much"]],
    ["photo", ["拍照", "出片", "打卡", "摄影", "拍照点", "机位", "哪里拍照", "사진", "포토", "촬영", "포토스팟",
               "photo", "picture", "instagram", "photo spot"]],
    ["food", ["美食", "吃什么", "餐厅", "好吃", "附近吃", "小吃", "맛집", "음식", "식당",
              "food", "restaurant", "eat", "where to eat"]],
    ["course", ["怎么玩", "游玩路线", "推荐路线", "游览路线", "行程", "路线", "安排", "半天", "一日",
                "玩多久", "玩多长时间", "建议玩多久", "추천 코스", "코스", "관람 코스", "얼마나 둘러봐요",
                "itinerary", "course", "route", "plan", "how to play", "how long"]],
    ["audience", ["适合人群", "适合谁", "什么人", "带小孩", "带孩子", "婴儿车", "轮椅", "적합", "추천 대상",
                  "suitable", "best for", "who should", "stroller", "wheelchair"]],
    ["tips", ["注意", "贴士", "建议", "准备", "穿什么", "注意什么", "要注意", "주의", "팁", "유의사항",
              "tip", "advice", "note", "prepare", "what to know"]],
    ["stay", ["住宿", "住哪", "酒店", "숙소", "호텔", "hotel", "stay", "accommodation"]],
    ["around", ["周边", "附近", "旁边", "周边景点", "주변", "근처", "nearby", "around", "near"]],
    ["history", ["历史", "由来", "背景", "为什么叫", "历史背景", "역사", "유래", "유래가",
                 "history", "background", "origin"]],
    ["highlights", ["亮点", "看点", "必看", "玩什么", "必去", "주요 볼거리", "볼거리", "하이라이트",
                    "highlights", "highlight", "must see", "best part", "what to see"]],
    ["overview", ["介绍", "简介", "概况", "详情", "详细", "什么样", "是什么", "怎么样", "好玩吗",
                  "有什么好玩的", "有什么好看的", "소개", "개요", "어때", "어떤 곳",
                  "about", "overview", "introduction", "introduce", "what is", "tell me about", "info"]],
  ];

  var CATEGORY_KEYWORDS = {
    "01_艺术村落_文化街区": ["艺术", "村落", "文化村", "文化街区", "小巷", "涂鸦", "壁画", "文创", "街拍",
      "예술", "마을", "문화마을", "골목", "벽화", "그림", "art", "village", "culture", "alley", "mural", "craft"],
    "02_海岸休闲_日落夜景": ["海岸", "海边", "沙滩", "海水浴场", "海滩", "日落", "夜景", "喷泉", "看海", "踏浪",
      "해안", "바다", "해변", "해수욕장", "일몰", "노을", "야경", "분수",
      "coast", "beach", "seaside", "sunset", "night view", "fountain", "sea"],
    "03_湿地生态_自然观景": ["湿地", "生态", "候鸟", "鸟", "芦苇", "观景台", "自然", "河口", "滩涂", "观鸟",
      "습지", "생태", "철새", "갈대", "전망대", "자연", "강하구", "갯벌",
      "wetland", "ecology", "bird", "birdwatching", "reed", "nature", "lookout", "estuary"],
    "04_小众渔港_文艺拍照": ["渔港", "港口", "码头", "浦口", "小众", "拍照", "文艺", "渔市",
      "어항", "포구", "항구", "부두", "사진", "감성", "port", "harbor", "fishing port", "photo", "fishing village"],
  };

  var GROUP_KEYWORDS = {
    "two_mf": ["情侣", "夫妻", "约会", "男女", "恋人", "对象", "커플", "남녀", "연인", "데이트",
               "couple", "boyfriend", "girlfriend", "date", "partner", "romantic"],
    "two_mm": ["两个男生", "男男", "哥们", "兄弟俩", "两位男士", "남성 둘", "남자 둘", "친구 둘",
               "two guys", "male friends", "two men", "buddies"],
    "two_ff": ["两个女生", "闺蜜", "女女", "姐妹俩", "两位女士", "여성 둘", "여자 둘", "친구 둘",
               "two girls", "female friends", "two women", "besties", "girlfriends"],
    "group_3plus": ["三人", "四个人", "一家", "家庭", "全家", "朋友一群", "团体", "多人", "亲子", "孩子们",
                    "3인", "가족", "단체", "여럿", "아이들",
                    "family", "group", "three people", "four people", "kids", "children", "together"],
  };

  var SOLO_WORDS = ["一个人", "独自", "单人", "一人", "独游", "혼자", "나 홀로", "solo", "alone", "by myself"];
  var MALE_WORDS = ["男", "男生", "男性", "남", "male", "guy", "man"];
  var FEMALE_WORDS = ["女", "女生", "女性", "여", "female", "girl", "woman"];

  var STOPWORDS = ("的 了 是 在 我 你 他 她 它 们 请 想 要 问 一下 请问 帮我 告诉 知道 吗 呢 啊 呀 吧 哦 嗯 哈 " +
    "关于 对于 这个 那个 这里 那里 有 没有 可以 能 会 很 太 非常 就 都 也 还 再 又 和 与 或 及 " +
    "谢谢 感谢 麻烦 你好 您好 hi hello 给我 我想 我想要 谁能 谁可以 " +
    "은 는 이 가 을 를 의 에 에서 로 으로 와 과 도 만 까지 부터 요 죠 네요 네 다 " +
    "the a an is are was were do does did i you he she it we they my your this that there here " +
    "about please tell me can could would should what when where who how why").split(/\s+/);

  /* ---------------- 本地化文案 ---------------- */
  var T = {
    zh: {
      noSpot: "没有在当前玩法库里找到这个景点。可以换一种说法，或点上方的玩法 / 景点名试试（例如「没云台」）。",
      outsideCat: "「{name}」属于「{cat}」，不在当前所选玩法里。点上方「{cat}」即可切过去再问。",
      emptyQ: "想了解哪个景点？直接打景点名，或问「怎么去 / 门票 / 开放时间」。",
      suppTitle: "其它玩法补充推荐（主推荐之后）",
      suppReason: "与当前所选玩法节奏不同，可作为主推荐之后的延伸安排；{group} 前往也合适。",
      anyTraveler: "各类出行者",
      nearbyTitle: "附近景点（按直线距离）",
      nearbyNone: "定位不可用：请在系统设置里允许定位，或直接问某个景点。",
      nearbyEmpty: "附近 15 公里内没有收录的景点。",
      km: "公里",
      listTitle: "「{cat}」收录景点",
      listMore: "想细问哪一个？直接打景点名即可。",
      noField: "这个景点暂未收录该项资料。",
      welcome: "你好，我是釜山旅行助手。全部资料已内置在安装包里，不联网也能问。\n试试：没云台 日落 / 甘川文化村 怎么去 / 多大浦 门票",
      offline: "离线数据库",
    },
    ko: {
      noSpot: "현재 테마 데이터에서 이 명소를 찾지 못했습니다. 명소 이름을 직접 입력하거나 상단에서 테마를 바꿔 보세요.",
      outsideCat: "「{name}」은(는) 「{cat}」 테마에 속합니다. 상단의 「{cat}」를 눌러 전환한 뒤 질문해 주세요.",
      emptyQ: "어느 명소가 궁금하신가요? 명소 이름을 입력하거나 「가는 법 / 입장료 / 운영 시간」을 물어보세요.",
      suppTitle: "다른 테마 추가 추천 (주 추천 이후)",
      suppReason: "현재 테마와는 다른 분위기로, 주 추천 이후의 연장 코스로 적합합니다. {group} 방문도 무난합니다.",
      anyTraveler: "누구나",
      nearbyTitle: "주변 명소 (직선거리 순)",
      nearbyNone: "위치를 사용할 수 없습니다. 설정에서 위치를 허용하거나 명소 이름을 직접 질문해 주세요.",
      nearbyEmpty: "15km 이내에 수록된 명소가 없습니다.",
      km: "km",
      listTitle: "「{cat}」 수록 명소",
      listMore: "더 자세히 알고 싶은 명소 이름을 입력해 주세요.",
      noField: "이 항목의 자료는 아직 수록되지 않았습니다.",
      welcome: "안녕하세요, 부산 여행 도우미입니다. 모든 자료가 앱에 내장되어 있어 인터넷 없이도 질문할 수 있습니다.\n예시: 몰운대 일몰 / 감천문화마을 가는 법 / 다대포 입장료",
      offline: "오프라인 데이터베이스",
    },
    en: {
      noSpot: "I could not find that spot in the selected theme. Try another name, or pick a theme above.",
      outsideCat: "“{name}” belongs to “{cat}”, which is not the theme you selected. Tap “{cat}” above to switch.",
      emptyQ: "Which spot do you want to know about? Type a spot name, or ask “how to get there / tickets / hours”.",
      suppTitle: "More picks from other themes (after the main list)",
      suppReason: "A different vibe from the chosen theme; suitable as an extension after the main picks. Good for {group}.",
      anyTraveler: "any traveler",
      nearbyTitle: "Nearby spots (by straight-line distance)",
      nearbyNone: "Location unavailable. Allow location in system settings, or just ask about a spot by name.",
      nearbyEmpty: "No listed spots within 15 km.",
      km: "km",
      listTitle: "Spots in “{cat}”",
      listMore: "Type a spot name to get details.",
      noField: "This field is not covered for this spot yet.",
      welcome: "Hi, I am your Busan travel assistant. Everything is bundled in the app, so it works offline.\nTry: Molundae sunset / Gamcheon how to get there / Dadaepo tickets",
      offline: "Offline database",
    },
  };

  var QUESTION_TEMPLATES = {
    overview: { zh: "{name} 是什么样的地方？", ko: "{name} 어떤 곳인가요?", en: "What is {name} like?" },
    transport: { zh: "{name} 怎么去？", ko: "{name} 어떻게 가나요?", en: "How do I get to {name}?" },
    hours: { zh: "{name} 的开放时间是？", ko: "{name} 개방 시간은 언제인가요?", en: "What are the opening hours of {name}?" },
    ticket: { zh: "{name} 需要门票吗？", ko: "{name} 입장료가 있나요?", en: "Is there an entrance fee for {name}?" },
    course: { zh: "{name} 怎么玩最合适？", ko: "{name} 어떻게 즐기는 게 좋을까요?", en: "What's the best way to enjoy {name}?" },
    photo: { zh: "{name} 有哪些拍照打卡点？", ko: "{name} 사진 명소는 어디인가요?", en: "Where are the best photo spots in {name}?" },
    food: { zh: "{name} 附近有什么美食？", ko: "{name} 근처 맛집은 어디인가요?", en: "Any good food near {name}?" },
    tips: { zh: "去 {name} 需要注意什么？", ko: "{name} 방문 시 주의할 점은?", en: "What should I know before visiting {name}?" },
    source: { zh: "{name} 的官方网址是什么？", ko: "{name} 공식 사이트 주소는?", en: "What is the official website of {name}?" },
    audience: { zh: "{name} 适合什么人去？", ko: "{name} 누구에게 적합한가요?", en: "Who is {name} best for?" },
    around: { zh: "{name} 附近还有什么景点？", ko: "{name} 근처에 다른 명소가 있나요?", en: "What else is near {name}?" },
    stay: { zh: "{name} 附近住哪里方便？", ko: "{name} 근처 숙소는 어디가 좋나요?", en: "Where to stay near {name}?" },
    history: { zh: "{name} 的历史由来是什么？", ko: "{name}의 역사와 유래는?", en: "What is the history of {name}?" },
  };
  var NEXT_ORDER = ["transport", "hours", "ticket", "course", "photo", "food", "tips", "source", "overview"];

  /* ---------------- 状态 ---------------- */
  var data = null;
  var state = {
    lang: "zh",
    category: null,      // 当前玩法（唯一主数据源）
    group: null,         // 当前出行人数
    autoCategory: true,  // true=随提问联动；false=用户手动锁定
    autoGroup: true,
  };

  function byCategory(cat) {
    return (data.spots || []).filter(function (s) { return s.category === cat; });
  }

  function displayName(spot, lang) {
    if (!spot) return "";
    if (lang === "ko" && spot.name_ko) return spot.name_ko;
    if (lang === "en" && spot.name_en) return spot.name_en;
    return spot.name;
  }

  function catLabel(cat, lang) {
    var t = data && data.strings && data.strings.categories[cat];
    return (t && t[lang]) || cat;
  }

  function groupLabel(g, lang) {
    if (!g) return T[lang].anyTraveler;
    var t = data && data.strings && data.strings.groups[g];
    return (t && t[lang]) || g;
  }

  function fieldLabel(f, lang) {
    var t = data && data.strings && data.strings.field_labels[f];
    return (t && t[lang]) || f;
  }

  function hits(q, words) {
    var n = 0;
    for (var i = 0; i < words.length; i++) {
      var w = words[i];
      if (w && q.indexOf(String(w).toLowerCase()) !== -1) n++;
    }
    return n;
  }

  function detectField(q) {
    var low = String(q || "").toLowerCase();
    for (var i = 0; i < INTENT_RULES.length; i++) {
      var words = INTENT_RULES[i][1].slice().sort(function (a, b) { return b.length - a.length; });
      for (var j = 0; j < words.length; j++) {
        if (low.indexOf(String(words[j]).toLowerCase()) !== -1) return INTENT_RULES[i][0];
      }
    }
    return null;
  }

  function inferCategory(q, spotHint) {
    if (spotHint) return spotHint;
    var best = null, bestScore = 0;
    for (var cat in CATEGORY_KEYWORDS) {
      var s = hits(String(q || "").toLowerCase(), CATEGORY_KEYWORDS[cat]);
      if (s > bestScore) { best = cat; bestScore = s; }
    }
    return bestScore >= 1 ? best : null;
  }

  function inferGroup(q) {
    var low = String(q || "").toLowerCase();
    var best = null, bestScore = 0;
    for (var g in GROUP_KEYWORDS) {
      var s = hits(low, GROUP_KEYWORDS[g]);
      if (s > bestScore) { best = g; bestScore = s; }
    }
    if (bestScore >= 1) return best;
    if (hits(low, SOLO_WORDS) >= 1) {
      if (hits(low, FEMALE_WORDS) >= 1) return "solo_female";
      if (hits(low, MALE_WORDS) >= 1) return "solo_male";
    }
    return null;
  }

  function matchSpot(q, scopeCat) {
    var low = String(q || "").toLowerCase();
    var pool = scopeCat ? byCategory(scopeCat) : (data.spots || []);
    var best = null, bestLen = 0;
    for (var i = 0; i < pool.length; i++) {
      var s = pool[i];
      for (var a = 0; a < s.aliases.length; a++) {
        var alias = String(s.aliases[a]).toLowerCase();
        if (alias && alias.length >= 2 && low.indexOf(alias) !== -1 && alias.length > bestLen) {
          best = s; bestLen = alias.length;
        }
      }
    }
    return best;
  }

  function matchSpotAnywhere(q) {
    var low = String(q || "").toLowerCase();
    var best = null, bestLen = 0;
    (data.spots || []).forEach(function (s) {
      s.aliases.forEach(function (alias) {
        var al = String(alias).toLowerCase();
        if (al && al.length >= 2 && low.indexOf(al) !== -1 && al.length > bestLen) {
          best = s; bestLen = al.length;
        }
      });
    });
    return best;
  }

  function isOnlySpotName(q, spot) {
    if (!spot) return false;
    var rest = String(q || "");
    spot.aliases.forEach(function (a) { rest = rest.split(a).join(" "); });
    rest = rest.replace(/[，。！？、；：“”‘’（）()\[\]【】《》,.!?;:'"~/|]/g, " ")
               .replace(/\s+/g, " ").trim().toLowerCase();
    var words = rest.length ? rest.split(" ") : [];
    for (var i = 0; i < words.length; i++) {
      if (words[i] && STOPWORDS.indexOf(words[i]) === -1) return false;
    }
    return true;
  }

  function crossSupplements(cat, lang, limit) {
    limit = limit || 2;
    var others = Object.keys(data.strings.categories).filter(function (c) { return c !== cat; });
    var pools = {};
    others.forEach(function (c) { pools[c] = byCategory(c); });
    var out = [], idx = 0;
    while (out.length < limit) {
      var progressed = false;
      for (var i = 0; i < others.length; i++) {
        var c = others[i];
        if (idx < pools[c].length) {
          out.push(pools[c][idx]);
          progressed = true;
          if (out.length >= limit) break;
        }
      }
      if (!progressed) break;
      idx += 1;
    }
    return out.map(function (s) {
      return {
        spot: s,
        name: displayName(s, lang),
        cat: s.category,
        catLabel: catLabel(s.category, lang),
        reason: T[lang].suppReason.replace("{group}", groupLabel(state.group, lang)),
      };
    });
  }

  function suggestQuestions(spot, field, lang) {
    var picks = [];
    var avail = spot ? Object.keys(spot.fields[lang] || spot.fields.zh || {}) : [];
    for (var i = 0; i < NEXT_ORDER.length; i++) {
      var f = NEXT_ORDER[i];
      if (f === field) continue;
      if (avail.length && avail.indexOf(f) === -1) continue;
      picks.push(f);
      if (picks.length === 3) break;
    }
    if (!picks.length) picks = ["transport", "hours", "ticket"];
    var name = displayName(spot, lang);
    return picks.map(function (f) {
      return (QUESTION_TEMPLATES[f][lang] || QUESTION_TEMPLATES[f].zh).replace("{name}", name);
    });
  }

  function fieldText(spot, f, lang) {
    var fields = spot.fields[lang] || {};
    var v = fields[f] || (spot.fields.zh ? spot.fields.zh[f] : "");
    if (!v && f === "audience" && data.audience[spot.category]) {
      var a = data.audience[spot.category][lang] || data.audience[spot.category].zh || "";
      return a.replace(/^.*适合人群[：:]\s*/m, "").trim();
    }
    return v || "";
  }

  /* ---------------- 主入口 ---------------- */
  function answer(question, opts) {
    opts = opts || {};
    var q = String(question || "").trim();
    var lang = opts.lang || state.lang || "zh";

    if (opts.category !== undefined) state.category = opts.category || null;
    if (opts.group !== undefined) state.group = opts.group || null;
    if (opts.autoCategory !== undefined) state.autoCategory = !!opts.autoCategory;
    if (opts.autoGroup !== undefined) state.autoGroup = !!opts.autoGroup;

    if (!q) {
      return { text: T[lang].emptyQ, followups: [], spot: null, field: null,
               category: state.category, group: state.group, supplements: [], sources: [] };
    }

    var anywhere = matchSpotAnywhere(q);
    var field = detectField(q);

    // 自动模式：提问里的景点 / 关键词决定当前玩法
    if (state.autoCategory) {
      var inferredCat = inferCategory(q, anywhere ? anywhere.category : null);
      if (inferredCat) state.category = inferredCat;
    }
    if (state.autoGroup) {
      var inferredGroup = inferGroup(q);
      if (inferredGroup) state.group = inferredGroup;
    }

    var scope = state.category;
    var spot = matchSpot(q, scope);

    // 手动锁定了别的玩法，而问题指向当前玩法之外的景点：给出切换提示，不越界作答
    if (!spot && anywhere && scope && anywhere.category !== scope) {
      var txt = T[lang].outsideCat
        .replace("{name}", displayName(anywhere, lang))
        .replace("{cat}", catLabel(anywhere.category, lang));
      return {
        text: txt, followups: [], spot: null, field: field, category: scope,
        group: state.group, supplements: [], sources: [],
        switchTo: anywhere.category,
      };
    }

    if (!spot) {
      var pool = scope ? byCategory(scope) : [];
      if (pool.length) {
        var lines = ["**" + T[lang].listTitle.replace("{cat}", catLabel(scope, lang)) + "**"];
        pool.slice(0, 6).forEach(function (s) {
          var hi = fieldText(s, "overview", lang) || fieldText(s, "course", lang);
          var first = (hi || "").split(/\n/).filter(function (x) { return x.trim(); })[0] || "";
          lines.push("- **" + displayName(s, lang) + "**" + (first ? "：" + first.trim() : ""));
        });
        lines.push("\n" + T[lang].listMore);
        return {
          text: lines.join("\n"), followups: [], spot: null, field: field,
          category: scope, group: state.group, supplements: [], sources: [T[lang].offline],
        };
      }
      return { text: T[lang].noSpot, followups: [], spot: null, field: field,
               category: scope, group: state.group, supplements: [], sources: [] };
    }

    var name = displayName(spot, lang);
    var sections = [];
    var asked = field && !isOnlySpotName(q, spot) ? field : null;
    var usedFields = [];

    if (asked) {
      var body = fieldText(spot, asked, lang);
      if (body) {
        sections.push("**" + fieldLabel(asked, lang) + "**\n" + body);
        usedFields = [asked];
      } else {
        sections.push("**" + fieldLabel(asked, lang) + "**\n" + T[lang].noField);
      }
    } else {
      fieldOrder().forEach(function (f) {
        var body = fieldText(spot, f, lang);
        if (body) {
          sections.push("**" + fieldLabel(f, lang) + "**\n" + body);
          usedFields.push(f);
        }
      });
    }

    var head = "### " + name + " · " + catLabel(spot.category, lang);
    var supp = crossSupplements(spot.category, lang, 2);
    var text = head + "\n\n" + sections.join("\n\n");

    if (supp.length) {
      var sLines = ["---", "**" + T[lang].suppTitle + "**"];
      var open = lang === "zh" ? "（" : " (";
      var close = lang === "zh" ? "）" : ")";
      supp.forEach(function (s) {
        sLines.push("- **" + s.name + "**" + open + s.catLabel + close + "\n  " + s.reason);
      });
      text += "\n\n" + sLines.join("\n");
    }

    return {
      text: text,
      followups: suggestQuestions(spot, asked, lang),
      spot: spot,
      field: asked,
      category: spot.category,
      group: state.group,
      supplements: supp,
      sources: [T[lang].offline + "：" + catLabel(spot.category, lang)],
    };
  }

  function distanceKm(lat1, lng1, lat2, lng2) {
    var R = 6371, toRad = Math.PI / 180;
    var dLat = (lat2 - lat1) * toRad, dLng = (lng2 - lng1) * toRad;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * toRad) * Math.cos(lat2 * toRad) *
            Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return 2 * R * Math.asin(Math.sqrt(a));
  }

  function nearby(lat, lng, limit) {
    limit = limit || 5;
    return (data.spots || [])
      .filter(function (s) { return s.lat && s.lng; })
      .map(function (s) { return { spot: s, km: distanceKm(lat, lng, s.lat, s.lng) }; })
      .filter(function (x) { return x.km <= 15; })
      .sort(function (a, b) { return a.km - b.km; })
      .slice(0, limit);
  }

  function init(payload) {
    data = payload;
    if (!state.category) state.category = Object.keys(data.strings.categories)[0] || null;
    return state;
  }

  function setLang(lang) { if (LANGS.indexOf(lang) !== -1) state.lang = lang; return state.lang; }

  return {
    init: init,
    answer: answer,
    nearby: nearby,
    setLang: setLang,
    displayName: displayName,
    catLabel: catLabel,
    groupLabel: groupLabel,
    fieldLabel: fieldLabel,
    detectField: detectField,
    inferCategory: inferCategory,
    inferGroup: inferGroup,
    matchSpot: matchSpot,
    getState: function () { return JSON.parse(JSON.stringify(state)); },
    setState: function (patch) { Object.keys(patch).forEach(function (k) { state[k] = patch[k]; }); return state; },
    strings: T,
  };
});
