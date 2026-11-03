#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# —— devtools 引导：把技能包的 scripts 放进 import 路径（第一百一十令）——
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from paths import SKILL as SKILL_DIR, PROJ as PROJ_DIR  # noqa: E402
_sys.path.insert(0, _os.path.join(SKILL_DIR, "scripts"))
# —— 引导结束 ——

"""build_jsdata.py —— 生成前端运行所需的两张表（节气／农历）

产物：assets/data.js
  window.BAZI_TABLES = { jq:{y0,y1,base,from,head,seq}, ln:{y0,y1,s} }

  jq   —— 每年 24 个「节」距当年 1 月 1 日 00:00 的分钟数，base36 定长 4 位，按年顺排。
            仅覆盖 1900–2112（sxtwl 精确区）；表外年份（如唐代）由前端天文算法回推，
            两条路在 jqDate() 内分流，接口一致。
  ln.s  —— 1900–2100 每年「闰月月序(2 位) + 13 个月大小(1 = 30 天)」

数据源：sxtwl（寿星天文历，MIT）。仅重建表时运行，成品不需要 sxtwl。
"""
import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SKILL_DIR, "assets", "data.js")

# 前端节气序号：0 小寒 … 23 冬至（与 sxtwl 的 0 冬至 差 1）
TERMS = ["小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明", "谷雨",
         "立夏", "小满", "芒种", "夏至", "小暑", "大暑", "立秋", "处暑",
         "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪", "冬至"]
SX = ["冬至", "小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明",
      "谷雨", "立夏", "小满", "芒种", "夏至", "小暑", "大暑", "立秋",
      "处暑", "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪"]

JQ_Y0, JQ_Y1 = 1900, 2112         # 节气表区间；600–1899 由前端天文回推
LN_Y0, LN_Y1 = 600, 2100          # 农历表：600 起（sxtwl 天文回推，供古代显示「几月初几」）
DIGIT = "0123456789abcdefghijklmnopqrstuvwxyz"


def b36(n, width):
    s, v = "", n
    while v:
        s = DIGIT[v % 36] + s
        v //= 36
    s = s.rjust(width, "0")
    assert len(s) == width, (n, width)
    return s


