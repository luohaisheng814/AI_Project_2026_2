const fs = require('fs');
const vm = require('vm');
global.window = global;
global.BusanLive = { position: () => ({ lat: 35.10, lng: 129.03, accuracy: 38, provider: 'gps' }) };
global.BusanHost = null;
vm.runInThisContext(fs.readFileSync('android/assets/cloud_snapshot.js', 'utf8'));
vm.runInThisContext(fs.readFileSync('android/assets/photos.js', 'utf8'));
vm.runInThisContext(fs.readFileSync('android/assets/cloud.js', 'utf8'));
BusanCloud.setDb(window.BUSAN_CLOUD_SNAPSHOT);
BusanCloud.init('zh');
let pass = 0, fail = 0;
function ok(name, cond, detail = '') {
  if (cond) { pass++; console.log('PASS', name, detail); }
  else { fail++; console.log('FAIL', name, detail); }
}
ok('spots=18', BusanCloud.allSpots().length === 18, BusanCloud.allSpots().length);
ok('photos every spot >=2', BusanCloud.allSpots().every(s => (window.BUSAN_PHOTOS[s.id] || []).length >= 2),
  BusanCloud.allSpots().map(s => s.id + ':' + (window.BUSAN_PHOTOS[s.id] || []).length).join(' '));
ok('photos total 54', Object.values(window.BUSAN_PHOTOS).reduce((n, v) => n + v.length, 0) === 54);
ok('map label NAVER jump', BusanCloud.strings().jump.indexOf('NAVER') >= 0, BusanCloud.strings().jump);
ok('map label NAVER webmap', BusanCloud.strings().webmap.indexOf('NAVER') >= 0, BusanCloud.strings().webmap);
ok('map label Google', BusanCloud.strings().google.indexOf('Google') >= 0, BusanCloud.strings().google);
ok('alias 看川', BusanCloud.findSpot('看川').name === '甘川文化村');
ok('alias 甘村', BusanCloud.findSpot('甘村').name === '甘川文化村');
ok('alias 甘村文化村', BusanCloud.findSpot('甘村文化村').name === '甘川文化村');
ok('alias 乙淑岛', BusanCloud.findSpot('乙淑岛').name === '乙淑岛候鸟公园');
ok('alias 长林浦', BusanCloud.findSpot('长林浦').name === '长林浦口');
const route = BusanCloud.routeTo(BusanCloud.findSpot('甘村'), { lat: 35.10, lng: 129.03, accuracy: 38 });
ok('route kind', route && route.kind === 'route');
ok('route 3 links', route && route.links.length === 3);
ok('route best', route && /最优建议/.test(route.text));
ok('route distance 4.8', route && /4.8 km/.test(route.text));
ok('route km meta', route && Math.abs(route.routeMeta.km - 4.84) < 0.05);
ok('route links nmap', route && route.links.every(l=>/nmap:\/\/route/.test(l.href)));
ok('route has photos', route && route.photos && route.photos.length === 3, route && route.photos.length);
const spotAnswer = BusanCloud.answer('甘川文化村 门票', {lang:'zh'});
ok('spot answer has photos', spotAnswer && spotAnswer.photos && spotAnswer.photos.length === 3, spotAnswer && spotAnswer.photos.length);
const nearBest = BusanCloud.routeTo(BusanCloud.findSpot('南浦洞'), { lat: 35.10, lng: 129.03, accuracy: 38 });
ok('best walk <=1.2km', nearBest && /步行\/无障碍优先/.test(nearBest.text), nearBest && nearBest.routeMeta.km);
const farBest = BusanCloud.routeTo(BusanCloud.findSpot('海云台'), { lat: 35.10, lng: 129.03, accuracy: 38 });
ok('best transit >7km', farBest && /公共交通优先 \+ 打车备选/.test(farBest.text), farBest && farBest.routeMeta.km);
const noPos = BusanCloud.routeTo(BusanCloud.findSpot('甘川'), null);
ok('route no pos fallback', noPos && /还没拿到当前位置/.test(noPos.text));
ok('answer route', BusanCloud.answer('去甘村文化村的路线有几条可以推荐的', {lang:'zh'}).kind === 'route');
ok('spot ticket', /免费/.test(BusanCloud.answer('甘川文化村 门票', {lang:'zh'}).text));
ok('recommend morning', BusanCloud.recommend('morning','上午去哪里').choices.length === 3);
const groups = ['一个人男性推荐','一个人女性推荐','两个人男女推荐','两个男生推荐','两个女生推荐','三个人以上推荐'];
const expected = ['solo_male','solo_female','two_mf','two_mm','two_ff','group_3plus'];
ok('group recognition', groups.every((q,i)=>BusanCloud.groupOf(q)===expected[i]));
groups.forEach((q,i)=>{
  const r = BusanCloud.answer(q, {lang:'zh'});
  ok('group answer '+expected[i], r.choices && r.choices.length === 3, r.choices && r.choices.map(c=>c.name).join('/'));
});
ok('theme combo', BusanCloud.groupRecommend('solo_male','any','推荐','01_艺术村落_文化街区').choices[0].name === '甘川文化村');
const near = BusanCloud.nearbyRoutes({lat:35.10,lng:129.03,accuracy:38}, '附近的景点怎么去', 3);
ok('nearby 3 points', near && near.choices && near.choices.length === 3, near && near.choices.map(x=>x.name).join('/'));
ok('nearby text nearest', near && /南浦洞BIFF广场/.test(near.text));
BusanCloud.setDb(BUSAN_CLOUD_SNAPSHOT);
BusanCloud.setLang('zh');
global.BusanUI = { getLang: () => 'zh', isAutoGrp: () => true, getGrp: () => '', online: () => false };
vm.runInThisContext(fs.readFileSync('android/assets/planner.js', 'utf8'));
const cases = [
  ['去甘村文化村的路线有几条可以推荐的', false],
  ['甘川文化村路线规划', true],
  ['从当前位置去甘川文化村有几条路线', false],
  ['甘川文化村怎么去', false],
  ['甘川文化村 门票', false],
  ['半天想拍照，少走路，帮我安排', true]
];
cases.forEach(c=>ok('intercept '+c[0], BusanPlanner.intercept(c[0]) === c[1], String(BusanPlanner.intercept(c[0]))));
const parties = ['solo_male','solo_female','two_mf','two_mm','two_ff','group_3plus'];
parties.forEach(pt=>{
  const pl = BusanPlanner.buildLocal('半天拍照，少走路', {party:pt});
  ok('planner '+pt, pl && pl.ctx && pl.ctx.party === pt && pl.choices.length >= 2, pl && pl.choices.map(c=>c.name).join('/'));
});
vm.runInThisContext(fs.readFileSync('android/assets/data.js', 'utf8'));
vm.runInThisContext(fs.readFileSync('android/assets/app.js', 'utf8'));
BusanEngine.init(window.BUSAN_DATA);
ok('offline engine spot', /甘川/.test(BusanEngine.answer('甘川文化村', {lang:'zh'}).text));
ok('offline group infer', BusanEngine.inferGroup('一个人女性推荐') === 'solo_female');
ok('offline field detect', BusanEngine.detectField('甘川文化村 门票') === 'ticket');
console.log('SUMMARY', {pass, fail});
process.exit(fail ? 1 : 0);
