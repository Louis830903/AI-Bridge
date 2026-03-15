<div align="center">

```
     _    ___      ____       _     _            
    / \  |_ _|    | __ ) _ __(_) __| | __ _  ___ 
   / _ \  | |_____|  _ \| '__| |/ _` |/ _` |/ _ \
  / ___ \ | |_____| |_) | |  | | (_| | (_| |  __/
 /_/   \_\___|    |____/|_|  |_|\__,_|\__, |\___|
                                      |___/      
```

<h1>🌉 AI-Bridge</h1>

<p>
  <strong>MCP + A2A Dual Protocol Gateway</strong><br>
  <strong>MCP + A2A 双协议网关</strong>
</p>

<p>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=flat-square" alt="License">
  </a>
  <a href="https://python.org">
    <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  </a>
  <a href="https://modelcontextprotocol.io">
    <img src="https://img.shields.io/badge/MCP-Compatible-00D084?style=flat-square&logo=anthropic&logoColor=white" alt="MCP">
  </a>
  <a href="https://github.com/Louis830903/AI-Bridge/releases">
    <img src="https://img.shields.io/github/v/release/Louis830903/AI-Bridge?style=flat-square&color=blue" alt="Release">
  </a>
  <a href="https://github.com/Louis830903/AI-Bridge/stargazers">
    <img src="https://img.shields.io/github/stars/Louis830903/AI-Bridge?style=flat-square&color=yellow" alt="Stars">
  </a>
</p>

<p>
  <a href="README_CN.md">🇨🇳 中文版</a> •
  <a href="#-quick-start">🚀 Quick Start</a> •
  <a href="#-features">✨ Features</a> •
  <a href="#-architecture">🏗️ Architecture</a>
</p>

<p><strong>🚀 One Gateway. Both Protocols. Infinite Possibilities.</strong></p>

</div>

---

## 📢 What's New | 最新动态

```diff
🎉 v4.0.0 - Enterprise Management Layer!
+ Policy Engine - Tool-level access control (PBAC)
+ Metering System - Usage tracking and cost estimation
+ Distributed Tracing - OpenTelemetry compatible tracing
+ Multi-Agent Orchestrator - DAG-based task scheduling
+ Protocol Bridge Enhancement - Bidirectional MCP ↔ A2A conversion
+ 473+ Tests - Comprehensive test coverage

🔧 v3.0.0 - Protocol Gateway Architecture!
+ MCP + A2A Dual Protocol Gateway - Unified entry point for AI tools
+ Browser Connector - Proxy to mature MCP Servers (Browser Use, Chrome DevTools, Playwright)
+ Protocol Bridge - MCP ↔ A2A interoperability  
+ Service Discovery - Health check and auto-failover
+ Enterprise Features - Auth, Audit, Rate Limiting, Health Check
+ CLI Tool Adapters - FFmpeg, Pandoc, yt-dlp, ImageMagick, SoX, Prettier, Docker
+ MCP Connectors - SQLite, Firecrawl, Notion, Slack
```

---

## 🔥 Why AI-Bridge?

<table>
<tr>
<td width="50%">

### ❌ The Old Way
```
Each AI Tool → Different Protocol → Different Integration
      ↓
  🐢 Slow integration
  💥 Fragmented ecosystem
  🎯 Inconsistent APIs
  🌍 No interoperability
```

</td>
<td width="50%">

### ✅ The AI-Bridge Way
```
Any AI Tool → AI-Bridge Gateway → MCP or A2A Protocol
      ↓
  ⚡ Unified entry point
  🔒 Protocol interoperability
  🎯 Consistent experience
  🌍 Enterprise-ready
```

</td>
</tr>
</table>

---

## ⚡ Features

<div align="center">

