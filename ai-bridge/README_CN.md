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

### **AI 自动化领域的"万能接口"**
### **The "USB-C" for AI Automation**

<br/>

[![License](https://img.shields.io/badge/许可证-Apache%202.0-blue.svg?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-兼容-00D084?style=for-the-badge&logo=anthropic&logoColor=white)](https://modelcontextprotocol.io)
[![PRs Welcome](https://img.shields.io/badge/PRs-欢迎-brightgreen?style=for-the-badge)](CONTRIBUTING.md)

<br/>

**🚀 一个协议，连接所有 AI，操控所有应用**

**🚀 One Protocol. Any AI. Every App.**

<br/>

[📖 English](README.md) • [🎯 功能特性](#-核心能力) • [🌍 支持平台](#-支持平台) • [🚀 快速开始](#-快速开始)

---

<br/>

<img src="https://raw.githubusercontent.com/Louis830903/AI-Bridge/main/docs/assets/demo.gif" alt="AI-Bridge Demo" width="800"/>

</div>

<br/>

## 🔥 为什么选择 AI-Bridge？

<table>
<tr>
<td width="50%">

### ❌ 传统方案

```
AI → 截图 → OCR识别 → 坐标计算 → 鼠标点击
        ↓
   🐢 慢（秒级延迟）
   💥 不稳定（经常崩）
   🎯 不准确（点错位置）
   🌍 不支持多语言
```

</td>
<td width="50%">

### ✅ AI-Bridge 方案

```
AI → MCP协议 → AI-Bridge → 原生API
        ↓
   ⚡ 快（毫秒级响应）
   🔒 稳定（原生调用）
   🎯 精准（语义定位）
   🌍 全球+中国全覆盖
```

</td>
</tr>
</table>

<br/>

## ⚡ 核心能力

<div align="center">

| 🤖 **全AI兼容** | 🌏 **13个即时通讯平台** | 📊 **办公套件** | 🖥️ **任意桌面应用** |
|:---:|:---:|:---:|:---:|
| Claude、GPT、千问、Gemini、OpenClaw 等所有 MCP 兼容的 AI | WhatsApp、Telegram、Slack、Teams、Discord、飞书、钉钉、企微、LINE、Viber、Messenger、KakaoTalk、Google Chat | Word、Excel、PowerPoint、WPS Office | Windows UIA、Chrome、Edge |

</div>

<br/>

## 🌍 支持平台

<div align="center">

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          🌐 全球 + 中国 全覆盖                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   💬 即时通讯（13个平台）                                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  🌍 全球企业级        │  🌍 全球消费级        │  🇨🇳 中国本土      │   │
│   │  ├─ Slack            │  ├─ WhatsApp          │  ├─ 飞书 Feishu   │   │
│   │  ├─ Microsoft Teams  │  ├─ Telegram          │  ├─ 钉钉 DingTalk │   │
│   │  ├─ Discord          │  ├─ Messenger         │  └─ 企微 WeCom    │   │
│   │  └─ Google Chat      │  ├─ LINE              │                   │   │
│   │                      │  ├─ Viber             │                   │   │
│   │                      │  └─ KakaoTalk         │                   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   🌐 浏览器                📄 办公软件              🖥️ 桌面应用              │
│   ├─ Chrome              ├─ Microsoft Word       ├─ 任意 Windows 应用     │
│   └─ Edge                ├─ Microsoft Excel      └─ 通过 UI Automation    │
│                          ├─ Microsoft PowerPoint                          │
│                          └─ WPS Office（国产）                             │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

</div>

<br/>

## 🏗️ 系统架构

```
                              ╔═══════════════════════════════════════════╗
                              ║           🤖 AI 助手                       ║
                              ║  Claude │ GPT │ 千问 │ Gemini │ OpenClaw  ║
                              ╚═══════════════════════════════════════════╝
                                                  │
                                                  │ MCP 协议
                                                  ▼
╔════════════════════════════════════════════════════════════════════════════════╗
║                              🌉 AI-BRIDGE 核心                                  ║
║  ┌────────────────────────────────────────────────────────────────────────┐   ║
║  │                         📡 MCP 服务器                                   │   ║
║  │               JSON-RPC 处理器 │ 路由器 │ 响应构建器                      │   ║
║  └────────────────────────────────────────────────────────────────────────┘   ║
║  ┌────────────────────────────────────────────────────────────────────────┐   ║
║  │                      🔌 适配器管理器                                     │   ║
║  │              注册 │ 生命周期管理 │ 调度 │ 健康检查                        │   ║
║  └────────────────────────────────────────────────────────────────────────┘   ║
║  ┌────────────────────────────────────────────────────────────────────────┐   ║
║  │                      📋 AAIP 协议引擎                                    │   ║
║  │              语义化操作 │ 元素定位器 │ 响应处理                           │   ║
║  └────────────────────────────────────────────────────────────────────────┘   ║
╚════════════════════════════════════════════════════════════════════════════════╝
                                          │
            ┌─────────────────────────────┼─────────────────────────────┐
            ▼                             ▼                             ▼
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│   🌐 浏览器适配器    │      │   💬 IM 适配器       │      │   📊 办公适配器      │
│   ─────────────     │      │   ─────────────     │      │   ─────────────     │
│   Chrome │ Edge     │      │   13 个平台          │      │   Word │ Excel     │
│   [Playwright]      │      │   [REST APIs]       │      │   PPT │ WPS        │
│                     │      │                     │      │   [win32com]       │
└─────────────────────┘      └─────────────────────┘      └─────────────────────┘
```

<br/>

## 🚀 快速开始

### 安装

```bash
# 基础安装
pip install ai-bridge

# 完整安装（所有适配器）
pip install ai-bridge[all]

# 按需安装
pip install ai-bridge[browser]      # Chrome、Edge
pip install ai-bridge[im]           # 所有13个IM平台
pip install ai-bridge[office]       # Word、Excel、PPT、WPS
pip install ai-bridge[china]        # 飞书、钉钉、企微
```

### 30秒上手

```python
from aibridge import AIBridge

bridge = AIBridge()

# 🌐 浏览器自动化
await bridge.execute("chrome", "goto", "https://github.com")
await bridge.execute("chrome", "click", {"name": "登录"})

# 💬 发送 Slack 消息
await bridge.execute("slack", "send_message", {
    "channel": "#general",
    "text": "🚀 AI-Bridge 部署成功！"
})

# 💬 发送飞书消息
await bridge.execute("feishu", "send", {
    "chat_id": "oc_xxx",
    "text": "🚀 项目已上线！"
})

# 📊 Excel 自动化
await bridge.execute("excel", "write", {
    "file": "报表.xlsx",
    "cell": "A1",
    "value": "AI 生成的报告"
})
```

### Claude Desktop 集成

在 `claude_desktop_config.json` 中添加：

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

## 📡 AAIP 协议规范

**AI Application Interaction Protocol** — AI 与 GUI 通信的标准协议。

```yaml
# 请求格式
Request:
  app: "chrome" | "slack" | "feishu" | "excel" | ...
  action: "click" | "type" | "read" | "send" | ...
  target:
    name: "提交按钮"           # 按文本定位
    css: "#submit-btn"        # 按 CSS 选择器
    xpath: "//button[@id='x']" # 按 XPath
    automation_id: "btn_001"   # 按 UIA ID
  value: any
  options:
    timeout: 5000
    wait_after: 1000

# 响应格式
Response:
  success: true
  data: { ... }
  screenshot: "base64..."  # 可选
```

### 标准操作

| 操作 | 说明 | Description |
|------|------|-------------|
| `click` | 点击元素 | Click element |
| `type` | 输入文本 | Input text |
| `read` | 读取文本 | Read text |
| `screenshot` | 截图 | Capture screen |
| `list_elements` | 列出可交互元素 | List elements |
| `send` | 发送消息（IM） | Send message |
| `launch` | 启动应用 | Start app |
| `close` | 关闭应用 | Close app |

<br/>

## 💬 即时通讯示例

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

# 获取群列表
chats = await bridge.execute("feishu", "list_chats")
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
    "content": "请审批您的报销单"
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

<details>
<summary><b>🔵 Slack</b></summary>

```python
# 发送消息
await bridge.execute("slack", "send_message", {
    "channel": "#engineering",
    "text": "Build succeeded! ✅"
})

# 发送富文本
await bridge.execute("slack", "send_blocks", {
    "channel": "#alerts",
    "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "*Alert*: CPU > 90%"}}]
})
```
</details>

<details>
<summary><b>🔵 Telegram</b></summary>

```python
# 发送消息
await bridge.execute("telegram", "send_message", {
    "chat_id": "123456",
    "text": "来自 AI-Bridge 的问候！🤖"
})

# 发送图片
await bridge.execute("telegram", "send_photo", {
    "chat_id": "123456",
    "photo": "report.png",
    "caption": "今日报告 📊"
})
```
</details>

<details>
<summary><b>🟣 Microsoft Teams</b></summary>

```python
# 发送到频道
await bridge.execute("teams", "send_message", {
    "channel_id": "xxx",
    "text": "会议提醒：今天下午3点"
})
```
</details>

<details>
<summary><b>🟣 Discord</b></summary>

```python
# 发送嵌入消息
await bridge.execute("discord", "send_embed", {
    "channel": "channel_id",
    "embed": {
        "title": "🎉 新版本发布",
        "description": "v2.0.0 现已上线！",
        "color": 0x00ff00
    }
})
```
</details>

<br/>

## 📊 办公自动化

```python
# 📝 Word 文档
await bridge.execute("word", "create", {
    "path": "报告.docx",
    "content": "# 2024年度报告\n\n摘要内容..."
})

# 📊 Excel 表格
await bridge.execute("excel", "write", {
    "file": "数据.xlsx",
    "sheet": "销售",
    "range": "A1:D10",
    "data": [["产品", "Q1", "Q2", "Q3"], ...]
})

# 📽️ PowerPoint 演示
await bridge.execute("powerpoint", "create", {
    "path": "演示.pptx",
    "slides": [
        {"title": "Q1 业绩", "content": "营收增长 25%"}
    ]
})

# 📄 WPS Office
await bridge.execute("wps", "write", {
    "file": "报表.xlsx",
    "cell": "A1",
    "value": "销售数据"
})
```

<br/>

## ⚙️ 配置文件

创建 `aibridge.yaml`：

```yaml
server:
  transport: stdio
  log_level: INFO

adapters:
  # 🌐 浏览器
  chrome:
    enabled: true
    cdp_url: "http://localhost:9222"
  
  # 🌍 全球 IM
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
  
  # 🇨🇳 国内 IM
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
  
  # 📊 办公软件
  office:
    enabled: true
    visible: true
```

<br/>

## 🔌 扩展开发

几分钟内创建自定义适配器：

```python
from aibridge.adapters.base import BaseAdapter, AdapterInfo

class MyAppAdapter(BaseAdapter):
    info = AdapterInfo(
        id="myapp",
        name="我的应用",
        type="custom",
        actions=["click", "type", "read", "custom_action"]
    )
    
    async def connect(self):
        """初始化应用连接"""
        self.client = MyAppClient()
    
    async def execute(self, action, target=None, value=None, options=None):
        """处理操作"""
        if action == "custom_action":
            return await self.client.do_something(value)
        # ... 处理其他操作
```

<br/>

## 📍 路线图

- [x] 🏗️ 核心协议 & MCP 服务器
- [x] 🌐 浏览器适配器（Chrome、Edge）
- [x] 💬 全球 IM（Slack、Teams、Discord、Telegram、WhatsApp...）
- [x] 🇨🇳 国内 IM（飞书、钉钉、企微）
- [x] 📊 办公套件（MS Office、WPS）
- [x] 🖥️ 桌面自动化（Windows UIA）
- [ ] 🏪 适配器市场
- [ ] 🎨 可视化流程编排
- [ ] 🏢 企业版功能
- [ ] 📱 移动端支持

<br/>

## 🤝 参与贡献

欢迎贡献代码！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)。

```bash
# 克隆仓库
git clone https://github.com/Louis830903/AI-Bridge.git
cd AI-Bridge/ai-bridge

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 提交 PR
```

<br/>

## 📜 许可证

Apache 2.0 — 详见 [LICENSE](LICENSE)

<br/>

## 🔗 链接

<div align="center">

[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github)](https://github.com/Louis830903/AI-Bridge)
[![文档](https://img.shields.io/badge/文档-blue?style=for-the-badge&logo=readthedocs&logoColor=white)](https://ai-bridge.dev)
[![Discord](https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/aibridge)

</div>

<br/>

---

<div align="center">

### 🌟 给我们点个 Star 吧！

### 🌟 Star us on GitHub — it helps!

<br/>

**为 AI 自动化社区倾心打造 ❤️**

**Built with ❤️ for the AI Automation Community**

<br/>

```
 █████╗ ██╗      ██████╗ ██████╗ ██╗██████╗  ██████╗ ███████╗
██╔══██╗██║      ██╔══██╗██╔══██╗██║██╔══██╗██╔════╝ ██╔════╝
███████║██║█████╗██████╔╝██████╔╝██║██║  ██║██║  ███╗█████╗  
██╔══██║██║╚════╝██╔══██╗██╔══██╗██║██║  ██║██║   ██║██╔══╝  
██║  ██║██║      ██████╔╝██║  ██║██║██████╔╝╚██████╔╝███████╗
╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝╚═════╝  ╚═════╝ ╚══════╝
                                                              
              一个协议，连接所有 AI，操控所有应用
```

</div>
