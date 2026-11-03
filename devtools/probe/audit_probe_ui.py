#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# —— devtools 引导：把技能包的 scripts 放进 import 路径（第一百一十令）——
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from paths import SKILL as SKILL_DIR, PROJ as PROJ_DIR  # noqa: E402
_sys.path.insert(0, _os.path.join(SKILL_DIR, "scripts"))
# —— 引导结束 ——

"""audit_probe_ui.py —— 界面与打印主动探针（第一百零三令）

撞的是**交互与排版**，现有 check.py 只做静态结构与几处几何：
  A. 交互（814px）：农历越界提示、换省清经纬、选市填经纬并勾真太阳时、
     折叠／展开、大运点选联动、定位现在、反推全流程、长姓名不压字、toast 单例
  B. 窄屏（320px）：7 个下拉是否遮字（按最长选项真实文字宽度比可用宽度）、
     同一行元素是否重叠、整页是否横向溢出
  C. 打印：真实 print-to-pdf → 转 PNG → 扫描「大面积实心黑条」（D95 黑块特征）

用法：python3 scripts/audit_probe_ui.py <html 路径>
退出码：0 全过；1 有问题项
"""
import json
import os
import re
import subprocess
import sys
import urllib.parse
import tempfile

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FAIL = []
N = 0


def ok(m):
    global N
    N += 1
    print("  ✓ " + m)


def bad(m):
    FAIL.append(m)
    print("  ✗ " + m)


def run_page(html, js, width=814, height=1200, budget=5000):
    """注入 js（末尾须写 document.title='UI:'+JSON），返回解析后的 dict。"""
    h = open(html, encoding="utf-8").read()
    tmp = html + ".uiprobe.html"
    open(tmp, "w", encoding="utf-8").write(h.replace("</body>", "<script>" + js + "</script></body>"))
    try:
        r = subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                            "--virtual-time-budget=%d" % budget,
                            "--window-size=%d,%d" % (width, height),
                            "--dump-dom", "file://" + os.path.abspath(tmp)],
                           capture_output=True, text=True, timeout=180)
        m = re.search(r"<title>UI:(.*?)</title>", r.stdout, re.S)
        return json.loads(m.group(1)) if m else None
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


# ---------------------------------------------------------------- 真窄屏运行器
# macOS 无头 Chrome 的窗口有最小宽度（实测 500px），--window-size=320 会被夹到 500，
# 过去的「320px 测试」其实跑在 500px 上，等于没测（第一百零八令发现）。
# 改用 iframe 固定宽 320：iframe 内视口即 320，才量得到真窄屏（配合 --allow-file-access-from-files）。
NARROW_WRAP = """<html><head><meta charset="utf-8"></head><body style="margin:0;background:#ddd">
<iframe id="f" src="%s" style="width:%dpx;height:1800px;border:0"></iframe>
<script>
var F = document.getElementById('f');
function inject(){
  var d = null, w = null;
  try { d = F.contentDocument; w = F.contentWindow; } catch (e) {}
  if (!d || !d.querySelector('.srow')) { return setTimeout(inject, 200); }
  var s = d.createElement('script');
  s.textContent = %s;
  d.body.appendChild(s);
}
setTimeout(inject, 600);
(function poll(n){
  var R = null;
  try { R = F.contentWindow.__R; }
  catch (e) { document.title = 'UI:' + JSON.stringify({err: String(e)}); return; }
  if (R) { document.title = 'UI:' + JSON.stringify(R); return; }
  if (n <= 0) { document.title = 'UI:' + JSON.stringify({err: 'iframe 内测量超时'}); return; }
  setTimeout(function(){ poll(n - 1); }, 200);
})(30);
</script></body></html>"""


def run_narrow(html_path, width=320, budget=8000):
    """在 width 宽的 iframe 里跑 NARROW_JS，返回 dict；取不到则 None。"""
    inner = NARROW_JS.replace("document.title = 'UI:' + JSON.stringify(R);", "window.__R = R;")
    src = "file://" + urllib.parse.quote(os.path.abspath(html_path))
    tmp = html_path + ".narrow.html"
    open(tmp, "w", encoding="utf-8").write(NARROW_WRAP % (src, width, json.dumps(inner)))
    try:
        r = subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                            "--allow-file-access-from-files",
                            "--virtual-time-budget=%d" % budget,
                            "--window-size=900,1800", "--dump-dom", "file://" + os.path.abspath(tmp)],
                           capture_output=True, text=True, timeout=180)
        m = re.search(r"<title>UI:(.*?)</title>", r.stdout, re.S)
        return json.loads(m.group(1)) if m else None
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