| | Feature | Description |
|---|---------|-------------|
| 🔗 | **Protocol Gateway** | MCP + A2A dual protocol support, unified entry point |
| 🤖 | **Universal AI Support** | Claude, GPT, Qwen, Gemini, any MCP-compatible AI |
| 🌐 | **Browser Connector** | Proxy to Browser Use, Chrome DevTools MCP, Playwright MCP |
| 🛠️ | **CLI Tool Adapters** | FFmpeg, Pandoc, yt-dlp, ImageMagick, Blender, SoX, Prettier, Docker |
| 📊 | **Office Suite** | Word, Excel, PowerPoint, WPS Office |
| 🔐 | **Enterprise Features** | Auth, Audit, Rate limiting, Policy-based access control |
| 📊 | **Metering & Quota** | Usage tracking, cost estimation, quota management |
| 🔍 | **Distributed Tracing** | OpenTelemetry compatible, cross-service tracing |
| 🧠 | **Multi-Agent** | A2A protocol, DAG orchestrator for agent collaboration |

</div>

---

## 🚀 Quick Start

### Installation

```bash
# Basic installation
pip install ai-bridge

# With browser support
pip install ai-bridge[browser]

# With all features
pip install ai-bridge[all]
```

### As MCP Server (Claude Desktop)

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "ai-bridge": {
      "command": "python",
      "args": ["-m", "aibridge"],
      "env": {
        "AIBRIDGE_CHROME_ENABLED": "true"
      }
    }
  }
}
```

### v3.0 - Protocol Gateway

```python
import asyncio
from aibridge.connectors.mcp import BrowserConnector, BrowserConnectorConfig
from aibridge.connectors.mcp.browser import BrowserBackend

async def main():
    # 1. Create browser connector (auto-select available backend)
    config = BrowserConnectorConfig(
        name="browser",
        backend=BrowserBackend.AUTO,  # Browser Use, Chrome DevTools, or Playwright
        headless=True,
    )
    connector = BrowserConnector(config)
    
    async with connector:
        # 2. Navigate to website
        await connector.navigate("https://www.google.com")
        
        # 3. Type in search box
        await connector.type("input[name=q]", "AI-Bridge MCP")
        
        # 4. Click search button
        await connector.click("input[name=btnK]")
        
        # 5. Take screenshot
        await connector.screenshot("result.png")

asyncio.run(main())
```

### Direct Adapter Usage

```python
import asyncio
from aibridge.adapters.browser.chrome import ChromeAdapter
from aibridge.core.protocol import Target

async def main():
    adapter = ChromeAdapter({"headless": True})
    await adapter.connect()
    
    await adapter.execute(action="goto", value="https://github.com")
    await adapter.execute(action="screenshot", options={"path": "result.png"})
    
    await adapter.disconnect()

asyncio.run(main())
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AI Assistant                             │
│         (Claude, GPT, Qwen, Gemini, etc.)                   │
└────────────────────┬────────────────────────────────────────┘
                     │ MCP / A2A Protocol
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              AI-Bridge v4.0 Protocol Gateway                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │             Enterprise Management Layer (v4.0)            │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │  │
│  │  │  Policy  │ │ Metering │ │ Tracing  │ │Orchestrator│ │  │
│  │  │  Engine  │ │ Collector│ │  (OTel)  │ │   (DAG)  │ │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ │  │
│  └─────────────────────────────────────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ MCP Registry │  │ A2A Gateway  │  │Protocol Bridge│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │     Auth     │  │    Audit     │  │ Rate Limiter │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┼───────────┬───────────┐
         ▼           ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
    │ Browser │ │  Office │ │   CLI   │ │   MCP   │
    │Connector│ │Adapters │ │Adapters │ │Ecosystem│
    └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

---

## 🛠️ Supported Tools

### Browser Automation
- **Chrome** - Full browser control via Playwright
- **Edge** - Microsoft Edge automation

### Office Suite
- **Word** - Document creation and editing
- **Excel** - Spreadsheet automation
- **PowerPoint** - Presentation management
- **WPS Office** - Chinese office suite support

### CLI Tool Adapters
- **FFmpeg** - Video/audio processing
- **Pandoc** - Document conversion
- **yt-dlp** - Video downloading
- **ImageMagick** - Image manipulation
- **Blender** - 3D rendering
- **Playwright** - Browser automation CLI
- **SoX** - Audio processing (convert, trim, concat, effects)
- **Prettier** - Code formatting (multi-language support)
- **Docker** - Container operations (images, containers, volumes)

