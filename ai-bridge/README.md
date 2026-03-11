# AI-Bridge

<p align="center">
  <img src="docs/assets/logo.png" alt="AI-Bridge Logo" width="200">
</p>

<p align="center">
  <strong>The "USB-C" for AI Automation — Bridge AI Assistants to GUI Applications</strong>
</p>

<p align="center">
  <a href="https://github.com/Louis830903/AI-Bridge/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python"></a>
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-compatible-green.svg" alt="MCP"></a>
</p>

<p align="center">
  <a href="README_CN.md">中文文档</a> | 
  <a href="docs/DEVELOPMENT_PLAN.md">Development Plan</a> |
  <a href="docs/AAIP_SPEC.md">AAIP Specification</a>
</p>

---

## What is AI-Bridge?

**AI-Bridge** is an open-source infrastructure layer that enables AI assistants to interact with GUI applications through a standardized protocol. Think of it as the **"USB-C" for AI automation** — one universal interface to connect any AI to any application.

### The Problem

Current AI automation approaches are fragmented and unreliable:

```
AI Assistant → Screenshot → OCR → Coordinate Calculation → Mouse Click
                    ↓
            Slow, Unstable, Error-prone
```

### Our Solution

AI-Bridge provides a semantic, standardized interface:

```
AI Assistant → MCP Protocol → AI-Bridge → Native App API
                    ↓
            Fast, Reliable, Predictable
```

## Key Features

- **MCP Compatible** — Works with Claude, GPT, Qwen, and any MCP-compatible AI
- **Global + China** — 13 IM platforms: WhatsApp, Messenger, Telegram, Slack, Teams, Discord, LINE, Viber, KakaoTalk, Feishu, DingTalk, WeCom, Google Chat
- **Glue Code Architecture** — Lightweight wrappers around mature libraries
- **Protocol-Driven** — AAIP (AI Application Interaction Protocol) standard
- **Extensible** — Easy to add new adapters

## Supported Applications

| Category | Applications | Status |
|----------|-------------|--------|
| **Browser** | Chrome, Edge | ✅ Ready |
| **Global IM (Enterprise)** | Slack, Microsoft Teams, Discord, Google Chat | ✅ Ready |
| **Global IM (Consumer)** | WhatsApp, Messenger, Telegram, LINE, Viber, KakaoTalk | ✅ Ready |
| **China IM** | Feishu (飞书), DingTalk (钉钉), WeCom (企业微信) | ✅ Ready |
| **Office** | Word, Excel, PowerPoint, WPS | ✅ Ready |
| **Desktop** | Any Windows App (via UIA) | ✅ Ready |

## Quick Start

### Installation

```bash
pip install ai-bridge

# With all adapters
pip install ai-bridge[all]

# Specific adapters
pip install ai-bridge[browser,im,office]
```

### Basic Usage

```python
from aibridge import AIBridge

# Initialize
bridge = AIBridge()

# Chrome automation
await bridge.execute("chrome", "goto", "https://example.com")
await bridge.execute("chrome", "click", {"name": "Submit"})

# Send Feishu message
await bridge.execute("feishu", "send", {
    "chat_id": "oc_xxx",
    "text": "Hello from AI-Bridge!"
})

# Excel automation
await bridge.execute("excel", "write", {
    "file": "report.xlsx",
    "cell": "A1",
    "value": "Sales Report"
})
```

### Claude Desktop Integration

Add to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "aibridge": {
      "command": "python",
      "args": ["-m", "aibridge"],
      "env": {
        "FEISHU_APP_ID": "your_app_id",
        "FEISHU_APP_SECRET": "your_secret"
      }
    }
  }
}
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│              AI Assistants                       │
│    Claude | GPT | Qwen | OpenClaw | Custom      │
└─────────────────────────────────────────────────┘
                        │ MCP Protocol
                        ▼
┌─────────────────────────────────────────────────┐
│              AI-Bridge Core                      │
│   ┌─────────────────────────────────────────┐  │
│   │           MCP Server                     │  │
│   │    Protocol Parser / Router / Response   │  │
│   └─────────────────────────────────────────┘  │
│   ┌─────────────────────────────────────────┐  │
│   │         Adapter Manager                  │  │
│   │   Registration / Lifecycle / Dispatch    │  │
│   └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Browser   │ │     IM      │ │   Office    │
│   Adapter   │ │   Adapter   │ │   Adapter   │
│ [Playwright]│ │ [HTTP API]  │ │  [win32com] │
└─────────────┘ └─────────────┘ └─────────────┘
```

## AAIP Protocol

AI-Bridge defines the **AI Application Interaction Protocol (AAIP)** — a standard for AI-to-GUI communication:

```yaml
# Request Format
Request:
  app: string       # Target application ID
  action: string    # Operation type
  target: object    # Element locator
  value: any        # Operation value
  options: object   # Additional options