# ---------------------------------------------------------------- A 交互
UI_JS = r"""
setTimeout(function(){
  var R = {err:null}, B = window.Bazi, q = function(id){ return document.getElementById(id); };
  function fire(el, type){ el.dispatchEvent(new Event(type, {bubbles:true})); }
  try {
    // 固定生辰，避免「打开即此刻」影响
    B.state.base = new Date(Date.UTC(1991,4,18,19,0));
    B.state.gender = 'male'; B.state.name = '';
    B.doChart();

    // ① 农历越界：1899 年点「农历」→ 提示并回退公历
    B.state.base = new Date(Date.UTC(1899,4,18,19,0)); B.doChart();
    q('tab-lunar').click();
    var ts = document.querySelector('.toast');
    R.lunar = { toast: ts ? ts.textContent : '', active: q('tab-solar').className };
    B.state.base = new Date(Date.UTC(1991,4,18,19,0)); B.doChart();

    // ② 选市 → 经纬与真太阳时自动填
    var pv = q('fProv'), ct = q('fCity');
    function pick(el, txt){ for (var i=0;i<el.options.length;i++) {
        var t = el.options[i].text;
        if (t === txt || t === txt.replace(/市$/, '') || txt.indexOf(t) === 0) return el.options[i].value;
      } return null; }
    pv.value = pick(pv, '山东省'); fire(pv, 'change');
    ct.value = pick(ct, '青岛市'); fire(ct, 'change');
    R.city = { lon: q('fLon').value, lat: q('fLat') ? q('fLat').value : '', tst: q('fTst').checked };

    // ③ 换省是否清经纬（D88 复发位：勾选状态是否跟着清）
    pv.value = pick(pv, '江苏省'); fire(pv, 'change');
    R.provSwitch = { lon: q('fLon').value, lat: q('fLat') ? q('fLat').value : '',
                     tst: q('fTst').checked, tstState: !!B.state.tst, place: B.state.placeName };

    // ④ 折叠／展开
    q('fold').click(); var c1 = q('panel').className, t1 = q('fold').querySelector('.ft').textContent;
    q('fold').click(); var c2 = q('panel').className, t2 = q('fold').querySelector('.ft').textContent;
    R.fold = { closed: /closed/.test(c1), txt1: t1, open: !/closed/.test(c2), txt2: t2 };

    // ⑤ 大运点选联动（主盘大运列与流年首年都要变）
    B.state.base = new Date(Date.UTC(1991,4,18,19,0)); B.doChart();
    var dy0 = q('gz-dy').textContent, ln0 = (document.querySelector('[data-ln="0"] .yr') || {}).textContent;
    var cols = document.querySelectorAll('[data-dy]');
    function tap(el){
      var b = el.getBoundingClientRect(), x = b.left + b.width/2, y = b.top + b.height/2;
      el.dispatchEvent(new PointerEvent('pointerdown', {bubbles:true, clientX:x, clientY:y}));
      window.dispatchEvent(new PointerEvent('pointerup', {bubbles:true, clientX:x, clientY:y}));
    }
    if (cols.length > 6) tap(cols[6]);
    R.pick = { dyBefore: dy0, dyAfter: q('gz-dy').textContent,
               lnBefore: ln0, lnAfter: (document.querySelector('[data-ln="0"] .yr') || {}).textContent,
               onIdx: (function(){ var e=document.querySelector('[data-dy].on'); return e?e.getAttribute('data-dy'):null; })() };

    // ⑥ 定位现在
    var loc = q('locate'); if (loc) loc.click();
    R.locate = { onIdx: (function(){ var e=document.querySelector('[data-dy].on'); return e?e.getAttribute('data-dy'):null; })() };

    // ⑦ 反推全流程：用当前盘四柱反推，再点第一个候选
    q('tab-rev').click();
    var pil = B.chart.d.pillars;
    ['rvY','rvM','rvD','rvH'].forEach(function(pre, i){
      var g = q(pre+'g'), z = q(pre+'z');
      g.value = String(B.GAN.indexOf(pil[i].gan)); z.value = String(B.ZHI.indexOf(pil[i].zhi));
    });
    q('revGo').click();
    var btns = q('revHits').querySelectorAll('button');
    R.rev = { n: btns.length, first: btns.length ? btns[0].textContent : '' };
    if (btns.length) {
      var want = pil.map(function(p){ return p.gan + p.zhi; }).join('');
      btns[0].click();
      R.rev.after = B.chart.d.pillars.map(function(p){ return p.gan+p.zhi; }).join('');
      R.rev.want = want;
    }

    // ⑧ 长姓名 24 字：不得压住「公历」
    q('tab-solar').click();
    q('fName').value = '一二三四五六七八九十一二三四五六七八九十一二三四';
    fire(q('fName'), 'input');
    setTimeout(function(){
      var nm = document.querySelector('.who .nm'), wv = document.querySelector('.who .r1');
      var a = nm.getBoundingClientRect(), b = wv.getBoundingClientRect();
      R.name = { gap: Math.round(b.left - a.right), clipped: nm.scrollWidth > nm.clientWidth + 1,
                 title: nm.getAttribute('title') || '' };

      // ⑨ toast 单例：连点两次越界
      B.state.base = new Date(Date.UTC(1899,4,18,19,0)); B.doChart();
      q('tab-lunar').click(); q('tab-lunar').click();
      R.toast = { n: document.querySelectorAll('.toast').length };
      B.state.base = new Date(Date.UTC(1991,4,18,19,0)); B.doChart();
      document.title = 'UI:' + JSON.stringify(R);
    }, 260);
  } catch (e) { R.err = String(e && e.stack || e); document.title = 'UI:' + JSON.stringify(R); }
}, 600);
"""


