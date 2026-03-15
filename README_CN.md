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
  <strong>🚀 一行代码，AI 操控任意桌面软件</strong><br/>
  <strong>🚀 One line of code. AI controls any desktop app.</strong>
</p>

<br/>

<!-- 徽章墙 -->
<p>
  <a href="https://github.com/Louis830903/AI-Bridge/stargazers">
    <img src="https://img.shields.io/github/stars/Louis830903/AI-Bridge?style=for-the-badge&logo=github&color=yellow&label=Star" alt="Stars">
  </a>
  <a href="https://github.com/Louis830903/AI-Bridge/releases">
    <img src="https://img.shields.io/github/v/release/Louis830903/AI-Bridge?style=for-the-badge&color=blue&label=版本" alt="Release">
  </a>
  <a href="https://python.org">
    <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  </a>
  <a href="https://modelcontextprotocol.io">
    <img src="https://img.shields.io/badge/MCP-兼容-00D084?style=for-the-badge&logo=anthropic&logoColor=white" alt="MCP">
  </a>
</p>

<p>
  <a href="https://github.com/Louis830903/AI-Bridge/actions">
    <img src="https://img.shields.io/badge/测试-647%20通过-success?style=flat-square" alt="Tests">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/许可证-Apache%202.0-blue.svg?style=flat-square" alt="License">
  </a>
  <a href="https://github.com/Louis830903/AI-Bridge/pulls">
    <img src="https://img.shields.io/badge/PR-欢迎-brightgreen?style=flat-square" alt="PRs">
  </a>
</p>

<br/>

<!-- 导航 -->
<p>
  <a href="README.md">🇺🇸 English</a> •
  <a href="#-30-秒演示">⚡ 30秒演示</a> •
  <a href="#-使用场景">🎯 使用场景</a> •
  <a href="#-快速开始">🚀 快速开始</a> •
  <a href="#️-系统架构">🏗️ 系统架构</a>
</p>

</div>

---

<br/>

<!-- Demo GIF 展示区 -->
<div align="center">

## ⚡ 30 秒演示

<!-- 演示代码 -->
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

**☝️ AI 自动：打开 Chrome → 访问 GitHub → 截图保存**

</div>

<br/>

---

## 🎯 使用场景

<table>
<tr>
<td width="25%" align="center">

### 🎬 自动剪辑视频

```
"把这个视频剪成30秒，
加上背景音乐，
导出1080p"
     ↓
AI-Bridge + FFmpeg
     ↓
✅ 几秒搞定
```

</td>
<td width="25%" align="center">

### 📊 自动生成报告

```
"从 Excel 取销售数据，
生成图表，
做成 PPT 报告"
     ↓
AI-Bridge + Office
     ↓
✅ 专业报告
```

</td>
<td width="25%" align="center">

### 🌐 网页自动化

```
"登录网站，
抓取商品信息，
存入数据库"
     ↓
AI-Bridge + Chrome
     ↓
✅ 数据入库
```

</td>
<td width="25%" align="center">

### 🤖 多 Agent 协作

```
"搜集 AI 新闻，
分析趋势，
发送摘要到 Slack"
     ↓
AI-Bridge + A2A
     ↓
✅ Agent 协作
```

</td>
</tr>
</table>

---

## 🔥 为什么选择 AI-Bridge？

<table>
<tr>
<td width="50%">

### ❌ 以前：AI 只能聊天

```
用户："帮我剪辑视频"
AI：  "我做不到，但我可以告诉你
       怎么手动操作..."
```

**AI 只能输出文字** 😞

</td>
<td width="50%">

### ✅ 现在：AI 直接行动

```
用户："帮我剪辑视频"
AI：  *打开 FFmpeg*
      *处理视频*
      *导出结果*
      "搞定！视频在这里"
```

**AI 真正干活** 🚀

</td>
</tr>
</table>

<br/>

<div align="center">

### ⚡ 背后的魔法

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    你的 AI      │     │   AI-Bridge     │     │    任意软件     │
│ (Claude, GPT)   │ ──▶ │      网关       │ ──▶ │ Chrome, Office  │
│                 │ MCP │                 │     │ FFmpeg, Docker  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

</div>

---

## 🚀 快速开始

### 1️⃣ 安装

```bash
pip install ai-bridge
```

### 2️⃣ 配置 Claude Desktop

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

### 3️⃣ 搞定！让 Claude 帮你：

```
"打开 Chrome 截图 github.com"
"把这个视频转成 MP3"
"用这些数据生成 Excel 报告"
```

---

## 🛠️ 支持的工具

<div align="center">

| 分类 | 工具 |
|:----:|------|
| 🌐 **浏览器** | Chrome, Edge (Playwright 驱动) |
| 📊 **办公** | Word, Excel, PowerPoint, WPS |
| 🎬 **媒体** | FFmpeg, ImageMagick, Blender, SoX |
| 📄 **文档** | Pandoc (40+ 格式) |
| 🎵 **下载** | yt-dlp (1000+ 网站) |
| 🐳 **开发** | Docker, Prettier |
| 🔗 **MCP 生态** | Browser Use, Firecrawl, Notion, Slack, GitHub |

