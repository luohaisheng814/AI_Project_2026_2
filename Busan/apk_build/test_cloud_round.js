/* 本轮 cloud.js 回归测试：单链接来源 + 条件化推荐 */
const fs = require("fs");
const vm = require("vm");
const path = "D:/AI_Project_2026_2/Busan/android/assets/";

global.window = global;
window.BUSAN_CLOUD_SNAPSHOT = JSON.parse(fs.readFileSync(path + "cloud_snapshot.json", "utf8"));
eval(fs.readFileSync(path + "cloud.js", "utf8"));

const C = window.BusanCloud;
C.init("zh");
C.setDb(window.BUSAN_CLOUD_SNAPSHOT);

const cases = [
  ["甘川文化村", "只点景点名"],
  ["甘川文化村 轮椅 怎么去", "轮椅 + 交通"],
  ["甘川文化村 带孩子 拍照", "亲子 + 拍照"],
  ["峨嵋山观景台 门票", "无官网 url 的 fallback"],
  ["乙淑岛候鸟公园 日落 免费", "日落 + 免费"],
  ["甘川文化村 少走路 半天", "少走路 + 半天"]
];

for (const [q, label] of cases) {
  const r = C.answer(q);
  console.log("\n=== " + label + " :: " + q + " ===");
  console.log("sourceUrl=" + r.sourceUrl);
  console.log("sources=" + JSON.stringify(r.sources));
  console.log(r.text);
}

C.setLang("ko");
console.log("\n=== KO :: 감천문화마을 휠체어 ===");
console.log(C.answer("감천문화마을 휠체어").text);

C.setLang("en");
console.log("\n=== EN :: Gamcheon wheelchair ===");
console.log(C.answer("Gamcheon wheelchair").text);
