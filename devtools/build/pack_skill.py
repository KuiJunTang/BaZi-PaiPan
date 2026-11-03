#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# —— devtools 引导：定位技能包（第一百一十令）——
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from paths import SKILL as SKILL_DIR, PROJ as PROJ_DIR  # noqa: E402
# —— 引导结束 ——

"""pack_skill.py —— 打可分发包（dist/八字排盘-技能包-vX.Y.Z.zip）

只打**白名单里的 11 个运行文件**（第一百一十令：技能包只含运行所需），根目录固定 `bazi-paipan/`。

为什么不用 `zip -r`：macOS 的 `zip` 存中文名不带 UTF-8 标志位，Windows 解压 `references/口径与表格.md`
会变乱码（D108）。这里用 zipfile 并显式置 `flag_bits |= 0x800`，各平台均按 UTF-8 解名。

用法：
    python3 devtools/build/pack_skill.py            # 版本号取自 SKILL.md 的 version，不另写一处
    python3 devtools/build/pack_skill.py --verify   # 打完再解到临时目录实测：文件数、中文名、出盘逐字节比对
"""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT_NAME = "bazi-paipan"          # 包根目录名：纯 ASCII，避免各平台解压乱码
FILES = [                          # 11 个，运行所需；增删须同步 SKILL.md「文件」一节
    "SKILL.md",
    "scripts/paipan.py",
    "scripts/bazi_core.py",
    "scripts/render.py",
    "scripts/jieqi_data.py",
    "assets/app.css",
    "assets/app.js",
    "assets/data.js",
    "assets/cities.js",
    "assets/logo.b64",
    "references/口径与表格.md",
]


def skill_version():
    with open(os.path.join(SKILL_DIR, "SKILL.md"), encoding="utf-8") as f:
        m = re.search(r"^version:\s*([0-9][0-9.]*)", f.read(), re.M)
    if not m:
        sys.exit("SKILL.md 缺 version 字段，无法命名分发件")
    return m.group(1)


def build(version):
    dist = os.path.join(PROJ_DIR, "dist")
    os.makedirs(dist, exist_ok=True)
    out = os.path.join(dist, "八字排盘-技能包-v%s.zip" % version)
    missing = [f for f in FILES if not os.path.exists(os.path.join(SKILL_DIR, f))]
    if missing:
        sys.exit("技能包缺文件：%s" % "、".join(missing))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in FILES:
            src = os.path.join(SKILL_DIR, rel)
            zi = zipfile.ZipInfo(ROOT_NAME + "/" + rel, date_time=(2026, 11, 3, 0, 0, 0))
            zi.flag_bits |= 0x800                      # UTF-8 文件名标志（D108）
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            with open(src, "rb") as f:
                z.writestr(zi, f.read())
    print("已打包：%s（%d 个文件，%.0f KB）"
          % (out, len(FILES), os.path.getsize(out) / 1024.0))
    for rel in FILES:
        p = os.path.join(SKILL_DIR, rel)
        print("  %9d B  %s  %s" % (os.path.getsize(p),
                                   hashlib.sha256(open(p, "rb").read()).hexdigest()[:12], rel))
    return out


def verify(zip_path):
    """解到临时干净目录：查文件数／中文名／编码标志，出盘后与成品逐字节比对。"""
    fails = []
    tmp = tempfile.mkdtemp(prefix="bazi_install_")
    try:
        with zipfile.ZipFile(zip_path) as z:
            # 只有中文名需要 0x800；ASCII 名加不加标志都一样解（zipfile 写 ASCII 名时会自行清掉该位）
            bad_flag = [i.filename for i in z.infolist()
                        if any(ord(c) > 127 for c in i.filename) and not (i.flag_bits & 0x800)]
            names = z.namelist()
            z.extractall(tmp)
        if len(names) != len(FILES):
            fails.append("条目数 %d ≠ %d" % (len(names), len(FILES)))
        if bad_flag:
            fails.append("未置 UTF-8 标志：%s" % "、".join(bad_flag))
        for rel in FILES:
            if not os.path.exists(os.path.join(tmp, ROOT_NAME, rel)):
                fails.append("解压缺文件：%s" % rel)
        print("解压：%d 条，中文名 %s，UTF-8 标志 %s"
              % (len(names),
                 "正常" if os.path.exists(os.path.join(tmp, ROOT_NAME, "references/口径与表格.md")) else "乱码",
                 "齐" if not bad_flag else "缺"))

        calc = os.path.join(tmp, "calc")
        r = subprocess.run([sys.executable, os.path.join(tmp, ROOT_NAME, "scripts/paipan.py"),
                            "--birth", "1991-05-18 19:00", "--gender", "male",
                            "--fixed", "--out", calc],
                           capture_output=True, text=True)
        if r.returncode != 0:
            fails.append("干净目录出盘失败：%s" % (r.stderr.strip().splitlines() or ["(无输出)"])[-1])
        else:
            a = os.path.join(calc, "八字排盘.html")
            b = os.path.join(PROJ_DIR, "out", "八字排盘.html")
            if not os.path.exists(a):
                fails.append("解压包未产出 HTML")
            else:
                ha = hashlib.sha256(open(a, "rb").read()).hexdigest()
                hb = hashlib.sha256(open(b, "rb").read()).hexdigest()
                same = ha == hb
                print("出盘：%s（%d B）%s 成品" %
                      (os.path.basename(a), os.path.getsize(a), "＝" if same else "≠"))
                if not same:
                    fails.append("解压包产物与成品不一致（%s ≠ %s）" % (ha[:12], hb[:12]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for f in fails:
        print("  ✗ " + f)
    print("结果：%s" % ("全部通过" if not fails else "失败 %d 项" % len(fails)))
    return 0 if not fails else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="打包后解到临时目录实测")
    a = ap.parse_args()
    z = build(skill_version())
    if a.verify:
        sys.exit(verify(z))
