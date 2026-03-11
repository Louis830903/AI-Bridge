# AI-Bridge 推广文案 / Promotion Copy

---

## 📝 英文版 (Hacker News / Reddit / Product Hunt)

### Title Options:
1. **AI-Bridge: The "USB-C" for AI Automation – One Protocol to Control 13 IM Platforms + Office + Browser**
2. **Show HN: AI-Bridge – Let Claude/GPT Control Slack, Teams, Telegram, Feishu, Excel via MCP**
3. **Open Source MCP Server connecting AI Agents to 13 IM platforms (WhatsApp, Slack, Discord, Telegram...) + Office Suite**

### Body (Hacker News / Reddit):

```
Hey everyone! 👋

I built AI-Bridge because I was frustrated with AI automation tools that rely on screenshots + OCR + coordinate clicking. They're slow, unstable, and break constantly.

**The Problem:**
```
AI → Screenshot → OCR → Coordinates → Click
     = Slow, Unstable, Error-prone
```

**The Solution:**
```
AI → MCP Protocol → AI-Bridge → Native API
     = Fast, Reliable, Precise
```

**What AI-Bridge does:**
- 🤖 Works with Claude, GPT, Qwen, and any MCP-compatible AI
- 💬 Controls 13 IM platforms: Slack, Teams, Discord, Telegram, WhatsApp, Messenger, LINE, Viber, KakaoTalk, Feishu, DingTalk, WeCom, Google Chat
- 📊 Automates Office: Word, Excel, PowerPoint, WPS
- 🌐 Browser automation: Chrome, Edge
- 🖥️ Desktop apps via Windows UI Automation

**Example:**
```python
# Send Slack message
await bridge.execute("slack", "send_message", {
    "channel": "#general",
    "text": "Deployed! 🚀"
})

# Automate Excel
await bridge.execute("excel", "write", {
    "file": "report.xlsx",
    "cell": "A1", 
    "value": "AI-Generated"
})
```

**Why it matters:**
- Write once, control everything
- Millisecond response (not seconds)
- Global + China coverage (unique!)
- ~500 lines of core code wrapping mature libraries

GitHub: https://github.com/Louis830903/AI-Bridge

Would love feedback! What platforms should I add next?
```

---

## 📝 中文版 (掘金 / 知乎 / V2EX)

### 标题选项:
1. **开源了！AI-Bridge：让 Claude/GPT 直接操控飞书、钉钉、企微、Slack、Excel 的 MCP 服务器**
2. **告别截图+OCR！一个协议让 AI 控制 13 个即时通讯平台 + Office 全家桶**
3. **我写了个 AI 自动化的"万能接口"：支持飞书/钉钉/企微/Slack/Telegram/Discord...**

### 正文 (掘金/知乎):

```markdown
# AI-Bridge：AI 自动化的"USB-C"

## 痛点

现在的 AI 自动化方案太痛苦了：

```
AI → 截图 → OCR → 坐标计算 → 点击
      ↓
  慢、不稳定、经常崩
```

我做了一个截图+OCR的方案，结果：
- 截图要 2-3 秒
- OCR 识别中文经常出错
- 窗口移动一下坐标就全错
- 换个分辨率直接寄

## 解决方案

AI-Bridge 直接调用原生 API：

```
AI → MCP 协议 → AI-Bridge → 原生 API
      ↓
  毫秒级、稳定、精准
```

## 支持什么？

### 💬 即时通讯（13个平台，全球最全！）

| 全球企业 | 全球消费 | 中国本土 |
|---------|---------|---------|
| Slack | WhatsApp | 飞书 |
| Teams | Telegram | 钉钉 |
| Discord | Messenger | 企微 |
| Google Chat | LINE/Viber/KakaoTalk | |

### 📊 办公软件
- Microsoft Office (Word/Excel/PPT)
- WPS Office（国产！）

### 🌐 浏览器
- Chrome, Edge

## 怎么用？

```python
from aibridge import AIBridge

