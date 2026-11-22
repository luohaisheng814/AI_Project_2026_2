/* 釜山 AI 旅行助手 v3.1 断言：
 *   A. 追问建议区新增「收起 / 展开」头部：结构、样式、aria、夜间配色
 *   B. 折叠状态持久化（busan_fu_collapsed），三语标签随语言切换，空列表自动隐藏
 *   C. 后台管理台（admin_ui.html）：登录、账号、内容、版本、审计五个面
 *   D. sync.js 真行为：state 解析、版本比较、内容合并、本地缓存应用到 BUSAN_DATA / 云端库
 *   E. 前端接入：BUILD 24/3.1、脚本顺序、设置面板、更新横幅/弹窗文案
 *   F. 版本一致：manifest 24/3.1、PWA 缓存 3.1、构建清单包含新文件
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const A = path.join(ROOT, "android", "assets");
const html = fs.readFileSync(path.join(A, "index.html"), "utf8");
const sync = fs.readFileSync(path.join(A, "sync.js"), "utf8");
const sw = fs.readFileSync(path.join(A, "sw.js"), "utf8");
const adminUi = fs.readFileSync(path.join(ROOT, "admin_ui.html"), "utf8");
const apkMan = fs.readFileSync(path.join(ROOT, "android", "AndroidManifest.xml"), "utf8");
const buildPy = fs.readFileSync(path.join(ROOT, "apk_build", "build_apk.py"), "utf8");

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

/* ---------------- A. 追问区结构 ---------------- */
ok("结构: #followups 内有头部按钮 #fuToggle", /<button class="fu-head" id="fuToggle" type="button" aria-expanded="true" aria-controls="fuBody">/.test(html));
ok("结构: 头部三段（标题 / 条数 / 动作）", /<span class="fu-title" id="fuTitle">/.test(html) && /<span class="fu-sum" id="fuSum">/.test(html) && /<span class="fu-act" id="fuAct">收起<\/span>/.test(html));
ok("结构: 胶囊容器独立为 #fuBody", /<div class="fu-body" id="fuBody"><\/div>/.test(html));
ok("结构: 默认隐藏（无追问时不出头）", /<div id="followups" hidden>/ .test(html));
ok("样式: 外层改为纵向 flex", /flex-direction:column/.test(css("  #followups")) && /overflow:hidden/.test(css("  #followups")));
ok("样式: 折叠时主体 display:none", /#followups\.folded \.fu-body\{display:none\}/.test(html));
ok("样式: 主体仍限高 27vh 可滚动", /max-height:27vh/.test(css("  .fu-body")) && /overflow-y:auto/.test(css("  .fu-body")));
ok("样式: 头部触控高度 ≥36px", /min-height:36px/.test(css("  .fu-head")));
ok("样式: 动作胶囊有底有边", /border:1px solid #cfe3ea/.test(css("  .fu-act")));
ok("夜间: 标题亮蓝", /body\.night \.fu-title\{color:#a9dcec\}/.test(html));
ok("夜间: 动作胶囊深底", /body\.night \.fu-act\{background:#1b2732/.test(html));
ok("夜间: 胶囊深底亮字", /body\.night \.fu-body \.pick\{background:#1a242d/.test(html));

/* ---------------- B. 折叠逻辑 ---------------- */
ok("逻辑: 状态键 busan_fu_collapsed", /localStorage\.getItem\("busan_fu_collapsed"\) === "1"/.test(fn("fuIsFolded")));
ok("逻辑: 折叠写 '1'、展开写 '0'", /fold \? "1" : "0"/.test(fn("setFuFolded")));
ok("逻辑: 折叠加 .folded 类", /classList\.toggle\("folded", folded && n > 0\)/.test(fn("paintFu")));
ok("逻辑: aria-expanded 跟随状态", /setAttribute\("aria-expanded", \(folded && n > 0\) \? "false" : "true"\)/.test(fn("paintFu")));
ok("逻辑: 折叠时显示条数", /folded && n\)[\s\S]{0,40}L\(n \+ " 条 · 点击展开"/.test(fn("paintFu")));
ok("逻辑: 三语标题", /L\("追问建议", "이어서 묻기", "Follow-ups"\)/.test(fn("paintFu")));
ok("逻辑: 三语动作", /L\("展开", "펼치기", "Expand"\)/.test(fn("paintFu")) && /L\("收起", "접기", "Collapse"\)/.test(fn("paintFu")));
ok("逻辑: 头部点击翻转状态", /fuToggle\.onclick = function\(\)\{ setFuFolded\(!fuIsFolded\(\)\); \}/.test(html));
ok("逻辑: 只渲染 5 条以内", /slice\(0, 5\)/.test(fn("renderFollowups")));
ok("逻辑: 渲染进 fuBody 而非整块", /fuBody\.innerHTML = ""/.test(fn("renderFollowups")) && /fuBody\.appendChild\(b\)/.test(fn("renderFollowups")));
ok("逻辑: 无追问时整块隐藏", /followups\.hidden = !list\.length/.test(fn("renderFollowups")));
ok("逻辑: 渲染后刷新头部计数", /paintFu\(\);/.test(fn("renderFollowups")));
ok("逻辑: 换语言重刷头部", /paintThemeBtn\(\);[\s\S]{0,80}paintFu\(\);/.test(fn("applyUI")));
ok("清理: 重绘时只清胶囊并隐藏整块", /if \(fuBody\) fuBody\.innerHTML = ""; followups\.hidden = true;/.test(html));
ok("清理: resetChat 同口径", /resetChat: function\(\)\{ chat\.innerHTML = ""; if \(fuBody\) fuBody\.innerHTML = ""; followups\.hidden = true; \}/.test(html));
ok("不回退: 追问胶囊仍是 .pick 且点击即提问", /b\.className = "pick";[\s\S]{0,80}b\.onclick = function\(\)\{ ask\(q\); \}/.test(fn("renderFollowups")));

/* ---------------- C. 后台管理台 ---------------- */
ok("后台: 单文件管理台存在", adminUi.length > 20000, adminUi.length);
ok("后台: 登录页默认提示 admin/admin", /默认管理员：<code>admin<\/code> \/ <code>admin<\/code>/.test(adminUi));
ok("后台: 五个标签齐全", ["overview", "users", "content", "version", "audit"].every(function(t){
  return adminUi.indexOf('data-tab="' + t + '"') >= 0;
}));
ok("后台: 管理员 / 普通用户两级权限文案", /管理员/.test(adminUi) && /普通用户/.test(adminUi));
ok("后台: 普通用户只读提示", /只能查看账号列表/.test(adminUi) && /只能浏览内容，不能修改/.test(adminUi));
ok("后台: 登录拿 Bearer token", /localStorage\.setItem\('busan_admin_token',state\.token\)/.test(adminUi) && /\['Authorization'\]='Bearer '\+state\.token/.test(adminUi));
ok("后台: 账号表含角色/状态/最近登录", /<th>角色<\/th><th>状态<\/th><th>最近登录<\/th>/.test(adminUi));
ok("后台: 新建/编辑账号可设角色与停用", /id="uRole"/.test(adminUi) && /id="uStatus"/.test(adminUi) && /disabled/.test(adminUi));
ok("后台: 内容页可搜索 + 新增 + 删除", /id="spotSearch"/.test(adminUi) && /id="btnNewSpot"/.test(adminUi) && /id="btnDelSpot"/.test(adminUi));
ok("后台: 三语字段编辑（zh/ko/en 标签）", /\['zh','ko','en'\]\.map/.test(adminUi) && /data-l="'\+l\+'"/.test(adminUi));
ok("后台: 版本发布含版本号与说明", /id="vName"/.test(adminUi) && /id="vCode"/.test(adminUi) && /id="vNotes"/.test(adminUi));
ok("后台: 概览展示 rev 与当前版本", /content?每次保存|每次保存 \+1/.test(adminUi) && /当前版本/.test(adminUi));
ok("后台: 手机接入地址一键复制", /id="baseUrl"/.test(adminUi) && /btnCopyBase/.test(adminUi));

/* ---------------- D. sync.js 真行为 ---------------- */
function fakeLS() {
  const m = {};
  return {
    getItem: k => (k in m ? m[k] : null),
    setItem: (k, v) => { m[k] = String(v); },
    removeItem: k => { delete m[k]; },
    _m: m
  };
}
function loadSync() {
  const store = fakeLS();
  const ctx = {
    console, setTimeout, clearTimeout, setInterval, Promise, JSON, Number, String, Object, Date,
    localStorage: store, navigator: { onLine: true },
    fetch: function(){ return Promise.reject(new Error("offline")); },
    document: {
      readyState: "loading", addEventListener: function(){},
      getElementById: function(){ return null; },
      head: { appendChild: function(){} }, body: { appendChild: function(){} },
      createElement: function(){ return { style: {}, setAttribute(){}, appendChild(){} }; },
      hidden: false
    },
    URL: URL, AbortController: typeof AbortController === "function" ? AbortController : undefined
  };
  ctx.window = ctx;
  ctx.addEventListener = function(){};
  vm.createContext(ctx);
  vm.runInContext(sync, ctx, { filename: "sync.js" });
  return { S: ctx.BusanSync, ctx, store };
}

const { S, ctx, store } = loadSync();
ok("sync: 暴露 BusanSync 接口", !!(S && S.parseState && S.mergeSpots && S.versionNewer && S.applySpots));
ok("sync: 内置 BUILD = 24 / 3.1", S.BUILD.code === 24 && S.BUILD.name === "3.1", JSON.stringify(S.BUILD));
ok("sync: 轮询 25 秒", /var POLL_MS = 25000;/.test(sync));
ok("sync: 回到前台会补一次", /visibilitychange[\s\S]{0,120}pollOnce\(false\)/.test(sync));
ok("sync: 先试 /api/state.json 再试 /api/state", /getJson\(b, "\/api\/state\.json"\)\.catch[\s\S]{0,80}getJson\(b, "\/api\/state"\)/.test(sync));
ok("sync: 内容也双路径", /"\/api\/content\.json"[\s\S]{0,120}"\/api\/content"/.test(sync));
ok("sync: 离线不轮询", /navigator\.onLine === false/.test(sync));

const st1 = S.parseState('{"rev":7,"version":{"code":25,"name":"3.2","notes":"x"}}');
ok("sync: 解析 state 取 rev/version", st1 && st1.rev === 7 && st1.version.code === 25 && st1.version.name === "3.2", JSON.stringify(st1));
ok("sync: 脏 state 不炸", S.parseState("not json") === null && S.parseState("{}").rev === 0);
ok("sync: 25 > 24 判定为新版本", S.versionNewer({ code: 25 }) === true);
ok("sync: 24 不比 24 新", S.versionNewer({ code: 24 }) === false);
ok("sync: 旧版本号不倒灌", S.versionNewer({ code: 23 }) === false);

const merged = S.mergeSpots(
  [{ id: "a", name: "旧名", fields: { zh: { overview: "旧" } } }, { id: "b", name: "B" }],
  [{ id: "a", name: "新名", fields: { zh: { overview: "新" } } }, { id: "c", name: "C" }]
);
ok("sync: 合并保留旧对象并覆盖字段（服务端未下发的旧条目会被剔除）", merged.length === 2 && merged[0].name === "新名" && merged[0].fields.zh.overview === "新" && !merged.some(x => x.id === "b"));
ok("sync: 新增条目直接进库", merged.some(x => x.id === "c" && x.name === "C"));
ok("sync: 软删除条目不再下发", S.mergeSpots([{ id: "a" }, { id: "b" }], [{ id: "a" }]).length === 1);
ok("sync: contentPayload 兼容 spots / content.spots", S.contentPayload({ rev: 3, spots: [{ id: "a" }] }).rev === 3 && S.contentPayload({ content: { spots: [{ id: "a" }] } }).spots.length === 1);
ok("sync: 空内容返回 null", S.contentPayload({ rev: 3, spots: [] }) === null);

/* 应用内容：同时改 BUSAN_DATA 与云端库 */
const baseDb = { spots: [{ id: "a", name: "旧名" }] };
ctx.BUSAN_DATA = { spots: [{ id: "a", name: "旧名" }] };
let setDbCalled = 0;
ctx.BusanCloud = { getDb: () => baseDb, setDb: () => { setDbCalled++; } };
ok("sync: applySpots 改 BUSAN_DATA", S.applySpots([{ id: "a", name: "新名" }, { id: "z", name: "新增" }]) === 2 && ctx.BUSAN_DATA.spots[0].name === "新名" && ctx.BUSAN_DATA.spots.length === 2);
ok("sync: applySpots 同步云端库并回写", baseDb.spots[0].name === "新名" && setDbCalled === 1);
ok("sync: 本地缓存恢复走同一合并", (function(){
  const p = { rev: 9, spots: [{ id: "a", name: "缓存名" }] };
  store.setItem("busan_admin_content", JSON.stringify(p));
  const n = S.applyLocalContent();
  return n === 1 && ctx.BUSAN_DATA.spots[0].name === "缓存名";
})());

/* ---------------- E. 前端接入 ---------------- */
ok("接入: BUILD 常量在页内", /window\.BUSAN_BUILD = { code: 24, name: "3.1" };/ .test(html));
ok("接入: 先 admin_base.js 后 sync.js", html.indexOf('src="admin_base.js"') > 0 && html.indexOf('src="sync.js"') > html.indexOf('src="admin_base.js"'));
ok("接入: sync.js 在 data.js 之后执行启动", html.indexOf('src="sync.js"') > html.indexOf('src="data.js"'));
ok("接入: 设置面板有后台地址输入", /id="syncBase"/.test(html) && /id="syncSave"/.test(html) && /id="syncNow"/.test(html));
ok("接入: 设置面板有状态行", /id="syncStatus"/.test(html));
ok("接入: 三语设置说明", /id="syncDesc"/.test(html) && /内容与版本/.test(html));
ok("接入: 更新横幅文案（后台内容已更新）", /"后台内容已更新（rev "/.test(sync) || /后台内容已更新/.test(sync));
ok("接入: 新版本弹层文案", /"发现新版本"/.test(sync) && /"下载安装包"/.test(sync) && /"跳过这个版本"/.test(sync));
ok("接入: 下载优先本地 /api/download", /state\.base && state\.ok[\s\S]{0,50}"\/api\/download"/.test(sync));
ok("接入: Pages 兜底地址", /https:\/\/luohaisheng814\.github\.io\/AI_Project_2026_2/.test(sync));
ok("接入: 跳过版本记住 code", /ls\(KEY\.skip, String\(v\.code\)\)/.test(sync));
ok("接入: 后台地址手填优先", /var manual = \(ls\(KEY\.base\) \|\| ""\)/.test(sync) && /if \(manual\) list\.push\(manual\)/.test(sync));

/* ---------------- F. 版本一致性 ---------------- */
ok("版本: manifest 24 / 3.1", /android:versionCode="24"/.test(apkMan) && /android:versionName="3.1"/.test(apkMan));
ok("版本: PWA 缓存名升级", /const CACHE = 'busan-3\.1';/.test(sw));
ok("版本: 缓存清单带 admin_base.js 与 sync.js", /'\.\/admin_base\.js'/.test(sw) && /'\.\/sync\.js'/.test(sw));
ok("版本: /api 请求不吃缓存", /url\.pathname\.indexOf\("\/api\/"\) >= 0/.test(sw) && /fetch\(req\)\.catch/.test(sw));
ok("构建: 必需文件清单含 sync.js / admin_base.js", /"sync\.js"/.test(buildPy) && /"admin_base\.js"/.test(buildPy));
ok("构建: 清单也含 sw.js 与 manifest", /"sw\.js"/.test(buildPy) && /"manifest\.webmanifest"/.test(buildPy));
ok("不回退: v3.0 昼夜按钮还在", /<button id="themeBtn"/.test(html) && /function computeNight/.test(html));
ok("不回退: v2.9 推荐条折叠还在", /id="qrecToggle"/.test(html) || /qrec-head/.test(html));

console.log(`\n结果: ${pass} 通过 / ${fail} 失败`);
if (failed.length) {
  console.log("失败项:");
  failed.forEach(f => console.log("  - " + f));
  process.exit(1);
}

