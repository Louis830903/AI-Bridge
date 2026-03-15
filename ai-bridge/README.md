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
  <strong>The "USB-C" for AI Automation</strong><br>
  <strong>AI 自动化领域的"万能接口"</strong>
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
  <a href="https://github.com/Louis830903/AI-Bridge/issues">
    <img src="https://img.shields.io/badge/PRs-Welcome-brightgreen?style=flat-square" alt="PRs Welcome">
  </a>
</p>

<p>
  <a href="README_CN.md">🇨🇳 中文版</a> •
  <a href="#-quick-start">🚀 Quick Start</a> •
  <a href="#-features">✨ Features</a> •
  <a href="#-documentation">📖 Docs</a> •
  <a href="#-examples">💡 Examples</a>
</p>

<p><strong>🚀 One Protocol. Any AI. Every App.</strong></p>

<!-- DEMO GIF -->
<!-- 替换为实际的 demo.gif URL -->
<!-- <img src="docs/assets/demo.gif" alt="AI-Bridge Demo" width="800"/> -->

</div>

---

## 📢 What's New | 最新动态

```diff
🎉 v3.0.0 Released - Protocol Gateway Architecture!
+ MCP + A2A Dual Protocol Gateway - Connect any AI tool
+ Browser Connector - Proxy to mature MCP Servers (Browser Use, Chrome DevTools, Playwright)
+ Protocol Bridge - MCP ↔ A2A interoperability
+ Service Discovery - Health check and auto-failover
+ JSON-RPC over STDIO - Full MCP protocol implementation

🗓️ v2.6.0 (Previous)
  MCP Server Support - Connect any MCP-compatible AI
  O-R-A Loop Orchestrator - Intelligent task planning
  Shared LLM Architecture - Efficient AI resource usage
```

---

## 🔥 Why AI-Bridge?

<table>
<tr>
<td width="50%">

### ❌ The Old Way
```
AI → Screenshot → OCR → Coordinates → Click
        ↓
   🐢 Slow (seconds)
   💥 Fragile (breaks on UI changes)
   🎯 Inaccurate (wrong coordinates)
   🌍 OCR fails on non-English
```

</td>
<td width="50%">

### ✅ The AI-Bridge Way
```
AI → MCP Protocol → AI-Bridge → Native API
        ↓
   ⚡ Fast (milliseconds)
   🔒 Stable (semantic selectors)
   🎯 Precise (A11y tree + UID)
   🌍 Works globally (i18n native)
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
| 🤖 | **Universal AI Support** | Claude, GPT, Qwen, Gemini, OpenClaw, any MCP-compatible AI |
| 🌐 | **Browser Connector** | Proxy to Browser Use, Chrome DevTools MCP, Playwright MCP |
| 💬 | **13 IM Platforms** | WhatsApp, Telegram, Slack, Teams, Discord, Feishu, DingTalk, WeCom, LINE, Viber, Messenger, KakaoTalk, Google Chat |
| 📊 | **Office Suite** | Word, Excel, PowerPoint, WPS Office |
| 🖥️ | **Desktop Apps** | Any Windows app via UI Automation |
| 🎯 | **Semantic Matching** | 15+ platforms, intent-based actions |
| 🔄 | **O-R-A Loop** | Observe-Reason-Action intelligent planning |
| 🧠 | **Multi-Agent** | A2A protocol for agent collaboration |

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

### 3-Minute Example

**v3.0 - Protocol Gateway (Recommended)**

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

**v2.x - Direct Adapter (Still Supported)**

```python
import asyncio
from aibridge.adapters.browser.chrome import ChromeAdapter
from aibridge.core.protocol import Target

async def main():
    # 1. Create adapter
    adapter = ChromeAdapter({"headless": True})
    
    # 2. Connect to browser
    await adapter.connect()
    
    # 3. Navigate to website
    await adapter.execute(action="goto", value="https://www.baidu.com")
    
    # 4. Type in search box
    await adapter.execute(
        action="type",
        target=Target(css="#kw"),
        value="AI-Bridge automation"
    )
    
    # 5. Click search button
    await adapter.execute(
        action="click",
        target=Target(css="#su")
    )
    
    # 6. Take screenshot
    await adapter.execute(
        action="screenshot",
        options={"path": "result.png"}
    )
    
    # 7. Disconnect
    await adapter.disconnect()

