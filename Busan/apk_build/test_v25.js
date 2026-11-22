/* v2.5 回归：天气适配、天气变化检测、星级评级 */
const fs = require('fs');
const vm = require('vm');
global.window = global;

const store = {};
global.localStorage = {
  getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: k => { delete store[k]; }
};

vm.runInThisContext(fs.readFileSync('android/assets/cloud_snapshot.js', 'utf8'));
vm.runInThisContext(fs.readFileSync('android/assets/photos.js', 'utf8'));
vm.runInThisContext(fs.readFileSync('android/assets/cloud.js', 'utf8'));
vm.runInThisContext(fs.readFileSync('android/assets/ratings.js', 'utf8'));
vm.runInThisContext(fs.readFileSync('android/assets/weather.js', 'utf8'));
BusanCloud.setDb(window.BUSAN_CLOUD_SNAPSHOT);
BusanCloud.init('zh');

let pass = 0, fail = 0;
function ok(name, cond, detail = '') {
  if (cond) { pass++; console.log('PASS', name, detail); }
  else { fail++; console.log('FAIL', name, detail); }
}

const spots = BusanCloud.allSpots();
ok('spots=18', spots.length === 18, spots.length);

/* ---- 星级 ---- */
ok('rating traits 18', Object.keys(BusanRating.base).length === 18);
spots.forEach(s => {
  const r = BusanRating.of(s.id);
  ok('rating ' + s.id, !!r && r.score >= 3.5 && r.score <= 5 &&
    ['play', 'view', 'ease', 'value'].every(k => r[k] >= 1 && r[k] <= 5),
    r && r.score);
});
ok('starsText 4.5', BusanRating.starsText(4.5) === '★★★★☆', BusanRating.starsText(4.5));
ok('starsText 5', BusanRating.starsText(5) === '★★★★★');
ok('grade 4.7', BusanRating.grade(4.7) === '强烈推荐', BusanRating.grade(4.7));
ok('summary has 4 axes', /玩法/.test(BusanRating.summary('甘川文化村')) && /性价比/.test(BusanRating.summary('甘川文化村')));
ok('catAvg 海岸', BusanRating.catAvg('02_海岸休闲_日落夜景') >= 4.0, BusanRating.catAvg('02_海岸休闲_日落夜景'));
ok('categorySummary 4 groups', BusanRating.categorySummary().length === 4, BusanRating.categorySummary().map(x => x.label + ':' + x.stars).join(' '));
ok('user rating default 0', BusanRating.userOf('甘川文化村') === 0);
BusanRating.setUser('甘川文化村', 4);
ok('user rating saved', BusanRating.userOf('甘川文化村') === 4 && store['busan_rating_user'].indexOf('"甘川文化村":4') > 0);
BusanRating.setUser('甘川文化村', 0);
ok('user rating cleared', BusanRating.userOf('甘川文化村') === 0);
ok('starsHtml half', /width:80%/.test(BusanRating.starsHtml(4)), BusanRating.starsHtml(4).slice(0, 90));

/* ---- 天气 ---- */
ok('WMO 0 clear', BusanWeather.classOf(0) === 'clear');
ok('WMO 2 cloudy', BusanWeather.classOf(2) === 'cloudy');
ok('WMO 45 fog', BusanWeather.classOf(45) === 'fog');
ok('WMO 61 rain', BusanWeather.classOf(61) === 'rain');
ok('WMO 71 snow', BusanWeather.classOf(71) === 'snow');
ok('WMO 95 storm', BusanWeather.classOf(95) === 'storm');
ok('traits 18', Object.keys(BusanWeather.traits).length === 18);

const clear = { cls: 'clear', temp: 24, wind: 3.2, precipProb: 10 };
const rain = { cls: 'rain', temp: 18, wind: 6, precipProb: 85 };
const hot = { cls: 'clear', temp: 33, wind: 2, precipProb: 5 };
const cold = { cls: 'cloudy', temp: -2, wind: 11, precipProb: 20 };

const recClear = BusanWeather.recommend(clear, 3);
const recRain = BusanWeather.recommend(rain, 3);
const recHot = BusanWeather.recommend(hot, 3);
const recCold = BusanWeather.recommend(cold, 3);

ok('clear top is coast', recClear.some(r => ['海云台海水浴场', '广安里海水浴场', '松岛海水浴场', '多大浦海水浴场'].includes(r.id)),
  recClear.map(r => r.id + ':' + r.score).join(' '));
ok('rain top indoor', ['西面', '洛东江河口生态中心'].includes(recRain[0].id), recRain.map(r => r.id + ':' + r.score).join(' '));
ok('rain punish beach', BusanWeather.fitOf('海云台海水浴场', rain) < BusanWeather.fitOf('西面', rain),
  BusanWeather.fitOf('海云台海水浴场', rain) + ' < ' + BusanWeather.fitOf('西面', rain));