def jq_block():
    """按年 24 项：距当年 1 月 1 日 00:00 的分钟数（base36 定长 4 位）。"""
    import sxtwl
    out = []
    for y in range(JQ_Y0, JQ_Y1 + 1):
        found = {}
        day = datetime.date(y, 1, 1)
        while day.year == y:
            o = sxtwl.fromSolar(day.year, day.month, day.day)
            if o.hasJieQi():
                name = SX[o.getJieQi()]
                if name not in found:            # 跨年漂移时以本年内首次出现为准
                    t = sxtwl.JD2DD(o.getJieQiJD())
                    cur = datetime.datetime(int(t.Y), int(t.M), int(t.D), int(t.h), int(t.m))
                    found[name] = int((cur - datetime.datetime(y, 1, 1)).total_seconds() // 60)
            day += datetime.timedelta(days=1)
        miss = [n for n in TERMS if n not in found]
        assert not miss, (y, miss)
        for name in TERMS:
            out.append(b36(found[name], 4))
    return "".join(out)


def _jdn(y, m, d):
    """与前端 app.js jdn() 完全一致的儒略日（1582-10-15 起格里历，之前儒略历）。"""
    a = (14 - m) // 12
    y2 = y + 4800 - a
    m2 = m + 12 * a - 3
    base = d + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4
    old = (y < 1582) or (y == 1582 and (m < 10 or (m == 10 and d < 15)))
    return base - 32083 if old else base - y2 // 100 + y2 // 400 - 32045


def lunar_block():
    """农历表 600–2100：每年「闰月月序(2 位) + 13 个月大小(1=30天)」，并返回基准 JDN。

    sxtwl 在极少数年份有精度异常：600 年闰正月 28 天（远古边界）、689–700 与 761–762
    年边界整体错位（正月初一在公历上错移，月长 300+ 天）。策略：轻微异常（28/31 天）
    就近取 29/30；连续错位段取「段首正月初一 → 段后正月初一」的总 JDN 跨度，按 384（闰）
    /354（平）分摊到段内各年，凑足总长——保证段尾之后累加基准精确复位，不污染其后年份；
    段内月日位置为近似。"""
    import sxtwl
    rows = {}
    day = datetime.date(LN_Y0, 1, 1) - datetime.timedelta(days=120)   # 前导，防首年正月被截断
    end = datetime.date(LN_Y1, 12, 31) + datetime.timedelta(days=70)  # 补足末年腊月
    while day <= end:
        o = sxtwl.fromSolar(day.year, day.month, day.day)
        ly = o.getLunarYear()
        if (LN_Y0 - 1) <= ly <= LN_Y1:
            key = (ly, o.getLunarMonth(), bool(o.isLunarLeap()))
            rows.setdefault(key, [day, day])
            rows[key][1] = day
        day += datetime.timedelta(days=1)

    def ns_of(y):
        leap = next((m for (yy, m, lp) in rows if yy == y and lp), 0)
        seq = []
        for m in range(1, 13):
            if (y, m, False) in rows:
                seq.append((m, False))
                if leap == m:
                    seq.append((m, True))
        if len(seq) not in (12, 13):
            return None
        ns = []
        for m, lp in seq:
            a, b = rows[(y, m, lp)]
            nn = _jdn(b.year, b.month, b.day) - _jdn(a.year, a.month, a.day) + 1
            if nn > 31 or nn < 28:
                return None
            ns.append(nn)
        return leap, ns

    meta = {y: ns_of(y) for y in range(LN_Y0, LN_Y1 + 1)}
    out, fallback_years, approx = [], [], []
    y = LN_Y0
    while y <= LN_Y1:
        if meta[y] is not None:
            leap, ns = meta[y]
            a0 = rows.get((y, 1, False))
            b0 = rows.get((y + 1, 1, False))
            ylen = (_jdn(b0[0].year, b0[0].month, b0[0].day) -
                    _jdn(a0[0].year, a0[0].month, a0[0].day)) if (a0 and b0) else sum(ns)
            # 校验：月长总和须等于「正月初一 → 次年正月初一」的真实年长，否则按年长分配
            if all(n in (29, 30) for n in ns) and sum(ns) == ylen:
                lens = "".join("1" if n == 30 else "0" for n in ns)
            else:
                for n in ns:
                    if n not in (29, 30):
                        approx.append((y, n))
                m = len(ns)
                extra = max(0, min(m, ylen - 29 * m))
                lens = "".join("1" if j < extra else "0" for j in range(m))
            out.append("%02d%s" % (leap, lens.ljust(13, "0")))
            y += 1
            continue
            out.append("%02d%s" % (leap, lens.ljust(13, "0")))
            y += 1
            continue
        y0 = y                                        # 连续错位段 [y0, y1]
        while y <= LN_Y1 and meta[y] is None:
            y += 1
        y1 = y - 1
        fallback_years.extend(range(y0, y1 + 1))
        n = y1 - y0 + 1
        a0, b0 = rows.get((y0, 1, False)), rows.get((y1 + 1, 1, False))
        total = (_jdn(b0[0].year, b0[0].month, b0[0].day) -
                 _jdn(a0[0].year, a0[0].month, a0[0].day)) if (a0 and b0) else 354 * n
        k = max(0, min(n, int(round((total - 354 * n) / 30.0))))
        ls = [384 if i < k else 354 for i in range(n)]
        ls[-1] += total - sum(ls)                     # 残差并入末位，保证总长精确
        for L in ls:
            if L >= 372:
                leap, m = 1, 13
            else:
                leap, m = 0, 12
            extra = max(0, min(m, L - 29 * m))
            out.append("%02d%s" % (leap, "".join("1" if j < extra else "0" for j in range(m)).ljust(13, "0")))

    d0 = rows[(LN_Y0, 1, False)][0]
    return {"y0": LN_Y0, "y1": LN_Y1, "s": "".join(out),
            "base": _jdn(d0.year, d0.month, d0.day),
            "_fallback": fallback_years, "_approx": approx}


def main():
    jq = jq_block()
    ln = lunar_block()
    js = ("/* data.js —— 由 scripts/build_jsdata.py 生成，勿手改。\n"
          "   节气 %d–%d 每年 24 项；农历 %d–%d（含基准 JDN）。数据源：sxtwl 寿星天文历（MIT）。 */\n"
          "(function(g){g.BAZI_TABLES=%s;\n})(typeof window!=='undefined'?window:globalThis);\n"
          % (JQ_Y0, JQ_Y1, LN_Y0, LN_Y1,
             json.dumps({"jq": {"y0": JQ_Y0, "y1": JQ_Y1, "s": jq},
                         "ln": {"y0": LN_Y0, "y1": LN_Y1, "base": ln["base"], "s": ln["s"]}},
                        ensure_ascii=False, separators=(",", ":"))))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(js)
    print("节气 %d 年（%d 字节）｜农历 %d 年（%d 字节，基准 JDN %d）｜文件 %.1f KB"
          % (JQ_Y1 - JQ_Y0 + 1, len(jq), LN_Y1 - LN_Y0 + 1, len(ln["s"]), ln["base"], len(js) / 1024.0))
    if ln["_fallback"]:
        print("  农历回退年（sxtwl 边界异常，整年大小交替）：%s" % ln["_fallback"])
    if ln["_approx"]:
        print("  农历近似月（28/31 天→29/30）：%s" % ln["_approx"])


if __name__ == "__main__":
    main()
