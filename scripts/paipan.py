#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paipan.py —— 八字排盘命令行入口

用法示例：
    python3 paipan.py --birth "1991-05-18 19:00" --gender male --out ./out
    python3 paipan.py --birth "1991-05-18 19:20" --gender male --lon 121.5 --true-solar
    python3 paipan.py --birth "1991/5/18 19:00" --gender female --name 张某某 --out ./out

产出（同名一对，同源生成，禁手改）：
    <输出目录>/八字排盘.html
    <输出目录>/八字排盘.md
文件名固定为「八字排盘」，不带姓名与四柱（2026-11-01 道长令）。
"""
import argparse
import datetime
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bazi_core as B  # noqa: E402
import render  # noqa: E402

# 落款整块居中（2026-11-01 道长令）：标—署名—三模块联系方式，自上而下居中排列
SIGN = "膠東魁君堂　復城道長　制作"
BRAND = ('<div class="fr">'
         '<span class="m"><i>微信公众号：</i><b>魁君堂</b></span>'
         '<span class="m"><i>复城道长微信：</i><b>18550386868</b></span>'
         '<span class="m"><i>魁君堂官网：</i>'
         '<a href="https://www.kuijuntang.com" target="_blank" rel="noopener">www.kuijuntang.com</a></span>'
         '</div>')


def parse_birth(s):
    s = s.strip().replace("　", " ")
    m = re.match(r"^(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})日?\s*(\d{1,2})?[:时点]?(\d{1,2})?分?$", s)
    if not m:
        raise SystemExit("出生时间格式无法识别：%r（示例：1991-05-18 19:00）" % s)
    y, mo, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
    hh = int(m.group(4) or 0)
    mi = int(m.group(5) or 0)
    return datetime.datetime(y, mo, dd, hh, mi)


def main(argv=None):
    ap = argparse.ArgumentParser(description="八字排盘（四柱·藏干·十神·大运·流年）")
    ap.add_argument("--birth", default=None,
                    help='出生时间，"1991-05-18 19:00"；不给则按此刻（页面亦默认此刻）')
    ap.add_argument("--fixed", action="store_true",
                    help="页面以 --birth 生辰固定打开，不跟随打开时刻")
    ap.add_argument("--gender", default="male", choices=["male", "female"], help="male=乾造 female=坤造")
    ap.add_argument("--name", default="", help="命主姓名（可空）")
    ap.add_argument("--lon", type=float, default=None, help="出生地经度（东经为正），启用真太阳时必须")
    ap.add_argument("--lat", type=float, default=None,
                    help="出生地纬度（北纬为正）。给出后真太阳时按时辰古法（日出定卯、日落定酉）")
    ap.add_argument("--place", default="", help="出生地名称（仅用于界面显示，如 青岛）")
    ap.add_argument("--true-solar", action="store_true", help="启用真太阳时校正")
    ap.add_argument("--no-late-zi", action="store_true", help="23:00 后不换日（默认换日）")
    ap.add_argument("--now", default=None, help="以指定日期作「现在」定位高亮，如 2026-10-31")
    ap.add_argument("--focus", type=int, default=None,
                    help="默认定位到某年（文本提及的年份），如 2032；缺省定位今年")
    ap.add_argument("--out", default="./out", help="输出目录")
    a = ap.parse_args(argv)

    now = parse_birth(a.now + " 12:00") if a.now else datetime.datetime.now().replace(second=0, microsecond=0)
    birth = parse_birth(a.birth) if a.birth else now
    if a.true_solar and a.lon is None:
        raise SystemExit("启用真太阳时须给出 --lon 经度")

    d = B.paipan(birth, a.gender, longitude=a.lon, use_true_solar=a.true_solar,
                 late_zi_next_day=not a.no_late_zi, now=now,
                 focus_year=a.focus, name=a.name, latitude=a.lat)

    foot = BRAND
    # 页面标签（浏览器标签页标题）恒为「魁君堂·八字排盘」（2026-11-01 令）；
    # 输出文档（文件／MD 标题）名为「八字排盘」（2026-11-01 令）
    title = "魁君堂·八字排盘"

    os.makedirs(a.out, exist_ok=True)
    # 文件名固定为「八字排盘」，不加任何后缀（2026-11-01 令）
    stem = "八字排盘"
    p_html = os.path.join(a.out, stem + ".html")
    p_md = os.path.join(a.out, stem + ".md")

    init = {
        "birth": [birth.year, birth.month, birth.day, birth.hour, birth.minute],
        "gender": a.gender,
        "name": a.name,
        "now": [now.year, now.month, now.day],
        "focus": a.focus,
        "lon": a.lon,
        "lat": a.lat,
        "tst": bool(a.true_solar),
        "place": a.place,
        "foot": foot,
        "live": not a.fixed,
    }
    with open(p_html, "w", encoding="utf-8") as f:
        f.write(render.render_html(d, footer=foot, sign=SIGN, doc_title=title, init=init))
    with open(p_md, "w", encoding="utf-8") as f:
        f.write(render.render_md(d) + "\n" +
                "\n---\n膠東魁君堂　復城道長　制作\n\n"
                "微信公众号：魁君堂　复城道长微信：18550386868　|　"
                "魁君堂官网：https://www.kuijuntang.com\n")

    print("四柱：%s" % " ".join(x["gan"] + x["zhi"] for x in d["pillars"]))
    print("起运：%s　交运：%s" % (d["qiyun"]["text"], d["qiyun"]["jiaoyun_text"]))
    print("人元司令：%s（%s后%d日）" % (d["siling"]["gan"], d["siling"]["jie"], d["siling"]["days"]))
    print("HTML：%s" % p_html)
    print("MD　：%s" % p_md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