# Response Format
Response:
  success: bool
  data: any
  error: string
  screenshot: string  # Base64 (optional)
```

### Standard Actions

| Action | Description |
|--------|-------------|
| `click` | Click element |
| `type` | Input text |
| `read` | Read element text |
| `screenshot` | Take screenshot |
| `list_elements` | List interactive elements |
| `wait` | Wait for element |
| `launch` | Start application |
| `close` | Close application |

## Adapters

### Browser Adapter (Chrome/Edge)

```python
# Navigate
await bridge.execute("chrome", "goto", "https://google.com")

# Click button
await bridge.execute("chrome", "click", {"name": "Search"})

# Fill input
await bridge.execute("chrome", "type", {
    "target": {"css": "input[name='q']"},
    "value": "AI-Bridge"
})

# Get page content
result = await bridge.execute("chrome", "read", {"css": "h1"})
```

### Feishu Adapter

```python
# List chats
chats = await bridge.execute("feishu", "list_chats")

# Send message
await bridge.execute("feishu", "send", {
    "chat_id": "oc_xxx",
    "text": "Meeting reminder: 3pm today"
})

# Send card message
await bridge.execute("feishu", "send_card", {
    "chat_id": "oc_xxx",
    "title": "Task Update",
    "content": "Project completed!"
})
```

### Slack Adapter

```python
# Send message
await bridge.execute("slack", "send_message", {
    "channel": "#general",
    "text": "Hello from AI-Bridge!"
})

# List channels
channels = await bridge.execute("slack", "list_channels")
```

### Telegram Adapter

```python
# Send message
await bridge.execute("telegram", "send_message", {
    "chat_id": "123456",
    "text": "Hello from AI-Bridge!"
})

# Send photo
await bridge.execute("telegram", "send_photo", {
    "chat_id": "123456",
    "photo": "screenshot.png",
    "caption": "Today's report"
})
```

### Discord Adapter

```python
# Send message
await bridge.execute("discord", "send_message", {
    "channel": "channel_id",
    "text": "Hello from AI-Bridge!"
})

# Send embed
await bridge.execute("discord", "send_embed", {
    "channel": "channel_id",
    "embed": {"title": "Report", "description": "Daily summary"}
})
```

### Office Adapter

```python
# Create Word document
await bridge.execute("word", "create", {
    "path": "report.docx",
    "content": "Annual Report 2024"
})

# Read Excel cell
value = await bridge.execute("excel", "read", {
    "file": "data.xlsx",
    "sheet": "Sheet1",
    "cell": "A1"
})

# Write Excel cell
await bridge.execute("excel", "write", {
    "file": "data.xlsx",
    "cell": "B1",
    "value": 100
})
```

## Configuration

Create `aibridge.yaml`:

```yaml
server:
  transport: stdio
  log_level: INFO

adapters:
  chrome:
    enabled: true
    cdp_url: "http://localhost:9222"
  
  # Global IM
  slack:
    enabled: true
    bot_token: ${SLACK_BOT_TOKEN}
    
  teams:
    enabled: true
    tenant_id: ${TEAMS_TENANT_ID}
    client_id: ${TEAMS_CLIENT_ID}
    client_secret: ${TEAMS_CLIENT_SECRET}
    
  discord:
    enabled: true
    bot_token: ${DISCORD_BOT_TOKEN}
    
  telegram:
    enabled: true
    bot_token: ${TELEGRAM_BOT_TOKEN}
  
  # China IM  
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
    
  office:
    enabled: true
    visible: true
```

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Adding a New Adapter

```python
from aibridge.adapters.base import BaseAdapter, AdapterInfo

class MyAdapter(BaseAdapter):
    info = AdapterInfo(
        id="myapp",
        name="My Application",
        type="custom",
        actions=["click", "type", "read"]
    )
    
    async def connect(self):
        # Initialize connection
        pass
    
    async def execute(self, action, target=None, value=None, options=None):
        # Handle actions
        pass
```

## Roadmap

- [x] Core protocol & MCP Server
- [x] Browser adapters (Chrome, Edge)
- [x] Global IM adapters (Slack, Teams, Discord, Telegram)
- [x] China IM adapters (Feishu, DingTalk, WeCom)
- [x] Office adapters (MS Office, WPS)
- [x] Generic desktop adapter (UIA)
- [ ] Adapter marketplace
- [ ] Visual workflow builder
- [ ] Enterprise features

## License

Apache 2.0 — See [LICENSE](LICENSE)

## Links

- [GitHub](https://github.com/Louis830903/AI-Bridge)
- [Documentation](https://ai-bridge.dev)
- [AAIP Specification](docs/AAIP_SPEC.md)
- [Development Plan](docs/DEVELOPMENT_PLAN.md)

---

<p align="center">
  Made with ❤️ for the AI automation community
</p>
