# -*- coding: utf-8 -*-
"""
生成监控数据可视化 Dashboard HTML。
自包含单文件，Chart.js CDN 加载图表，数据内嵌 JSON。
支持五个板块：考生之家、招教网（四川）、招教网（福建）、招教网（重庆）、招教网（广东）。
"""

import json
import os
from datetime import datetime, date


def build(bm_active, bm_closed, zj_sc_entries, zj_fj_entries,
          zj_cq_entries=None, zj_gd_entries=None, output_path="dashboard.html"):
    """生成 dashboard.html。

    bm_active: 考生之家进行中/即将开始的条目列表
    bm_closed: 考生之家已结束的条目列表
    zj_sc_entries: 招教网（四川）全部条目列表
    zj_fj_entries: 招教网（福建）全部条目列表
    zj_cq_entries: 招教网（重庆）全部条目列表
    zj_gd_entries: 招教网（广东）全部条目列表
    """
    if zj_cq_entries is None:
        zj_cq_entries = []
    if zj_gd_entries is None:
        zj_gd_entries = []

    bm_data = {
        "active": bm_active,
        "closed": bm_closed,
    }

    def _zj_stats(entries):
        cities = {}
        bianzhi = {"编制": 0, "编外": 0, "选调": 0, "未知": 0}
        daily = {}
        for e in entries:
            c = e.get("city") or "其他"
            cities[c] = cities.get(c, 0) + 1
            bz = e.get("bianzhi", "未知")
            bianzhi[bz] = bianzhi.get(bz, 0) + 1
            d = e.get("date", "")
            if d and d != "热门推荐":
                daily[d] = daily.get(d, 0) + 1
        return {
            "total": len(entries),
            "cities": dict(sorted(cities.items(), key=lambda x: -x[1])),
            "bianzhi": bianzhi,
            "daily": sorted(daily.items()),
        }

    sc_stats = _zj_stats(zj_sc_entries)
    fj_stats = _zj_stats(zj_fj_entries)
    cq_stats = _zj_stats(zj_cq_entries)
    gd_stats = _zj_stats(zj_gd_entries)

    global_stats = {
        "total_bm_active": len(bm_active),
        "total_bm_closed": len(bm_closed),
        "total_zj_sc": sc_stats["total"],
        "total_zj_fj": fj_stats["total"],
        "total_zj_cq": cq_stats["total"],
        "total_zj_gd": gd_stats["total"],
        "sc_city_count": len(sc_stats["cities"]),
        "fj_city_count": len(fj_stats["cities"]),
        "cq_city_count": len(cq_stats["cities"]),
        "gd_city_count": len(gd_stats["cities"]),
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    html = _render_html(
        bm_json=json.dumps(bm_data, ensure_ascii=False),
        zj_sc_json=json.dumps(zj_sc_entries, ensure_ascii=False),
        zj_fj_json=json.dumps(zj_fj_entries, ensure_ascii=False),
        zj_cq_json=json.dumps(zj_cq_entries, ensure_ascii=False),
        zj_gd_json=json.dumps(zj_gd_entries, ensure_ascii=False),
        sc_stats_json=json.dumps(sc_stats, ensure_ascii=False),
        fj_stats_json=json.dumps(fj_stats, ensure_ascii=False),
        cq_stats_json=json.dumps(cq_stats, ensure_ascii=False),
        gd_stats_json=json.dumps(gd_stats, ensure_ascii=False),
        global_stats_json=json.dumps(global_stats, ensure_ascii=False),
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return os.path.abspath(output_path)


def _render_html(bm_json, zj_sc_json, zj_fj_json, zj_cq_json, zj_gd_json,
                 sc_stats_json, fj_stats_json, cq_stats_json, gd_stats_json,
                 global_stats_json):
    return R"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>招聘监控 Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {
  --bg: #f5f7fa; --card: #fff; --text: #2c3e50; --muted: #7f8c8d;
  --border: #e0e4e8; --accent: #3498db; --red: #e74c3c; --green: #27ae60;
  --orange: #f39c12; --purple: #8e44ad; --sc-color: #e67e22; --fj-color: #1abc9c;
  --cq-color: #9b59b6; --gd-color: #e74c3c;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }
header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: #fff; padding: 24px 32px; }
header h1 { font-size: 24px; margin-bottom: 4px; }
header .sub { color: #a0aec0; font-size: 14px; }
.stats-row { display: flex; gap: 16px; padding: 24px 32px; flex-wrap: wrap; }
.stat-card { background: var(--card); border-radius: 12px; padding: 20px 24px; flex: 1; min-width: 140px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.stat-card .num { font-size: 32px; font-weight: 700; }
.stat-card .label { color: var(--muted); font-size: 13px; margin-top: 4px; }
.stat-card.c1 .num { color: var(--accent); }
.stat-card.c2 .num { color: var(--green); }
.stat-card.c3 .num { color: var(--sc-color); }
.stat-card.c4 .num { color: var(--fj-color); }
.stat-card.c5 .num { color: var(--purple); }
.stat-card.c6 .num { color: var(--red); }
.stat-card.c7 .num { color: var(--cq-color); }
.stat-card.c8 .num { color: var(--gd-color); }
.tabs { display: flex; gap: 0; padding: 0 32px; border-bottom: 2px solid var(--border); }
.tab-btn { padding: 12px 24px; border: none; background: none; cursor: pointer; font-size: 15px; color: var(--muted); border-bottom: 2px solid transparent; margin-bottom: -2px; transition: all 0.2s; }
.tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }
.tab-btn:hover { color: var(--text); }
.tab-content { display: none; padding: 24px 32px; }
.tab-content.active { display: block; }
.charts-row { display: grid; grid-template-columns: 2fr 1fr; gap: 24px; margin-bottom: 24px; }
.charts-row-2 { display: grid; grid-template-columns: 1fr; gap: 24px; margin-bottom: 24px; }
.chart-box { background: var(--card); border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.chart-box h3 { font-size: 15px; margin-bottom: 16px; color: var(--text); }
.filters { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; }
.filters input { padding: 8px 14px; border: 1px solid var(--border); border-radius: 8px; font-size: 14px; width: 260px; outline: none; }
.filters input:focus { border-color: var(--accent); }
.filter-btns { display: flex; gap: 6px; }
.filter-btn { padding: 6px 14px; border: 1px solid var(--border); border-radius: 20px; background: var(--card); cursor: pointer; font-size: 13px; transition: all 0.2s; white-space: nowrap; }
.filter-btn:hover { border-color: var(--accent); }
.filter-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.filter-btn.city-btn { padding: 4px 10px; font-size: 12px; }
.filter-btn.city-btn.active { background: var(--green); border-color: var(--green); }
.city-filters { display: grid; grid-template-columns: repeat(9, auto); gap: 6px; justify-content: start; }
.city-filters-4col { grid-template-columns: repeat(4, auto); }
.table-wrap { background: var(--card); border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.table-scroll { max-height: 70vh; overflow-y: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { background: #f8f9fb; padding: 12px 16px; text-align: left; font-weight: 600; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid var(--border); position: sticky; top: 0; z-index: 1; }
td { padding: 10px 16px; border-bottom: 1px solid var(--border); }
tr:hover td { background: #f8f9fb; }
.table-info { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; font-size: 13px; color: var(--muted); border-bottom: 1px solid var(--border); }
.page-btns { display: flex; gap: 4px; }
.page-btn { padding: 4px 10px; border: 1px solid var(--border); border-radius: 4px; background: var(--card); cursor: pointer; font-size: 12px; }
.page-btn:hover { background: #f0f0f0; }
.page-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
.badge-biannei { background: #d4efdf; color: #1e8449; }
.badge-bianwai { background: #fadbd8; color: #c0392b; }
.badge-xuandiao { background: #d6eaf8; color: #2471a3; }
.badge-unknown { background: #eaecee; color: #7f8c8d; }
.badge-hot { background: #fdedec; color: #e74c3c; }
.bm-card { background: var(--card); border-radius: 12px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border-left: 4px solid var(--accent); }
.bm-card.ending { border-left-color: var(--red); }
.bm-card .bm-title { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
.bm-card .bm-meta { color: var(--muted); font-size: 13px; }
.bm-card .bm-meta span { margin-right: 16px; }
.bm-card .countdown { display: inline-block; padding: 4px 12px; border-radius: 6px; font-weight: 600; font-size: 13px; }
.countdown.urgent { background: #fadbd8; color: #c0392b; }
.countdown.warn { background: #fef9e7; color: #b7950b; }
.countdown.ok { background: #d5f5e3; color: #1e8449; }
.no-results { text-align: center; padding: 40px; color: var(--muted); }
footer { text-align: center; padding: 24px; color: var(--muted); font-size: 12px; }
@media (max-width: 768px) {
  .charts-row { grid-template-columns: 1fr; }
  .stats-row { padding: 16px; }
  .tabs, .tab-content { padding-left: 16px; padding-right: 16px; }
}
</style>
</head>
<body>

<header>
  <h1>📊 招聘监控 Dashboard</h1>
  <div class="sub">考生之家 + 招教网（四川 + 福建 + 重庆 + 广东）· 数据更新于 <span id="updateTime"></span></div>
</header>

<div class="stats-row" id="statsRow"></div>

<div class="tabs">
  <button class="tab-btn active" onclick="switchTab('bm')">🏫 考生之家</button>
  <button class="tab-btn" onclick="switchTab('zj-sc')">🎓 招教网（四川）</button>
  <button class="tab-btn" onclick="switchTab('zj-fj')">🎓 招教网（福建）</button>
  <button class="tab-btn" onclick="switchTab('zj-cq')">🎓 招教网（重庆）</button>
  <button class="tab-btn" onclick="switchTab('zj-gd')">🎓 招教网（广东）</button>
</div>

<!-- 考生之家 -->
<div class="tab-content active" id="tab-bm">
  <div class="charts-row-2">
    <div class="chart-box"><h3>📅 报名项目时间线</h3><div id="bmTimeline"></div></div>
  </div>
</div>

<!-- 招教网（四川） -->
<div class="tab-content" id="tab-zj-sc">
  <div class="charts-row">
    <div class="chart-box"><h3>🏙 城市分布</h3><canvas id="chartScCity"></canvas></div>
    <div class="chart-box"><h3>📌 编制类型</h3><canvas id="chartScBianzhi"></canvas></div>
  </div>
  <div class="charts-row">
    <div class="chart-box"><h3>📈 每日新增</h3><canvas id="chartScDaily"></canvas></div>
  </div>
  <div class="filters">
    <input type="text" id="zjScSearch" placeholder="🔍 搜索标题..." oninput="pageSc=1;renderZjScTable()">
    <div class="filter-btns" id="scBzFilters"></div>
  </div>
  <div class="filters" style="margin-bottom:16px">
    <span style="font-size:13px;color:var(--muted);margin-right:4px;line-height:28px">🏙</span>
    <div class="city-filters city-filters-4col" id="scCityFilters"></div>
  </div>
  <div class="table-wrap">
    <div class="table-info">
      <span id="zjScTableInfo">加载中...</span>
      <div class="page-btns" id="zjScPages"></div>
    </div>
    <div class="table-scroll">
      <table id="zjScTable"><thead><tr><th>编制</th><th>城市</th><th>标题</th><th>人数</th><th>日期</th></tr></thead><tbody></tbody></table>
    </div>
  </div>
  <div class="no-results" id="zjScNoResults" style="display:none">没有匹配的结果</div>
</div>

<!-- 招教网（福建） -->
<div class="tab-content" id="tab-zj-fj">
  <div class="charts-row">
    <div class="chart-box"><h3>🏙 城市分布</h3><canvas id="chartFjCity"></canvas></div>
    <div class="chart-box"><h3>📌 编制类型</h3><canvas id="chartFjBianzhi"></canvas></div>
  </div>
  <div class="charts-row">
    <div class="chart-box"><h3>📈 每日新增</h3><canvas id="chartFjDaily"></canvas></div>
  </div>
  <div class="filters">
    <input type="text" id="zjFjSearch" placeholder="🔍 搜索标题..." oninput="pageFj=1;renderZjFjTable()">
    <div class="filter-btns" id="fjBzFilters"></div>
  </div>
  <div class="filters" style="margin-bottom:16px">
    <span style="font-size:13px;color:var(--muted);margin-right:4px;line-height:28px">🏙</span>
    <div class="city-filters" id="fjCityFilters"></div>
  </div>
  <div class="table-wrap">
    <div class="table-info">
      <span id="zjFjTableInfo">加载中...</span>
      <div class="page-btns" id="zjFjPages"></div>
    </div>
    <div class="table-scroll">
      <table id="zjFjTable"><thead><tr><th>编制</th><th>城市</th><th>标题</th><th>人数</th><th>日期</th></tr></thead><tbody></tbody></table>
    </div>
  </div>
  <div class="no-results" id="zjFjNoResults" style="display:none">没有匹配的结果</div>
</div>

<!-- 招教网（重庆） -->
<div class="tab-content" id="tab-zj-cq">
  <div class="charts-row">
    <div class="chart-box"><h3>🏙 城市分布</h3><canvas id="chartCqCity"></canvas></div>
    <div class="chart-box"><h3>📌 编制类型</h3><canvas id="chartCqBianzhi"></canvas></div>
  </div>
  <div class="charts-row">
    <div class="chart-box"><h3>📈 每日新增</h3><canvas id="chartCqDaily"></canvas></div>
  </div>
  <div class="filters">
    <input type="text" id="zjCqSearch" placeholder="🔍 搜索标题..." oninput="pageCq=1;renderZjCqTable()">
    <div class="filter-btns" id="cqBzFilters"></div>
  </div>
  <div class="filters" style="margin-bottom:16px">
    <span style="font-size:13px;color:var(--muted);margin-right:4px;line-height:28px">🏙</span>
    <div class="city-filters" id="cqCityFilters"></div>
  </div>
  <div class="table-wrap">
    <div class="table-info">
      <span id="zjCqTableInfo">加载中...</span>
      <div class="page-btns" id="zjCqPages"></div>
    </div>
    <div class="table-scroll">
      <table id="zjCqTable"><thead><tr><th>编制</th><th>城市</th><th>标题</th><th>人数</th><th>日期</th></tr></thead><tbody></tbody></table>
    </div>
  </div>
  <div class="no-results" id="zjCqNoResults" style="display:none">没有匹配的结果</div>
</div>

<!-- 招教网（广东） -->
<div class="tab-content" id="tab-zj-gd">
  <div class="charts-row">
    <div class="chart-box"><h3>🏙 城市分布</h3><canvas id="chartGdCity"></canvas></div>
    <div class="chart-box"><h3>📌 编制类型</h3><canvas id="chartGdBianzhi"></canvas></div>
  </div>
  <div class="charts-row">
    <div class="chart-box"><h3>📈 每日新增</h3><canvas id="chartGdDaily"></canvas></div>
  </div>
  <div class="filters">
    <input type="text" id="zjGdSearch" placeholder="🔍 搜索标题..." oninput="pageGd=1;renderZjGdTable()">
    <div class="filter-btns" id="gdBzFilters"></div>
  </div>
  <div class="filters" style="margin-bottom:16px">
    <span style="font-size:13px;color:var(--muted);margin-right:4px;line-height:28px">🏙</span>
    <div class="city-filters" id="gdCityFilters"></div>
  </div>
  <div class="table-wrap">
    <div class="table-info">
      <span id="zjGdTableInfo">加载中...</span>
      <div class="page-btns" id="zjGdPages"></div>
    </div>
    <div class="table-scroll">
      <table id="zjGdTable"><thead><tr><th>编制</th><th>城市</th><th>标题</th><th>人数</th><th>日期</th></tr></thead><tbody></tbody></table>
    </div>
  </div>
  <div class="no-results" id="zjGdNoResults" style="display:none">没有匹配的结果</div>
</div>

<footer>招聘监控 Dashboard | 本地版</footer>

<script type="application/json" id="bm-data">""" + bm_json + R"""</script>
<script type="application/json" id="zj-sc-data">""" + zj_sc_json + R"""</script>
<script type="application/json" id="zj-fj-data">""" + zj_fj_json + R"""</script>
<script type="application/json" id="zj-cq-data">""" + zj_cq_json + R"""</script>
<script type="application/json" id="zj-gd-data">""" + zj_gd_json + R"""</script>
<script type="application/json" id="sc-stats">""" + sc_stats_json + R"""</script>
<script type="application/json" id="fj-stats">""" + fj_stats_json + R"""</script>
<script type="application/json" id="cq-stats">""" + cq_stats_json + R"""</script>
<script type="application/json" id="gd-stats">""" + gd_stats_json + R"""</script>
<script type="application/json" id="global-stats">""" + global_stats_json + R"""</script>
<script>
(function() {
  // Data
  var BM_DATA = JSON.parse(document.getElementById('bm-data').textContent);
  var ZJ_SC_DATA = JSON.parse(document.getElementById('zj-sc-data').textContent);
  var ZJ_FJ_DATA = JSON.parse(document.getElementById('zj-fj-data').textContent);
  var ZJ_CQ_DATA = JSON.parse(document.getElementById('zj-cq-data').textContent);
  var ZJ_GD_DATA = JSON.parse(document.getElementById('zj-gd-data').textContent);
  var SC_STATS = JSON.parse(document.getElementById('sc-stats').textContent);
  var FJ_STATS = JSON.parse(document.getElementById('fj-stats').textContent);
  var CQ_STATS = JSON.parse(document.getElementById('cq-stats').textContent);
  var GD_STATS = JSON.parse(document.getElementById('gd-stats').textContent);
  var GLOBAL = JSON.parse(document.getElementById('global-stats').textContent);

  // Chart rendering state — track per-tab
  var renderedCharts = { bm: false, sc: false, fj: false, cq: false, gd: false };

  // Per-tab filter state
  var activeBzSc = null, activeCitySc = null, pageSc = 1;
  var activeBzFj = null, activeCityFj = null, pageFj = 1;
  var activeBzCq = null, activeCityCq = null, pageCq = 1;
  var activeBzGd = null, activeCityGd = null, pageGd = 1;
  var PAGE_SIZE = 30;

  document.getElementById('updateTime').textContent = GLOBAL.updated;
  renderStats();
  renderBmTab();
  initZJTab('sc');
  initZJTab('fj');
  initZJTab('cq');
  initZJTab('gd');

  // Stats cards
  function renderStats() {
    var row = document.getElementById('statsRow');
    var g = GLOBAL;
    row.innerHTML =
      '<div class="stat-card c1"><div class="num">' + g.total_bm_active + '</div><div class="label">考生之家 · 进行中</div></div>' +
      '<div class="stat-card c6"><div class="num">' + g.total_bm_closed + '</div><div class="label">考生之家 · 已结束</div></div>' +
      '<div class="stat-card c3"><div class="num">' + g.total_zj_sc + '</div><div class="label">招教网 · 四川</div></div>' +
      '<div class="stat-card c4"><div class="num">' + g.total_zj_fj + '</div><div class="label">招教网 · 福建</div></div>' +
      '<div class="stat-card c7"><div class="num">' + g.total_zj_cq + '</div><div class="label">招教网 · 重庆</div></div>' +
      '<div class="stat-card c8"><div class="num">' + g.total_zj_gd + '</div><div class="label">招教网 · 广东</div></div>' +
      '<div class="stat-card c5"><div class="num">' + (g.sc_city_count + g.fj_city_count + g.cq_city_count + g.gd_city_count) + '</div><div class="label">覆盖城市</div></div>';
  }

  // BM tab
  function renderBmTab() {
    var container = document.getElementById('bmTimeline');
    var active = BM_DATA.active || [];
    var closed = BM_DATA.closed || [];
    var html = '';
    if (active.length === 0) {
      html += '<div class="no-results">暂无进行中的报名项目</div>';
    }
    active.forEach(function(e) {
      var isEnding = e.phase === 'ongoing' && e.remaining !== null && e.remaining <= 120;
      var cls = isEnding ? 'bm-card ending' : 'bm-card';
      var cd = '';
      if (e.remaining !== null) {
        var cdClass, cdText;
        if (e.remaining < 60) { cdText = e.remaining + '分钟'; cdClass = 'urgent'; }
        else if (e.remaining < 1440) { cdText = Math.floor(e.remaining / 60) + '小时'; cdClass = 'warn'; }
        else { cdText = Math.floor(e.remaining / 1440) + '天'; cdClass = 'ok'; }
        cd = '<span class="countdown ' + cdClass + '">⏳ ' + cdText + '</span>';
      }
      html += '<div class="' + cls + '">' +
        '<div class="bm-title">【' + (e.area || '') + '】' + e.name + ' ' + cd + '</div>' +
        '<div class="bm-meta">' +
        '<span>📅 ' + (e.start || '?') + ' ~ ' + (e.end || '?') + '</span>' +
        (e.pay_start ? '<span>💰 缴费 ' + e.pay_start + ' ~ ' + e.pay_end + '</span>' : '') +
        (e.phase === 'upcoming' ? '<span>⏳ 即将开始</span>' : '<span>🔴 报名中</span>') +
        '</div></div>';
    });
    if (closed.length > 0) {
      html += '<h4 style="margin:20px 0 12px;color:var(--muted)">📁 近期已结束 (' + closed.length + ')</h4>';
      closed.forEach(function(c) {
        html += '<div style="padding:6px 0;color:var(--muted);font-size:14px">· ' + c.name + '</div>';
      });
    }
    container.innerHTML = html;
  }

  // ====================================================================== //
  // ZJ tab helpers
  // ====================================================================== //
  function getZJData(key) {
    if (key === 'sc') return ZJ_SC_DATA;
    if (key === 'fj') return ZJ_FJ_DATA;
    if (key === 'cq') return ZJ_CQ_DATA;
    return ZJ_GD_DATA;
  }
  function getZJStats(key) {
    if (key === 'sc') return SC_STATS;
    if (key === 'fj') return FJ_STATS;
    if (key === 'cq') return CQ_STATS;
    return GD_STATS;
  }
  function getActiveBz(key) {
    if (key === 'sc') return activeBzSc;
    if (key === 'fj') return activeBzFj;
    if (key === 'cq') return activeBzCq;
    return activeBzGd;
  }
  function setActiveBz(key, v) {
    if (key === 'sc') activeBzSc = v;
    else if (key === 'fj') activeBzFj = v;
    else if (key === 'cq') activeBzCq = v;
    else activeBzGd = v;
  }
  function getActiveCity(key) {
    if (key === 'sc') return activeCitySc;
    if (key === 'fj') return activeCityFj;
    if (key === 'cq') return activeCityCq;
    return activeCityGd;
  }
  function setActiveCity(key, v) {
    if (key === 'sc') activeCitySc = v;
    else if (key === 'fj') activeCityFj = v;
    else if (key === 'cq') activeCityCq = v;
    else activeCityGd = v;
  }
  function getPage(key) {
    if (key === 'sc') return pageSc;
    if (key === 'fj') return pageFj;
    if (key === 'cq') return pageCq;
    return pageGd;
  }
  function setPage(key, v) {
    if (key === 'sc') pageSc = v;
    else if (key === 'fj') pageFj = v;
    else if (key === 'cq') pageCq = v;
    else pageGd = v;
  }
  function chartPrefix(key) {
    if (key === 'sc') return 'Sc';
    if (key === 'fj') return 'Fj';
    if (key === 'cq') return 'Cq';
    return 'Gd';
  }
  function tabLabel(key) {
    if (key === 'sc') return '四川';
    if (key === 'fj') return '福建';
    if (key === 'cq') return '重庆';
    return '广东';
  }

  function renderZJCharts(key) {
    if (renderedCharts[key]) return;
    renderedCharts[key] = true;
    var stats = getZJStats(key);
    var prefix = chartPrefix(key);
    var accentColor = key === 'sc' ? '#e67e22' : key === 'fj' ? '#1abc9c' : key === 'cq' ? '#9b59b6' : '#e74c3c';

    // City chart
    var cities = stats.cities;
    new Chart(document.getElementById('chart' + prefix + 'City'), {
      type: 'bar',
      data: { labels: Object.keys(cities), datasets: [{ label: '招聘数量', data: Object.values(cities), backgroundColor: accentColor, borderRadius: 4 }] },
      options: { indexAxis: 'y', responsive: true, plugins: { legend: { display: false } }, scales: { x: { ticks: { stepSize: 5 } } } }
    });

    // Bianzhi chart
    var bz = stats.bianzhi;
    new Chart(document.getElementById('chart' + prefix + 'Bianzhi'), {
      type: 'doughnut',
      data: { labels: ['编制', '编外', '选调', '未知'], datasets: [{ data: [bz['编制'], bz['编外'], bz['选调'], bz['未知']], backgroundColor: ['#27ae60', '#e74c3c', '#3498db', '#bdc3c7'], borderWidth: 0 }] },
      options: { responsive: true, plugins: { legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true } } } }
    });

    // Daily chart
    var daily = stats.daily;
    new Chart(document.getElementById('chart' + prefix + 'Daily'), {
      type: 'line',
      data: { labels: daily.map(function(d) { return d[0]; }), datasets: [{ label: '每日新增', data: daily.map(function(d) { return d[1]; }), borderColor: accentColor, backgroundColor: accentColor.replace(')', ',0.1)').replace('rgb', 'rgba'), fill: true, tension: 0.3, pointRadius: 4, pointBackgroundColor: accentColor }] },
      options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { ticks: { stepSize: 1 } } } }
    });
  }

  function initZJTab(key) {
    // BZ filter buttons
    (function() {
      var container = document.getElementById(key + 'BzFilters');
      ['全部', '编制', '编外', '选调', '未知'].forEach(function(t) {
        var btn = document.createElement('button');
        btn.className = 'filter-btn' + (t === '全部' ? ' active' : '');
        btn.textContent = t;
        btn.onclick = function() {
          document.querySelectorAll('#' + key + 'BzFilters .filter-btn').forEach(function(b) { b.classList.remove('active'); });
          btn.classList.add('active');
          setActiveBz(key, t === '全部' ? null : t);
          setPage(key, 1);
          renderZJTable(key);
        };
        container.appendChild(btn);
      });
    })();

    // City filter buttons
    (function() {
      var container = document.getElementById(key + 'CityFilters');
      var stats = getZJStats(key);
      var cities = Object.keys(stats.cities);
      container.innerHTML = '';
      var allBtn = document.createElement('button');
      allBtn.className = 'filter-btn city-btn active';
      allBtn.textContent = '全部';
      allBtn.onclick = function() {
        document.querySelectorAll('#' + key + 'CityFilters .filter-btn').forEach(function(b) { b.classList.remove('active'); });
        allBtn.classList.add('active');
        setActiveCity(key, null);
        setPage(key, 1);
        renderZJTable(key);
      };
      container.appendChild(allBtn);
      cities.forEach(function(c) {
        var btn = document.createElement('button');
        btn.className = 'filter-btn city-btn';
        btn.textContent = c + ' (' + stats.cities[c] + ')';
        btn.onclick = function() {
          document.querySelectorAll('#' + key + 'CityFilters .filter-btn').forEach(function(b) { b.classList.remove('active'); });
          btn.classList.add('active');
          setActiveCity(key, c);
          setPage(key, 1);
          renderZJTable(key);
        };
        container.appendChild(btn);
      });
    })();

    renderZJTable(key);
  }

  function renderZJTable(key) {
    var searchEl = document.getElementById('zj' + chartPrefix(key) + 'Search');
    var search = (searchEl ? searchEl.value : '').toLowerCase();
    var data = getZJData(key);
    var activeBz = getActiveBz(key);
    var activeCity = getActiveCity(key);
    var page = getPage(key);

    var filtered = data;
    if (activeBz) { filtered = filtered.filter(function(e) { return e.bianzhi === activeBz; }); }
    if (activeCity) { filtered = filtered.filter(function(e) { return e.city === activeCity; }); }
    if (search) { filtered = filtered.filter(function(e) { return (e.title || '').toLowerCase().indexOf(search) >= 0 || (e.city || '').toLowerCase().indexOf(search) >= 0; }); }

    var totalPages = Math.ceil(filtered.length / PAGE_SIZE) || 1;
    if (page > totalPages) { page = totalPages; setPage(key, page); }
    var start = (page - 1) * PAGE_SIZE;
    var pageData = filtered.slice(start, start + PAGE_SIZE);
    var prefix = chartPrefix(key);

    document.getElementById('zj' + prefix + 'TableInfo').textContent = '显示 ' + (start + 1) + '-' + Math.min(start + PAGE_SIZE, filtered.length) + ' / 共 ' + filtered.length + ' 条';

    var pageHtml = '';
    for (var i = 1; i <= totalPages; i++) {
      pageHtml += '<button class="page-btn' + (i === page ? ' active' : '') + '" onclick="window._goZJPage(\'' + key + '\',' + i + ')">' + i + '</button>';
    }
    document.getElementById('zj' + prefix + 'Pages').innerHTML = pageHtml;

    var tbody = document.querySelector('#zj' + prefix + 'Table tbody');
    var noResults = document.getElementById('zj' + prefix + 'NoResults');
    if (filtered.length === 0) {
      tbody.innerHTML = '';
      noResults.style.display = 'block';
      document.getElementById('zj' + prefix + 'TableInfo').textContent = '共 0 条';
      return;
    }
    noResults.style.display = 'none';

    var badgeClass = { '编制': 'badge-biannei', '编外': 'badge-bianwai', '选调': 'badge-xuandiao', '未知': 'badge-unknown' };
    tbody.innerHTML = pageData.map(function(e) {
      var bz = e.bianzhi || '未知';
      var isHot = e.date === '热门推荐';
      return '<tr><td><span class="badge ' + (badgeClass[bz] || 'badge-unknown') + '">' + bz + '</span></td>' +
        '<td>' + (e.city || '?') + '</td>' +
        '<td style="max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"><a href="' + (e.url || '#') + '" target="_blank" title="' + (e.title || '').replace(/"/g, '&quot;') + '" style="color:var(--text);text-decoration:none">' + e.title + '</a></td>' +
        '<td>' + (e.count ? e.count + '人' : '-') + '</td>' +
        '<td>' + (isHot ? '<span class="badge badge-hot">热门</span>' : e.date) + '</td></tr>';
    }).join('');
  }

  window._goZJPage = function(key, p) { setPage(key, p); renderZJTable(key); };
  window.renderZjScTable = function() { renderZJTable('sc'); };
  window.renderZjFjTable = function() { renderZJTable('fj'); };
  window.renderZjCqTable = function() { renderZJTable('cq'); };
  window.renderZjGdTable = function() { renderZJTable('gd'); };

  // Tab switching
  window.switchTab = function(name) {
    document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
    document.querySelectorAll('.tab-content').forEach(function(c) { c.classList.remove('active'); });
    document.getElementById('tab-' + name).classList.add('active');

    // Activate correct tab button
    var btns = document.querySelectorAll('.tab-btn');
    if (name === 'bm') btns[0].classList.add('active');
    else if (name === 'zj-sc') btns[1].classList.add('active');
    else if (name === 'zj-fj') btns[2].classList.add('active');
    else if (name === 'zj-cq') btns[3].classList.add('active');
    else if (name === 'zj-gd') btns[4].classList.add('active');

    // Lazy render charts
    if (name === 'zj-sc' && !renderedCharts['sc']) renderZJCharts('sc');
    if (name === 'zj-fj' && !renderedCharts['fj']) renderZJCharts('fj');
    if (name === 'zj-cq' && !renderedCharts['cq']) renderZJCharts('cq');
    if (name === 'zj-gd' && !renderedCharts['gd']) renderZJCharts('gd');
  };
})();
</script>
</body>
</html>"""