def probe_ui(html):
    print("\n[A] 交互（814px，真事件驱动）")
    r = run_page(html, UI_JS)
    if not r:
        bad("交互探针未取到结果")
        return
    if r.get("err"):
        bad("交互探针异常：%s" % r["err"].splitlines()[0])
        return

    lr = r.get("lunar") or {}
    if "农历表仅 1900–2100" in (lr.get("toast") or "") and "on" in (lr.get("active") or ""):
        ok("1899 年点「农历」→ 明确提示「农历表仅 1900–2100 年可用」并回退公历")
    else:
        bad("农历越界未提示或未回退：%s" % lr)

    c = r.get("city") or {}
    if c.get("lon") and c.get("lat") and c.get("tst") is True:
        ok("选「山东省·青岛市」→ 经度 %s、纬度 %s 自动填并勾真太阳时" % (c["lon"], c["lat"]))
    else:
        bad("选市未自动填经纬／未勾真太阳时：%s" % c)

    ps = r.get("provSwitch") or {}
    if ps.get("lon") == "" and ps.get("lat") == "":
        if ps.get("tst") is True and not ps.get("tstState"):
            bad("换省后经纬已清空，但仍勾着真太阳时且状态为开：界面说在算真太阳时，实际无经度")
        elif ps.get("tst") is True:
            bad("换省后经纬已清空，复选框仍勾着真太阳时（无经度，静默失效）")
        else:
            ok("换省 → 经纬与地名一并清空，真太阳时勾选同步取消（不留旧省值）")
    else:
        bad("换省未清空经纬：%s" % ps)

    f = r.get("fold") or {}
    if f.get("closed") and f.get("txt1") == "展开信息" and f.get("open") and f.get("txt2") == "收起信息":
        ok("折叠／展开：面板收起、按钮文案随之切换")
    else:
        bad("折叠状态或文案异常：%s" % f)

    p = r.get("pick") or {}
    if p.get("dyBefore") != p.get("dyAfter") and p.get("onIdx") == "6":
        ok("点选第 7 步大运 → 主盘大运列 %s→%s，高亮跟随" % (p.get("dyBefore"), p.get("dyAfter")))
    else:
        bad("大运点选未联动：%s" % p)
    if p.get("lnBefore") != p.get("lnAfter"):
        ok("换大运 → 流年列同步换段（首年 %s→%s）" % (p.get("lnBefore"), p.get("lnAfter")))
    else:
        bad("换大运后流年未换段：%s→%s" % (p.get("lnBefore"), p.get("lnAfter")))

    rv = r.get("rev") or {}
    if rv.get("n", 0) > 0 and rv.get("after") == rv.get("want"):
        ok("反推：按当前四柱列出 %d 个候选，点第一个后主盘四柱与之相符" % rv["n"])
    else:
        bad("反推流程异常：%s" % rv)

    nm = r.get("name") or {}
    if nm.get("gap", -99) >= 0 and nm.get("clipped") and nm.get("title"):
        ok("24 字长姓名：限宽省略（悬停显示全名），与「公历」留有 %d px 间隙" % nm["gap"])
    else:
        bad("长姓名压字或未省略：%s" % nm)

    t = r.get("toast") or {}
    if t.get("n") == 1:
        ok("连续触发提示 → 浮条仍为单例（节点数 1）")
    else:
        bad("toast 出现叠层：节点数 %s" % t.get("n"))


