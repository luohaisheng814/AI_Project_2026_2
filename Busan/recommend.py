# -*- coding: utf-8 -*-

import intent_parser as IP

# ---------------- 出行人数 -> 推荐策略 ----------------
GROUP_STRATEGY = {
    "solo_male": {
        "zh": "独自出行的男性：优先给高效路线（少走回头路）、拍照机位、一个人也能吃的简餐与咖啡馆，"
              "并提醒末班交通与夜归安全。",
        "ko": "혼자 여행하는 남성: 효율적인 동선(되돌아가지 않는 코스), 사진 포인트, "
              "혼자서도 가능한 식사·카페를 우선 안내하고, 막차와 야간 귀가 안전을 함께 안내.",
        "en": "Solo male traveler: prioritize an efficient one-way route, photo spots, "
              "solo-friendly meals and cafés, and note last trains plus night-return safety.",
    },
    "solo_female": {
        "zh": "独自出行的女性：重点给安全提示、白天时段安排、照明与人流充足的路线、"
              "适合一人拍照与休息的咖啡馆，避免偏僻小巷与夜间独行。",
        "ko": "혼자 여행하는 여성: 안전 팁, 낮 시간대 일정, 조명과 유동 인구가 충분한 동선, "
              "혼자 사진 찍기 좋고 쉴 수 있는 카페를 안내하고, 외진 골목과 야간 단독 이동은 피하도록 안내.",
        "en": "Solo female traveler: emphasize safety tips, daytime scheduling, well-lit busy routes, "
              "and cafés comfortable for one person; avoid isolated alleys and walking alone at night.",
    },
    "two_mf": {
        "zh": "情侣/异性两人：偏浪漫节奏，安排日落与夜景时段、合影机位、氛围感咖啡馆与晚餐，"
              "标注适合并肩散步的路线与停留时长。",
        "ko": "커플(남녀 2인): 일몰·야경 시간대, 함께 찍기 좋은 포토존, 분위기 좋은 카페와 저녁 식사, "
              "나란히 걷기 좋은 동선과 체류 시간을 안내.",
        "en": "Couples: build a romantic pace — sunset and night views, photo spots for two, "
              "atmospheric cafés and dinner, with walkable routes and suggested dwell time.",
    },
    "two_mm": {
        "zh": "男性两人：偏效率与性价比，主打动线紧凑、啤酒小吃、运动与打卡类体验，压缩排队时间。",
        "ko": "남성 2인: 효율과 가성비 중심, 동선은 짧게, 맥주와 간단한 안주, 활동적인 체험 위주로 구성하고 대기 시간은 줄이기.",
        "en": "Two male friends: keep it efficient and good-value — a tight route, beer and street food, "
              "active experiences, minimal queuing.",
    },
    "two_ff": {
        "zh": "女性两人：偏出片与慢节奏，安排咖啡馆、甜品、文创小店与拍照点，标注排队热度与最佳光线时段。",
        "ko": "여성 2인: 사진과 여유로운 동선 중심, 카페·디저트·소품숍·포토존을 배치하고 "
              "대기 정도와 빛이 좋은 시간대를 안내.",
        "en": "Two female friends: photo-friendly and relaxed — cafés, desserts, concept shops and photo spots, "
              "with queue levels and best-light timings.",
    },
    "group_3plus": {
        "zh": "三人及以上：强调集合点、分批活动、适合团体的餐位与卫生间/休息点，路线留弹性并控制总时长。",
        "ko": "3인 이상: 집결 지점, 소그룹 분산 활동, 단체 식사가 가능한 곳, 화장실·휴식 지점을 안내하고 "
              "일정은 유연하게, 총 소요 시간은 관리.",
        "en": "Groups of 3+: set clear meeting points, allow split activities, group-friendly restaurants, "
              "restrooms and rest stops; keep the plan flexible and total time under control.",
    },
}

