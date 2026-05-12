"""
自动化工作流编排器
用法:
  python automation.py monitor     # 执行一次监控
  python automation.py report      # 生成并推送日报
  python automation.py loop        # 持续循环监控(每10分钟)
  python automation.py task-done 1.1  # 标记任务完成
  python automation.py status      # 查看当前进度
"""
import sys
import os
import time
import json
import yaml
import subprocess
from datetime import datetime, timezone, timedelta

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TZ = timezone(timedelta(hours=8))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run_monitor():
    """执行一次监控"""
    print(f"[{datetime.now(TZ).strftime('%H:%M:%S')}] 执行监控...")
    subprocess.run([sys.executable, os.path.join(BASE_DIR, "monitor.py")])

def run_report():
    """生成并推送日报"""
    print(f"[{datetime.now(TZ).strftime('%H:%M:%S')}] 生成日报...")
    subprocess.run([sys.executable, os.path.join(BASE_DIR, "daily_report.py")])

def mark_task_done(task_id):
    """标记任务完成"""
    tasks_path = os.path.join(BASE_DIR, "tasks.yaml")
    with open(tasks_path, "r", encoding="utf-8") as f:
        content = f.read()

    if task_id in content:
        # 把 status: pending 或 status: in_progress 改为 status: done
        import re
        pattern = rf"(id:\s*[\"']?{re.escape(task_id)}[\"']?\n.*?status:\s*)(pending|in_progress)"
        new_content = re.sub(pattern, rf"\g<1>done", content, flags=re.DOTALL)
        with open(tasks_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"✅ 任务 {task_id} 已标记完成")
    else:
        print(f"❌ 未找到任务 {task_id}")

def show_status():
    """显示当前进度"""
    tasks_path = os.path.join(BASE_DIR, "tasks.yaml")
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = yaml.safe_load(f)

    print("\n" + "=" * 50)
    print("  Token 比价站 · 任务进度")
    print("=" * 50)

    total = 0
    done = 0
    for day_block in tasks.get("days", []):
        day = day_block["day"]
        title = day_block["title"]
        print(f"\n📅 Day {day}: {title}")
        print("-" * 40)
        for task in day_block.get("tasks", []):
            total += 1
            status = task.get("status", "pending")
            icon = {"done": "✅", "in_progress": "🔄", "pending": "⬜", "skipped": "⏭️"}.get(status, "❓")
            if status == "done":
                done += 1
            print(f"  {icon} [{task['id']}] {task['name']} ({task['time']})")

    pct = round(done / total * 100) if total > 0 else 0
    print(f"\n{'=' * 50}")
    print(f"  总进度: {done}/{total} ({pct}%)")
    print("=" * 50)

    # 自动化任务状态
    print("\n🤖 自动化任务:")
    for at in tasks.get("automated_tasks", []):
        icon = "✅" if at.get("script") else "📝"
        print(f"  {icon} {at['name']} — {at['frequency']}")

def monitor_loop():
    """持续监控循环"""
    print("🔄 启动持续监控模式 (Ctrl+C 退出)")
    print(f"   每10分钟检测一次，日报每天21:00推送\n")

    last_report_date = ""

    try:
        while True:
            run_monitor()

            # 检查是否到了推送日报的时间
            now = datetime.now(TZ)
            today = now.strftime("%Y-%m-%d")
            if now.hour >= 21 and last_report_date != today:
                print(f"\n📤 到推送时间了，生成日报...")
                run_report()
                last_report_date = today

            # 等待10分钟
            next_run = now + timedelta(minutes=10)
            print(f"   下次检测: {next_run.strftime('%H:%M:%S')}")
            time.sleep(600)

    except KeyboardInterrupt:
        print("\n👋 监控已停止")

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python automation.py monitor    — 执行一次监控")
        print("  python automation.py report     — 生成并推送日报")
        print("  python automation.py loop       — 持续监控循环")
        print("  python automation.py task-done <任务ID> — 标记任务完成")
        print("  python automation.py status     — 查看任务进度")
        return

    cmd = sys.argv[1]

    if cmd == "monitor":
        run_monitor()
    elif cmd == "report":
        run_report()
    elif cmd == "loop":
        monitor_loop()
    elif cmd == "task-done":
        if len(sys.argv) < 3:
            print("请指定任务ID，如: python automation.py task-done 1.1")
        else:
            mark_task_done(sys.argv[2])
    elif cmd == "status":
        show_status()
    else:
        print(f"未知命令: {cmd}")

if __name__ == "__main__":
    main()
