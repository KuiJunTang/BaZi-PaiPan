#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# —— devtools 引导：把技能包的 scripts 放进 import 路径（第一百一十令）——
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from paths import SKILL as SKILL_DIR, PROJ as PROJ_DIR  # noqa: E402
_sys.path.insert(0, _os.path.join(SKILL_DIR, "scripts"))
# —— 引导结束 ——

"""verify_js.py —— 前端内核（app.js）与 Python 内核（bazi_core.py）全量对拍

做法：随机取 N 个出生时刻（含真太阳时若干），Python 算出四柱／起运／交运／
人元司令／12 步大运／当年流年，写成期望值；再用 node 跑 app.js 算同样一批，
逐项比对。需要 node（本机已装）。

用法：python3 verify_js.py [N]
"""
import datetime
import json
import os
import random
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bazi_core as B  # noqa: E402

NODE = "node"
APP = os.path.join(SKILL_DIR, "assets", "app.js")


def make_cases(n, seed=20261031):
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        # 三成抽唐代至清末（600–1899），验证表外天文回推与儒略历日柱
        y = rnd.randint(600, 1899) if i % 10 < 3 else rnd.randint(1902, 2098)
        m = rnd.randint(1, 12)
        d = rnd.randint(1, 28)
        h = rnd.randint(0, 23)
        mi = rnd.randint(0, 59)
        g = "male" if i % 2 == 0 else "female"
        lon = None
        tst = False
        lat = None
        if i % 7 == 0:
            lon = round(rnd.uniform(75, 135), 2)
            lat = round(rnd.uniform(18, 50), 2)
            tst = True
        out.append({"y": y, "m": m, "d": d, "h": h, "mi": mi, "g": g,
                    "lon": lon, "lat": lat, "tst": tst})
    return out


def py_side(cases):
    res = []
    for c in cases:
        birth = datetime.datetime(c["y"], c["m"], c["d"], c["h"], c["mi"])
        d = B.paipan(birth, c["g"], longitude=c["lon"], use_true_solar=c["tst"],
                     now=datetime.datetime(2026, 10, 31), dayun_steps=12,
                     latitude=c["lat"])
        res.append({
            "pillars": [x["gan"] + x["zhi"] for x in d["pillars"]],
            # 九十八令：十神与藏干十神纳入对拍（原只比四柱，D96 的分叉因此漏检）
            "stars": [[p["star"]] + [c["god"] for c in p["cang"]] for p in d["pillars"]],
            "qiyun": d["qiyun"]["text"],
            "jiaoyun": d["qiyun"]["jiaoyun_text"],
            "siling": [d["siling"]["gan"], d["siling"]["jie"], d["siling"]["days"]],
            "dy": [(x["gan"] + x["zhi"]) if not x.get("is_pre") else "运前" for x in d["dayun"]],
            "ln": [[x["year"], x["gan"] + x["zhi"]] for x in d["liunian"]],
            "sel": [d["sel"]["dy"], d["sel"]["ln"]],
        })
    return res


JS = r"""
const B = require(process.argv[2]);
const cases = JSON.parse(require('fs').readFileSync(process.argv[3], 'utf8'));
const out = cases.map(c => {
  const birth = new Date(Date.UTC(c.y, c.m - 1, c.d, c.h, c.mi));
  const d = B.paipan({birth, gender: c.g, now: new Date(Date.UTC(2026, 9, 31, 12)),
    trueSolar: c.tst, lon: c.lon, lat: c.lat, steps: 12});
  return {
    pillars: d.pillars.map(p => p.gan + p.zhi),
    stars: d.pillars.map(p => [p.star].concat(p.cang.map(c => c.god))),
    qiyun: d.qiyun.text,
    jiaoyun: d.qiyun.jiaoyun_text,
    siling: [d.siling.gan, d.siling.jie, d.siling.days],
    dy: d.dayun.map(x => x.gan ? x.gan + x.zhi : '运前'),
    ln: d.dayun[d.sel.dy].ln.map(x => [x.year || null, x.gan + x.zhi]),
    sel: [d.sel.dy, d.sel.ln]
  };
});
process.stdout.write(JSON.stringify(out));
"""


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    cases = make_cases(n)
    py = py_side(cases)
    with tempfile.TemporaryDirectory() as td:
        cp = os.path.join(td, "cases.json")
        jp = os.path.join(td, "run.js")
        with open(cp, "w", encoding="utf-8") as f:
            json.dump(cases, f)
        with open(jp, "w", encoding="utf-8") as f:
            f.write(JS)
        try:
            r = subprocess.run([NODE, jp, os.path.abspath(APP), cp],
                               capture_output=True, text=True, timeout=120)
        except FileNotFoundError:
            print("未找到 node，跳过对拍")
            return 2
        if r.returncode != 0:
            print("node 运行失败：\n" + r.stderr[-800:])
            return 1
        js = json.loads(r.stdout)

    fields = ["pillars", "stars", "qiyun", "jiaoyun", "siling", "dy", "ln", "sel"]
    bad = {k: 0 for k in fields}
    first = {}
    for i, (a, b) in enumerate(zip(py, js)):
        for k in fields:
            if a[k] != b[k]:
                bad[k] += 1
                if k not in first:
                    first[k] = (cases[i], a[k], b[k])
    total = sum(bad.values())
    print("对拍 %d 例（含真太阳时 %d 例；唐至清末 %d 例）"
          % (n, sum(1 for c in cases if c["tst"]), sum(1 for c in cases if c["y"] < 1900)))
    for k in fields:
        print("  %-8s 不一致 %d" % (k, bad[k]))
    if total:
        for k, v in first.items():
            print("首个差异 [%s] %s\n  py=%s\n  js=%s" % (k, v[0], v[1], v[2]))
        return 1
    print("结果：%d 项字段全一致" % len(fields))
    return 0


if __name__ == "__main__":
    sys.exit(main())
