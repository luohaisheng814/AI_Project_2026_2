/* 釜山 AI 旅行助手 v2.7 断言：右上角天气按钮 + 权限询问 + 自动收起 + 按时间昼夜 */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const A = path.join(ROOT, "android", "assets");
const html = fs.readFileSync(path.join(A, "index.html"), "utf8");
const apkMan = fs.readFileSync(path.join(ROOT, "android", "AndroidManifest.xml"), "utf8");
const native = fs.readFileSync(path.join(ROOT, "android", "java", "com", "busan", "tour", "MainActivity.java"), "utf8");
const iosYml = fs.readFileSync(path.join(ROOT, "ios", "project.yml"), "utf8");
const sw = fs.readFileSync(path.join(A, "sw.js"), "utf8");

let pass = 0, fail = 0;
const failed = [];
function ok(name, cond, extra) {
  if (cond) pass++;
  else { fail++; failed.push(name + (extra ? " -> " + extra : "")); }
}

/* 1. 入口位置：页头右上角 */
ok("右上角: header 内新增 #wxFab", /<button id="wxFab" class="wx-fab"/.test(html));
ok("右上角: 与标题同一行（.brand 内）", /<div class="brand">[\s\S]{0,400}id="wxFab"/.test(html));
ok("右上角: 旧天气条 #wxStrip 已移除", !/id="wxStrip"/.test(html));
ok("右上角: 旧 #wxBtn 已移除", !/getElementById\("wxBtn"\)/.test(html));
ok("右上角: FAB 靠上对齐", /\.wx-fab\{[\s\S]{0,200}align-self:flex-start/.test(html));
ok("右上角: 圆形胶囊 32px 起", /\.wx-fab\{[\s\S]{0,260}border-radius:16px/.test(html) && /min-height:32px/.test(html));
ok("右上角: 有天气时高亮", /\.wx-fab\.on/.test(html));
ok("右上角: 无障碍 aria", /aria-label="天气"|aria-expanded/.test(html));

/* 2. 短暂显示的气泡 */
ok("气泡: #wxPill 默认 hidden", /<div class="wx-pill" id="wxPill" hidden>/.test(html));
ok("气泡: 绝对定位在页头下方右侧", /\.wx-pill\{[\s\S]{0,160}position:absolute[\s\S]{0,80}right:10px[\s\S]{0,80}top:calc\(100%/.test(html));
ok("气泡: 超出宽度省略", /\.wx-pill\{[\s\S]{0,420}text-overflow:ellipsis/.test(html));
ok("气泡: show 默认 8 秒", /wxPillShow\(autoHideMs\)[\s\S]{0,300}setTimeout\(wxPillHide, autoHideMs \|\| 8000\)/.test(html));
ok("气泡: 取到天气后露 10 秒", /if \(msg\) wxPillShow\(10000\)/.test(html));
ok("气泡: 手动关闭清除定时器", /clearTimeout\(wxPillTimer\)/.test(html));
ok("气泡: 滚开首页自动收起", /wxPillHideIfAway/.test(html) && /scrollHeight - chat\.scrollTop - chat\.clientHeight\) > 140/.test(html));
ok("气泡: 弹层/后台自动收起", /\.modal,\.sheet/.test(html) && /document\.hidden/.test(html));
ok("气泡: 聊天区绑定 scroll", /chatEl\.addEventListener\("scroll", wxPillHideIfAway/.test(html));

/* 3. 权限询问流程 */
ok("权限: 无数据先给权限卡", /wxPermissionCard\(\);[\s\S]{0,40}\/\/ 先说明为什么要定位/.test(html));
ok("权限: 已授权直接进综合流程", /perm === "granted"[\s\S]{0,80}mixFlow\("weather"\)/.test(html));
ok("权限: 有数据只露气泡不再重复授权", /if \(w\)\{ wxPillShow\(\); return; \}/.test(html));
ok("权限: 卡片说明“没有天气权限”", /没有单独的“天气权限”/.test(html));
ok("权限: 允许按钮走原生授权", /grantWeather\(\)/.test(html) && /BusanLive\.ensure/.test(html));
ok("权限: 被拒可跳系统设置", /act-settings/.test(html) && /openAppSettings/.test(html));

/* 4. 按时间昼夜 */
ok("昼夜: body.night 作用域", /body\.night\{/.test(html));
ok("昼夜: 夜间变量", /--sand:#0d1319; --ink:#e8eff4/.test(html));
ok("昼夜: 夜间顶栏更深", /body\.night header\{[\s\S]{0,120}linear-gradient\(135deg,#0d5a70,#072e3c\)/.test(html));
ok("昼夜: 19 点到 6 点判夜", /h >= 19 \|\| h < 6/.test(html));
ok("昼夜: 每分钟复判", /setInterval\(function\(\)\{ applyDayNight\(\); paintThemeBtn\(\); \}, 60 \* 1000\)/.test(html));
ok("昼夜: 切前台复判", /addEventListener\("visibilitychange", function\(\)\{ applyDayNight\(\); paintThemeBtn\(\); \}\)/.test(html));
ok("昼夜: 同步 theme-color", /#072e3c/.test(html) && /#0a4e63/.test(html));
ok("昼夜: 可手动覆盖", /setThemeMode/.test(html) && /mode === "night"/.test(html) && /mode === "day"/.test(html));
ok("昼夜: class 切换", /document\.body\.classList\.toggle\("night", night\)/.test(html));
ok("昼夜: BusanUI 暴露", /isNight: function|themeMode: function/.test(html));

/* 5. 版本与双端同步 */
ok("版本: APK 22 / 2.9（随版本链路同步）", /android:versionCode="24"/.test(apkMan) && /android:versionName="3\.1"/.test(apkMan));
ok("版本: 原生 UA 2.9", /BusanTour\/3\.1 \(Android\)/.test(native));
ok("版本: iOS 2.9 / 22", /MARKETING_VERSION: "3\.1"/.test(iosYml) && /CURRENT_PROJECT_VERSION: "24"/.test(iosYml));
ok("版本: 无 2.6 残留 UA", !/BusanTour\/2\.6/.test(native));

/* 6. 既有能力不回退 */
["BusanWeather", "BusanRating", "paintWxBar", "wxAdapt", "initWeather", "ratingHtml", "wxPanelHtml"].forEach((k) => {
  ok("保留: " + k, html.indexOf(k) > -1);
});
ok("保留: PWA manifest", fs.existsSync(path.join(A, "manifest.webmanifest")));
ok("保留: service worker", sw.indexOf("busan-3.1") > -1);
ok("保留: 深色下官网链接可读", /body\.night \.official \.ol a/.test(html));
ok("夜间: 有天气时按钮仍是橙底", /body\.night \.wx-fab\.on\{[\s\S]{0,120}#f0a94c/.test(html));
ok("夜间: 权限按钮不发白", /body\.night \.permact button\{/.test(html));
ok("气泡: 不挡下面按钮", /\.wx-pill\{[\s\S]{0,420}pointer-events:none/.test(html));

console.log("");
console.log("PASS " + pass + " / FAIL " + fail);
if (fail) { console.log("FAILED:"); failed.forEach((f) => console.log("  x " + f)); }
console.log(fail ? "v2.7 断言未通过" : "v2.7 全部断言通过");
process.exit(fail ? 1 : 0);