# Run it
asyncio.run(main())
```

**That's it!** You've automated a browser in 7 lines of code 🎉

---

## 💡 Examples

### 🤖 AI Assistant Integration

```python
from aibridge.core.manager import AdapterManager
from aibridge.adapters.browser.chrome import ChromeAdapter

# Setup
manager = AdapterManager()
manager.register(ChromeAdapter({"headless": True}))

# Your AI calls this
async def ai_control(action_description: str):
    """Let AI control the browser"""
    # Parse natural language to action
    if "search" in action_description:
        return await manager.execute(
            app="chrome",
            action="goto", 
            value="https://google.com"
        )
```

### 💬 Send Feishu Message

```python
from aibridge.adapters.im.feishu import FeishuAdapter

adapter = FeishuAdapter({
    "app_id": "your_app_id",
    "app_secret": "your_app_secret"
})

await adapter.connect()
await adapter.execute(
    action="send_message",
    target=Target(name="chat_id"),
    value="Hello from AI-Bridge! 🤖"
)
```

### 📊 Excel Automation

```python
from aibridge.adapters.office.excel import ExcelAdapter

adapter = ExcelAdapter()
await adapter.connect()

# Create new workbook
await adapter.execute(action="create")

# Write data
await adapter.execute(
    action="write",
    target=Target(name="A1"),
    value="Hello World"
)

# Save
await adapter.execute(action="save", value="report.xlsx")
```

---

## 📖 Documentation

| Resource | Link |
|----------|------|
| 📚 Full Documentation | [docs.ai-bridge.dev](https://docs.ai-bridge.dev) |
| 🚀 Quick Start Guide | [docs.ai-bridge.dev/quickstart](https://docs.ai-bridge.dev/quickstart) |
| 📖 API Reference | [docs.ai-bridge.dev/api](https://docs.ai-bridge.dev/api) |
| 💡 Examples Gallery | [docs.ai-bridge.dev/examples](https://docs.ai-bridge.dev/examples) |
| 🏗️ Architecture | [docs.ai-bridge.dev/architecture](https://docs.ai-bridge.dev/architecture) |
| 🤝 Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 📝 Changelog | [CHANGELOG.md](CHANGELOG.md) |

---

## 🌍 Supported Platforms

<details>
<summary>Click to expand full platform list (20+ platforms)</summary>

### 💬 Instant Messaging (13 platforms)
- **Enterprise**: Slack, Microsoft Teams, Discord, Google Chat
- **Consumer**: WhatsApp, Telegram, Messenger, LINE, Viber, KakaoTalk
- **China**: 飞书(Feishu), 钉钉(DingTalk), 企业微信(WeCom)

### 🌐 Browser (2 platforms)
- Google Chrome
- Microsoft Edge

### 📄 Office (4 platforms)
- Microsoft Word
- Microsoft Excel  
- Microsoft PowerPoint
- WPS Office

### 🖥️ Desktop
- Any Windows application via UI Automation

</details>

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AI Assistant                             │
│         (Claude, GPT, Qwen, Gemini, etc.)                   │
└────────────────────┬────────────────────────────────────────┘
                     │ MCP Protocol
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                     AI-Bridge Server                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Intent Engine│  │ O-R-A Loop   │  │ Session Mgr  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┼───────────┬───────────┐
         ▼           ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
    │ Browser │ │   IM    │ │  Office │ │ Desktop │
    │Adapters │ │Adapters │ │Adapters │ │Adapters │
    └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contributing Guide

```bash
# 1. Fork and clone
git clone https://github.com/your-username/AI-Bridge.git
cd AI-Bridge

# 2. Install dev dependencies
pip install -e ".[dev]"

# 3. Run tests
pytest tests/ -v

# 4. Make changes and submit PR
```

---

## 📊 Project Stats

<div align="center">

![GitHub stars](https://img.shields.io/github/stars/Louis830903/AI-Bridge?style=social)
![GitHub forks](https://img.shields.io/github/forks/Louis830903/AI-Bridge?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/Louis830903/AI-Bridge?style=social)

</div>

---

## 📄 License

This project is licensed under the [Apache License 2.0](LICENSE).

---

## 🙏 Acknowledgements

- [Playwright](https://playwright.dev/) - Browser automation
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- All our [contributors](https://github.com/Louis830903/AI-Bridge/graphs/contributors) ❤️

---

<div align="center">

**[⬆ Back to Top](#-ai-bridge)**

Made with ❤️ by the AI-Bridge Team

</div>
