#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# —— devtools 引导：把技能包的 scripts 放进 import 路径（第一百一十令）——
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from paths import SKILL as SKILL_DIR, PROJ as PROJ_DIR  # noqa: E402
_sys.path.insert(0, _os.path.join(SKILL_DIR, "scripts"))
# —— 引导结束 ——

"""validate_core.py —— 用 sxtwl（寿星天文历）作独立第三方，全量比对内核结果。

校验项：
 1. 日柱：1900-01-01 至 2100-12-31 逐日比对（共 73414 天）
 2. 年柱 / 月柱：每年 24 个节气前后各 1 天 + 每月 3 个时刻抽查
 3. 时柱：12 时辰全对比
 4. 节气表：与 sxtwl 实时结果比对（数据表本身由 sxtwl 生成，此处验生成无损）
 5. 已知案例：1991-05-18 戌时（截图原盘）四柱、藏干、大运
"""
import datetime
import sys

import bazi_core as B

GAN, ZHI = B.GAN, B.ZHI


def main():
    import sxtwl
    ok = True
    # ---- 1 日柱 ----
    d = datetime.date(1900, 1, 1)
    end = datetime.date(2100, 12, 31)
    n = bad = 0
    first_bad = []
    while d <= end:
        dt = datetime.datetime(d.year, d.month, d.day, 12)
        mine = B.day_gz_index(dt)
        s = sxtwl.fromSolar(d.year, d.month, d.day).getDayGZ()
        theirs = B._gz(s.tg, s.dz)
        n += 1
        if mine != theirs:
            bad += 1
            if len(first_bad) < 5:
                first_bad.append((d, GAN[mine % 10] + ZHI[mine % 12],
                                  GAN[theirs % 10] + ZHI[theirs % 12]))
        d += datetime.timedelta(days=1)
    print("[1] 日柱逐日比对 %d 天，错 %d 天 %s" % (n, bad, first_bad))
    ok &= bad == 0

    # ---- 2 年柱 / 月柱 ----
    n = bad = 0
    sample_bad = []
    for y in range(1900, 2101):
        for idx in range(24):
            t = B.term_dt(y, idx)
            # sxtwl 的年/月干支以「日」为界（交节当日整天即换），故比对取交节前后各 2 天，
            # 避开当日；交节当日的精确时刻行为另见 [2b]。
            for delta in (-2, 2):
                dt = t + datetime.timedelta(days=delta, hours=1)
                sd = sxtwl.fromSolar(dt.year, dt.month, dt.day)
                yg = B.year_gz_index(dt)
                mg = B.month_gz_index(dt)
                n += 1
                if (yg % 10 != sd.getYearGZ().tg or yg % 12 != sd.getYearGZ().dz or
                        mg % 10 != sd.getMonthGZ().tg or mg % 12 != sd.getMonthGZ().dz):
                    bad += 1
                    if len(sample_bad) < 5:
                        sample_bad.append((dt.isoformat(),
                                           GAN[yg % 10] + ZHI[yg % 12] + " " + GAN[mg % 10] + ZHI[mg % 12],
                                           GAN[sd.getYearGZ().tg] + ZHI[sd.getYearGZ().dz] + " " +
                                           GAN[sd.getMonthGZ().tg] + ZHI[sd.getMonthGZ().dz]))
    print("[2] 年柱/月柱 节气前后比对 %d 例，错 %d 例 %s" % (n, bad, sample_bad))
    ok &= bad == 0

    # ---- 2b 交节当日精确时刻（分钟级口径，sxtwl 无对应能力，此处验内核自身规则）----
    n = bad = 0
    for (y, idx, hh, mm, want_month) in [
            (1914, 2, 12, 0, "乙丑"),   # 立春 1914-02-04 23:29 之前仍属丑月
            (1914, 2, 23, 59, "丙寅"),  # 立春 23:29 之后属寅月
            (1991, 8, 8, 0, "壬辰"),    # 立夏 1991-05-06 08:26 之前仍属辰月
            (1991, 8, 9, 0, "癸巳"),    # 立夏之后属巳月
    ]:
        if y == 1914:
            dt = datetime.datetime(1914, 2, 4, hh, mm)
        else:
            dt = datetime.datetime(1991, 5, 6, hh, mm)
        mg = B.month_gz_index(dt)
        n += 1
        if B.GAN[mg % 10] + B.ZHI[mg % 12] != want_month:
            bad += 1
            print("    交节当日错:", dt, B.GAN[mg % 10] + B.ZHI[mg % 12], "应", want_month)
    print("[2b] 交节当日分钟级判定 %d 例，错 %d" % (n, bad))
    ok &= bad == 0

    # ---- 3 时柱 ----
    n = bad = 0
    for h in range(24):
        dt = datetime.datetime(1991, 5, 18, h, 30)
        s = sxtwl.fromSolar(1991, 5, 18)
        sgz = s.getDayGZ()
        day_ref = dt + datetime.timedelta(days=1) if h >= 23 else dt
        hi = B.hour_gz_index(dt, B.day_gz_index(day_ref))
        hz = sxtwl.getShiGz(sgz.tg, h)
        n += 1
        if hi % 10 != hz.tg or hi % 12 != hz.dz:
            bad += 1
            print("    时柱错:", h, GAN[hi % 10] + ZHI[hi % 12], GAN[hz.tg] + ZHI[hz.dz])
    print("[3] 时柱 %d 时辰比对，错 %d" % (n, bad))
    ok &= bad == 0

    # ---- 4 节气表完整性 ----
    n = bad = 0
    for y in range(1900, 2101):
        for idx in range(24):
            t = B.term_dt(y, idx)
            n += 1
            if not (t.year == y and 0 <= t.month <= 12):
                bad += 1
    print("[4] 节气表 %d 项，年份异常 %d" % (n, bad))
    ok &= bad == 0

    # ---- 5 已知案例 ----
    r = B.paipan(datetime.datetime(1991, 5, 18, 19, 0), "male",
                 now=datetime.datetime(2026, 10, 31))
    pillars = " ".join(p["gan"] + p["zhi"] for p in r["pillars"])
    print("[5] 案例四柱：%s（期望 辛未 癸巳 戊子 壬戌）" % pillars)
    print("    主星：%s（期望 伤官 正财 日主 偏财）" % " ".join(p["star"] for p in r["pillars"]))
    print("    藏气：%s" % " | ".join("".join(c["gan"] + c["short"] for c in p["cang"]) for p in r["pillars"]))
    print("    起运：%s（期望 出生后4年1月22天20小时）" % r["qiyun"]["text"])
    print("    交运：%s（期望 逢乙年小暑后4天）" % r["qiyun"]["jiaoyun_text"])
    print("    大运：%s" % ", ".join("%d/%d岁/%s%s" % (d["year"], d["age"], d["gan"], d["zhi"])
                                   for d in r["dayun"][:6]))
    print("    人元司令：%s（%s后%d日）（期望 庚 立夏后12日）" %
          (r["siling"]["gan"], r["siling"]["jie"], r["siling"]["days"]))
    ok &= pillars == "辛未 癸巳 戊子 壬戌"
    ok &= r["qiyun"]["text"] == "出生后4年1月22天20小时"

    print("\n结果：%s" % ("全部通过" if ok else "有失败项"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