# ---------------------------------------------------------------- B 窄屏
NARROW_JS = r"""
setTimeout(function(){
  var R = {err:null, sels:[], overlap:[], doc:0, scale:1, iw:innerWidth}, q = function(id){ return document.getElementById(id); };
  try {
    B = window.Bazi; B.state.base = new Date(Date.UTC(1991,4,18,19,0)); B.doChart();
    var cv = document.createElement('canvas'), cx = cv.getContext('2d');
    ['fy','fm','fd','fh','fmi','fProv','fCity'].forEach(function(id){
      var el = q(id); if (!el) { R.sels.push({id:id, missing:true}); return; }
      var cs = getComputedStyle(el);
      cx.font = cs.fontWeight + ' ' + cs.fontSize + ' ' + cs.fontFamily;
      var w = 0, worst = '';
      for (var i=0;i<el.options.length;i++) { var t = el.options[i].text; var tw = cx.measureText(t).width; if (tw>w){w=tw;worst=t;} }
      var padL = parseFloat(cs.paddingLeft), padR = parseFloat(cs.paddingRight);
      var avail = el.clientWidth - padL - padR;
      R.sels.push({id:id, need:Math.round(w), avail:Math.round(avail), worst:worst, over: w > avail + 0.5});
    });
    // 同行元素两两重叠检测
    var row = q('fy').parentNode;
    var kids = [].slice.call(row.children).filter(function(e){ var b=e.getBoundingClientRect(); return b.width>1 && b.height>1; });
    for (var i=0;i<kids.length;i++) for (var j=i+1;j<kids.length;j++) {
      var a = kids[i].getBoundingClientRect(), b = kids[j].getBoundingClientRect();
      var ox = Math.min(a.right,b.right) - Math.max(a.left,b.left);
      var oy = Math.min(a.bottom,b.bottom) - Math.max(a.top,b.top);
      if (ox > 0.5 && oy > 0.5) R.overlap.push([kids[i].id||kids[i].className, kids[j].id||kids[j].className, Math.round(ox)]);
    }
    // 六行几何（第一百零八令）：首控件贴列左、末控件贴行右、行内不越界。
    // 公历与农历各量一次——农历月「闰十一月」最宽，最易把行顶出右列。
    function rowsNow(){
      return [].map.call(document.querySelectorAll('.srow .pmod'), function(m){
        var b = m.getBoundingClientRect();
        var ks = [].filter.call(m.children, function(e){ return e.getBoundingClientRect().width > 1; });
        var f = ks.length ? ks[0].getBoundingClientRect() : null;
        var l = ks.length ? ks[ks.length-1].getBoundingClientRect() : null;
        return {l:Math.round(b.left), r:Math.round(b.right),
                fl:f?Math.round(f.left):null, lr:l?Math.round(l.right):null,
                sw:m.scrollWidth, cw:m.clientWidth};
      });
    }
    R.rows = rowsNow();
    var tb = q('tab-lunar');
    if (tb) { tb.click(); R.rowsLunar = rowsNow(); tb.blur();
              q('tab-solar').click(); }
    R.doc = document.documentElement.scrollWidth - document.documentElement.clientWidth;
    var w1 = q('fy').closest('.srow');
    R.scale = w1 ? (w1.getBoundingClientRect().width / w1.scrollWidth) : 1;
    document.title = 'UI:' + JSON.stringify(R);
  } catch (e) { R.err = String(e); document.title = 'UI:' + JSON.stringify(R); }
}, 800);
"""


