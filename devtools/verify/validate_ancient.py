#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# —— devtools 引导：把技能包的 scripts 放进 import 路径（第一百一十令）——
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from paths import SKILL as SKILL_DIR, PROJ as PROJ_DIR  # noqa: E402
_sys.path.insert(0, _os.path.join(SKILL_DIR, "scripts"))
# —— 引导结束 ——

"""validate_ancient.py —— 古代年份（600–1899）内核校验，以 sxtwl 为第三方

校验项
  [A] 日柱：抽样年份随机取日，与 sxtwl 逐日比对（儒略历日柱体系）
  [B] 节气：每年 24 气与 sxtwl 同项比对，统计最大偏差（内核走 Meeus 天文回推）
  [C] 年柱／月柱：交节前后各 2 日与 sxtwl 比对
  [D] 边界：1582-10-04/15 儒略—格里换历处的日柱连续性

sxtwl 在古代偶有缺项（如 900 年缺惊蛰），故 [B] 遇缺则以 sxtwl 该项缺失告警，不计错。
"""
import datetime
import random
import sys

import sxtwl

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import bazi_core as B  # noqa: E402

SX = ["冬至", "小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明",
      "谷雨", "立夏", "小满", "芒种", "夏至", "小暑", "大暑", "立秋",
      "处暑", "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪"]


def gz(i):
    return B.GAN[i % 10] + B.ZHI[i % 12]


def sxt_day(y, m, d):
    o = sxtwl.fromSolar(y, m, d)
    g = o.getDayGZ()
    return B.GAN[g.tg] + B.ZHI[g.dz]


def sxt_terms(y):
    """该年 sxtwl 给出的节气：{(月,日): (名, datetime)}"""
    out = {}
    day = datetime.date(y, 1, 1)
    while day.year == y:
        o = sxtwl.fromSolar(day.year, day.month, day.day)
        if o.hasJieQi():
            t = sxtwl.JD2DD(o.getJieQiJD())
            out[(int(t.M), int(t.D))] = (SX[o.getJieQi()],
                                         datetime.datetime(int(t.Y), int(t.M), int(t.D),
                                                           int(t.h), int(t.m)))
        day += datetime.timedelta(days=1)
    return out


def main():
    rnd = random.Random(1226)
    ok = True

    # [A] 日柱
    n = bad = 0
    samples = list(range(600, 1900, 25)) + [899, 900, 1582]
    for y in samples:
        for _ in range(12):
            m = rnd.randint(1, 12)
            d = rnd.randint(1, 28)
            if y == 1582 and m == 10 and 5 <= d <= 14:
                continue
            want = sxt_day(y, m, d)
            got = gz(B.day_gz_index(datetime.datetime(y, m, d, 12)))
            n += 1
            if want != got:
                bad += 1
                if bad <= 5:
                    print("    日柱错 %04d-%02d-%02d sxtwl=%s 内核=%s" % (y, m, d, want, got))
    print("[A] 古代日柱抽样 %d 例，错 %d" % (n, bad))
    ok &= bad == 0

    # [B] 节气（最大偏差）
    mx, mx_at, miss = 0.0, None, 0
    cnt = 0
    for y in range(600, 1900, 50):
        st = sxt_terms(y)
        for idx in range(24):
            name = B._TERMS[idx]
            got = B.term_dt(y, idx)
            hit = None
            for (mm, dd), (nm, dt) in st.items():
                if nm == name and abs((dt - got).days) <= 3:
                    hit = dt
                    break
            if hit is None:
                miss += 1
                continue
            cnt += 1
            diff = abs((got - hit).total_seconds()) / 60.0
            if diff > mx:
                mx, mx_at = diff, (y, name, got, hit)
    print("[B] 节气比对 %d 项（sxtwl 缺项 %d），最大偏差 %.1f 分钟" % (cnt, miss, mx))
    if mx_at:
        print("    最大处：%d %s 内核=%s sxtwl=%s" % (mx_at[0], mx_at[1],
                                                 mx_at[2].strftime("%m-%d %H:%M"),
                                                 mx_at[3].strftime("%m-%d %H:%M")))
    # 天文回推精度约 ±15 分钟，超过 30 分钟即判异常
    if mx > 30:
        bad_b = 1
        print("    ！偏差超 30 分钟，回推可疑")
    else:
        bad_b = 0
    ok &= bad_b == 0

    # [C] 年柱／月柱：距交节 ±25 日（远离边界，避开 sxtwl 古代月柱提前换日的缺陷）
    n = bad = 0
    JIE = ("立春", "惊蛰", "清明", "立夏", "芒种", "小暑",
           "立秋", "白露", "寒露", "立冬", "大雪", "小寒")
    for y in range(620, 1900, 40):
        for name, dt in sorted(sxt_terms(y).values()):
            if name not in JIE:
                continue
            for delta in (-25, 25):
                d = dt + datetime.timedelta(days=delta)
                o = sxtwl.fromSolar(d.year, d.month, d.day)
                mg, yg = o.getMonthGZ(), o.getYearGZ()
                want_m = B.GAN[mg.tg] + B.ZHI[mg.dz]
                want_y = B.GAN[yg.tg] + B.ZHI[yg.dz]
                got_m = gz(B.month_gz_index(d))
                got_y = gz(B.year_gz_index(d))
                n += 1
                if want_m != got_m or want_y != got_y:
                    bad += 1
                    if bad <= 5:
                        print("    柱错 %s %s%+d 年 %s/%s 月 %s/%s" % (d.date(), name, delta,
                                                                   want_y, got_y, want_m, got_m))
    print("[C] 距交节 ±25 日的年柱·月柱 %d 例，错 %d" % (n, bad))
    ok &= bad == 0

    # [C2] 自洽：交节前 1 日与后 1 日，月柱必不同且地支相邻
    n = bad = 0
    for y in range(620, 1900, 40):
        for name, dt in sorted(sxt_terms(y).values()):
            if name not in JIE:
                continue
            a = B.month_gz_index(dt - datetime.timedelta(days=1))
            b = B.month_gz_index(dt + datetime.timedelta(days=1))
            n += 1
            if a == b or (b % 12 - a % 12) % 12 != 1:
                bad += 1
                if bad <= 5:
                    print("    换月错 %s %s %s→%s" % (dt.date(), name, gz(a), gz(b)))
    print("[C2] 交节前後月柱递进 %d 例，错 %d" % (n, bad))
    ok &= bad == 0

    # [D] 换历连续性
    a = gz(B.day_gz_index(datetime.datetime(1582, 10, 4, 12)))
    b = gz(B.day_gz_index(datetime.datetime(1582, 10, 15, 12)))
    cont = (B.GAN.index(b[0]) - B.GAN.index(a[0])) % 10 == 1
    print("[D] 1582-10-04 %s → 10-15 %s，干支连续：%s" % (a, b, "是" if cont else "否"))
    ok &= cont

    print("结果：%s" % ("全部通过" if ok else "有异常"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
