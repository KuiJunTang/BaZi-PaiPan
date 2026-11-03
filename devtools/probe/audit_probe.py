#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# —— devtools 引导：把技能包的 scripts 放进 import 路径（第一百一十令）——
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from paths import SKILL as SKILL_DIR, PROJ as PROJ_DIR  # noqa: E402
_sys.path.insert(0, _os.path.join(SKILL_DIR, "scripts"))
# —— 引导结束 ——

"""audit_probe.py —— 主动审计探针（第一百零二令）

不重复现有校验，专撞**现有脚本没覆盖的角落**：
  A. 十神穷举：10 日干 × 10 他干（100 组）、12 支藏干 × 10 日干
  B. 大运穷举：60 个年份（盖全 60 甲子）× 男女，12 步与独立推排比对
  C. 极端年份：600 表首、2099／2100 年末（12 步大运越出农历表）
  D. 节气边界：立春／芒种／小寒 ±1 分钟换柱；夏至／春分（中气）不得换
  E. 真太阳时：经度两端（73.5°E 喀什／135.1°E 抚远）× 均时差极值月
  F. 古法时辰：漠河 53.5°N 冬至、三亚 18.2°N 夏至

农历边界、年号、反推在前端脚本 `audit_probe_js.js`——Python 端没有这两套实现。

用法：python3 scripts/audit_probe.py
退出码：0 全过；1 有可疑项
"""
import datetime
import sys

sys.path.insert(0, __file__.rsplit('/', 1)[0])

import bazi_core as B
from verify_independent import ten_god_ref, dayun_ref, CANG_REF, GAN, ZHI, gz_index

FAIL = []
N = 0

# term_dt 的索引是**二十四气**：0 小寒、2 立春、4 惊蛰、6 清明、8 立夏、10 芒种、
# 12 小暑、14 立秋、16 白露、18 寒露、20 立冬、22 大雪为「节」；奇数索引为中气。
JIE_IDX = ((2, "立春", "年柱＋月柱"), (10, "芒种", "月柱"), (0, "小寒", "月柱"))
QI_IDX = ((11, "夏至"), (5, "春分"))


def bad(msg):
    FAIL.append(msg)
    print("  ✗ " + msg)


def ok(msg):
    global N
    N += 1
    print("  ✓ " + msg)


def chart(dt, gender='male', **kw):
    return B.paipan(dt, gender, now=datetime.datetime.now(), **kw)


def gz_of(d):
    return "".join(p['gan'] + p['zhi'] for p in d['pillars'])


# ---------------------------------------------------------------- A 十神穷举
def probe_ten_god():
    print("\n[A] 十神穷举（100 组＋藏干）")
    wrong = [(d, o) for d in GAN for o in GAN if B.ten_god(d, o) != ten_god_ref(d, o)]
    if wrong:
        bad("十神与独立实现不符 %d 组，例：%s" % (len(wrong), wrong[:5]))
    else:
        ok("10 日干 × 10 他干 = 100 组十神，与独立实现全同")

    bad_c = []
    for z in ZHI:
        for d in GAN:
            for g in CANG_REF[z]:
                if B.ten_god(d, g) != ten_god_ref(d, g):
                    bad_c.append((z, d, g, B.ten_god(d, g), ten_god_ref(d, g)))
    if bad_c:
        bad("藏干十神不符 %d 处：%s" % (len(bad_c), bad_c[:5]))
    else:
        ok("12 支藏干 × 10 日干（100 个组合）十神全同，无「日主」误标")


# ---------------------------------------------------------------- B 大运穷举
def probe_dayun():
    print("\n[B] 大运穷举（60 年 × 男女）")
    diff = []
    for i in range(60):
        dt = datetime.datetime(1950 + i, 6, 15, 10, 0)
        for gender in ('male', 'female'):
            d = chart(dt, gender)
            got = [o['gan'] + o['zhi'] for o in d['dayun'] if not o.get('is_pre')]
            mp = d['pillars'][1]
            want, _fw = dayun_ref(d['pillars'][0]['gan'], gz_index(mp['gan'], mp['zhi']),
                                  gender, 12)
            if got != want:
                diff.append((1950 + i, gender, got[:3], want[:3]))
    if diff:
        bad("大运推排不符 %d 例：%s" % (len(diff), diff[:3]))
    else:
        ok("60 个年份 × 男女 = 120 例，12 步大运干支与独立推排全同")


