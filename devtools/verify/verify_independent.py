#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# —— devtools 引导：把技能包的 scripts 放进 import 路径（第一百一十令）——
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from paths import SKILL as SKILL_DIR, PROJ as PROJ_DIR  # noqa: E402
_sys.path.insert(0, _os.path.join(SKILL_DIR, "scripts"))
# —— 引导结束 ——

"""独立口径复核（2026-11-02 九十八令）

目的：不用「自己验自己」。本脚本的判据全部独立于 bazi_core：
  1. 四柱干支 —— 取 sxtwl（寿星天文历，C++ 库）的 getYearGZ／getMonthGZ／getDayGZ／getShiGz；
  2. 十神 —— 本文件内按阴阳五行生克重写一份（与 bazi_core.ten_god 无共享代码）；
  3. 藏干 —— 本文件内置标准藏干表；
  4. 大运 —— 本文件按「阳男阴女顺、阴男阳女逆」从月柱独立推排；
  5. 流年 —— 用 sxtwl 取该年（7 月，必在立春后）年干支独立核对。

已知口径差异（非缺陷，单独统计）：
  · sxtwl 的年／月柱按「日」切换（节气当天 0 点即换），本项目按**精确节气时刻**切换；
    故节气当天出生的样本单列为「边界样本」，不计入不一致，另用精确时刻人工核对。
  · 本项目默认 23:00 起算次日（晚子时换日），sxtwl 按自然日。故随机样本时刻取 0–22 时，
    23 点换日规则另设专项。

用法：python3 verify_independent.py [样本数，默认 240]
"""
import datetime
import random
import sys

import sxtwl

from bazi_core import paipan, term_dt

GAN = '甲乙丙丁戊己庚辛壬癸'
ZHI = '子丑寅卯辰巳午未申酉戌亥'
GAN_WX = {'甲': '木', '乙': '木', '丙': '火', '丁': '火', '戊': '土',
          '己': '土', '庚': '金', '辛': '金', '壬': '水', '癸': '水'}
# 相生环：木→火→土→金→水→木；相克：+2（木克土、土克水、水克火、火克金、金克木）
WX_RING = ['木', '火', '土', '金', '水']

# 标准藏干表（主气在前）
CANG_REF = {
    '子': ['癸'], '丑': ['己', '癸', '辛'], '寅': ['甲', '丙', '戊'], '卯': ['乙'],
    '辰': ['戊', '乙', '癸'], '巳': ['丙', '庚', '戊'], '午': ['丁', '己'],
    '未': ['己', '丁', '乙'], '申': ['庚', '壬', '戊'], '酉': ['辛'],
    '戌': ['戊', '辛', '丁'], '亥': ['壬', '甲'],
}


def ten_god_ref(day_gan, other):
    """独立十神：同我比劫、我生食伤、我克财、克我官杀、生我印。同阴阳取前者。"""
    dw, ow = GAN_WX[day_gan], GAN_WX[other]
    same = (GAN.index(day_gan) % 2) == (GAN.index(other) % 2)
    di, oi = WX_RING.index(dw), WX_RING.index(ow)
    if dw == ow:
        return '比肩' if same else '劫财'
    step = (oi - di) % 5
    if step == 1:
        return '食神' if same else '伤官'
    if step == 2:
        return '偏财' if same else '正财'
    if step == 3:
        return '七杀' if same else '正官'
    return '偏印' if same else '正印'


def dayun_ref(year_gan, month_gz, gender, steps=12):
    """独立排大运：阳年男／阴年女顺排，阴年男／阳年女逆排，自月柱起。"""
    yang_year = GAN.index(year_gan) % 2 == 0
    forward = (yang_year and gender == 'male') or (not yang_year and gender == 'female')
    mi = month_gz
    out = []
    for _ in range(steps):
        mi = (mi + 1) % 60 if forward else (mi - 1) % 60
        out.append(GAN[mi % 10] + ZHI[mi % 12])
    return out, forward


def gz_index(gan, zhi):
    for i in range(60):
        if i % 10 == GAN.index(gan) and i % 12 == ZHI.index(zhi):
            return i
    raise ValueError('干支不配 %s%s' % (gan, zhi))


def gz_of_index(i):
    return GAN[i % 10] + ZHI[i % 12]


