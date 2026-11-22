/* 釜山 AI 旅行助手 v2.6 静态断言（UI 收口 + PWA + 双端版本同步）
 * 运行：cd D:\AI_Project_2026_2\Busan && node apk_build/test_v26.js
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const A = path.join(ROOT, "android", "assets");
const read = (p) => fs.readFileSync(p, "utf8");
const readBuf = (p) => fs.readFileSync(p);

let pass = 0, fail = 0;
const failed = [];
function ok(name, cond, extra) {
  if (cond) { pass++; }
  else { fail++; failed.push(name + (extra ? " -> " + extra : "")); }
}

const html = read(path.join(A, "index.html"));
const manifest = read(path.join(A, "manifest.webmanifest"));
const sw = read(path.join(A, "sw.js"));
const apkMan = read(path.join(ROOT, "android", "AndroidManifest.xml"));
const native = read(path.join(ROOT, "android", "java", "com", "busan", "tour", "MainActivity.java"));
const iosYml = read(path.join(ROOT, "ios", "project.yml"));
const iosPlist = read(path.join(ROOT, "ios", "BusanTour", "Info.plist"));

/* ---------- 1. PWA 元信息 ---------- */
ok("head: theme-color", /<meta name="theme-color" content="#0a4e63">/.test(html));
ok("head: apple standalone", /apple-mobile-web-app-capable" content="yes"/.test(html));
ok("head: status bar translucent", /apple-mobile-web-app-status-bar-style" content="black-translucent"/.test(html));
ok("head: apple title", /apple-mobile-web-app-title" content="釜山助手"/.test(html));
ok("head: apple-touch-icon", /rel="apple-touch-icon" href="icon-180\.png"/.test(html));
ok("head: favicon 192", /rel="icon" type="image\/png" href="icon-192\.png"/.test(html));
ok("head: manifest link", /rel="manifest" href="manifest\.webmanifest"/.test(html));
ok("head: no telephone autolink", /format-detection" content="telephone=no"/.test(html));

/* ---------- 2. manifest 合法性 ---------- */
let mj = null;
try { mj = JSON.parse(manifest); } catch (e) { }
ok("manifest: JSON 可解析", !!mj, "parse error");
if (mj) {
  ok("manifest: name", mj.name === "釜山 AI 旅行助手", mj.name);
  ok("manifest: short_name", mj.short_name === "釜山助手", mj.short_name);
  ok("manifest: start_url", mj.start_url === "./index.html", mj.start_url);
  ok("manifest: scope", mj.scope === "./", mj.scope);
  ok("manifest: display standalone", mj.display === "standalone", mj.display);
  ok("manifest: theme_color", mj.theme_color === "#0a4e63", mj.theme_color);
  const icons = (mj.icons || []).map((x) => x.sizes + "|" + x.purpose);
  ok("manifest: has 192 any", icons.includes("192x192|any"), icons.join(","));
  ok("manifest: has 512 any", icons.includes("512x512|any"), icons.join(","));
  ok("manifest: has 512 maskable", icons.includes("512x512|maskable"), icons.join(","));
}

/* ---------- 3. 图标真实尺寸 ---------- */
function pngSize(p) {
  const b = readBuf(p);
  if (b.slice(1, 4).toString("ascii") !== "PNG") return null;
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
[["icon-180.png", 180], ["icon-192.png", 192], ["icon-512.png", 512]].forEach(([f, n]) => {
  const s = pngSize(path.join(A, f));
  ok("icon " + f + " 存在且 " + n + "x" + n, s && s.w === n && s.h === n, s ? s.w + "x" + s.h : "missing");
});
const s1024 = pngSize(path.join(ROOT, "pwa", "icon-1024.png"));
ok("icon 1024（只给 PWA/iOS，不进 APK）", s1024 && s1024.w === 1024 && s1024.h === 1024, s1024 ? s1024.w + "x" + s1024.h : "missing");
ok("APK assets 不含 1024/原图（不撑大安装包）",
   !fs.existsSync(path.join(A, "icon-1024.png")) && !fs.existsSync(path.join(A, "icon_raw.png")));

/* ---------- 4. service worker ---------- */
ok("sw: 存在且非空", sw.length > 1500, sw.length + "B");
ok("sw: 缓存名跟版本 2.9", /const CACHE = 'busan-3\.1'/.test(sw));
ok("sw: 缓存 index.html", /'\.\/index\.html'/.test(sw));
ok("sw: 缓存图标 180", /'\.\/icon-180\.png'/.test(sw));
ok("sw: 只处理 GET", /req\.method !== 'GET'/.test(sw));
ok("sw: 跨域请求不缓存（天气走网络）", /url\.origin !== self\.location\.origin/.test(sw));
ok("sw: 导航回退到 index.html", /caches\.match\('\.\/index\.html'\)/.test(sw));
ok("sw: HTML 网络优先（更新能即时生效）", /req\.mode === 'navigate' \|\| \/\\\.html\?\$\/i\.test\(url\.pathname\)/.test(sw));
ok("sw: 激活清理旧缓存", /caches\.delete\(k\)/.test(sw));

const shell = (sw.match(/const SHELL = \[([\s\S]*?)\];/) || [])[1] || "";
const shellFiles = (shell.match(/'\.\/([^']+)'/g) || []).map((s) => s.slice(3, -1).replace(/^\.\//, "")).filter((f) => f.indexOf(".") > -1);
const missingShell = shellFiles.filter((f) => !fs.existsSync(path.join(A, f)));
ok("sw: 预缓存清单文件全部存在", missingShell.length === 0, missingShell.join(","));
ok("sw: 预缓存含 weather/ratings", /weather\.js/.test(shell) && /ratings\.js/.test(shell));

/* ---------- 5. 前端 v2.6 UI 收口 ---------- */
ok("ui: 夜间模式作用域 body.night", /body\.night\{/.test(html));
ok("ui: 深色重定义 --sand", /--sand:#0d1319/.test(html));
ok("ui: 深色重定义 --ink", /--ink:#e8eff4/.test(html));
ok("ui: 宽屏单列居中", /@media \(min-width:700px\)/.test(html) && /max-width:560px;\s*margin:0 auto/.test(html));
ok("ui: 窄屏 360 收边距", /@media \(max-width:360px\)/.test(html));
ok("ui: 输入框 16px 防 iOS 缩放", /#q\{font-size:16px\}/.test(html));
ok("ui: 选项触控 44px", /\.choice\{min-height:44px\}/.test(html));
ok("ui: 发送/图标按钮 40px", /\.send,\.icon-btn\{min-height:40px\}/.test(html));
ok("ui: chip 34px", /\.chip\{padding:8px 12px;\s*min-height:34px\}/.test(html));
ok("ui: overscroll 禁用", /overscroll-behavior-y:none/.test(html));
ok("ui: text-size-adjust", /-webkit-text-size-adjust:100%/.test(html));

/* ---------- 6. 天气快捷入口 ---------- */
ok("ui: 欢迎语含天气入口文案", /今天天气适合去哪/.test(html));
ok("ui: 天气入口 data-wx", /data-wx="1"/.test(html));
ok("ui: 天气入口绑定到右上角按钮", /getElementById\("wxFab"\)\.onclick/.test(html) && /document\.getElementById\("wxFab"\)\.onclick/.test(html));

/* ---------- 7. SW 注册 ---------- */
ok("sw注册: https 才注册", html.indexOf('"serviceWorker" in navigator && /^https?:$/.test(location.protocol)') > -1);
ok("sw注册: register sw.js", /navigator\.serviceWorker\.register\("sw\.js"\)/.test(html));

/* ---------- 8. 双端版本同步 ---------- */
ok("apk: versionCode 22", /android:versionCode="24"/.test(apkMan));
ok("apk: versionName 2.9", /android:versionName="3\.1"/.test(apkMan));
ok("apk: 注释含 v2.6", /v2\.6/.test(apkMan));
ok("native: UA 2.9", /BusanTour\/3\.1 \(Android\)/.test(native));
ok("native: 类注释 v2.9", /釜山 AI 旅行助手 v3\.1/.test(native));
ok("ios: MARKETING_VERSION 2.9", /MARKETING_VERSION: "3\.1"/.test(iosYml));
ok("ios: CURRENT_PROJECT_VERSION 22", /CURRENT_PROJECT_VERSION: "24"/.test(iosYml));
ok("ios: AppIcon 资源集启用", /ASSETCATALOG_COMPILER_APPICON_NAME: AppIcon/.test(iosYml));
ok("ios: 引用同一套 assets", /path: \.\.\/android\/assets/.test(iosYml));
ok("ios: Info.plist icon name", /CFBundleIconName[\s\S]{0,40}AppIcon/.test(iosPlist));
ok("ios: 版本号走变量", /\$\(MARKETING_VERSION\)/.test(iosPlist) && /\$\(CURRENT_PROJECT_VERSION\)/.test(iosPlist));
ok("ios: AppIcon Contents.json", fs.existsSync(path.join(ROOT, "ios", "BusanTour", "Assets.xcassets", "AppIcon.appiconset", "Contents.json")));
ok("ios: AppIcon 1024 文件", fs.existsSync(path.join(ROOT, "ios", "BusanTour", "Assets.xcassets", "AppIcon.appiconset", "icon-1024.png")));

/* ---------- 9. 旧版本残留 ---------- */
ok("残留: 无 v2.5 UA", !/BusanTour\/2\.[56]/.test(native));
ok("残留: manifest 无 versionCode 18", !/android:versionCode="18"/.test(apkMan));
ok("残留: ios 无 2.5", !/MARKETING_VERSION: "2\.5"/.test(iosYml));

/* ---------- 10. v2.5 能力保留 ---------- */
["BusanWeather", "BusanRating", "wxFab", "wxText", "paintWxBar", "ratingHtml", "wxAdapt", "initWeather"].forEach((k) => {
  ok("v2.5 保留: " + k, html.indexOf(k) > -1);
});

console.log("");
console.log("PASS " + pass + " / FAIL " + fail);
if (fail) { console.log("FAILED:"); failed.forEach((f) => console.log("  x " + f)); }
console.log(fail ? "v2.6 断言未通过" : "v2.6 全部断言通过");
process.exit(fail ? 1 : 0);

