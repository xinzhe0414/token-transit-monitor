"""
每日进度报告生成器 v2 — 每天21:00运行
整合: 监控状态 + 收益数据 + 待办事项 + 风险预警 + 自动回复统计
输出: reports/日报_YYYY-MM-DD.md + 飞书推送
"""
import json
import os
import sys
import yaml
from datetime import datetime, timezone, timedelta
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TZ = timezone(timedelta(hours=8))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_data():
    """加载今日监控数据"""
    data_dir = os.path.join(BASE_DIR, "data")
    stations_file = os.path.join(data_dir, "stations.json")
    history_file = os.path.join(data_dir, "history.json")
    alerts_file = os.path.join(data_dir, "alerts.json")
    revenue_file = os.path.join(data_dir, "revenue.json")
    reply_stats_file = os.path.join(data_dir, "reply_stats.json")

    current = {}
    history = {}
    alerts = []
    revenue = {}
    reply_stats = {}

    if os.path.exists(stations_file):
        with open(stations_file, "r", encoding="utf-8") as f:
            current = json.load(f)
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
    if os.path.exists(alerts_file):
        with open(alerts_file, "r", encoding="utf-8") as f:
            alerts = json.load(f)
    if os.path.exists(revenue_file):
        with open(revenue_file, "r", encoding="utf-8") as f:
            revenue = json.load(f)
    if os.path.exists(reply_stats_file):
        with open(reply_stats_file, "r", encoding="utf-8") as f:
            reply_stats = json.load(f)

    return current, history, alerts, revenue, reply_stats

