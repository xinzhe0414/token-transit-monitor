"""
客户常见问题自动回复 — 模板匹配 + 快速复制
用法:
  python auto_responder.py list            # 列出所有模板
  python auto_responder.py search "封号"   # 搜索匹配模板
  python auto_responder.py show 1          # 显示第1个模板完整内容
  python auto_responder.py stats           # 查看回复统计
  python auto_responder.py used "封号"     # 标注该模板被使用
"""
import sys
import os
import json
import yaml
from datetime import datetime, timezone, timedelta

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TZ = timezone(timedelta(hours=8))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

REPLY_TEMPLATES = [
    {
        "id": 1,
        "tags": ["封号", "安全", "API Key"],
        "question": "用中转站会被 OpenAI 封号吗？",
        "reply": """**短答**：正规官转站不会，灰产站有风险。

**详细说明**：
- 官转站（OpenRouter/YesCode/oaipro）从 OpenAI 官方渠道采购 API，和你直连完全一样
- OpenAI 封的是违反 ToS 的行为（非支持地区直连 + 逆向账号），不是正常 API 调用
- 判断依据：如果你拿到的是 `sk-` 开头的 Key → 官转。如果是其他格式 → 可能是逆向账号

**建议**：只用官转站，不用 0.1 倍率以下的灰产站。本站评测表标注了每家类型（官转🟢/混合🟡/灰产🔴）。""",
        "used_count": 0
    },
    {
        "id": 2,
        "tags": ["价格", "便宜", "对比"],
        "question": "为什么中转站比官方还便宜？",
        "reply": """**短答**：正规站的便宜来自「批量折扣」和「地区价差」，不是歪门邪道。

**几个合法原因**：
1. **批量采购**：官转站月消耗百万刀级别，拿到的批发价远低于零售价
2. **Prompt 缓存套利**：重复 System Prompt 官方半价，中转站可能原价收但对用户还是比官网便宜
3. **Batch API 套利**：非紧急请求打包走 Batch API（官方 5 折）
4. **补贴期**：新站为了抢用户，前几个月不赚钱甚至倒贴

**警惕信号**：如果价格低到官方 0.3 折以下 → 大概率是逆向账号拼车或模型掉包。""",
        "used_count": 0
    },
    {
        "id": 3,
        "tags": ["延迟", "速度", "卡"],
        "question": "哪个中转站延迟最低？",
        "reply": """**短答**：看实时数据最准 → 本站监控表每小时更新。

**一般规律**：
- **日本/新加坡节点**：对国内延迟最低（60-150ms）
- **美国节点**：延迟高（200-400ms）但稳定
- **香港节点**：延迟最低（30-80ms）但容易被墙

**本站推荐**（2026年5月实测）：
1. YesCode — 日本节点，平均 120ms
2. oaipro — 香港节点，平均 80ms
3. OpenRouter — 美国节点，平均 250ms 但最稳定

> 实际延迟和你本地网络有关，建议各站都试一下。""",
        "used_count": 0
    },
    {
        "id": 4,
        "tags": ["注册", "支付", "充值"],
        "question": "怎么注册和充值？支持微信/支付宝吗？",
        "reply": """**各站支付方式汇总**：

| 站名 | 支付方式 | 最低充值 |
|------|---------|---------|
| OpenRouter | 信用卡/PayPal/USDT | $5 |
| YesCode | 微信/支付宝/对公转账 | ¥10 |
| oaipro | 微信/支付宝 | ¥10 |
| Cubence | 微信/支付宝/信用卡 | ¥20 |
| Duck Code | 微信/支付宝 | ¥10 |

**新手建议**：先充 ¥10-20 试水，确认能用再追加。不要一次性充大额。""",
        "used_count": 0
    },
    {
        "id": 5,
        "tags": ["模型", "真假", "掉包"],
        "question": "怎么确认中转站返回的是真模型，不是 Qwen 冒充的？",
        "reply": """**用 hvoy.ai 验证** → https://hvoy.ai

**手动验证法**：
1. 问「用中文重复我说的话」→ Qwen 会逐字重复，Claude 会先理解再转述
2. 问「写一首关于月亮的七言绝句」→ 对比不同模型的输出风格
3. 写代码任务 → Claude Opus 的代码质量明显更高

**本站保障**：评测表标注了每家站的模型真伪状态。我们定期用 hvoy.ai 批量检测。

> 如果你怀疑某站掉包，欢迎反馈，我们手动核实。""",
        "used_count": 0
    },
    {
        "id": 6,
        "tags": ["跑路", "风险", "充值安全"],
        "question": "充了钱中转站跑路了怎么办？",
        "reply": """**短答**：这就是为什么我们只推荐官转站。

**降低风险的方法**：
1. **单次充值 ≤ ¥200**：不囤大额余额
2. **用光再充**：不要因为优惠就充年卡
3. **1 主 + 2 备**：不要只依赖一家
4. **看运营时间**：运营 < 6 个月的站跑路概率最高

**本站立场**：
- 🟢 官转站（OpenRouter/YesCode/oaipro/Cubence）：跑路概率极低，有投资人背书
- 🟡 个人站（Duck Code/PackyCode）：运营超 1 年，口碑好但仍有风险
- 🔴 新站/灰产站：不推荐，随时可能跑路

> 本站不卖 Token、不收佣金预付款，只提供中立评测。""",
        "used_count": 0
    },
    {
        "id": 7,
        "tags": ["接入", "代码", "BASE_URL"],
        "question": "怎么接入？需要改代码吗？",
        "reply": """**不需要改代码，只改 2 行配置**：

```python
# OpenAI SDK
import openai
client = openai.OpenAI(
    base_url="https://api.oaipro.com/v1",  # 改这里
    api_key="sk-xxxxxxxx"                   # 改这里
)
```

```bash
# Claude Code / 其他 CLI
export OPENAI_BASE_URL="https://api.oaipro.com/v1"
export OPENAI_API_KEY="sk-xxxxxxxx"
```

**各站的接入文档**：
- OpenRouter: https://openrouter.ai/docs
- YesCode: 注册后在后台看文档
- oaipro: 同上

> 如果你用的是 Claude Code，改 `ANTHROPIC_BASE_URL` 环境变量即可。""",
        "used_count": 0
    },
    {
        "id": 8,
        "tags": ["Claude", "封号", "Anthropic"],
        "question": "用中转站能用 Claude 吗？被封了怎么办？",
        "reply": """**可以用，但有注意事项**：

1. **Claude 对非支持地区管控更严**：2025.9 Anthropic 停止向中国资本控股公司提供 Claude
2. **官转站目前仍可用**：OpenRouter/YesCode 等通过海外实体采购
3. **风险在上升**：Anthropic 2026.4 已收紧 Claude 订阅政策，不排除进一步收紧 API

**兜底方案**：
- DeepSeek V4 性能接近 Claude，¥3-6/百万 Token
- 通义千问 Qwen3.6 免费额度充裕
- 不要把全部工作流依赖一家模型

> 本站监控会在 Claude 中转大面积不可用时第一时间告警。""",
        "used_count": 0
    }
]