</div>

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         AI 助手                                  │
│               (Claude, GPT, 千问, Gemini 等)                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │ MCP / A2A 协议
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AI-Bridge v5.0 网关                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  v5.0 协议扩展层                                           │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────┐ │  │
│  │  │Agent Card  │ │ Prometheus │ │ A2A 流式   │ │MCP 发现 │ │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └─────────┘ │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  v4.0 企业管理层                                           │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────┐ │  │
│  │  │  策略引擎  │ │  计量采集  │ │  分布追踪  │ │ DAG编排 │ │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └─────────┘ │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ MCP 注册中心 │  │  A2A 网关   │  │    协议桥接器      │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┬──────────────────┐
        ▼                   ▼                   ▼                  ▼
   ┌─────────┐         ┌─────────┐         ┌─────────┐       ┌─────────┐
   │ 浏览器  │         │  办公   │         │   CLI   │       │   MCP   │
   │ 适配器  │         │ 适配器  │         │  适配器 │       │  生态   │
   └─────────┘         └─────────┘         └─────────┘       └─────────┘
        │                   │                   │                  │
   Chrome/Edge          Word/Excel         FFmpeg/Docker      Firecrawl
                        PowerPoint         yt-dlp/Pandoc      Notion/Slack
```

---

## 📊 企业级功能

<details>
<summary><b>🔐 策略访问控制 (PBAC)</b></summary>

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
<summary><b>📈 使用量计量与配额</b></summary>

```python
from aibridge.enterprise import MeteringCollector, QuotaManager

metering = MeteringCollector()
await metering.record(user_id="user1", tool_name="browser/navigate")

quota = QuotaManager(metering)
quota.set_user_quota("user1", QuotaConfig(max_calls_per_day=1000))
```

</details>

<details>
<summary><b>🔍 分布式追踪 (OpenTelemetry)</b></summary>

```python
from aibridge.enterprise import Tracer, TracerConfig

tracer = Tracer(TracerConfig(service_name="my-service"))
with tracer.start_as_current_span("tool_call") as span:
    span.set_attribute("user.id", "user1")
    # ... 执行工具
```

</details>

<details>
<summary><b>🤖 多 Agent 编排</b></summary>

```python
from aibridge.core import TaskGraph, Orchestrator

graph = TaskGraph(name="research-workflow")
t1 = graph.add_task("search", "search-agent", "web_search")
t2 = graph.add_task("analyze", "analyzer-agent", depends_on={t1.task_id})
result = await orchestrator.execute(graph)
```

</details>

---

## 📖 文档

| 资源 | 链接 |
|------|------|
| 📚 快速入门 | [examples/basic_usage.py](ai-bridge/examples/basic_usage.py) |
| 🏗️ 网关演示 | [examples/gateway_demo.py](ai-bridge/examples/gateway_demo.py) |
| 📋 更新日志 | [CHANGELOG.md](ai-bridge/CHANGELOG.md) |
| 🤝 参与贡献 | [CONTRIBUTING.md](ai-bridge/CONTRIBUTING.md) |

---

## 🌟 Star 趋势

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=Louis830903/AI-Bridge&type=Date)](https://star-history.com/#Louis830903/AI-Bridge&Date)

</div>

---

## 🤝 参与贡献

欢迎贡献代码！请查看 [CONTRIBUTING.md](ai-bridge/CONTRIBUTING.md)。

```bash
git clone https://github.com/Louis830903/AI-Bridge.git
cd AI-Bridge/ai-bridge
pip install -e ".[dev]"
pytest tests/ -v
```

---

## 📄 许可证

Apache 2.0 — 详见 [LICENSE](LICENSE)

---

<div align="center">

### 🙏 致谢

[Playwright](https://playwright.dev/) • [MCP](https://modelcontextprotocol.io/) • [A2A](https://google.github.io/a2a-spec/) • [所有贡献者](https://github.com/Louis830903/AI-Bridge/graphs/contributors) ❤️

<br/>

---

<br/>

**如果 AI-Bridge 帮到了你，请给个 ⭐ 支持一下！**

<br/>

```
     _    ___      ____       _     _            
    / \  |_ _|    | __ ) _ __(_) __| | __ _  ___ 
   / _ \  | |_____|  _ \| '__| |/ _` |/ _` |/ _ \
  / ___ \ | |_____| |_) | |  | | (_| | (_| |  __/
 /_/   \_\___|    |____/|_|  |_|\__,_|\__, |\___|
                                      |___/      

        让 AI 从聊天走向行动 🚀
```

<br/>

**为 AI 自动化社区倾心打造 ❤️**

</div>
