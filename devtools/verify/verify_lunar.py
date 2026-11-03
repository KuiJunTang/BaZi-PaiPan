#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# —— devtools 引导：把技能包的 scripts 放进 import 路径（第一百一十令）——
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from paths import SKILL as SKILL_DIR, PROJ as PROJ_DIR  # noqa: E402
_sys.path.insert(0, _os.path.join(SKILL_DIR, "scripts"))
# —— 引导结束 ——

"""verify_lunar.py —— 前端农历表与 sxtwl 对拍（含闰月、回推）"""
import datetime, json, os, random, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
APP = os.path.abspath(os.path.join(SKILL_DIR, "assets", "app.js"))

JS = r"""
const B = require(process.argv[2]);
const cases = JSON.parse(require('fs').readFileSync(process.argv[3], 'utf8'));
const out = cases.map(c => {
  const dt = new Date(Date.UTC(c[0], c[1]-1, c[2], 12, 0));
  const l = B.solarToLunar(dt);
  let back = null;
  if (l) { const s = B.lunarToSolar(l.y, l.m, l.leap, l.d);
    back = [s.getUTCFullYear(), s.getUTCMonth()+1, s.getUTCDate()]; }
  return l ? [l.y, l.m, l.leap, l.d, back] : null;
});
process.stdout.write(JSON.stringify(out));
"""

def main():
    import sxtwl
    rnd = random.Random(7)
    cases = []
    d = datetime.date(1900, 2, 1)
    while d <= datetime.date(2100, 12, 31):
        cases.append([d.year, d.month, d.day]); d += datetime.timedelta(days=7)
    for _ in range(400):
        d = datetime.date(1900, 2, 1) + datetime.timedelta(days=rnd.randint(0, 73000))
        cases.append([d.year, d.month, d.day])
    with tempfile.TemporaryDirectory() as td:
        cp = os.path.join(td, "c.json"); jp = os.path.join(td, "r.js")
        json.dump(cases, open(cp, "w")); open(jp, "w").write(JS)
        r = subprocess.run(["node", jp, APP, cp], capture_output=True, text=True, timeout=180)
        if r.returncode: print(r.stderr[-600:]); return 1
        js = json.loads(r.stdout)
    bad = rt = 0; first = None
    for c, j in zip(cases, js):
        o = sxtwl.fromSolar(c[0], c[1], c[2])
        want = [o.getLunarYear(), o.getLunarMonth(), bool(o.isLunarLeap()), o.getLunarDay()]
        if j is None or j[:4] != want:
            bad += 1
            if not first: first = (c, want, j)
        if j and j[4] != c:
            rt += 1
            if not first: first = (c, "回推", j[4])
    print("农历对拍 %d 天（含随机 400 天）" % len(cases))
    print("  转换不符 %d；闰月/腊月回推不符 %d" % (bad, rt))
    if first: print("  首例：", first)
    print("结果：%s" % ("一致" if bad == 0 and rt == 0 else "有差异"))
    return 0 if bad == 0 and rt == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