def load_stats():
    stats_file = os.path.join(BASE_DIR, "data", "reply_stats.json")
    if os.path.exists(stats_file):
        with open(stats_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"total_used": 0, "templates": {}}

def save_stats(stats):
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    with open(os.path.join(BASE_DIR, "data", "reply_stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def mark_used(tag_or_id):
    stats = load_stats()
    stats["total_used"] += 1

    # 按 ID 或标签匹配
    for t in REPLY_TEMPLATES:
        if str(t["id"]) == tag_or_id or tag_or_id in t["tags"]:
            tid = str(t["id"])
            stats["templates"][tid] = stats["templates"].get(tid, 0) + 1
            t["used_count"] += 1
            print(f"✅ 模板「{t['question']}」使用次数 +1")
            save_stats(stats)
            return
    print(f"❌ 未找到匹配模板: {tag_or_id}")

def list_templates():
    print("\n📋 自动回复模板库\n")
    print(f"{'ID':<4} {'标签':<25} {'问题':<40} {'使用':<6}")
    print("-" * 78)
    for t in REPLY_TEMPLATES:
        tags = " ".join(t["tags"])
        q = t["question"][:38] + (".." if len(t["question"]) > 38 else "")
        print(f"{t['id']:<4} {tags:<25} {q:<40} {t['used_count']:<6}")

def search_templates(keyword):
    results = [t for t in REPLY_TEMPLATES if keyword in t["question"] or keyword in " ".join(t["tags"])]
    if not results:
        print(f"❌ 未找到包含「{keyword}」的模板")
        return
    for t in results:
        print(f"\n{'='*60}")
        print(f"[{t['id']}] {t['question']}")
        print(f"标签: {', '.join(t['tags'])} | 已使用: {t['used_count']} 次")
        print(f"{'='*60}")
        print(t["reply"])

def show_template(tid):
    for t in REPLY_TEMPLATES:
        if str(t["id"]) == tid:
            print(f"\n{'='*60}")
            print(f"[{t['id']}] {t['question']}")
            print(f"标签: {', '.join(t['tags'])} | 已使用: {t['used_count']} 次")
            print(f"{'='*60}")
            print(t["reply"])
            return
    print(f"❌ 未找到模板 {tid}")

def show_stats():
    stats = load_stats()
    print(f"\n📊 自动回复统计")
    print(f"总使用次数: {stats['total_used']}")
    print(f"\n各模板使用排行:")
    print(f"{'ID':<4} {'问题':<45} {'次数':<6}")
    print("-" * 58)
    sorted_items = sorted(stats.get("templates", {}).items(), key=lambda x: x[1], reverse=True)
    for tid, count in sorted_items:
        t = next((x for x in REPLY_TEMPLATES if str(x["id"]) == tid), None)
        q = t["question"][:43] + ".." if t and len(t["question"]) > 43 else (t["question"] if t else "未知")
        print(f"{tid:<4} {q:<45} {count:<6}")

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python auto_responder.py list          — 列出所有模板")
        print("  python auto_responder.py search <关键词> — 搜索模板")
        print("  python auto_responder.py show <ID>     — 显示完整内容")
        print("  python auto_responder.py used <标签/ID> — 标注使用")
        print("  python auto_responder.py stats         — 查看统计")
        return

    cmd = sys.argv[1]

    if cmd == "list":
        list_templates()
    elif cmd == "search":
        keyword = sys.argv[2] if len(sys.argv) > 2 else ""
        search_templates(keyword)
    elif cmd == "show":
        tid = sys.argv[2] if len(sys.argv) > 2 else "1"
        show_template(tid)
    elif cmd == "used":
        tag = sys.argv[2] if len(sys.argv) > 2 else ""
        mark_used(tag)
    elif cmd == "stats":
        show_stats()
    else:
        print(f"未知命令: {cmd}")

if __name__ == "__main__":
    main()
