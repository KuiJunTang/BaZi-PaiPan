# -*- coding: utf-8 -*-
"""devtools 公共路径（第一百一十令：开发工具搬出技能包后统一在此定位）。

技能包只留「装好就能出盘」的东西；审计、构建、校验脚本都住在 devtools/，
但读写仍指向技能包里的 assets／scripts，避免出现第二份副本。

可用环境变量覆盖：
    BAZI_SKILL  技能包目录（默认见下：仓库形态取仓库根，否则 ~/.workbuddy/skills/bazi-paipan）
    BAZI_PROJ   本工程目录（默认 devtools 的上一级）
"""
import os
import sys

# 让同目录与 verify/ 下的模块可互相 import（audit_probe 复用 verify_independent）
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, "verify")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_ROOT = os.path.dirname(_HERE)


def _default_skill():
    """仓库形态（SKILL.md 与 devtools/ 同级）直接认仓库根：clone 下来不必设环境变量。

    本工程内根目录没有 SKILL.md（技能在 ~/.workbuddy/skills/ 下），故仍取安装目录。
    """
    if (os.path.exists(os.path.join(_ROOT, "SKILL.md"))
            and os.path.exists(os.path.join(_ROOT, "scripts", "paipan.py"))):
        return _ROOT
    return os.path.expanduser("~/.workbuddy/skills/bazi-paipan")


SKILL = os.environ.get("BAZI_SKILL") or _default_skill()
PROJ = os.environ.get("BAZI_PROJ") or _ROOT


def skill(*p):
    return os.path.join(SKILL, *p)


def proj(*p):
    return os.path.join(PROJ, *p)