def sxtwl_gz(y, m, d, hour):
    """用 sxtwl 取四柱（独立源）。hour 取整点小时数。"""
    day = sxtwl.fromSolar(y, m, d)
    yg, mg, dg = day.getYearGZ(), day.getMonthGZ(), day.getDayGZ()
    hg = sxtwl.getShiGz(dg.tg, hour)
    return ((GAN[yg.tg] + ZHI[yg.dz]), (GAN[mg.tg] + ZHI[mg.dz]),
            (GAN[dg.tg] + ZHI[dg.dz]), (GAN[hg.tg] + ZHI[hg.dz]))


def on_term_day(dt):
    """是否落在节气当天（此类样本 sxtwl 按日切换、本项目按时刻切换，口径不同）。"""
    cands = []
    for yy in (dt.year - 1, dt.year, dt.year + 1):
        try:
            for idx in range(24):
                cands.append(term_dt(yy, idx))
        except Exception:
            pass
    return any(c.date() == dt.date() for c in cands)


def is_julian_gap(y, m, d):
    """1582-10-05 ~ 10-14 在格里历中不存在。"""
    return y == 1582 and m == 10 and 5 <= d <= 14


def check_one(dt, gender):
    """返回 (问题列表, 是否边界样本)。"""
    d = paipan(dt, gender=gender)
    p = d['pillars']
    mine = (p[0]['gan'] + p[0]['zhi'], p[1]['gan'] + p[1]['zhi'],
            p[2]['gan'] + p[2]['zhi'], p[3]['gan'] + p[3]['zhi'])
    ref = sxtwl_gz(dt.year, dt.month, dt.day, dt.hour)
    issues = []
    names = ('年柱', '月柱', '日柱', '时柱')
    boundary = on_term_day(dt)
    for i in range(4):
        if mine[i] != ref[i]:
            if boundary and i in (0, 1):
                continue          # 节气当天口径差异，单列
            issues.append('%s 我=%s sxtwl=%s' % (names[i], mine[i], ref[i]))

    # 十神（日主对年/月/时干、以及各柱藏干）
    dm = p[2]['gan']
    for i in (0, 1, 2, 3):
        want = '日主' if i == 2 else ten_god_ref(dm, p[i]['gan'])
        if i != 2 and p[i]['star'] != want:
            issues.append('%s干十神 我=%s 独立=%s' % (names[i], p[i]['star'], want))
        for c in p[i]['cang']:
            w = ten_god_ref(dm, c['gan'])
            if c['god'] != w:
                issues.append('%s藏干%s十神 我=%s 独立=%s' % (names[i], c['gan'], c['god'], w))

    # 藏干表
    for i in (0, 1, 2, 3):
        z = p[i]['zhi']
        mine_c = [c['gan'] for c in p[i]['cang']]
        if mine_c != CANG_REF[z]:
            issues.append('%s藏干 我=%s 标准=%s' % (names[i], ''.join(mine_c), ''.join(CANG_REF[z])))

    # 大运干支序列
    seq, forward = dayun_ref(p[0]['gan'], gz_index(p[1]['gan'], p[1]['zhi']), gender)
    mine_seq = [x['gan'] + x['zhi'] for x in d['dayun'][1:1 + len(seq)]]
    if mine_seq != seq:
        issues.append('大运序列 我=%s 独立=%s' % (' '.join(mine_seq[:4]), ' '.join(seq[:4])))
    # 顺逆方向：与现代大运首步对比
    # 流年干支
    for dy in d['dayun']:
        for ln in dy.get('ln', []):
            y = ln['year']
            if not isinstance(y, int) or not (600 <= y <= 2100):
                continue          # 运前空缺列（empty:True）跳过
            ref_y = GAN[sxtwl.fromSolar(y, 7, 1).getYearGZ().tg] + ZHI[sxtwl.fromSolar(y, 7, 1).getYearGZ().dz]
            if ln['gan'] + ln['zhi'] != ref_y:
                issues.append('流年 %d 我=%s%s 独立=%s' % (y, ln['gan'], ln['zhi'], ref_y))
                break
        else:
            continue
        break

    # 人元司令：属「月令分野」而非藏干（如酉月前 7 日庚司令、藏干只有辛），
    # 故不校验干支归属，仅校验天数落在节气后 0–30 日内。
    # 节气间隔最长约 31.5 天，月内天数可达 31；分野表累计 30 天后取末干（通行处理）
    if not (0 <= d['siling']['days'] <= 32):
        issues.append('人元司令天数异常：%s' % d['siling']['days'])
    return issues, boundary


