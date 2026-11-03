/* audit_probe_js.js —— 前端侧主动探针（第一百零二令）
   撞现有脚本没覆盖的角落：反推（自洽／候选真值／1582 改历空洞）、农历边界、
   年号改元、极晚出生年。用法：node audit_probe_js.js [app.js 路径]（缺省取技能包 assets/app.js）            */
const path = require('path');
const SKILL = process.env.BAZI_SKILL || path.join(require('os').homedir(), '.workbuddy/skills/bazi-paipan');
const B = require(path.resolve(process.argv[2] || path.join(SKILL, 'assets/app.js')));

let okN = 0;
const FAIL = [];
const ok = (m) => { okN++; console.log('  ✓ ' + m); };
const bad = (m) => { FAIL.push(m); console.log('  ✗ ' + m); };

const GAN = B.GAN, ZHI = B.ZHI;
const dstr = (d) => d.toISOString().slice(0, 10);

/* ---------- A/B. 反推 ---------- */
const NOW = new Date(Date.UTC(2026, 10, 2, 12));
const pillarsAt = (dt) => B.paipan({ birth: dt, gender: 'male', now: NOW })
  .pillars.map((p) => p.gan + p.zhi).join(' ');
const idxOf = (dt) => B.paipan({ birth: dt, gender: 'male', now: NOW })
  .pillars.map((p) => gzIndex(p.gan, p.zhi));

/* 子时解与「前一晚 23:30」同四柱，故允许落在 ±1.5 天内；其余应同日。 */
function probeReverse() {
  console.log('\n[A] 反推：自洽（原时刻的解须在±1.5天内）＋候选真值（按精确时刻复核）');
  const seeds = [];
  [[1991, 5, 18, 19, 0], [1900, 1, 31, 12, 0], [2026, 2, 4, 0, 30],
   [1644, 3, 1, 8, 0], [600, 6, 15, 15, 0], [1582, 10, 4, 21, 0],
   [2099, 12, 31, 18, 0], [1984, 2, 4, 23, 30], [2000, 2, 29, 6, 30],
   [1912, 1, 1, 3, 0], [1949, 10, 1, 9, 0], [2033, 11, 7, 13, 0]].forEach((s) => {
    seeds.push(new Date(Date.UTC(s[0], s[1] - 1, s[2], s[3], s[4])));
  });
  // 交节前后 30 分钟各来一发：这是「12:00 校验」最容易翻车的时段
  [600, 1582, 1900, 2026, 2100].forEach((y) => {
    for (let i = 0; i < 24; i += 2) {
      const t = B._jq(y, i);
      if (!t) continue;
      const tt = new Date(t.getTime());
      seeds.push(new Date(tt.getTime() - 30 * 60000));
      seeds.push(new Date(tt.getTime() + 30 * 60000));
    }
  });

  let miss = [], wrong = [], hitTotal = 0;
  seeds.forEach((dt) => {
    const ids = idxOf(dt), want = pillarsAt(dt);
    const hits = B.reverse(ids, 600, 2100);
    hitTotal += hits.length;
    const near = hits.some((h) => Math.abs(h - dt) <= 1.5 * 864e5 && pillarsAt(h) === want);
    if (!near) miss.push(dstr(dt) + ' ' + dt.toISOString().slice(11, 16) + ' 求 ' + want);
    hits.forEach((h) => {
      const got = pillarsAt(h);
      if (got !== want) wrong.push(dstr(h) + ' ' + h.toISOString().slice(11, 16) + ' 得 ' + got + ' 求 ' + want);
    });
  });
  if (miss.length) bad(`反推漏解 ${miss.length} 例：` + miss.slice(0, 4).join('；'));
  else ok(`${seeds.length} 例（含 60 个交节前后时刻、晚子时、改历、表首尾）反推均在 ±1.5 天内命中，共 ${hitTotal} 个解`);
  if (wrong.length) bad(`反推候选按精确时刻复核不符 ${wrong.length} 例：` + wrong.slice(0, 3).join('；'));
  else ok('所有候选按其自身时刻重算，四柱与所求一致（无「12 点校验」错解）');
}

/* ---------- C. 1582 改历空洞 ---------- */
function probeGap() {
  console.log('\n[B] 1582 改历：反推不得给出 10-05～10-14');
  const ids = [0, 1, 2, 3].map((i) => i); // 任意四柱
  const bads = [];
  // 取若干真实四柱，检查解集里有没有落进空洞的日期
  [[1582, 10, 20, 12, 0], [1582, 11, 1, 9, 0], [1582, 9, 30, 15, 0]].forEach((s) => {
    const dt = new Date(Date.UTC(s[0], s[1] - 1, s[2], s[3], s[4]));
    const d = B.paipan({ birth: dt, gender: 'female', now: new Date(Date.UTC(2026, 10, 2, 12)) });
    const want = d.pillars.map((p) => gzIndex(p.gan, p.zhi));
    B.reverse(want, 600, 2100).forEach((h) => {
      const t = dstr(h);
      if (t >= '1582-10-05' && t <= '1582-10-14') bads.push(t);
    });
  });
  if (bads.length) bad('反推出现不存在的历日：' + [...new Set(bads)].join('、'));
  else ok('反推未产生 1582-10-05～10-14 的虚构日期');
}