# ---------------- 玩法分类 -> 答案呈现骨架 ----------------
CATEGORY_STYLE = {
    "01_艺术村落_文化街区": {
        "zh": "答案按「漫步路线」组织：入口 → 主巷打卡点 → 观景台 → 咖啡馆收尾，"
              "每段标注步行分钟数与拍照提示；坡道多，提醒穿好走的鞋。",
        "ko": "답변은 '산책 코스'로 구성: 입구 → 주요 골목 포토존 → 전망대 → 카페 마무리. "
              "구간별 도보 시간과 촬영 팁을 표시하고, 오르막이 많으니 편한 신발을 안내.",
        "en": "Structure the answer as a walking route: entrance → alley photo spots → lookout → café finish, "
              "with walking minutes and photo tips per section; note the steep slopes and good shoes.",
    },
    "02_海岸休闲_日落夜景": {
        "zh": "答案按「时间轴」组织：抵达 → 海边散步 → 日落机位（提前 40 分钟占位）→ 夜间演出/喷泉 → 返程交通，"
              "标注日落时间与末班车。",
        "ko": "답변은 '타임라인'으로 구성: 도착 → 해변 산책 → 일몰 포인트(40분 전 자리 확보) → 야간 공연/분수 → 귀가 교통. "
              "일몰 시각과 막차를 함께 안내.",
        "en": "Structure the answer as a timeline: arrival → beach walk → sunset spot (arrive 40 min early) → "
              "night show/fountain → return transport, with sunset time and last train.",
    },
    "03_湿地生态_自然观景": {
        "zh": "答案按「观察点」组织：观景台 → 芦苇/滩涂步道 → 候鸟最佳时段，"
              "标注季节、潮汐与望远镜/长焦建议，强调轻声与不惊扰。",
        "ko": "답변은 '관찰 포인트'로 구성: 전망대 → 갈대/갯벌 산책로 → 철새 관찰 최적 시간. "
              "계절·물때·망원경/망원 렌즈를 안내하고 조용히 관찰할 것을 강조.",
        "en": "Structure the answer by observation points: lookout → reed/mudflat trail → best birdwatching window, "
              "with season, tide, and lens advice; emphasize quiet, non-disturbing behavior.",
    },
    "04_小众渔港_文艺拍照": {
        "zh": "答案按「拍照清单」组织：机位 1/2/3（含最佳光线时段与构图建议）→ 海鲜餐 → 返程，人少清静，适合慢拍。",
        "ko": "답변은 '촬영 리스트'로 구성: 포토존 1/2/3(빛 좋은 시간대와 구도 팁) → 해산물 식사 → 귀가. "
              "한적하니 여유로운 촬영에 적합.",
        "en": "Structure the answer as a shot list: spot 1/2/3 with best light and composition → seafood meal → "
              "return; it is quiet and good for slow photography.",
    },
}


def build_profile_text(category, group_type, lang):
    """注入 Prompt 的「玩法骨架 + 人数策略」文本。"""
    parts = [
        CATEGORY_STYLE.get(category, {}).get(lang, ""),
        GROUP_STRATEGY.get(group_type, {}).get(lang, ""),
    ]
    return "\n".join([p for p in parts if p])


# ---------------- 预测下一个问题 ----------------
QUESTION_TEMPLATES = {
    "overview":  {"zh": "{name} 是什么样的地方？", "ko": "{name} 어떤 곳인가요?", "en": "What is {name} like?"},
    "transport": {"zh": "{name} 怎么去？", "ko": "{name} 어떻게 가나요?", "en": "How do I get to {name}?"},
    "hours":     {"zh": "{name} 的开放时间是？", "ko": "{name} 개방 시간은 언제인가요?",
                  "en": "What are the opening hours of {name}?"},
    "ticket":    {"zh": "{name} 需要门票吗？", "ko": "{name} 입장료가 있나요?",
                  "en": "Is there an entrance fee for {name}?"},
    "course":    {"zh": "{name} 怎么玩最合适？", "ko": "{name} 어떻게 즐기는 게 좋을까요?",
                  "en": "What's the best way to enjoy {name}?"},
    "photo":     {"zh": "{name} 有哪些拍照打卡点？", "ko": "{name} 사진 명소는 어디인가요?",
                  "en": "Where are the best photo spots in {name}?"},
    "food":      {"zh": "{name} 附近有什么美食？", "ko": "{name} 근처 맛집은 어디인가요?",
                  "en": "Any good food near {name}?"},
    "tips":      {"zh": "去 {name} 需要注意什么？", "ko": "{name} 방문 시 주의할 점은?",
                  "en": "What should I know before visiting {name}?"},
    "source":    {"zh": "{name} 的官方网址是什么？", "ko": "{name} 공식 사이트 주소는?",
                  "en": "What is the official website of {name}?"},
    "audience":  {"zh": "{name} 适合什么人去？", "ko": "{name} 누구에게 적합한가요?",
                  "en": "Who is {name} best for?"},
    "around":    {"zh": "{name} 附近还有什么景点？", "ko": "{name} 근처에 다른 명소가 있나요?",
                  "en": "What else is near {name}?"},
    "stay":      {"zh": "{name} 附近住哪里方便？", "ko": "{name} 근처 숙소는 어디가 좋나요?",
                  "en": "Where to stay near {name}?"},
    "history":   {"zh": "{name} 的历史由来是什么？", "ko": "{name}의 역사와 유래는?",
                  "en": "What is the history of {name}?"},
}

NEXT_ORDER = ["transport", "hours", "ticket", "course", "photo", "food", "tips", "source", "overview"]


def suggest_questions(spot_name, field, lang="zh", available_fields=None):
    """预测 3 个后续问题；没有的字段不预测，避免问出空答案。"""
    picks = []
    for f in NEXT_ORDER:
        if f == field:
            continue
        if available_fields and f not in available_fields:
            continue
        picks.append(f)
        if len(picks) == 3:
            break
    if not picks:
        picks = ["transport", "hours", "ticket"]

    out = []
    for f in picks:
        tpl = QUESTION_TEMPLATES.get(f, {}).get(lang, "{name} ?")
        q = tpl.replace("{name}", spot_name) if spot_name else tpl.replace("{name} ", "").replace("{name}", "")
        out.append(q.strip())
    return out