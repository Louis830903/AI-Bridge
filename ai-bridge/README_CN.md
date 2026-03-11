# AI-Bridge

<p align="center">
  <img src="docs/assets/logo.png" alt="AI-Bridge Logo" width="200">
</p>

<p align="center">
  <strong>AI自动化的"USB-C" —— 连接AI助手与GUI应用的标准协议</strong>
</p>

<p align="center">
  <a href="https://github.com/Louis830903/AI-Bridge/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python"></a>
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-compatible-green.svg" alt="MCP"></a>
</p>

<p align="center">
  <a href="README.md">English</a> | 
  <a href="docs/DEVELOPMENT_PLAN.md">开发计划</a> |
  <a href="docs/AAIP_SPEC.md">AAIP协议规范</a>
</p>

---

## 什么是 AI-Bridge？

**AI-Bridge** 是一个开源的AI自动化基础设施层，通过标准化协议让AI助手能够操控GUI应用。可以把它理解为 **AI自动化领域的"USB-C"** —— 一个通用接口，连接任何AI到任何应用。

### 当前的问题

现有的AI自动化方案碎片化且不可靠：

```
AI助手 → 截图 → OCR识别 → 坐标计算 → 鼠标点击
              ↓
        慢、不稳定、容易出错
```

### 我们的解决方案

AI-Bridge 提供语义化、标准化的接口：

```
AI助手 → MCP协议 → AI-Bridge → 原生应用API
              ↓
        快速、可靠、可预测
```

## 核心特性

- **MCP兼容** — 支持 Claude、GPT、千问等所有兼容MCP的AI
- **全球化+本土化** — 13个 IM 平台: WhatsApp, Messenger, Telegram, Slack, Teams, Discord, LINE, Viber, KakaoTalk, 飞书, 钉钉, 企微, Google Chat
- **胶水代码架构** — 轻量封装成熟库，~500行核心代码
- **协议驱动** — AAIP（AI应用交互协议）标准
- **易于扩展** — 轻松添加新适配器

## 支持的应用

| 类别 | 应用 | 状态 |
|------|------|------|
| **浏览器** | Chrome, Edge | ✅ 就绪 |
| **全球IM (企业级)** | Slack, Microsoft Teams, Discord, Google Chat | ✅ 就绪 |
| **全球IM (消费级)** | WhatsApp, Messenger, Telegram, LINE, Viber, KakaoTalk | ✅ 就绪 |
| **国内IM** | 飞书, 钉钉, 企业微信 | ✅ 就绪 |
| **办公软件** | Word, Excel, PowerPoint, WPS | ✅ 就绪 |
| **桌面应用** | 任意Windows应用 (通过UIA) | ✅ 就绪 |

## 快速开始

### 安装

```bash
pip install ai-bridge

# 安装所有适配器
pip install ai-bridge[all]

# 安装特定适配器
pip install ai-bridge[browser,im,office]
```

### 基础用法

```python
from aibridge import AIBridge

# 初始化
bridge = AIBridge()

# Chrome自动化
await bridge.execute("chrome", "goto", "https://example.com")
await bridge.execute("chrome", "click", {"name": "提交"})

# 发送飞书消息
await bridge.execute("feishu", "send", {
    "chat_id": "oc_xxx",
    "text": "来自AI-Bridge的问候！"
})

# Excel自动化
await bridge.execute("excel", "write", {
    "file": "报告.xlsx",
    "cell": "A1",
    "value": "销售报告"
})
```

### Claude Desktop 集成

在 Claude Desktop 配置文件 (`claude_desktop_config.json`) 中添加：

```json
{
  "mcpServers": {
    "aibridge": {
      "command": "python",
      "args": ["-m", "aibridge"],
      "env": {
        "FEISHU_APP_ID": "你的app_id",
        "FEISHU_APP_SECRET": "你的secret"
      }
    }
  }
}
```

## 架构

```
┌─────────────────────────────────────────────────┐
│                AI 助手                           │
│    Claude | GPT | 千问 | OpenClaw | 自定义      │
└─────────────────────────────────────────────────┘
                        │ MCP 协议
                        ▼
┌─────────────────────────────────────────────────┐
│              AI-Bridge 核心                      │
│   ┌─────────────────────────────────────────┐  │
│   │            MCP Server                    │  │
│   │      协议解析 / 路由 / 响应               │  │
│   └─────────────────────────────────────────┘  │
│   ┌─────────────────────────────────────────┐  │
│   │          适配器管理器                     │  │
│   │    注册 / 生命周期 / 调度                 │  │
│   └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  浏览器      │ │    IM       │ │   Office    │
│  适配器      │ │   适配器    │ │   适配器    │
│ [Playwright]│ │ [HTTP API]  │ │  [win32com] │
└─────────────┘ └─────────────┘ └─────────────┘
```

## AAIP 协议

AI-Bridge 定义了 **AAIP（AI应用交互协议）** —— AI与GUI通信的标准：

```yaml
# 请求格式
Request:
  app: string       # 目标应用ID
  action: string    # 操作类型
  target: object    # 元素定位器
  value: any        # 操作值
  options: object   # 附加选项

# 响应格式
Response:
  success: bool
  data: any
  error: string
  screenshot: string  # Base64 (可选)
```

### 标准操作

| 操作 | 说明 |
|------|------|
| `click` | 点击元素 |
| `type` | 输入文本 |
| `read` | 读取元素文本 |
| `screenshot` | 截图 |
| `list_elements` | 列出可交互元素 |
| `wait` | 等待元素出现 |
| `launch` | 启动应用 |
| `close` | 关闭应用 |

