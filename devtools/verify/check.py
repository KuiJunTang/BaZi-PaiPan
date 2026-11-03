#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# —— devtools 引导：把技能包的 scripts 放进 import 路径（第一百一十令）——
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from paths import SKILL as SKILL_DIR, PROJ as PROJ_DIR  # noqa: E402
_sys.path.insert(0, _os.path.join(SKILL_DIR, "scripts"))
# —— 引导结束 ——

"""check.py —— 交付自检（拿数字说话，不报「基本没问题」）

静态：
 1. HTML 与 MD 同名成对在场
 2. 单文件零外部依赖（logo 为 data: 内联，外链只允许官网）
 3. 内联数据表齐备（节气 213 年 × 24、农历 600–2100 共 1501 年）
 4. BAZI_INIT 与 MD 初始命主一致（live 模式下不比对）；MD 含大运、流年两表
 5. 署名四要素、logo 与官网链接、无写死落款、字号全走 --u
 6. 录入面板：省市两级、无「历史」按钮
运行时（装了 Chrome 才跑）：
 7. 无头浏览器渲染后：四柱 8 字、大运 13 列、流年 1–10 列、起运块、面板在场
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FAIL = []
OKS = []
# 断言总数（唯一事实处）。增删断言必同步此数，并同步 HANDOFF「复跑」与六份文档里的项数写法；
# check_docs.py 直接读本常量比对，勿在文档里各写一套。包内 SKILL.md 不写项数——
# 它跑不了本脚本，写了就有「照跑必失败、遂自补假脚本」的空位（D107）。
CHECK_ITEMS = 56


def bad(msg):
    FAIL.append(msg)
    print("  ✗ " + msg)


def ok(msg):
    OKS.append(msg)
    print("  ✓ " + msg)


PROBE = """<script>
setTimeout(function(){
  function mid(e){var b=e.getBoundingClientRect();return Math.round(b.top+b.height/2);}
  function r(e){var b=e.getBoundingClientRect();return Math.round(b.right);}
  function box(e){var b=e.getBoundingClientRect();
    return {l:Math.round(b.left),r:Math.round(b.right),w:Math.round(b.width),h:Math.round(b.height)};}
  var ph=document.querySelector('.panel .ph'), lg=document.querySelector('.panel .ph .lg');
  var tt=document.querySelector('.panel .ph .tblock'), fo=document.getElementById('fold');
  var pan=document.getElementById('panel'), gz=document.querySelector('.gz');
  var cd=document.querySelector('.panel .card');
  var who=document.querySelector('.who'), head=document.querySelector('.head');
  var lab=document.querySelector('.sect .lab'), glbl=document.querySelector('.head .lbl');
  var R={hdr:{logo:mid(lg),ttl:mid(tt),fold:mid(fo),
             foldRight:r(fo),cardRight:cd?r(cd):0,
             panelRight:Math.round(pan.getBoundingClientRect().right)},
         gz: gz?Math.round(parseFloat(getComputedStyle(gz).fontSize)):0,
         who: who?box(who):null, head: head?box(head):null,
         sectLab: lab?Math.round(lab.getBoundingClientRect().width):0,
         gridLab: glbl?Math.round(glbl.getBoundingClientRect().width):0};
  document.title='GEO:'+JSON.stringify(R);
},400);
</script>"""


def geometry(html_path):
    """注入脚本量取顶栏几何，返回 {hdr:{...}, gz:字号}；取不到则 None。"""
    if not os.path.exists(CHROME):
        return None
    h = open(html_path, encoding="utf-8").read()
    tmp = html_path + ".geo.html"
    open(tmp, "w", encoding="utf-8").write(h.replace("</body>", PROBE + "</body>"))
    try:
        r = subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                            "--virtual-time-budget=3000", "--window-size=814,1200",
                            "--dump-dom", "file://" + os.path.abspath(tmp)],
                           capture_output=True, text=True, timeout=90)
        m = re.search(r"<title>GEO:(.*?)</title>", r.stdout, re.S)
        return json.loads(m.group(1)) if m else None
    except Exception:
        return None
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass



PROBE_LOGIC = """<script>
setTimeout(function(){
  var R = {};
  try {
    var B = window.Bazi;
    function ids(dt){ return B.paipan({birth:dt,gender:'male',now:new Date(Date.UTC(2026,10,2,12))})
      .pillars.map(function(p){ for(var i=0;i<60;i++) if(i%10===B.GAN.indexOf(p.gan)&&i%12===B.ZHI.indexOf(p.zhi)) return i; }); }
    function pil(dt){ return B.paipan({birth:dt,gender:'male',now:new Date(Date.UTC(2026,10,2,12))})
      .pillars.map(function(p){return p.gan+p.zhi;}).join(''); }
    // 交节落在时辰内：600-01-03 09:43，小寒 09:13（巳时之内）；立春前子时：2026-02-04 00:30
    var cases = [new Date(Date.UTC(600,0,3,9,43)), new Date(Date.UTC(2026,1,4,0,30))];
    R.rev = cases.map(function(dt){
      var want = pil(dt), hits = B.reverse(ids(dt), 600, 2100);
      var near = hits.some(function(h){ return Math.abs(h-dt)<=1.5*864e5 && pil(h)===want; });
      var wrong = hits.filter(function(h){ return pil(h)!==want; }).length;
      return {n:hits.length, near:near, wrong:wrong, want:want};
    });
    // 年号边界：判据在 eraOf 内（1950 起不得再有民国）
    R.era = {y1949: B.eraText(B.eraOf(1949)), y1950: B.eraOf(1950)===null, y581: B.eraText(B.eraOf(581))};
    // 换省须连真太阳时一并清（D100）：选市自动勾上，再换省不得留下「已勾但无经度」
    (function(){
      var C = window.BAZI_CITIES || [], pi = -1, ci = -1, i, j;
      for (i = 0; i < C.length; i++) if (C[i][0] === '山东省') {
        pi = i; for (j = 0; j < C[i][1].length; j++) if (C[i][1][j][0] === '青岛市') ci = j;
      }
      if (pi < 0 || ci < 0) { R.tst = {skip:true}; return; }
      var pv = document.getElementById('fProv'), ct = document.getElementById('fCity');
      function fire(el){ el.dispatchEvent(new Event('change', {bubbles:true})); }
      pv.value = String(pi); fire(pv);
      ct.value = String(ci); fire(ct);
      var on = document.getElementById('fTst').checked;
      var pi2 = -1; for (i = 0; i < C.length; i++) if (C[i][0] === '江苏省') pi2 = i;
      pv.value = String(pi2); fire(pv);
      R.tst = {on:on, lon:document.getElementById('fLon').value,
               still:document.getElementById('fTst').checked};
    })();
    // 藏干几何（第一百零九令）：藏干＋十神为一组，组中心须落在本列中轴；同列各行藏干须同一竖线
    R.cang = [].map.call(document.querySelectorAll('.cang .grid .c'), function(c){
      var cb = c.getBoundingClientRect(), rows = [].slice.call(c.querySelectorAll('.cg'));
      return {cx: cb.left + cb.width / 2,
              g: rows.map(function(g){
        // 取「字」左缘到「十神」右缘为组的内容范围（.cg 本身是整格宽，用它量不出偏移）
        var bb = g.querySelector('b').getBoundingClientRect();
        var ii = g.querySelector('i').getBoundingClientRect();
        return {c: (bb.left + ii.right) / 2, bc: bb.left + bb.width / 2};
      })};
    });
    // 录入区行几何（第一百零八令）：首控件须贴列左、末控件须贴行右、行内不得溢出
    R.rows = [].map.call(document.querySelectorAll('.srow .pmod'), function(m){
      var b = m.getBoundingClientRect();
      var ks = [].filter.call(m.children, function(e){ return e.getBoundingClientRect().width > 1; });
      var f = ks.length ? ks[0].getBoundingClientRect() : null;
      var l = ks.length ? ks[ks.length - 1].getBoundingClientRect() : null;
      return {l:Math.round(b.left), r:Math.round(b.right),
              fl:f ? Math.round(f.left) : null, lr:l ? Math.round(l.right) : null,
              sw:m.scrollWidth, cw:m.clientWidth};
    });
  } catch(e) { R.err = String(e); }
  document.title = 'LOGIC:' + JSON.stringify(R);
}, 500);
</script>"""


def probe_logic(html_path):
    """注入脚本跑反推与年号判据，返回 dict；取不到则 None。"""
    if not os.path.exists(CHROME):
        return None
    h = open(html_path, encoding="utf-8").read()
    tmp = html_path + ".logic.html"
    open(tmp, "w", encoding="utf-8").write(h.replace("</body>", PROBE_LOGIC + "</body>"))
    try:
        r = subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                            "--virtual-time-budget=6000", "--window-size=814,1200",
                            "--dump-dom", "file://" + os.path.abspath(tmp)],
                           capture_output=True, text=True, timeout=120)
        m = re.search(r"<title>LOGIC:(.*?)</title>", r.stdout, re.S)
        return json.loads(m.group(1)) if m else None
    except Exception:
        return None
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def runtime(html_path, pillars, live):
    if not os.path.exists(CHROME):
        print("  · 未装 Chrome，跳过运行时检查")
        return
    r = subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                        "--virtual-time-budget=4000", "--window-size=814,1600",
                        "--dump-dom", "file://" + os.path.abspath(html_path)],
                       capture_output=True, text=True, timeout=90)
    body = re.sub(r"<script[\s\S]*?</script>", "", r.stdout)
    text = re.sub(r"<[^>]+>", "", body).replace("\n", "")
    if "八字排盘" in text and "四柱十神" in text and "排盘" in text:
        ok("顶部标题区在场（标＋八字排盘＋副题）")
    else:
        bad("顶部标题区缺失")
    n_pmod = len(re.findall(r'class="pmod"', body))
    n_sel = len(re.findall(r'<select class="sel"', body))
    n_shead = len(re.findall(r'class="shead"', body))
    if n_pmod == 6 and n_sel == 7 and n_shead == 3 and 'class="card"' in body and 'goBtn' not in body:
        ok("录入卡三节各两行（3 节／%d 行）＋ %d 个下拉，无排盘按钮（自动重排）" % (n_pmod, n_sel))
    else:
        bad("录入区结构异常：节 %d／模块 %d 行（应 6）、下拉 %d 个、goBtn=%s"
            % (n_shead, n_pmod, n_sel, 'goBtn' in body))
    if 'id="wheel"' in body or 'id="wheelTog"' in body or 'id="fText"' in body:
        bad("仍残留滚轮／录入两种旧方式")
    else:
        ok("已去「录入」「微调」两种旧方式（第十七令）")
    geo = geometry(html_path)
    if geo:
        c = geo.get("hdr") or {}
        if c and abs(c["logo"] - c["ttl"]) <= 2 and abs(c["logo"] - c["fold"]) <= 2:
            ok("顶栏 logo／标题／折叠 三者垂直居中（中线 %s／%s／%s）"
               % (c["logo"], c["ttl"], c["fold"]))
        else:
            bad("顶栏未垂直居中：%s" % c)
        if c and c.get("cardRight") and abs(c["foldRight"] - c["cardRight"]) <= 2:
            ok("收起信息按钮右缘与卡片右缘对齐（%s 对 %s）" % (c["foldRight"], c["cardRight"]))
        else:
            bad("收起信息未与卡片对齐：%s 对 %s" % (c.get("foldRight") if c else "?",
                                                c.get("cardRight") if c else "?"))
        if re.search(r"\.srow\{[^}]*grid-template-columns:calc\(78 \* var\(--u\)\) minmax\(0, 1fr\)", body) \
                and ".panel.closed.pbody{display:none}" in re.sub(r"\s", "", body):
            ok("节标题留在左列（两列栅格，右列 minmax(0,1fr) 防窄屏撑宽）；收起信息收起全部内容")
        else:
            bad("节标题两列规则（或 minmax 防撑宽）／全收规则缺失")
        gz = geo.get("gz") or 0
        if gz and gz <= 42:
            ok("四柱大字已压缩到 %s px（原 50）" % gz)
        else:
            bad("四柱大字仍过大：%s px" % gz)
        w, hd = geo.get("who"), geo.get("head")
        if w and hd:
            if w["w"] < 700 and abs(w["l"] - hd["l"]) <= 1 and abs(w["r"] - hd["r"]) <= 1:
                ok("命盘整幅 %s px（列宽收拢），元信息行与表头左右齐（%s／%s）"
                   % (w["w"], w["l"], hd["l"]))
            else:
                bad("命盘幅宽／元信息行未对齐：who=%s head=%s" % (w, hd))
        else:
            bad("命盘元信息行或表头缺失")
        sl, gl = geo.get("sectLab") or 0, geo.get("gridLab") or 0
        if sl and gl and abs(sl - gl) <= 1:
            ok("大运／流年标签列与表格标签列同宽 %d px" % sl)
        else:
            bad("大运／流年标签列宽失配：%s 对 %s" % (sl, gl))
    if "起运：" in text and "人元司令" in text and "定位现在" in text:
        ok("起运交运块与「定位现在」在场")
    else:
        bad("起运交运块缺失")
    n_gz = len(re.findall(r'class="gz [^"]+"', body))
    if n_gz >= 8:
        ok("四柱干支 %d 字渲染在场" % n_gz)
    else:
        bad("四柱干支不足：%d 字" % n_gz)
    n_dy = len(re.findall(r'data-dy="\d+"', body))
    n_ln = len(re.findall(r'data-ln="\d+"', body))
    if n_dy == 13 and 1 <= n_ln <= 10:
        ok("大运 13 列（运前＋12 步）／流年 %d 列" % n_ln)
    else:
        bad("列数异常：大运 %d（应 13）／流年 %d（应 1–10）" % (n_dy, n_ln))
    if live:
        print("  · live 模式：页面按打开时刻排盘，不与 MD 四柱比对")
    else:
        miss = [p for p in pillars if p not in text]
        if miss:
            bad("渲染后正文缺四柱：%s" % miss)
        else:
            ok("渲染后正文四柱齐备：%s" % " ".join(pillars))


def main(argv):
    d = argv[1] if len(argv) > 1 else "./out"
    if not os.path.isdir(d):
        print("目录不存在：%s" % d)
        return 1
    pairs = [(os.path.join(d, f), os.path.join(d, f[:-5] + ".md"))
             for f in sorted(os.listdir(d)) if f.endswith(".html")]
    if not pairs:
        print("未找到 HTML 产物")
        return 1

    for html_p, md_p in pairs:
        print("\n[%s]" % os.path.basename(html_p))
        h = open(html_p, encoding="utf-8").read()
        if not os.path.exists(md_p):
            bad("缺同名 MD：%s" % md_p)
            continue
        m = open(md_p, encoding="utf-8").read()
        ok("HTML/MD 成对在场")
        if "<title>魁君堂·八字排盘</title>" in h:
            ok("页面标签恒为「魁君堂·八字排盘」")
        else:
            bad("页面标签不是「魁君堂·八字排盘」")

        res = []
        if re.search(r"<link\b", h):
            res.append("<link>")
        if re.search(r"<script[^>]+src=", h):
            res.append("<script src>")
        if re.search(r"@import", h):
            res.append("@import")
        # 外链网络字体（允许 data: 内联字体，仅禁止 http(s) 远程字体——独立运行硬禁忌）
        for ff in re.findall(r"@font-face\s*\{[^}]*\}", h, re.S):
            if re.search(r"url\((https?://[^)]+)\)", ff):
                res.append("外链字体@font-face")
        for tag in re.findall(r"<img\b[^>]*>", h):
            if 'src="data:' not in tag:
                res.append("外链图片")
        # 所有 http(s) URL（属性值或 JS 源码字符串），官网 a 链接与 SVG/XML 命名空间除外
        # （www.w3.org 是 xmlns 命名空间标识符，内嵌于 data: 内联 SVG，从不发起网络请求）
        for u in re.findall(r"""(?:src|href)=['"](https?://[^'"]+)['"]|['"](https?://[^'"]+)['"]""", h):
            _u = u[0] or u[1]
            if "kuijuntang.com" in _u or "www.w3.org" in _u:
                continue
            res.append("外链 " + _u)
        # 独立运行硬禁忌：运行时网络调用
        if re.search(r"\bfetch\s*\(", h) or re.search(r"XMLHttpRequest", h) \
                or re.search(r"new\s+WebSocket\s*\(", h):
            res.append("运行时网络调用(fetch/XHR/WS)")
        if res:
            bad("外部资源：%s" % "、".join(res))
        else:
            ok("单文件零外部依赖（%.1f KB）" % (len(h.encode()) / 1024))
        # 内核三块内联完整性保险：防止误把内联脚本改成外链导致独立运行失效
        if "BAZI_TABLES" in h and "BAZI_CITIES" in h and "autoChart" in h:
            ok("内核三块（data/cities/app）已内联，无外链脚本依赖")
        else:
            bad("内核块疑似未内联：缺 BAZI_TABLES/BAZI_CITIES/autoChart")
        if 'id="fLat"' in h and "sunRiseSetAST" in h and "hourBranchAncient" in h:
            ok("古法定时辰在场：纬度输入＋日出日落／昼夜弧划分")
        else:
            bad("古法定时辰要素缺失（fLat／sunRiseSetAST／hourBranchAncient）")
        if "♂" not in h and "♀" not in h:
            ok("性别按钮已去 ♂♀ 符号（连体分段控件）")
        else:
            bad("性别符号残留")
        _s = h.replace(" ", "")
        import math as _math
        # ===== 下拉防遮挡常设断言（八十八令 2026-11-01 定稿，此后每次审计必查）=====
        # D86 教训：旧估算框架 22u 偏小（实际=左pad7＋右pad20＋隙4=31u，右pad须让出箭头区
        # 8–18u），且最坏文案数错（fd 按 1 位数字、fh 漏 1 位、fCity 按 5 字而数据最长 11 字）
        # ——遮字三次复发皆源于估算失真。本断言一律按真实最坏文案＋31u 框架×1.12 复算。
        def _est_w(digits, cjk):  # 最坏文本宽（u）：数字/标点 0.62em、CJK 1em、字体回退 1.12
            return (digits * 0.62 + cjk * 1.0) * 16 * 1.12 + 31
        # 公历/农历取宽者：fy「2026年」 fm公历「11月」 fd公历「31日」
        # fh「23-子时」(3 个半角＋2 CJK) fmi「59分」 fProv「黑龙江省」 fCity「西双版纳」
        _sel_need = {"fy": _est_w(4, 1), "fm": _est_w(2, 1), "fd": _est_w(2, 1),
                     "fh": _est_w(3, 2), "fmi": _est_w(2, 1),
                     "fProv": _est_w(0, 4), "fCity": _est_w(0, 4)}
        _sel_bad = []
        for _k, _need in _sel_need.items():
            _m = re.search(r"#" + _k + r"[^{]*\{[^}]*width:calc\(([\d.]+)\*var\(--u\)\)", _s)
            if not _m or float(_m.group(1)) < _need:
                _sel_bad.append(_k)
        # 农历模式覆盖宽：fm「闰十一月」103 fd「二十一」85
        for _k, _need in (("fm", _est_w(0, 4)), ("fd", _est_w(0, 3))):
            _m = re.search(r"\.panel\.lunar#" + _k + r"\{width:calc\(([\d.]+)\*var\(--u\)\)", _s)
            if not _m or float(_m.group(1)) < _need:
                _sel_bad.append(_k + "(lunar)")
        if not _sel_bad:
            ok("下拉防遮挡常设断言：7 下拉×公历农历两模式宽度 ≥ 最坏文案×1.12＋31u 框架")
        else:
            bad("下拉宽度不足（会遮字）：%s" % "、".join(_sel_bad))
        # 右内边距必须让出箭头区（箭头占右 8–18u）：select.sel 右 pad ≥18u
        # padding 简写首值即右 pad（0 20u 0 7u＝上0 右20 下0 左7）
        _msel = re.search(r"select\.sel\{[^}]*padding:0calc\(([\d.]+)\*var\(--u\)\)0calc\(([\d.]+)\*var\(--u\)\)", _s)
        if _msel and float(_msel.group(1)) >= 18:
            ok("select.sel 右内边距 %su ≥ 箭头区 18u（文字永不进入箭头区）" % _msel.group(1))
        else:
            bad("select.sel 右内边距不足 18u（文字会压到箭头）：%s" % (_msel.groups() if _msel else None))
        # 东经／北纬输入框：占位「东经 120.38」(2 CJK＋空格＋5 数字＋点) 需 ≥115u，且两框同宽
        # 第一百零四令起，经纬两框不再各定宽，而是同一条规则 flex:1 1 0 等分右列：
        # 右列宽 ＝ 卡内宽 704u（724u − 卡内边 20u）− 标题列 78u − 列隙 4u ＝ 622u；
        # 减去两处 10u 行隙与「真太阳时」标签（复选框 16u＋隙 6u＋4 个汉字 64u）后两框均分。
        _inp_need = (2 * 1.0 + 0.28 + 5 * 0.62 + 0.27) * 16 * 1.12 + 14
        _mrule = re.search(r"\.pmod\.ipt\.lon,\.pmod\.ipt\.lat\{([^}]*)\}", _s)
        _each = 0.0
        if _mrule and "flex:110" in _mrule.group(1).replace(" ", ""):
            _each = (622 - 20 - 86) / 2.0
        if _each >= _inp_need:
            ok("经纬两框同一条规则等分右列（各约 %.0fu）≥ 占位文案需求 %.1fu" % (_each, _inp_need))
        else:
            bad("经纬两框非等分或右列容不下占位文案：规则=%s 各约 %.1fu（需 ≥%.1f）"
                % (_mrule.group(1) if _mrule else None, _each, _inp_need))
        # 长州郡名展示端缩短：app.js shortCity 与 Python 同规则复算 348 市，缩短后 ≤4 字
        def _short_city(n):
            n = re.sub(r"(自治州|地区|盟|市)$", "", n)
            _prev = None
            while _prev != n:
                _prev = n
                n = re.sub(r"(蒙古族?|藏族?|回族?|彝族?|白族?|傣族?|苗族?|侗族?|壮族?|土家族?|"
                           r"朝鲜族?|哈萨克族?|哈尼族?|傈僳族?|景颇族?|布依族?|柯尔克孜|仡佬族?|羌族?|维吾尔族?)$",
                           "", n)
            return n
        if "function shortCity" in h:
            _cities_src = open(os.path.join(SKILL_DIR, "assets", "cities.js"), encoding="utf-8").read()
            _cnames = re.findall(r"\['([^']+)',\s*-?\d{1,3}\.\d+,\s*-?\d{1,3}\.\d+\]", _cities_src)
            _over = [c for c in _cnames if len(_short_city(c)) > 4]
            if not _over:
                ok("长州郡名展示端缩短（shortCity）：%d 市复算缩短后全部 ≤4 字" % len(_cnames))
            else:
                bad("shortCity 后仍有 >4 字市名：%s" % _over[:3])
        else:
            bad("app.js 缺 shortCity（长市名会顶出下拉框宽）")

        if ".who.kv.tst{margin-left:auto;min-width:calc(114*var(--u))" in _s:
            ok("命盘两处真太阳时同宽挂右（真字左缘垂直对齐）")
        else:
            bad("真太阳时对齐样式缺失")
        _pm = _s.split(".srow.pmod{")[1].split("}")[0] if ".srow.pmod{" in _s else ""
        if "@media(max-width:620px)" not in _s and "flex-wrap:wrap" not in _pm \
                and "width:100%" in _pm and "#fy{width:calc(94*var(--u))" in _s \
                and "#fProv,#fCity{flex:110;width:calc(103*var(--u))" in _s:
            ok("三节各两行、右列两行同宽吃满（基准宽＋flex 分摊，无换行兜底）")
        else:
            bad("两行制式断言未过（右列未吃满／媒体换行残留）")

        mj = re.search(r'"jq":\{"y0":(\d+),"y1":(\d+),"s":"([0-9a-z]+)"\}', h)
        ml = re.search(r'"ln":\{"y0":(\d+),"y1":(\d+),"base":\d+,"s":"([0-9a-z]+)"\}', h)
        if mj and ml and len(mj.group(3)) % 96 == 0 and len(ml.group(3)) % 15 == 0:
            ok("节气表 %s–%s 共 %d 年；农历表 %s–%s 共 %d 年"
               % (mj.group(1), mj.group(2), len(mj.group(3)) // 96,
                  ml.group(1), ml.group(2), len(ml.group(3)) // 15))
        else:
            bad("数据表缺失或长度异常")

        mi = re.search(r"window\.BAZI_INIT=(\{.*?\});</script>", h, re.S)
        if not mi:
            bad("缺 BAZI_INIT")
            continue
        init = json.loads(mi.group(1))
        live = bool(init.get("live"))
        ps = re.search(r"# 八字排盘 · (\S+) (\S+) (\S+) (\S+)", m)
        if not ps:
            bad("MD 缺四柱标题")
            continue
        pillars = list(ps.groups())
        b = init["birth"]
        if live:
            ok("BAZI_INIT 为 live（页面取打开时刻）；MD 记录 %04d-%02d-%02d %02d:%02d"
               % tuple(b))
        elif ("%d年%d月%d日" % (b[0], b[1], b[2])) in m:
            ok("初始命主与 MD 一致：%04d-%02d-%02d %02d:%02d" % tuple(b))
        else:
            bad("初始命主与 MD 不符")
        if re.search(r"^## 大运$", m, re.M) and re.search(r"^## 流年", m, re.M):
            ok("MD 含大运、流年两表")
        else:
            bad("MD 缺大运或流年表")

        need_txt = ["膠東魁君堂", "復城道長", "制作", "魁君堂官网：", "18550386868"]
        lack = [t for t in need_txt if t not in h or t not in m]
        if lack:
            bad("署名/品牌缺项：%s" % lack)
        else:
            ok("署名与品牌四要素齐备")

        if re.search(r'class="brand"[^>]*href="https://www\.kuijuntang\.com"', h) or \
           re.search(r'href="https://www\.kuijuntang\.com"[^>]*class="brand"', h):
            if re.search(r'class="brand"[\s\S]{0,400}?src="data:image/png;base64,[A-Za-z0-9+/=]{200,}"', h):
                ok("底部魁君堂标已内联，且点击进官网")
            else:
                bad("logo 图片未内联或过小")
        else:
            bad("底部缺 logo 或未加官网链接")

        if "histBtn" in h or "历史" in re.sub(r"<script[\s\S]*?</script>", "", h):
            bad("仍存在「历史」入口")
        else:
            ok("无「历史」入口（第九令已去）")
        if 'id="fProv"' in h and 'id="fCity"' in h:
            n_city = len(re.findall(r"\[['\"][^'\"]{2,20}['\"],\s*\d{2,3}\.\d+", h))
            if n_city > 300:
                ok("省市两级选择：地级行政区 %d 个" % n_city)
            else:
                bad("城市数据不足：%d 个" % n_city)
        else:
            bad("省市两级选择缺失")
        body_h = re.sub(r"<script[\s\S]*?</script>", "", h)
        # 落款：整块居中，标—署名—三模块联系方式（第十五令）
        n_m = len(re.findall(r'class="m"', body_h))
        has_brand = bool(re.search(r'class="fl">[\s\S]{0,900}?class="brand"', body_h))
        has_sign = 'class="l1"' in body_h
        if has_brand and has_sign and n_m == 3:
            ok("落款居中三模块：标＋署名＋联系方式 %d 项" % n_m)
        else:
            bad("落款结构异常（标%d 署名%d 模块%d）" % (has_brand, has_sign, n_m))
        if re.search(r'\.foot\{[^}]*flex-direction:column', h) and \
           re.search(r'\.foot\{[^}]*align-items:center', h) and \
           re.search(r'\.foot\{[^}]*text-align:center', h):
            ok("落款整块居中（column／align-items:center／text-align:center）")
        else:
            bad("落款未整块居中")
        if '<hr class="fline">' in body_h and re.search(r'\.foot \.fline\{[^}]*border-top:1px solid', h):
            ok("logo 上方分割线在场（与命盘同宽）")
        else:
            bad("logo 上方缺分割线")
        if "calc((100vw - var(--sbw, 0px)) / 772)" in h and "setProperty('--sbw'" in h:
            ok("滚动条占宽补偿在场（--u 扣减 --sbw，防整页横滚）")
        else:
            bad("缺滚动条占宽补偿（100vw 含滚动条会横滚）")
        n_srow = len(re.findall(r'class="srow[ "]', body_h))
        n_two = len(re.findall(r'class="pmod"', body_h))
        if n_srow == 3 and n_two == 6 and "grid-row:1 / span 2" in h.replace("  ", " ") \
           and ".srow.hasrev .shead{grid-row:1 / span 3}" in h:
            ok("录入卡三节、每节两行（srow %d／pmod %d）；节标题跨两行纵向居中，反推展开时跨三行（srow %d）"
               % (n_srow, n_two, n_srow))
        else:
            bad("节／行排布异常：srow %d／pmod %d／跨行居中规则=%s"
                % (n_srow, n_two, "grid-row:1 / span 2" in h))
        # 一百零八令：行自列左起排、控件吃满到右缘——整组右推会左留白，定宽会右留白，
        # 两者都属「无端空白」；px 最小宽度在小 --u 下不缩，会把行顶出右列压住节标题。
        _pmod = h.split(".srow .pmod{")[1].split("}")[0].replace(" ", "") if ".srow .pmod{" in h else ""
        _fg = h.split(".pmod .fg{")[1].split("}")[0].replace(" ", "") if ".pmod .fg{" in h else ""
        _tg = h.split(".pmod .tg{")[1].split("}")[0].replace(" ", "") if ".pmod .tg{" in h else ""
        _seg2 = h.split(".pmod .seg{")[1].split("}")[0].replace(" ", "") if ".pmod .seg{" in h else ""
        _px = re.findall(r"#f(?:y|m|d|h|mi|Prov|City)[^{]*\{[^}]*min-width:(\d+)px", h)
        if "width:100%" in _pmod and "justify-content:flex-start" in _pmod \
                and "justify-content:flex-start" in _fg \
                and "flex:11auto" in _tg and "flex:11auto" in _seg2:
            ok("行自列左起排、控件吃满右缘（.pmod／.fg 均 flex-start；历法切换与性别段 flex:1 吃满）")
        else:
            bad("行排布断言未过（flex-start／tg·seg 吃满缺失）")
        if _px:
            bad("下拉仍留 px 最小宽度 %s（小 --u 下不缩，会把整行顶出右列压住节标题）" % _px[:4])
        else:
            ok("七组下拉无 px 最小宽度（字随 u 等比缩，行不越界）")
        f_l1 = h.split(".foot .l1{")[1].split("}")[0] if ".foot .l1{" in h else ""
        f_m = h.split(".foot .fr .m i{")[1].split("}")[0] if ".foot .fr .m i{" in h else ""
        if "color:#000" in f_l1 and "color:#000" in f_m:
            ok("落款文字纯黑（署名／标签／值）")
        else:
            bad("落款文字未全黑：l1=%r m-i=%r" % (f_l1, f_m))
        if "space-between" in h.split(".foot{")[1].split("}")[0] or "text-align:right" in h.split(".foot{")[1].split("}")[0]:
            bad("落款仍为左右分置")
        else:
            ok("已去左右分置（无 space-between／右对齐）")
        if 'class="wheel' in h.split("<body>")[1].split("</body>")[0]:
            bad("页面仍含滚轮区")
        else:
            ok("命盘无滚轮区（第十七令已去）")
        if "丙午年" in h or "丙午年" in m:
            bad("出现写死落款「丙午年」")
        else:
            ok("无写死落款")

        # ===== 交互一致性常设断言（D88，2026-11-02 审计）=====
        # 教训：控件状态与实际计算静默不一致——农历越界弹回无提示（fBirth 已撤销）、
        # 换省/取消选市后 S.lon 残留旧省经度（真太阳时算错）、勾真太阳时无经度静默按平太阳时。
        # 一律要求「有可见反馈 + 状态彻底清空」，此后每次审计必查。
        _d88 = []
        if "function toast(" not in h:
            _d88.append("缺 toast 提示函数")
        if "农历表仅 1900–2100 年可用" not in h:
            _d88.append("农历越界无提示文案")
        if not re.search(r"q\('fProv'\)\.onchange[\s\S]{0,240}S\.lon\s*=\s*null", h):
            _d88.append("换省未清 S.lon")
        if not re.search(r"q\('fCity'\)\.onchange[\s\S]{0,240}S\.lon\s*=\s*null", h):
            _d88.append("取消选市未清 S.lon")
        if not re.search(r"if\s*\(S\.tst\s*&&\s*S\.lon\s*===\s*null\)\s*toast\(", h):
            _d88.append("真太阳时缺经度无提示")
        # toast 必须单例（D93）：连续触发不得叠出多层同位置浮条
        if "var toastEl = null" not in h or "if (!toastEl) {" not in h:
            _d88.append("toast 未单例化（连续触发会叠层）")
        if not _d88:
            ok("交互一致性：农历越界/真太阳时缺经度有 toast；换省与取消选市清空 S.lon")
        else:
            bad("交互一致性缺陷（D88）：%s" % "、".join(_d88))

        # ===== 流年年号纪年常设断言（D90，2026-11-02 九十四令）=====
        # 建国前（<1949）点选流年时，交运行中部显示该年年号纪年（民国十三年／隋·开皇二十年），
        # 便于与原历核对。要求：显示位在交运行内、年号复用 eraText、1949 起不显示、
        # 样式与交运同行同字号（仅整行中线居中与省略，不得另设字号或颜色）。
        _d90 = []
        if 'id="lnEra"' not in h:
            _d90.append("交运行缺年号显示位 lnEra")
        if "function paintEra(" not in h:
            _d90.append("缺 paintEra")
        # 口径须与元信息行一致（cyear>=1912 && cyear<=1949）：<＝1949 含民国三十八年（D92）
        if not re.search(r"y\s*<=\s*1949", h.replace("\u00a0", " ")):
            _d90.append("未按 1949（含）分界，与元信息行口径不一致")
        if not re.search(r"el\.textContent\s*=\s*e\s*\?\s*eraText\(e\)", h.replace("\u00a0", " ")):
            _d90.append("年号未复用 eraText（恐与元信息行不一致）")
        if h.count("paintEra()") < 3:
            _d90.append("paintEra 未在渲染/点选/定位现在三处调用")
        _mcss = re.search(r"\.qy\s+\.ln-era\{([^}]*)\}", h)
        if not _mcss:
            _d90.append("缺 .ln-era 样式")
        else:
            _c = _mcss.group(1).replace(" ", "")
            # 九十五令：须以**整行中线**绝对居中（按剩余余白居中会偏右，道长已指正）
            if ("position:absolute" not in _c or "left:50%" not in _c
                    or "translate(-50%" not in _c):
                _d90.append(".ln-era 未按整行中线居中（position:absolute/left:50%/translate）")
            if "position:relative" not in re.search(r"\.qy\s+\.r\{([^}]*)\}", h).group(1).replace(" ", ""):
                _d90.append(".qy .r 缺 position:relative（年号无定位参照）")
            if "font-size" in _c or "color:" in _c:
                _d90.append(".ln-era 自设字号或颜色（应随交运行）")
        if ".qy .ln-era:empty{display:none}" not in h.replace("  ", " "):
            _d90.append("空年号未隐藏（1949 后会留空位）")
        # ===== 姓名溢出常设断言（D94，2026-11-02 审计）=====
        # 左列（labw≈58px）仅容 4 字；实测 5 字即压「公历」，6 字重叠 12px、14 字重叠 66px。
        # 要求：姓名限宽省略并挂 title 存全名，字距收至 .6u 保证复姓双名（4 字）完整。
        _d94 = []
        _mnm = re.search(r"\.who\s+\.nm\{([^}]*)\}", h)
        if not _mnm:
            _d94.append("缺 .who .nm 样式")
        else:
            _c = _mnm.group(1).replace(" ", "")
            for _k in ("max-width:100%", "overflow:hidden", "text-overflow:ellipsis"):
                if _k not in _c:
                    _d94.append(".nm 缺 %s（长姓名会压住公历）" % _k)
        if not re.search(r'class="nm"\s+title=', h):
            _d94.append("姓名缺 title（省略后无法查看全名）")
        if not _d94:
            ok("姓名溢出防护：限宽省略＋title 全名，4 字以内不省略")
        else:
            bad("姓名溢出缺陷（D94）：%s" % "、".join(_d94))

        # ===== 打印／导出 PDF 安全常设断言（D95，2026-11-02 九十七令）=====
        # 教训：-webkit-mask-image 用于横条渐隐，导出／打印 PDF 时被 Chrome 渲染成实心黑块
        # （大运 13 列必溢出必中招，流年不溢出故正常）。渐隐一律改用绝对定位伪元素实现。
        _d95 = []
        _maskdecl = re.findall(r"[-\w]*mask-image\s*:", h)
        if _maskdecl:
            _d95.append("存在 mask-image 声明（导出 PDF 会渲染成黑块）：%s" % len(_maskdecl))
        if ".sect .wrap2::after" not in h.replace("  ", " "):
            _d95.append("缺 .wrap2 渐隐伪元素")
        if not re.search(r"\.sect\s+\.wrap2::after\{[^}]*linear-gradient", h.replace("\n", " ")):
            _d95.append("渐隐未用 linear-gradient 实现")
        if not re.search(r"@media print\{[\s\S]{0,600}\.sect \.wrap2::after\{display:none\}", h):
            _d95.append("打印时未隐藏渐隐伪元素")
        if not re.search(r"w2\.classList\.toggle\('more'", h):
            _d95.append("JS 未同步 wrap2 的 more 标记（渐隐不生效）")
        if not _d95:
            ok("打印安全：无 mask-image（PDF 不出黑块），渐隐用伪元素且打印隐藏")
        else:
            bad("打印安全缺陷（D95）：%s" % "、".join(_d95))

        # ===== 藏干十神口径（D96，2026-11-02 九十八令独立复核）=====
        # 教训：Python 端曾把日柱藏干中与日干相同的藏干标成「日主」，而简称却取 ten_god 得「比」，
        # 数据与显示自相矛盾（JS 端本正确）。「日主」只属于日柱天干的主星。
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import datetime as _dt
            import bazi_core as _bc
            _probe = None
            for _cand in (_dt.datetime(1991, 10, 18, 2, 29), _dt.datetime(1984, 2, 4, 23, 0),
                          _dt.datetime(2026, 11, 2, 22, 49)):
                _d = _bc.paipan(_cand)
                if any(c['gan'] == _d['pillars'][2]['gan']
                       for c in _d['pillars'][2]['cang']):
                    _probe = _d
                    break
            if _probe is None:
                bad("藏干十神检查找不到「日柱藏干含日干」的样本（请更新样本日期）")
            else:
                _wrong = [c for p in _probe['pillars'] for c in p['cang']
                          if c['god'] == '日主']
                _dm = _probe['pillars'][2]['gan']
                _mismatch = [c for p in _probe['pillars'] for c in p['cang']
                             if c['god'] != _bc.ten_god(_dm, c['gan'])]
                if _wrong:
                    bad("藏干十神误标「日主」（D96）：%s%s" % (_wrong[0]['gan'], _wrong[0]['god']))
                elif _mismatch:
                    bad("藏干十神与 ten_god 不一致：%s" % _mismatch[0]['gan'])
                else:
                    ok("藏干十神口径：同干取比肩（无误标「日主」），与 ten_god 全一致")
        except Exception as _e:
            bad("藏干十神检查无法执行：%r" % _e)

        if not _d90:
            ok("流年年号纪年：交运行内整行中线居中、≤1949 才显（与元信息行同口径）、复用 eraText、样式随交运")
        else:
            bad("流年年号纪年缺陷（D90）：%s" % "、".join(_d90))

        hard = re.findall(r"(?<!var\(--u\))(?<![\w-])font-size:\s*\d+px", h)
        if hard:
            bad("存在硬写字号：%s" % hard[:5])
        else:
            ok("字号全部走 --u 缩放")

        lg = probe_logic(html_p) if os.path.exists(CHROME) else "skip"
        if lg == "skip":
            print("  · 未装 Chrome，跳过反推／年号判据探针")
        elif not lg:
            bad("反推／年号判据探针未取到结果（CHROME 注入失败）")
        elif lg.get("err"):
            bad("反推探针异常：%s" % lg["err"])
        else:
            rev = lg.get("rev") or []
            if (len(rev) == 2 and all(r["near"] and r["wrong"] == 0 and r["n"] > 0 for r in rev)):
                ok("反推按候选时刻判年／月柱：交节落时辰内（600-01-03 巳时）与立春前子时两例均命中，候选四柱全自洽")
            else:
                bad("反推漏解或候选不符：%s" % rev)
            e = lg.get("era") or {}
            if e.get("y1949") == "民国三十八年" and e.get("y1950") is True and e.get("y581") == "隋·开皇元年":
                ok("年号边界收在 eraOf 内：1949＝民国三十八年、1950 起为空、581＝隋·开皇元年")
            else:
                bad("年号边界异常：%s" % e)
            cg = lg.get("cang") or []
            dev = [round(g["c"] - c["cx"], 1) for c in cg for g in c["g"]]
            if cg and all(abs(d) <= 1 for d in dev):
                ok("藏干整组居中：%d 组「藏干＋十神」中心与本列中轴偏差 ≤1px（最大 %.1f）"
                   % (len(dev), max(abs(d) for d in dev)))
            else:
                bad("藏干组未与本列中轴对齐：%s" % dev[:8])
            line_ok = True
            for c in cg:
                xs = [g["bc"] for g in c["g"]]
                if xs and max(xs) - min(xs) > 1:
                    line_ok = False
            if cg and line_ok:
                ok("同列各行藏干同处一竖线（不一左一右）")
            else:
                bad("同列藏干未对齐成一竖线")
            rg = lg.get("rows") or []
            if len(rg) == 6 and all(r["fl"] is not None and abs(r["fl"] - r["l"]) <= 1
                                    and abs(r["lr"] - r["r"]) <= 1 for r in rg):
                ok("六行首尾贴齐：首控件左缘＝列左缘、末控件右缘＝行右缘（无左留白、无右留白）")
            else:
                bad("行首尾未贴齐（留白或错位）：%s" % rg)
            if rg and all(r["sw"] - r["cw"] <= 1 for r in rg):
                ok("六行均无内部溢出（内容不被挤出行框）")
            else:
                bad("行内溢出（内容被挤出右列，会压住节标题）：%s"
                    % [(r["sw"] - r["cw"]) for r in rg])
            t = lg.get("tst") or {}
            if t.get("skip"):
                bad("换省探针取不到省市数据")
            elif t.get("on") is True and t.get("lon") == "" and t.get("still") is False:
                ok("换省 → 经纬清空的同时取消真太阳时（不留「已勾但无经度」的静默失效）")
            else:
                bad("换省后真太阳时状态异常：%s" % t)

        runtime(html_p, pillars, live)

    # 断言数自洽：装了 Chrome 就应为声明的 CHECK_ITEMS（未装则运行时项跳过，仅提示）
    if os.path.exists(CHROME) and len(OKS) != CHECK_ITEMS:
        bad("断言数 %d 与声明 CHECK_ITEMS=%d 不符（文档同值会失真，改断言须同步此数）"
            % (len(OKS), CHECK_ITEMS))
    print("\n结果：%s（通过 %d 项）" % ("全部通过" if not FAIL else "失败 %d 项" % len(FAIL), len(OKS)))
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