# ---------------------------------------------------------------- C 极端年份
def probe_edges_year():
    print("\n[C] 极端年份（表首尾、大运越出农历表）")
    cases = [
        ("0600-01-01 00:30", "表首年份"),
        ("0600-12-31 23:30", "表首年尾＋晚子时"),
        ("2099-12-31 23:30", "晚子时跨年"),
        ("2100-06-15 10:00", "表尾年"),
        ("2100-12-31 23:30", "表尾年末＋晚子时"),
    ]
    for s, why in cases:
        dt = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M")
        try:
            d = chart(dt)
        except Exception as e:
            bad("%s（%s）排盘异常：%r" % (s, why, e))
            continue
        yrs = [o['year'] for o in d['dayun']]
        lns = [x['year'] for x in d['liunian'] if x.get('year')]
        if any(y is None for y in yrs):
            bad("%s（%s）大运起始年出现 None：%s" % (s, why, yrs))
        elif not lns:
            bad("%s（%s）流年为空" % (s, why))
        else:
            over = [y for y in lns if y > 2100]
            ok("%s（%s）四柱 %s；大运至 %d；流年 %d 项%s"
               % (s, why, gz_of(d), yrs[-1], len(lns),
                  "（含 %d 项越表，干支照算）" % len(over) if over else ""))


# ---------------------------------------------------------------- D 节气边界
def probe_jie():
    print("\n[D] 节气边界（节 ±1 分钟换柱；中气不换）")
    for y in (600, 1582, 1900, 2100):
        badn = []
        for idx, name, what in JIE_IDX:
            t = B.term_dt(y, idx)
            pa = gz_of(chart(t - datetime.timedelta(minutes=1)))[:4]
            pb = gz_of(chart(t + datetime.timedelta(minutes=1)))[:4]
            if pa == pb:
                badn.append("%d %s 前后 1 分钟 %s 未换（仍 %s）" % (y, name, what, pa))
        for idx, name in QI_IDX:
            t = B.term_dt(y, idx)
            pa = gz_of(chart(t - datetime.timedelta(minutes=1)))[:4]
            pb = gz_of(chart(t + datetime.timedelta(minutes=1)))[:4]
            if pa != pb:
                badn.append("%d %s（中气）前后年月柱竟变了：%s→%s" % (y, name, pa, pb))
        if badn:
            bad("；".join(badn))
        else:
            ok("%d 年：立春换年＋月、芒种／小寒换月，差 1 分钟即切换；夏至／春分（中气）不换" % y)


# ---------------------------------------------------------------- E 真太阳时
def probe_tst():
    print("\n[E] 真太阳时（经度两端 × 均时差极值）")
    for lon, city in ((73.5, "喀什"), (135.1, "抚远")):
        for md in ("02-11", "11-03"):
            s = "2000-%s 11:55" % md
            dt = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M")
            d = chart(dt, use_true_solar=True, longitude=lon, latitude=40.0)
            shift = d['tst_shift']
            base = (lon - 120.0) * 4.0            # 经度差 × 4 分
            eot = shift - base                    # 余下即均时差
            if not (-17 <= eot <= 17):
                bad("%s %s 均时差分量 %.1f 分越界（应 ±16 内）" % (city, s, eot))
            else:
                ok("%s %s 偏移 %+d 分（经度差 %+.1f ＋均时差 %+.1f）"
                   % (city, s, shift, base, eot))


# ---------------------------------------------------------------- F 古法时辰
def probe_ancient_hour():
    print("\n[F] 古法时辰（高纬冬至／低纬夏至）")
    for lat, lon, city, md in ((53.47, 122.5, "漠河", "12-21"), (18.25, 109.5, "三亚", "06-21")):
        dt = datetime.datetime.strptime("2000-%s 12:00" % md, "%Y-%m-%d %H:%M")
        d = chart(dt, use_true_solar=True, longitude=lon, latitude=lat)
        sun = d.get('sun')
        if not sun:
            bad("%s %s 无日出日落数据" % (city, md))
            continue
        ok("%s %s 日出 %s／日落 %s，时柱 %s"
           % (city, md, sun['rise'], sun['set'], d['pillars'][3]['zhi']))


def main():
    print("== 主动审计探针（audit_probe.py）==")
    probe_ten_god()
    probe_dayun()
    probe_edges_year()
    probe_jie()
    probe_tst()
    probe_ancient_hour()
    print("\n结果：%s（通过 %d 项，问题 %d 项）"
          % ("全部通过" if not FAIL else "有可疑项", N, len(FAIL)))
    for x in FAIL:
        print("  · " + x)
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
