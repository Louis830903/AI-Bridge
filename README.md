<div align="center">

<!-- 动态 Logo -->
<img src="docs/assets/social-preview.png" alt="AI-Bridge Banner" width="800"/>

<br/><br/>

<!-- 核心 Slogan - 震撼开场 -->
# 🌉 AI-Bridge

### **From Chat to Action**
### **让 AI 从聊天走向行动**

<br/>

<p>
  <strong>🚀 One line of code. AI controls any desktop app.</strong><br/>
  <strong>🚀 一行代码，AI 操控任意桌面软件</strong>
</p>

<br/>

<!-- 徽章墙 -->
<p>
  <a href="https://github.com/Louis830903/AI-Bridge/stargazers">
    <img src="https://img.shields.io/github/stars/Louis830903/AI-Bridge?style=for-the-badge&logo=github&color=yellow" alt="Stars">
  </a>
  <a href="https://github.com/Louis830903/AI-Bridge/releases">
    <img src="https://img.shields.io/github/v/release/Louis830903/AI-Bridge?style=for-the-badge&color=blue" alt="Release">
  </a>
  <a href="https://python.org">
    <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  </a>
  <a href="https://modelcontextprotocol.io">
    <img src="https://img.shields.io/badge/MCP-Compatible-00D084?style=for-the-badge&logo=anthropic&logoColor=white" alt="MCP">
  </a>
</p>

<p>
  <a href="https://github.com/Louis830903/AI-Bridge/actions">
    <img src="https://img.shields.io/badge/Tests-647%20Passed-success?style=flat-square" alt="Tests">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=flat-square" alt="License">
  </a>
  <a href="https://github.com/Louis830903/AI-Bridge/pulls">
    <img src="https://img.shields.io/badge/PRs-Welcome-brightgreen?style=flat-square" alt="PRs">
  </a>
</p>

<br/>

<!-- 导航 -->
<p>
  <a href="README_CN.md">🇨🇳 中文</a> •
  <a href="#-30-second-demo">⚡ 30s Demo</a> •
  <a href="#-use-cases">🎯 Use Cases</a> •
  <a href="#-quick-start">🚀 Quick Start</a> •
  <a href="#-architecture">🏗️ Architecture</a>
</p>

</div>

---

<br/>

<!-- Demo GIF 展示区 -->
<div align="center">

## ⚡ 30-Second Demo

<!-- 演示图片 -->
<table>
<tr>
<td align="center">

```python
import asyncio
from aibridge.adapters.browser.chrome import ChromeAdapter

async def main():
    # 1. 初始化浏览器
    adapter = ChromeAdapter({"headless": False})
    await adapter.connect()
    
    # 2. 打开网页
    await adapter.execute("goto", value="https://github.com")
    
    # 3. 截图保存
    await adapter.execute("screenshot", options={"path": "github.png"})
    
    await adapter.disconnect()

asyncio.run(main())
```

</td>
</tr>
</table>

**☝️ AI automatically: Opens Chrome → Navigates to GitHub → Takes Screenshot**

</div>

<br/>

---

## 🎯 Use Cases

<table>
<tr>
<td width="25%" align="center">

### 🎬 Auto Video Edit

```
"Cut this video to 30s,
add background music,
export as 1080p"
     ↓
AI-Bridge + FFmpeg
     ↓
✅ Done in seconds
```

</td>
<td width="25%" align="center">

### 📊 Auto Report

```
"Get sales data from Excel,
generate charts,
create PPT report"
     ↓
AI-Bridge + Office
     ↓
✅ Professional report
```

</td>
<td width="25%" align="center">

### 🌐 Web Automation

```
"Login to website,
scrape product info,
save to database"
     ↓
AI-Bridge + Chrome
     ↓
✅ Data collected
```

</td>
<td width="25%" align="center">

### 🤖 Multi-Agent

```
"Research AI news,
analyze trends,
send summary to Slack"
     ↓
AI-Bridge + A2A
     ↓
✅ Agents collaborate
```

</td>
</tr>
</table>

---

## 🔥 Why AI-Bridge?

<table>
<tr>
<td width="50%">

### ❌ Before: AI Can Only Chat

```
User: "Edit this video"
AI:   "I can't do that, but here's
       how you could do it manually..."
```

**AI is limited to text responses** 😞

</td>
<td width="50%">

### ✅ After: AI Takes Action

```
User: "Edit this video"
AI:   *Opens FFmpeg*
      *Processes video*
      *Exports result*
      "Done! Here's your video."
```

**AI actually does the work** 🚀

</td>
</tr>
</table>

<br/>

<div align="center">

### ⚡ The Magic Behind

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Your AI       │     │   AI-Bridge     │     │   Any App       │
│ (Claude, GPT)   │ ──▶ │   Gateway       │ ──▶ │ Chrome, Office  │
│                 │ MCP │                 │     │ FFmpeg, Docker  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

</div>

---

## 🚀 Quick Start

### 1️⃣ Install

```bash
pip install ai-bridge
```

### 2️⃣ Add to Claude Desktop

```json
{
  "mcpServers": {
    "ai-bridge": {
      "command": "python",
      "args": ["-m", "aibridge"]
    }
  }
}
```

### 3️⃣ Done! Ask Claude to:

```
"Open Chrome and take a screenshot of github.com"
"Convert this video to MP3"
"Create an Excel report from this data"
```

---

## 🛠️ Supported Tools

<div align="center">

