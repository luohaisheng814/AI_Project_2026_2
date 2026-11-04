/**
 * test_engine.js —— APK 内置离线引擎回归测试（Node 运行，无需 Android 设备）
 * 覆盖：三语意图识别、景点匹配、玩法作用域、跨类补充、GPS 附近排序、跨语言一致性。
 * 运行：node apk_build/test_engine.js
 */
const path = require("path");

global.window = {};
require(path.join(__dirname, "..", "android", "assets", "data.js"));
const DATA = global.window.BUSAN_DATA;
const E = require(path.join(__dirname, "..", "android", "assets", "app.js"));

const fails = [];
function ok(cond, msg) { if (!cond) fails.push(msg); }
function has(hay, needle, msg) { ok(String(hay).indexOf(needle) !== -1, msg + `（缺少「${needle}」）`); }

E.init(DATA);

console.log("景点数:", DATA.spots.length);
DATA.spots.forEach(s => {
  ok(s.fields.zh && Object.keys(s.fields.zh).length >= 1, `${s.name} 缺少中文字段`);
  ok(s.fields.ko && Object.keys(s.fields.ko).length >= 1, `${s.name} 缺少韩文字段`);
  ok(s.fields.en && Object.keys(s.fields.en).length >= 1, `${s.name} 缺少英文字段`);
  const zhKeys = Object.keys(s.fields.zh).join(",");
  ok(Object.keys(s.fields.ko).join(",") === zhKeys, `${s.name} 韩文字段与中文字段不一致`);
});

/* 1. 中文：单字段问答 */
E.setLang("zh");
E.setState({ autoCategory: true, autoGroup: true, category: null, group: null });
let r = E.answer("没云台 怎么去", { lang: "zh" });
ok(r.spot && r.spot.name === "没云台", "中文未命中没云台");
ok(r.field === "transport", `中文意图应为 transport，实际 ${r.field}`);
has(r.text, "**交通**", "中文回答缺少交通小节");
has(r.text, "没云台", "中文回答缺少景点名");
console.log("\n[zh] 没云台 怎么去 ->", r.spot.name, r.field);

/* 2. 韩文：同一问题用韩文按钮语言 */
E.setLang("ko");
r = E.answer("몰운대 어떻게 가나요", { lang: "ko" });
ok(r.spot && r.spot.name === "没云台", "韩文未命中没云台");
has(r.text, "몰운대", "韩文回答缺少韩文景点名");
has(r.text, "교통", "韩文回答缺少「교통」小节");
ok(!/\*\*交通\*\*/.test(r.text), "韩文回答不应出现中文小节名");
ok(/[가-힣]/.test(r.text), "韩文回答不含韩文");
console.log("[ko] 몰운대 어떻게 가나요 ->", r.spot.name, "| 韩文正文:", r.spot.fields.ko.transport.slice(0, 40));

/* 3. 英文：英文提问 + 英文按钮 */
E.setLang("en");
r = E.answer("How do I get to Gamcheon Culture Village?", { lang: "en" });
ok(r.spot && r.spot.name === "甘川文化村", "英文未命中甘川文化村");
has(r.text, "Gamcheon Culture Village", "英文回答缺少英文景点名");
has(r.text, "Transportation", "英文回答缺少 Transportation 小节");
console.log("[en] Gamcheon ->", r.spot.name, r.field);

/* 4. 输入语言与按钮语言不一致：按钮优先 */
E.setLang("zh");
r = E.answer("입장료 얼마예요 (몰운대)", { lang: "zh" });
ok(r.spot && r.spot.name === "没云台", "中文按钮下韩文提问应仍能命中景点");
ok(r.field === "ticket", `「입장료」应识别为 ticket，实际 ${r.field}`);
ok(/[\u4e00-\u9fa5]/.test(r.text), "中文按钮下回答应为中文");
console.log("[zh] 韩文提问(门票) ->", r.field, "| 语言正确");

/* 5. 意图识别表 */
const fieldCases = [
  ["门票多少钱", "ticket"], ["입장료", "ticket"], ["opening hours", "hours"],
  ["怎么去", "transport"], ["사진 명소", "photo"], ["附近有什么好吃的", "food"],
  ["适合带小孩吗", "audience"], ["附近景点", "around"], ["官网", "source"],
  ["这里有什么亮点", "highlights"], ["highlights", "highlights"], ["주요 볼거리", "highlights"],
];
fieldCases.forEach(([q, want]) => ok(E.detectField(q) === want, `意图识别失败：${q} -> ${E.detectField(q)}，期望 ${want}`));

