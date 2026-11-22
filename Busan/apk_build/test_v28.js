/* 釜山 AI 旅行助手 v2.8 断言：
 *   A. mix.js 的综合排序逻辑（时间 + 天气 + 距离 + 评级）——真跑代码，不只 grep
 *   B. 界面接线：天气按钮 / “附近”都要先问权限，再走同一条链路
 *   C. 双端版本号、PWA 缓存名、既有能力不回退
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const A = path.join(ROOT, "android", "assets");
const html = fs.readFileSync(path.join(A, "index.html"), "utf8");
const mixSrc = fs.readFileSync(path.join(A, "mix.js"), "utf8");
const sw = fs.readFileSync(path.join(A, "sw.js"), "utf8");
const apkMan = fs.readFileSync(path.join(ROOT, "android", "AndroidManifest.xml"), "utf8");
const native = fs.readFileSync(path.join(ROOT, "android", "java", "com", "busan", "tour", "MainActivity.java"), "utf8");
const iosYml = fs.readFileSync(path.join(ROOT, "ios", "project.yml"), "utf8");
const data = JSON.parse(fs.readFileSync(path.join(A, "cloud_snapshot.json"), "utf8"));

let pass = 0, fail = 0;
const failed = [];
function ok(name, cond, extra) {
  if (cond) pass++;
  else { fail++; failed.push(name + (extra ? " -> " + extra : "")); }
}

/* ---------- 把 mix.js 放进最小沙箱，接上真实的 18 个景点与真实天气打分 ---------- */
function haversine(a, b, c, d) {
  const R = 6371, rad = Math.PI / 180;
  const dLat = (c - a) * rad, dLng = (d - b) * rad;
  const x = Math.sin(dLat / 2) ** 2 + Math.cos(a * rad) * Math.cos(c * rad) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
}
const spots = data.spots;
const sandbox = { console, Date, Math, JSON, Number, String, isFinite, parseInt, parseFloat };
sandbox.window = sandbox;
sandbox.BUSAN_DATA = { spots };
sandbox.BusanCloud = {
  allSpots: () => spots,
  spotTitle: (s) => (s ? s.name : ""),
  haversine,
  nearby: (lat, lng, n) =>
    spots.filter((s) => s.lat != null)
      .map((s) => ({ spot: s, km: haversine(lat, lng, s.lat, s.lng) }))
      .sort((x, y) => x.km - y.km).slice(0, n || 3)
};
sandbox.BusanRating = {
  of: (id) => (id === "札嘎其市场" ? { score: 4.4 } : id === "海云台海水浴场" ? { score: 4.7 } : { score: 4.0 }),
  starsText: (n) => "★★★★".slice(0, Math.round(n || 0))
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(A, "weather.js"), "utf8"), sandbox);
vm.runInContext(mixSrc, sandbox);
const MX = sandbox.BusanMix;

ok("mix: 加载成功", !!(MX && MX.ranked && MX.ctxOf));
ok("mix: 自带 haversine 兜底", MX && typeof MX.distScore === "function");

/* ---------- 1. 时间轴的边界 ---------- */
const bandCases = [
  [3, "night"], [4, "dawn"], [5, "dawn"], [6, "morning"], [10, "morning"],
  [11, "noon"], [13, "noon"], [14, "afternoon"], [16, "afternoon"],
  [17, "dusk"], [18, "dusk"], [19, "night"], [23, "night"], [0, "night"], [2, "night"]
];
bandCases.forEach(([h, want]) => ok("时段: " + h + " 点 -> " + want, MX.bandOf(h) === want, "got " + MX.bandOf(h)));
[19, 20, 23, 0, 3, 5].forEach((h) => ok("夜间: " + h + " 点算夜", MX.nightOf(h) === true));
[6, 9, 12, 15, 18].forEach((h) => ok("白天: " + h + " 点算昼", MX.nightOf(h) === false));
ok("夜间: 与页面同一口径 19/6", MX.nightOf(18) === false && MX.nightOf(19) === true);

/* ---------- 2. 距离分 ---------- */
ok("距离: 500 m 内最高", MX.distScore(0.4) === 22);
ok("距离: 越远越低", MX.distScore(1) > MX.distScore(3) && MX.distScore(3) > MX.distScore(6));
ok("距离: 远到极限被压到 -12", MX.distScore(30) === -12);
ok("距离: 无坐标不给分", MX.distScore(null) === 0);

/* ---------- 3. 时间分（用景点自带的 best_time / vibes） ---------- */
const byId = (id) => spots.find((s) => s.id === id);
const market = byId("札嘎其市场"), beach = byId("海云台海水浴场"), sunset = byId("多大浦海水浴场");
ok("时间: 夜间室内 > 夜间海边", MX.timeScore(market, "night") > MX.timeScore(beach, "night"),
  MX.timeScore(market, "night") + " vs " + MX.timeScore(beach, "night"));
ok("时间: 傍晚 sunset 标的景点得分最高", MX.timeScore(sunset, "dusk") >= 12, MX.timeScore(sunset, "dusk"));
ok("时间: 夜间 best_time=evening 的景点吃分",
  MX.timeScore(byId("多大浦梦之夕阳喷泉"), "night") >= 10, MX.timeScore(byId("多大浦梦之夕阳喷泉"), "night"));