| Category | Tools |
|:--------:|-------|
| 🌐 **Browser** | Chrome, Edge (Playwright-powered) |
| 📊 **Office** | Word, Excel, PowerPoint, WPS |
| 🎬 **Media** | FFmpeg, ImageMagick, Blender, SoX |
| 📄 **Docs** | Pandoc (40+ formats) |
| 🎵 **Download** | yt-dlp (1000+ sites) |
| 🐳 **DevOps** | Docker, Prettier |
| 🔗 **MCP Ecosystem** | Browser Use, Firecrawl, Notion, Slack, GitHub |

</div>

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI Assistant                              │
│              (Claude, GPT, Qwen, Gemini, etc.)                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ MCP / A2A Protocol
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  AI-Bridge v5.0 Gateway                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  v5.0 Protocol Extension                                   │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────┐ │  │
│  │  │Agent Card  │ │ Prometheus │ │A2A Streaming│ │MCP Disco│ │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └─────────┘ │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  v4.0 Enterprise Layer                                     │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────┐ │  │
│  │  │  Policy    │ │  Metering  │ │  Tracing   │ │Orchestr │ │  │
│  │  │  Engine    │ │  Collector │ │   (OTel)   │ │  (DAG)  │ │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └─────────┘ │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │MCP Registry  │  │ A2A Gateway  │  │  Protocol Bridge   │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┬──────────────────┐
        ▼                   ▼                   ▼                  ▼
   ┌─────────┐         ┌─────────┐         ┌─────────┐       ┌─────────┐
   │ Browser │         │  Office │         │   CLI   │       │   MCP   │
   │ Adapter │         │ Adapter │         │ Adapter │       │Ecosystem│
   └─────────┘         └─────────┘         └─────────┘       └─────────┘
        │                   │                   │                  │
   Chrome/Edge          Word/Excel         FFmpeg/Docker      Firecrawl
                        PowerPoint         yt-dlp/Pandoc      Notion/Slack
```

---

## 📊 Enterprise Features

<details>
<summary><b>🔐 Policy-Based Access Control</b></summary>

```python
from aibridge.enterprise import PolicyEngine, ToolPolicy

policy_engine = PolicyEngine()
policy = ToolPolicy(
    policy_id="dev-policy",
    statements=[{
        "effect": "allow",
        "actions": ["tool:call"],
        "resources": ["browser/*", "ffmpeg/*"],
    }]
)
policy_engine.register_policy(policy)
```

</details>

<details>
<summary><b>📈 Usage Metering & Quota</b></summary>

```python
from aibridge.enterprise import MeteringCollector, QuotaManager

metering = MeteringCollector()
await metering.record(user_id="user1", tool_name="browser/navigate")

quota = QuotaManager(metering)
quota.set_user_quota("user1", QuotaConfig(max_calls_per_day=1000))
```

</details>

<details>
<summary><b>🔍 Distributed Tracing (OpenTelemetry)</b></summary>

```python
from aibridge.enterprise import Tracer, TracerConfig

tracer = Tracer(TracerConfig(service_name="my-service"))
with tracer.start_as_current_span("tool_call") as span:
    span.set_attribute("user.id", "user1")
    # ... execute tool
```

</details>

<details>
<summary><b>🤖 Multi-Agent Orchestration</b></summary>

```python
from aibridge.core import TaskGraph, Orchestrator

graph = TaskGraph(name="research-workflow")
t1 = graph.add_task("search", "search-agent", "web_search")
t2 = graph.add_task("analyze", "analyzer-agent", depends_on={t1.task_id})
result = await orchestrator.execute(graph)
```

</details>

---

## 📖 Documentation

| Resource | Link |
|----------|------|
| 📚 Quick Start | [examples/basic_usage.py](ai-bridge/examples/basic_usage.py) |
| 🏗️ Gateway Demo | [examples/gateway_demo.py](ai-bridge/examples/gateway_demo.py) |
| 📋 Changelog | [CHANGELOG.md](ai-bridge/CHANGELOG.md) |
| 🤝 Contributing | [CONTRIBUTING.md](ai-bridge/CONTRIBUTING.md) |

---

## 🌟 Star History

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=Louis830903/AI-Bridge&type=Date)](https://star-history.com/#Louis830903/AI-Bridge&Date)

</div>

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](ai-bridge/CONTRIBUTING.md).

```bash
git clone https://github.com/Louis830903/AI-Bridge.git
cd AI-Bridge/ai-bridge
pip install -e ".[dev]"
pytest tests/ -v
```

---

## 📄 License

Apache 2.0 — see [LICENSE](LICENSE)

---

<div align="center">

### 🙏 Acknowledgements

[Playwright](https://playwright.dev/) • [MCP](https://modelcontextprotocol.io/) • [A2A](https://google.github.io/a2a-spec/) • [All Contributors](https://github.com/Louis830903/AI-Bridge/graphs/contributors) ❤️

<br/>

---

<br/>

**If AI-Bridge helps you, please give us a ⭐!**

<br/>

```
     _    ___      ____       _     _            
    / \  |_ _|    | __ ) _ __(_) __| | __ _  ___ 
   / _ \  | |_____|  _ \| '__| |/ _` |/ _` |/ _ \
  / ___ \ | |_____| |_) | |  | | (_| | (_| |  __/
 /_/   \_\___|    |____/|_|  |_|\__,_|\__, |\___|
                                      |___/      

         From Chat to Action 🚀
```

<br/>

**Made with ❤️ for the AI Automation Community**

</div>