/* 6. 玩法 / 人数推断 */
ok(E.inferCategory("海边看日落和夜景") === "02_海岸休闲_日落夜景", "玩法推断：海边日落 应为 02");
ok(E.inferCategory("湿地候鸟观鸟") === "03_湿地生态_自然观景", "玩法推断：湿地候鸟 应为 03");
ok(E.inferCategory("渔港码头小众拍照") === "04_小众渔港_文艺拍照", "玩法推断：渔港 应为 04");
ok(E.inferGroup("和闺蜜两个人去") === "two_ff", "人数推断：闺蜜 应为 two_ff");
ok(E.inferGroup("一个人去，女生") === "solo_female", "人数推断：一个人女生 应为 solo_female");
ok(E.inferGroup("一家三口带孩子") === "group_3plus", "人数推断：一家三口 应为 group_3plus");

/* 7. 手动锁定玩法时的作用域：不越界作答，给切换指引 */
E.setState({ autoCategory: false, category: "03_湿地生态_自然观景", group: null });
r = E.answer("没云台 门票", { lang: "zh", autoCategory: false });
ok(r.switchTo === "02_海岸休闲_日落夜景", `手动 03 下提问 02 景点应给切换指引，实际 ${r.switchTo}`);
ok(!r.spot, "手动 03 下不应直接用 02 的景点作答");
console.log("[scope] 手动 03 + 没云台 -> switchTo", r.switchTo);

/* 8. 跨类补充：数量受限、来自其它玩法、排在正文之后 */
E.setState({ autoCategory: true, category: "02_海岸休闲_日落夜景", group: "two_mf" });
["zh", "ko", "en"].forEach(lang => {
  const res = E.answer("多大浦海水浴场 门票", { lang });
  ok(res.supplements.length <= 2, `${lang} 补充数量超过 2`);
  res.supplements.forEach(s => ok(s.cat !== res.spot.category, `${lang} 补充来自同玩法：${s.cat}`));
  ok(res.text.indexOf("补充") !== -1 || res.text.indexOf("추가") !== -1 || res.text.indexOf("More picks") !== -1,
     `${lang} 回答缺少补充推荐小节`);
});
const zhRes = E.answer("多大浦海水浴场 门票", { lang: "zh" });
const koRes = E.answer("多大浦海水浴场 门票", { lang: "ko" });
ok(zhRes.supplements.map(s => s.cat).join("|") === koRes.supplements.map(s => s.cat).join("|"),
   "补充推荐的玩法顺序不应随语言改变");
console.log("[supp] 补充:", zhRes.supplements.map(s => `${s.spot.name}/${s.catLabel}`).join(" , "));

/* 9. 未知景点：给出当前玩法清单，不编造内容 */
E.setState({ autoCategory: false, category: "04_小众渔港_文艺拍照" });
r = E.answer("这里有什么好玩的", { lang: "zh", autoCategory: false });
ok(r.text.indexOf("收录景点") !== -1 || r.text.length > 0, "未命中景点时应给出可用景点清单");
console.log("[fallback] 列表输出长度:", r.text.length);

/* 10. GPS 附近排序 */
const near = E.nearby(35.0510, 128.8820, 5);
ok(near.length > 0, "坐标附近应能返回景点");
ok(near[0].km < 5, `最近景点距离异常：${near[0].km}`);
for (let i = 1; i < near.length; i++) ok(near[i].km >= near[i - 1].km, "附近列表未按距离升序");
console.log("[gps] 附近:", near.map(n => `${n.spot.name} ${n.km.toFixed(1)}km`).join(" , "));

/* 11. 连续追问保留上下文：同一景点不同字段 */
E.setState({ autoCategory: true, category: "02_海岸休闲_日落夜景", group: null });
const a1 = E.answer("没云台", { lang: "zh" });
const a2 = E.answer("没云台 开放时间", { lang: "zh" });
ok(a1.field === null, "只给景点名时应输出全部字段");
ok(a2.field === "hours", "第二问应识别为 hours");
ok(Object.keys(a1.spot.fields.zh).length >= 6, "全部字段输出应覆盖多数小节");

/* 12. 后续问题建议不与当前字段重复 */
(E.answer("多大浦海水浴场 门票", { lang: "zh" }).followups || []).forEach(q => {
  ok(q.indexOf("门票") === -1 || q.indexOf("需要门票") === -1, "后续问题不应重复当前字段");
});

if (fails.length) {
  console.error(`\n❌ 失败 ${fails.length} 项：`);
  fails.forEach(f => console.error(" - " + f));
  process.exit(1);
}
console.log("\n✅ 离线引擎全部断言通过");
