# 招聘监控系统（纯本地版）

从 [bm-monitor-local](../bm-monitor-local) 重构而来，**移除所有推送功能**，完全本地运行。

## 监控范围

- **考生之家** (bm.e21cn.com)：四川考试报名信息
- **招教网（四川）** (zhaojiao.net, areaid=23)：四川教师招聘信息
- **招教网（福建）** (zhaojiao.net, areaid=14)：福建教师招聘信息

## 快速开始

### 1. 安装依赖

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 运行

```bash
# 统一监控（推荐）：抓取三个站点 + 生成 Dashboard + 自动打开浏览器
python unified_monitor.py

# 只看数据不打开浏览器
python unified_monitor.py --no-browser

# 只测试不保存状态
python unified_monitor.py --test

# 单独运行考生之家
python bm_monitor.py --once

# 单独运行招教网（四川，areaid=23）
python zhaojiao_monitor.py --test

# 循环监控模式（每 30 分钟）
python unified_monitor.py --loop --interval 30
```

### 3. 双击运行

直接双击 `local_monitor.bat`（需要先配置 `.venv`）。

## 输出文件

| 文件 | 说明 |
|------|------|
| `dashboard.html` | 可视化数据面板（三个板块），自动打开浏览器 |
| `daily_report.txt` | 文本日报 |
| `bm_monitor_state.json` | 考生之家状态缓存 |
| `zj_sc_monitor_state.json` | 招教网（四川）状态缓存 |
| `zj_fj_monitor_state.json` | 招教网（福建）状态缓存 |

## 环境变量（可选）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `BM_URL` | 考生之家首页 | `https://bm.e21cn.com/` |
| `BM_KEYWORDS` | 关键词过滤（逗号分隔） | 空（不过滤） |
| `BM_AREAS` | 地区过滤（逗号分隔） | 空（不过滤） |
| `BM_ENDING_HOURS` | 即将截止提醒阈值（小时） | `2` |
| `ZJ_PAGES` | 招教网爬取页数（两个地区共用） | `3` |
| `ZJ_KEYWORDS` | 招教网关键词过滤（两个地区共用） | 空 |

## 招教网地区配置

如需修改地区，编辑 `unified_monitor.py` 中的 `ZJ_REGIONS` 字典：

```python
ZJ_REGIONS = {
    "sc": {"label": "四川", "areaid": "23", ...},
    "fj": {"label": "福建", "areaid": "14", ...},
}
```

## 与原版区别

- ❌ 移除了 Telegram 推送
- ❌ 移除了 Server酱 推送
- ❌ 移除了 Gitee Go / GitHub Actions CI
- ❌ 移除了所有凭据（Token/SendKey）
- ✅ 保留了两个站点的爬取和解析
- ✅ 新增了招教网（福建）areaid=14
- ✅ 保留了变化检测和状态持久化
- ✅ 保留了 Dashboard 可视化（三个板块）
- ✅ 新增了文本日报保存功能
- ✅ 新增了 `--loop` 循环监控模式
- ✅ 新增了 Windows Toast 桌面通知