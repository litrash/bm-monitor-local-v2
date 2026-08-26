# -*- coding: utf-8 -*-
"""
统一监控脚本（纯本地版） - 同时监控考生之家 + 招教网（四川）+ 招教网（福建），生成可视化 Dashboard。

用法:
  python unified_monitor.py              # 运行一次，生成 Dashboard 并打开浏览器
  python unified_monitor.py --test       # 只测试不保存
  python unified_monitor.py --no-browser # 不自动打开浏览器
  python unified_monitor.py --loop       # 循环监控模式（每 30 分钟）
"""

import argparse
import logging
import os
import subprocess
import sys
import webbrowser
from datetime import datetime

from generate_dashboard import build as build_dashboard

# 复用两个模块的核心函数
from bm_monitor import (
    fetch_html as bm_fetch,
    parse_entries as bm_parse,
    build_daily_report as bm_build_report,
    load_state as bm_load_state,
    save_state as bm_save_state,
    load_config as bm_load_config,
)

from zhaojiao_monitor import (
    fetch_all_pages as zj_fetch_all,
    parse_all_pages as zj_parse_all,
    build_report as zj_build_report,
    load_state as zj_load_state,
    save_state as zj_save_state,
)

log = logging.getLogger("unified_monitor")
DEFAULT_REPORT = "daily_report.txt"

# 招教网地区配置
ZJ_REGIONS = {
    "sc": {
        "label": "四川",
        "areaid": "23",
        "state_file": "zj_sc_monitor_state.json",
        "report_file": "zj_sc_report.txt",
        "base_url": "https://www.zhaojiao.net/zhaojiao/list-150.html",
        "pages": 3,
        "keyword_filter": [],
    },
    "fj": {
        "label": "福建",
        "areaid": "14",
        "state_file": "zj_fj_monitor_state.json",
        "report_file": "zj_fj_report.txt",
        "base_url": "https://www.zhaojiao.net/zhaojiao/list-150.html",
        "pages": 3,
        "keyword_filter": [],
    },
    "cq": {
        "label": "重庆",
        "areaid": "4",
        "state_file": "zj_cq_monitor_state.json",
        "report_file": "zj_cq_report.txt",
        "base_url": "https://www.zhaojiao.net/zhaojiao/list-150.html",
        "pages": 3,
        "keyword_filter": [],
    },
    "gd": {
        "label": "广东",
        "areaid": "20",
        "state_file": "zj_gd_monitor_state.json",
        "report_file": "zj_gd_report.txt",
        "base_url": "https://www.zhaojiao.net/zhaojiao/list-150.html",
        "pages": 3,
        "keyword_filter": [],
    },
}


def _build_zj_config(region_cfg):
    """根据地区配置构造 zhaojiao_monitor 可用的 config dict。"""
    env_pages = os.environ.get("ZJ_PAGES", "")
    env_keywords = os.environ.get("ZJ_KEYWORDS", "")
    return {
        "base_url": region_cfg["base_url"],
        "areaid": region_cfg["areaid"],
        "pages": int(env_pages) if env_pages else region_cfg["pages"],
        "state_file": region_cfg["state_file"],
        "log_file": "zj_monitor.log",
        "report_file": region_cfg["report_file"],
        "keyword_filter": (
            [x.strip() for x in env_keywords.split(",") if x.strip()]
            if env_keywords else region_cfg["keyword_filter"]
        ),
    }


def _run_zj_region(region_key, region_cfg):
    """抓取单个招教网地区，返回 (report, entries, success)。"""
    cfg = _build_zj_config(region_cfg)
    label = region_cfg["label"]
    log.info("抓取招教网（%s）areaid=%s...", label, cfg["areaid"])

    all_html = zj_fetch_all(cfg)
    entries = zj_parse_all(all_html)
    log.info("招教网（%s）: %d 条招聘信息", label, len(entries))

    prev_state = zj_load_state(cfg["state_file"])
    report, has_changes = zj_build_report(entries, prev_state, cfg)
    zj_save_state(cfg["state_file"], entries)

    # 保存单地区报告
    with open(cfg["report_file"], "w", encoding="utf-8") as f:
        f.write(report)

    log.info("招教网（%s）日报生成完成", label)
    return report, entries, has_changes