bridge = AIBridge()

# 发飞书消息
await bridge.execute("feishu", "send", {
    "chat_id": "oc_xxx",
    "text": "AI 自动发送的消息 🤖"
})

# 发钉钉告警
await bridge.execute("dingtalk", "send_webhook", {
    "text": "⚠️ 服务器 CPU > 90%"
})

# Excel 自动填表
await bridge.execute("excel", "write", {
    "file": "报表.xlsx",
    "cell": "A1",
    "value": "自动生成的数据"
})
```

## 为什么做这个？

1. **MCP 协议火了** - Claude Desktop 支持后，AI 自动化市场爆发
2. **国内没人做** - 国外工具不支持飞书/钉钉/企微/WPS
3. **胶水代码的力量** - 核心 ~500 行，封装成熟库能力无限

## 开源地址

GitHub: https://github.com/Louis830903/AI-Bridge

欢迎 Star ⭐️ / Fork / PR！

下一步计划：
- [ ] 适配器市场
- [ ] 可视化流程编排
- [ ] 企业版功能

---

有什么想自动化的场景？评论区告诉我！
```

---

## 📝 V2EX 版本（更口语化）

### 标题:
**开源一个 MCP 服务器，让 AI 直接控制飞书/钉钉/Slack/Excel，不用截图 OCR 了**

### 正文:

```
做 AI 自动化的应该都有体会，截图+OCR+坐标点击这套方案有多坑：

- 截图慢
- OCR 中文识别一坨
- 窗口一动坐标全错
- 换分辨率直接 GG

所以我写了 AI-Bridge，直接调原生 API：

- 支持 13 个 IM：飞书、钉钉、企微、Slack、Teams、Discord、Telegram、WhatsApp...
- 支持 Office：Word、Excel、PPT、WPS
- 支持浏览器：Chrome、Edge
- 兼容 MCP 协议，Claude Desktop 直接用

代码很简单：

```python
# 发飞书
await bridge.execute("feishu", "send", {"chat_id": "oc_xxx", "text": "Hello"})

# 发钉钉
await bridge.execute("dingtalk", "send_webhook", {"text": "告警！"})
```

GitHub: https://github.com/Louis830903/AI-Bridge

求 Star 🌟

大家有什么想自动化的场景可以提 issue，我来加适配器。
```

---

## 📝 Twitter/X 版本

### English:
```
🚀 Just open-sourced AI-Bridge!

The "USB-C" for AI automation:
✅ 13 IM platforms (Slack, Teams, Discord, Telegram, WhatsApp, Feishu...)
✅ Office Suite (Word, Excel, PPT, WPS)
✅ Browser automation
✅ MCP compatible (works with Claude!)

No more screenshot + OCR + coordinate clicking 🎯

GitHub: https://github.com/Louis830903/AI-Bridge

#AI #Automation #MCP #Claude #OpenSource
```

### 中文:
```
🚀 开源了 AI-Bridge！

AI 自动化的"万能接口"：
✅ 13 个 IM 平台（飞书/钉钉/企微/Slack/Telegram...）
✅ Office 全家桶（Word/Excel/WPS）
✅ 浏览器自动化
✅ MCP 协议兼容，Claude Desktop 直接用

告别截图+OCR，直接调原生 API 🎯

GitHub: https://github.com/Louis830903/AI-Bridge

#AI自动化 #开源 #RPA
```

---

## 📝 Product Hunt Tagline

**One-liner:**
> AI-Bridge: The universal adapter connecting AI assistants to 13 IM platforms + Office + Browser

**Description:**
> Stop using screenshots + OCR for AI automation. AI-Bridge lets Claude, GPT, and other AI assistants directly control Slack, Teams, Telegram, WhatsApp, Feishu, DingTalk, Excel, and more through native APIs. One MCP server to rule them all.
