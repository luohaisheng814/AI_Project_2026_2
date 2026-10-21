# -*- coding: utf-8 -*-
"""
多语言模块：所有页面文案集中在一处，切换语言后整页刷新。
分类名、人数分组也在这里翻译。
"""

import config

LANGUAGES = {"zh": "中文", "ko": "한국어", "en": "English"}

# 语言 -> 注入 LLM 的输出语言指令
LLM_LANG_NAME = {"zh": "简体中文", "ko": "한국어(Korean)", "en": "English"}

STRINGS = {
    # ---------------- 通用 ----------------
    "app_name":            {"zh": "釜山 AI 旅行助手", "ko": "부산 AI 여행 도우미", "en": "Busan AI Travel Assistant"},
    "ok":                  {"zh": "确定", "ko": "확인", "en": "OK"},
    "cancel":              {"zh": "取消", "ko": "취소", "en": "Cancel"},
    "close":               {"zh": "关闭", "ko": "닫기", "en": "Close"},
    "refresh":             {"zh": "刷新", "ko": "새로고침", "en": "Refresh"},
    "refresh_captcha":     {"zh": "刷新验证码", "ko": "인증코드 새로고침", "en": "Refresh code"},
    "send":                {"zh": "发送", "ko": "전송", "en": "Send"},
    "clear":               {"zh": "清空", "ko": "지우기", "en": "Clear"},
    "back":                {"zh": "返回", "ko": "뒤로", "en": "Back"},
    "logout":              {"zh": "退出登录", "ko": "로그아웃", "en": "Log out"},
    "language":            {"zh": "语言", "ko": "언어", "en": "Language"},
    "error":               {"zh": "错误", "ko": "오류", "en": "Error"},
    "warning":             {"zh": "提示", "ko": "알림", "en": "Warning"},
    "success":             {"zh": "成功", "ko": "성공", "en": "Success"},
    "searching":           {"zh": "正在检索资料...", "ko": "자료를 검색하는 중...", "en": "Searching sources..."},
    "thinking":            {"zh": "AI 正在思考...", "ko": "AI가 생각하는 중...", "en": "AI is thinking..."},
    "please_select":       {"zh": "请先选择", "ko": "먼저 선택하세요", "en": "Please select"},

    # ---------------- 登录页 ----------------
    "login_title":         {"zh": "用户登录", "ko": "사용자 로그인", "en": "User Login"},
    "username":            {"zh": "用户名", "ko": "사용자 이름", "en": "Username"},
    "password":            {"zh": "密码", "ko": "비밀번호", "en": "Password"},
    "captcha":             {"zh": "验证码", "ko": "인증코드", "en": "Captcha"},
    "captcha_ph":          {"zh": "请输入右侧验证码", "ko": "오른쪽 인증코드 입력", "en": "Enter the code"},
    "login_btn":           {"zh": "登 录", "ko": "로그인", "en": "Log in"},
    "goto_register":       {"zh": "没有账号？立即注册", "ko": "계정이 없나요? 회원가입", "en": "No account? Register now"},
    "login_ok":            {"zh": "登录成功，正在进入主界面...", "ko": "로그인 성공, 메인 화면으로 이동합니다...", "en": "Login successful, loading main window..."},
    "login_fail":          {"zh": "用户名或密码错误", "ko": "사용자 이름 또는 비밀번호가 틀렸습니다", "en": "Incorrect username or password"},
    "user_not_found":      {"zh": "该用户不存在，请先注册", "ko": "존재하지 않는 사용자입니다. 먼저 회원가입하세요", "en": "User not found, please register first"},
    "captcha_wrong":       {"zh": "验证码错误", "ko": "인증코드가 틀렸습니다", "en": "Wrong captcha"},
    "empty_fields":        {"zh": "请填写完整信息", "ko": "모든 항목을 입력하세요", "en": "Please fill in all fields"},

    # ---------------- 注册页 ----------------
    "register_title":      {"zh": "用户注册", "ko": "회원가입", "en": "User Register"},
    "new_username":        {"zh": "新建用户名", "ko": "새 사용자 이름", "en": "New Username"},
    "new_password":        {"zh": "密码", "ko": "비밀번호", "en": "Password"},
    "confirm_password":    {"zh": "确认密码", "ko": "비밀번호 확인", "en": "Confirm Password"},
    "register_btn":        {"zh": "注 册", "ko": "회원가입", "en": "Register"},
    "back_to_login":       {"zh": "返回登录界面", "ko": "로그인 화면으로 돌아가기", "en": "Back to Login"},
    "pwd_mismatch":        {"zh": "两次输入的密码不一致", "ko": "비밀번호가 일치하지 않습니다", "en": "Passwords do not match"},
    "user_exists":         {"zh": "用户名已存在，请更换", "ko": "이미 존재하는 사용자 이름입니다", "en": "Username already exists"},
    "register_ok":         {"zh": "注册成功，请返回登录界面登录", "ko": "회원가입 성공, 로그인 화면으로 돌아가 로그인하세요", "en": "Registered successfully, please go back and log in"},
    "register_fail":       {"zh": "注册失败，请稍后重试", "ko": "회원가입 실패, 나중에 다시 시도하세요", "en": "Registration failed, please retry later"},
    "pwd_too_short":       {"zh": "密码长度至少 4 位", "ko": "비밀번호는 최소 4자리입니다", "en": "Password must be at least 4 characters"},

    # ---------------- 后台管理 ----------------
    "admin_login_title":   {"zh": "后台管理登录", "ko": "관리자 로그인", "en": "Admin Login"},
    "admin_account":       {"zh": "管理员账号", "ko": "관리자 계정", "en": "Admin Account"},
    "admin_password":      {"zh": "管理员密码", "ko": "관리자 비밀번호", "en": "Admin Password"},
    "admin_login_btn":     {"zh": "进入后台", "ko": "관리자 페이지 입장", "en": "Enter Admin Panel"},
    "admin_panel_title":   {"zh": "用户数据库后台管理", "ko": "사용자 데이터베이스 관리", "en": "User Database Admin Panel"},
    "admin_default_hint":  {"zh": "默认管理员账号/密码：admin / admin", "ko": "기본 관리자 계정/비밀번호: admin / admin", "en": "Default admin account/password: admin / admin"},
    "col_id":              {"zh": "ID", "ko": "ID", "en": "ID"},
    "col_username":        {"zh": "用户名", "ko": "사용자 이름", "en": "Username"},
    "col_password":        {"zh": "密码", "ko": "비밀번호", "en": "Password"},
    "col_role":            {"zh": "等级", "ko": "등급", "en": "Role"},
    "col_created":         {"zh": "注册时间", "ko": "가입 시간", "en": "Created At"},
    "col_action":          {"zh": "操作", "ko": "작업", "en": "Actions"},
    "col_logs":            {"zh": "查询次数", "ko": "질의 수", "en": "Queries"},
    "view_logs":           {"zh": "查看查询记录", "ko": "질의 기록 보기", "en": "View Query History"},
    "logs_title":          {"zh": "查询记录", "ko": "질의 기록", "en": "Query History"},
    "no_logs":             {"zh": "该用户暂无查询记录", "ko": "질의 기록이 없습니다", "en": "No query history for this user"},
    "db_path_label":       {"zh": "数据库", "ko": "데이터베이스", "en": "Database"},
    "role_user":           {"zh": "用户", "ko": "사용자", "en": "User"},
    "role_admin":          {"zh": "管理员", "ko": "관리자", "en": "Admin"},
    "set_as_user":         {"zh": "设为普通用户", "ko": "일반 사용자로 설정", "en": "Set as User"},
    "set_as_admin":        {"zh": "设为管理员", "ko": "관리자로 설정", "en": "Set as Admin"},
    "reset_pwd":           {"zh": "重置密码(123456)", "ko": "비밀번호 초기화(123456)", "en": "Reset Password(123456)"},
    "need_select_user":    {"zh": "请先在列表中选中一个用户", "ko": "목록에서 사용자를 선택하세요", "en": "Please select a user first"},
    "role_updated":        {"zh": "用户等级已更新", "ko": "사용자 등급이 변경되었습니다", "en": "User role updated"},
    "pwd_reset_done":      {"zh": "密码已重置为 123456", "ko": "비밀번호가 123456으로 초기화되었습니다", "en": "Password reset to 123456"},
    "admin_only":          {"zh": "该账号没有管理员权限", "ko": "관리자 권한이 없는 계정입니다", "en": "This account has no admin permission"},
    "user_count":          {"zh": "用户总数", "ko": "전체 사용자 수", "en": "Total users"},

    # ---------------- 主界面 / 桌面版 ----------------
    "main_title":          {"zh": "釜山 AI 智能问答", "ko": "부산 AI 질의응답", "en": "Busan AI Q&A"},
    "desktop_title":       {"zh": "釜山 AI 桌面版（问答模块测试）", "ko": "부산 AI 데스크톱 버전(질의응답 테스트)", "en": "Busan AI Desktop (Q&A Module Test)"},
    "nav_play":            {"zh": "玩法分类（四选一）", "ko": "테마 분류(택1)", "en": "Theme (choose one)"},
    "nav_people":          {"zh": "出行人数（选其一）", "ko": "인원 수(택1)", "en": "Group Size (choose one)"},
    "chat_welcome":        {"zh": "你好！请先选择左侧的「玩法」和「人数」，然后向我提问。\n例如：甘川文化村 / 甘川文化村 交通 / 甘川文化村 开放时间",
                            "ko": "안녕하세요! 왼쪽에서 '테마'와 '인원 수'를 선택한 뒤 질문해 주세요.\n예: 감천문화마을 / 감천문화마을 교통 / 감천문화마을 개방시간",
                            "en": "Hi! Please choose a theme and group size on the left, then ask me anything.\nE.g. Gamcheon Culture Village / transportation / opening hours"},
    "input_placeholder":   {"zh": "输入你的问题，回车或点击发送...", "ko": "질문을 입력하고 Enter 또는 전송을 누르세요...", "en": "Type your question, press Enter or Send..."},
    "need_theme":          {"zh": "请先在左侧选择一个玩法分类", "ko": "왼쪽에서 테마를 먼저 선택하세요", "en": "Please select a theme on the left first"},
    "current_selection":   {"zh": "当前选择", "ko": "현재 선택", "en": "Current"},
    "sources_label":       {"zh": "资料来源", "ko": "자료 출처", "en": "Sources"},
    "source_local":        {"zh": "本地分类资料库", "ko": "로컬 분류 자료", "en": "Local category database"},
    "source_core":         {"zh": "核心数据库 rules.txt", "ko": "핵심 데이터베이스 rules.txt", "en": "Core database rules.txt"},
    "source_profile":      {"zh": "重点景点档案", "ko": "주요 명소 아카이브", "en": "Spot Profile"},
    "source_web":          {"zh": "官网 / 百科在线查询", "ko": "공식 사이트 / 백과 온라인 조회", "en": "Official site / Encyclopedia (online)"},
    "suggest_label":       {"zh": "AI 预测你可能还想问", "ko": "AI가 예측한 다음 질문", "en": "You may also ask"},
    "no_result":           {"zh": "没有检索到相关资料，请换个说法再试试。", "ko": "관련 자료를 찾지 못했습니다. 다른 표현으로 질문해 보세요.", "en": "No relevant data found. Please try another wording."},
    "offline_mode":        {"zh": "（未配置 LLM_API_KEY，当前为本地检索直出模式）",
                            "ko": "(LLM_API_KEY 미설정, 로컬 검색 직접 출력 모드)",
                            "en": "(No LLM_API_KEY set, running in local retrieval mode)"},
    "web_failed":          {"zh": "在线查询未获取到内容（可能无网络或被目标站点拦截）",
                            "ko": "온라인 조회 실패(네트워크 없음 또는 사이트 차단)",
                            "en": "Online lookup returned nothing (offline or blocked)"},

    # ---------------- CLI ----------------
    "cli_title":           {"zh": "=== 釜山 AI 智能问答模块测试（命令行版 app.py）===",
                            "ko": "=== 부산 AI 질의응답 모듈 테스트(CLI app.py) ===",
                            "en": "=== Busan AI Q&A Module Test (CLI app.py) ==="},
    "cli_switch":          {"zh": "输入 /lang 切换语言，输入 /quit 退出",
                            "ko": "/lang 입력 시 언어 변경, /quit 입력 시 종료",
                            "en": "Type /lang to switch language, /quit to exit"},
    "cli_lang_menu":       {"zh": "选择语言：1) 中文  2) 한국어  3) English",
                            "ko": "언어 선택: 1) 中文  2) 한국어  3) English",
                            "en": "Select language: 1) 中文  2) 한국어  3) English"},
    "cli_ask":             {"zh": "请输入问题", "ko": "질문을 입력하세요", "en": "Your question"},
    "cli_bye":             {"zh": "已退出。", "ko": "종료되었습니다.", "en": "Bye."},

    # ---------------- 分类名 ----------------
    "cat_01":              {"zh": "01 艺术村落·文化街区", "ko": "01 예술마을·문화거리", "en": "01 Art Village · Cultural Streets"},
    "cat_02":              {"zh": "02 海岸休闲·日落夜景", "ko": "02 해안 휴식·일몰 야경", "en": "02 Coastal Leisure · Sunset"},
    "cat_03":              {"zh": "03 湿地生态·自然观景", "ko": "03 습지 생태·자연 전망", "en": "03 Wetland Ecology · Nature"},
    "cat_04":              {"zh": "04 小众渔港·文艺拍照", "ko": "04 이색 어항·감성 사진", "en": "04 Hidden Ports · Photo Spots"},

    # ---------------- 人数分组 ----------------
    "grp_solo_male":       {"zh": "一人（男）", "ko": "1인(남)", "en": "Solo (Male)"},
    "grp_solo_female":     {"zh": "一人（女）", "ko": "1인(여)", "en": "Solo (Female)"},
    "grp_two_mf":          {"zh": "两人（男女）", "ko": "2인(남녀)", "en": "Two (M&F)"},
    "grp_two_mm":          {"zh": "两人（男男）", "ko": "2인(남남)", "en": "Two (M&M)"},
    "grp_two_ff":          {"zh": "两人（女女）", "ko": "2인(여여)", "en": "Two (F&F)"},
    "grp_group_3plus":     {"zh": "三人及以上", "ko": "3인 이상", "en": "3 or More"},

    # ---------------- 其它 ----------------
    "welcome_user":        {"zh": "欢迎你", "ko": "환영합니다", "en": "Welcome"},
    "db_error":            {"zh": "数据库操作失败", "ko": "데이터베이스 오류", "en": "Database error"},
    "window_login":        {"zh": "登录", "ko": "로그인", "en": "Login"},
    "query_logged":        {"zh": "（本次查询已记录到你的用户档案）", "ko": "(이 질의는 사용자 기록에 저장되었습니다)", "en": "(This query was saved to your profile)"},
}

