/* 釜山 AI 旅行助手 v3.0 断言：
 *   A. 个性化推荐条：可收起/展开的头部 + 单行横向滚动的正文
 *   B. 收起/展开的状态机（默认收起、localStorage 记忆、点点子自动收起）
 *   C. 纵向占地：折叠态只有一行标题，展开态高度受 max-height 约束
 *   D. 顺手收口的横滑区（综合推荐胶囊、手动天气 chip）
 *   E. 不回退：v2.8 的权限链路、v2.7 的天气按钮、v2.6 的偏好条与三语
 *   F. 双端版本号 / PWA 缓存名同步到 3.0 / 23
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
const mixSrc = fs.readFileSync(path.join(A, "mix.js"), "utf8");

let pass = 0, fail = 0;
const failed = [];
function ok(name, cond, extra) {
  if (cond) pass++;
  else { fail++; failed.push(name + (extra ? " -> " + extra : "")); }
}
/** 取一段 CSS 规则体，便于逐条断言属性 */
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

/* ---------------- A. 组件结构 ---------------- */
ok("结构: 欢迎语气泡里有 .qrec 容器", /<div class="qrec" id="qrec" data-count="' \+ quick\.length \+ '"/.test(html));
ok("结构: 头部是按钮并带 aria-expanded", /class="qrec-head" id="qrecToggle" type="button" aria-expanded="false" aria-controls="qrecBody"/.test(html));
ok("结构: 三语标题「个性化推荐」", /L\("个性化推荐", "맞춤 추천", "Picks for you"\)/.test(html));
ok("结构: 摘要位 #qrecSum 存在", /<span class="qrec-sum" id="qrecSum"><\/span>/.test(html));
ok("结构: 动作位 #qrecAct 存在", /<span class="qrec-act" id="qrecAct"><\/span>/.test(html));
ok("结构: 正文 .qrec-body 存在", /<div class="qrec-body" id="qrecBody">/.test(html));
ok("结构: 正文里套 .qrec-scrollwrap 做右侧渐隐", /qrec-body" id="qrecBody"><div class="qrec-scrollwrap"><div class="quick">/.test(html));
ok("结构: 点子共 5 个（quick 数组）", (html.match(/lang === "zh" \? "[^"]*" : lang === "ko"/g) || []).length >= 4);
ok("结构: 5 个点子仍是 .pick 按钮", /quick\.map\(function\(q, i\)\{[\s\S]{0,300}class="pick"[\s\S]{0,80}esc\(q\)/.test(html));
ok("结构: 最后一个点子仍走天气入口 data-wx", /i === quick\.length - 1\) \? ' data-wx="1"'/.test(html));
ok("结构: 其余点子仍带 data-q", /' data-q="' \+ esc\(q\) \+ '"/.test(html));
ok("结构: greet 末尾调用 initQrec", /initQrec\(\);\s*\n\s*var res = \{text: "", followups: \[\]\};/.test(html));

/* ---------------- B. 状态机 ---------------- */
ok("状态: 默认收起（qrecOpen = false）", /var qrecOpen = false;/.test(html));
ok("状态: 上次选择从 localStorage 读回", /localStorage\.getItem\("busan_qrec"\) === "1"/.test(html));
ok("状态: 每次切换写回 localStorage", /localStorage\.setItem\("busan_qrec", qrecOpen \? "1" : "0"\)/.test(fn("setQrec")));
ok("状态: setQrec 收 boolean", /function setQrec\(open\)\{[\s\S]{0,80}qrecOpen = !!open/.test(html));
ok("状态: 切换时用 classList.toggle('open')", /box\.classList\.toggle\("open", qrecOpen\)/.test(fn("qrecPaint")));
ok("状态: 同步 aria-expanded", /head\.setAttribute\("aria-expanded", qrecOpen \? "true" : "false"\)/.test(fn("qrecPaint")));
ok("状态: 展开/收起按钮文案三语", /qrecOpen \? L\("收起", "접기", "Hide"\) : L\("展开", "펼치기", "Show"\)/.test(fn("qrecPaint")));
ok("状态: 收起时摘要提示单行横滑", /L\("5 个点子 · 展开后单行横滑"/.test(html));
ok("状态: 展开时摘要提示左右滑动", /L\("5 个点子 · 左右滑动看更多", "5가지 · 좌우로 넘겨 보기"/.test(html));
ok("状态: 头部点击绑定切换", /head\.onclick = function\(\)\{ setQrec\(!qrecOpen\); \}/.test(fn("initQrec")));
ok("状态: 点普通点子后自动收起", /if \(qrecOpen\) setQrec\(false\);\s*\n\s*ask\(b\.getAttribute\("data-q"\)\)/.test(html));
ok("状态: 点天气点子后也自动收起", /if \(qrecOpen\) setQrec\(false\);\s*\n\s*var fab = document\.getElementById\("wxFab"\)/.test(html));

/* ---------------- C. 折叠态的占地 ---------------- */
const qrecBody = css("  .qrec-body");
const qrecOpenCss = css("  .qrec.open .qrec-body");
ok("占地: 折叠态 max-height:0", /max-height:0/.test(qrecBody), qrecBody.slice(0, 60));
ok("占地: 折叠态 opacity:0 + overflow:hidden", /opacity:0/.test(qrecBody) && /overflow:hidden/.test(qrecBody));
ok("占地: 展开态高度封顶 76px（约两行内）", /max-height:76px/.test(qrecOpenCss));
ok("占地: 展开有 0.26s 过渡，不是硬切", /transition:max-height \.26s/.test(qrecBody));
ok("占地: 头部一行最小 38px（收起只占这一行）", /min-height:38px/.test(css("  .qrec-head")));
ok("占地: 76px 展开高度 < 原来三行点子的约 110px", 76 < 110);

/* ---------------- C2. 横向滚动 ---------------- */
const qrecQuick = css("  .qrec-body .quick");
ok("横滑: 词组不再换行（flex-wrap:nowrap）", /flex-wrap:nowrap/.test(qrecQuick));
ok("横滑: overflow-x:auto", /overflow-x:auto/.test(qrecQuick));
ok("横滑: 隐藏系统滚动条", /\.qrec-body \.quick::-webkit-scrollbar\{display:none\}/.test(html));
ok("横滑: 支持 iOS 惯性滚动", /-webkit-overflow-scrolling:touch/.test(qrecQuick));
ok("横滑: 手势吸附 scroll-snap", /scroll-snap-type:x proximity/.test(qrecQuick));
ok("横滑: 点子不被压缩（flex:0 0 auto）", /\.qrec-body \.pick\{flex:0 0 auto/.test(html));
ok("横滑: 单个点子最长 78vw 并省略号", /max-width:78vw/.test(html) && /text-overflow:ellipsis/.test(html));
ok("横滑: 右侧渐隐提示（::after 渐变）", /\.qrec-scrollwrap::after\{[\s\S]{0,120}linear-gradient/.test(html));
ok("横滑: 渐隐不挡点击（pointer-events:none）", /\.qrec-scrollwrap::after\{[\s\S]{0,140}pointer-events:none/.test(html));

/* ---------------- D. 其他横滑收口 ---------------- */
const mixRow = css("  .mixrow");
ok("胶囊: 三枚不再换行", /flex-wrap:nowrap/.test(mixRow) && /overflow-x:auto/.test(mixRow));
ok("胶囊: 不被压缩", /flex:0 0 auto/.test(css("  .mixchip")));
ok("天气 chip: 单行横滑", /flex-wrap:nowrap/.test(css("  .wxchips")) && /overflow-x:auto/.test(css("  .wxchips")));
ok("天气 chip: 按钮不被压缩", /flex:0 0 auto/.test(css("  .wxchips button")));
ok("夜景: 推荐条有夜间配色", /body\.night \.qrec\{/.test(html) && /body\.night \.qrec-act\{/.test(html));
ok("夜景: 夜间渐隐底色跟随", /body\.night \.qrec-scrollwrap::after\{/.test(html) && /rgba\(21,30,38,0\)/.test(html));
ok("夜景: 夜间点子配色", /body\.night \.qrec \.pick\{/.test(html));

/* ---------------- E. 不回退 ---------------- */
ok("不回退: 天气按钮仍在页头", /<button id="wxFab" class="wx-fab"/.test(html));
ok("不回退: 气泡第二行 #wxCtx", /id="wxCtx"/.test(html));
ok("不回退: 天气入口先权限卡", /wxPermissionCard/.test(html) && /mixFlow\("weather"\)/.test(html));
ok("不回退: 附近入口先权限卡", /mixPermissionCard\("nearby"\)/.test(html) && /mixFlow\("nearby"\)/.test(html));
ok("不回退: mix.js 仍被引入", /<script src="mix\.js"><\/script>/.test(html));
ok("不回退: mix.js 仍导出 ranked", /ranked:\s*ranked|ranked,/i.test(mixSrc.replace(/\s+/g, " ")) || /function ranked\(/.test(mixSrc));
ok("不回退: 偏好条仍可折叠", /id="prefsToggle"/.test(html) && /function setPrefs\(open/.test(html));
ok("不回退: 偏好条仍是三语", /"玩法 · 出行" : lang === "ko" ? "테마 · 同行"|"玩法 · 出行" : lang === "ko"/.test(html));
ok("不回退: 三语按钮仍在", /data-lang="zh"/.test(html) && /data-lang="ko"/.test(html) && /data-lang="en"/.test(html));
ok("不回退: 附近按钮仍在页脚", /id="gps"/.test(html));
ok("不回退: 昼夜判定仍是 19/6", /return h >= 19 \|\| h < 6;/.test(html));
ok("不回退: 手动天气 chip 仍 8 项", (html.match(/k: "(clear|cloudy|rain|snow|fog|storm|hot|cold)", zh:/g) || []).length === 8);

/* ---------------- F. 版本 ---------------- */
ok("版本: APK 23 / 3.0", /android:versionCode="24"/.test(apkMan) && /android:versionName="3\.1"/.test(apkMan));
ok("版本: 无旧 versionCode 21 残留", !/android:versionCode="21"/.test(apkMan));
ok("版本: 原生 UA 3.0", /BusanTour\/3\.1 \(Android\)/.test(native));
ok("版本: 无 2.8 UA 残留", !/BusanTour\/2\.8/.test(native));
ok("版本: 类注释 v3.0 且保留 v2.9 说明", /釜山 AI 旅行助手 v3\.1/.test(native) && /v2\.9 个性化推荐条/.test(native));
ok("版本: iOS 3.0 / 23", /MARKETING_VERSION: "3\.1"/.test(iosYml) && /CURRENT_PROJECT_VERSION: "24"/.test(iosYml));
ok("版本: iOS README 同步 3.0", /（v3\.1）/.test(iosReadme));
ok("版本: PWA 缓存名 busan-3.1", /const CACHE = 'busan-3\.1'/.test(sw));
ok("版本: 无旧缓存残留", sw.indexOf("busan-2.8") === -1);
ok("版本: SW 清单仍含 mix.js", /'\.\/mix\.js'/.test(sw));
ok("版本: PWA 脚本产物名 v30", /Busan_Tour_WebApp_v30/.test(pwaPy) && /Busan_iOS_WebApp_v30\.zip/.test(pwaPy));
ok("版本: PWA 说明 3.0", /v3\.1 · iPhone/.test(pwaPy));
ok("版本: AndroidManifest 有 v2.9 说明块", /v2\.9：个性化推荐/.test(apkMan));

/* ---------------- 汇总 ---------------- */
console.log("");
console.log("==== v2.9 结果（版本已随 3.0 同步） ====");
console.log("通过 " + pass + " / 失败 " + fail);
if (fail) {
  failed.forEach((f) => console.log("  ✗ " + f));
  console.log("v2.9 断言未通过");
  process.exit(1);
} else {
  console.log("v2.9 全部断言通过");
}