def run_once():
    """运行一次：同时抓取三个站点，生成统一日报和 Dashboard。
    返回: (bm_active, bm_closed, zj_sc_entries, zj_fj_entries, has_changes)
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    bm_active, bm_closed = [], []

    # ===================================================================== #
    # 第一部分：考生之家
    # ===================================================================== #
    bm_cfg = bm_load_config()
    bm_report = ""
    bm_has_changes = False

    try:
        log.info("=" * 40)
        log.info("抓取考生之家...")
        html = bm_fetch(bm_cfg["url"])
        active, closed = bm_parse(html)
        log.info("考生之家: %d 条进行中, %d 条已结束", len(active), len(closed))

        bm_active, bm_closed = active, closed

        prev_state = bm_load_state(bm_cfg["state_file"])
        bm_report, bm_has_changes = bm_build_report(active, closed, prev_state, bm_cfg)
        bm_save_state(bm_cfg["state_file"], active, closed)

        is_first = not prev_state.get("entries")
        log.info("考生之家日报生成完成")
        if is_first:
            log.info("(首次运行，建立基线)")
        elif bm_has_changes:
            log.info("检测到变化！")
        else:
            log.info("无变化")
    except Exception as e:
        log.error("考生之家抓取失败: %s", e, exc_info=True)
        bm_report = f"⚠️ 考生之家抓取失败: {e}"

    # ===================================================================== #
    # 第二部分：招教网（四川 + 福建 + 重庆 + 广东）
    # ===================================================================== #
    zj_results = {}
    for region_key in ZJ_REGIONS:
        region_cfg = ZJ_REGIONS[region_key]
        try:
            log.info("=" * 40)
            report, entries, has_changes = _run_zj_region(region_key, region_cfg)
            zj_results[region_key] = {
                "report": report,
                "entries": entries,
                "has_changes": has_changes,
                "success": True,
            }
        except Exception as e:
            log.error("招教网（%s）抓取失败: %s", region_cfg["label"], e, exc_info=True)
            zj_results[region_key] = {
                "report": f"⚠️ 招教网（{region_cfg['label']}）抓取失败: {e}",
                "entries": [],
                "has_changes": False,
                "success": False,
            }
            # 确保状态文件存在
            cfg = _build_zj_config(region_cfg)
            zj_save_state(cfg["state_file"], zj_load_state(cfg["state_file"]).get("entries", []))

    # ===================================================================== #
    # 第三部分：组装统一消息
    # ===================================================================== #
    sections = [
        f"📋 每日招聘监控日报",
        f"更新时间：{now}",
        "",
        "━" * 40,
        "🏫 考生之家 (bm.e21cn.com)",
        "━" * 40,
        bm_report,
        "",
    ]

    for region_key in ZJ_REGIONS:
        r = zj_results[region_key]
        label = ZJ_REGIONS[region_key]["label"]
        sections.append("━" * 40)
        sections.append(f"🎓 招教网（{label}）(zhaojiao.net)")
        sections.append("━" * 40)
        sections.append(r["report"])
        sections.append("")

    sections.append("— 本地招聘监控")

    full_report = "\n".join(sections)

    # 输出到控制台
    print(full_report)

    # 保存到本地文件
    with open(DEFAULT_REPORT, "w", encoding="utf-8") as f:
        f.write(full_report)
    log.info("日报已保存到: %s", DEFAULT_REPORT)

    has_changes = bm_has_changes or any(
        zj_results[k]["has_changes"] for k in ZJ_REGIONS
    )

    return (
        bm_active, bm_closed,
        {k: zj_results[k]["entries"] for k in ZJ_REGIONS},
        has_changes,
    )


def main():
    ap = argparse.ArgumentParser(description="统一招聘监控（纯本地版）")
    ap.add_argument("--test", action="store_true", help="只测试不保存")
    ap.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    ap.add_argument("--no-dashboard", action="store_true", help="不生成可视化 Dashboard")
    ap.add_argument("--loop", action="store_true", help="循环监控模式")
    ap.add_argument("--interval", type=int, default=30, help="循环间隔（分钟），默认 30")
    ap.add_argument("--push", action="store_true", help="运行后推送 Dashboard 到 GitHub Pages")
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

    if args.test:
        log.info("测试模式（不保存状态）")
        bm_cfg = bm_load_config()

        log.info("--- 考生之家 ---")
        html = bm_fetch(bm_cfg["url"])
        active, closed = bm_parse(html)
        log.info("%d 条进行中, %d 条已结束", len(active), len(closed))
        for a in active[:5]:
            log.info("  [%s] %s %s~%s", a["area"], a["name"], a["start"], a["end"])

        for region_key in ZJ_REGIONS:
            region_cfg = ZJ_REGIONS[region_key]
            label = region_cfg["label"]
            cfg = _build_zj_config(region_cfg)
            log.info("--- 招教网（%s）---", label)
            all_html = zj_fetch_all(cfg)
            entries = zj_parse_all(all_html)
            log.info("%d 条", len(entries))
            for e in entries[:5]:
                log.info("  [%s] %s | %s", e["city"], e["title"], e["date"])
        return

    if args.loop:
        log.info("循环监控模式，每 %d 分钟检查一次", args.interval)
        import time
        while True:
            try:
                _do_run(args)
            except KeyboardInterrupt:
                log.info("已退出")
                break
            except Exception as e:
                log.error("出错: %s", e, exc_info=True)
            try:
                time.sleep(args.interval * 60)
            except KeyboardInterrupt:
                break
    else:
        _do_run(args)


def _do_run(args):
    """执行一次完整的监控 + Dashboard 生成流程。"""
    result = run_once()
    if result is None:
        return
    bm_active, bm_closed, zj_entries, has_changes = result

    # Dashboard
    if not args.no_dashboard:
        try:
            path = build_dashboard(
                bm_active, bm_closed,
                zj_entries.get("sc", []), zj_entries.get("fj", []),
                zj_entries.get("cq", []), zj_entries.get("gd", []),
            )
            log.info("Dashboard 已生成: %s", path)

            if not args.no_browser:
                webbrowser.open("file:///" + path.replace("\\", "/"))
                log.info("浏览器已打开 Dashboard")

            # Windows Toast 通知
            _show_toast("招聘监控日报已更新", "点击 Dashboard 查看完整数据")

            # 推送到 GitHub
            if args.push:
                _push_to_github()
        except Exception as e:
            log.warning("Dashboard 生成失败: %s", e)


def _push_to_github():
    """将 dashboard.html 提交并推送到 GitHub Pages。"""
    import subprocess
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    dashboard = "dashboard.html"
    try:
        subprocess.run(["git", "add", dashboard], check=True, capture_output=True)
        result = subprocess.run(
            ["git", "commit", "-m", f"update dashboard {now}"],
            capture_output=True, text=True,
        )
        if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
            log.info("Dashboard 无变化，跳过推送")
            return
        if result.returncode != 0:
            log.warning("Git commit 失败: %s", result.stderr)
            return
        push_result = subprocess.run(
            ["git", "push", "origin", "main"],
            capture_output=True, text=True, timeout=30,
        )
        if push_result.returncode == 0:
            log.info("✅ Dashboard 已推送到 GitHub Pages")
        else:
            log.warning("Git push 失败: %s", push_result.stderr)
    except FileNotFoundError:
        log.warning("未找到 git 命令，请确认已安装 Git")
    except subprocess.TimeoutExpired:
        log.warning("Git push 超时，请检查网络连接")
    except Exception as e:
        log.warning("推送失败: %s", e)


def _show_toast(title, body):
    """显示 Windows 桌面通知。"""
    try:
        ps = f'''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$template.GetElementsByTagName("text")[0].AppendChild($template.CreateTextNode("{title}")) > $null
$template.GetElementsByTagName("text")[1].AppendChild($template.CreateTextNode("{body}")) > $null
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("招聘监控")
$notification = [Windows.UI.Notifications.ToastNotification]::new($template)
$notifier.Show($notification)
'''
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, timeout=10)
    except Exception:
        pass  # 通知失败不影响主流程


if __name__ == "__main__":
    main()