## 适配器示例

### 浏览器适配器 (Chrome/Edge)

```python
# 导航
await bridge.execute("chrome", "goto", "https://google.com")

# 点击按钮
await bridge.execute("chrome", "click", {"name": "搜索"})

# 填写输入框
await bridge.execute("chrome", "type", {
    "target": {"css": "input[name='q']"},
    "value": "AI-Bridge"
})

# 获取页面内容
result = await bridge.execute("chrome", "read", {"css": "h1"})
```

### 飞书适配器

```python
# 获取群列表
chats = await bridge.execute("feishu", "list_chats")

# 发送消息
await bridge.execute("feishu", "send", {
    "chat_id": "oc_xxx",
    "text": "会议提醒：今天下午3点"
})

# 发送卡片消息
await bridge.execute("feishu", "send_card", {
    "chat_id": "oc_xxx",
    "title": "任务更新",
    "content": "项目已完成！"
})
```

### Slack 适配器

```python
# 发送消息
await bridge.execute("slack", "send_message", {
    "channel": "#general",
    "text": "Hello from AI-Bridge!"
})

# 获取频道列表
channels = await bridge.execute("slack", "list_channels")
```

### Telegram 适配器

```python
# 发送消息
await bridge.execute("telegram", "send_message", {
    "chat_id": "123456",
    "text": "来自AI-Bridge的问候！"
})

# 发送图片
await bridge.execute("telegram", "send_photo", {
    "chat_id": "123456",
    "photo": "screenshot.png",
    "caption": "今日报告"
})
```

### Discord 适配器

```python
# 发送消息
await bridge.execute("discord", "send_message", {
    "channel": "channel_id",
    "text": "Hello from AI-Bridge!"
})

# 发送富文本
await bridge.execute("discord", "send_embed", {
    "channel": "channel_id",
    "embed": {"title": "报告", "description": "每日汇总"}
})
```

### 钉钉适配器

```python
# Webhook方式发送消息
await bridge.execute("dingtalk", "send_webhook", {
    "text": "系统告警：服务器CPU使用率超过90%"
})

# 工作通知
await bridge.execute("dingtalk", "send_work_notice", {
    "userid_list": ["user1", "user2"],
    "content": "请审批您的报销单"
})
```

### 企业微信适配器

```python
# 发送应用消息
await bridge.execute("wecom", "send", {
    "touser": "@all",
    "content": "全员通知：明天放假"
})

# 发送到群聊
await bridge.execute("wecom", "send_to_chat", {
    "chatid": "CHATID",
    "content": "群公告：周会改到周四"
})
```

### Office适配器

```python
# 创建Word文档
await bridge.execute("word", "create", {
    "path": "报告.docx",
    "content": "2024年度报告"
})

# 读取Excel单元格
value = await bridge.execute("excel", "read", {
    "file": "数据.xlsx",
    "sheet": "Sheet1",
    "cell": "A1"
})

# 写入Excel单元格
await bridge.execute("excel", "write", {
    "file": "数据.xlsx",
    "cell": "B1",
    "value": 100
})
```

## 配置

创建 `aibridge.yaml`：

```yaml
server:
  transport: stdio
  log_level: INFO

adapters:
  chrome:
    enabled: true
    cdp_url: "http://localhost:9222"
  
  # 全球 IM
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
  
  # 国内 IM
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
    agent_id: ${WECOM_AGENT_ID}
    
  office:
    enabled: true
    visible: true
    
  wps:
    enabled: true
    visible: true
```

## 为什么选择 AI-Bridge？

### 核心价值

| 维度 | 传统方案 | AI-Bridge |
|------|---------|-----------|
| **稳定性** | 截图+OCR，容易出错 | 原生API，精准可靠 |
| **速度** | 秒级延迟 | 毫秒级响应 |
| **维护** | 每个AI单独适配 | 一次适配，所有AI可用 |
| **本土化** | 不支持国内应用 | 原生支持飞书/钉钉/企微/WPS |
| **全球化** | 零散支持 | 原生支持Slack/Teams/Discord/Telegram |

### 胶水代码的力量

```
我们的核心代码：~500行
     ↓
封装的成熟库能力：无限
     ↓
价值 = 标准协议 + 生态位 + 本土化
```

## 参与贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

### 添加新适配器

```python
from aibridge.adapters.base import BaseAdapter, AdapterInfo

class MyAdapter(BaseAdapter):
    info = AdapterInfo(
        id="myapp",
        name="我的应用",
        type="custom",
        actions=["click", "type", "read"]
    )
    
    async def connect(self):
        # 初始化连接
        pass
    
    async def execute(self, action, target=None, value=None, options=None):
        # 处理操作
        pass
```

## 路线图

- [x] 核心协议 & MCP Server
- [x] 浏览器适配器 (Chrome, Edge)
- [x] IM适配器 (飞书, 钉钉, 企业微信)
- [x] 办公适配器 (MS Office, WPS)
- [x] 通用桌面适配器 (UIA)
- [ ] 适配器市场
- [ ] 可视化流程编排
- [ ] 企业版功能

## 许可证

Apache 2.0 — 详见 [LICENSE](LICENSE)

## 链接

- [GitHub](https://github.com/Louis830903/AI-Bridge)
- [文档](https://ai-bridge.dev)
- [AAIP规范](docs/AAIP_SPEC.md)
- [开发计划](docs/DEVELOPMENT_PLAN.md)

---

<p align="center">
  为AI自动化社区用 ❤️ 打造
</p>