def load_tasks():
    """加载任务清单"""
    tasks_path = os.path.join(BASE_DIR, "tasks.yaml")
    with open(tasks_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def calc_uptime(history_data):
    """从历史数据计算各站今日可用率"""
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    uptime = {}
    for name, records in history_data.items():
        today_records = [r for r in records if r.get("time", "").startswith(today)]
        if not today_records:
            uptime[name] = None
            continue
        online = sum(1 for r in today_records if r.get("status") == "在线")
        uptime[name] = round(online / len(today_records) * 100, 1)
    return uptime

def calc_avg_latency(history_data):
    """从历史数据计算各站今日平均延迟"""
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    latency = {}
    for name, records in history_data.items():
        today_records = [r for r in records if r.get("time", "").startswith(today) and r.get("delay_ms")]
        if not today_records:
            latency[name] = None
            continue
        latency[name] = round(sum(r["delay_ms"] for r in today_records) / len(today_records))
    return latency

def calc_month_revenue(revenue_data):
    """计算本月佣金"""
    this_month = datetime.now(TZ).strftime("%Y-%m")
    month_total = sum(
        c["amount"] for c in revenue_data.get("commission_log", [])
        if c["date"].startswith(this_month)
    )
    return month_total

def calc_recent_commission(revenue_data, days=7):
    """计算最近N天佣金"""
    cutoff = (datetime.now(TZ) - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = sum(
        c["amount"] for c in revenue_data.get("commission_log", [])
        if c["date"] >= cutoff
    )
    return recent

def generate_report():
    """生成每日报告"""
    current, history, alerts, revenue, reply_stats = load_data()
    tasks = load_tasks()
    uptime = calc_uptime(history)
    latency = calc_avg_latency(history)
    now = datetime.now(TZ)
    today_str = now.strftime("%Y-%m-%d")

    # 任务进度
    total_tasks = 0
    done_tasks = 0
    todo_items = []
    for day_block in tasks.get("days", []):
        for task in day_block.get("tasks", []):
            total_tasks += 1
            status = task.get("status", "pending")
            if status == "done":
                done_tasks += 1
            elif status in ("pending", "in_progress"):
                todo_items.append(f"- [ ] **[{task['id']}] {task['name']}** (Day{day_block['day']} | {task['time']})")
    pct = round(done_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # 今日告警
    today_alerts = [a for a in alerts if a.get("time", "").startswith(today_str)]

    # 本月佣金
    month_commission = calc_month_revenue(revenue)
    total_commission = revenue.get("total_commission", 0)
    recent_7d_commission = calc_recent_commission(revenue, 7)

    report = f"""# Token 比价站 · 每日进度报告

> 📅 {now.strftime('%Y年%m月%d日 %A')} | 自动生成于 {now.strftime('%H:%M')}

---

## 📊 今日收益概览

| 指标 | 数值 |
|------|------|
| 今日页面 UV | {revenue.get('today_uv', '未统计')} |
| 今日联盟点击 | {revenue.get('today_clicks', '未统计')} |
| 近 7 天佣金 | ¥{recent_7d_commission} |
| 本月累计佣金 | ¥{month_commission} |
| 历史总佣金 | ¥{total_commission} |

---

## 📈 任务进度: {done_tasks}/{total_tasks} ({pct}%)

"""

    # 按天分组显示任务
    for day_block in tasks.get("days", []):
        day = day_block["day"]
        title = day_block["title"]
        report += f"### Day {day}: {title}\n"
        for task in day_block.get("tasks", []):
            status = task.get("status", "pending")
            icon = {"done": "✅", "in_progress": "🔄", "pending": "⬜", "skipped": "⏭️"}.get(status, "❓")
            report += f"- {icon} [{task['id']}] {task['name']}\n"
        report += "\n"

    report += f"""---

## 🖥️ 中转站实时状态

| 站名 | 类型 | 状态 | 延迟 | 今日可用率 |
|------|------|------|------|-----------|
"""

    for station in current.get("stations", []):
        name = station["name"]
        status_icon = "🟢" if station["status"] == "在线" else ("🟡" if "超时" in station["status"] else "🔴")
        delay_str = f"{station['delay_ms']}ms" if station.get("delay_ms") else "-"
        uptime_str = f"{uptime.get(name, '-')}%" if uptime.get(name) is not None else "-"
        report += f"| {status_icon} {name} | {station.get('type', '')} | {station['status']} | {delay_str} | {uptime_str} |\n"

    # 风险预警
    report += f"""
---

## ⚠️ 风险预警

"""

    if today_alerts:
        for a in today_alerts[-10:]:
            report += f"- {a['time'][:19]} | {a['alert']}\n"
    else:
        report += "> ✅ 今日无异常告警，所有站点运行正常。\n"

    # 待办事项
    report += f"""
---

## 📋 待办事项 (优先级排序)

"""
    if todo_items:
        for item in todo_items[:10]:
            report += f"{item}\n"
    else:
        report += "> ✅ 当前无待办任务。\n"

    # 自动回复统计
    if reply_stats.get("total_used", 0) > 0:
        report += f"""
---

## 💬 客户回复统计

今日使用模板: {reply_stats.get('total_used', 0)} 次
"""
        for tid, count in sorted(reply_stats.get("templates", {}).items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                report += f"- 模板#{tid}: {count} 次\n"

    # 自动化任务状态
    report += f"""
---

## 🤖 自动化任务运行状态

| 任务 | 频率 | 状态 |
|------|------|------|
| 中转站可用性监控 | 每10分钟 | ✅ 运行中 |
| 每日报告生成 | 每天21:00 | ✅ 本次报告 |
| 风险预警扫描 | 每30分钟 | ✅ 运行中 |
| 客户自动回复模板 | 按需调用 | ✅ 就绪 |
| 收益追踪 | 按需更新 | ✅ 就绪 |
| 每周竞品追踪 | 每周一 | ⏳ 下次: 下周一 |
| 文章引流 | 每月2篇 | 📝 按计划 |

---

## 🎯 下一步行动建议

1. 检查待办事项，优先完成 Day{tasks['meta']['current_day']} 的节点
2. 如有告警站，登录确认是中转站挂了还是检测误报
3. 今天打开过 auto_responder.py 吗？在社区回复时 `python auto_responder.py search <关键词>` 快速匹配
4. 更新收益: `python revenue_tracker.py update --uv <今日UV>`
"""

    return report

def save_report(report):
    """保存报告到本地"""
    reports_dir = os.path.join(BASE_DIR, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    filepath = os.path.join(reports_dir, f"日报_{today}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)
    return filepath

def push_to_feishu(report):
    """推送到飞书文档"""
    import subprocess
    import re

    tmp_dir = os.path.join(BASE_DIR, "reports")
    os.makedirs(tmp_dir, exist_ok=True)
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    tmp_file = os.path.join(tmp_dir, f"推送_{today}.md")
    with open(tmp_file, "w", encoding="utf-8") as f:
        f.write(report)

    title = f"Token比价站日报_{today}"
    # Windows: npx 是 .cmd 文件，需要 shell=True
    use_shell = sys.platform == "win32"
    tmp_abs = tmp_file.replace("\\", "/")
    cmd = f'npx @larksuite/cli@latest docs +create --api-version v2 --doc-format markdown --title "{title}" --content @{tmp_abs}'

    try:
        result = subprocess.run(
            cmd if use_shell else cmd.split(),
            capture_output=True, text=True, timeout=120, encoding="utf-8",
            cwd=BASE_DIR,
            shell=use_shell
        )
        if result.returncode == 0:
            match = re.search(r'"url":\s*"([^"]+)"', result.stdout)
            if match:
                return match.group(1)
        else:
            print(f"飞书推送失败: {result.stderr}")
    except Exception as e:
        print(f"飞书推送异常: {e}")
    return None

def main():
    print("=" * 50)
    print("  生成每日进度报告...")
    print("=" * 50)

    report = generate_report()
    filepath = save_report(report)
    print(f"\n✅ 报告已保存: {filepath}")

    # 推送飞书
    print("\n📤 推送到飞书...")
    url = push_to_feishu(report)
    if url:
        print(f"✅ 飞书文档: {url}")
    else:
        print("⚠️ 飞书推送失败，报告仅保存在本地")

    print("\n" + report)

if __name__ == "__main__":
    main()
