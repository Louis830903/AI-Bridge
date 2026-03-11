<div align="center">

```
     _    ___      ____       _     _            
    / \  |_ _|    | __ ) _ __(_) __| | __ _  ___ 
   / _ \  | |_____|  _ \| '__| |/ _` |/ _` |/ _ \
  / ___ \ | |_____| |_) | |  | | (_| | (_| |  __/
 /_/   \_\___|    |____/|_|  |_|\__,_|\__, |\___|
                                      |___/      
```

# 🌉 AI-Bridge

### **The "USB-C" for AI Automation**
### **AI 自动化领域的"万能接口"**

<br/>

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-Compatible-00D084?style=for-the-badge&logo=anthropic&logoColor=white)](https://modelcontextprotocol.io)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen?style=for-the-badge)](CONTRIBUTING.md)

<br/>

**🚀 One Protocol. Any AI. Every App.**

**🚀 一个协议，连接所有 AI，操控所有应用**

<br/>

[📖 Documentation](#quick-start) • [🎯 Features](#-superpowers) • [🌍 Supported Apps](#-supported-platforms) • [🚀 Quick Start](#-quick-start)

[📖 文档](#quick-start) • [🎯 功能特性](#-superpowers) • [🌍 支持平台](#-supported-platforms) • [🚀 快速开始](#-quick-start)

---

<br/>

<img src="https://raw.githubusercontent.com/Louis830903/AI-Bridge/main/docs/assets/demo.gif" alt="AI-Bridge Demo" width="800"/>

</div>

<br/>

## 🔥 Why AI-Bridge? | 为什么选择 AI-Bridge？

<table>
<tr>
<td width="50%">

### ❌ The Old Way | 传统方式

```
AI → Screenshot → OCR → Coordinates → Click
        ↓
   🐢 Slow (seconds)
   💥 Unstable (breaks often)
   🎯 Inaccurate (wrong clicks)
   🌍 No i18n (OCR fails)
```

</td>
<td width="50%">

### ✅ The AI-Bridge Way | AI-Bridge 方式

```
AI → MCP Protocol → AI-Bridge → Native API
        ↓
   ⚡ Fast (milliseconds)
   🔒 Stable (native calls)
   🎯 Precise (semantic)
   🌍 Global + China ready
```

</td>
</tr>
</table>

<br/>

## ⚡ Superpowers

<div align="center">

| 🤖 **Universal AI** | 🌏 **13 IM Platforms** | 📊 **Office Suite** | 🖥️ **Any Desktop App** |
|:---:|:---:|:---:|:---:|
| Claude, GPT, Qwen, Gemini, OpenClaw, and any MCP-compatible AI | WhatsApp, Telegram, Slack, Teams, Discord, Feishu, DingTalk, WeCom, LINE, Viber, Messenger, KakaoTalk, Google Chat | Word, Excel, PowerPoint, WPS Office | Windows UIA, Chrome, Edge |

</div>

<br/>

## 🌍 Supported Platforms

<div align="center">

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           🌐 GLOBAL + CHINA COVERAGE                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   💬 INSTANT MESSAGING (13 Platforms)                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  🌍 Global Enterprise    │  🌍 Global Consumer   │  🇨🇳 China        │   │
│   │  ├─ Slack               │  ├─ WhatsApp          │  ├─ 飞书 Feishu   │   │
│   │  ├─ Microsoft Teams     │  ├─ Telegram          │  ├─ 钉钉 DingTalk │   │
│   │  ├─ Discord             │  ├─ Messenger         │  └─ 企微 WeCom    │   │
│   │  └─ Google Chat         │  ├─ LINE              │                   │   │
│   │                         │  ├─ Viber             │                   │   │
│   │                         │  └─ KakaoTalk         │                   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   🌐 BROWSER                  📄 OFFICE                 🖥️ DESKTOP          │
│   ├─ Chrome                  ├─ Microsoft Word         ├─ Any Windows App   │
│   └─ Edge                    ├─ Microsoft Excel        └─ via UI Automation │
│                              ├─ Microsoft PowerPoint                        │
│                              └─ WPS Office (CN)                             │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

</div>

<br/>

## 🏗️ Architecture | 架构

```
                              ╔═══════════════════════════════════════════╗
                              ║           🤖 AI ASSISTANTS                ║
                              ║  Claude │ GPT │ Qwen │ Gemini │ OpenClaw  ║
                              ╚═══════════════════════════════════════════╝
                                                  │
                                                  │ MCP Protocol
                                                  ▼
╔════════════════════════════════════════════════════════════════════════════════╗
║                              🌉 AI-BRIDGE CORE                                  ║
║  ┌────────────────────────────────────────────────────────────────────────┐   ║
║  │                         📡 MCP Server                                   │   ║
║  │              JSON-RPC Handler │ Router │ Response Builder               │   ║
║  └────────────────────────────────────────────────────────────────────────┘   ║
║  ┌────────────────────────────────────────────────────────────────────────┐   ║
║  │                      🔌 Adapter Manager                                 │   ║
║  │             Registration │ Lifecycle │ Dispatch │ Health Check          │   ║
║  └────────────────────────────────────────────────────────────────────────┘   ║
║  ┌────────────────────────────────────────────────────────────────────────┐   ║
║  │                      📋 AAIP Protocol Engine                            │   ║
║  │              Semantic Actions │ Element Locators │ Responses            │   ║
║  └────────────────────────────────────────────────────────────────────────┘   ║
╚════════════════════════════════════════════════════════════════════════════════╝
                                          │
            ┌─────────────────────────────┼─────────────────────────────┐
            ▼                             ▼                             ▼
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│   🌐 Browser        │      │   💬 IM             │      │   📊 Office         │
│   ─────────────     │      │   ─────────────     │      │   ─────────────     │
│   Chrome │ Edge     │      │   13 Platforms      │      │   Word │ Excel      │
│   [Playwright]      │      │   [REST APIs]       │      │   PPT │ WPS         │
│                     │      │                     │      │   [win32com]        │
└─────────────────────┘      └─────────────────────┘      └─────────────────────┘
            │                             │                             │
            ▼                             ▼                             ▼
    ┌───────────┐                ┌───────────────┐              ┌───────────┐
    │  Webpages │                │  Chat/Channel │              │ Documents │
    └───────────┘                └───────────────┘              └───────────┘
```

<br/>

## 🚀 Quick Start

### Installation | 安装

```bash
# Basic installation | 基础安装
pip install ai-bridge

# Full installation (all adapters) | 完整安装
pip install ai-bridge[all]

# Selective installation | 按需安装
pip install ai-bridge[browser]      # Chrome, Edge
pip install ai-bridge[im]           # All 13 IM platforms
pip install ai-bridge[office]       # Word, Excel, PPT, WPS
pip install ai-bridge[china]        # Feishu, DingTalk, WeCom
```

### 30-Second Demo | 30秒上手

```python
from aibridge import AIBridge

bridge = AIBridge()

# 🌐 Browser Automation | 浏览器自动化
await bridge.execute("chrome", "goto", "https://github.com")
await bridge.execute("chrome", "click", {"name": "Sign in"})

# 💬 Send to Slack
await bridge.execute("slack", "send_message", {
    "channel": "#general",
    "text": "🚀 Deployed by AI-Bridge!"
})

# 💬 发送飞书消息
await bridge.execute("feishu", "send", {
    "chat_id": "oc_xxx",
    "text": "🚀 AI-Bridge 部署成功！"
})

# 📊 Excel Automation | Excel 自动化
await bridge.execute("excel", "write", {
    "file": "report.xlsx",
    "cell": "A1",
    "value": "AI-Generated Report"
})
```

### Claude Desktop Integration | Claude Desktop 集成

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "aibridge": {
      "command": "python",
      "args": ["-m", "aibridge"],
      "env": {
        "SLACK_BOT_TOKEN": "xoxb-xxx",
        "FEISHU_APP_ID": "cli_xxx",
        "FEISHU_APP_SECRET": "xxx"
      }
    }
  }
}
```

<br/>

## 📡 AAIP Protocol | 协议规范

**AI Application Interaction Protocol** — The standard for AI-to-GUI communication.

```yaml
# Request Format | 请求格式
Request:
  app: "chrome" | "slack" | "feishu" | "excel" | ...
  action: "click" | "type" | "read" | "send" | ...
  target:
    name: "Submit Button"      # By text | 按文本
    css: "#submit-btn"         # By CSS | 按CSS
    xpath: "//button[@id='x']" # By XPath
    automation_id: "btn_001"   # By UIA ID
  value: any
  options:
    timeout: 5000
    wait_after: 1000

# Response Format | 响应格式
Response:
  success: true
  data: { ... }
  screenshot: "base64..."  # Optional
```

### Standard Actions | 标准操作

| Action | Description | 说明 |
|--------|-------------|------|
| `click` | Click element | 点击元素 |
| `type` | Input text | 输入文本 |
| `read` | Read element text | 读取文本 |
| `screenshot` | Capture screen | 截图 |
| `list_elements` | List interactive elements | 列出可交互元素 |
| `send` | Send message (IM) | 发送消息 |
| `launch` | Start application | 启动应用 |
| `close` | Close application | 关闭应用 |

<br/>

## 💬 IM Platform Examples | 即时通讯示例

<details>
<summary><b>🔵 Slack</b></summary>

```python
# Send message | 发送消息
await bridge.execute("slack", "send_message", {
    "channel": "#engineering",
    "text": "Build succeeded! ✅"
})

# Send with blocks | 发送富文本
await bridge.execute("slack", "send_blocks", {
    "channel": "#alerts",
    "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "*Alert*: CPU > 90%"}}]
})
```
</details>

<details>
<summary><b>🟣 Microsoft Teams</b></summary>

```python
# Send to channel | 发送到频道
await bridge.execute("teams", "send_message", {
    "channel_id": "xxx",
    "text": "Meeting reminder: 3pm today"
})

# Send adaptive card | 发送自适应卡片
await bridge.execute("teams", "send_card", {
    "channel_id": "xxx",
    "card": {...}
})
```
</details>

<details>
<summary><b>🔵 Telegram</b></summary>

```python
# Send message | 发送消息
await bridge.execute("telegram", "send_message", {
    "chat_id": "123456",
    "text": "Hello from AI-Bridge! 🤖"
})

# Send photo | 发送图片
await bridge.execute("telegram", "send_photo", {
    "chat_id": "123456",
    "photo": "report.png",
    "caption": "Daily Report 📊"
})
```
</details>

<details>
<summary><b>🟣 Discord</b></summary>

```python
# Send embed | 发送嵌入消息
await bridge.execute("discord", "send_embed", {
    "channel": "channel_id",
    "embed": {
        "title": "🎉 New Release",
        "description": "v2.0.0 is now available!",
        "color": 0x00ff00
    }
})
```
</details>

<details>
<summary><b>🔵 飞书 Feishu</b></summary>

```python
# 发送文本消息
await bridge.execute("feishu", "send", {
    "chat_id": "oc_xxx",
    "text": "任务已完成 ✅"
})

# 发送卡片消息
await bridge.execute("feishu", "send_card", {
    "chat_id": "oc_xxx",
    "title": "📊 日报",
    "content": "今日完成5个任务"
})
```
</details>

<details>
<summary><b>🔵 钉钉 DingTalk</b></summary>

```python
# Webhook 消息
await bridge.execute("dingtalk", "send_webhook", {
    "text": "⚠️ 服务器告警：CPU 使用率 > 90%"
})

# 工作通知
await bridge.execute("dingtalk", "send_work_notice", {
    "userid_list": ["user1", "user2"],
    "content": "请审批报销单"
})
```
</details>

<details>
<summary><b>🟢 企业微信 WeCom</b></summary>

```python
# 应用消息
await bridge.execute("wecom", "send", {
    "touser": "@all",
    "content": "📢 全员通知：明天团建"
})

# 群聊消息
await bridge.execute("wecom", "send_to_chat", {
    "chatid": "CHATID",
    "content": "周会改到周四下午"
})
```
</details>

<br/>

## 📊 Office Automation | 办公自动化

```python
# 📝 Word
await bridge.execute("word", "create", {
    "path": "report.docx",
    "content": "# Annual Report 2024\n\nExecutive Summary..."
})

# 📊 Excel
await bridge.execute("excel", "write", {
    "file": "data.xlsx",
    "sheet": "Sales",
    "range": "A1:D10",
    "data": [["Product", "Q1", "Q2", "Q3"], ...]
})

# 📽️ PowerPoint
await bridge.execute("powerpoint", "create", {
    "path": "deck.pptx",
    "slides": [
        {"title": "Q1 Results", "content": "Revenue up 25%"}
    ]
})

# 📄 WPS Office (China)
await bridge.execute("wps", "write", {
    "file": "报表.xlsx",
    "cell": "A1",
    "value": "销售数据"
})
```

<br/>

## ⚙️ Configuration | 配置

Create `aibridge.yaml`:

```yaml
server:
  transport: stdio
  log_level: INFO

adapters:
  # 🌐 Browser
  chrome:
    enabled: true
    cdp_url: "http://localhost:9222"
  
  # 🌍 Global IM
  slack:
    enabled: true
    bot_token: ${SLACK_BOT_TOKEN}
  
  teams:
    enabled: true
    tenant_id: ${TEAMS_TENANT_ID}
    client_id: ${TEAMS_CLIENT_ID}
  
  discord:
    enabled: true
    bot_token: ${DISCORD_BOT_TOKEN}
  
  telegram:
    enabled: true
    bot_token: ${TELEGRAM_BOT_TOKEN}
  
  # 🇨🇳 China IM
  feishu:
    enabled: true
    app_id: ${FEISHU_APP_ID}
    app_secret: ${FEISHU_APP_SECRET}
  
  dingtalk:
    enabled: true
    app_key: ${DINGTALK_APP_KEY}
    app_secret: ${DINGTALK_APP_SECRET}
  
  wecom:
    enabled: true
    corp_id: ${WECOM_CORP_ID}
    corp_secret: ${WECOM_CORP_SECRET}
  
  # 📊 Office
  office:
    enabled: true
    visible: true
```

<br/>

## 🔌 Extend It | 扩展开发

Create custom adapters in minutes:

```python
from aibridge.adapters.base import BaseAdapter, AdapterInfo

class MyAppAdapter(BaseAdapter):
    info = AdapterInfo(
        id="myapp",
        name="My Application",
        type="custom",
        actions=["click", "type", "read", "custom_action"]
    )
    
    async def connect(self):
        """Initialize your app connection"""
        self.client = MyAppClient()
    
    async def execute(self, action, target=None, value=None, options=None):
        """Handle actions"""
        if action == "custom_action":
            return await self.client.do_something(value)
        # ... handle other actions
```

<br/>

## 📍 Roadmap | 路线图

- [x] 🏗️ Core Protocol & MCP Server
- [x] 🌐 Browser Adapters (Chrome, Edge)
- [x] 💬 Global IM (Slack, Teams, Discord, Telegram, WhatsApp...)
- [x] 🇨🇳 China IM (Feishu, DingTalk, WeCom)
- [x] 📊 Office Suite (MS Office, WPS)
- [x] 🖥️ Desktop Automation (Windows UIA)
- [ ] 🏪 Adapter Marketplace
- [ ] 🎨 Visual Workflow Builder
- [ ] 🏢 Enterprise Features
- [ ] 📱 Mobile App Support

<br/>

## 🤝 Contributing | 参与贡献

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md).

欢迎贡献代码！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)。

```bash
# Clone
git clone https://github.com/Louis830903/AI-Bridge.git
cd AI-Bridge/ai-bridge

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Submit PR
```

<br/>

## 📜 License | 许可证

Apache 2.0 — See [LICENSE](LICENSE)

<br/>

## 🔗 Links | 链接

<div align="center">

[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github)](https://github.com/Louis830903/AI-Bridge)
[![Documentation](https://img.shields.io/badge/Docs-blue?style=for-the-badge&logo=readthedocs&logoColor=white)](https://ai-bridge.dev)
[![Discord](https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/aibridge)

</div>

<br/>

---

<div align="center">

### 🌟 Star us on GitHub — it helps!

### 🌟 给我们点个 Star 吧 — 这对我们很重要！

<br/>

**Built with ❤️ for the AI Automation Community**

**为 AI 自动化社区倾心打造**

<br/>

```
 █████╗ ██╗      ██████╗ ██████╗ ██╗██████╗  ██████╗ ███████╗
██╔══██╗██║      ██╔══██╗██╔══██╗██║██╔══██╗██╔════╝ ██╔════╝
███████║██║█████╗██████╔╝██████╔╝██║██║  ██║██║  ███╗█████╗  
██╔══██║██║╚════╝██╔══██╗██╔══██╗██║██║  ██║██║   ██║██╔══╝  
██║  ██║██║      ██████╔╝██║  ██║██║██████╔╝╚██████╔╝███████╗
╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝╚═════╝  ╚═════╝ ╚══════╝
                                                              
              One Protocol. Any AI. Every App.
```

</div>