def rand_dt(rng):
    """随机日期时刻：80% 1900–2100，20% 600–1900；时刻 0–22 时。"""
    if rng.random() < 0.8:
        y = rng.randint(1900, 2100)
    else:
        y = rng.randint(600, 1899)
    m = rng.randint(1, 12)
    d = rng.randint(1, 28)
    h = rng.randint(0, 22)
    mi = rng.choice([0, 5, 15, 29, 30, 45, 59])
    return datetime.datetime(y, m, d, h, mi)


def detail(dt, gender):
    """可人工核对的明细。"""
    d = paipan(dt, gender=gender)
    p = d['pillars']
    lines = []
    lines.append('%s %s（%s）' % (dt.strftime('%Y-%m-%d %H:%M'), '男' if gender == 'male' else '女', d['label']))
    lines.append('  四柱：' + '　'.join('%s%s' % (x['gan'], x['zhi']) for x in p))
    lines.append('  主星：' + '　'.join(x['star'] for x in p))
    lines.append('  藏干：' + '　'.join(''.join(c['gan'] for c in x['cang']) for x in p))
    lines.append('  藏神：' + '　'.join('/'.join(c['god'] for c in x['cang']) for x in p))
    lines.append('  起运：%s；交运：%s' % (d['qiyun']['text'], d['qiyun']['jiaoyun_text']))
    dy = d['dayun'][1:5]
    lines.append('  大运：' + '　'.join('%s(%d岁)' % (x['gan'] + x['zhi'], x['age']) for x in dy))
    ln = d['dayun'][1]['ln'][:4]
    lines.append('  流年：' + '　'.join('%d%s%s' % (x['year'], x['gan'], x['zhi']) for x in ln))
    lines.append('  人元：%s（%s后%d日）' % (d['siling']['gan'], d['siling']['jie'], d['siling']['days']))
    ref = sxtwl_gz(dt.year, dt.month, dt.day, dt.hour)
    lines.append('  独立源(sxtwl)：' + '　'.join(ref))
    # 口径差异说明（避免把口径当错误）
    if on_term_day(dt):
        lines.append('  ※ 本样本落在节气当日：sxtwl 按「日」换年/月柱，本项目按**精确节气时刻**，'
                     '差异属口径不同；本项目已用 term_dt 前后 1 分钟验证切换正确。')
    if dt.hour >= 23:
        lines.append('  ※ 本样本在 23 时后：本项目「晚子时归次日」（日柱、时柱按次日），'
                     'sxtwl 按自然日，故日柱差一位属口径不同。')
    return '\n'.join(lines)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 240
    rng = random.Random(20261102)
    bad = []
    boundary = 0
    tested = 0
    print('=== 独立口径复核（sxtwl + 独立十神/藏干/大运）===')
    print('样本 %d 例，年份 600–2100，时刻 0–22 时' % n)
    for k in range(n):
        dt = rand_dt(rng)
        gender = rng.choice(['male', 'female'])
        if is_julian_gap(dt.year, dt.month, dt.day):
            continue
        try:
            issues, bd = check_one(dt, gender)
        except Exception as e:
            bad.append((dt, gender, ['异常：%r' % e]))
            continue
        tested += 1
        if bd:
            boundary += 1
        if issues:
            bad.append((dt, gender, issues))

    print('实际核对 %d 例（其中节气当天边界样本 %d 例）' % (tested, boundary))
    print('不一致样本 %d 例' % len(bad))
    for dt, g, iss in bad[:20]:
        print('  ✗', dt.strftime('%Y-%m-%d %H:%M'), '男' if g == 'male' else '女')
        for x in iss[:6]:
            print('      -', x)
    if not bad:
        print('  ✓ 四柱／十神／藏干／大运／流年／人元 全部一致')

    print()
    print('=== 手工复核明细（可逐项对照万年历）===')
    samples = [
        (datetime.datetime(1991, 5, 18, 19, 0), 'male'),
        (datetime.datetime(2026, 11, 2, 22, 49), 'male'),
        (datetime.datetime(1984, 2, 4, 23, 0), 'female'),
        (datetime.datetime(1587, 11, 2, 9, 0), 'male'),
        (datetime.datetime(1949, 10, 1, 15, 0), 'male'),
        (datetime.datetime(2000, 2, 29, 6, 30), 'female'),
    ]
    for dt, g in samples:
        print()
        print(detail(dt, g))

    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