/* ---------- 4. 天气分 ---------- */
const rainW = { cls: "rain", temp: 14, feels: 12, wind: 3, precipProb: 85 };
const clearW = { cls: "clear", temp: 22, feels: 22, wind: 2, precipProb: 5 };
ok("天气: 雨天室内高于海边", MX.weatherScore(market, rainW) > MX.weatherScore(beach, rainW));
ok("天气: 晴天海边高于市场", MX.weatherScore(beach, clearW) > MX.weatherScore(market, clearW));
ok("天气: 没天气时不加不减", MX.weatherScore(beach, null) === 0);

/* ---------- 5. 综合排序（核心） ---------- */
const posNampo = { lat: 35.0966, lng: 129.0306 };             // 南浦洞/札嘎其一带
const nightRain = MX.ctxOf({ pos: posNampo, w: rainW, hour: 21 });
const rowsNight = MX.ranked(nightRain, 3);
ok("排序: 夜间下雨给 3 个", rowsNight.length === 3);
ok("排序: 夜间下雨首选要么室内、要么夜味（night/food）",
  (rowsNight[0].spot.plan.indoor === 1) ||
  (rowsNight[0].spot.vibes || []).some((v) => v === "night" || v === "food"),
  rowsNight.map((r) => r.id).join("/"));
ok("排序: 夜间下雨首选离你 2 km 内", rowsNight[0].km <= 2, rowsNight[0].km.toFixed(1));
ok("排序: 前三个里至少两个室内", rowsNight.filter((r) => r.spot.plan && r.spot.plan.indoor).length >= 2,
  rowsNight.map((r) => r.id + (r.spot.plan.indoor ? "(in)" : "(out)")).join("/"));
ok("排序: 每个结果都带距离", rowsNight.every((r) => isFinite(r.km) && r.km >= 0));
ok("排序: 每个结果都带理由", rowsNight.every((r) => r.reasons.length >= 2));
ok("排序: 理由里写到了 km", rowsNight[0].reasons.join(" ▸ ").indexOf("km") > -1);
ok("排序: 分数降序", rowsNight[0].score >= rowsNight[1].score && rowsNight[1].score >= rowsNight[2].score);

const posDadaepo = (() => { const s = byId("多大浦海水浴场"); return { lat: s.lat + 0.004, lng: s.lng + 0.004 }; })();
const duskClear = MX.ctxOf({ pos: posDadaepo, w: clearW, hour: 18 });
const rowsDusk = MX.ranked(duskClear, 3);
ok("排序: 傍晚晴天在多大浦附近，首选带 sunset 属性的景点",
  ["多大浦海水浴场", "没云台", "峨嵋山观景台", "多大浦梦之夕阳喷泉"].indexOf(rowsDusk[0].id) > -1,
  rowsDusk.map((r) => r.id).join("/"));

const noonCtx = MX.ctxOf({ pos: posNampo, w: clearW, hour: 12 });
ok("排序: 午间晴天不再往海边堆", MX.ranked(noonCtx, 3)[0].id !== "海云台海水浴场",
  MX.ranked(noonCtx, 3).map((r) => r.id).join("/"));

const noPos = MX.ctxOf({ pos: null, w: clearW, hour: 12 });
ok("排序: 没坐标也能排（距离项不参与）", MX.ranked(noPos, 3).length === 3);

/* ---------- 6. 上下文与建议 ---------- */
ok("上下文: 一行里有时间、日段和天气", /^\d\d:\d\d ·/.test(MX.contextLine(nightRain)) && MX.contextLine(nightRain).indexOf("雨") > -1,
  MX.contextLine(nightRain));
ok("上下文: 没天气时明确写未取到", MX.contextLine(MX.ctxOf({ pos: null, w: null, hour: 12 })).indexOf("未取到") > -1);
ok("建议: 夜雨说就近/室内", /室内|就近|屋檐/.test(MX.advice(nightRain), MX.advice(nightRain)));
ok("建议: 晴天说海景/观景", /海|观景/.test(MX.advice(MX.ctxOf({ pos: posNampo, w: clearW, hour: 15 }))));
ok("建议: 高温提醒防晒/树荫", MX.advice(MX.ctxOf({ pos: posNampo, w: { cls: "clear", temp: 33 }, hour: 12 })).length > 0);
ok("三语: 切换英文后上下文仍是时间行", (MX.setLang("en"), /^\d\d:\d\d ·/.test(MX.contextLine(nightRain))));
MX.setLang("zh");

