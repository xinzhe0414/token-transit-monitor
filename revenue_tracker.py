"""
收益追踪器 — 联盟点击 + UV 统计 + 佣金预估
用法:
  python revenue_tracker.py update --uv 150           # 更新今日 UV
  python revenue_tracker.py update --clicks 12         # 更新今日联盟点击
  python revenue_tracker.py update --commission 35     # 新增佣金 ¥35
  python revenue_tracker.py summary                    # 本月汇总
  python revenue_tracker.py export                     # 导出 CSV
"""
import sys
import os
import json
import csv
from datetime import datetime, timezone, timedelta

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TZ = timezone(timedelta(hours=8))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "revenue.json")

def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "today_uv": "0",
        "today_clicks": "0",
        "total_commission": 0,
        "month_estimate": 0,
        "daily_log": [],
        "commission_log": []
    }

def save(data):
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def update_uv(value):
    data = load()
    data["today_uv"] = value
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    data["daily_log"] = [d for d in data["daily_log"] if d.get("date") != today]
    data["daily_log"].append({
        "date": today,
        "uv": value,
        "clicks": data.get("today_clicks", "0"),
        "updated_at": datetime.now(TZ).isoformat()
    })
    save(data)
    print(f"✅ 今日 UV 更新: {value}")

def update_clicks(value):
    data = load()
    data["today_clicks"] = value
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    for d in data["daily_log"]:
        if d.get("date") == today:
            d["clicks"] = value
            break
    save(data)
    print(f"✅ 今日联盟点击更新: {value}")

def add_commission(amount):
    data = load()
    data["total_commission"] = data.get("total_commission", 0) + amount
    data["commission_log"].append({
        "date": datetime.now(TZ).strftime("%Y-%m-%d"),
        "time": datetime.now(TZ).strftime("%H:%M"),
        "amount": amount,
        "source": "affiliate"
    })
    # 更新本月预估
    this_month = datetime.now(TZ).strftime("%Y-%m")
    month_total = sum(
        c["amount"] for c in data["commission_log"]
        if c["date"].startswith(this_month)
    )
    data["month_estimate"] = month_total
    save(data)
    print(f"✅ 新增佣金: ¥{amount} | 本月累计: ¥{month_total}")

def show_summary():
    data = load()
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    this_month = datetime.now(TZ).strftime("%Y-%m")

    # 本月佣金
    month_commission = sum(
        c["amount"] for c in data.get("commission_log", [])
        if c["date"].startswith(this_month)
    )

    # 最近 7 天数据
    recent_days = []
    from datetime import date as dt_date
    for i in range(6, -1, -1):
        d = (datetime.now(TZ) - timedelta(days=i)).strftime("%Y-%m-%d")
        day_data = next((x for x in data.get("daily_log", []) if x.get("date") == d), None)
        recent_days.append({
            "date": d,
            "uv": day_data["uv"] if day_data else "-",
            "clicks": day_data["clicks"] if day_data else "-"
        })

    print(f"""
{'='*56}
  📊 收益追踪汇总 | {today}
{'='*56}

💰 佣金收入
  本月累计: ¥{month_commission}
  历史总计: ¥{data.get('total_commission', 0)}
  本月预估: ¥{data.get('month_estimate', 0)}

📈 最近 7 天流量
{'日期':<12} {'UV':<10} {'联盟点击':<10}
{'-'*34}""")
    for d in recent_days:
        print(f"{d['date']:<12} {str(d['uv']):<10} {str(d['clicks']):<10}")

    # 佣金明细
    recent_commissions = [c for c in data.get("commission_log", []) if c["date"] >= (datetime.now(TZ) - timedelta(days=7)).strftime("%Y-%m-%d")]
    if recent_commissions:
        print(f"\n💵 最近 7 天佣金明细")
        for c in recent_commissions:
            print(f"  {c['date']} {c['time']} | +¥{c['amount']}")

    print()

def export_csv():
    data = load()
    csv_path = os.path.join(BASE_DIR, "data", "revenue_export.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        # 日报表
        writer.writerow(["日期", "UV", "联盟点击"])
        for d in data.get("daily_log", []):
            writer.writerow([d["date"], d.get("uv", 0), d.get("clicks", 0)])

        writer.writerow([])
        writer.writerow(["日期", "时间", "金额", "来源"])
        for c in data.get("commission_log", []):
            writer.writerow([c["date"], c.get("time", ""), c["amount"], c.get("source", "")])

    print(f"✅ 已导出: {csv_path}")

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python revenue_tracker.py update --uv 150        — 更新 UV")
        print("  python revenue_tracker.py update --clicks 12     — 更新点击")
        print("  python revenue_tracker.py update --commission 35 — 新增佣金")
        print("  python revenue_tracker.py summary                — 本月汇总")
        print("  python revenue_tracker.py export                 — 导出 CSV")
        return

    cmd = sys.argv[1]

    if cmd == "update":
        if len(sys.argv) >= 3:
            flag = sys.argv[2]
            val = sys.argv[3] if len(sys.argv) > 3 else "0"
            if flag == "--uv":
                update_uv(val)
            elif flag == "--clicks":
                update_clicks(val)
            elif flag == "--commission":
                add_commission(int(val))
            else:
                print(f"未知参数: {flag}")
    elif cmd == "summary":
        show_summary()
    elif cmd == "export":
        export_csv()
    else:
        print(f"未知命令: {cmd}")

if __name__ == "__main__":
    main()
