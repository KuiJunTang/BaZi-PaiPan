#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bazi_core.py —— 八字排盘内核（纯标准库，无第三方依赖）

口径说明
--------
* 历法时区：北京时间（UTC+8），不做夏令时还原；可选真太阳时校正（经度差 + 均时差）。
* 年柱：立春换年（非正月初一）。
* 月柱：十二「节」换月（立春→寅、惊蛰→卯……小寒→丑），非中气。
* 日柱：儒略日推算，23:00 后归次日（晚子时换日，主流排盘口径）。
* 时柱：五鼠遁。
* 大运：阳年男／阴年女顺行，阴年男／阳年女逆行；起运按「3 日折 1 年、1 日折 4 月、
  1 月折 30 日」折算，交运时刻 = 出生时刻 + 折算时长。
* 藏干、十神、人元司令皆用通行表格，见 references/口径与表格.md。
"""
import datetime
import math

import jieqi_data

GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"
GAN_WX = "木木火火土土金金水水"
ZHI_WX = "水土木木土火火土金金土水"
SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

CANG = {
    "子": "癸", "丑": "己癸辛", "寅": "甲丙戊", "卯": "乙",
    "辰": "戊乙癸", "巳": "丙庚戊", "午": "丁己", "未": "己丁乙",
    "申": "庚壬戊", "酉": "辛", "戌": "戊辛丁", "亥": "壬甲",
}

SHORT = {"比肩": "比", "劫财": "劫", "食神": "食", "伤官": "伤", "偏财": "才",
         "正财": "财", "七杀": "杀", "正官": "官", "偏印": "枭", "正印": "印",
         "日主": "主"}

# 人元司令分野（节气后日数，累计）：寅月戊7丙7甲16 …… 通行表
SILING = {
    "寅": [("戊", 7), ("丙", 7), ("甲", 16)],
    "卯": [("甲", 10), ("乙", 20)],
    "辰": [("乙", 9), ("癸", 3), ("戊", 18)],
    "巳": [("戊", 5), ("庚", 9), ("丙", 16)],
    "午": [("丙", 10), ("己", 9), ("丁", 11)],
    "未": [("丁", 9), ("乙", 3), ("己", 18)],
    "申": [("戊", 7), ("壬", 7), ("庚", 16)],
    "酉": [("庚", 10), ("辛", 20)],
    "戌": [("辛", 9), ("丁", 3), ("戊", 18)],
    "亥": [("戊", 7), ("甲", 5), ("壬", 18)],
    "子": [("壬", 10), ("癸", 20)],
    "丑": [("癸", 9), ("辛", 3), ("己", 18)],
}

# 12 节索引（jieqi_data.TERMS 中位置）：立春惊蛰清明立夏芒种小暑立秋白露寒露立冬大雪小寒
JIE_ORDER = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 0]

# 儒略日 -> 60 甲子序的偏移（以 sxtwl 全量比对校准，见 validate_core.py）
DAY_GZ_SHIFT = 49


# ---------------------------------------------------------------- 基础工具
def term_dt(year, idx):
    """某年第 idx 号节气的北京时刻（datetime）。"""
    if jieqi_data.YEAR_MIN <= year <= jieqi_data.YEAR_MAX:
        minutes = jieqi_data.DATA[year][idx]
        return datetime.datetime(year, 1, 1) + datetime.timedelta(minutes=minutes)
    return _term_dt_astro(year, idx)


def delta_t_seconds(year):
    """ΔT = TT − UT（秒）。Espenak–Meeus 多项式，用于把天文回推的 TT 时刻折成 UT。

    古代 ΔT 可达 40 分钟以上（600 年约 45 分钟），不修正会使交节时刻整体偏晚，
    进而误判月柱；1900 年后走 sxtwl 表，不经此函数。
    """
    y = float(year)
    if y < 500:
        u = (y - 1820) / 100.0
        return -20 + 32 * u * u
    if y < 1600:
        u = (y - 1000) / 100.0
        return (1574.2 - 556.01 * u + 71.23472 * u ** 2 + 0.319781 * u ** 3
                - 0.8503463 * u ** 4 - 0.005050998 * u ** 5 + 0.0083572073 * u ** 6)
    if y < 1700:
        t = y - 1600
        return 120 - 0.9808 * t - 0.01532 * t ** 2 + t ** 3 / 7129.0
    if y < 1800:
        t = y - 1700
        return (8.83 + 0.1603 * t - 0.0059285 * t ** 2 + 0.00013336 * t ** 3
                - t ** 4 / 1174000.0)
    if y < 1860:
        t = y - 1800
        return (13.72 - 0.332447 * t + 0.0068612 * t ** 2 + 0.0041116 * t ** 3
                - 0.00037436 * t ** 4 + 0.0000121272 * t ** 5
                - 0.0000001699 * t ** 6 + 0.000000000875 * t ** 7)
    if y < 1900:
        t = y - 1860
        return (7.62 + 0.5737 * t - 0.251754 * t ** 2 + 0.01680668 * t ** 3
                - 0.0004473624 * t ** 4 + t ** 5 / 233174.0)
    if y < 1920:
        t = y - 1900
        return -2.79 + 1.494119 * t - 0.0598939 * t ** 2 + 0.0061966 * t ** 3 - 0.000197 * t ** 4
    if y < 1941:
        t = y - 1920
        return 21.20 + 0.84493 * t - 0.076100 * t ** 2 + 0.0020936 * t ** 3
    if y < 1961:
        t = y - 1950
        return 29.07 + 0.407 * t - t ** 2 / 233.0 + t ** 3 / 2547.0
    if y < 1986:
        t = y - 1975
        return 45.45 + 1.067 * t - t ** 2 / 260.0 - t ** 3 / 718.0
    if y < 2005:
        t = y - 2000
        return (63.86 + 0.3345 * t - 0.060374 * t ** 2 + 0.0017275 * t ** 3
                + 0.000651814 * t ** 4 + 0.00002373599 * t ** 5)
    if y < 2050:
        t = y - 2000
        return 62.92 + 0.32217 * t + 0.005589 * t ** 2
    return -20 + 32 * ((y - 1820) / 100.0) ** 2


def _term_dt_astro(year, idx):
    """表外年份保底：Meeus 太阳视黄经二分定位（精度约 ±15 分钟，交节边界须复核）。"""
    target = (285 + idx * 15) % 360  # 小寒 idx0 对应黄经 285°
    approx = datetime.datetime(year, 1, 1) + datetime.timedelta(days=idx * 15.2)
    a = approx - datetime.timedelta(days=12)
    b = approx + datetime.timedelta(days=12)
    for _ in range(60):
        mid = a + (b - a) / 2
        if _lon_crossed(a, mid, target):
            b = mid
        else:
            a = mid
    # 解出的是力学时（TT）时刻：减 ΔT 得 UT，再加东八区
    return (a + (b - a) / 2 + datetime.timedelta(hours=8)
            - datetime.timedelta(seconds=delta_t_seconds(year)))


def _lon(dt):
    """太阳视黄经（度，0-360）。"""
    jd = _jdn_frac(dt)
    t = (jd - 2451545.0) / 36525.0
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    m = math.radians(357.52911 + 35999.05029 * t - 0.0001537 * t * t)
    c = ((1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(m)
         + (0.019993 - 0.000101 * t) * math.sin(2 * m)
         + 0.000289 * math.sin(3 * m))
    true_lon = l0 + c
    omega = math.radians(125.04 - 1934.136 * t)
    app = true_lon - 0.00569 - 0.00478 * math.sin(omega)
    return app % 360


def _lon_crossed(a, b, target):
    la, lb = _lon(a), _lon(b)
    span = (lb - la) % 360
    return ((target - la) % 360) <= span


def _jdn_frac(dt):
    jdn = _jdn(dt.year, dt.month, dt.day)
    frac = (dt.hour * 3600 + dt.minute * 60 + dt.second) / 86400.0
    return jdn - 0.5 + frac


def _jdn(y, m, d):
    """儒略日数：1582-10-15 起用格里历，之前用儒略历（与 sxtwl 日柱体系一致）。"""
    a = (14 - m) // 12
    y2 = y + 4800 - a
    m2 = m + 12 * a - 3
    base = d + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4
    if y < 1582 or (y == 1582 and (m < 10 or (m == 10 and d < 15))):
        return base - 32083
    return base - y2 // 100 + y2 // 400 - 32045


def gz_name(i):
    return GAN[i % 10] + ZHI[i % 12]


def gan_wx(g):
    return GAN_WX[GAN.index(g)]


def zhi_wx(z):
    return ZHI_WX[ZHI.index(z)]


def ten_god(day_gan, other_gan):
    """日干（我）对另一天干的十神。"""
    if other_gan == day_gan:
        return "比肩"
    dw, ow = gan_wx(day_gan), gan_wx(other_gan)
    same = (GAN.index(day_gan) % 2) == (GAN.index(other_gan) % 2)
    if dw == ow:
        return "比肩" if same else "劫财"
    if SHENG[dw] == ow:
        return "食神" if same else "伤官"
    if KE[dw] == ow:
        return "偏财" if same else "正财"
    if KE[ow] == dw:
        return "七杀" if same else "正官"
    return "偏印" if same else "正印"


# ---------------------------------------------------------------- 四柱
def jie_list(year):
    """该年 12 个「节」：(时刻, 节气名, 节气索引)"""
    out = []
    for idx in JIE_ORDER:
        out.append((term_dt(year, idx), jieqi_data_terms()[idx], idx))
    return out


_TERMS = ["小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明", "谷雨",
          "立夏", "小满", "芒种", "夏至", "小暑", "大暑", "立秋", "处暑",
          "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪", "冬至"]


def jieqi_data_terms():
    return _TERMS


def _cand_years(y):
    """前中后三年，保证跨年节气可判；表外年份走天文保底。"""
    return [y - 1, y, y + 1]


def prev_jie(dt):
    """dt 之前（含）最近的一个「节」：(时刻, 名, 索引)。"""
    cands = []
    for y in _cand_years(dt.year):
        for t, name, idx in jie_list(y):
            if t <= dt:
                cands.append((t, name, idx))
    return max(cands, key=lambda x: x[0]) if cands else None


def next_jie(dt):
    cands = []
    for y in _cand_years(dt.year):
        for t, name, idx in jie_list(y):
            if t > dt:
                cands.append((t, name, idx))
    return min(cands, key=lambda x: x[0]) if cands else None


def year_gz_index(dt):
    y = dt.year
    if dt < term_dt(y, 2):   # 立春前属上一年
        y -= 1
    return (y - 4) % 60


def month_gz_index(dt):
    t, name, idx = prev_jie(dt)
    zhi_i = (idx // 2 + 1) % 12
    # 年干（以立春为界）
    yg = year_gz_index(dt) % 10
    k = (zhi_i - 2) % 12          # 寅=0 的月序
    gan_i = (yg * 2 + 2 + k) % 10
    return gan_i * 10 + zhi_i if False else _gz(gan_i, zhi_i)


def _gz(gan_i, zhi_i):
    """由干、支索引求 60 甲子序号"""
    for i in range(60):
        if i % 10 == gan_i and i % 12 == zhi_i:
            return i
    raise ValueError("干支不配")


def day_gz_index(dt):
    return (_jdn(dt.year, dt.month, dt.day) + DAY_GZ_SHIFT) % 60


def hour_gz_index(dt, day_idx=None):
    """时柱；day_idx 可传入已换日后的日柱。"""
    h = dt.hour
    zhi_i = ((h + 1) // 2) % 12
    if day_idx is None:
        day_idx = day_gz_index(dt)
    dg = day_idx % 10
    zi_gan = (dg % 5) * 2
    gan_i = (zi_gan + zhi_i) % 10
    return _gz(gan_i, zhi_i)


# ---------------------------------------------------------------- 排盘
def _eot_minutes(dt):
    """均时差（分钟，正＝真太阳时快于平太阳时）。

    Meeus 28.1：E = L0 − 0.0057183 − α + Δψ·cosε。T 取力学时（TT，含 ΔT），
    太阳视黄经与节气回推同一套（_lon），古代日期自洽——现代 Spencer 近似式
    在唐代会偏差 1–3 分钟，此法全网期可用。"""
    ut = dt - datetime.timedelta(hours=8)
    tt = ut + datetime.timedelta(seconds=delta_t_seconds(ut.year))
    jd = _jdn_frac(tt)
    t = (jd - 2451545.0) / 36525.0
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    omega = math.radians(125.04 - 1934.136 * t)
    eps = (23.4392911 - 0.0130042 * t - 1.64e-7 * t * t + 5.04e-7 * t ** 3
           + 9.20 / 3600.0 * math.cos(omega))
    lam = math.radians(_lon(tt))
    alpha = math.degrees(math.atan2(math.cos(math.radians(eps)) * math.sin(lam),
                                    math.cos(lam))) % 360.0
    e = (l0 - 0.0057183 - alpha
         - 0.00478 * math.sin(omega) * math.cos(math.radians(eps))) % 360.0
    if e > 180.0:
        e -= 360.0
    return e * 4.0


def true_solar_time(dt, longitude, eot=True):
    """北京时间 -> 真太阳时（经度差 + 均时差，均时差为天文法）。"""
    delta_min = (longitude - 120.0) * 4.0
    if eot:
        delta_min += _eot_minutes(dt)
    return dt + datetime.timedelta(minutes=delta_min)


def _obliquity(tt_dt):
    """真黄赤交角（度），Meeus 22.2 含主章动项。"""
    t = (_jdn_frac(tt_dt) - 2451545.0) / 36525.0
    omega = math.radians(125.04 - 1934.136 * t)
    return (23.4392911 - 0.0130042 * t - 1.64e-7 * t * t + 5.04e-7 * t ** 3
            + 9.20 / 3600.0 * math.cos(omega))


def sun_rise_set_ast(date_dt, latitude):
    """古法定时辰用：给定真太阳时（AST）日期与纬度，返回（日出AST分, 日落AST分）。

    日出日落按太阳上边缘 h0=−0.833°（含蒙气差与视半径）；
    太阳赤纬由该日 AST 正午的视黄经（_lon，与节气同套）算出：
    sinδ = sinε·sinλ。返回的「AST 分」是以真太阳时 0:00 起计的分钟数。"""
    noon = date_dt.replace(hour=12, minute=0, second=0, microsecond=0)
    lam = math.radians(_lon(noon))
    eps = math.radians(_obliquity(noon))
    sin_d = math.sin(eps) * math.sin(lam)
    phi = math.radians(latitude)
    h0 = math.radians(-0.833)
    x = (math.sin(h0) - math.sin(phi) * sin_d) / (math.cos(phi) * math.cos(math.asin(sin_d)))
    x = max(-1.0, min(1.0, x))
    H0 = math.degrees(math.acos(x))
    return 720.0 - 4.0 * H0, 720.0 + 4.0 * H0


def hour_branch_ancient(ast_min, sunrise, sunset):
    """古法十二时辰：日出定卯初、日落定酉初，昼弧/夜弧各六等分。

    昼：卯辰巳午未申；夜：酉戌亥子丑寅。午初＝真太阳正午、子初＝真太阳子夜
    （昼弧中点、夜弧中点自动落在正午/子夜）。
    返回（支索引 0-11，子=0；昼夜标记）。"""
    day = sunset - sunrise
    night = 1440.0 - day
    if sunrise <= ast_min < sunset:
        k = min(int((ast_min - sunrise) / (day / 6.0)), 5)
        return (3 + k) % 12, "day"
    u = ast_min - sunset if ast_min >= sunset else ast_min + 1440.0 - sunset
    k = min(int(u / (night / 6.0)), 5)
    return (9 + k) % 12, "night"


def hour_gz_ancient(ast_min, sunrise, sunset, day_idx):
    """古法时柱：支按日出/日落划分，干按五鼠遁（日干起子）。"""
    zhi_i, seg = hour_branch_ancient(ast_min, sunrise, sunset)
    zi_gan = (day_idx % 5) * 2
    return _gz((zi_gan + zhi_i) % 10, zhi_i), seg


def paipan(birth, gender="male", longitude=None, use_true_solar=False,
           late_zi_next_day=True, dayun_steps=12, now=None,
           focus_year=None, name="", latitude=None):
    """birth: datetime（北京时间）。latitude: 纬度（度，北正）。

    use_true_solar 且 latitude 给定时，时辰按古法（日出定卯初、日落定酉初，
    昼夜弧各六等分），日柱以真太阳子夜分日；否则按固定钟点切分。"""
    if now is None:
        now = datetime.datetime.now()
    calc = birth
    tst_shift = 0
    ancient = False
    sun = None
    if use_true_solar and longitude is not None:
        calc = true_solar_time(birth, longitude)
        tst_shift = round((calc - birth).total_seconds() / 60)
        ancient = latitude is not None

    year_i = year_gz_index(calc)
    month_i = month_gz_index(calc)

    day_ref = calc
    if ancient:
        sunrise, sunset = sun_rise_set_ast(calc, latitude)
        ast_min = calc.hour * 60 + calc.minute + calc.second / 60.0
        day_i = day_gz_index(calc)              # 子初＝真太阳子夜，按 calc 当日
        hour_i, seg = hour_gz_ancient(ast_min, sunrise, sunset, day_i)
        sun = {
            "rise": "%.2d:%.2d" % (int(sunrise) // 60, int(round(sunrise)) % 60),
            "set": "%.2d:%.2d" % (int(sunset) // 60, int(round(sunset)) % 60),
            "seg": seg,
        }
    else:
        if late_zi_next_day and calc.hour >= 23:
            day_ref = calc + datetime.timedelta(days=1)
        day_i = day_gz_index(day_ref)
        hour_i = hour_gz_index(calc, day_i)

    day_gan = GAN[day_i % 10]

    pillars = []
    for pos, gi in (("年柱", year_i), ("月柱", month_i), ("日柱", day_i), ("时柱", hour_i)):
        g, z = GAN[gi % 10], ZHI[gi % 12]
        cang = []
        for c in CANG[z]:
            cang.append({
                "gan": c, "wx": gan_wx(c),
                "god": ten_god(day_gan, c),   # 藏干：同干即比肩（"日主"仅用于日柱天干 star，D96）
                "short": SHORT[ten_god(day_gan, c)],
            })
        star = "日主" if pos == "日柱" else ten_god(day_gan, g)
        pillars.append({
            "pos": pos, "gan": g, "zhi": z,
            "gan_wx": gan_wx(g), "zhi_wx": zhi_wx(z),
            "star": star, "star_short": SHORT.get(star, ""),
            "cang": cang,
        })

    # 人元司令
    pj = prev_jie(calc)
    days_after = int((calc - pj[0]).total_seconds() // 86400)
    siling_gan, acc = None, 0
    for g, n in SILING[ZHI[month_i % 12]]:
        acc += n
        if days_after < acc:
            siling_gan = g
            break
    if siling_gan is None:
        siling_gan = SILING[ZHI[month_i % 12]][-1][0]

    # 大运
    is_yang_year = (year_i % 10) % 2 == 0
    forward = (is_yang_year and gender == "male") or (not is_yang_year and gender == "female")
    if forward:
        nj = next_jie(calc)
        span = nj[0] - calc
        ref = nj
    else:
        span = calc - pj[0]
        ref = pj

    days = span.total_seconds() / 86400.0
    years = int(days // 3)
    months_f = (days - years * 3) * 4.0
    months = int(months_f)
    days_f = (months_f - months) * 30.0
    d_days = int(days_f)
    hours = int(round((days_f - d_days) * 24))
    if hours >= 24:
        hours -= 24
        d_days += 1

    jiaoyun = _add_years_months_days(birth, years, months, d_days) + datetime.timedelta(hours=hours)

    dayun_list = []
    # 「运前」列
    dayun_list.append({
        "year": birth.year, "age": 1, "gan": "", "zhi": "",
        "gan_wx": "", "zhi_wx": "", "star": "运", "star_short": "前",
        "is_pre": True, "highlight": False,
    })
    for i in range(1, dayun_steps + 1):
        gi = (month_i + i) % 60 if forward else (month_i - i) % 60
        g, z = GAN[gi % 10], ZHI[gi % 12]
        y = jiaoyun.year + 10 * (i - 1)
        age = y - birth.year + 1
        star = ten_god(day_gan, g)
        zstar = ten_god(day_gan, CANG[z][0])
        dayun_list.append({
            "year": y, "age": age, "gan": g, "zhi": z,
            "gan_wx": gan_wx(g), "zhi_wx": zhi_wx(z),
            "star": star, "star_short": SHORT[star],
            "zhi_star": zstar, "zhi_star_short": SHORT[zstar],
            "is_pre": False, "highlight": False,
        })

    # ---- 各步大运所辖十年 ----
    def _decade(base_year):
        out = []
        for k in range(10):
            y = base_year + k
            gi = (y - 4) % 60
            g, z = GAN[gi % 10], ZHI[gi % 12]
            star = ten_god(day_gan, g)
            zstar = ten_god(day_gan, CANG[z][0])
            out.append({
                "year": y, "age": y - birth.year + 1, "gan": g, "zhi": z,
                "gan_wx": gan_wx(g), "zhi_wx": zhi_wx(z),
                "star": star, "star_short": SHORT[star],
                "zhi_star": zstar, "zhi_star_short": SHORT[zstar],
                "cang": [{"gan": c, "wx": gan_wx(c), "short": SHORT[ten_god(day_gan, c)]}
                         for c in CANG[z]],
                "highlight": False,
            })
        return out

    for c in dayun_list:
        c["cang"] = ([{"gan": x, "wx": gan_wx(x), "short": SHORT[ten_god(day_gan, x)]}
                      for x in CANG[c["zhi"]]] if c["zhi"] else [])
        if c["is_pre"]:
            # 运前：只列出生年至起运前一年，其余留空
            n = max(0, min(10, jiaoyun.year - birth.year))
            arr = _decade(birth.year)[:n]
            for _ in range(n, 10):
                arr.append({"year": None, "age": None, "gan": "", "zhi": "",
                            "gan_wx": "", "zhi_wx": "", "star": "", "star_short": "",
                            "zhi_star": "", "zhi_star_short": "", "cang": [], "empty": True,
                            "highlight": False})
            c["ln"] = arr
        else:
            c["ln"] = _decade(c["year"])

    def _dy_for(year):
        idx = 0
        for i, c in enumerate(dayun_list[1:], start=1):
            if year >= c["year"]:
                idx = i
        return idx

    def _ln_index(arr, y):
        for j, c in enumerate(arr):
            if c.get("year") == y:
                return j
        for j in range(len(arr) - 1, -1, -1):
            if arr[j].get("year"):
                return j
        return 0

    now_dy = _dy_for(now.year)
    now_ln = _ln_index(dayun_list[now_dy]["ln"], now.year)

    # 默认选点：优先「文本提及的年份」，否则今年
    if focus_year:
        sel_dy = _dy_for(focus_year)
        sel_ln = _ln_index(dayun_list[sel_dy]["ln"], focus_year)
    else:
        sel_dy, sel_ln = now_dy, now_ln

    dayun_list[sel_dy]["highlight"] = True
    liunian_list = dayun_list[sel_dy]["ln"]
    liunian_list[sel_ln]["highlight"] = True

    # 交运描述：逢某年某节后 N 天
    jy_jie = prev_jie(jiaoyun)
    jy_days = (jiaoyun.date() - jy_jie[0].date()).days
    jy_year_gz = gz_name((jiaoyun.year - 4) % 60)

    dyc = dayun_list[sel_dy]
    lnc = liunian_list[sel_ln]
    top = {
        "dayun": {
            "gan": dyc["gan"], "zhi": dyc["zhi"],
            "gan_wx": dyc["gan_wx"], "zhi_wx": dyc["zhi_wx"],
            "star": dyc["star"], "cang": dyc["cang"],
        },
        "liunian": {
            "gan": lnc["gan"], "zhi": lnc["zhi"],
            "gan_wx": lnc["gan_wx"], "zhi_wx": lnc["zhi_wx"],
            "star": lnc["star"], "cang": lnc["cang"],
        },
    }

    return {
        "name": name,
        "gender": gender,
        "label": "乾造" if gender == "male" else "坤造",
        "birth": birth,
        "calc": calc,
        "tst_shift": tst_shift,
        "sun": sun,
        "pillars": pillars,
        "day_master": day_gan,
        "siling": {"gan": siling_gan, "jie": pj[1], "days": days_after},
        "qiyun": {
            "forward": forward,
            "years": years, "months": months, "days": d_days, "hours": hours,
            "text": "出生后%d年%d月%d天%d小时" % (years, months, d_days, hours),
            "jiaoyun_dt": jiaoyun,
            "jiaoyun_text": "逢%s年%s后%d天" % (jy_year_gz[0], jy_jie[1], jy_days),
            "jiaoyun_year_gz": jy_year_gz,
            "ref_jie": ref[1],
        },
        "dayun": dayun_list,
        "dayun_cur": sel_dy,
        "liunian": liunian_list,
        "liunian_cur": sel_ln,
        "sel": {"dy": sel_dy, "ln": sel_ln},
        "now": {"dy": now_dy, "ln": now_ln},
        "top": top,
    }


def _add_years_months_days(dt, y, m, d):
    """按日历年月日相加（月份溢出顺延）。"""
    yy = dt.year + y
    mm = dt.month + m
    yy += (mm - 1) // 12
    mm = (mm - 1) % 12 + 1
    import calendar
    dd = min(dt.day, calendar.monthrange(yy, mm)[1])
    out = dt.replace(year=yy, month=mm, day=dd)
    return out + datetime.timedelta(days=d)


def season_luokuan(now=None):
    """落款：{干支}年{春夏秋冬}（按当日节气，立春换岁，节气换季）。"""
    if now is None:
        now = datetime.datetime.now()
    gi = year_gz_index(now)
    # 季节：以四立为界
    y = now.year
    lichun, lixia, liqiu, lidong = (term_dt(y, 2), term_dt(y, 8), term_dt(y, 14), term_dt(y, 20))
    if now >= lidong:
        season = "冬"
    elif now >= liqiu:
        season = "秋"
    elif now >= lixia:
        season = "夏"
    else:
        season = "春"
    return gz_name(gi) + "年" + season
