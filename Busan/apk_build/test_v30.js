/* 釜山 AI 旅行助手 v3.0 断言：
 *   A. 页头右上角新增昼夜切换按钮（结构 + 样式 + 反馈提示）
 *   B. 三态循环：自动 → 白天 → 夜间 → 自动，选择持久化、刷新后照旧
 *   C. 自动模式仍按手机本地时间（06:00–18:59 白天 / 19:00–05:59 夜间），每分钟与回到前台复判
 *   D. 三语标签、结论卡规则句同步说明“可手动切”
 *   E. 不回退：v2.9 折叠推荐条、v2.8 权限链路、v2.7 天气按钮、v2.6 偏好条
 *   F. 双端版本 / PWA 缓存同步到 3.0 / 23
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const A = path.join(ROOT, "android", "assets");
const html = fs.readFileSync(path.join(A, "index.html"), "utf8");
const sw = fs.readFileSync(path.join(A, "sw.js"), "utf8");
const apkMan = fs.readFileSync(path.join(ROOT, "android", "AndroidManifest.xml"), "utf8");
const native = fs.readFileSync(path.join(ROOT, "android", "java", "com", "busan", "tour", "MainActivity.java"), "utf8");
const iosYml = fs.readFileSync(path.join(ROOT, "ios", "project.yml"), "utf8");
const iosReadme = fs.readFileSync(path.join(ROOT, "ios", "README.md"), "utf8");
const pwaPy = fs.readFileSync(path.join(ROOT, "pwa", "build_pwa.py"), "utf8");

let pass = 0, fail = 0;
const failed = [];
function ok(name, cond, extra) {
  if (cond) pass++;
  else { fail++; failed.push(name + (extra ? " -> " + extra : "")); }
}
function css(sel) {
  const at = html.indexOf(sel + "{");
  if (at < 0) return "";
  const end = html.indexOf("}", at);
  return end < 0 ? "" : html.slice(at + sel.length, end);
}
function fn(name) {
  const at = html.indexOf("function " + name + "(");
  if (at < 0) return "";
  const end = html.indexOf("\n  }", at);
  return end < 0 ? html.slice(at) : html.slice(at, end);
}

/* ---------------- A. 结构 ---------------- */
ok("结构: 页头有 #themeBtn", /<button id="themeBtn" class="theme-btn" type="button" data-mode="auto" aria-label="自动昼夜">/.test(html));
ok("结构: 按钮里有图标位 #themeIcon", /<span id="themeIcon">🌓<\/span>/.test(html));
ok("结构: 按钮排在天气按钮左边（同一行 .brand）", /<\/div>\s*<button id="themeBtn"[\s\S]{0,160}<button id="wxFab"/.test(html));
ok("样式: 34×34 圆形按钮，达触控下限", /width:34px; height:34px/.test(css("  .theme-btn")) && /border-radius:50%/.test(css("  .theme-btn")));
ok("样式: 按钮靠上对齐（不把标题挤下去）", /align-self:flex-start/.test(css("  .theme-btn")));
ok("样式: 白天态浅黄底", /\.theme-btn\[data-mode="day"\]\{[\s\S]{0,90}#ffe9b8/.test(html));
ok("样式: 夜间态深底亮字", /\.theme-btn\[data-mode="night"\]\{[\s\S]{0,90}#12232d/.test(html));
ok("反馈: 页内有一次性提示 #themeToast", /<div class="ui-toast" id="themeToast" hidden><\/div>/.test(html));
ok("反馈: 提示浮在输入框上方、1.8 秒淡出", /\.ui-toast\{[\s\S]{0,200}bottom:86px/.test(html) && /transition:opacity \.18s/.test(css("  .ui-toast")));
ok("反馈: 提示不挡点击", /pointer-events:none/.test(css("  .ui-toast")));

/* ---------------- B. 三态循环 ---------------- */
ok("逻辑: 三态顺序 auto → day → night", /var THEME_ORDER = \["auto", "day", "night"\];/.test(html));
ok("逻辑: 默认 auto", /var themeMode = "auto";/.test(html));
ok("逻辑: 图标随状态变", /icon: "☀️"/.test(fn("themeMeta")) && /icon: "🌙"/.test(fn("themeMeta")) && /icon: "🌓"/.test(fn("themeMeta")));
ok("逻辑: 点一下按取模循环", /THEME_ORDER\.indexOf\(themeMode\)/.test(fn("cycleTheme")) && /% THEME_ORDER\.length/.test(fn("cycleTheme")));
ok("逻辑: 循环后写 localStorage.busan_theme", /localStorage\.setItem\("busan_theme", mode\)/.test(fn("setThemeMode")));
ok("逻辑: 非法值回落 auto", /THEME_ORDER\.indexOf\(mode\) < 0\) mode = "auto"/.test(fn("setThemeMode")));
ok("逻辑: 切换后重算配色 + 重画按钮", /applyDayNight\(\);[\s\S]{0,60}paintThemeBtn\(\);/.test(fn("setThemeMode")));
ok("逻辑: 按钮写 data-mode 供配色", /btn\.setAttribute\("data-mode", themeMode\)/.test(fn("paintThemeBtn")));
ok("逻辑: aria-pressed 跟随夜间态", /aria-pressed", themeMode === "night"/.test(fn("paintThemeBtn")));
ok("逻辑: aria-label 三语说明当前状态", /L\("昼夜：", "주야: ", "Theme: "\)/.test(fn("paintThemeBtn")));
ok("逻辑: 启动读回上次选择", /localStorage\.getItem\("busan_theme"\)/.test(fn("initDayNight")));
ok("逻辑: 启动绑定点击", /btn\.onclick = cycleTheme/.test(fn("initDayNight")));
ok("逻辑: 定时器与回到前台都会重画按钮", /setInterval\(function\(\)\{ applyDayNight\(\); paintThemeBtn\(\); \}, 60 \* 1000\)/.test(fn("initDayNight")));
ok("逻辑: 切语言后按钮文案跟着变", /paintPrefs\(\);[\s\S]{0,40}paintThemeBtn\(\);/.test(fn("applyUI")));
ok("接口: BusanUI 暴露 cycleTheme", /cycleTheme: cycleTheme,/.test(html));
ok("接口: BusanUI.setThemeMode 走同一实现", /setThemeMode: function\(mode\)\{ return setThemeMode\(mode, false\); \}/.test(html));
ok("接口: 对外仍可读当前模式", /themeMode: function\(\)\{ return themeMode; \}/.test(html));

/* ---------------- C. 自动模式与判定 ---------------- */
ok("判定: night 强制夜间", /if \(mode === "night"\) return true;/.test(fn("computeNight")));
ok("判定: day 强制白天", /if \(mode === "day"\) return false;/.test(fn("computeNight")));
ok("判定: auto 仍 19 点到 6 点", /return h >= 19 \|\| h < 6;/.test(fn("computeNight")));
ok("判定: 夜间态同时切 theme-color 两套", /night \? "#072e3c" : "#0a4e63"/.test(fn("applyDayNight")));
ok("判定: 手动模式下定时器不会覆盖（applyDayNight 只看 themeMode）", !/new Date\(\)\.getHours\(\)/.test(fn("applyDayNight")));

/* ---------------- D. 三语文案 ---------------- */
ok("文案: 自动/白天/夜间 三语", /zh: "白天", ko: "주간", en: "Day"/.test(fn("themeMeta")) && /zh: "夜间", ko: "야간", en: "Night"/.test(fn("themeMeta")));
ok("文案: 自动提示三语", /🌓 自动：仍按手机时间切昼夜/.test(html) && /🌓 자동: 휴대폰 시각 기준/.test(html));
ok("文案: 白天提示三语", /☀️ 已切到白天配色（手动）/.test(html) && /☀️ Daylight colours \(manual\)/.test(html));
ok("文案: 夜间提示三语", /🌙 已切到夜间配色（手动）/.test(html) && /🌙 Night colours \(manual\)/.test(html));
ok("文案: 结论卡说明可手动切，但仍保留时间规则", /06:00–18:59 白天，19:00–05:59 夜间；右上角按钮可手动切/.test(html));

/* ---------------- E. 不回退 ---------------- */
ok("不回退: 天气按钮仍在", /<button id="wxFab" class="wx-fab"/.test(html));
ok("不回退: 天气气泡第二行 #wxCtx", /id="wxCtx"/.test(html));
ok("不回退: 天气入口先权限卡", /wxPermissionCard/.test(html) && /mixFlow\("weather"\)/.test(html));
ok("不回退: 附近入口先权限卡", /mixPermissionCard\("nearby"\)/.test(html) && /mixFlow\("nearby"\)/.test(html));
ok("不回退: mix.js 引入", /<script src="mix\.js"><\/script>/.test(html));
ok("不回退: 个性化推荐条仍在", /<div class="qrec" id="qrec"/.test(html) && /function setQrec\(open\)/.test(html));
ok("不回退: 推荐条仍横滑", /flex-wrap:nowrap/.test(css("  .qrec-body .quick")));
ok("不回退: 偏好条可折叠", /id="prefsToggle"/.test(html) && /function setPrefs\(open/.test(html));
ok("不回退: 三语按钮", /data-lang="zh"/.test(html) && /data-lang="ko"/.test(html) && /data-lang="en"/.test(html));
ok("不回退: 附近按钮与规划按钮", /id="gps"/.test(html) && /id="planBtn"/.test(html));
ok("不回退: 夜间样式仍在（body.night 定义）", /body\.night\{[\s\S]{0,120}--sand:#0d1319/.test(html));
ok("不回退: SW 清单含 mix.js", /'\.\/mix\.js'/.test(sw));

/* ---------------- F. 版本 ---------------- */
ok("版本: APK 23 / 3.0", /android:versionCode="24"/.test(apkMan) && /android:versionName="3\.1"/.test(apkMan));
ok("版本: 无 22 / 2.9 残留", !/android:versionCode="22"/.test(apkMan) && !/android:versionName="2\.9"/.test(apkMan));
ok("版本: 原生 UA 3.0", /BusanTour\/3\.1 \(Android\)/.test(native) && !/BusanTour\/2\.9/.test(native));
ok("版本: 类注释 v3.0 且说明昼夜开关", /釜山 AI 旅行助手 v3\.1/.test(native) && /v3\.0 昼夜手动开关/.test(native));
ok("版本: iOS 3.0 / 23", /MARKETING_VERSION: "3\.1"/.test(iosYml) && /CURRENT_PROJECT_VERSION: "24"/.test(iosYml));
ok("版本: iOS README 同步 3.0", /（v3\.1）/.test(iosReadme));
ok("版本: PWA 缓存 busan-3.1", /const CACHE = 'busan-3\.1'/.test(sw));
ok("版本: 无 busan-2.9 残留", sw.indexOf("busan-2.9") === -1);
ok("版本: PWA 产物 v30", /Busan_Tour_WebApp_v30/.test(pwaPy) && /Busan_iOS_WebApp_v30\.zip/.test(pwaPy));
ok("版本: manifest 有 v3.0 说明块", /v3\.0：页头右上角新增昼夜切换按钮/.test(apkMan));

console.log("");
console.log("==== v3.0 结果 ====");
console.log("通过 " + pass + " / 失败 " + fail);
if (fail) {
  failed.forEach((f) => console.log("  ✗ " + f));
  console.log("v3.0 断言未通过");
  process.exit(1);
} else {
  console.log("v3.0 全部断言通过");
}