ok('hot favours shade', BusanWeather.fitOf('洛东江河口生态中心', hot) > BusanWeather.fitOf('甘川文化村', hot),
  BusanWeather.fitOf('洛东江河口生态中心', hot) + ' > ' + BusanWeather.fitOf('甘川文化村', hot));
ok('cold top indoor', recCold[0].id === '西面' || recCold[0].id === '洛东江河口生态中心', recCold[0].id);
ok('cold punish coast', BusanWeather.fitOf('海云台海水浴场', cold) < BusanWeather.fitOf('西面', cold));
ok('wind punish coast', BusanWeather.fitOf('广安里海水浴场', cold) < BusanWeather.fitOf('龙头山公园', cold));
ok('rain tips umbrella', BusanWeather.tips(rain).some(t => /伞|우산|umbrella/.test(t)), BusanWeather.tips(rain).join(' | '));
ok('storm tips avoid coast', BusanWeather.tips({ cls: 'storm', temp: 22, wind: 16, precipProb: 95 }).some(t => /海边|해변|beach/.test(t)));
ok('recommend 3 distinct', recClear.length === 3 && new Set(recClear.map(r => r.id)).size === 3);
ok('recommend reason', recRain[0].reason.length > 0, recRain[0].reason);

ok('diff none when same', BusanWeather.diff(clear, Object.assign({}, clear)).length === 0);
const d1 = BusanWeather.diff(clear, rain);
ok('diff class clear->rain', d1.some(c => c.type === 'class' && c.from === 'clear' && c.to === 'rain'), JSON.stringify(d1));
ok('diff rain prob', d1.some(c => c.type === 'rain'));
const d2 = BusanWeather.diff(Object.assign({}, clear, { temp: 24 }), Object.assign({}, clear, { temp: 31 }));
ok('diff temp +7', d2.some(c => c.type === 'temp' && c.up === true), JSON.stringify(d2));
const d3 = BusanWeather.diff(clear, cold);
ok('diff wind 11', d3.some(c => c.type === 'wind'), JSON.stringify(d3));
ok('changeText has advise', /更适合|적합|Better/.test(BusanWeather.changeText(d1, rain)), BusanWeather.changeText(d1, rain).split('\n')[0]);

const sample = {
  latitude: 35.1, longitude: 129.0, timezone: 'Asia/Seoul',
  current: { temperature_2m: 21.4, relative_humidity_2m: 66, apparent_temperature: 21.0, precipitation: 0, weather_code: 61, wind_speed_10m: 7.2 },
  hourly: {
    time: ['2026-11-22T10:00', '2026-11-22T11:00', '2026-11-22T12:00', '2026-11-22T13:00'],
    precipitation_probability: [20, 55, 80, 90],
    temperature_2m: [21, 21, 22, 22], weather_code: [61, 61, 63, 63]
  },
  daily: { temperature_2m_max: [23.1], temperature_2m_min: [15.2], weather_code: [61], precipitation_probability_max: [90] }
};
const now = new Date('2026-11-22T10:30:00+09:00').getTime();
ok('parse class rain', BusanWeather.parse(sample).cls === 'rain');
ok('parse temp', BusanWeather.parse(sample).temp === 21.4);
ok('parse daily', BusanWeather.parse(sample).max === 23.1 && BusanWeather.parse(sample).min === 15.2);
ok('url has lat/lng', /latitude=35\.1796/.test(BusanWeather.url(35.1796, 129.0756)) && /current=temperature_2m/.test(BusanWeather.url(35.1796, 129.0756)));

BusanWeather.clear();
const w0 = BusanWeather.manual('rain');
ok('manual state', BusanWeather.state().cls === 'rain' && BusanWeather.state().manual === true);
ok('banner manual', /雨|비|Rain/.test(BusanWeather.banner(w0)), BusanWeather.banner(w0));
BusanWeather.setLang('en');
ok('banner en', /Rain/.test(BusanWeather.banner(w0)), BusanWeather.banner(w0));
BusanWeather.setLang('zh');

/* ---- 天气提示（UI 里 wxAdapt 用的就是这套结果） ---- */
const note = BusanWeather.recommend(rain, 2).map(r => r.name).join('、');
ok('rain note names indoor', /洛东江河口生态中心|西面/.test(note), note);
const noteClear = BusanWeather.recommend(clear, 2).map(r => r.name).join('、');
ok('clear note names coast', /海水浴场|梦之夕阳|没云台/.test(noteClear), noteClear);

console.log('SUMMARY', { pass, fail });
process.exit(fail ? 1 : 0);
