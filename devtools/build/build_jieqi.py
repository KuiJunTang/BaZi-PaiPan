#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# —— devtools 引导：把技能包的 scripts 放进 import 路径（第一百一十令）——
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from paths import SKILL as SKILL_DIR, PROJ as PROJ_DIR  # noqa: E402
_sys.path.insert(0, _os.path.join(SKILL_DIR, "scripts"))
# —— 引导结束 ——

"""build_jieqi.py —— 生成节气数据表 jieqi_data.py

数据源：sxtwl（寿星天文历 Python 版，MIT）。本脚本仅在「重建数据表」时运行，
运行时不需要 sxtwl。生成结果：每年 24 个节气的「北京时间距当年 1 月 1 日 00:00 的分钟数」。

用法：python3 build_jieqi.py [起始年] [结束年]
"""
import sys
import os

TERMS = ["小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明", "谷雨",
         "立夏", "小满", "芒种", "夏至", "小暑", "大暑", "立秋", "处暑",
         "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪", "冬至"]
# sxtwl getJieQi() 索引 -> 节气名
SX_ORDER = ["冬至", "小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明",
            "谷雨", "立夏", "小满", "芒种", "夏至", "小暑", "大暑", "立秋",
            "处暑", "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪"]


def build(y0, y1):
    import sxtwl
    import datetime
    out = {}
    for y in range(y0, y1 + 1):
        found = {}
        day = datetime.date(y, 1, 1)
        while day.year == y:
            d = sxtwl.fromSolar(day.year, day.month, day.day)
            if d.hasJieQi():
                name = SX_ORDER[d.getJieQi()]
                t = sxtwl.JD2DD(d.getJieQiJD())
                # JD2DD 返回北京时间（东八区）
                dt = t
                base = datetime.datetime(y, 1, 1)
                cur = datetime.datetime(int(dt.Y), int(dt.M), int(dt.D), int(dt.h), int(dt.m))
                minutes = int(round((cur - base).total_seconds() / 60))
                if not (0 <= minutes < 366 * 1440):
                    raise RuntimeError("%d 年 %s 分钟数越界 %d" % (y, name, minutes))
                found[name] = minutes
            day += datetime.timedelta(days=1)
        row = []
        for name in TERMS:
            if name not in found:
                raise RuntimeError("%d 年缺节气 %s" % (y, name))
            row.append(found[name])
        out[y] = row
    return out


def emit(out, path):
    lines = ["# -*- coding: utf-8 -*-",
             '"""jieqi_data.py —— 节气表（自动生成，勿手改）',
             "",
             "数据源：sxtwl / 寿星天文历（MIT）",
             "生成脚本：build_jieqi.py",
             "单位：北京时间（UTC+8）距当年 1 月 1 日 00:00 的分钟数",
             "顺序：小寒 大寒 立春 雨水 惊蛰 春分 清明 谷雨 立夏 小满 芒种 夏至",
             "      小暑 大暑 立秋 处暑 白露 秋分 寒露 霜降 立冬 小雪 大雪 冬至",
             '"""',
             "",
             "TERMS = %r" % (TERMS,),
             "",
             "YEAR_MIN = %d" % min(out),
             "YEAR_MAX = %d" % max(out),
             "",
             "DATA = {"]
    for y in sorted(out):
        lines.append("    %d: %r," % (y, out[y]))
    lines.append("}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    a = int(sys.argv[1]) if len(sys.argv) > 1 else 1900
    b = int(sys.argv[2]) if len(sys.argv) > 2 else 2100
    data = build(a, b)
    here = os.path.dirname(os.path.abspath(__file__))
    emit(data, os.path.join(here, "jieqi_data.py"))
    print("已生成 %d-%d 共 %d 年 × 24 节气" % (a, b, len(data)))