def probe_narrow(html):
    print("\n[B] 窄屏 320px（下拉遮字／重叠／横向溢出）")
    r = run_narrow(html, 320)
    if not r:
        bad("窄屏探针未取到结果")
        return
    if r.get("iw") not in (None, 320):
        bad("窄屏视口实为 %spx（若为 500 则是无头窗口夹宽，测试失真）" % r.get("iw"))
    if r.get("err"):
        bad("窄屏探针异常：%s" % r["err"])
        return
    over = [s for s in r.get("sels") or [] if s.get("over") or s.get("missing")]
    if over:
        bad("下拉遮字 %d 个：%s" % (len(over),
                                 "、".join("%s 需 %spx／可用 %spx（最坏「%s」）"
                                          % (s["id"], s.get("need"), s.get("avail"), s.get("worst", ""))
                                          for s in over)))
    else:
        ok("7 个下拉在 320px 下均容得下最长选项（按真实文字宽度量，未截断）")
    if r.get("overlap"):
        bad("同行元素重叠：%s" % r["overlap"][:3])
    else:
        ok("时间行元素两两不重叠")
    for tag, rows in (("公历", r.get("rows") or []), ("农历", r.get("rowsLunar") or [])):
        if not rows:
            bad("%s 行几何未取到（切换失败？）" % tag)
            continue
        off = [x for x in rows if x["fl"] is None or abs(x["fl"] - x["l"]) > 1 or abs(x["lr"] - x["r"]) > 1]
        if len(rows) == 6 and not off:
            ok("320px %s模式六行首尾贴齐（首控件＝列左、末控件＝行右，无留白错位）" % tag)
        else:
            bad("320px %s模式行首尾错位 %d 行：%s" % (tag, len(off), off[:3]))
        ovf = [x["sw"] - x["cw"] for x in rows if x["sw"] - x["cw"] > 1]
        if not ovf:
            ok("320px %s模式六行无内溢出（无 px 下限把行顶出右列）" % tag)
        else:
            bad("320px %s模式行内溢出：%s px" % (tag, ovf))
    if r.get("doc", 0) <= 1:
        ok("320px 无横向溢出（scrollWidth−clientWidth＝%s）" % r.get("doc"))
    else:
        bad("320px 出现横向溢出 %spx" % r.get("doc"))


# ---------------------------------------------------------------- C 打印
def probe_print(html):
    print("\n[C] 打印／导出 PDF（黑块特征扫描）")
    if not os.path.exists(CHROME):
        bad("未装 Chrome，无法验打印")
        return
    tmpdir = tempfile.mkdtemp()
    pdf = os.path.join(tmpdir, "p.pdf")
    png = os.path.join(tmpdir, "p.png")
    try:
        subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                        "--no-pdf-header-footer", "--print-to-pdf=" + pdf,
                        "file://" + os.path.abspath(html)],
                       capture_output=True, timeout=120)
        if not os.path.exists(pdf):
            bad("未能生成 PDF")
            return
        subprocess.run(["sips", "-s", "format", "png", pdf, "--out", png],
                       capture_output=True, timeout=120)
        try:
            from PIL import Image
        except ImportError:
            bad("缺 Pillow，无法扫描黑块")
            return
        im = Image.open(png).convert("L")
        w, h = im.size
        px = im.load()
        # 找「连续 ≥ 宽 45%、两端都在页面内容区内」的近黑行。
        # 排除页边：sips 把纸外渲染成黑边（页首尾各一条满宽黑带），那是渲染边界不是版心。
        rows = []
        for y in range(int(h * 0.05), int(h * 0.95), 2):
            run = best = 0
            bx0 = bx1 = 0
            for x in range(0, w, 2):
                if px[x, y] < 40:
                    if run == 0:
                        x0 = x
                    run += 1
                    if run > best:
                        best, bx0, bx1 = run, x0, x
                else:
                    run = 0
            # 两端须离页边（≥3%），且连续长度 ≥45% 宽
            if best >= w * 0.45 / 2 and bx0 > w * 0.03 and bx1 < w * 0.97:
                rows.append(y)
        # 连续黑行成块
        blocks, cur = [], []
        for y in rows:
            if cur and y - cur[-1] > 6:
                blocks.append(cur); cur = []
            cur.append(y)
        if cur:
            blocks.append(cur)
        tall = [b for b in blocks if len(b) * 2 >= 12]
        if tall:
            bad("打印 PDF 出现 %d 处实心黑条（高 %s px），D95 特征" % (len(tall), [len(b) * 2 for b in tall]))
        else:
            ok("打印 PDF 无大面积实心黑条（%d×%d 渲染扫描，最长黑行块高 %s px）"
               % (w, h, max([len(b) * 2 for b in blocks], default=0)))
    finally:
        for p in (pdf, png):
            try:
                os.remove(p)
            except OSError:
                pass
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass


def main():
    html = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJ_DIR, "out", "八字排盘.html")
    print("== 界面与打印主动探针（audit_probe_ui.py）==")
    print("  页面：%s" % html)
    probe_ui(html)
    probe_narrow(html)
    probe_print(html)
    print("\n结果：%s（通过 %d 项，问题 %d 项）"
          % ("全部通过" if not FAIL else "有问题项", N, len(FAIL)))
    for x in FAIL:
        print("  · " + x)
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