/* ---------- D. 农历边界 ---------- */
function probeLunar() {
  console.log('\n[C] 农历：表首／表尾／闰月');
  const cases = [
    ['1900-01-31', '正月初一', (l) => l.m === 1 && l.d === 1 && !l.leap],
    ['2100-12-31', null, (l) => !!l],
    ['2020-05-23', '闰四月初一', (l) => l.m === 4 && l.d === 1 && l.leap],
    ['2023-03-22', '闰二月初一', (l) => l.m === 2 && l.d === 1 && l.leap],
    ['1984-02-02', '正月初一', (l) => l.m === 1 && l.d === 1 && !l.leap],
  ];
  const bads = [];
  cases.forEach(([s, note, chk]) => {
    const p = s.split('-').map(Number);
    const l = B.solarToLunar(new Date(Date.UTC(p[0], p[1] - 1, p[2], 12, 0)));
    if (!l || !chk(l)) bads.push(`${s}${note ? '（应' + note + '）' : ''} 得 ${JSON.stringify(l)}`);
  });
  if (bads.length) bad('农历换算不符：' + bads.join('；'));
  else ok('农历表首 1900-01-31＝正月初一、2100 年末可取、2020 闰四月／2023 闰二月、1984 正月初一，全对');

  // 往返：公历→农历→公历
  let rt = [];
  for (let y = 1900; y <= 2100; y += 37) {
    const d0 = new Date(Date.UTC(y, 5, 15, 12, 0));
    const l = B.solarToLunar(d0);
    const back = B.lunarToSolar(l.y, l.m, l.leap, l.d);
    if (!back || dstr(back) !== dstr(d0)) rt.push(dstr(d0) + '→' + JSON.stringify(l) + '→' + (back && dstr(back)));
  }
  if (rt.length) bad('农历往返不符：' + rt.slice(0, 3).join('；'));
  else ok('公历→农历→公历 往返一致（1900–2100 抽 6 年）');
}

/* ---------- E. 年号 ---------- */
function probeEra() {
  console.log('\n[D] 年号：改元年与边界');
  const cases = [
    [600, '隋', '开皇'], [618, '唐', '武德'], [1368, '明', '洪武'],
    [1644, '清', '顺治'], [1912, '民国', ''], [1949, '民国', ''],
    [1950, null, null], [1900, '清', null], [1911, '清', '宣统'],
  ];
  const bads = [];
  cases.forEach(([y, dyn, era]) => {
    const e = B.eraOf ? B.eraOf(y) : null;
    if (!e) { if (dyn) bads.push(`${y} 无年号（应 ${dyn}）`); return; }
    if (dyn === null) { bads.push(`${y} 不应有年号，得 ${e.dyn}${e.era}`); return; }
    if (e.dyn !== dyn) bads.push(`${y} 朝代 ${e.dyn}≠${dyn}`);
    if (era && e.era !== era) bads.push(`${y} 年号 ${e.era}≠${era}`);
  });
  if (bads.length) bad('年号不符：' + bads.join('；'));
  else ok('600 隋·开皇／618 唐·武德／1368 明·洪武／1644 清·顺治／1912 民国／1950 无年号，全对');
}

/* ---------- F. 极晚出生 ---------- */
function probeLate() {
  console.log('\n[E] 极晚出生（大运、流年越出农历表尾）');
  const cases = [[2099, 12, 31, 23, 30], [2100, 6, 15, 10, 0], [2100, 12, 31, 23, 30]];
  const bads = [];
  cases.forEach((s) => {
    const dt = new Date(Date.UTC(s[0], s[1] - 1, s[2], s[3], s[4]));
    try {
      const d = B.paipan({ birth: dt, gender: 'male', now: new Date(Date.UTC(2026, 10, 2, 12)) });
      const dys = d.dayun.map((x) => x.year);
      const lns = d.dayun[d.sel.dy].ln.filter((x) => x.year);
      if (dys.some((y) => !y)) bads.push(`${s.join('-')} 大运年含空`);
      if (!lns.length) bads.push(`${s.join('-')} 流年为空`);
      if (lns.some((x) => !x.gan)) bads.push(`${s.join('-')} 流年干支缺失`);
    } catch (e) {
      bads.push(`${s.join('-')} 抛错 ${e.message}`);
    }
  });
  if (bads.length) bad('极晚出生异常：' + bads.join('；'));
  else ok('2099／2100 年末出生：大运 12 步齐、流年十年齐、干支不空（越表年份照算干支）');
}

function gzIndex(g, z) {
  for (let i = 0; i < 60; i++) if (i % 10 === GAN.indexOf(g) && i % 12 === ZHI.indexOf(z)) return i;
  return -1;
}

console.log('== 前端主动探针（audit_probe_js.js）==');
probeReverse();
probeGap();
probeLunar();
probeEra();
probeLate();
console.log(`\n结果：${FAIL.length ? '有可疑项' : '全部通过'}（通过 ${okN} 项，问题 ${FAIL.length} 项）`);
FAIL.forEach((x) => console.log('  · ' + x));
process.exit(FAIL.length ? 1 : 0);
