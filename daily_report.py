"""
每日进度报告生成器 — 每天21:00运行
输出: reports/日报_YYYY-MM-DD.md + 飞书推送
"""
import json
import os
import sys
import yaml
from datetime import datetime, timezone, timedelta

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from collections import defaultdict

TZ = timezone(timedelta(hours=8))

def load_data():
    """加载今日监控数据"""
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    stations_file = os.path.join(data_dir, "stations.json")
    history_file = os.path.join(data_dir, "history.json")
    alerts_file = os.path.join(data_dir, "alerts.json")

    current = {}
    history = {}
    alerts = []

    if os.path.exists(stations_file):
        with open(stations_file, "r", encoding="utf-8") as f:
            current = json.load(f)
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
    if os.path.exists(alerts_file):
        with open(alerts_file, "r", encoding="utf-8") as f:
            alerts = json.load(f)

    return current, history, alerts

def load_tasks():
    """加载任务清单"""
    tasks_path = os.path.join(os.path.dirname(__file__), "tasks.yaml")
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

def generate_report():
    """生成每日报告"""
    current, history, alerts = load_data()
    tasks = load_tasks()
    uptime = calc_uptime(history)
    latency = calc_avg_latency(history)
    now = datetime.now(TZ)
    today_str = now.strftime("%Y-%m-%d")

    # 待办事项
    todo_items = []
    for day_block in tasks.get("days", []):
        for task in day_block.get("tasks", []):
            if task.get("status") in ("pending", "in_progress"):
                todo_items.append(f"- [ ] **[{task['id']}] {task['name']}** (Day{day_block['day']} | {task['time']})")

    # 今日告警
    today_alerts = [a for a in alerts if a.get("time", "").startswith(today_str)]

    # 收益数据（手动维护，从 data/revenue.json 读取）
    revenue = load_revenue()

    report = f"""# Token 比价站 · 每日进度报告

> 📅 {now.strftime('%Y年%m月%d日 %A')} | 自动生成于 {now.strftime('%H:%M')}

---

## 📊 今日收益概览

| 指标 | 数值 |
|------|------|
| 今日页面 UV | {revenue.get('today_uv', '未统计')} |
| 今日联盟点击 | {revenue.get('today_clicks', '未统计')} |
| 累计佣金收入 | ¥{revenue.get('total_commission', 0)} |
| 本月预估收入 | ¥{revenue.get('month_estimate', 0)} |

---

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
        for a in today_alerts[-10:]:  # 最多显示10条
            report += f"- {a['time'][:19]} | {a['alert']}\n"
    else:
        report += "> ✅ 今日无异常告警，所有站点运行正常。\n"

    # 待办事项
    report += f"""
---

## 📋 待办事项

"""
    if todo_items:
        for item in todo_items[:8]:
            report += f"{item}\n"
    else:
        report += "> ✅ 当前无待办任务。\n"

    # 长期自动化任务状态
    report += f"""
---

## 🤖 自动化任务运行状态

| 任务 | 频率 | 状态 |
|------|------|------|
| 中转站可用性监控 | 每10分钟 | ✅ 运行中 |
| 每日报告生成 | 每天21:00 | ✅ 本次报告 |
| 风险预警扫描 | 每30分钟 | ✅ 运行中 |
| 每周竞品追踪 | 每周一 | ⏳ 下次: 下周一 |
| 文章引流 | 每月2篇 | 📝 按计划 |

---

## 🎯 下一步行动建议

1. 检查待办事项中的任务，优先完成 Day{tasks['meta']['current_day']} 的节点
2. 如有告警站，登录确认是中转站挂了还是检测误报
3. 每周至少写 1 篇引流文章，保持搜索排名
"""

    return report

def load_revenue():
    """加载收益数据"""
    revenue_file = os.path.join(os.path.dirname(__file__), "data", "revenue.json")
    if os.path.exists(revenue_file):
        with open(revenue_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "today_uv": "未统计",
        "today_clicks": "未统计",
        "total_commission": 0,
        "month_estimate": 0
    }

def save_report(report):
    """保存报告到本地"""
    reports_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    filepath = os.path.join(reports_dir, f"日报_{today}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)
    return filepath

def push_to_feishu(report):
    """推送到飞书文档"""
    import subprocess

    tmp_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(tmp_dir, exist_ok=True)
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    tmp_file = os.path.join(tmp_dir, f"推送_{today}.md")
    with open(tmp_file, "w", encoding="utf-8") as f:
        f.write(report)

    title = f"Token比价站日报_{today}"
    # Windows 下 npx 是 .cmd 文件，需要 shell=True
    use_shell = sys.platform == "win32"
    cmd = f'npx @larksuite/cli@latest docs +create --api-version v2 --doc-format markdown --title "{title}" --content @{tmp_file}'
    try:
        result = subprocess.run(
            cmd if use_shell else cmd.split(),
            capture_output=True, text=True, timeout=120, encoding="utf-8",
            cwd=os.path.dirname(__file__),
            shell=use_shell
        )
        if result.returncode == 0:
            import re
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