/* ---------- 7. 界面接线：先权限 → 定位 → 天气 → 时间 ---------- */
ok("接线: index.html 引入 mix.js", /<script src="mix\.js"><\/script>/.test(html));
ok("接线: 天气按钮已授权走综合流程", /perm === "granted"[\s\S]{0,100}mixFlow\("weather"\)/.test(html));
ok("接线: 天气按钮没授权先给权限卡", /wxPermissionCard\(\);[\s\S]{0,40}\/\/ 先说明为什么要定位/.test(html));
ok("接线: “附近”先给同一张权限卡", /mixPermissionCard\("nearby"\)/.test(html));
ok("接线: “附近”有坐标/已授权走综合流程", /pos \|\| perm === "granted"[\s\S]{0,60}mixFlow\("nearby"\)/.test(html));
ok("接线: 综合流程先 ensure 定位", /function mixFlow[\s\S]{0,1300}BusanLive\.ensure/.test(html));
ok("接线: 取到天气后才出结论", /fetchWeather\(null, \{ force: true, silent: true, notify: false, quiet: true, done:[\s\S]{0,200}mixResult/.test(html));
ok("接线: 没坐标也降级给结论（写明未定位）", /mixResult\(null, wxState\(\), \{ kind: kind, why: why \}\)/ .test(html));
ok("接线: 天气请求支持 quiet/done", /opts\.quiet[\s\S]{0,80}opts\.done/.test(html) && /if \(opts\.done\) opts\.done\(w\)/.test(html));
ok("接线: 权限卡写明三步（坐标→天气→时间）", /读你的坐标[\s\S]{0,60}取当地天气[\s\S]{0,60}当前时间/.test(html));
ok("接线: 三枚胶囊渲染", /result\.mixChips[\s\S]{0,400}mixchip/.test(html) && /\.mixchip\{/.test(html));
ok("接线: 胶囊有夜间配色", /body\.night \.mixchip\{/.test(html) && /body\.night \.mixchip\.w\{/.test(html));
ok("接线: 气泡第二行有时间上下文", /id="wxCtx"/.test(html) && /function wxCtxLine\(\)/.test(html) && /MX\.bandName/.test(html));
ok("接线: 无天气时按钮图标随昼夜变", /MX\.nightOf\(nowH\)[\s\S]{0,40}🌙/.test(html));
ok("接线: 综合结论带 3 个可点选项", /mixResult[\s\S]{0,2600}choices\.push/.test(html));
ok("接线: BusanUI 暴露综合入口", /mix: function\(opts\)/.test(html) && /startMix: function/.test(html) && /mixAdvice: function/.test(html));
ok("接线: 结论里只陈述昼夜规则，不断言当前配色", /06:00–18:59 白天，19:00–05:59 夜间/.test(html) && !/保持白天配色/.test(html));

/* ---------- 8. 版本与 PWA ---------- */
ok("版本: APK 22 / 2.9", /android:versionCode="24"/.test(apkMan) && /android:versionName="3\.1"/.test(apkMan));
ok("版本: UA 2.9", /BusanTour\/3\.1 \(Android\)/.test(native));
ok("版本: 类注释 v2.9", /釜山 AI 旅行助手 v3\.1/.test(native));
ok("版本: iOS 2.9 / 22", /MARKETING_VERSION: "3\.1"/.test(iosYml) && /CURRENT_PROJECT_VERSION: "24"/.test(iosYml));
ok("版本: 无 2.7 残留 UA", !/BusanTour\/2\.7/.test(native));
ok("PWA: 缓存名 busan-3.1", /const CACHE = 'busan-3\.1'/.test(sw));
ok("PWA: 清单含 mix.js", /'\.\/mix\.js'/.test(sw));
ok("PWA: 清单仍含 weather/ratings", /'\.\/weather\.js'/.test(sw) && /'\.\/ratings\.js'/.test(sw));
ok("PWA: manifest 与图标仍在", fs.existsSync(path.join(A, "manifest.webmanifest")) &&
  [180, 192, 512].every((n) => fs.existsSync(path.join(A, "icon-" + n + ".png"))));
ok("PWA: assets 里没有多余大图", !fs.existsSync(path.join(A, "icon_raw.png")) && !fs.existsSync(path.join(A, "icon-1024.png")));

/* ---------- 9. 既有能力不回退 ---------- */
["BusanWeather", "BusanRating", "paintWxBar", "wxAdapt", "initWeather", "ratingHtml", "wxPanelHtml",
 "grantWeather", "grantNearby", "routePermissionCard", "nearbyRoutePermissionCard", "renderNearby",
 "locateOnce", "BusanLightbox", "BusanPlanner", "renderFollowups"].forEach((k) => {
  ok("保留: " + k, html.indexOf(k) > -1);
});
ok("保留: 手动天气 chip 仍可用", /data-k="' \+ c\.k/.test(html) && /WX\.manual\(k\)/.test(html));
ok("保留: 星级块仍渲染", /RT\.starsHtml/.test(html));
ok("保留: 权限被拒可跳系统设置", /openAppSettings/.test(html));
ok("保留: 弹层/后台收起气泡", /wxPillHideIfAway/.test(html) && /document\.hidden/.test(html));

console.log("");
console.log("PASS " + pass + " / FAIL " + fail);
if (fail) { console.log("FAILED:"); failed.forEach((f) => console.log("  x " + f)); }
console.log(fail ? "v2.8 断言未通过" : "v2.8 全部断言通过");
process.exit(fail ? 1 : 0);

