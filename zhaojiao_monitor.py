# -*- coding: utf-8 -*-
"""
招教网(www.zhaojiao.net) 教师招聘信息爬取模块（纯本地版）

爬取指定列表页的前N页，解析招聘公告条目，支持变化检测和状态持久化。

用法:
  python zhaojiao_monitor.py             # 本地运行一次
  python zhaojiao_monitor.py --test      # 测试解析
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, date, timedelta

import requests
from bs4 import BeautifulSoup

DEFAULT_STATE = "zj_monitor_state.json"
DEFAULT_LOG = "zj_monitor.log"
DEFAULT_REPORT = "zj_report.txt"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

# 模拟完整浏览器请求头，避免被反爬拦截
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.zhaojiao.net/",
    "Cache-Control": "max-age=0",
}

log = logging.getLogger("zj_monitor")


# --------------------------------------------------------------------------- #
# 配置
# --------------------------------------------------------------------------- #
def _env(v):
    return os.environ.get(v, "")


def load_config():
    cfg = {
        "base_url": _env("ZJ_URL") or "https://www.zhaojiao.net/zhaojiao/list-150.html",
        "areaid": _env("ZJ_AREAID") or "23",  # 23 = 四川
        "pages": int(_env("ZJ_PAGES") or "3"),
        "state_file": DEFAULT_STATE,
        "log_file": DEFAULT_LOG,
        "report_file": _env("ZJ_REPORT_FILE") or DEFAULT_REPORT,
        "keyword_filter": [x.strip() for x in _env("ZJ_KEYWORDS").split(",") if x.strip()],
    }
    return cfg


# --------------------------------------------------------------------------- #
# 抓取
# --------------------------------------------------------------------------- #
def _build_page_url(base_url, areaid, page_num):
    """构造分页URL: list-150-{page}.html?areaid=23 (第1页用 list-150.html)"""
    if page_num <= 1:
        return f"{base_url}?areaid={areaid}"
    if base_url.endswith(".html"):
        paged = base_url.replace(".html", f"-{page_num}.html")
    else:
        paged = f"{base_url}-{page_num}.html"
    return f"{paged}?areaid={areaid}"


def fetch_page(base_url, areaid, page_num, retries=3):
    url = _build_page_url(base_url, areaid, page_num)
    session = requests.Session()
    last_error = None
    for i in range(retries):
        try:
            if i == 0:
                try:
                    session.get("https://www.zhaojiao.net/", headers=HEADERS, timeout=15)
                except Exception:
                    pass
            r = session.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            r.encoding = "utf-8"
            return r.text
        except Exception as e:
            last_error = e
            if i == retries - 1:
                raise
            log.warning("第%d页 第%d次抓取失败: %s, %d秒后重试...", page_num, i + 1, e, (i + 1) * 5)
            time.sleep((i + 1) * 5)
    raise last_error


def fetch_all_pages(cfg, pages=None):
    if pages is None:
        pages = cfg.get("pages", 3)
    all_html = []
    for p in range(1, pages + 1):
        html = fetch_page(cfg["base_url"], cfg["areaid"], p)
        all_html.append(html)
        log.info("第%d页抓取成功, 长度=%d", p, len(html))
    return all_html


# --------------------------------------------------------------------------- #
# 解析
# --------------------------------------------------------------------------- #
def _clean(s):
    return " ".join((s or "").split())


def _classify_bianzhi(title):
    """根据标题关键词分类编制类型。
    返回: '编外' | '选调' | '编制' | '未知'
    优先级: 编外 > 选调 > 编制 > 未知
    """
    if any(k in title for k in ['编外', '编制外', '员额', '储备', '两自一包', '临聘', '代课', '合同', '外聘', '兼职']):
        return '编外'
    if any(k in title for k in ['选调', '考调', '选聘', '考聘']):
        return '选调'
    if any(k in title for k in ['考核招聘', '公开考核', '引进', '公费师范', '优师',
                                  '编内', '编制内', '有编', '入编', '带编', '在编', '事业编']):
        return '编制'
    return '未知'


def parse_entries(html):
    """从HTML中解析招聘条目列表。返回 list of dicts。"""
    soup = BeautifulSoup(html, "lxml")
    entries = []
    base_href = "https://www.zhaojiao.net/zhaojiao/"

    for item in soup.select("div.content-item"):
        a = item.select_one("a.item-con")
        if not a:
            continue
        href = a.get("href", "")
        full_url = href if href.startswith("http") else base_href.rstrip("/") + "/" + href.lstrip("/")

        area_el = item.select_one("span.item-zp")
        title_el = item.select_one("span.item-text")
        date_el = item.select_one("span.item-time")

        area = _clean(area_el.get_text()) if area_el else ""
        title = _clean(title_el.get_text()) if title_el else ""
        date_str = _clean(date_el.get_text()) if date_el else ""

        # 提取人数：取标题中最后一个 (\d+)人，避免"考核招聘96人（含教师岗4人）"取到96
        count = None
        all_counts = re.findall(r'(\d+)人', title)
        if all_counts:
            count = int(all_counts[-1])

        # 提取城市（从area标签中：如 [成都市教师招聘] → 成都市）
        city = ""
        m = re.search(r'\[(.+?)教师招聘\]', area)
        if m:
            city = m.group(1)

        # 编制分类
        bianzhi = _classify_bianzhi(title)

        key = f"{title}|{date_str}"
        entries.append({
            "key": key,
            "area": area,
            "city": city,
            "title": title,
            "date": date_str,
            "count": count,
            "bianzhi": bianzhi,
            "url": full_url,
        })

    return entries


def parse_all_pages(all_html):
    """解析多页HTML，去重合并。"""
    all_entries = []
    seen_keys = set()
    for html in all_html:
        entries = parse_entries(html)
        for e in entries:
            if e["key"] not in seen_keys:
                seen_keys.add(e["key"])
                all_entries.append(e)
    return all_entries


# --------------------------------------------------------------------------- #
# 过滤
# --------------------------------------------------------------------------- #
def filter_entry(e, cfg):
    kws = cfg.get("keyword_filter") or []
    if kws and not any(k in e["title"] for k in kws):
        return False
    return True


# --------------------------------------------------------------------------- #
# 构建日报
# --------------------------------------------------------------------------- #
BIANZHI_ICON = {"编制": "🟢", "编外": "🔴", "选调": "🔄", "未知": "⚪"}


def build_report(entries, prev_state, cfg):
    """生成招教网日报消息，按城市分组，标注编制类型。"""
    prev_map = {e["key"]: e for e in prev_state.get("entries", [])}
    curr_keys = {e["key"] for e in entries}
    is_first = not prev_map

    # 过滤：只保留近3天 + 热门推荐
    today = date.today()
    cutoff = today - timedelta(days=3)
    def _is_recent(e):
        d = e.get("date", "")
        if d == "热门推荐":
            return True
        try:
            return datetime.strptime(d, "%Y-%m-%d").date() >= cutoff
        except ValueError:
            return True

    recent_entries = [e for e in entries if _is_recent(e)]

    # 过滤 + 分类
    filtered = [e for e in recent_entries if filter_entry(e, cfg)]

    # 按城市分组，城市内按编制类型排序
    by_city = {}
    for e in filtered:
        city = e.get("city") or "其他"
        by_city.setdefault(city, []).append(e)

    # 排序：条目多的城市排前面
    sorted_cities = sorted(by_city.items(), key=lambda x: -len(x[1]))

    # 统计
    new_count = 0
    bz_count = {"编制": 0, "编外": 0, "选调": 0, "未知": 0}
    filtered_out = len(entries) - len(recent_entries)

    for e in filtered:
        bz_count[e["bianzhi"]] = bz_count.get(e["bianzhi"], 0) + 1
        if is_first or e["key"] not in prev_map:
            new_count += 1

    # 检测已下线
    removed = []
    for key in prev_map:
        if key not in curr_keys:
            pe = prev_map[key]
            removed.append(pe["title"])

    # 组装消息
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg_lines = [
        f"📋 招教网招聘日报（四川 · 近3天）",
        f"更新时间：{now}",
        "",
        f"📊 共 {len(filtered)} 条 | 🟢编制 {bz_count['编制']} | 🔴编外 {bz_count['编外']} | 🔄选调 {bz_count['选调']} | ⚪未知 {bz_count['未知']}",
    ]
    if new_count:
        msg_lines.append(f"   🆕 新增 {new_count} 条")
    if filtered_out:
        msg_lines.append(f"   📎 已过滤 {filtered_out} 条旧数据")
    if removed:
        msg_lines.append(f"   ❌ 已下线 {len(removed)} 条")
    msg_lines.append("")

    # 按城市输出
    for city, city_entries in sorted_cities:
        msg_lines.append(f"━" * 30)
        msg_lines.append(f"🏙 {city}（{len(city_entries)}条）")

        # 城市内按编制类型排序
        city_entries.sort(key=lambda e: ["编制", "选调", "未知", "编外"].index(e["bianzhi"]))

        for e in city_entries:
            key = e["key"]
            icon = BIANZHI_ICON.get(e["bianzhi"], "⚪")

            if is_first or key not in prev_map:
                tag = "🆕"
            else:
                tag = ""

            line = f"{icon} {tag} {e['title']}"
            if e.get("date"):
                line += f"\n      📅 {e['date']}"
            msg_lines.append(line)

        msg_lines.append("")

    # 已下线
    if removed:
        msg_lines.append("━" * 30)
        msg_lines.append("❌ 已下线：")
        for r in removed[:10]:
            msg_lines.append(f"   · {r}")
        if len(removed) > 10:
            msg_lines.append(f"   ... 等共 {len(removed)} 条")

    msg_lines.append("")
    msg_lines.append("— 招教网本地监控")

    has_changes = bool(new_count or removed)
    return "\n".join(msg_lines), has_changes


# --------------------------------------------------------------------------- #
# 状态持久化
# --------------------------------------------------------------------------- #
def load_state(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"entries": []}


def save_state(path, entries):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "entries": entries,
        }, f, ensure_ascii=False, indent=2)


def save_report(path, report):
    """将报告保存到本地文件。"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def run_once(cfg):
    all_html = fetch_all_pages(cfg)
    entries = parse_all_pages(all_html)
    log.info("共解析到 %d 条招聘信息", len(entries))

    prev_state = load_state(cfg["state_file"])
    report, has_changes = build_report(entries, prev_state, cfg)
    save_state(cfg["state_file"], entries)

    log.info("\n%s", report)

    # 保存报告
    save_report(cfg["report_file"], report)
    log.info("报告已保存到: %s", cfg["report_file"])

    return report, has_changes, entries


def main():
    ap = argparse.ArgumentParser(description="招教网招聘信息监控（纯本地版）")
    ap.add_argument("--test", action="store_true", help="测试解析")
    args = ap.parse_args()

    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    cfg = load_config()

    if args.test:
        log.info("测试解析招教网...")
        all_html = fetch_all_pages(cfg)
        entries = parse_all_pages(all_html)
        log.info("共 %d 条", len(entries))
        for e in entries[:10]:
            print(f"  [{e['city']}] {e['title']} | {e['date']} | {e['url']}")
        return

    run_once(cfg)


if __name__ == "__main__":
    main()