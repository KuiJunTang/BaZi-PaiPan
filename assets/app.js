/* app.js —— 八字排盘前端：历法与排盘内核 + 命盘渲染 + 录入界面
   数据表见 data.js（BAZI_TABLES）。全部零依赖，可离线运行。
   同时可在 Node 中 require 作内核回归测试（见 scripts/verify_js.py）。 */
(function (g) {
  'use strict';

  /* 经典滚动条占宽补偿（2026-11-01 修复整页横滚）：100vw 含竖滚动条宽度，
     量出实际差值写入 --sbw，版式单位 --u 据此扣减；无经典滚动条时为 0 */
  if (typeof document !== 'undefined') {
    var setSbw = function () {
      var d = document.documentElement;
      d.style.setProperty('--sbw', Math.max(0, g.innerWidth - d.clientWidth) + 'px');
    };
    /* 行自适应（2026-11-01 八十三令）：真机表单控件/按钮有字底下限，缩窗时控件
       不再跟随收缩而行宽在缩，遂溢出。此处量测各行，超宽即整行等比 scale——
       transform 作用于渲染层，可突破字底下限，任何宽度都保证单行、不遮字、不出界 */
    var fitRows = function () {
      var mods = document.querySelectorAll('.pmod');
      Array.prototype.forEach.call(mods, function (m) {
        m.style.transform = '';
        if (m.scrollWidth > m.clientWidth + 1) {
          m.style.transformOrigin = 'left center';
          m.style.transform = 'scale(' + (m.clientWidth / m.scrollWidth) + ')';
        }
      });
    };
    setSbw();
    fitRows();
    var fitSoon = function () { setTimeout(fitRows, 60); setTimeout(fitRows, 400); };
    g.addEventListener('resize', function () { setSbw(); fitRows(); fitSoon(); });
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(function () { fitRows(); fitSoon(); });
    }
    g.addEventListener('load', function () { fitRows(); fitSoon(); });
    /* ResizeObserver：任何布局尺寸变化（含字体回退、历法切换）即时重算 */
    if (g.ResizeObserver) {
      var ro = new g.ResizeObserver(function () { fitRows(); });
      var startRO = function () {
        Array.prototype.forEach.call(document.querySelectorAll('.pmod'), function (m) { ro.observe(m); });
        ro.observe(document.documentElement);
      };
      if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', startRO); }
      else { startRO(); }
    }
  }

  if (!g.BAZI_TABLES && typeof require === 'function') { try { require('./data.js'); } catch (e) { } }
  if (!g.BAZI_CITIES && typeof require === 'function') { try { require('./cities.js'); } catch (e) { } }
  var T = g.BAZI_TABLES;

  var GAN = '甲乙丙丁戊己庚辛壬癸', ZHI = '子丑寅卯辰巳午未申酉戌亥';
  var GAN_WX = '木木火火土土金金水水', ZHI_WX = '水土木木土火火土金金土水';
  var SHENG = { '木': '火', '火': '土', '土': '金', '金': '水', '水': '木' };
  var KE = { '木': '土', '土': '水', '水': '火', '火': '金', '金': '木' };
  var WXC = { '木': 'mu', '火': 'huo', '土': 'tu', '金': 'jin', '水': 'shui' };
  var CANG = {
    '子': '癸', '丑': '己癸辛', '寅': '甲丙戊', '卯': '乙', '辰': '戊乙癸', '巳': '丙庚戊',
    '午': '丁己', '未': '己丁乙', '申': '庚壬戊', '酉': '辛', '戌': '戊辛丁', '亥': '壬甲'
  };
  var SHORT = { '比肩': '比', '劫财': '劫', '食神': '食', '伤官': '伤', '偏财': '才',
    '正财': '财', '七杀': '杀', '正官': '官', '偏印': '枭', '正印': '印', '日主': '主' };
  var SILING = {
    '寅': [['戊', 7], ['丙', 7], ['甲', 16]], '卯': [['甲', 10], ['乙', 20]],
    '辰': [['乙', 9], ['癸', 3], ['戊', 18]], '巳': [['戊', 5], ['庚', 9], ['丙', 16]],
    '午': [['丙', 10], ['己', 9], ['丁', 11]], '未': [['丁', 9], ['乙', 3], ['己', 18]],
    '申': [['戊', 7], ['壬', 7], ['庚', 16]], '酉': [['庚', 10], ['辛', 20]],
    '戌': [['辛', 9], ['丁', 3], ['戊', 18]], '亥': [['戊', 7], ['甲', 5], ['壬', 18]],
    '子': [['壬', 10], ['癸', 20]], '丑': [['癸', 9], ['辛', 3], ['己', 18]]
  };
  var TERMS = ['小寒', '大寒', '立春', '雨水', '惊蛰', '春分', '清明', '谷雨',
    '立夏', '小满', '芒种', '夏至', '小暑', '大暑', '立秋', '处暑',
    '白露', '秋分', '寒露', '霜降', '立冬', '小雪', '大雪', '冬至'];
  var JIE_ORDER = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 0];
  var LUNAR_MON = ['正', '二', '三', '四', '五', '六', '七', '八', '九', '十', '冬', '腊'];
  var LUNAR_DAY = ['初一', '初二', '初三', '初四', '初五', '初六', '初七', '初八', '初九', '初十',
    '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
    '廿一', '廿二', '廿三', '廿四', '廿五', '廿六', '廿七', '廿八', '廿九', '三十'];

  /* ---------------- 年号纪年（仅用于公历填好后的「显示」，不作输入） ----------------
     2026-11-02 九十三年令：1900 年前无农历表，元信息行改显「朝代·年号+年数 · 时辰」；
     民国（1912–1949）在农历后附「民国X年」。数据取中原正统王朝，年内改元取后者，
     并立政权（辽/金/西夏）从略；数组须严格按起始年升序。 */
  var ERAS = [
    ['隋', '开皇', 581], ['隋', '仁寿', 601], ['隋', '大业', 605],
    ['唐', '武德', 618], ['唐', '贞观', 627], ['唐', '永徽', 650], ['唐', '显庆', 656],
    ['唐', '龙朔', 661], ['唐', '麟德', 664], ['唐', '乾封', 666], ['唐', '总章', 668],
    ['唐', '咸亨', 670], ['唐', '上元', 674], ['唐', '仪凤', 676], ['唐', '调露', 679],
    ['唐', '永隆', 680], ['唐', '开耀', 681], ['唐', '永淳', 682], ['唐', '弘道', 683],
    ['唐', '嗣圣', 684], ['唐', '文明', 684], ['唐', '光宅', 684], ['唐', '垂拱', 685],
    ['唐', '永昌', 689], ['唐', '载初', 689], ['唐', '天授', 690], ['唐', '如意', 692],
    ['唐', '长寿', 692], ['唐', '延载', 694], ['唐', '证圣', 695], ['唐', '天册万岁', 695],
    ['唐', '万岁登封', 696], ['唐', '万岁通天', 696], ['唐', '神功', 697], ['唐', '圣历', 698],
    ['唐', '久视', 700], ['唐', '大足', 701], ['唐', '长安', 701], ['唐', '神龙', 705],
    ['唐', '景龙', 707], ['唐', '景云', 710], ['唐', '太极', 712], ['唐', '延和', 712],
    ['唐', '先天', 712], ['唐', '开元', 713], ['唐', '天宝', 742], ['唐', '至德', 756],
    ['唐', '乾元', 758], ['唐', '上元', 760], ['唐', '宝应', 762], ['唐', '广德', 763],
    ['唐', '永泰', 765], ['唐', '大历', 766], ['唐', '建中', 780], ['唐', '兴元', 784],
    ['唐', '贞元', 785], ['唐', '永贞', 805], ['唐', '元和', 806], ['唐', '长庆', 821],
    ['唐', '宝历', 825], ['唐', '大和', 827], ['唐', '开成', 836], ['唐', '会昌', 841],
    ['唐', '大中', 847], ['唐', '咸通', 860], ['唐', '乾符', 874], ['唐', '广明', 880],
    ['唐', '中和', 881], ['唐', '光启', 885], ['唐', '文德', 888], ['唐', '龙纪', 889],
    ['唐', '大顺', 890], ['唐', '景福', 892], ['唐', '乾宁', 894], ['唐', '光化', 898],
    ['唐', '天复', 901], ['唐', '天祐', 904],
    ['后梁', '开平', 907], ['后梁', '乾化', 911], ['后梁', '贞明', 915], ['后梁', '龙德', 921],
    ['后唐', '同光', 923], ['后唐', '天成', 926], ['后唐', '长兴', 930], ['后唐', '应顺', 934],
    ['后唐', '清泰', 934], ['后晋', '天福', 936], ['后晋', '开运', 944], ['后汉', '天福', 947],
    ['后汉', '乾祐', 948], ['后周', '广顺', 951], ['后周', '显德', 954],
    ['宋', '建隆', 960], ['宋', '乾德', 963], ['宋', '开宝', 968], ['宋', '太平兴国', 976],
    ['宋', '雍熙', 984], ['宋', '端拱', 988], ['宋', '淳化', 990], ['宋', '至道', 995],
    ['宋', '咸平', 998], ['宋', '景德', 1004], ['宋', '大中祥符', 1008], ['宋', '天禧', 1017],
    ['宋', '乾兴', 1022], ['宋', '天圣', 1023], ['宋', '明道', 1032], ['宋', '景祐', 1034],
    ['宋', '宝元', 1038], ['宋', '康定', 1040], ['宋', '庆历', 1041], ['宋', '皇祐', 1049],
    ['宋', '至和', 1054], ['宋', '嘉祐', 1056], ['宋', '治平', 1064], ['宋', '熙宁', 1068],
    ['宋', '元丰', 1078], ['宋', '元祐', 1086], ['宋', '绍圣', 1094], ['宋', '元符', 1098],
    ['宋', '建中靖国', 1101], ['宋', '崇宁', 1102], ['宋', '大观', 1107], ['宋', '政和', 1111],
    ['宋', '重和', 1118], ['宋', '宣和', 1119], ['宋', '靖康', 1126], ['宋', '建炎', 1127],
    ['宋', '绍兴', 1131], ['宋', '隆兴', 1163], ['宋', '乾道', 1165], ['宋', '淳熙', 1174],
    ['宋', '绍熙', 1190], ['宋', '庆元', 1195], ['宋', '嘉泰', 1201], ['宋', '开禧', 1205],
    ['宋', '嘉定', 1208], ['宋', '宝庆', 1225], ['宋', '绍定', 1228], ['宋', '端平', 1234],
    ['宋', '嘉熙', 1237], ['宋', '淳祐', 1241], ['宋', '宝祐', 1253], ['宋', '开庆', 1259],
    ['宋', '景定', 1260], ['宋', '咸淳', 1265], ['宋', '德祐', 1275], ['宋', '景炎', 1276],
    ['宋', '祥兴', 1278],
    ['元', '至元', 1264], ['元', '元贞', 1295], ['元', '大德', 1297], ['元', '至大', 1308],
    ['元', '皇庆', 1312], ['元', '延祐', 1314], ['元', '至治', 1321], ['元', '泰定', 1324],
    ['元', '致和', 1328], ['元', '天历', 1328], ['元', '至顺', 1330], ['元', '元统', 1333],
    ['元', '至元', 1335], ['元', '至正', 1341],
    ['明', '洪武', 1368], ['明', '建文', 1399], ['明', '永乐', 1403], ['明', '洪熙', 1425],
    ['明', '宣德', 1426], ['明', '正统', 1436], ['明', '景泰', 1450], ['明', '天顺', 1457],
    ['明', '成化', 1465], ['明', '弘治', 1488], ['明', '正德', 1506], ['明', '嘉靖', 1522],
    ['明', '隆庆', 1567], ['明', '万历', 1573], ['明', '泰昌', 1620], ['明', '天启', 1621],
    ['明', '崇祯', 1628],
    ['清', '天聪', 1627], ['清', '崇德', 1636], ['清', '顺治', 1644], ['清', '康熙', 1662],
    ['清', '雍正', 1723], ['清', '乾隆', 1736], ['清', '嘉庆', 1796], ['清', '道光', 1821],
    ['清', '咸丰', 1851], ['清', '同治', 1862], ['清', '光绪', 1875], ['清', '宣统', 1909],
    ['民国', '', 1912]
  ];
  function eraOf(y) {  // 公历年 → {dyn,era,n}；取起始年 ≤ y 的最近一条
    // 边界判据只此一处（第一百零二令）：民国止于 1949，1950 起无年号；
    // 年号表自 581 起。原先调用处各判一次（<1900 / 1912–1949 / ≤1949），
    // 三处写法略有出入，D92 已因此出过一次错，现统一收到函数内。
    if (y < 581 || y > 1949) return null;
    var hit = null;
    for (var i = 0; i < ERAS.length; i++) {
      if (ERAS[i][2] <= y) hit = ERAS[i]; else break;
    }
    return hit ? { dyn: hit[0], era: hit[1], n: y - hit[2] + 1 } : null;
  }
  function cnCount(n) {  // 年号/民国年数 → 中文（元年／十五／二十三／六十…）
    var D = '〇一二三四五六七八九';
    if (n === 1) return '元';
    if (n < 10) return D[n];
    if (n === 10) return '十';
    if (n < 20) return '十' + D[n - 10];
    if (n % 10 === 0) return D[Math.floor(n / 10)] + '十';
    return D[Math.floor(n / 10)] + '十' + D[n % 10];
  }
  function eraText(e) {  // 明·万历十五年 / 民国十三年
    if (!e) return '';
    return e.era ? (e.dyn + '·' + e.era + cnCount(e.n) + '年')
                 : (e.dyn + cnCount(e.n) + '年');
  }

  /* ---------------- 历法基础 ---------------- */
  function mod(a, n) { return ((a % n) + n) % n; }
  function D(y, m, d, h, mi) { return new Date(Date.UTC(y, m - 1, d, h || 0, mi || 0)); }
  function clone(dt) { return new Date(dt.getTime()); }
  function addMin(dt, n) { return new Date(dt.getTime() + n * 60000); }
  /* 儒略日：1582-10-15 起用格里历，之前用儒略历（与 sxtwl 的日柱体系一致） */
  function jdn(y, m, d) {
    var a = Math.floor((14 - m) / 12), y2 = y + 4800 - a, m2 = m + 12 * a - 3;
    var base = d + Math.floor((153 * m2 + 2) / 5) + 365 * y2 + Math.floor(y2 / 4);
    var old = (y < 1582) || (y === 1582 && (m < 10 || (m === 10 && d < 15)));
    if (old) return base - 32083;
    return base - Math.floor(y2 / 100) + Math.floor(y2 / 400) - 32045;
  }
  /* 儒略日 → 日期标签（混合历逆运算）。毫秒加减在 1582 年前会因儒略／格里闰年差
     而漂移一日，故凡是「按日步进」一律走 jdn，不走 Date 毫秒。 */
  function fromJdn(jd) {
    var a, b, c, d2, e, m, day, month, year;
    if (jd < 2299161) {                 // 儒略历
      c = jd + 32082;
      d2 = Math.floor((4 * c + 3) / 1461);
      e = c - Math.floor(1461 * d2 / 4);
      m = Math.floor((5 * e + 2) / 153);
      day = e - Math.floor((153 * m + 2) / 5) + 1;
      month = m + 3 - 12 * Math.floor(m / 10);
      year = d2 - 4800 + Math.floor(m / 10);
    } else {                            // 格里历
      a = jd + 32044;
      b = Math.floor((4 * a + 3) / 146097);
      c = a - Math.floor(146097 * b / 4);
      d2 = Math.floor((4 * c + 3) / 1461);
      e = c - Math.floor(1461 * d2 / 4);
      m = Math.floor((5 * e + 2) / 153);
      day = e - Math.floor((153 * m + 2) / 5) + 1;
      month = m + 3 - 12 * Math.floor(m / 10);
      year = 100 * b + d2 - 4800 + Math.floor(m / 10);
    }
    return [year, month, day];
  }

  var JQ = T.jq, LN = T.ln;
  function jqMin(y, idx) { return parseInt(JQ.s.substr(((y - JQ.y0) * 24 + idx) * 4, 4), 36); }

  /* 表外年份（唐及更早、或 2112 之后）：Meeus 太阳视黄经二分回推
     精度约 ±15 分钟，仅用于年/月柱换柱判定；1900–2112 走 sxtwl 表。 */
  function sunLon(utMs) {
    var d = new Date(utMs), y = d.getUTCFullYear(), mo = d.getUTCMonth() + 1, da = d.getUTCDate();
    var jd = jdn(y, mo, da) - 0.5 +
      (d.getUTCHours() * 3600000 + d.getUTCMinutes() * 60000 +
        d.getUTCSeconds() * 1000 + d.getUTCMilliseconds()) / 86400000;
    var t = (jd - 2451545) / 36525;
    var l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t;
    var m = (357.52911 + 35999.05029 * t - 0.0001537 * t * t) * Math.PI / 180;
    var c = (1.914602 - 0.004817 * t - 0.000014 * t * t) * Math.sin(m) +
      (0.019993 - 0.000101 * t) * Math.sin(2 * m) + 0.000289 * Math.sin(3 * m);
    var om = (125.04 - 1934.136 * t) * Math.PI / 180;
    return mod(l0 + c - 0.00569 - 0.00478 * Math.sin(om), 360);
  }
  /* ΔT = TT − UT（秒），Espenak–Meeus 多项式；古代可达数十分钟，不减会整体偏晚 */
  function deltaT(y) {
    var u, t;
    if (y < 500) { u = (y - 1820) / 100; return -20 + 32 * u * u; }
    if (y < 1600) {
      u = (y - 1000) / 100;
      return 1574.2 - 556.01 * u + 71.23472 * u * u + 0.319781 * u * u * u -
        0.8503463 * Math.pow(u, 4) - 0.005050998 * Math.pow(u, 5) + 0.0083572073 * Math.pow(u, 6);
    }
    if (y < 1700) { t = y - 1600; return 120 - 0.9808 * t - 0.01532 * t * t + t * t * t / 7129; }
    if (y < 1800) {
      t = y - 1700;
      return 8.83 + 0.1603 * t - 0.0059285 * t * t + 0.00013336 * t * t * t - Math.pow(t, 4) / 1174000;
    }
    if (y < 1860) {
      t = y - 1800;
      return 13.72 - 0.332447 * t + 0.0068612 * t * t + 0.0041116 * Math.pow(t, 3) -
        0.00037436 * Math.pow(t, 4) + 0.0000121272 * Math.pow(t, 5) -
        0.0000001699 * Math.pow(t, 6) + 0.000000000875 * Math.pow(t, 7);
    }
    if (y < 1900) {
      t = y - 1860;
      return 7.62 + 0.5737 * t - 0.251754 * t * t + 0.01680668 * Math.pow(t, 3) -
        0.0004473624 * Math.pow(t, 4) + Math.pow(t, 5) / 233174;
    }
    if (y < 1920) {
      t = y - 1900;
      return -2.79 + 1.494119 * t - 0.0598939 * t * t + 0.0061966 * Math.pow(t, 3) - 0.000197 * Math.pow(t, 4);
    }
    if (y < 1941) { t = y - 1920; return 21.20 + 0.84493 * t - 0.0761 * t * t + 0.0020936 * Math.pow(t, 3); }
    if (y < 1961) { t = y - 1950; return 29.07 + 0.407 * t - t * t / 233 + t * t * t / 2547; }
    if (y < 1986) { t = y - 1975; return 45.45 + 1.067 * t - t * t / 260 - t * t * t / 718; }
    if (y < 2005) {
      t = y - 2000;
      return 63.86 + 0.3345 * t - 0.060374 * t * t + 0.0017275 * Math.pow(t, 3) +
        0.000651814 * Math.pow(t, 4) + 0.00002373599 * Math.pow(t, 5);
    }
    if (y < 2050) { t = y - 2000; return 62.92 + 0.32217 * t + 0.005589 * t * t; }
    u = (y - 1820) / 100; return -20 + 32 * u * u;
  }
  function jqAstro(y, idx) {
    var target = mod(285 + idx * 15, 360);
    var approx = D(y, 1, 1, 0, 0).getTime() + idx * 15.2 * 86400000 - 8 * 3600000; // UT
    var a = approx - 12 * 86400000, b = approx + 12 * 86400000, i, mid, la, lb;
    for (i = 0; i < 48; i++) {
      mid = (a + b) / 2;
      la = sunLon(a); lb = sunLon(mid);
      if ((target - la + 360) % 360 <= (lb - la + 360) % 360) b = mid; else a = mid;
    }
    // 解出的是力学时（TT）：减 ΔT 得 UT，再加东八区
    return new Date((a + b) / 2 + 8 * 3600000 - deltaT(y) * 1000);
  }
  function jqDate(y, idx) {
    if (y >= JQ.y0 && y <= JQ.y1) return addMin(D(y, 1, 1, 0, 0), jqMin(y, idx));
    return jqAstro(y, idx);
  }

  var LUNAR_BASE_JDN = (LN && LN.base) ? LN.base : jdn(1900, 1, 31);
  var LUNAR_BASE = new Date((LUNAR_BASE_JDN - 2440588) * 86400000);  // LN.y0 年正月初一（UTC 00:00）
  function lnInfo(y) {
    var i = (y - LN.y0) * 15, s = LN.s.substr(i, 15);
    return { leap: parseInt(s.substr(0, 2), 10), lens: s.substr(2) };
  }
  function lunarMonths(y) {
    var inf = lnInfo(y), out = [], k = 0, m;
    for (m = 1; m <= 12; m++) {
      out.push({ m: m, leap: false, len: inf.lens.charAt(k++) === '1' ? 30 : 29 });
      if (inf.leap === m) out.push({ m: m, leap: true, len: inf.lens.charAt(k++) === '1' ? 30 : 29 });
    }
    return out;
  }
  function lunarYearDays(y) {
    return lunarMonths(y).reduce(function (a, b) { return a + b.len; }, 0);
  }
  function solarToLunar(dt) {
    var y = dt.getUTCFullYear(), m = dt.getUTCMonth() + 1, d = dt.getUTCDate();
    var days = jdn(y, m, d) - LUNAR_BASE_JDN;
    if (days < 0) return null;
    var ly = LN.y0;
    while (ly <= LN.y1 && days >= lunarYearDays(ly)) { days -= lunarYearDays(ly); ly++; }
    if (ly > LN.y1) return null;
    var ms = lunarMonths(ly), i;
    for (i = 0; i < ms.length; i++) {
      if (days < ms[i].len) return { y: ly, m: ms[i].m, leap: ms[i].leap, d: days + 1 };
      days -= ms[i].len;
    }
    return null;
  }
  function lunarToSolar(y, m, leap, d) {
    var days = 0, yy, ms, i, found = false;
    if (y < LN.y0 || y > LN.y1) return null;
    for (yy = LN.y0; yy < y; yy++) days += lunarYearDays(yy);
    ms = lunarMonths(y);
    for (i = 0; i < ms.length; i++) {
      if (ms[i].m === m && ms[i].leap === leap) { found = true; break; }
      days += ms[i].len;
    }
    if (!found) return null;
    days += Math.min(d, ms[i].len) - 1;
    return new Date(LUNAR_BASE.getTime() + days * 86400000);
  }
  function lunarDayText(d) { return LUNAR_DAY[d - 1] || ('' + d); }
  function lunarText(o) {
    if (!o) return '';
    return (o.leap ? '闰' : '') + LUNAR_MON[o.m - 1] + '月' + lunarDayText(o.d);
  }

  /* ---------------- 四柱 ---------------- */
  function yearGzIndex(dt) {
    var y = dt.getUTCFullYear(), lc = jqDate(y, 2);
    if (lc && dt < lc) y -= 1;
    return mod(y - 4, 60);
  }
  function jieList(y) {
    var out = [], i, t;
    for (i = 0; i < JIE_ORDER.length; i++) {
      t = jqDate(y, JIE_ORDER[i]);
      if (t) out.push({ t: t, name: TERMS[JIE_ORDER[i]], idx: JIE_ORDER[i] });
    }
    return out;
  }
  function prevJie(dt) {
    var y = dt.getUTCFullYear(), best = null, ys = [y - 1, y, y + 1], i, j, list;
    for (i = 0; i < ys.length; i++) {
      list = jieList(ys[i]);
      for (j = 0; j < list.length; j++) {
        if (list[j].t <= dt && (!best || list[j].t > best.t)) best = list[j];
      }
    }
    return best;
  }
  function nextJie(dt) {
    var y = dt.getUTCFullYear(), best = null, ys = [y - 1, y, y + 1], i, j, list;
    for (i = 0; i < ys.length; i++) {
      list = jieList(ys[i]);
      for (j = 0; j < list.length; j++) {
        if (list[j].t > dt && (!best || list[j].t < best.t)) best = list[j];
      }
    }
    return best;
  }
  function gzOf(ganI, zhiI) {
    for (var i = 0; i < 60; i++) if (i % 10 === ganI && i % 12 === zhiI) return i;
    return 0;
  }
  function monthGzIndex(dt) {
    var pj = prevJie(dt);
    if (!pj) return 0;
    var zhiI = (Math.floor(pj.idx / 2) + 1) % 12;
    var yg = yearGzIndex(dt) % 10;
    var k = mod(zhiI - 2, 12);
    return gzOf((yg * 2 + 2 + k) % 10, zhiI);
  }
  function dayGzIndex(dt) {
    return mod(jdn(dt.getUTCFullYear(), dt.getUTCMonth() + 1, dt.getUTCDate()) + 49, 60);
  }
  function hourGzIndex(dt, dayIdx) {
    var zhiI = Math.floor((dt.getUTCHours() + 1) / 2) % 12;
    var dg = (dayIdx === undefined ? dayGzIndex(dt) : dayIdx) % 10;
    return gzOf(((dg % 5) * 2 + zhiI) % 10, zhiI);
  }
  function ganWx(ch) { return GAN_WX.charAt(GAN.indexOf(ch)); }
  function zhiWx(ch) { return ZHI_WX.charAt(ZHI.indexOf(ch)); }
  function tenGod(dayGan, other) {
    if (other === dayGan) return '比肩';
    var dw = ganWx(dayGan), ow = ganWx(other);
    var same = mod(GAN.indexOf(dayGan), 2) === mod(GAN.indexOf(other), 2);
    if (dw === ow) return same ? '比肩' : '劫财';
    if (SHENG[dw] === ow) return same ? '食神' : '伤官';
    if (KE[dw] === ow) return same ? '偏财' : '正财';
    if (KE[ow] === dw) return same ? '七杀' : '正官';
    return same ? '偏印' : '正印';
  }

  /* 真太阳时：经度差 × 4 分 ＋ 均时差 */
  /* 均时差（分钟，正＝真太阳时快）：Meeus 28.1，T 取 TT（含 ΔT），
     太阳视黄经与节气回推同一套 sunLon，古代日期自洽（Spencer 旧式唐代偏差 1–3 分） */
  function eotMinutes(dt) {
    var ut = dt.getTime() - 8 * 3600000;
    var yU = new Date(ut).getUTCFullYear();
    var tt = ut + deltaT(yU) * 1000;
    var d = new Date(tt);
    var jd = jdn(d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate()) - 0.5 +
      (d.getUTCHours() * 3600000 + d.getUTCMinutes() * 60000 + d.getUTCSeconds() * 1000) / 86400000;
    var t = (jd - 2451545) / 36525;
    var l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t;
    var om = (125.04 - 1934.136 * t) * Math.PI / 180;
    var eps = 23.4392911 - 0.0130042 * t - 1.64e-7 * t * t + 5.04e-7 * t * t * t +
      9.20 / 3600 * Math.cos(om);
    var lam = sunLon(tt) * Math.PI / 180;
    var er = eps * Math.PI / 180;                       // eps 为度，三角函数前转弧度
    var alpha = Math.atan2(Math.cos(er) * Math.sin(lam), Math.cos(lam)) * 180 / Math.PI;
    var e = mod(l0 - 0.0057183 - alpha - 0.00478 * Math.sin(om) * Math.cos(er), 360);
    if (e > 180) e -= 360;
    return e * 4;
  }
  function trueSolar(dt, lon) {
    return addMin(dt, (lon - 120) * 4 + eotMinutes(dt));
  }

  function addYMD(dt, y, m, d) {
    var yy = dt.getUTCFullYear() + y, mm = dt.getUTCMonth() + 1 + m;
    yy += Math.floor((mm - 1) / 12); mm = mod(mm - 1, 12) + 1;
    var last = new Date(Date.UTC(yy, mm, 0)).getUTCDate();
    var dd = Math.min(dt.getUTCDate(), last);
    return new Date(Date.UTC(yy, mm - 1, dd, dt.getUTCHours(), dt.getUTCMinutes()) + d * 86400000);
  }

  /* ---------------- 古法定时辰 ----------------
     日出定卯初、日落定酉初，昼弧/夜弧各六等分（卯辰巳午未申／酉戌亥子丑寅）；
     午初＝真太阳正午、子初＝真太阳子夜。日出日落按太阳上边缘 −0.833°（含蒙气差）。 */
  function obliquity(msTT) {
    var d = new Date(msTT);
    var jd = jdn(d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate()) - 0.5 +
      (d.getUTCHours() * 3600000 + d.getUTCMinutes() * 60000 + d.getUTCSeconds() * 1000) / 86400000;
    var t = (jd - 2451545) / 36525;
    var om = (125.04 - 1934.136 * t) * Math.PI / 180;
    return 23.4392911 - 0.0130042 * t - 1.64e-7 * t * t + 5.04e-7 * t * t * t +
      9.20 / 3600 * Math.cos(om);
  }
  function sunRiseSetAST(astNoonMs, lat) {
    var lam = sunLon(astNoonMs) * Math.PI / 180;
    var eps = obliquity(astNoonMs) * Math.PI / 180;
    var sinD = Math.sin(eps) * Math.sin(lam);
    var dec = Math.asin(sinD);
    var phi = lat * Math.PI / 180, h0 = -0.833 * Math.PI / 180;
    var x = (Math.sin(h0) - Math.sin(phi) * sinD) / (Math.cos(phi) * Math.cos(dec));
    x = Math.max(-1, Math.min(1, x));
    var H0 = Math.acos(x) * 180 / Math.PI;
    return [720 - 4 * H0, 720 + 4 * H0];
  }
  function hourBranchAncient(astMin, rise, set) {
    var day = set - rise, night = 1440 - day, k, u;
    if (astMin >= rise && astMin < set) {
      k = Math.min(Math.floor((astMin - rise) / (day / 6)), 5);
      return [mod(3 + k, 12), 'day'];
    }
    u = astMin >= set ? astMin - set : astMin + 1440 - set;
    k = Math.min(Math.floor(u / (night / 6)), 5);
    return [mod(9 + k, 12), 'night'];
  }

  /* ---------------- 排盘 ---------------- */
  function paipan(o) {
    var birth = o.birth, gender = o.gender || 'male';
    var now = o.now || new Date();
    var steps = o.steps || 12;
    var calc = birth, tst = 0, sun = null, ancient = false;
    if (o.trueSolar && o.lon !== null && o.lon !== undefined) {
      calc = trueSolar(birth, o.lon);
      tst = Math.round((calc - birth) / 60000);
      ancient = o.lat !== null && o.lat !== undefined;
    }
    var yearI = yearGzIndex(calc), monthI = monthGzIndex(calc);
    var dayRef = calc, dayI, hourI;
    if (ancient) {
      var cy = calc.getUTCFullYear(), cm = calc.getUTCMonth(), cd = calc.getUTCDate();
      var noonAST = Date.UTC(cy, cm, cd, 12, 0, 0);
      var rs = sunRiseSetAST(noonAST, o.lat);
      var astMin = calc.getUTCHours() * 60 + calc.getUTCMinutes() + calc.getUTCSeconds() / 60;
      dayI = dayGzIndex(calc);                     // 子初＝真太阳子夜，按 calc 当日
      var br = hourBranchAncient(astMin, rs[0], rs[1]);
      var ziGan = (dayI % 5) * 2;
      hourI = gzOf(mod(ziGan + br[0], 10), br[0]);     // 五鼠遁起子
      var f2 = function (x) { x = Math.floor(x); return (x < 10 ? '0' : '') + x; };
      sun = { rise: f2(rs[0] / 60) + ':' + f2(rs[0] % 60),
              set: f2(rs[1] / 60) + ':' + f2(rs[1] % 60), seg: br[1] };
    } else {
      if (o.lateZi !== false && calc.getUTCHours() >= 23) dayRef = new Date(calc.getTime() + 86400000);
      dayI = dayGzIndex(dayRef);
      hourI = hourGzIndex(calc, dayI);
    }
    var dayGan = GAN.charAt(dayI % 10);
    var pos = ['年柱', '月柱', '日柱', '时柱'], idxs = [yearI, monthI, dayI, hourI];
    var pillars = [], i, j;
    for (i = 0; i < 4; i++) {
      var gg = GAN.charAt(idxs[i] % 10), zz = ZHI.charAt(idxs[i] % 12);
      var cang = [], cs = CANG[zz];
      for (j = 0; j < cs.length; j++) {
        var cg = cs.charAt(j), tg = tenGod(dayGan, cg);
        cang.push({ gan: cg, wx: ganWx(cg), short: SHORT[tg], god: tg });
      }
      var star = (pos[i] === '日柱') ? '日主' : tenGod(dayGan, gg);
      pillars.push({ pos: pos[i], gan: gg, zhi: zz, gan_wx: ganWx(gg), zhi_wx: zhiWx(zz),
        star: star, star_short: SHORT[star], cang: cang });
    }

    var pj = prevJie(calc);
    var daysAfter = Math.floor((calc - pj.t) / 86400000);
    var sl = SILING[ZHI.charAt(monthI % 12)], acc = 0, silGan = sl[sl.length - 1][0];
    for (i = 0; i < sl.length; i++) {
      acc += sl[i][1];
      if (daysAfter < acc) { silGan = sl[i][0]; break; }
    }

    var isYang = (yearI % 10) % 2 === 0;
    var forward = (isYang && gender === 'male') || (!isYang && gender === 'female');
    var spanDays, refName;
    if (forward) { var nj = nextJie(calc); spanDays = (nj.t - calc) / 86400000; refName = nj.name; }
    else { spanDays = (calc - pj.t) / 86400000; refName = pj.name; }

    var years = Math.floor(spanDays / 3);
    var monthsF = (spanDays - years * 3) * 4;
    var months = Math.floor(monthsF);
    var daysF = (monthsF - months) * 30;
    var dd = Math.floor(daysF);
    var hours = Math.round((daysF - dd) * 24);
    if (hours >= 24) { hours -= 24; dd += 1; }
    var jiaoyun = addYMD(birth, years, months, dd);
    jiaoyun = new Date(jiaoyun.getTime() + hours * 3600000);

    var dayun = [{ year: birth.getUTCFullYear(), age: 1, gan: '', zhi: '', star: '运',
      star_short: '前', is_pre: true, cang: [] }];
    for (i = 1; i <= steps; i++) {
      var gi = forward ? mod(monthI + i, 60) : mod(monthI - i, 60);
      var dg2 = GAN.charAt(gi % 10), dz2 = ZHI.charAt(gi % 12);
      var y2 = jiaoyun.getUTCFullYear() + 10 * (i - 1);
      var st2 = tenGod(dayGan, dg2), zs2 = tenGod(dayGan, CANG[dz2].charAt(0));
      var cg2 = [];
      for (j = 0; j < CANG[dz2].length; j++) {
        var ch = CANG[dz2].charAt(j);
        cg2.push({ gan: ch, wx: ganWx(ch), short: SHORT[tenGod(dayGan, ch)] });
      }
      dayun.push({ year: y2, age: y2 - birth.getUTCFullYear() + 1, gan: dg2, zhi: dz2,
        gan_wx: ganWx(dg2), zhi_wx: zhiWx(dz2), star: st2, star_short: SHORT[st2],
        zhi_star: zs2, zhi_star_short: SHORT[zs2], is_pre: false, cang: cg2 });
    }
    function decade(base) {
      var arr = [], k;
      for (k = 0; k < 10; k++) {
        var yy = base + k, gi2 = mod(yy - 4, 60);
        var g3 = GAN.charAt(gi2 % 10), z3 = ZHI.charAt(gi2 % 12);
        var s3 = tenGod(dayGan, g3), z3s = tenGod(dayGan, CANG[z3].charAt(0));
        var c3 = [];
        for (j = 0; j < CANG[z3].length; j++) {
          var c4 = CANG[z3].charAt(j);
          c3.push({ gan: c4, wx: ganWx(c4), short: SHORT[tenGod(dayGan, c4)] });
        }
        arr.push({ year: yy, age: yy - birth.getUTCFullYear() + 1, gan: g3, zhi: z3,
          gan_wx: ganWx(g3), zhi_wx: zhiWx(z3), star: s3, star_short: SHORT[s3],
          zhi_star: z3s, zhi_star_short: SHORT[z3s], cang: c3 });
      }
      return arr;
    }
    for (i = 0; i < dayun.length; i++) {
      dayun[i].ln = dayun[i].is_pre ? preDecade() : decade(dayun[i].year);
    }
    /* 运前：只列出生年至起运前一年的流年，起运之后留空（道长第九令） */
    function preDecade() {
      var by = birth.getUTCFullYear(), qy = jiaoyun.getUTCFullYear();
      var n = Math.max(0, Math.min(10, qy - by));
      var arr = decade(by).slice(0, n), k;
      for (k = n; k < 10; k++) {
        arr.push({ year: 0, age: 0, gan: '', zhi: '', empty: true, gan_wx: '土', zhi_wx: '土',
          star: '', star_short: '', zhi_star: '', zhi_star_short: '', cang: [] });
      }
      return arr;
    }
    function lnIndexOf(arr, year) {
      for (var k = 0; k < arr.length; k++) if (arr[k].year === year) return k;
      return -1;
    }
    function lastReal(arr) {
      for (var k = arr.length - 1; k >= 0; k--) if (arr[k].year) return k;
      return 0;
    }
    function dyFor(year) {
      var k = 0;
      for (var q = 1; q < dayun.length; q++) if (year >= dayun[q].year) k = q;
      return k;
    }
    var nowDy = dyFor(now.getUTCFullYear());
    var nowLn = lnIndexOf(dayun[nowDy].ln, now.getUTCFullYear());
    if (nowLn < 0) nowLn = lastReal(dayun[nowDy].ln);
    var selDy = nowDy, selLn = nowLn;
    if (o.focus) {
      selDy = dyFor(o.focus);
      selLn = lnIndexOf(dayun[selDy].ln, o.focus);
      if (selLn < 0) selLn = lastReal(dayun[selDy].ln);
    }
    var jyJie = prevJie(jiaoyun);
    if (!jyJie) jyJie = { name: '', t: jiaoyun };
    var jyDays = Math.floor((D(jiaoyun.getUTCFullYear(), jiaoyun.getUTCMonth() + 1, jiaoyun.getUTCDate(), 0, 0) -
      D(jyJie.t.getUTCFullYear(), jyJie.t.getUTCMonth() + 1, jyJie.t.getUTCDate(), 0, 0)) / 86400000);
    var jyGz = GAN.charAt(mod(jiaoyun.getUTCFullYear() - 4, 60) % 10);

    return {
      birth: birth, calc: calc, tst: tst, sun: sun, gender: gender, name: o.name || '',
      label: gender === 'male' ? '乾造' : '坤造',
      pillars: pillars, day_gan: dayGan,
      siling: { gan: silGan, jie: pj.name, days: daysAfter },
      qiyun: { forward: forward, years: years, months: months, days: dd, hours: hours,
        text: '出生后' + years + '年' + months + '月' + dd + '天' + hours + '小时',
        jiaoyun: jiaoyun,
        jiaoyun_text: jyJie.name ? ('逢' + jyGz + '年' + jyJie.name + '后' + jyDays + '天')
          : ('起运 ' + jiaoyun.getUTCFullYear() + ' 年') },
      dayun: dayun, sel: { dy: selDy, ln: selLn }, now: { dy: nowDy, ln: nowLn }
    };
  }

  /* 反推：由四柱求日期。日柱 60 日一循环，先定位首个吻合日再步进 60 天，
     避免逐年逐日扫（600–2100 共五十余万天）。子时取 00:00：子时换日，
     23:00–23:59 已属次日日柱，00:00–00:59 才是当日日柱的无歧义时刻。

     第一百零二令（D99）修正：年柱／月柱必须按**候选时刻**判，不能拿 12:00 代替。
     交节落在当日 00:00 与候选钟点之间时，12:00 与真实时刻分属两月／两年，
     当日真解会被判掉（如 2026-02-04 00:30 生于立春前，年柱仍属乙巳）。
     进一步：交节可能落在**时辰之内**（如 600-01-03 09:13 小寒，而 09:43 出生属巳时），
     故整个时辰窗口取两端各判一次——一年二十四节，落在某一时辰里的情形年年都有。
     子时另检前一日 23 时档：日柱同属该日，年月柱却按前一日判。 */
  function reverse(ids, y0, y1) {
    var out = [], yi = ids[0], mi = ids[1], di = ids[2], hi = ids[3];
    var zhiI = hi % 12;
    var jd0 = jdn(y0, 1, 1), jd1 = jdn(y1, 12, 31);
    var start = D(y0, 1, 1, 12, 0);
    var first = jd0 + mod(di - dayGzIndex(start), 60);
    var sH = zhiI === 0 ? 0 : zhiI * 2 - 1;      // 时辰起钟点
    var span = zhiI === 0 ? 1 : 2;               // 时辰跨小时数
    var dg = di % 10;
    if (gzOf(((dg % 5) * 2 + zhiI) % 10, zhiI) !== hi) return out;  // 时干不合，整盘无解
    function fit(dt) {
      return yearGzIndex(dt) === yi && monthGzIndex(dt) === mi;
    }
    for (var jd = first; jd <= jd1; jd += 60) {
      var p = fromJdn(jd), t0 = D(p[0], p[1], p[2], sH, 0);
      if (dayGzIndex(t0) !== di) continue;       // 日柱已不合，整个时辰都不必再看
      if (fit(t0)) { out.push(t0); }
      else {
        var t1 = new Date(D(p[0], p[1], p[2], sH + span, 0).getTime() - 60000);
        if (fit(t1)) out.push(t1);               // 交节在时辰内，取窗口末
        else if (zhiI === 0) {                   // 前一日 23:00–23:59（深夜子时）
          var q0 = D(p[0], p[1], p[2] - 1, 23, 0);
          if (fit(q0)) out.push(q0);
          else {
            var q1 = D(p[0], p[1], p[2] - 1, 23, 59);
            if (fit(q1)) out.push(q1);
          }
        }
      }
      if (out.length > 60) break;
    }
    return out;
  }

  /* ---------------- 渲染 ---------------- */
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function gzSpan(ch, wx, extra) {
    return '<span class="gz ' + (extra || '') + WXC[wx] + '">' + ch + '</span>';
  }
  function cangRows(items) {
    if (!items || !items.length) return '';
    return items.map(function (c) {
      return '<div class="cg"><b class="' + WXC[c.wx] + '">' + c.gan + '</b><i>' + c.short + '</i></div>';
    }).join('');
  }
  function colHtml(o, i, kind) {
    if (o.empty) return '<div class="col empty"></div>';
    var body = o.is_pre
      ? '<div class="pre">运</div><div class="pre">前</div>'
      : '<div class="pair"><b class="' + WXC[o.gan_wx] + '">' + o.gan + '</b><i>' + o.star_short + '</i></div>' +
        '<div class="pair"><b class="' + WXC[o.zhi_wx] + '">' + o.zhi + '</b><i>' + o.zhi_star_short + '</i></div>';
    return '<div class="col" data-' + kind + '="' + i + '"><div class="yr">' + o.year + '</div>' +
      '<div class="age">' + o.age + '岁</div>' + body + '</div>';
  }

  var CHART = null;
  function renderChart(d, foot) {
    CHART = { d: d, foot: foot, dy: d.sel.dy, ln: d.sel.ln };
    var b = d.birth;
    var btxt = b.getUTCFullYear() + '年' + (b.getUTCMonth() + 1) + '月' + b.getUTCDate() + '日 ' +
      pad2(b.getUTCHours()) + ':' + pad2(b.getUTCMinutes());
    var lun = solarToLunar(d.calc);
    // 元信息行两行制（2026-11-01 五十三～五十七令）：
    // 第一行＝姓名＋公历＋真太阳时（勾选时，钟表时刻）；
    // 第二行＝乾造／坤造徽标＋农历全日期带时辰（紧贴无空格）＋真太阳时（显示时辰，
    //         与上行真太阳时上下对齐——两行 tst 项同挂 .kv.tst 右对齐）
    // 时辰取排盘结果（古法/固定口径都在 paipan 内定），不再按钟点公式现算
    var zhiCalc = d.pillars[3].zhi;
    var r1 = '<span class="kv"><i>公历</i>' + btxt + '</span>' +
      (d.tst ? '<span class="kv tst"><i>真太阳时</i>' + pad2(d.calc.getUTCHours()) + ':' +
        pad2(d.calc.getUTCMinutes()) + '</span>' : '');
    // 九十三年令（2026-11-02）：农历表已扩至 600 起，古代亦可显「几月初几」。
    // 年份表示：<1900 用「朝代·年号年数」；1912–1949 用「民国X年」；1900–1911 及其余用农历年。
    // 仅显示，不作输入（古代不接受农历录入）。
    var cyear = b.getUTCFullYear();
    var era = eraOf(cyear);
    var r2;
    if (lun) {
      var useEra = ((cyear < 1900) || (cyear >= 1912 && cyear <= 1949)) && era;
      var ytxt = useEra ? eraText(era) : (cnYear(lun.y) + '年');
      r2 = '<span class="kv"><i>' + (useEra ? '纪年' : '农历') + '</i>' + ytxt + ' ' +
        lunarText(lun) + zhiCalc + '时</span>';
    } else {
      r2 = era
        ? '<span class="kv"><i>纪年</i>' + eraText(era) + ' · ' + zhiCalc + '时</span>'
        : '<span class="kv"><i>时辰</i>' + zhiCalc + '时</span>';
    }
    r2 += (d.tst ? '<span class="kv tst"><i>真太阳时</i>' + zhiCalc + '时</span>' : '');
    var who = '<div class="who">' +
      '<span class="nm" title="' + esc(d.name || '示例') + '">' + esc(d.name || '示例') + '</span>' +
      '<span class="wv r1">' + r1 + '</span>' +
      '<span class="tag">' + d.label + '</span>' +
      '<span class="wv r2">' + r2 + '</span>' +
      '</div>';

    var head = '<div class="grid head"><div class="lbl">盘式</div>' +
      ['年柱', '月柱', '日柱', '时柱', '大运', '流年'].map(function (n) {
        return '<div class="c">' + n + '</div>'; }).join('') + '</div>';

    var dyc = d.dayun[CHART.dy], lnc = dyc.ln[CHART.ln];
    var starRow = '<div class="grid star"><div class="lbl">主星</div>' +
      d.pillars.map(function (p) { return '<div class="c">' + p.star + '</div>'; }).join('') +
      '<div class="c" id="star-dy">' + (dyc.is_pre ? '运前' : dyc.star) + '</div>' +
      '<div class="c" id="star-ln">' + lnc.star + '</div></div>';

    var pilRow = '<div class="grid pillars"><div class="lbl">' + d.label + '</div>' +
      d.pillars.map(function (p) {
        return '<div class="c">' + gzSpan(p.gan, p.gan_wx) + gzSpan(p.zhi, p.zhi_wx, 'zhi ') + '</div>';
      }).join('') +
      '<div class="c" id="gz-dy">' + (dyc.gan ? gzSpan(dyc.gan, dyc.gan_wx) + gzSpan(dyc.zhi, dyc.zhi_wx, 'zhi ') : '') + '</div>' +
      '<div class="c" id="gz-ln">' + (lnc.gan ? gzSpan(lnc.gan, lnc.gan_wx) + gzSpan(lnc.zhi, lnc.zhi_wx, 'zhi ') : '') + '</div>' +
      '<span class="sep"></span></div>';

    var cangRow = '<div class="cang"><div class="grid"><div class="lbl">藏气</div>' +
      d.pillars.map(function (p) { return '<div class="c">' + cangRows(p.cang) + '</div>'; }).join('') +
      '<div class="c" id="cang-dy">' + cangRows(dyc.cang) + '</div>' +
      '<div class="c" id="cang-ln">' + cangRows(lnc.cang) + '</div></div></div>';

    var qy = '<div class="qy"><div class="r"><span>起运：' + d.qiyun.text + '</span>' +
      '<span class="rt">人元司令：' + d.siling.gan + '（' + d.siling.jie + '后' + d.siling.days + '日）</span></div>' +
      '<div class="r"><span>交运：' + d.qiyun.jiaoyun_text + '</span>' +
      '<span class="ln-era" id="lnEra"></span>' +
      '<a class="locate" id="locate">定位现在</a></div></div>';

    var dyCols = d.dayun.map(function (o, i) { return colHtml(o, i, 'dy'); }).join('');
    var lnHtml = lnc && dyc ? dyc.ln.map(function (o, i) { return colHtml(o, i, 'ln'); }).join('') : '';

    var dySect = '<section class="sect"><div class="wrap2">' +
      '<div class="lab"><span class="v">大运</span></div>' +
      '<div class="strip" id="dyStrip"><div class="cols" id="dyCols">' + dyCols + '</div></div></div></section>';
    var lnSect = '<section class="sect"><div class="wrap2">' +
      '<div class="lab"><span class="v">流年</span></div>' +
      '<div class="strip" id="lnStrip"><div class="cols" id="lnCols">' + lnHtml + '</div></div></div></section>';

    document.getElementById('chart').innerHTML =
      who + head + starRow + pilRow + cangRow + qy + dySect + lnSect;
    mark();
    paintEra();
    bindChart();
  }

  function pad2(n) { return (n < 10 ? '0' : '') + n; }

  function mark() {
    var d = CHART;
    document.querySelectorAll('[data-dy]').forEach(function (el) {
      el.classList.toggle('on', +el.getAttribute('data-dy') === d.dy);
    });
    document.querySelectorAll('[data-ln]').forEach(function (el) {
      el.classList.toggle('on', +el.getAttribute('data-ln') === d.ln);
    });
  }
  /* 九十四令（2026-11-02）：建国前（1949 年及以前，民国三十八年止）的流年，在「交运」行中部
     随点选显示该年的年号纪年（如「民国十三年」「隋·开皇二十年」），便于与原历核对；
     1950 年起不显示。口径须与元信息行（cyear>=1912 && cyear<=1949）完全一致——两处同盘同判，
     见 D92。年号仅作显示，不参与任何计算，也不作为输入。 */
  function paintEra() {
    var el = document.getElementById('lnEra');
    if (!el || !CHART || !CHART.d) return;
    var dyc = CHART.d.dayun[CHART.dy];
    var o = dyc && dyc.ln ? dyc.ln[CHART.ln] : null;
    var y = o ? o.year : null;
    var e = (y && y <= 1949) ? eraOf(y) : null;
    el.textContent = e ? eraText(e) : '';
  }
  function paintTop() {
    var d = CHART.d, dyc = d.dayun[CHART.dy], lnc = dyc.ln[CHART.ln];
    document.getElementById('star-dy').textContent = dyc.is_pre ? '运前' : dyc.star;
    document.getElementById('star-ln').textContent = lnc.star;
    document.getElementById('gz-dy').innerHTML = dyc.gan ? gzSpan(dyc.gan, dyc.gan_wx) + gzSpan(dyc.zhi, dyc.zhi_wx, 'zhi ') : '';
    document.getElementById('gz-ln').innerHTML = lnc.gan
      ? gzSpan(lnc.gan, lnc.gan_wx) + gzSpan(lnc.zhi, lnc.zhi_wx, 'zhi ') : '';
    document.getElementById('cang-dy').innerHTML = cangRows(dyc.cang);
    document.getElementById('cang-ln').innerHTML = cangRows(lnc.cang);
  }
  function paintLnRow() {
    var d = CHART.d, dyc = d.dayun[CHART.dy];
    document.getElementById('lnCols').innerHTML =
      dyc.ln.map(function (o, i) { return colHtml(o, i, 'ln'); }).join('');
  }

  function bindChart() {
    var dyStrip = document.getElementById('dyStrip'), lnStrip = document.getElementById('lnStrip');
    attach(dyStrip, 'dy'); attach(lnStrip, 'ln');
    [dyStrip, lnStrip].forEach(function (st) {
      if (!st) return;
      var upd = function () {
        // 九十七令：渐隐改挂 .wrap2 伪元素（不用 mask，导出 PDF 不再出黑块），
        // 故与 strip 同步打 more 标记
        var more = st.scrollLeft + st.clientWidth < st.scrollWidth - 4;
        st.classList.toggle('more', more);
        var w2 = st.parentNode;
        if (w2 && w2.classList) w2.classList.toggle('more', more);
      };
      st.addEventListener('scroll', upd);
      setTimeout(upd, 30); upd();
    });
    var loc = document.getElementById('locate');
    if (loc) loc.addEventListener('click', function (e) {
      e.preventDefault();
      CHART.dy = CHART.d.now.dy; CHART.ln = CHART.d.now.ln;
      paintLnRow(); paintTop(); mark(); paintEra();
      scrollToSel('dy');
    });
    mark();
  }
  function scrollToSel(kind) {
    var strip = document.getElementById(kind === 'dy' ? 'dyStrip' : 'lnStrip');
    var idx = kind === 'dy' ? CHART.dy : CHART.ln;
    var col = strip.querySelector('[data-' + kind + '="' + idx + '"]');
    if (col) strip.scrollLeft = Math.max(0, col.offsetLeft - strip.clientWidth / 2 + col.offsetWidth / 2);
  }

  /* 点击选中；内容溢出时按住横向拖动为翻看（全局只注册一次监听） */
  var DRAG = { strip: null, kind: '', down: false, moved: false, sx: 0, sl: 0, idx: -1 };
  function attach(strip, kind) {
    if (!strip) return;
    strip.addEventListener('pointerdown', function (e) {
      DRAG.strip = strip; DRAG.kind = kind; DRAG.down = true; DRAG.moved = false;
      DRAG.sx = e.clientX; DRAG.sl = strip.scrollLeft;
      var c = e.target.closest ? e.target.closest('[data-' + kind + ']') : null;
      DRAG.idx = c ? +c.getAttribute('data-' + kind) : -1;
    });
  }
  if (typeof window !== 'undefined' && typeof document !== 'undefined') {
    window.addEventListener('pointermove', function (e) {
      if (!DRAG.down || !DRAG.strip) return;
      var dx = e.clientX - DRAG.sx;
      if (Math.abs(dx) > 4) DRAG.moved = true;
      if (DRAG.strip.scrollWidth > DRAG.strip.clientWidth + 2) DRAG.strip.scrollLeft = DRAG.sl - dx;
    });
    window.addEventListener('pointerup', function () {
      if (DRAG.down && !DRAG.moved && DRAG.idx >= 0) pick(DRAG.kind, DRAG.idx);
      DRAG.down = false; DRAG.idx = -1; DRAG.strip = null;
    });
  }
  function pick(kind, i) {
    var d = CHART.d;
    if (kind === 'ln' && d.dayun[CHART.dy].ln[i] && d.dayun[CHART.dy].ln[i].empty) return;
    if (kind === 'dy') {
      if (i === CHART.dy) return;
      var y = d.dayun[CHART.dy].ln[CHART.ln].year;
      CHART.dy = i;
      var arr = d.dayun[i].ln, keep = -1;
      for (var j = 0; j < arr.length; j++) if (arr[j].year === y) keep = j;
      CHART.ln = keep < 0 ? 0 : keep;
      paintLnRow(); mark(); scrollToSel('ln');
    } else {
      CHART.ln = i;
    }
    paintTop(); mark(); paintEra();
  }

  g.Bazi = { paipan: paipan, solarToLunar: solarToLunar, lunarToSolar: lunarToSolar,
    _eot: eotMinutes, _trueSolar: trueSolar,
    lunarText: lunarText, reverse: reverse, tenGod: tenGod, renderChart: renderChart,
    eraOf: eraOf, eraText: eraText,   // 测试钩子（第一百零二令）：年号只显示，导出仅供脚本核对
    get chart() { return CHART; }, pick: pick, setChart: function (c) { CHART = c; },
    paintTop: paintTop, paintLnRow: paintLnRow, mark: mark, paintEra: paintEra,
    range: { y0: 600, y1: 2100 },
    _jq: function (y, i) { return jqDate(y, i); }, _jdn: jdn, _astro: jqAstro,
    _dayGz: dayGzIndex, _monthGz: monthGzIndex, _yearGz: yearGzIndex, _gzOf: gzOf,
    GAN: GAN, ZHI: ZHI };
  if (typeof module !== 'undefined' && module.exports) module.exports = g.Bazi;
  /* ================= 录入界面 ================= */
  if (typeof document === 'undefined') return;

  var S = { mode: 'solar', base: null, gender: 'male', name: '', lon: null, tst: false,
    focus: null, now: new Date(), placeName: '', prov: -1, city: -1, live: false };
  var ITEM = 42, wlock = false, wtimer = null, FOOT = '';
  var PROVS = g.BAZI_CITIES || [];
  function provOf(name) {
    for (var i = 0; i < PROVS.length; i++)
      for (var j = 0; j < PROVS[i][1].length; j++)
        if (PROVS[i][1][j][0] === name) return i;
    return -1;
  }
  function q(id) { return document.getElementById(id); }
  // 轻量提示（2026-11-02 审计 D88）：取代已撤销的 fBirth 行，用于「农历越界／真太阳时缺经度」
  // 等静默回退场景，避免用户点了控件却毫无反馈。
  /* 轻提示单例（D93）：同一时刻只允许一条，后到的替换先到的并重置计时——
     否则连续触发会叠出多层同位置的浮条（视觉重影）。 */
  var toastEl = null, toastTimer = null;
  function toast(msg) {
    if (!toastEl) {
      toastEl = document.createElement('div');
      toastEl.className = 'toast';
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = msg;
    requestAnimationFrame(function () { toastEl.classList.add('show'); });
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove('show'); }, 2200);
  }
  function f2(n) { return (n < 10 ? '0' : '') + n; }
  function daysInMonth(y, m) { return new Date(Date.UTC(y, m, 0)).getUTCDate(); }
  function cnYear(y) {
    return String(y).split('').map(function (c) { return '〇一二三四五六七八九'[+c]; }).join('');
  }
  function parts() {
    var b = S.base;
    return [b.getUTCFullYear(), b.getUTCMonth() + 1, b.getUTCDate(), b.getUTCHours(), b.getUTCMinutes()];
  }
  function setBase(y, m, d, h, mi) {
    S.base = D(y, m, Math.min(d, daysInMonth(y, m)), h, mi);
  }

  var COLS = [];
  function buildCols() {
    var p = parts(), y = p[0], m = p[1], d = p[2], cols = [], arr = [], yy;
    for (yy = g.Bazi.range.y0; yy <= g.Bazi.range.y1; yy++) arr.push({ v: yy, t: yy + '年' });
    cols.push({ key: 'y', items: arr, idx: y - g.Bazi.range.y0 });
    if (S.mode === 'lunar') {
      var lun = solarToLunar(S.base) || { y: y, m: 1, leap: false, d: 1 };
      var ms = lunarMonths(lun.y), mArr = [], sel = 0, i;
      for (i = 0; i < ms.length; i++) {
        mArr.push({ t: (ms[i].leap ? '闰' : '') + LUNAR_MON[ms[i].m - 1] + '月',
          m: ms[i].m, leap: ms[i].leap });
        if (ms[i].m === lun.m && ms[i].leap === lun.leap) sel = i;
      }
      cols.push({ key: 'm', items: mArr, idx: sel, lunar: true });
      var len = ms[sel].len, dArr = [], k;
      for (k = 1; k <= len; k++) dArr.push({ v: k, t: LUNAR_DAY[k - 1] });
      cols.push({ key: 'd', items: dArr, idx: Math.min(lun.d, len) - 1 });
    } else {
      var mArr2 = [], mm;
      for (mm = 1; mm <= 12; mm++) mArr2.push({ v: mm, t: mm + '月' });
      cols.push({ key: 'm', items: mArr2, idx: m - 1 });
      var dm = daysInMonth(y, m), dArr2 = [], dd;
      for (dd = 1; dd <= dm; dd++) dArr2.push({ v: dd, t: dd + '日' });
      cols.push({ key: 'd', items: dArr2, idx: Math.min(d, dm) - 1 });
    }
    var hArr = [], miArr = [], h, mi;
    for (h = 0; h < 24; h++) hArr.push({ v: h, t: h + '时' });
    for (mi = 0; mi < 60; mi++) miArr.push({ v: mi, t: f2(mi) + '分' });
    cols.push({ key: 'h', items: hArr, idx: p[3] });
    cols.push({ key: 'mi', items: miArr, idx: p[4] });
    return cols;
  }

  function markSel(col, idx) {
    var items = col.querySelectorAll('.wi'), i;
    for (i = 0; i < items.length; i++) items[i].classList.toggle('sel', i === idx);
  }

  function renderWheel() {
    COLS = buildCols();
    var w = q('wheel');
    if (!w) { syncSelects(); return; }
    var html = '', i, j;
    for (i = 0; i < COLS.length; i++) {
      html += '<div class="wcol" data-i="' + i + '"><div class="pad"></div>';
      for (j = 0; j < COLS[i].items.length; j++) {
        html += '<div class="wi">' + COLS[i].items[j].t + '</div>';
      }
      html += '<div class="pad"></div></div>';
    }
    w.innerHTML = html;
    var one = w.querySelector('.wi');
    ITEM = one ? one.offsetHeight || 42 : 42;
    wlock = true;
    var cols = w.querySelectorAll('.wcol');
    for (i = 0; i < cols.length; i++) {
      cols[i].scrollTop = COLS[i].idx * ITEM;
      markSel(cols[i], COLS[i].idx);
    }
    setTimeout(function () { wlock = false; }, 80);
    syncSelects();
  }

  /* ---- 时间行：五个下拉框，与滚轮同源于 COLS ---- */
  function fillSel(sel, items, idx, fmt) {
    if (!sel) return;
    var h = '', i;
    for (i = 0; i < items.length; i++) h += '<option value="' + i + '">' + fmt(items[i], i) + '</option>';
    sel.innerHTML = h;
    sel.value = String(idx);
  }
  function syncSelects() {
    if (!COLS.length || !q('fy')) return;
    var lunar = S.mode === 'lunar';
    var pnl = q('panel'); if (pnl) pnl.classList.toggle('lunar', lunar);
    fillSel(q('fy'), COLS[0].items, COLS[0].idx, function (it) { return it.v + '年'; });
    fillSel(q('fm'), COLS[1].items, COLS[1].idx, function (it) {
      return lunar ? it.t : it.v + '月';
    });
    fillSel(q('fd'), COLS[2].items, COLS[2].idx, function (it) {
      return lunar ? it.t : it.v + '日';
    });
    fillSel(q('fh'), COLS[3].items, COLS[3].idx, function (it) {
      return it.v + '-' + ZHI[Math.floor(((it.v + 1) % 24) / 2)] + '时';
    });
    fillSel(q('fmi'), COLS[4].items, COLS[4].idx, function (it) { return it.v + '分'; });
  }
  function bindSel(id, i) {
    var el = q(id);
    if (!el) return;
    el.onchange = function () {
      COLS[i].idx = +this.value;
      applyWheel();
      if (i <= 1) renderWheel(); else { renderBirthText(); syncSelects(); }
    };
  }

  function applyWheel() {
    // 时分也以滚轮／下拉框的选点为准（旧码取 parts()，改了时／分不生效）
    var h = COLS[3].items[COLS[3].idx].v, mi = COLS[4].items[COLS[4].idx].v;
    var y, m, d, sol;
    if (S.mode === 'lunar') {
      var ly = COLS[0].items[COLS[0].idx].v;
      var mo = COLS[1].items[COLS[1].idx];
      var ld = COLS[2].items[COLS[2].idx].v;
      sol = lunarToSolar(ly, mo.m, mo.leap, ld);
      if (sol) S.base = D(sol.getUTCFullYear(), sol.getUTCMonth() + 1, sol.getUTCDate(), h, mi);
    } else {
      y = COLS[0].items[COLS[0].idx].v;
      m = COLS[1].items[COLS[1].idx].v;
      d = COLS[2].items[COLS[2].idx].v;
      setBase(y, m, d, h, mi);
    }
    renderBirthText();
    autoChart();
  }

  function renderBirthText() {
    var p = parts(), el = q('fBirth');
    if (!el) return;
    var eff = (S.tst && S.lon !== null) ? trueSolar(S.base, S.lon) : S.base;
    var lun = solarToLunar(S.base);
    var zhiC = ZHI[Math.floor(((S.base.getUTCHours() + 1) % 24) / 2)];
    var SEP = ' · ';
    var t;
    if (S.mode === 'lunar' && lun) {
      // 农历输入：时刻以时辰显示，紧贴日期不加空格（2026-11-01 五十五令）
      t = cnYear(lun.y) + '年' + lunarText(lun) + zhiC + '时' +
        SEP + '公历 ' + p[0] + '年' + p[1] + '月' + p[2] + '日';
    } else {
      t = p[0] + '年' + p[1] + '月' + p[2] + '日 ' + f2(p[3]) + ':' + f2(p[4]) +
        (lun ? SEP + '农历' + lunarText(lun) + zhiC + '时' : '');
    }
    if (S.tst && S.lon !== null) {
      t += SEP + '真太阳时 ' + f2(eff.getUTCHours()) + ':' + f2(eff.getUTCMinutes());
    }
    el.textContent = t;
  }

  function onWheelScroll(e) {
    var col = e.target;
    if (!col || !col.classList || !col.classList.contains('wcol') || wlock) return;
    var i = +col.getAttribute('data-i');
    var idx = Math.round(col.scrollTop / ITEM);
    idx = Math.max(0, Math.min(COLS[i].items.length - 1, idx));
    if (COLS[i].idx === idx) return;
    COLS[i].idx = idx;
    markSel(col, idx);
    clearTimeout(wtimer);
    wtimer = setTimeout(function () {
      var rebuild = (i <= 1);
      applyWheel();
      if (rebuild) renderWheel(); else { renderBirthText(); syncSelects(); }
    }, 130);
  }

  /* 八十八令（2026-11-01）：长州郡名展示端缩短——「克孜勒苏柯尔克孜自治州」→「克孜勒苏」，
     「西双版纳傣族自治州」→「西双版纳」。只缩短下拉显示文字，S.placeName 仍存全名。
     规则：去尾缀（自治州／地区／盟／市），再循环去尾端民族段；check.py 以同一规则
     对 348 市复算断言「缩短后 ≤4 字」，与下拉框宽 103u 互为表里。 */
  function shortCity(n) {
    n = n.replace(/(自治州|地区|盟|市)$/, '');
    var prev;
    do {
      prev = n;
      n = n.replace(/(蒙古族?|藏族?|回族?|彝族?|白族?|傣族?|苗族?|侗族?|壮族?|土家族?|朝鲜族?|哈萨克族?|哈尼族?|傈僳族?|景颇族?|布依族?|柯尔克孜|仡佬族?|羌族?|维吾尔族?)$/, '');
    } while (n !== prev);
    return n;
  }
  function fillCity(pi, selName) {
    var sel = q('fCity');
    if (!sel) return;
    sel.innerHTML = pi < 0 ? '<option value="">地级市</option>'
      : '<option value="">地级市</option>' + PROVS[pi][1].map(function (c, i) {
        return '<option value="' + i + '">' + shortCity(c[0]) + '</option>'; }).join('');
    if (pi >= 0 && selName) {
      for (var i = 0; i < PROVS[pi][1].length; i++) {
        if (PROVS[pi][1][i][0] === selName) { sel.value = String(i); S.city = i; }
      }
    }
  }
  function renderPlace() {
    var el = q('fPlace');
    if (!el) return;
    if (S.lon === null) {
      el.innerHTML = '可不选（选择后使用真太阳时）<span class="ar">›</span>';
    } else {
      var nm = S.prov >= 0 && S.placeName ? PROVS[S.prov][0] + ' · ' + S.placeName : (S.placeName || '自定义');
      var geo = '东经 ' + S.lon.toFixed(2) + '°' +
        (S.lat !== null && S.lat !== undefined ? ' · 北纬 ' + S.lat.toFixed(2) + '°' : '');
      el.innerHTML = nm + '（' + geo + '）' +
        (S.tst ? ' · 真太阳时' + (S.lat !== null && S.lat !== undefined ? '·古法' : '') : '') +
        '<span class="ar">›</span>';
    }
  }

  function buildRev() {
    var ids = ['rvY', 'rvM', 'rvD', 'rvH'], i, a, b;
    for (i = 0; i < 4; i++) {
      var g1 = q(ids[i] + 'g'), z1 = q(ids[i] + 'z');
      if (!g1) continue;
      var gh = '', zh = '';
      for (a = 0; a < 10; a++) gh += '<option value="' + a + '">' + GAN.charAt(a) + '</option>';
      for (b = 0; b < 12; b++) zh += '<option value="' + b + '">' + ZHI.charAt(b) + '</option>';
      g1.innerHTML = gh; z1.innerHTML = zh;
    }
    var d = CHART && CHART.d;
    if (d) {
      for (i = 0; i < 4; i++) {
        var gg = q(ids[i] + 'g'), zz = q(ids[i] + 'z');
        if (gg) gg.value = String(GAN.indexOf(d.pillars[i].gan));
        if (zz) zz.value = String(ZHI.indexOf(d.pillars[i].zhi));
      }
    }
  }

  function doReverse() {
    var ids = ['rvY', 'rvM', 'rvD', 'rvH'], want = [], i;
    for (i = 0; i < 4; i++) {
      var gi = +q(ids[i] + 'g').value, zi = +q(ids[i] + 'z').value;
      if (mod(gi - zi, 2) !== 0) { want = null; break; }
      want.push(gzOf(gi, zi));
    }
    var box = q('revHits');
    if (!want) { box.innerHTML = '<span class="none">干支阴阳不配，请重选</span>'; return; }
    var hits = reverse(want, g.Bazi.range.y0, g.Bazi.range.y1);
    if (!hits.length) { box.innerHTML = '<span class="none">未找到匹配日期</span>'; return; }
    box.innerHTML = '';
    // 倒序（2026-11-01 令）：最近的年份排在前
    hits.sort(function (a, b) { return b - a; }).slice(0, 24).forEach(function (dt) {
      var btn = document.createElement('button');
      btn.textContent = dt.getUTCFullYear() + '-' + f2(dt.getUTCMonth() + 1) + '-' +
        f2(dt.getUTCDate()) + ' ' + f2(dt.getUTCHours()) + ':' + f2(dt.getUTCMinutes());
      btn.onclick = function () { S.base = dt; setMode('solar'); };
      box.appendChild(btn);
    });
  }

  function setMode(mode) {
    if (mode === 'lunar') {
      var yy = S.base.getUTCFullYear();
      if (yy < 1900 || yy > 2100) {   // 九十三年令：古代不接受农历「输入」，仅按公历填后显示年号
        mode = 'solar';
        toast('农历表仅 1900–2100 年可用');
      }
    }
    S.mode = mode;
    ['solar', 'lunar', 'rev'].forEach(function (k) {
      var b = q('tab-' + k);
      if (b) b.classList.toggle('on', k === mode);
    });
    var wv = q('wheel'); if (wv) wv.style.display = mode === 'rev' ? 'none' : '';
    var rv = q('rev');
    rv.classList.toggle('on', mode === 'rev');
    /* 反推区在该节内多占一行：标题须跨 3 行居中（关时 2 行）。用类而非 :has()，兼容面更宽 */
    if (rv.parentNode && rv.parentNode.classList) {
      rv.parentNode.classList.toggle('hasrev', mode === 'rev');
    }
    if (mode === 'rev') buildRev(); else renderWheel();
    renderBirthText();
    autoChart();
    if (typeof fitRows === 'function') fitRows();
  }

  function doChart() {
    var d = paipan({ birth: S.base, gender: S.gender, name: S.name, now: S.now,
      trueSolar: S.tst, lon: S.lon, lat: S.lat, focus: S.focus, steps: 12 });
    renderChart(d, FOOT);
  }
  /* 顶部一改即自动重排（2026-11-01 令：去掉「排盘」按钮），90ms 防抖免连打字狂排 */
  var autot = null, booted = false;
  function autoChart() {
    if (!booted) return;
    clearTimeout(autot);
    autot = setTimeout(doChart, 90);
  }

  function hidePlaceBox() { var b = q('placeBox'); if (b) b.hidden = true; }
  function shiftYear(n) {
    var p = parts();
    var y = Math.max(g.Bazi.range.y0, Math.min(g.Bazi.range.y1, p[0] + n));
    setBase(y, p[1], p[2], p[3], p[4]);
    renderWheel(); renderBirthText();
  }
  function setSex(v) {
    S.gender = v;
    document.querySelectorAll('#fSex button').forEach(function (b) {
      b.classList.toggle('on', b.getAttribute('data-v') === v);
    });
    autoChart();
  }
  function parseText() {
    if (!q('fText')) return;
    var t = q('fText').value.replace(/[^\d]/g, '');
    if (t.length < 8) { q('fText').value = '格式示例：200106180759'; return; }
    var y = +t.substr(0, 4), mo = +t.substr(4, 2), d = +t.substr(6, 2);
    var h = t.length >= 10 ? +t.substr(8, 2) : 0, mi = t.length >= 12 ? +t.substr(10, 2) : 0;
    if (!(y >= g.Bazi.range.y0 && y <= g.Bazi.range.y1) || !(mo >= 1 && mo <= 12) ||
      !(d >= 1 && d <= 31)) { q('fText').value = '日期不合法'; return; }
    setBase(y, mo, d, Math.min(h, 23), Math.min(mi, 59));
    renderWheel(); renderBirthText();
  }

  function boot(init) {
    FOOT = init.foot || '';
    S.live = !!init.live;
    var nb0 = new Date();
    S.base = S.live
      ? D(nb0.getFullYear(), nb0.getMonth() + 1, nb0.getDate(), nb0.getHours(), nb0.getMinutes())
      : D(init.birth[0], init.birth[1], init.birth[2], init.birth[3], init.birth[4]);
    S.gender = init.gender || 'male';
    S.name = init.name || '';
    S.now = S.live ? new Date() : (init.now ? D(init.now[0], init.now[1], init.now[2], 12, 0) : new Date());
    S.focus = init.focus || null;
    S.lon = (init.lon === null || init.lon === undefined) ? null : init.lon;
    S.lat = (init.lat === null || init.lat === undefined) ? null : init.lat;
    S.tst = !!init.tst;
    S.placeName = init.place || '';

    q('fName').value = S.name;
    setSex(S.gender);
    renderPlace();
    renderBirthText();

    document.querySelectorAll('#fSex button').forEach(function (b) {
      b.onclick = function () { setSex(b.getAttribute('data-v')); };
    });
    q('fold').onclick = function () {
      var cl = q('panel').classList.toggle('closed');
      q('fold').querySelector('.ft').textContent = cl ? '展开信息' : '收起信息';
    };
    q('fName').oninput = function () { S.name = this.value.trim(); autoChart(); };
    q('fProv').innerHTML = '<option value="">省份</option>' + PROVS.map(function (p, i) {
      return '<option value="' + i + '">' + p[0] + '</option>';
    }).join('');
    fillCity(-1);
    if (S.placeName) {
      var pi = provOf(S.placeName);
      if (pi >= 0) {
        S.prov = pi; q('fProv').value = String(pi);
        fillCity(pi, S.placeName);
      }
    }
    var _fp = q('fPlace');
    if (_fp) _fp.onclick = function () { var b = q('placeBox'); if (b) b.hidden = !b.hidden; };
    q('fProv').onchange = function () {
      S.prov = this.value === '' ? -1 : +this.value;
      // D88：换省必须清空上一省残留的经纬度与地名，否则真太阳时继续沿用旧省经度（算错）
      S.city = -1; S.lon = null; S.lat = null; S.placeName = '';
      q('fLon').value = ''; if (q('fLat')) q('fLat').value = '';
      // 第一百零三令（D100）：经纬一清，真太阳时便无从计算。勾选状态必须同步取消，
      // 否则界面仍显示「真太阳时」已开，实际按平太阳时排——静默失效，与 D88 同类。
      if (q('fTst').checked) {
        q('fTst').checked = false; S.tst = false;
        toast('出生地已清除，真太阳时一并取消');
      }
      fillCity(S.prov);
      renderPlace(); renderBirthText(); autoChart();
    };
    q('fCity').onchange = function () {
      if (this.value === '') {
        // D88：取消选市同样清空经纬度，避免沿用已选市的经度
        S.city = -1; S.lon = null; S.lat = null; S.placeName = '';
        q('fLon').value = ''; if (q('fLat')) q('fLat').value = '';
        if (q('fTst').checked) {          // 同上：取消选市亦须取消真太阳时
          q('fTst').checked = false; S.tst = false;
          toast('出生地已清除，真太阳时一并取消');
        }
        renderPlace(); renderBirthText(); autoChart();
        return;
      }
      var c = PROVS[S.prov][1][+this.value];
      S.city = +this.value;
      S.placeName = c[0]; S.lon = c[1]; S.lat = c[2];
      q('fLon').value = c[1];
      if (q('fLat')) q('fLat').value = c[2];
      q('fTst').checked = true; S.tst = true;
      renderPlace(); renderBirthText(); autoChart();
    };
    q('fLon').oninput = function () {
      var v = parseFloat(this.value);
      S.lon = isFinite(v) ? v : null;
      if (isFinite(v) && !S.placeName) S.placeName = '自定义';
      renderPlace(); renderBirthText(); autoChart();
    };
    if (q('fLat')) q('fLat').oninput = function () {
      var v = parseFloat(this.value);
      S.lat = isFinite(v) ? v : null;
      renderPlace(); renderBirthText(); autoChart();
    };
    q('fTst').onchange = function () {
      S.tst = this.checked;
      // D88：勾选真太阳时却无经度时明确告知（否则静默按平太阳时，用户误以为已校正）
      if (S.tst && S.lon === null) toast('真太阳时需先选城市或填写经度，暂按平太阳时');
      renderPlace(); renderBirthText(); autoChart();
    };

    q('tab-solar').onclick = function () { setMode('solar'); };
    q('tab-lunar').onclick = function () { setMode('lunar'); };
    q('tab-rev').onclick = function () { setMode('rev'); };
    if (q('m10')) q('m10').onclick = function () { shiftYear(-10); };
    if (q('p10')) q('p10').onclick = function () { shiftYear(10); };
    if (q('nowBtn')) q('nowBtn').onclick = resetNow;
    q('revGo').onclick = doReverse;
    bindSel('fy', 0); bindSel('fm', 1); bindSel('fd', 2); bindSel('fh', 3); bindSel('fmi', 4);
    if (q('wheel')) q('wheel').addEventListener('scroll', onWheelScroll, true);

    setMode('solar');
    doChart();
    booted = true;
  }
  function resetNow() {
    var n = new Date();
    S.base = D(n.getFullYear(), n.getMonth() + 1, n.getDate(), n.getHours(), n.getMinutes());
    renderWheel(); renderBirthText(); autoChart();
  }

  g.Bazi.boot = boot;
  g.Bazi.state = S;
  g.Bazi.setMode = setMode;
  g.Bazi.doChart = doChart;
  g.Bazi.doReverse = doReverse;
  document.addEventListener('DOMContentLoaded', function () {
    if (g.BAZI_INIT) boot(g.BAZI_INIT);
  });
})(typeof window !== 'undefined' ? window : globalThis);
