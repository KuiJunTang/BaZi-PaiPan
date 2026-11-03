#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render.py —— 组装单文件 HTML（录入界面＋命盘）与同源 MD

HTML 由三部分组成，全部内联，零外部依赖：
  1. assets/app.css    样式
  2. assets/data.js    节气／农历表（build_jsdata.py 生成）
  3. assets/app.js     历法与排盘内核 + 命盘渲染 + 录入界面
Python 只负责算出入参（初始命主）与文本形态 MD；命盘由前端同一套内核渲染，
默认定位「今年」或 --focus 指定年。
"""
import html as _html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")


def _read(name):
    with open(os.path.join(ASSETS, name), encoding="utf-8") as f:
        return f.read()


def brand_html(text, footer=""):
    """底部左栏：魁君堂标（点击进官网）＋ 署名；右栏由调用方传入 footer。"""
    try:
        b64 = _read("logo.b64").strip()
    except OSError:
        b64 = ""
    logo = ('<a class="brand" href="https://www.kuijuntang.com" target="_blank" rel="noopener"'
            ' aria-label="魁君堂官网"><img alt="魁君堂" src="data:image/png;base64,%s"></a>' % b64) if b64 else ""
    left = '<div class="fl">%s%s</div>' % (
        logo, '<div class="l1">%s</div>' % text if text else "")
    return '<hr class="fline">' + left + (footer or "")


PANEL = """
<div class="panel" id="panel">
  <div class="ph"><span class="brandrow"><img class="lg" alt="魁君堂" src="data:image/png;base64,__LOGO__"><span class="tdiv"></span><span class="tblock"><b>八字排盘</b><i>四柱十神 · 大运流年</i></span></span><button class="fold" id="fold" aria-label="收起信息"><span class="ft">收起信息</span><span class="ar"><svg viewBox="0 0 12 8" aria-hidden="true"><path d="M1.2 6.4 L6 1.6 L10.8 6.4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></span></button></div>
  <hr class="phline">
  <div class="pbody" id="pbody">
    <div class="card">
      <!-- 第一百零四令（2026-11-03）：信息／时间／地点各成两行，节标题居中。
           行序固定——信息：姓名／性别；时间：历法切换＋现时／年月日时分；地点：省市／经纬＋真太阳时 -->
      <div class="srow">
        <div class="shead"><span>信息</span></div>
        <div class="pmod">
          <span class="fg"><label class="fl">姓名</label>
          <input class="ipt name" id="fName" placeholder="可不填" autocomplete="off"></span>
        </div>
        <div class="pmod">
          <span class="fg"><label class="fl">性别</label>
          <div class="seg" id="fSex">
            <button data-v="male" class="on">男</button><button data-v="female">女</button>
          </div></span>
        </div>
      </div>

      <div class="srow">
        <div class="shead"><span>时间</span></div>
        <div class="pmod">
          <span class="tg"><button id="tab-solar" class="on">公历</button><button id="tab-lunar">农历</button><button id="tab-rev">反推</button></span>
          <button class="now" id="nowBtn">现时</button>
        </div>
        <div class="pmod">
          <select class="sel" id="fy"></select>
          <select class="sel" id="fm"></select>
          <select class="sel" id="fd"></select>
          <select class="sel" id="fh"></select>
          <select class="sel" id="fmi"></select>
        </div>
      <div class="rev" id="rev">
        <div class="rvgrid">
          <div class="rvc"><span>年柱</span><select id="rvYg"></select><select id="rvYz"></select></div>
          <div class="rvc"><span>月柱</span><select id="rvMg"></select><select id="rvMz"></select></div>
          <div class="rvc"><span>日柱</span><select id="rvDg"></select><select id="rvDz"></select></div>
          <div class="rvc"><span>时柱</span><select id="rvHg"></select><select id="rvHz"></select></div>
        </div>
        <button class="btn blue" id="revGo">反推</button>
        <div class="hits" id="revHits"></div>
      </div>
      </div>

      <div class="srow">
        <div class="shead"><span>地点</span></div>
        <div class="pmod">
          <select class="sel" id="fProv"></select>
          <select class="sel" id="fCity"></select>
        </div>
        <div class="pmod">
          <input class="ipt lon" id="fLon" placeholder="东经 120.38">
          <input class="ipt lat" id="fLat" placeholder="北纬 39.90" title="北纬度数；选市自动填">
          <label class="cb"><input type="checkbox" id="fTst"> 真太阳时</label>
          <span id="fPlace" hidden></span>
        </div>
      </div>

    </div>
  </div>
</div>
"""

EXTRA_CSS = """
.placebox{display:flex;gap:calc(10 * var(--u));align-items:center;margin:calc(-6 * var(--u)) 0 calc(14 * var(--u)) calc(96 * var(--u));flex-wrap:wrap}
.placebox[hidden]{display:none}
.placebox select{height:calc(42 * var(--u));border:0;border-radius:calc(10 * var(--u));background:var(--field);
  font-size:calc(21 * var(--u));font-family:inherit;padding:0 calc(10 * var(--u));color:#1F1F1F;
  max-width:calc(300 * var(--u))}
