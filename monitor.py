"""
中转站监控脚本 — 每10分钟运行一次
检测所有配置的中转站可用性和延迟，写入 data/stations.json
"""
import requests
import json
import time
import os
import sys
import yaml
from datetime import datetime, timezone, timedelta

# Windows 控制台编码兼容
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 北京时间
TZ = timezone(timedelta(hours=8))

def load_config():
    cfg_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def check_station(name, url, timeout=10):
    """检测单个中转站，返回 (status, delay_ms, error_msg)"""
    start = time.time()
    try:
        r = requests.get(url, timeout=timeout, headers={
            "User-Agent": "TokenTransitMonitor/1.0"
        })
        delay = round((time.time() - start) * 1000)
        if r.status_code == 200:
            return "在线", delay, None
        else:
            return f"异常({r.status_code})", delay, f"HTTP {r.status_code}"
    except requests.exceptions.Timeout:
        return "超时", None, "连接超时"
    except requests.exceptions.ConnectionError:
        return "不可达", None, "连接失败"
    except Exception as e:
        return "错误", None, str(e)

def check_alerts(station_name, results, config):
    """检查是否需要告警"""
    alerts = []
    threshold = config.get("alerts", {})
    history = load_history(station_name)

    latest = results[-1] if results else None
    if latest:
        if latest.get("delay_ms") and latest["delay_ms"] > threshold.get("latency_critical_ms", 3000):
            alerts.append(f"🔴 {station_name} 延迟严重: {latest['delay_ms']}ms")
        elif latest.get("delay_ms") and latest["delay_ms"] > threshold.get("latency_warning_ms", 1000):
            alerts.append(f"🟡 {station_name} 延迟偏高: {latest['delay_ms']}ms")

        if latest.get("status") != "在线":
            consecutive = count_consecutive_failures(history)
            if consecutive >= threshold.get("consecutive_failures", 3):
                alerts.append(f"🔴 {station_name} 连续不可达 {consecutive} 次")

    return alerts

def load_history(station_name):
    """加载该站的历史记录"""
    history_file = os.path.join(os.path.dirname(__file__), "data", "history.json")
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            all_history = json.load(f)
        return all_history.get(station_name, [])
    return []

def count_consecutive_failures(history):
    """计算连续失败次数"""
    count = 0
    for record in reversed(history):
        if record.get("status") != "在线":
            count += 1
        else:
            break
    return count

def save_history(results):
    """追加历史记录（保留最近24小时）"""
    history_file = os.path.join(os.path.dirname(__file__), "data", "history.json")
    existing = {}
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            existing = json.load(f)

    now = datetime.now(TZ).isoformat()
    cutoff = (datetime.now(TZ) - timedelta(hours=24)).isoformat()

    for r in results:
        name = r["name"]
        if name not in existing:
            existing[name] = []
        existing[name].append(r)
        # 只保留24小时内的
        existing[name] = [e for e in existing[name] if e.get("time", "") > cutoff]

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

def main():
    config = load_config()
    stations = config.get("stations", [])
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)

    results = []
    all_alerts = []

    for station in stations:
        status, delay, error = check_station(station["name"], station["url"])
        record = {
            "name": station["name"],
            "type": station.get("type", ""),
            "status": status,
            "delay_ms": delay,
            "error": error,
            "time": datetime.now(TZ).isoformat()
        }
        results.append(record)

        # 检查告警
        alerts = check_alerts(station["name"], [record], config)
        all_alerts.extend(alerts)

    # 写入当前状态文件（给前端页面读）
    output = {
        "updated_at": datetime.now(TZ).isoformat(),
        "stations": results,
        "alerts": all_alerts
    }
    output_file = os.path.join(data_dir, "stations.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 追加历史
    save_history(results)

    # 如果有告警，写入告警文件
    if all_alerts:
        alert_file = os.path.join(data_dir, "alerts.json")
        existing_alerts = []
        if os.path.exists(alert_file):
            with open(alert_file, "r", encoding="utf-8") as f:
                existing_alerts = json.load(f)
        for a in all_alerts:
            existing_alerts.append({"time": datetime.now(TZ).isoformat(), "alert": a})
        with open(alert_file, "w", encoding="utf-8") as f:
            json.dump(existing_alerts[-50:], f, ensure_ascii=False, indent=2)  # 保留最近50条

    print(f"[{datetime.now(TZ).strftime('%H:%M:%S')}] 检测完成: {len(results)}个站点, {len(all_alerts)}个告警")
    for alert in all_alerts:
        print(f"  {alert}")

if __name__ == "__main__":
    main()