### MCP Ecosystem Connectors
- **Browser** - Proxy to Browser Use, Chrome DevTools MCP, Playwright MCP
- **Database** - PostgreSQL, MySQL, SQLite via MCP
- **Filesystem** - File operations via MCP
- **GitHub** - Repository operations via MCP
- **SQLite** - Lightweight database (query, execute, tables)
- **Firecrawl** - Web scraping (scrape, crawl, search, extract)
- **Notion** - Team collaboration (pages, databases, blocks)
- **Slack** - Communication (messages, channels, files)

---

## 🔐 Enterprise Features

### v4.0 - Enterprise Management Layer

```python
from aibridge.enterprise import (
    PolicyEngine, ToolPolicy, PolicyEffect, PolicyAction,  # Access Control
    MeteringCollector, QuotaManager, QuotaConfig,          # Usage Metering
    Tracer, TracerConfig, SpanKind,                        # Distributed Tracing
)
from aibridge.core import TaskGraph, Orchestrator          # Multi-Agent

# 1. Policy-Based Access Control (PBAC)
policy_engine = PolicyEngine()
policy = ToolPolicy(
    policy_id="dev-policy",
    name="Developer Policy",
    statements=[{
        "sid": "allow-browser",
        "effect": "allow",
        "actions": ["tool:call"],
        "resources": ["browser/*"],
    }]
)
policy_engine.register_policy(policy)
result = policy_engine.evaluate("user1", PolicyAction.CALL_TOOL, "browser/navigate")

# 2. Usage Metering & Quota
metering = MeteringCollector()
await metering.start()
await metering.record(user_id="user1", tool_name="browser/navigate", duration_ms=100)
stats = await metering.get_user_stats("user1", "day")

quota = QuotaManager(metering)
quota.set_user_quota("user1", QuotaConfig(max_calls_per_day=1000))
await quota.check_quota("user1")  # Raises QuotaExceeded if over limit

# 3. Distributed Tracing (OpenTelemetry Compatible)
tracer = Tracer(TracerConfig(service_name="my-service"))
with tracer.start_as_current_span("tool_call", kind=SpanKind.SERVER) as span:
    span.set_attribute("user.id", "user1")
    # ... execute tool
    span.set_status(SpanStatus.OK)

# 4. Multi-Agent Orchestration
graph = TaskGraph(name="research-workflow")
t1 = graph.add_task("search", "search-agent", "web_search")
t2 = graph.add_task("analyze", "analyzer-agent", "analyze", depends_on={t1.task_id})
result = await orchestrator.execute(graph)
```

### v3.0 - Basic Enterprise Features

```python
from aibridge.enterprise import AuthMiddleware, AuditLogger, RateLimiter

# Authentication (API Key + JWT)
auth = AuthMiddleware(secret_key="your-secret")
context = await auth.authenticate({"api_key": "key123"})

# Audit Logging
audit = AuditLogger()
await audit.log("execute_tool", user_id="user1", data={"tool": "browser"})

# Rate Limiting
limiter = RateLimiter(default_limit=100, window_seconds=60)
await limiter.check("user1")  # Raises RateLimitExceeded if over limit
```

---

## 📖 Documentation

| Resource | Link |
|----------|------|
| 📚 Quick Start Guide | [examples/basic_usage.py](examples/basic_usage.py) |
| 🏗️ Gateway Demo | [examples/gateway_demo.py](examples/gateway_demo.py) |
| 🤝 Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 📝 Changelog | [CHANGELOG.md](CHANGELOG.md) |

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# 1. Fork and clone
git clone https://github.com/your-username/AI-Bridge.git
cd AI-Bridge/ai-bridge

# 2. Install dev dependencies
pip install -e ".[dev]"

# 3. Run tests
pytest tests/ -v

# 4. Make changes and submit PR
```

---

## 📄 License

This project is licensed under the [Apache License 2.0](LICENSE).

---

## 🙏 Acknowledgements

- [Playwright](https://playwright.dev/) - Browser automation
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol
- [A2A](https://google.github.io/a2a-spec/) - Agent-to-Agent Protocol
- All our [contributors](https://github.com/Louis830903/AI-Bridge/graphs/contributors) ❤️

---

<div align="center">

**[⬆ Back to Top](#-ai-bridge)**

Made with ❤️ by the AI-Bridge Team

</div>