.placebox .ipt{width:calc(150 * var(--u));height:calc(42 * var(--u));border-radius:calc(10 * var(--u))}
.placebox{gap:calc(8 * var(--u))}
.placebox .cb{display:flex;align-items:center;gap:calc(5 * var(--u));font-size:calc(17.5 * var(--u));color:#6E6E6E;white-space:nowrap}
"""


def render_html(d, footer="", sign="", doc_title="八字排盘", init=None):
    css = _read("app.css") + EXTRA_CSS
    data = _read("data.js")
    cities = _read("cities.js")
    app = _read("app.js")
    init_json = json.dumps(init or {}, ensure_ascii=False)
    footer_html = brand_html(sign, footer)
    panel = PANEL.replace("__LOGO__", _read("logo.b64").strip())
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_html.escape(doc_title)}</title>
<style>{css}</style>
</head>
<body>
{panel}
<div class="page"><div id="chart"></div></div>
<div class="foot">{footer_html}</div>
<noscript><div style="text-align:center;padding:20px;color:#999">此页需启用 JavaScript 方可录入与排盘。</div></noscript>
<script>{data}</script>
<script>{cities}</script>
<script>window.BAZI_INIT={init_json};</script>
<script>{app}</script>
</body>
</html>
"""


# ---------------------------------------------------------------- MD
def render_md(d):
    """同源文本形态：与 HTML 同一份数据，逐项对应。"""
    p = d["pillars"]
    top = d["top"]
    L = []
    L.append("# 八字排盘 · %s" % " ".join(x["gan"] + x["zhi"] for x in p))
    L.append("")
    if d.get("name"):
        L.append("- 命主：%s" % d["name"])
    L.append("- 性别：%s（%s）" % ("男" if d["gender"] == "male" else "女", d["label"]))
    L.append("- 出生（公历／北京时间）：%s年%d月%d日 %02d:%02d"
             % (d["birth"].year, d["birth"].month, d["birth"].day, d["birth"].hour, d["birth"].minute))
    if d["tst_shift"]:
        L.append("- 真太阳时校正：%+d 分钟 → %s" % (d["tst_shift"], d["calc"].strftime("%Y-%m-%d %H:%M")))
    if d.get("sun"):
        L.append("- 古法定时辰：日出 %s／日落 %s（真太阳时，日出定卯初、日落定酉初，昼夜弧各六等分）"
                 % (d["sun"]["rise"], d["sun"]["set"]))
    L.append("- 起运：%s" % d["qiyun"]["text"])
    L.append("- 交运：%s" % d["qiyun"]["jiaoyun_text"])
    L.append("- 人元司令：%s（%s后%d日）" % (d["siling"]["gan"], d["siling"]["jie"], d["siling"]["days"]))
    _dy = d["dayun"][d["sel"]["dy"]]
    _ln = d["liunian"][d["sel"]["ln"]]
    L.append("- 显示定位：%s 大运 / %s 流年"
             % ("运前" if _dy.get("is_pre") else "%d" % _dy["year"],
                _ln["year"] if _ln.get("year") else "—"))
    L.append("")
    L.append("## 四柱")
    L.append("")
    L.append("| 盘式 | 年柱 | 月柱 | 日柱 | 时柱 | 大运 | 流年 |")
    L.append("| --- | --- | --- | --- | --- | --- | --- |")
    _dystar = "运前" if _dy.get("is_pre") else top["dayun"]["star"]
    L.append("| 主星 | " + " | ".join(x["star"] for x in p) + " | %s | %s |"
             % (_dystar, top["liunian"]["star"] or "—"))
    L.append("| %s | " % d["label"] + " | ".join(x["gan"] + x["zhi"] for x in p)
             + " | %s%s | %s%s |" % (top["dayun"]["gan"], top["dayun"]["zhi"],
                                     top["liunian"]["gan"], top["liunian"]["zhi"] or "—"))
    L.append("")
    L.append("### 藏气")
    L.append("")
    L.append("| 列 | 藏干（本气→余气）与十神 |")
    L.append("| --- | --- |")
    names = ["年柱", "月柱", "日柱", "时柱", "大运", "流年"]
    cols = [x["cang"] for x in p] + [top["dayun"]["cang"], top["liunian"]["cang"]]
    for n, c in zip(names, cols):
        L.append("| %s | %s |" % (n, "、".join("%s%s" % (x["gan"], x["short"]) for x in c) or "—"))
    L.append("")
    L.append("## 大运")
    L.append("")
    L.append("| 起始年 | 虚岁 | 干支 | 天干十神 | 地支本气十神 | 所选 |")
    L.append("| --- | --- | --- | --- | --- | --- |")
    for i, c in enumerate(d["dayun"]):
        flag = "●" if i == d["sel"]["dy"] else ""
        if c.get("is_pre"):
            L.append("| %d | %d | 运前 | — | — | %s |" % (c["year"], c["age"], flag))
        else:
            L.append("| %d | %d | %s%s | %s | %s | %s |"
                     % (c["year"], c["age"], c["gan"], c["zhi"], c["star"], c["zhi_star"], flag))
    L.append("")
    L.append("## 流年（%d 大运所辖十年）" % d["dayun"][d["sel"]["dy"]]["year"])
    L.append("")
    L.append("| 年份 | 虚岁 | 干支 | 天干十神 | 地支本气十神 | 所选 |")
    L.append("| --- | --- | --- | --- | --- | --- |")
    for i, c in enumerate(d["liunian"]):
        if not c.get("year"):
            L.append("| — | — | — | — | — | |")      # 起运后留空（第九令）
            continue
        L.append("| %d | %d | %s%s | %s | %s | %s |"
                 % (c["year"], c["age"], c["gan"], c["zhi"], c["star"], c["zhi_star"],
                    "●" if i == d["sel"]["ln"] else ""))
    L.append("")
    return "\n".join(L)