CATEGORY_KEYS = {
    "01_艺术村落_文化街区": "cat_01",
    "02_海岸休闲_日落夜景": "cat_02",
    "03_湿地生态_自然观景": "cat_03",
    "04_小众渔港_文艺拍照": "cat_04",
}
GROUP_KEYS = {g: "grp_" + g for g in config.GROUP_TYPES}


class I18N:
    """轻量翻译器：切换语言后调用页面 refresh_ui() 重绘全部文字。"""

    def __init__(self, lang=None):
        self.lang = lang or config.DEFAULT_LANG or "zh"
        if self.lang not in LANGUAGES:
            self.lang = "zh"
        self._listeners = []

    def set_lang(self, lang):
        if lang in LANGUAGES and lang != self.lang:
            self.lang = lang
            return True
        return False

    def cycle(self):
        """按钮循环切换：中文 -> 韩文 -> 英文 -> 中文"""
        idx = config.SUPPORTED_LANGS.index(self.lang)
        self.lang = config.SUPPORTED_LANGS[(idx + 1) % len(config.SUPPORTED_LANGS)]
        return self.lang

    @property
    def current_name(self):
        return LANGUAGES[self.lang]

    def t(self, key, **kwargs):
        item = STRINGS.get(key)
        if not item:
            return key
        text = item.get(self.lang) or item.get("zh") or key
        if kwargs:
            try:
                text = text.format(**kwargs)
            except Exception:
                pass
        return text

    def cat_name(self, folder_name):
        key = CATEGORY_KEYS.get(folder_name)
        return self.t(key) if key else folder_name

    def group_name(self, group_key):
        key = GROUP_KEYS.get(group_key)
        return self.t(key) if key else group_key

    # ---- 监听（页面注册刷新回调） ----
    def on_change(self, func):
        self._listeners.append(func)

    def notify(self):
        for f in list(self._listeners):
            try:
                f()
            except Exception:
                pass


# 全局单例：各模块共享同一语言状态
I = I18N()


def set_language(lang):
    I.set_lang(lang)
    I.notify()


def t(key, **kwargs):
    return I.t(key, **kwargs)